//! Personal XKB settings and wlroots output management through existing tools.
use crate::widgets::*;
use anyhow::{Context, Result, ensure};
use gtk::{glib, prelude::*};
use rampi_core::i18n::text as tr;
use std::{cell::Cell, path::PathBuf, rc::Rc};

const LAYOUTS: [(&str, &str); 6] = [
    ("de", "Deutsch"),
    ("us", "English (US)"),
    ("gb", "English (UK)"),
    ("fr", "Français"),
    ("es", "Español"),
    ("it", "Italiano"),
];

/// Standard Windows input-locale identifiers for the existing XKB choices.
pub fn rdp_keyboard_layout() -> u32 {
    let configured = keyboard_file().ok().and_then(|path| {
        let metadata = std::fs::symlink_metadata(&path).ok()?;
        if !metadata.is_file() || metadata.file_type().is_symlink() || metadata.len() > 16384 {
            return None;
        }
        std::fs::read_to_string(path).ok()
    });
    let code = configured.as_deref().and_then(|text| {
        text.lines()
            .find_map(|line| line.strip_prefix("XKB_DEFAULT_LAYOUT="))
    });
    match code {
        Some("de") => 0x0407,
        Some("us") => 0x0409,
        Some("gb") => 0x0809,
        Some("fr") => 0x040c,
        Some("es") => 0x040a,
        Some("it") => 0x0410,
        _ => 0,
    }
}

pub fn keyboard_file() -> Result<PathBuf> {
    Ok(rampi_core::config::config_dir()?.join("labwc/environment"))
}
pub fn save_keyboard(layout: &str) -> Result<()> {
    use std::{
        io::Write,
        os::unix::fs::{MetadataExt, PermissionsExt},
    };
    ensure!(
        LAYOUTS.iter().any(|(code, _)| *code == layout),
        tr("keyboard-invalid-layout", &[])
    );
    let path = keyboard_file()?;
    let dir = path
        .parent()
        .context(tr("settings-directory-missing", &[]))?;
    std::fs::create_dir_all(dir)?;
    let uid = gtk::gio::Credentials::new().unix_user()?;
    for folder in [
        dir,
        dir.parent()
            .context(tr("settings-directory-missing", &[]))?,
    ] {
        let meta = std::fs::symlink_metadata(folder)?;
        ensure!(
            meta.is_dir() && !meta.file_type().is_symlink() && meta.uid() == uid,
            tr("settings-directory-unsafe", &[])
        );
        std::fs::set_permissions(folder, std::fs::Permissions::from_mode(0o700))?;
    }
    let original = match std::fs::symlink_metadata(&path) {
        Ok(meta) => {
            ensure!(
                meta.is_file()
                    && !meta.file_type().is_symlink()
                    && meta.uid() == uid
                    && meta.len() <= 65536,
                tr("keyboard-config-unsafe", &[])
            );
            std::fs::read_to_string(&path)?
        }
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => String::new(),
        Err(e) => return Err(e.into()),
    };
    let mut temp = tempfile::NamedTempFile::new_in(dir)?;
    temp.as_file()
        .set_permissions(std::fs::Permissions::from_mode(0o600))?;
    for line in original
        .lines()
        .filter(|l| !l.trim_start().starts_with("XKB_DEFAULT_LAYOUT="))
    {
        writeln!(temp, "{line}")?;
    }
    writeln!(temp, "XKB_DEFAULT_LAYOUT={layout}")?;
    temp.as_file().sync_all()?;
    temp.persist(&path)?;
    std::fs::File::open(dir)?.sync_all()?;
    Ok(())
}

