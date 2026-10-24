use crate::widgets::*;
use gtk::{glib, prelude::*};
use std::{cell::RefCell, rc::Rc};
use vte::prelude::*;

pub fn build(
    stack: &gtk::Stack,
    conf: &Shared,
    status: &gtk::Label,
    field: &gtk::Entry,
    f: &Feedback,
) -> gtk::Box {
    let page = column();
    page.append(&label("Persönlicher SSH-Zugang · OpenSSH"));
    let generate = button("Persönlichen SSH-Schlüssel erstellen", f);
    let adopt = button("Rampi-Schlüssel in Formular übernehmen", f);
    let public = button("Öffentlichen Rampi-Schlüssel anzeigen", f);
    let scan = button("Hostschlüssel des aktiven Profils prüfen", f);
    let unlock = button("Aktiven SSH-Schlüssel entsperren", f);
    let output = label("");
    output.set_selectable(true);
    for b in [&generate, &adopt, &public, &unlock, &scan] {
        page.append(b);
    }
    page.append(&output);
    page.append(&label("Nach dem Speichern des Hostprofils den aktiven Schlüssel einmal entsperren. Die Passphrase bleibt im offiziellen OpenSSH-Terminal; der persönliche Agent hält den Schlüssel für diese Anmeldung bereit."));
    let (s, c, stat) = (stack.clone(), conf.clone(), status.clone());
    let unlocking = Rc::new(RefCell::new(None::<String>));
    unlock.connect_clicked(move |button| {
        if let Some(key) = unlocking.borrow().as_ref() {
            s.set_visible_child_name(key);
            return;
        }
        let identity = c.borrow().host().map(|h| h.identity.clone());
        let args = identity.and_then(|identity| crate::ssh_setup::unlock_arguments(&identity));
        match args {
            Ok(args) => {
                let name = format!("ssh-unlock-{}", glib::monotonic_time());
                crate::views::terminal(&s, &name, args, &stat);
                let key = format!("terminal-{name}");
                if let Some(term) = s.child_by_name(&key).and_then(|w| w.downcast::<vte::Terminal>().ok()) {
                    *unlocking.borrow_mut() = Some(key);
                    button.set_label("SSH-Entsperren fortsetzen");
                    let (state, button, stat) = (unlocking.clone(), button.downgrade(), stat.clone());
                    term.connect_child_exited(move |_, code| {
                        state.borrow_mut().take();
                        if let Some(button) = button.upgrade() { button.set_label("Aktiven SSH-Schlüssel entsperren"); }
                        stat.set_text(if code == 0 { "SSH-Schlüssel im persönlichen OpenSSH-Agent entsperrt." } else { "SSH-Schlüssel konnte nicht entsperrt werden. Ergebnis im Terminal prüfen." });
                    });
                }
            }
            Err(e) => stat.set_text(&e.to_string()),
        }
    });
    page.append(&label("Die Schlüsselerstellung läuft innerhalb von Rampi im offiziellen OpenSSH-Terminal. Wähle dort eine Passphrase. Vorhandene Schlüssel werden nicht überschrieben. Übertrage ausschließlich den öffentlichen Schlüssel in dein persönliches Windows-Konto."));
    let (s, stat) = (stack.clone(), status.clone());
    let running = Rc::new(RefCell::new(None::<String>));
    generate.connect_clicked(move |button| {
        if let Some(key) = running.borrow().as_ref() {
            s.set_visible_child_name(key);
            return;
        }
        match crate::ssh_setup::generate_arguments() {
            Ok(args) => {
                let name = format!("keygen-{}", glib::monotonic_time());
                crate::views::terminal(&s, &name, args, &stat);
                let key = format!("terminal-{name}");
                if let Some(term) = s
                    .child_by_name(&key)
                    .and_then(|w| w.downcast::<vte::Terminal>().ok())
                {
                    *running.borrow_mut() = Some(key);
                    button.set_label("Schlüsselerstellung fortsetzen");
                    let (state, button) = (running.clone(), button.clone());
                    term.connect_child_exited(move |_, _| {
                        state.borrow_mut().take();
                        button.set_label("Persönlichen SSH-Schlüssel erstellen");
                    });
                }
            }
            Err(e) => stat.set_text(&e.to_string()),
        }
    });
    let (field, stat) = (field.clone(), status.clone());
    adopt.connect_clicked(move |_| {
        let result = crate::ssh_setup::key_path().and_then(|path| {
            anyhow::ensure!(path.is_file(), "Zuerst einen Schlüssel erstellen");
            field.set_text(&path.to_string_lossy());
            Ok(())
        });
        status_result(&stat, result);
    });
    let stat = status.clone();
    public.connect_clicked(move |_| {
        let result = crate::ssh_setup::key_path().and_then(|p| {
            use std::io::Read;
            let mut value = String::new();
            std::fs::File::open(p.with_extension("pub"))?
                .take(16385)
                .read_to_string(&mut value)?;
            anyhow::ensure!(
                value.len() <= 16384 && value.starts_with("ssh-ed25519 "),
                "Ungültige öffentliche Schlüsseldatei"
            );
            output.set_text(value.trim());
            Ok(())
        });
        status_result(&stat, result);
    });
    let (s, c, stat, feed) = (stack.clone(), conf.clone(), status.clone(), f.clone());
    let source_page = page.downgrade();
    scan.connect_clicked(move |button| {
        let host = match c.borrow().host() {
            Ok(h) => h.clone(),
            Err(e) => {
                stat.set_text(&e.to_string());
                return;
            }
        };
        button.set_sensitive(false);
        let (s, stat, f, button, page, current) = (
            s.clone(),
            stat.clone(),
            feed.clone(),
            button.clone(),
            source_page.clone(),
            c.clone(),
        );
        glib::MainContext::default().spawn_local(async move {
            match crate::ssh_setup::scan(host).await {
                Ok(scanned) => {
                    let same = current.borrow().host().is_ok_and(|h| {
                        h.address == scanned.host.address
                            && h.port == scanned.host.port
                            && h.username == scanned.host.username
                    });
                    if same && page.upgrade().is_some_and(|p| p.is_mapped()) {
                        confirmation(&s, scanned, &stat, &f);
                    }
                }
                Err(e) => stat.set_text(&e.to_string()),
            }
            button.set_sensitive(true);
        });
    });
    page
}

