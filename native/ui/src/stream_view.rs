//! GTK presentation around existing Moonlight, GStreamer and Secret Service.
use crate::widgets::*;
use anyhow::{Result, ensure};
use gtk::{gdk, gio, glib, prelude::*};
use rampi_core::i18n::text as tr;
use rampi_stream::{
    client::{PairRequest, PairedHost, SavedIdentity, StreamOptions},
    runtime::{MoonlightRuntime, Phase, RemoteControl},
};
use std::{
    cell::{Cell, RefCell},
    rc::Rc,
    time::Duration,
};
use zeroize::Zeroizing;

const PORT: u16 = 47989;
type Active = Rc<RefCell<Option<RemoteControl>>>;

fn target(conf: &Shared) -> Result<(String, String, String)> {
    let settings = conf.borrow();
    let host = settings.host()?;
    let authority = if host.address.contains(':') {
        format!("[{}]", host.address.to_ascii_lowercase())
    } else {
        host.address.to_ascii_lowercase()
    };
    let source = format!("https://{authority}:{PORT}");
    rampi_core::config::validate_https(&source)?;
    let key = serde_json::to_string(&(&source, &host.username.to_ascii_lowercase()))?;
    let profile = glib::compute_checksum_for_string(glib::ChecksumType::Sha256, &key)
        .ok_or_else(|| anyhow::anyhow!(tr("stream-profile-missing", &[])))?
        .to_string();
    Ok((host.address.clone(), source, profile))
}

fn stop(active: &Active) {
    if let Some(control) = active.borrow().as_ref() {
        control.stop();
    }
}

