//! Per-provider pages using the existing Windows adapter and native SSH/VTE.
use crate::widgets::*;
use gtk::{glib, prelude::*};
use rampi_core::{config::Host, launch};

async fn control(host: &Host, module: &str, action: &str) -> anyhow::Result<Vec<u8>> {
    let args = launch::ssh_action(host, module, action)?;
    let (success, output) = crate::process::output("ssh", &args[1..], 25, 16384).await?;
    anyhow::ensure!(
        success,
        "Windows-Prüfung fehlgeschlagen. SSH-Schlüssel, bestätigten Hostfingerabdruck und installiertes Rampi-Hostpaket prüfen."
    );
    Ok(output)
}

pub fn open(stack: &gtk::Stack, conf: &Shared, module: &str, status: &gtk::Label, f: &Feedback) {
    let (title, program, website) = match module {
        "codex" => (
            "ChatGPT / Codex",
            "codex",
            "https://developers.openai.com/codex/cli/",
        ),
        "claude" => (
            "Claude Code",
            "claude",
            "https://code.claude.com/docs/en/setup",
        ),
        "antigravity" => (
            "Gemini / Antigravity",
            "agy",
            "https://antigravity.google/docs/cli/install/",
        ),
        _ => return,
    };
    let key = format!("ai-{module}");
    if let Some(old) = stack.child_by_name(&key) {
        stack.remove(&old);
    }
    let page = column();
    let heading = label(title);
    heading.add_css_class("heading");
    page.append(&heading);
    let from_setup = stack
        .child_by_name("setup")
        .is_some_and(|p| p.widget_name() == "setup-return");
    let back = button(
        if from_setup {
            "← Einrichtung"
        } else {
            "← Dashboard"
        },
        f,
    );
    back.set_widget_name("rampi-back");
    let route = stack.clone();
    back.connect_clicked(move |_| {
        route.set_visible_child_name(if from_setup { "setup" } else { "dashboard" })
    });
    page.append(&back);
    let target = match conf.borrow().host() {
        Ok(host) => format!("{} · {}@{} · Projekt: {}", host.name, host.username, host.address,
            if host.project.is_empty() { "Windows-Standardverzeichnis" } else { &host.project }),
        Err(_) => "Noch kein Windows-Host eingerichtet. Unter Einstellungen → Windows-Host ein persönliches Profil speichern und aktivieren.".into(),
    };
    page.append(&label(&target));
    page.append(&label(&format!(
        "1 · Host prüfen  →  2 · Offizielle CLI einrichten  →  3 · Sitzung öffnen\nAuf Windows {program} installieren und im offiziellen Programm anmelden. Projektsicherheit und Berechtigungen bleiben beim Anbieter.\nEin Verbindungsabbruch oder Modulwechsel beendet die Windows-Sitzung nicht."
    )));
    let output = label("Noch nicht geprüft. Erreichbarkeit bestätigt keine Anbieteranmeldung.");
    output.set_widget_name("ai-session-status");
    page.append(&output);
    let check = button("Host und Sitzung prüfen", f);
    check.set_widget_name("ai-check");
    let (c, state, module_id) = (conf.clone(), output.clone(), module.to_string());
    check.connect_clicked(move |button| {
        let host = match c.borrow().host().cloned() {
            Ok(host) => host,
            Err(error) => { state.set_text(&error.to_string()); return; }
        };
        button.set_sensitive(false);
        state.set_text("Persönliches Windows-Konto wird über OpenSSH geprüft …");
        let (state, button, module_id) = (state.clone(), button.clone(), module_id.clone());
        glib::MainContext::default().spawn_local(async move {
            let result: anyhow::Result<String> = async {
                let bytes = control(&host, &module_id, "Check").await?;
                let report: serde_json::Value = serde_json::from_slice(&bytes)?;
                anyhow::ensure!(report["schema"] == 1 && report["module"] == module_id, "Unbekannte Hostantwort; Hostpaket aktualisieren.");
                let installed = report["installed"].as_bool().ok_or_else(|| anyhow::anyhow!("Ungültige CLI-Prüfung"))?;
                let mux = report["multiplexer"].as_bool().ok_or_else(|| anyhow::anyhow!("Ungültige Persistenzprüfung"))?;
                let running = report["running"].as_bool().ok_or_else(|| anyhow::anyhow!("Ungültige Sitzungsprüfung"))?;
                Ok(format!("{}@{}\nCLI: {} · psmux: {} · Sitzung: {}\nAnbieteranmeldung bleibt ungeprüft; im offiziellen Terminal abschließen.",
                    host.username, host.address,
                    if installed { "vorhanden" } else { "fehlt" },
                    if mux { "vorhanden" } else { "fehlt" },
                    if running { "läuft auf Windows" } else { "nicht gestartet" }))
            }.await;
            state.set_text(&result.unwrap_or_else(|error| error.to_string()));
            button.set_sensitive(true);
        });
    });
    page.append(&check);
    let help = button("Offizielle Einrichtung anzeigen", f);
    let (s, c, stat, feedback) = (stack.clone(), conf.clone(), status.clone(), f.clone());
    help.connect_clicked(move |_| {
        // The shared WebKit browser stays in the same application window.
        crate::views::browser_at(&s, &c, &stat, &feedback, website);
    });
    page.append(&help);
    let attach = button("Sitzung öffnen / wiederverbinden", f);
    attach.set_widget_name("ai-attach");
    let (s, c, stat, module_id) = (
        stack.clone(),
        conf.clone(),
        status.clone(),
        module.to_string(),
    );
    attach.connect_clicked(move |_| {
        let args = c.borrow().host().and_then(|host| {
            Ok((
                launch::ssh(host, &module_id)?,
                format!("{module_id}-{}", launch::streaming_identity(host)?),
            ))
        });
        match args {
            Ok((args, key)) => crate::views::terminal(&s, &key, args, &stat),
            Err(error) => stat.set_text(&error.to_string()),
        }
    });
    page.append(&attach);
    let stop = button("Windows-Sitzung beenden …", f);
    stop.set_widget_name("ai-stop");
    let (s, c, state, feedback, module_id) = (
        stack.clone(),
        conf.clone(),
        output.clone(),
        f.clone(),
        module.to_string(),
    );
    stop.connect_clicked(move |_| {
        let host = match c.borrow().host().cloned() {
            Ok(host) => host,
            Err(error) => { state.set_text(&error.to_string()); return; }
        };
        let (state, module_id, route) = (state.clone(), module_id.clone(), s.clone());
        crate::views::confirm(&s, "Windows-Sitzung beenden?", &format!("{} · {}@{}\nDer laufende CLI-Prozess dieser Sitzung wird beendet. Andere Sitzungen bleiben erhalten. Für ein anderes Projekt anschließend neu öffnen.", title, host.username, host.address), &feedback, move || {
            let (state, module_id, route, host) = (state.clone(), module_id.clone(), route.clone(), host.clone());
            glib::MainContext::default().spawn_local(async move {
                match control(&host, &module_id, "Stop").await {
                    Ok(_) => {
                        if let Ok(identity) = launch::streaming_identity(&host)
                            && let Some(terminal) = route.child_by_name(&format!("terminal-{module_id}-{identity}")) { route.remove(&terminal); }
                        state.set_text("Windows-Sitzung beendet. Beim nächsten Öffnen wird eine neue Sitzung erstellt.");
                    }
                    Err(error) => state.set_text(&error.to_string()),
                }
            });
        });
    });
    page.append(&stop);
    let scroll = gtk::ScrolledWindow::builder()
        .hscrollbar_policy(gtk::PolicyType::Never)
        .child(&page)
        .build();
    stack.add_named(&scroll, Some(&key));
    stack.set_visible_child_name(&key);
    back.grab_focus();
}
