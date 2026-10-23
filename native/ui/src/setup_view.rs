//! Resumable first-run navigation reusing the same settings and service adapters.
use crate::widgets::*;
use gtk::{glib, prelude::*};
use rampi_core::config;
use std::{cell::Cell, rc::Rc};

const STEPS: [(&str, &str, &str); 15] = [
    (
        "Sprache und Tastatur",
        "Die Oberfläche ist derzeit deutsch. Unter System die persönliche Tastaturbelegung auswählen, anwenden und direkt im Testfeld prüfen.",
        "system",
    ),
    (
        "Bildschirm",
        "Unter System die vom Bildschirm angebotene Auflösung auswählen. Jede Änderung muss innerhalb von 15 Sekunden bestätigt werden, sonst wird sie zurückgesetzt. Änderungen gelten bis zur Abmeldung.",
        "system",
    ),
    (
        "WLAN",
        "Netze suchen, auswählen und verbinden. Vorhandene NetworkManager-Profile bleiben erhalten.",
        "wifi",
    ),
    (
        "Bluetooth",
        "Tastatur und Maus suchen und koppeln. Die Bestätigung erscheint innerhalb von Rampi.",
        "bluetooth",
    ),
    (
        "Linux-Konto",
        "Dein vorhandenes Linux-Konto und die PAM-Anmeldung bestimmen deine Rechte. Unter System kannst du dein Kennwort im eingebetteten Systemterminal ändern und dich abmelden. Die Verwaltung weiterer Konten ist noch nicht portiert.",
        "system",
    ),
    (
        "VPN",
        "VPN wählen: Tailscale innerhalb der Seite verbinden und bei Bedarf beim Anbieter anmelden, oder ein persönliches WireGuard-Profil importieren und verbinden. Die Statusanzeige zeigt den tatsächlichen Dienstzustand; Routen gelten systemweit.",
        "vpn",
    ),
    (
        "Windows-Host",
        "Persönliche Hosts anlegen und den aktiven Windows-11-Pro-Host auswählen. Windows benötigt das Rampi-Hostpaket.",
        "host",
    ),
    (
        "SSH-Schlüssel",
        "Einen persönlichen Schlüssel mit OpenSSH innerhalb von Rampi erstellen oder einen bestehenden Schlüssel verwenden. Den Hostfingerabdruck unabhängig am Windows-Host prüfen und erst danach in Rampi übernehmen. Ausschließlich den öffentlichen Schlüssel zum Windows-Konto übertragen.",
        "host",
    ),
    (
        "Codex",
        "Die offizielle Windows-CLI muss unter deinem Windows-Konto installiert und angemeldet sein. Nach der Einrichtung öffnest du das Codex-Modul; eine automatische Anbieterprüfung fehlt noch.",
        "host",
    ),
    (
        "Claude Code",
        "Die offizielle Windows-CLI muss unter deinem Windows-Konto installiert und angemeldet sein. Das Modul verwendet die bestehende persistente Hostintegration.",
        "host",
    ),
    (
        "Antigravity",
        "Nur eine tatsächlich unterstützte offizielle CLI verwenden. Eine verfügbare native Antigravity-CLI und deren Anmeldung sind hier nicht nachgewiesen.",
        "host",
    ),
    (
        "Desktop-Streaming",
        "Sunshine auf Windows und einen kompatiblen Moonlight-Client einrichten. Kopplung und Streaming erreichst du anschließend im Remote-Modul.",
        "remote",
    ),
    (
        "Remote Desktop",
        "Windows 11 Pro muss Remote Desktop erlauben. Host und Windows-Benutzer werden aus dem aktiven Profil übernommen.",
        "remote",
    ),
    (
        "Kanban und Browser",
        "Aufgabenquelle wählen: lokale Datei, GitHub, Gitea, Trello, Jira, Asana oder Notion. Die drei Schritte führen durch Quelle, persönlichen Zugang und Verbindungsprüfung. Danach das Board direkt öffnen.",
        "board",
    ),
    (
        "Abschluss",
        "Du kannst jeden Schritt überspringen und die Einrichtung später fortsetzen. Abschließen bestätigt nur deinen Einrichtungsdurchlauf, keine Verbindung oder Kompatibilität.",
        "diagnostics",
    ),
];