#[derive(Clone, Debug)]
pub struct Output {
    pub name: String,
    pub modes: Vec<String>,
    pub current: String,
}
pub async fn outputs() -> Result<Vec<Output>> {
    let (ok, bytes) = crate::process::output("wlr-randr", &["--json".into()], 4, 262144).await?;
    ensure!(ok, tr("display-service-unavailable", &[]));
    let value: serde_json::Value = serde_json::from_slice(&bytes)?;
    let rows = value.as_array().context(tr("display-list-invalid", &[]))?;
    ensure!(rows.len() <= 32, tr("display-list-limit", &[]));
    let mut result = vec![];
    for row in rows {
        if row["enabled"].as_bool() != Some(true) {
            continue;
        }
        let name = row["name"]
            .as_str()
            .context(tr("display-name-missing", &[]))?;
        ensure!(
            !name.is_empty() && name.len() <= 256 && !name.chars().any(char::is_control),
            tr("display-name-invalid", &[])
        );
        let modes = row["modes"]
            .as_array()
            .context(tr("display-modes-missing", &[]))?;
        ensure!(modes.len() <= 512, tr("display-modes-limit", &[]));
        let mut output = Output {
            name: name.into(),
            modes: vec![],
            current: String::new(),
        };
        for mode in modes {
            let width = mode["width"]
                .as_u64()
                .context(tr("display-width-missing", &[]))?;
            let height = mode["height"]
                .as_u64()
                .context(tr("display-height-missing", &[]))?;
            let rate = mode["refresh"].as_f64().unwrap_or(0.0);
            ensure!(
                (320..=16384).contains(&width)
                    && (200..=16384).contains(&height)
                    && rate.is_finite()
                    && (0.0..=1000.0).contains(&rate),
                tr("display-mode-invalid", &[])
            );
            let text = if rate > 0.0 {
                format!("{width}x{height}@{rate:.6}Hz")
            } else {
                format!("{width}x{height}")
            };
            if mode["current"].as_bool() == Some(true) {
                output.current = text.clone();
            }
            output.modes.push(text);
        }
        result.push(output);
    }
    Ok(result)
}
pub async fn apply(name: &str, mode: &str) -> Result<()> {
    let current = outputs().await?;
    ensure!(
        current
            .iter()
            .any(|o| o.name == name && o.modes.iter().any(|m| m == mode)),
        tr("display-mode-unavailable", &[])
    );
    let (ok, _) = crate::process::output(
        "wlr-randr",
        &["--output".into(), name.into(), "--mode".into(), mode.into()],
        4,
        32768,
    )
    .await?;
    ensure!(ok, tr("display-mode-failed", &[]));
    Ok(())
}

pub fn append(page: &gtk::Box, stack: &gtk::Stack, status: &gtk::Label, f: &Feedback) {
    let messages = rampi_core::i18n::text;
    page.append(&label(&messages("language-heading", &[])));
    page.append(&label(&messages("language-description", &[])));
    let languages = gtk::ListBox::new();
    languages.set_widget_name("language-choices");
    languages.set_selection_mode(gtk::SelectionMode::Single);
    for (_, name, _) in rampi_core::i18n::LANGUAGES {
        languages.append(&label(name));
    }
    let selected_language = f.settings_language();
    let index = rampi_core::i18n::LANGUAGES
        .iter()
        .position(|item| item.0 == selected_language)
        .unwrap_or(0);
    languages.select_row(languages.row_at_index(index as i32).as_ref());
    page.append(&languages);
    let save_language = button(&messages("language-save", &[]), f);
    let (feedback, stat) = (f.clone(), status.clone());
    save_language.connect_clicked(move |_| {
        let Some(selected) = languages.selected_row() else {
            return;
        };
        let Some((code, _, _)) = rampi_core::i18n::LANGUAGES.get(selected.index() as usize) else {
            return;
        };
        match feedback.save_language(code) {
            Ok(()) => stat.set_text(&rampi_core::i18n::text("language-saved", &[])),
            Err(error) => stat.set_text(&error.to_string()),
        }
    });
    page.append(&save_language);
    page.append(&label(&tr("keyboard-heading", &[])));
    let choices = gtk::ListBox::new();
    choices.set_selection_mode(gtk::SelectionMode::Single);
    for (_, title) in LAYOUTS {
        choices.append(&label(title));
    }
    choices.set_widget_name("keyboard-layout");
    choices.select_row(choices.row_at_index(0).as_ref());
    if let Ok(path) = keyboard_file()
        && let Ok(text) = std::fs::read_to_string(path)
        && let Some(index) = LAYOUTS.iter().position(|(code, _)| {
            text.lines()
                .any(|l| l == format!("XKB_DEFAULT_LAYOUT={code}"))
        })
    {
        choices.select_row(choices.row_at_index(index as i32).as_ref());
    }
    page.append(&choices);
    let save = button(&tr("keyboard-apply", &[]), f);
    let stat = status.clone();
    save.connect_clicked(move |b| {
        let Some(row) = choices.selected_row() else {
            return;
        };
        let index = row.index() as usize;
        let Some((code, _)) = LAYOUTS.get(index) else {
            return;
        };
        if let Err(e) = save_keyboard(code) {
            stat.set_text(&e.to_string());
            return;
        }
        b.set_sensitive(false);
        let (b, stat) = (b.clone(), stat.clone());
        glib::MainContext::default().spawn_local(async move {
            let result = crate::process::output("labwc", &["--reconfigure".into()], 3, 16384).await;
            stat.set_text(&tr(
                if matches!(result, Ok((true, _))) {
                    "keyboard-applied"
                } else {
                    "keyboard-saved-relogin"
                },
                &[],
            ));
            b.set_sensitive(true);
        });
    });
    page.append(&save);
    let test = gtk::Entry::builder()
        .placeholder_text(tr("keyboard-test", &[]))
        .build();
    test.set_widget_name("keyboard-try");
    page.append(&test);
    page.append(&label(&tr("display-heading", &[])));
    let refresh = button(&tr("display-refresh", &[]), f);
    page.append(&refresh);
    let list = column();
    page.append(&list);
    let (s, stat, feedback) = (stack.clone(), status.clone(), f.clone());
    refresh.connect_clicked(move |b| {
        b.set_sensitive(false);
        let (b, list, s, stat, feedback) = (
            b.clone(),
            list.clone(),
            s.clone(),
            stat.clone(),
            feedback.clone(),
        );
        glib::MainContext::default().spawn_local(async move {
            while let Some(child) = list.first_child() {
                list.remove(&child);
            }
            match outputs().await {
                Err(e) => stat.set_text(&e.to_string()),
                Ok(outputs) => {
                    for output in outputs {
                        list.append(&label(&tr(
                            "display-current",
                            &[("output", &output.name), ("mode", &output.current)],
                        )));
                        for mode in output.modes.clone() {
                            let action = button(&format!("{} · {mode}", output.name), &feedback);
                            action.set_sensitive(
                                mode != output.current && !output.current.is_empty(),
                            );
                            let (o, s, stat, f) =
                                (output.clone(), s.clone(), stat.clone(), feedback.clone());
                            action.connect_clicked(move |_| confirm(&s, &o, &mode, &stat, &f));
                            list.append(&action);
                        }
                    }
                }
            }
            b.set_sensitive(true);
        });
    });
}

