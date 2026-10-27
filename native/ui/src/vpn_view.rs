use crate::{widgets::*, wireguard};
use gtk::{glib, prelude::*};
use rampi_core::i18n::text as tr;
use std::{
    cell::{Cell, RefCell},
    rc::Rc,
};

pub fn build(stack: &gtk::Stack, feedback: &Feedback) -> gtk::Box {
    let page = column();
    page.append(&label(&tr("vpn-description", &[])));
    page.append(&label(&tr("wireguard-heading", &[])));
    let status = label("");
    status.set_widget_name("vpn-status");
    page.append(&status);
    let refresh = button(&tr("vpn-refresh", &[]), feedback);
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
                                1 => tr("vpn-connecting", &[]),
                                2 => tr("vpn-connected", &[]),
                                3 => tr("vpn-disconnecting", &[]),
                                _ => tr("vpn-disconnected", &[]),
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
                        s.set_text(&tr("wireguard-empty", &[]));
                    }
                }
                Err(error) => s.set_text(&error.to_string()),
            }
            button.set_sensitive(true);
        });
    });
    let actions = row();
    for (title, connect) in [
        (&tr("wireguard-connect", &[]), true),
        (&tr("wireguard-disconnect", &[]), false),
    ] {
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
                s.set_text(&tr("wireguard-select", &[]));
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
        .placeholder_text(tr("wireguard-path", &[]))
        .hexpand(true)
        .build();
    filename.set_widget_name("vpn-import-path");
    page.append(&filename);
    let import = button(&tr("wireguard-import", &[]), feedback);
    let (s, busy, refresh_import) = (status.clone(), busy.clone(), refresh.clone());
    import.connect_clicked(move |_| {
        if busy.get() {
            return;
        }
        let path = match rampi_core::config::expand_home(&filename.text()) {
            Ok(path) => path,
            Err(error) => {
                s.set_text(&error.to_string());
                return;
            }
        };
        busy.set(true);
        let (s, busy, refresh) = (s.clone(), busy.clone(), refresh_import.clone());
        glib::MainContext::default().spawn_local(async move {
            match wireguard::import(path).await {
                Ok(()) => s.set_text(&tr("wireguard-imported", &[])),
                Err(error) => s.set_text(&error.to_string()),
            }
            busy.set(false);
            if refresh.is_sensitive() {
                refresh.emit_clicked();
            }
        });
    });
    page.append(&import);
    page.append(&label(&tr("wireguard-private", &[])));
    page.append(&label(&tr("tailscale-heading", &[])));
    page.append(&crate::tailscale::view(feedback));
    page.append(&crate::tailscale::actions(stack, &status, feedback));
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