fn confirmation(
    stack: &gtk::Stack,
    scanned: crate::ssh_setup::Scanned,
    status: &gtk::Label,
    f: &Feedback,
) {
    if let Some(previous) = stack.child_by_name("ssh-trust") {
        stack.remove(&previous);
    }
    let page = column();
    page.append(&label(&format!(
        "Hostidentität prüfen · {}:{}",
        scanned.host.address, scanned.host.port
    )));
    let fingerprint = label(&scanned.fingerprint);
    fingerprint.set_selectable(true);
    fingerprint.set_widget_name("ssh-fingerprint");
    page.append(&fingerprint);
    page.append(&label("Ein empfangener Schlüssel ist noch kein Identitätsnachweis. Lies den SHA256-Fingerabdruck direkt am Windows-Host oder aus einem anderen vertrauenswürdigen Kanal ab. Auf Windows zeigt ssh-keygen -l -E sha256 -f C:\\ProgramData\\ssh\\ssh_host_ed25519_key.pub den Hostfingerabdruck. Gib genau diesen unabhängig geprüften Wert ein."));
    let expected = gtk::Entry::builder()
        .placeholder_text("Unabhängig geprüfter SHA256-Fingerabdruck")
        .build();
    expected.set_widget_name("ssh-expected");
    page.append(&expected);
    let no = button("Abbrechen", f);
    no.set_widget_name("rampi-back");
    let yes = button("Geprüften Hostschlüssel übernehmen", f);
    page.append(&no);
    page.append(&yes);
    let pending = Rc::new(RefCell::new(Some(scanned)));
    let (s, p) = (stack.clone(), pending.clone());
    no.connect_clicked(move |_| {
        p.borrow_mut().take();
        s.set_visible_child_name("settings");
    });
    let (s, stat) = (stack.clone(), status.clone());
    yes.connect_clicked(move |button| {
        let Some(scan) = pending.borrow_mut().take() else {
            return;
        };
        button.set_sensitive(false);
        let (s, stat, button, p, value) = (
            s.clone(),
            stat.clone(),
            button.clone(),
            pending.clone(),
            expected.text().to_string(),
        );
        glib::MainContext::default().spawn_local(async move {
            match crate::ssh_setup::accept(&scan, &value).await {
                Ok(()) => {
                    stat.set_text(
                        "Geprüfter Hostschlüssel in der persönlichen OpenSSH-Datei gespeichert.",
                    );
                    if s.visible_child_name().as_deref() == Some("ssh-trust") {
                        s.set_visible_child_name("settings");
                    }
                }
                Err(e) => {
                    stat.set_text(&e.to_string());
                    *p.borrow_mut() = Some(scan);
                }
            }
            button.set_sensitive(true);
        });
    });
    stack.add_named(&page, Some("ssh-trust"));
    stack.set_visible_child_name("ssh-trust");
    no.grab_focus();
}