pub(crate) fn confirm(
    stack: &gtk::Stack,
    output: &Output,
    target: &str,
    status: &gtk::Label,
    f: &Feedback,
) {
    if stack.child_by_name("display-confirm").is_some() {
        return;
    }
    let page = column();
    let countdown = label(&tr("display-changing", &[]));
    page.append(&countdown);
    let no = button(&tr("display-revert", &[]), f);
    no.set_widget_name("rampi-back");
    let yes = button(&tr("display-keep", &[]), f);
    yes.set_sensitive(false);
    page.append(&no);
    page.append(&yes);
    stack.add_named(&page, Some("display-confirm"));
    stack.set_visible_child_name("display-confirm");
    no.grab_focus();
    let done = Rc::new(Cell::new(false));
    let (s, o, target, stat, done1) = (
        stack.clone(),
        output.clone(),
        target.to_string(),
        status.clone(),
        done.clone(),
    );
    let rollback: Rc<dyn Fn()> = Rc::new(move || {
        if done1.replace(true) {
            return;
        }
        let (s, o, stat) = (s.clone(), o.clone(), stat.clone());
        glib::MainContext::default().spawn_local(async move {
            let result = apply(&o.name, &o.current).await;
            status_result(&stat, result);
            if s.visible_child_name().as_deref() == Some("display-confirm") {
                s.set_visible_child_name("settings");
            }
            if let Some(page) = s.child_by_name("display-confirm") {
                s.remove(&page);
            }
        });
    });
    let r = rollback.clone();
    no.connect_clicked(move |_| r());
    let (s, done2) = (stack.clone(), done.clone());
    yes.connect_clicked(move |_| {
        if !done2.replace(true) {
            s.set_visible_child_name("settings");
            if let Some(page) = s.child_by_name("display-confirm") {
                s.remove(&page);
            }
        }
    });
    let (s, o, stat) = (stack.clone(), output.clone(), status.clone());
    glib::MainContext::default().spawn_local(async move {
        match apply(&o.name, &target).await {
            Err(e) => {
                stat.set_text(&e.to_string());
                rollback();
            }
            Ok(()) if done.get() => {
                let _ = apply(&o.name, &o.current).await;
            }
            Ok(()) => {
                yes.set_sensitive(true);
                let remaining = Rc::new(Cell::new(15u32));
                glib::timeout_add_seconds_local(1, move || {
                    if done.get() {
                        return glib::ControlFlow::Break;
                    }
                    let seconds = remaining.get().saturating_sub(1);
                    remaining.set(seconds);
                    countdown.set_text(&tr(
                        "display-countdown",
                        &[("seconds", &seconds.to_string())],
                    ));
                    if seconds == 0 || s.visible_child_name().as_deref() != Some("display-confirm")
                    {
                        rollback();
                        glib::ControlFlow::Break
                    } else {
                        glib::ControlFlow::Continue
                    }
                });
            }
        }
    });
}
