//! Inline hidden-network form; NetworkManager owns association and credentials.
use crate::widgets::*;
use gtk::{glib, prelude::*};
use rampi_core::i18n::text as tr;
use std::{cell::RefCell, rc::Rc};
pub fn append(page: &gtk::Box, status: &gtk::Label, f: &Feedback) {
    let expander = gtk::Expander::builder()
        .label(tr("wifi-hidden", &[]))
        .build();
    expander.set_widget_name("hidden-network-form");
    let form = column();
    expander.set_child(Some(&form));
    page.append(&expander);
    let refresh = button(&tr("wifi-adapters", &[]), f);
    form.append(&refresh);
    let choices = inline_choices(&[], f);
    choices.set_widget_name("hidden-adapter");
    form.append(&choices);
    let ssid = gtk::Entry::builder()
        .placeholder_text(tr("wifi-ssid", &[]))
        .build();
    ssid.set_widget_name("hidden-ssid");
    form.append(&ssid);
    let mode = inline_choices(
        &["WPA2 Personal", "WPA3 Personal", &tr("wifi-open", &[])],
        f,
    );
    mode.set_widget_name("hidden-security");
    form.append(&mode);
    let password = gtk::PasswordEntry::builder()
        .placeholder_text(tr("wifi-credential-placeholder", &[]))
        .build();
    password.set_widget_name("hidden-password");
    form.append(&password);
    let connect = button(&tr("wifi-hidden", &[]), f);
    form.append(&connect);
    form.append(&label(&tr("wifi-profile-policy", &[])));
    let devices = Rc::new(RefCell::new(Vec::<(String, String)>::new()));
    let (d, picker, stat) = (devices.clone(), choices.clone(), status.clone());
    refresh.connect_clicked(move |b| {
        b.set_sensitive(false);
        let (b, d, picker, stat) = (b.clone(), d.clone(), picker.clone(), stat.clone());
        glib::MainContext::default().spawn_local(async move {
            match crate::bus::wifi_devices().await {
                Ok(rows) => {
                    let names: Vec<_> = rows.iter().map(|(_, name)| name.as_str()).collect();
                    replace_choices(&picker, &names);
                    *d.borrow_mut() = rows;
                }
                Err(e) => stat.set_text(&e.to_string()),
            }
            b.set_sensitive(true);
        });
    });
    let stat = status.clone();
    connect.connect_clicked(move |b| {
        let Some((device, _)) = devices
            .borrow()
            .get(choice_index(&choices) as usize)
            .cloned()
        else {
            stat.set_text(&tr("wifi-select-adapter", &[]));
            return;
        };
        let security = match choice_index(&mode) {
            0 => "wpa-psk",
            1 => "sae",
            2 => "open",
            _ => return,
        };
        let (name, secret) = (ssid.text().to_string(), password.text().to_string());
        password.set_text("");
        b.set_sensitive(false);
        let (b, stat) = (b.clone(), stat.clone());
        glib::MainContext::default().spawn_local(async move {
            status_result(
                &stat,
                crate::bus::wifi_hidden(&device, &name, security, secret).await,
            );
            b.set_sensitive(true);
        });
    });
}
