use crate::{views, widgets::*, wireguard};
use gtk::{glib, prelude::*};
use std::{
    cell::{Cell, RefCell},
    rc::Rc,
};

pub fn build(stack: &gtk::Stack, feedback: &Feedback) -> gtk::Box {
    let page = column();
    page.append(&label("VPN · Tailscale und WireGuard\nVPN-Verbindungen ändern systemweite Routen. NetworkManager und die vorhandenen Dienste prüfen deine Rechte."));
    page.append(&label("WireGuard · persönliche Profile"));
    let status = label("");
    status.set_widget_name("vpn-status");
    page.append(&status);
    let refresh = button("VPN-Profile aktualisieren", feedback);
    page.append(&refresh);
    let list = gtk::ListBox::new();
    list.set_widget_name("vpn-profiles");
    list.set_selection_mode(gtk::SelectionMode::Single);
    page.append(&list);
    let profiles: Rc<RefCell<Vec<wireguard::Profile>>> = Rc::new(RefCell::new(vec![]));
    let busy = Rc::new(Cell::new(false));
    let (p, l, s) = (profiles.clone(), list.clone(), status.clone());
    refresh.connect_clicked(move |button| {
        if !button.is_sensitive() {
            return;
        }
        button.set_sensitive(false);
        let (p, l, s, button) = (p.clone(), l.clone(), s.clone(), button.clone());
        glib::MainContext::default().spawn_local(async move {
            match wireguard::profiles().await {
                Ok(rows) => {
                    if *p.borrow() != rows {
                        let selected = l.selected_row().and_then(|r| {
                            p.borrow().get(r.index() as usize).map(|p| p.uuid.clone())
                        });
                        while let Some(child) = l.first_child() {
                            l.remove(&child);
                        }
                        for profile in &rows {
                            let state = match profile.state {
                                1 => "Verbindung wird aufgebaut",
                                2 => "Verbunden",
                                3 => "Wird getrennt",
                                _ => "Getrennt",
                            };
                            l.append(&label(&format!("{} · {state}", profile.name)));
                        }
                        let selected = rows.iter().position(|p| Some(&p.uuid) == selected.as_ref());
                        if let Some(index) = selected {
                            l.select_row(l.row_at_index(index as i32).as_ref());
                        }
                        *p.borrow_mut() = rows;
                    }
                    if p.borrow().is_empty() {
                        s.set_text("Noch keine persönlichen WireGuard-Profile vorhanden.");
                    }
                }
                Err(error) => s.set_text(&error.to_string()),
            }
            button.set_sensitive(true);
        });
    });
    let actions = row();
    for (title, connect) in [("WireGuard verbinden", true), ("WireGuard trennen", false)] {
        let action = button(title, feedback);
        let (p, l, s, busy, refresh) = (
            profiles.clone(),
            list.clone(),
            status.clone(),
            busy.clone(),
            refresh.clone(),
        );
        action.connect_clicked(move |_| {
            if busy.get() {
                return;
            }
            let selected = l
                .selected_row()
                .and_then(|r| p.borrow().get(r.index() as usize).cloned());
            let Some(selected) = selected else {
                s.set_text("Bitte ein persönliches Profil auswählen.");
                return;
            };
            busy.set(true);
            let (busy, s, refresh) = (busy.clone(), s.clone(), refresh.clone());
            glib::MainContext::default().spawn_local(async move {
                status_result(&s, wireguard::change(&selected.uuid, connect).await);
                busy.set(false);
                if refresh.is_sensitive() {
                    refresh.emit_clicked();
                }
            });
        });
        actions.append(&action);
    }
    page.append(&actions);
    let filename = gtk::Entry::builder()
        .placeholder_text("Pfad zur persönlichen WireGuard-Datei (.conf)")
        .hexpand(true)
        .build();
    filename.set_widget_name("vpn-import-path");
    page.append(&filename);
    let import = button("WireGuard-Profil importieren", feedback);
    let (s, busy, refresh_import) = (status.clone(), busy.clone(), refresh.clone());
    import.connect_clicked(move |_| {
        if busy.get() { return; }
        let path = match rampi_core::config::expand_home(&filename.text()) {
            Ok(path) => path,
            Err(error) => { s.set_text(&error.to_string()); return; },
        };
        busy.set(true);
        let (s, busy, refresh) = (s.clone(), busy.clone(), refresh_import.clone());
        glib::MainContext::default().spawn_local(async move {
            match wireguard::import(path).await {
                Ok(()) => s.set_text("Persönliches Profil importiert. Autostart ist aus; zum Verbinden das Profil auswählen."),
                Err(error) => s.set_text(&error.to_string()),
            }
            busy.set(false);
            if refresh.is_sensitive() { refresh.emit_clicked(); }
        });
    });
    page.append(&import);
    page.append(&label("Gemeinsame Profile und Profile anderer Benutzer werden hier nicht angeboten. Ein Import verbindet den Tunnel nicht automatisch."));
    page.append(&label("Tailscale · vorhandene offizielle Software"));
    let tailscale = row();
    for (title, key, args) in [
        (
            "Tailscale-Status",
            "tailscale-status",
            vec!["tailscale", "status"],
        ),
        (
            "Tailscale verbinden",
            "tailscale-up",
            vec!["pkexec", "tailscale", "up"],
        ),
        (
            "Tailscale trennen",
            "tailscale-down",
            vec!["pkexec", "tailscale", "down"],
        ),
    ] {
        let action = button(title, feedback);
        let (route, s) = (stack.clone(), status.clone());
        action.connect_clicked(move |_| {
            views::terminal(&route, key, args.iter().map(Into::into).collect(), &s)
        });
        tailscale.append(&action);
    }
    page.append(&tailscale);
    let refresh_on_map = refresh.downgrade();
    page.connect_map(move |_| {
        if let Some(r) = refresh_on_map.upgrade() {
            r.emit_clicked();
        }
    });
    let (weak_page, weak_refresh) = (page.downgrade(), refresh.downgrade());
    glib::timeout_add_seconds_local(3, move || {
        let (Some(page), Some(refresh)) = (weak_page.upgrade(), weak_refresh.upgrade()) else {
            return glib::ControlFlow::Break;
        };
        if page.is_mapped() && refresh.is_sensitive() {
            refresh.emit_clicked();
        }
        glib::ControlFlow::Continue
    });
    page
}
