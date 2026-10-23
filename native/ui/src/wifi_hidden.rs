//! Inline hidden-network form; NetworkManager owns association and credentials.
use crate::widgets::*;
use gtk::{glib, prelude::*};
use std::{cell::RefCell, rc::Rc};
pub fn append(page: &gtk::Box, status: &gtk::Label, f: &Feedback) {
    let expander = gtk::Expander::builder()
        .label("Verstecktes WLAN verbinden")
        .build();
    let form = column();
    expander.set_child(Some(&form));
    page.append(&expander);
    let refresh = button("WLAN-Adapter anzeigen", f);
    form.append(&refresh);
    let choices = gtk::DropDown::from_strings(&[]);
    choices.set_widget_name("hidden-adapter");
    form.append(&choices);
    let ssid = gtk::Entry::builder()
        .placeholder_text("Exakter Netzwerkname (SSID)")
        .build();
    ssid.set_widget_name("hidden-ssid");
    form.append(&ssid);
    let mode = gtk::DropDown::from_strings(&["WPA2 Personal", "WPA3 Personal", "Offenes Netz"]);
    mode.set_widget_name("hidden-security");
    form.append(&mode);
    let password = gtk::PasswordEntry::builder()
        .placeholder_text("WLAN-Kennwort")
        .build();
    password.set_widget_name("hidden-password");
    form.append(&password);
    let connect = button("Verstecktes WLAN verbinden", f);
    form.append(&connect);
    form.append(&label("Vorhandene passende Profile werden verwendet. Neue Profile sind ausschließlich für dein Linux-Konto freigegeben; Kennwörter verwaltet NetworkManager. Bei mehreren passenden Profilen wird keine automatische Auswahl getroffen."));
    let devices = Rc::new(RefCell::new(Vec::<(String, String)>::new()));
    let (d, picker, stat) = (devices.clone(), choices.clone(), status.clone());
    refresh.connect_clicked(move |b| {
        b.set_sensitive(false);
        let (b, d, picker, stat) = (b.clone(), d.clone(), picker.clone(), stat.clone());
        glib::MainContext::default().spawn_local(async move {
            match crate::bus::wifi_devices().await {
                Ok(rows) => {
                    let names: Vec<_> = rows.iter().map(|(_, name)| name.as_str()).collect();
                    picker.set_model(Some(&gtk::StringList::new(&names)));
                    *d.borrow_mut() = rows;
                }
                Err(e) => stat.set_text(&e.to_string()),
            }
            b.set_sensitive(true);
        });
    });
    let stat = status.clone();
    connect.connect_clicked(move |b| {
        let Some((device, _)) = devices.borrow().get(choices.selected() as usize).cloned() else {
            stat.set_text("Zuerst einen verfügbaren WLAN-Adapter auswählen.");
            return;
        };
        let security = match mode.selected() {
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
