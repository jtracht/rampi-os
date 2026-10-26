//! Rampi connection controls around the existing RDW/IronRDP desktop widget.
use crate::widgets::*;
use gtk::{glib, prelude::*};
use rampi_core::i18n::text as tr;
use rdw::DisplayExt;
use std::{cell::RefCell, rc::Rc};

pub fn open(stack: &gtk::Stack, conf: &Shared, f: &Feedback) {
    if stack.child_by_name("rdp-session").is_some() {
        stack.set_visible_child_name("rdp-session");
        return;
    }
    let page = column();
    let toolbar = row();
    let back = button(&tr("back-dashboard", &[]), f);
    back.set_widget_name("rampi-back");
    let route = stack.clone();
    back.connect_clicked(move |_| route.set_visible_child_name("dashboard"));
    toolbar.append(&back);
    let disconnect = button(&tr("rdp-disconnect", &[]), f);
    disconnect.set_sensitive(false);
    toolbar.append(&disconnect);
    page.append(&toolbar);
    let form = column();
    let target = label(&tr("rdp-active-profile", &[]));
    form.append(&target);
    let port = gtk::Entry::builder().text("3389").build();
    port.set_widget_name("rdp-port");
    form.append(&label(&tr("rdp-port", &[])));
    form.append(&port);
    let fingerprint = gtk::Entry::builder()
        .placeholder_text(tr("rdp-fingerprint-placeholder", &[]))
        .build();
    fingerprint.set_widget_name("rdp-certificate-pin");
    form.append(&label(&tr("rdp-fingerprint-label", &[])));
    form.append(&fingerprint);
    let password = gtk::PasswordEntry::builder()
        .placeholder_text(tr("rdp-password-placeholder", &[]))
        .show_peek_icon(true)
        .build();
    password.set_widget_name("rdp-password");
    form.append(&password);
    let connect = button(&tr("rdp-connect", &[]), f);
    form.append(&connect);
    page.append(&form);
    let status = label(&tr("rdp-profile-description", &[]));
    status.set_widget_name("rdp-status");
    page.append(&status);
    let certificate = label("");
    certificate.set_widget_name("rdp-certificate-status");
    certificate.set_selectable(true);
    page.append(&certificate);
    let display = rdw_rdp::Display::new(None);
    display.set_widget_name("rdp-desktop");
    display.set_hexpand(true);
    display.set_vexpand(true);
    display.set_property("scaling", true);
    display.set_remote_resize(false);
    page.append(&display);
    let state = status.clone();
    display.connect_local("rdp-error", false, move |values| {
        let error = values[1].get::<String>().unwrap_or_default();
        state.set_text(&tr("rdp-connection-failed", &[("error", &error)]));
        None
    });
    let expected: Rc<RefCell<String>> = Rc::new(RefCell::new(String::new()));
    let (pin, cert) = (expected.clone(), certificate.clone());
    display.connect_verify_tls_certificate(move |_, bytes| {
        let actual = glib::compute_checksum_for_data(glib::ChecksumType::Sha256, &bytes).unwrap();
        let matches = actual.as_str() == pin.borrow().as_str();
        cert.set_text(&tr(
            if matches {
                "rdp-certificate-matched"
            } else {
                "rdp-certificate-rejected"
            },
            &[("hash", &actual)],
        ));
        matches
    });
    let (c, summary, state, current) = (
        conf.clone(),
        target.clone(),
        status.clone(),
        display.clone(),
    );
    page.connect_map(move |_| {
        if current.property::<bool>("rdp-connected") {
            return;
        }
        match c.borrow().host() {
            Ok(host) => summary.set_text(&tr(
                "rdp-target",
                &[
                    ("name", &host.name),
                    ("address", &host.address),
                    ("account", &host.username),
                ],
            )),
            Err(error) => state.set_text(&error.to_string()),
        }
    });
    let (state, stop, start, controls) = (
        status.clone(),
        disconnect.clone(),
        connect.clone(),
        form.clone(),
    );
    display.connect_notify_local(Some("rdp-connected"), move |d, _| {
        if d.property::<bool>("rdp-connected") || !stop.is_sensitive() {
            return;
        }
        stop.set_sensitive(false);
        state.set_text(&tr("rdp-interrupted", &[]));
        let (d, start, controls) = (d.clone(), start.clone(), controls.clone());
        glib::MainContext::default().spawn_local(async move {
            let _ = d.rdp_disconnect().await;
            controls.set_visible(true);
            start.set_sensitive(true);
        });
    });
    let (d, state, start, controls) = (
        display.clone(),
        status.clone(),
        connect.clone(),
        form.clone(),
    );
    disconnect.connect_clicked(move |button| {
        button.set_sensitive(false);
        let (d, state, start, controls) =
            (d.clone(), state.clone(), start.clone(), controls.clone());
        glib::MainContext::default().spawn_local(async move {
            match d.rdp_disconnect().await {
                Ok(()) => state.set_text(&tr("rdp-disconnected", &[])),
                Err(error) => state.set_text(&tr(
                    "rdp-disconnect-failed",
                    &[("error", &error.to_string())],
                )),
            }
            controls.set_visible(true);
            start.set_sensitive(true);
        });
    });
    let (c, d, state, stop, controls, route) = (
        conf.clone(),
        display.clone(),
        status.clone(),
        disconnect.clone(),
        form.clone(),
        stack.clone(),
    );
    connect.connect_clicked(move |button| {
        let host = match c.borrow().host().cloned() {
            Ok(host) => host,
            Err(error) => {
                state.set_text(&error.to_string());
                return;
            }
        };
        let Ok(port) = port.text().parse::<u16>() else {
            state.set_text(&tr("rdp-invalid-port", &[]));
            return;
        };
        if port == 0 {
            state.set_text(&tr("rdp-invalid-port", &[]));
            return;
        }
        let pin = fingerprint
            .text()
            .chars()
            .filter(|c| *c != ':' && !c.is_whitespace())
            .collect::<String>()
            .to_ascii_lowercase();
        if pin.len() != 64 || !pin.bytes().all(|b| b.is_ascii_hexdigit()) {
            state.set_text(&tr("rdp-missing-fingerprint", &[]));
            return;
        }
        *expected.borrow_mut() = pin;
        let secret = zeroize::Zeroizing::new(password.text().to_string());
        password.set_text("");
        if secret.is_empty() {
            state.set_text(&tr("rdp-missing-password", &[]));
            return;
        }
        let resolution = host.resolution.split_once('x').and_then(|(width, height)| {
            Some((width.parse::<u16>().ok()?, height.parse::<u16>().ok()?))
        });
        let Some(resolution) = resolution else {
            state.set_text(&tr("rdp-invalid-resolution", &[]));
            return;
        };
        let layout = crate::system_settings::rdp_keyboard_layout();
        button.set_sensitive(false);
        state.set_text(&tr("rdp-connecting", &[]));
        let (d, state, stop, start, controls, route) = (
            d.clone(),
            state.clone(),
            stop.clone(),
            button.clone(),
            controls.clone(),
            route.clone(),
        );
        glib::MainContext::default().spawn_local(async move {
            match d
                .rdp_connect_configured(
                    &host.address,
                    port,
                    &host.username,
                    &secret,
                    resolution,
                    layout,
                )
                .await
            {
                Ok(()) => {
                    state.set_text(&tr("rdp-connected", &[]));
                    controls.set_visible(false);
                    stop.set_sensitive(true);
                    if route.visible_child_name().as_deref() == Some("rdp-session") {
                        d.grab_focus();
                    }
                }
                Err(error) => {
                    state.set_text(&tr(
                        "rdp-connection-failed",
                        &[("error", &error.to_string())],
                    ));
                    let _ = d.rdp_disconnect().await;
                    start.set_sensitive(true);
                }
            }
        });
    });
    stack.add_named(&page, Some("rdp-session"));
    stack.set_visible_child_name("rdp-session");
}
