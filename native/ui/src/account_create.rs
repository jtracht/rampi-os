//! Embedded sudo/useradd/passwd workflow; existing PAM and sudo policy authorize it.
use crate::widgets::*;
use gtk::{glib, prelude::*};
use rampi_core::accounts;
use std::{
    cell::{Cell, RefCell},
    ffi::OsString,
    rc::Rc,
};
use vte::prelude::*;

#[derive(Clone, PartialEq)]
struct CreatedAccount {
    name: String,
    uid: u32,
    home: std::path::PathBuf,
}
async fn verify(name: &str) -> anyhow::Result<CreatedAccount> {
    use std::os::unix::fs::{MetadataExt, PermissionsExt};
    let (ok, bytes) =
        crate::process::output("/usr/bin/getent", &["passwd".into(), name.into()], 5, 8192).await?;
    anyhow::ensure!(ok, "Neues Systemkonto konnte nicht geprüft werden");
    let value = String::from_utf8(bytes)?;
    let fields: Vec<_> = value.trim_end().split(':').collect();
    anyhow::ensure!(
        fields.len() == 7 && fields[0] == name && fields[6] == "/bin/bash",
        "Unerwartetes Systemkonto"
    );
    let uid: u32 = fields[2].parse()?;
    let home = std::path::PathBuf::from(fields[5]);
    anyhow::ensure!(uid > 0 && home.is_absolute(), "Unsicheres Systemkonto");
    let meta = std::fs::symlink_metadata(&home)?;
    anyhow::ensure!(
        meta.is_dir()
            && !meta.file_type().is_symlink()
            && meta.uid() == uid
            && meta.permissions().mode() & 0o777 == 0o700,
        "Home-Verzeichnis ist nicht privat oder gehört nicht dem neuen Konto. Ein Administrator muss das gesperrte Konto prüfen; Rampi verändert keine vorhandenen Verzeichnisse."
    );
    Ok(CreatedAccount {
        name: name.into(),
        uid,
        home,
    })
}

fn spawn(term: &vte::Terminal, argv: &[OsString], state: &gtk::Label, finish: Rc<dyn Fn(i32)>) {
    term.set_input_enabled(true);
    let strings: Vec<String> = argv
        .iter()
        .map(|v| v.to_string_lossy().into_owned())
        .collect();
    let argv: Vec<&str> = strings.iter().map(String::as_str).collect();
    let state = state.clone();
    term.spawn_async(vte::PtyFlags::DEFAULT, None, &argv, &[], glib::SpawnFlags::DEFAULT, || {}, -1, None::<&gtk::gio::Cancellable>, move |result| {
        if let Err(error) = result {
            finish(-1);
            state.set_text(&format!("Systemwerkzeug konnte nicht starten: {error}. Erneut versuchen; bestehende Konten bleiben erhalten."));
        }
    });
    term.grab_focus();
}

