//! Personal XKB settings and wlroots output management through existing tools.
use crate::widgets::*;
use anyhow::{Context, Result, ensure};
use gtk::{glib, prelude::*};
use std::{cell::Cell, path::PathBuf, rc::Rc};

const LAYOUTS: [(&str, &str); 6] = [
    ("de", "Deutsch"),
    ("us", "English (US)"),
    ("gb", "English (UK)"),
    ("fr", "Français"),
    ("es", "Español"),
    ("it", "Italiano"),
];

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
        "Unbekannte Tastaturbelegung"
    );
    let path = keyboard_file()?;
    let dir = path.parent().context("Konfigurationsordner fehlt")?;
    std::fs::create_dir_all(dir)?;
    let uid = gtk::gio::Credentials::new().unix_user()?;
    for folder in [dir, dir.parent().context("Konfigurationsordner fehlt")?] {
        let meta = std::fs::symlink_metadata(folder)?;
        ensure!(
            meta.is_dir() && !meta.file_type().is_symlink() && meta.uid() == uid,
            "Unsicherer persönlicher Konfigurationsordner"
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
                "Unsichere Tastaturkonfiguration"
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
    ensure!(ok, "Bildschirmdienst nicht erreichbar");
    let value: serde_json::Value = serde_json::from_slice(&bytes)?;
    let rows = value.as_array().context("Ungültige Bildschirmliste")?;
    ensure!(rows.len() <= 32, "Zu viele Bildschirme");
    let mut result = vec![];
    for row in rows {
        if row["enabled"].as_bool() != Some(true) {
            continue;
        }
        let name = row["name"].as_str().context("Bildschirmname fehlt")?;
        ensure!(
            !name.is_empty() && name.len() <= 256 && !name.chars().any(char::is_control),
            "Ungültiger Bildschirmname"
        );
        let modes = row["modes"].as_array().context("Bildschirmmodi fehlen")?;
        ensure!(modes.len() <= 512, "Zu viele Bildschirmmodi");
        let mut output = Output {
            name: name.into(),
            modes: vec![],
            current: String::new(),
        };
        for mode in modes {
            let width = mode["width"].as_u64().context("Breite fehlt")?;
            let height = mode["height"].as_u64().context("Höhe fehlt")?;
            let rate = mode["refresh"].as_f64().unwrap_or(0.0);
            ensure!(
                (320..=16384).contains(&width)
                    && (200..=16384).contains(&height)
                    && rate.is_finite()
                    && (0.0..=1000.0).contains(&rate),
                "Ungültiger Bildschirmmodus"
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
        "Dieser Bildschirmmodus wird nicht mehr angeboten"
    );
    let (ok, _) = crate::process::output(
        "wlr-randr",
        &["--output".into(), name.into(), "--mode".into(), mode.into()],
        4,
        32768,
    )
    .await?;
    ensure!(ok, "Bildschirmmodus konnte nicht angewendet werden");
    Ok(())
}

pub fn append(page: &gtk::Box, stack: &gtk::Stack, status: &gtk::Label, f: &Feedback) {
    page.append(&label("Tastatur · persönliche Belegung der Rampi-Sitzung"));
    let choices = gtk::DropDown::from_strings(&LAYOUTS.map(|(_, title)| title));
    choices.set_widget_name("keyboard-layout");
    if let Ok(path) = keyboard_file()
        && let Ok(text) = std::fs::read_to_string(path)
        && let Some(index) = LAYOUTS.iter().position(|(code, _)| {
            text.lines()
                .any(|l| l == format!("XKB_DEFAULT_LAYOUT={code}"))
        })
    {
        choices.set_selected(index as u32);
    }
    page.append(&choices);
    let save = button("Tastaturbelegung anwenden", f);
    let stat = status.clone();
    save.connect_clicked(move |b| {
        let index = choices.selected() as usize;
        let Some((code, _)) = LAYOUTS.get(index) else { return; };
        if let Err(e) = save_keyboard(code) { stat.set_text(&e.to_string()); return; }
        b.set_sensitive(false);
        let (b, stat) = (b.clone(), stat.clone());
        glib::MainContext::default().spawn_local(async move {
            let result = crate::process::output("labwc", &["--reconfigure".into()], 3, 16384).await;
            stat.set_text(if matches!(result, Ok((true, _))) {
                "Persönliche Tastaturbelegung gespeichert und an die Rampi-Sitzung übergeben. Hier im Testfeld prüfen."
            } else { "Belegung gespeichert. Sie gilt ab der nächsten Rampi-Anmeldung; laufende Sitzung konnte nicht neu geladen werden." });
            b.set_sensitive(true);
        });
    });
    page.append(&save);
    let test = gtk::Entry::builder()
        .placeholder_text("Tastatur hier testen: Y Z @ €")
        .build();
    test.set_widget_name("keyboard-try");
    page.append(&test);
    page.append(&label("Bildschirm · angebotene Auflösungen der laufenden Wayland-Sitzung. Änderungen gelten bis zur Abmeldung."));
    let refresh = button("Bildschirme und Auflösungen anzeigen", f);
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
                        list.append(&label(&format!(
                            "{} · aktuell {}",
                            output.name, output.current
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
    let countdown = label("Auflösung wird geändert …");
    page.append(&countdown);
    let no = button("Zurücksetzen", f);
    no.set_widget_name("rampi-back");
    let yes = button("Auflösung beibehalten", f);
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
            s.set_visible_child_name("settings");
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
                    countdown.set_text(&format!(
                        "Auflösung beibehalten? Automatisches Zurücksetzen in {seconds} Sekunden."
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