pub fn build(
    stack: &gtk::Stack,
    tabs: &gtk::Stack,
    conf: &Shared,
    status: &gtk::Label,
    f: &Feedback,
) -> gtk::Box {
    let page = column();
    let title = label("");
    title.add_css_class("heading");
    title.set_widget_name("setup-title");
    let description = label("");
    page.append(&title);
    page.append(&description);
    let progress = gtk::ProgressBar::new();
    page.append(&progress);
    let actions = column();
    let previous = button("Vorheriger Schritt", f);
    let open = button("Jetzt einrichten", f);
    let next = button("Weiter / Schritt überspringen", f);
    let later = button("Später fortsetzen", f);
    let finish = button("Einrichtung abschließen", f);
    for b in [&previous, &open, &next, &later, &finish] {
        actions.append(b);
    }
    page.append(&actions);
    let current = Rc::new(Cell::new(conf.borrow().setup_step));
    let render: Rc<dyn Fn()> = {
        let (current, title, description, progress, previous, next, finish) = (
            current.clone(),
            title,
            description,
            progress,
            previous.clone(),
            next.clone(),
            finish.clone(),
        );
        Rc::new(move || {
            let i = current.get();
            title.set_text(&format!("Einrichtung · {} / 15 · {}", i + 1, STEPS[i].0));
            description.set_text(STEPS[i].1);
            progress.set_fraction((i + 1) as f64 / 15.0);
            previous.set_sensitive(i > 0);
            next.set_sensitive(i < 14);
            finish.set_visible(i == 14);
        })
    };
    render();
    for (b, direction) in [(&previous, -1isize), (&next, 1)] {
        let (c, i, r, stat) = (
            conf.clone(),
            current.clone(),
            render.clone(),
            status.clone(),
        );
        b.connect_clicked(move |_| {
            let target = i.get().saturating_add_signed(direction).min(14);
            let mut candidate = c.borrow().clone();
            candidate.setup_step = target;
            let result =
                config::config_dir().and_then(|p| candidate.save(&p.join("settings.json")));
            if result.is_ok() {
                *c.borrow_mut() = candidate;
                i.set(target);
                r();
            }
            status_result(&stat, result);
        });
    }
    let (s, t, p, i) = (stack.clone(), tabs.clone(), page.clone(), current);
    open.connect_clicked(move |_| {
        p.set_widget_name("setup-return");
        match STEPS[i.get()].2 {
            "remote" => s.set_visible_child_name("remote"),
            "diagnostics" => s.set_visible_child_name("diagnostics"),
            tab => {
                t.set_visible_child_name(tab);
                s.set_visible_child_name("settings");
            }
        }
    });
    let (s, p) = (stack.clone(), page.clone());
    later.connect_clicked(move |_| {
        p.set_widget_name("setup");
        s.set_visible_child_name("dashboard");
    });
    let (s, p, c, stat) = (stack.clone(), page.clone(), conf.clone(), status.clone());
    finish.connect_clicked(move |_| {
        let mut candidate = c.borrow().clone();
        candidate.setup_complete = true;
        let result = config::config_dir().and_then(|p| candidate.save(&p.join("settings.json")));
        if result.is_ok() {
            *c.borrow_mut() = candidate;
            p.set_widget_name("setup");
            s.set_visible_child_name("dashboard");
        }
        status_result(&stat, result);
    });
    page
}

pub fn diagnostics(stack: &gtk::Stack, conf: &Shared, f: &Feedback) -> gtk::Box {
    let page = column();
    page.append(&label(
        "Lokale Diagnose · keine Zugangsdaten und keine Netzwerkänderungen",
    ));
    let back = button("← Zurück", f);
    back.set_widget_name("rampi-back");
    let s = stack.clone();
    back.connect_clicked(move |_| {
        s.set_visible_child_name(
            if s.child_by_name("setup")
                .is_some_and(|p| p.widget_name() == "setup-return")
            {
                "setup"
            } else {
                "settings"
            },
        );
    });
    page.append(&back);
    let result = label("");
    result.set_selectable(true);
    result.set_widget_name("diagnostics-result");
    page.append(&result);
    let check = button("Diagnose aktualisieren", f);
    page.append(&check);
    let c = conf.clone();
    check.connect_clicked(move |button| {
        button.set_sensitive(false);
        let (b, output, c) = (button.clone(), result.clone(), c.clone());
        glib::MainContext::default().spawn_local(async move {
            let mut lines = vec![format!("Rampi {} · Rust / Wayland", env!("CARGO_PKG_VERSION")), format!("Linux-Konto: {}", glib::user_name().to_string_lossy()), format!("Hostprofile: {} · aktiv: {}", c.borrow().hosts.len(), c.borrow().hosts.get(c.borrow().active_host).map(|h| h.name.as_str()).unwrap_or("keines"))];
            for command in ["ssh", "ssh-keygen", "wlfreerdp3", "moonlight", "tailscale", "labwc"] {
                lines.push(format!("{command}: {}", if glib::find_program_in_path(command).is_some() { "vorhanden (Funktion nicht geprüft)" } else { "nicht gefunden" }));
            }
            match crate::bus::system().await {
                Ok(connection) => {
                    for service in ["org.freedesktop.NetworkManager", "org.bluez"] {
                        use glib::variant::ToVariant;
                        let owner = crate::bus::call(&connection, "org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus", "NameHasOwner", Some(&(service,).to_variant())).await;
                        let available = owner.ok().and_then(|v| v.child_value(0).get::<bool>()).unwrap_or(false);
                        lines.push(format!("{service}: {}", if available { "Dienst erreichbar" } else { "nicht erreichbar" }));
                    }
                }
                Err(_) => lines.push("System-D-Bus nicht erreichbar".into()),
            }
            lines.push("Keine Prüfung von HDMI/GPU, Funkverbindung, Windows-Anmeldung oder Anbieterzugang durch diese Diagnose.".into());
            output.set_text(&lines.join("\n")); b.set_sensitive(true);
        });
    });
    page
}