pub fn open(stack: &gtk::Stack, f: &Feedback) {
    if stack.child_by_name("account-create").is_some() {
        stack.set_visible_child_name("account-create");
        return;
    }
    let page = column();
    let back = button("← System", f);
    back.set_widget_name("rampi-back");
    let s = stack.clone();
    back.connect_clicked(move |_| s.set_visible_child_name("settings"));
    page.append(&back);
    page.append(&label(
        "Weiteres Linux-Konto · 1 Anlegen → 2 Kennwort setzen → 3 Neu anmelden",
    ));
    page.append(&label("Benötigt vorhandene sudo-Berechtigung. Systemwerkzeuge fragen im Terminal nach Kennwörtern; Rampi speichert sie nicht. Das neue Konto erhält ein privates Home-Verzeichnis und keine Administratorrechte. Bestehende Konten werden nicht überschrieben."));
    let name = gtk::Entry::builder()
        .placeholder_text("Neuer Linux-Benutzername")
        .build();
    name.set_widget_name("account-new-name");
    page.append(&name);
    let create = button("Neues Konto anlegen …", f);
    create.set_widget_name("account-create-start");
    let password = button("Kennwort für das neue Konto setzen", f);
    password.set_widget_name("account-create-password");
    password.set_sensitive(false);
    let next = button("Weiteres Konto vorbereiten", f);
    next.set_sensitive(false);
    for b in [&create, &password, &next] {
        page.append(b);
    }
    let state = label("Noch kein Konto angelegt. Vorhandene sudo-Regeln bleiben unverändert.");
    state.set_widget_name("account-create-status");
    page.append(&state);
    let term = vte::Terminal::new();
    term.set_widget_name("account-create-terminal");
    term.set_hexpand(true);
    term.set_vexpand(true);
    term.set_scrollback_lines(1000);
    term.set_size(80, 8);
    term.set_input_enabled(false);
    page.append(&term);
    // Ephemeral UI state, not an alternate account/credential store.
    let current: Rc<RefCell<Option<CreatedAccount>>> = Rc::new(RefCell::new(None));
    let phase = Rc::new(Cell::new(0));
    let finish: Rc<dyn Fn(i32)> = {
        let (entry, state, start, pass, more, user, step, terminal) = (
            name.clone(),
            state.clone(),
            create.clone(),
            password.clone(),
            next.clone(),
            current.clone(),
            phase.clone(),
            term.downgrade(),
        );
        let (entry, state, start, pass, more) = (
            entry.downgrade(),
            state.downgrade(),
            start.downgrade(),
            pass.downgrade(),
            more.downgrade(),
        );
        Rc::new(move |code| {
            let (Some(entry), Some(state), Some(start), Some(pass), Some(more)) = (
                entry.upgrade(),
                state.upgrade(),
                start.upgrade(),
                pass.upgrade(),
                more.upgrade(),
            ) else {
                return;
            };
            if let Some(terminal) = terminal.upgrade() {
                terminal.set_input_enabled(false);
            }
            match (step.replace(0), code == 0) {
                (1, true) => {
                    let (user, pass, state, more, name) = (
                        user.clone(),
                        pass.clone(),
                        state.clone(),
                        more.clone(),
                        entry.text().to_string(),
                    );
                    state.set_text("Systemkonto und private Home-Rechte werden geprüft …");
                    glib::MainContext::default().spawn_local(async move {
                        match verify(&name).await {
                            Ok(account) => { *user.borrow_mut() = Some(account); pass.set_sensitive(true); state.set_text("Konto angelegt, Kennwort noch gesperrt. Jetzt ein Kennwort setzen; anschließend über die reguläre Anmeldung wechseln."); }
                            Err(error) => { more.set_sensitive(true); state.set_text(&error.to_string()); }
                        }
                    });
                }
                (1, false) => {
                    entry.set_sensitive(true);
                    start.set_sensitive(true);
                    state.set_text("Anlegen nicht erfolgreich. Systemmeldung prüfen; vorhandene Konten werden nicht übernommen. Ein möglicherweise teilweise angelegtes gesperrtes Konto muss ein Administrator über die Systemkonsole prüfen.");
                }
                (2, true) => {
                    more.set_sensitive(true);
                    state.set_text("Kennwort gesetzt. Das Konto kann sich über die reguläre PAM-Anmeldung anmelden. Persönliche Rampi-Daten entstehen beim ersten Start.");
                }
                (2, false) => {
                    pass.set_sensitive(true);
                    state.set_text("Kennwort nicht gesetzt. Systemmeldung prüfen und erneut versuchen. Ohne erfolgreiche Kennwortänderung bleibt das neue Konto gesperrt.");
                }
                _ => {}
            }
        })
    };
    let finished = finish.clone();
    term.connect_child_exited(move |_, code| finished(code));
    let (s, feedback, entry, status, terminal, start, step, finished) = (
        stack.clone(),
        f.clone(),
        name.clone(),
        state.clone(),
        term.clone(),
        create.clone(),
        phase.clone(),
        finish.clone(),
    );
    create.connect_clicked(move |_| {
        let username = entry.text().to_string();
        let args = match accounts::create(&username) { Ok(args) => args, Err(error) => { status.set_text(&error.to_string()); return; } };
        let (entry, state, terminal, start, step, finished) = (entry.clone(), status.clone(), terminal.clone(), start.clone(), step.clone(), finished.clone());
        crate::views::confirm(&s, "Neues Linux-Konto anlegen?", &format!("Konto {username} mit privatem Home-Verzeichnis anlegen. Das Kennwort bleibt zunächst gesperrt. Danach hier ein Kennwort setzen."), &feedback, move || {
            if !start.is_sensitive() { return; }
            start.set_sensitive(false); entry.set_sensitive(false); step.set(1);
            state.set_text("sudo prüft deine vorhandenen Rechte. Eingaben ausschließlich im eingebetteten Systemterminal.");
            spawn(&terminal, &args, &state, finished.clone());
        });
    });
    let (terminal, status, step, pass, user, finished) = (
        term,
        state.clone(),
        phase,
        password.clone(),
        current.clone(),
        finish,
    );
    password.connect_clicked(move |_| {
        if let Some(account) = user.borrow().clone() {
            pass.set_sensitive(false);
            let (pass, step, status, terminal, finished) = (pass.clone(), step.clone(), status.clone(), terminal.clone(), finished.clone());
            glib::MainContext::default().spawn_local(async move {
                match verify(&account.name).await {
                    Ok(current) if current == account => {
                        step.set(2); status.set_text("passwd fragt nach dem neuen Kennwort und dessen Bestätigung.");
                        spawn(&terminal, &accounts::password(&account.name).expect("Validated account name"), &status, finished);
                    }
                    _ => { pass.set_sensitive(true); status.set_text("Konto oder Home-Rechte haben sich verändert. Kennwortänderung abgewiesen; ein Administrator muss das Konto prüfen."); }
                }
            });
        }
    });
    let (entry, start, pass, user, status, more) =
        (name.clone(), create, password, current, state, next.clone());
    next.connect_clicked(move |_| {
        *user.borrow_mut() = None;
        entry.set_text("");
        entry.set_sensitive(true);
        start.set_sensitive(true);
        pass.set_sensitive(false);
        more.set_sensitive(false);
        status.set_text("Nächstes Konto vorbereiten. Zuvor angelegte Konten bleiben erhalten.");
        entry.grab_focus();
    });
    stack.add_named(&page, Some("account-create"));
    stack.set_visible_child_name("account-create");
    name.grab_focus();
}
