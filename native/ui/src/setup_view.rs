//! Resumable first-run navigation reusing the same settings and service adapters.
use crate::widgets::*;
use gtk::{glib, prelude::*};
use rampi_core::config;
use rampi_core::i18n::text as tr;
use std::{cell::Cell, rc::Rc};

const STEPS: [(&str, &str, &str); config::SETUP_STEP_IDS.len()] = [
    (
        "setup-language-title",
        "setup-language-description",
        "system",
    ),
    ("setup-display-title", "setup-display-description", "system"),
    ("category-wifi", "setup-wifi-description", "wifi"),
    (
        "category-bluetooth",
        "setup-bluetooth-description",
        "bluetooth",
    ),
    ("setup-account-title", "setup-account-description", "system"),
    ("category-vpn", "setup-vpn-description", "vpn"),
    ("setup-host-title", "setup-host-description", "host"),
    ("setup-ssh-title", "setup-ssh-description", "host"),
    ("setup-stream-title", "setup-stream-description", "remote"),
    ("module-remote", "setup-rdp-description", "remote"),
    ("category-board", "setup-board-description", "board"),
    (
        "setup-finish-title",
        "setup-finish-description",
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
    let previous = button(&tr("setup-previous", &[]), f);
    let open = button(&tr("setup-open", &[]), f);
    let next = button(&tr("setup-next", &[]), f);
    let later = button(&tr("setup-later", &[]), f);
    let finish = button(&tr("setup-finish", &[]), f);
    for b in [&previous, &open, &next, &later, &finish] {
        actions.append(b);
    }
    page.append(&actions);
    let current = Rc::new(Cell::new(conf.borrow().setup_index()));
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
            title.set_text(&tr(
                "setup-progress",
                &[
                    ("step", &(i + 1).to_string()),
                    ("total", &STEPS.len().to_string()),
                    ("title", &tr(STEPS[i].0, &[])),
                ],
            ));
            description.set_text(&tr(STEPS[i].1, &[]));
            progress.set_fraction((i + 1) as f64 / STEPS.len() as f64);
            previous.set_sensitive(i > 0);
            next.set_sensitive(i + 1 < STEPS.len());
            finish.set_visible(i + 1 == STEPS.len());
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
            let target = i
                .get()
                .saturating_add_signed(direction)
                .min(STEPS.len() - 1);
            let mut candidate = c.borrow().clone();
            candidate.setup_step = config::SETUP_STEP_IDS[target];
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
            for command in ["ssh", "ssh-keygen", "moonlight", "tailscale", "labwc"] {
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