pub fn open(stack: &gtk::Stack, conf: &Shared, f: &Feedback) {
    if stack.child_by_name("stream-session").is_some() {
        stack.set_visible_child_name("stream-session");
        return;
    }
    let page = column();
    let toolbar = row();
    let back = button("← Remote Desktop", f);
    back.set_widget_name("rampi-back");
    let route = stack.clone();
    back.connect_clicked(move |_| route.set_visible_child_name("remote"));
    toolbar.append(&back);
    let disconnect = button(&tr("stream-disconnect", &[]), f);
    disconnect.set_widget_name("stream-disconnect");
    toolbar.append(&disconnect);
    page.append(&toolbar);
    let settings_panel = column();
    page.append(&settings_panel);
    settings_panel.append(&label(&tr("stream-description", &[])));
    let host_label = label("");
    host_label.set_widget_name("stream-host");
    settings_panel.append(&host_label);
    let current = conf.clone();
    page.connect_map(move |_| {
        if let Ok(host) = current.borrow().host() {
            host_label.set_text(&tr(
                "stream-host-description",
                &[
                    ("name", &host.name),
                    ("address", &host.address),
                    ("user", &host.username),
                    ("resolution", &host.resolution),
                ],
            ));
        }
    });
    let state = label(&tr("stream-initial", &[]));
    state.set_widget_name("stream-status");
    page.append(&state);
    let controls = row();
    let pair = button(&tr("stream-pair", &[]), f);
    pair.set_widget_name("stream-pair");
    let load = button(&tr("stream-load", &[]), f);
    load.set_widget_name("stream-load");
    controls.append(&pair);
    controls.append(&load);
    settings_panel.append(&controls);
    let applications = gtk::StringList::new(&[]);
    let selection = gtk::ListBox::new();
    selection.set_selection_mode(gtk::SelectionMode::Single);
    selection.bind_model(Some(&applications), |item| {
        let text = item
            .downcast_ref::<gtk::StringObject>()
            .map(|s| s.string())
            .unwrap_or_default();
        let title = label(&text);
        title.set_margin_top(8);
        title.set_margin_bottom(8);
        title.upcast()
    });
    selection.set_widget_name("stream-applications");
    let app_scroll = gtk::ScrolledWindow::builder()
        .child(&selection)
        .min_content_height(40)
        .max_content_height(160)
        .propagate_natural_height(true)
        .hexpand(true)
        .build();
    settings_panel.append(&app_scroll);
    let start = button(&tr("stream-start", &[]), f);
    start.set_widget_name("stream-connect");
    start.set_sensitive(false);
    settings_panel.append(&start);
    let picture = gtk::Picture::builder()
        .hexpand(true)
        .vexpand(true)
        .can_shrink(true)
        .focusable(true)
        .build();
    picture.set_content_fit(gtk::ContentFit::Contain);
    picture.set_widget_name("stream-display");
    page.append(&picture);
    let active: Active = Rc::new(RefCell::new(None));
    crate::stream_input::attach(&picture, &active);
    let generation = Rc::new(Cell::new(0u64));
    let host_key = Rc::new(RefCell::new(String::new()));
    let app_ids = Rc::new(RefCell::new(Vec::<u32>::new()));

    for (trigger, pairing) in [(&pair, true), (&load, false)] {
        let (conf, state, active, serial, controls, start, apps, ids, key) = (
            conf.clone(),
            state.clone(),
            active.clone(),
            generation.clone(),
            controls.clone(),
            start.clone(),
            applications.clone(),
            app_ids.clone(),
            host_key.clone(),
        );
        let selection = selection.clone();
        trigger.connect_clicked(move |_| {
            stop(&active);
            serial.set(serial.get().wrapping_add(1));
            let ticket = serial.get();
            start.set_sensitive(false);
            ids.borrow_mut().clear();
            apps.splice(0, apps.n_items(), &[]);
            let (address, source, profile) = match target(&conf) {
                Ok(target) => target,
                Err(error) => {
                    state.set_text(&error.to_string());
                    return;
                }
            };
            *key.borrow_mut() = profile.clone();
            controls.set_sensitive(false);
            state.set_text(&tr(
                if pairing {
                    "stream-pair-preparing"
                } else {
                    "stream-pair-loading"
                },
                &[],
            ));
            let selected = selection.clone();
            let (state, serial, controls, start, apps, ids, conf) = (
                state.clone(),
                serial.clone(),
                controls.clone(),
                start.clone(),
                apps.clone(),
                ids.clone(),
                conf.clone(),
            );
            glib::MainContext::default().spawn_local(async move {
                let result: Result<_> = async {
                    let saved = if pairing {
                        let request =
                            gio::spawn_blocking(move || PairRequest::new(&address, PORT, "Rampi"))
                                .await
                                .map_err(|_| anyhow::anyhow!(tr("stream-pair-error", &[])))??;
                        ensure!(
                            serial.get() == ticket,
                            "{}",
                            tr("stream-pair-discarded", &[])
                        );
                        state.set_text(&tr("stream-pin", &[("pin", &request.pin())]));
                        let (_, saved) = gio::spawn_blocking(move || request.finish())
                            .await
                            .map_err(|_| anyhow::anyhow!(tr("stream-pair-interrupted", &[])))??;
                        ensure!(
                            serial.get() == ticket && target(&conf)?.2 == profile,
                            "Hostauswahl wurde geändert"
                        );
                        crate::secret_service::store_stream(&profile, &source, &saved.to_secret()?)
                            .await?;
                        saved
                    } else {
                        let encoded = Zeroizing::new(
                            crate::secret_service::load_stream(&profile, &source).await?,
                        );
                        let saved = SavedIdentity::from_secret(&encoded)?;
                        ensure!(
                            saved.matches_target(&address, PORT)?,
                            "{}",
                            tr("stream-wrong-host", &[])
                        );
                        saved
                    };
                    gio::spawn_blocking(move || PairedHost::restore(&saved)?.applications())
                        .await
                        .map_err(|_| {
                            anyhow::anyhow!("Anwendungsliste konnte nicht geladen werden")
                        })?
                }
                .await;
                if serial.get() != ticket {
                    return;
                }
                controls.set_sensitive(true);
                match result {
                    Ok(list) => {
                        for app in list.into_iter().take(256) {
                            let title: String = app
                                .title
                                .chars()
                                .take(512)
                                .map(|ch| if ch.is_control() { ' ' } else { ch })
                                .collect();
                            apps.append(&title);
                            ids.borrow_mut().push(app.id);
                        }
                        selected.select_row(selected.row_at_index(0).as_ref());
                        start.set_sensitive(!ids.borrow().is_empty());
                        state.set_text(&tr("stream-pair-ready", &[]));
                    }
                    Err(error) => state.set_text(&error.to_string()),
                }
            });
        });
    }
    let (conf, state, active_start, serial, selected, ids, key, form, controls_start, screen) = (
        conf.clone(),
        state.clone(),
        active.clone(),
        generation.clone(),
        selection.clone(),
        app_ids.clone(),
        host_key.clone(),
        start.clone(),
        controls.clone(),
        picture.clone(),
    );
    let polling_controls = controls.clone();
    let polling_state = state.clone();
    start.connect_clicked(move |_| {
        if active_start.borrow().is_some() {
            return;
        }
        let result = target(&conf).and_then(|target| {
            ensure!(
                target.2 == *key.borrow(),
                "Geänderten Host zuerst laden oder koppeln"
            );
            let id = *ids
                .borrow()
                .get(
                    selected
                        .selected_row()
                        .map(|r| r.index() as usize)
                        .unwrap_or(usize::MAX),
                )
                .ok_or_else(|| anyhow::anyhow!(tr("stream-select-app", &[])))?;
            let options = StreamOptions::for_resolution(&conf.borrow().host()?.resolution)?;
            Ok((target, id, options))
        });
        let ((address, source, profile), app, options) = match result {
            Ok(value) => value,
            Err(error) => {
                state.set_text(&error.to_string());
                return;
            }
        };
        form.set_sensitive(false);
        controls_start.set_sensitive(false);
        serial.set(serial.get().wrapping_add(1));
        let ticket = serial.get();
        screen.set_paintable(None::<&gdk::Paintable>);
        state.set_text(&tr("stream-connecting", &[]));
        let (state, active, serial, form, controls, screen, conf) = (
            state.clone(),
            active_start.clone(),
            serial.clone(),
            form.clone(),
            controls_start.clone(),
            screen.clone(),
            conf.clone(),
        );
        glib::MainContext::default().spawn_local(async move {
            let result: Result<_> = async {
                let encoded =
                    Zeroizing::new(crate::secret_service::load_stream(&profile, &source).await?);
                let saved = SavedIdentity::from_secret(&encoded)?;
                ensure!(
                    saved.matches_target(&address, PORT)?,
                    "{}",
                    tr("stream-wrong-host", &[])
                );
                gio::spawn_blocking(move || {
                    PairedHost::restore(&saved)?.prepare(&MoonlightRuntime::load()?, app, options)
                })
                .await
                .map_err(|_| anyhow::anyhow!(tr("stream-prepare-error", &[])))?
            }
            .await;
            if serial.get() != ticket {
                return;
            }
            match result {
                Ok((control, pending)) if target(&conf).is_ok_and(|t| t.2 == profile) => {
                    *active.borrow_mut() = Some(control);
                    screen.grab_focus();
                    // The official C start/stop and its lease always stay on this worker.
                    gio::spawn_blocking(move || {
                        if let Ok(session) = pending.start() {
                            session.wait();
                        }
                    });
                }
                Ok(_) => {
                    state.set_text(&tr("stream-host-changed", &[]));
                    form.set_sensitive(true);
                    controls.set_sensitive(true);
                }
                Err(error) => {
                    state.set_text(&error.to_string());
                    form.set_sensitive(true);
                    controls.set_sensitive(true);
                }
            }
        });
    });
    let state = polling_state;
    let (a, serial, state_stop, form, controls_stop) = (
        active.clone(),
        generation.clone(),
        state.clone(),
        start.clone(),
        controls.clone(),
    );
    let stop_screen = picture.clone();
    let stop_panel = settings_panel.clone();
    disconnect.connect_clicked(move |_| {
        serial.set(serial.get().wrapping_add(1));
        stop(&a);
        stop_screen.set_paintable(None::<&gdk::Paintable>);
        stop_panel.set_visible(true);
        state_stop.set_text(&tr("stream-disconnecting", &[]));
        let finished = a.borrow().is_none();
        form.set_sensitive(finished);
        controls_stop.set_sensitive(finished);
    });
    let (a, serial, screen, controls, form) = (
        active.clone(),
        generation.clone(),
        picture.clone(),
        controls.clone(),
        start.clone(),
    );
    let hidden_panel = settings_panel.clone();
    page.connect_unmap(move |_| {
        serial.set(serial.get().wrapping_add(1));
        stop(&a);
        screen.set_paintable(None::<&gdk::Paintable>);
        hidden_panel.set_visible(true);
        controls.set_sensitive(true);
        form.set_sensitive(true);
    });
    let weak = page.downgrade();
    glib::timeout_add_local(Duration::from_millis(33), move || {
        let Some(page) = weak.upgrade() else {
            stop(&active);
            return glib::ControlFlow::Break;
        };
        if !page.is_mapped() {
            return glib::ControlFlow::Continue;
        }
        let current = active.borrow().clone();
        if let Some(control) = current {
            match control.phase() {
                Phase::Connected => match control.take_frame() {
                    Ok(Some(frame)) => {
                        settings_panel.set_visible(false);
                        let texture = gdk::MemoryTexture::new(
                            frame.width as i32,
                            frame.height as i32,
                            gdk::MemoryFormat::R8g8b8a8,
                            &glib::Bytes::from_owned(frame.rgba),
                            frame.stride,
                        );
                        picture.set_paintable(Some(&texture));
                        state.set_text(&tr(
                            "stream-connected",
                            &[
                                ("width", &frame.width.to_string()),
                                ("height", &frame.height.to_string()),
                                ("decoder", &frame.decoder),
                            ],
                        ));
                    }
                    Ok(None) => (),
                    Err(_) => {
                        control.stop();
                        state.set_text(&tr("stream-decode-error", &[]));
                    }
                },
                Phase::Connecting { .. } => (),
                _ => {
                    active.borrow_mut().take();
                    settings_panel.set_visible(true);
                    picture.set_paintable(None::<&gdk::Paintable>);
                    state.set_text(&tr("stream-ended", &[]));
                    start.set_sensitive(true);
                    polling_controls.set_sensitive(true);
                }
            }
        }
        glib::ControlFlow::Continue
    });
    stack.add_named(&page, Some("stream-session"));
    stack.set_visible_child_name("stream-session");
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn personal_keyring_scope_follows_host_and_windows_account() {
        let settings = Rc::new(RefCell::new(rampi_core::config::Settings::default()));
        settings.borrow_mut().hosts = vec![rampi_core::config::Host {
            address: "Host.Example".into(),
            username: "Alice".into(),
            ..Default::default()
        }];
        let first = target(&settings).unwrap();
        settings.borrow_mut().hosts[0].address = "host.example".into();
        settings.borrow_mut().hosts[0].username = "ALICE".into();
        assert_eq!(first.2, target(&settings).unwrap().2);
        settings.borrow_mut().hosts[0].username = "Bob".into();
        assert_ne!(first.2, target(&settings).unwrap().2);
        settings.borrow_mut().hosts[0].address = "other.example".into();
        assert_ne!(first.1, target(&settings).unwrap().1);
    }
}
