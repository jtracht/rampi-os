//! Real XRDP integration through the production connection page in private Docker.
use crate::{
    checks::{find_button, named},
    widgets::{Feedback, Shared},
};
use anyhow::{Context, ensure};
use gtk::{glib, prelude::*};
use rdw::DisplayExt;
pub(crate) async fn type_remote(text: &str) -> anyhow::Result<()> {
    // wtype assigns physical codes in first-use order. Release-only commands
    // declare US evdev positions before sending actual scan-code input.
    let positions = "Escape 1 2 3 4 5 6 7 8 9 0 minus equal BackSpace Tab q w e r t y u i o p bracketleft bracketright Return Control_L a s d f g h j k l semicolon apostrophe grave Shift_L backslash z x c v b n m comma period slash Shift_R KP_Multiply Alt_L space";
    let mut keys: Vec<std::ffi::OsString> = positions
        .split_whitespace()
        .flat_map(|key| ["-p".into(), key.into()])
        .collect();
    for key in text.chars() {
        keys.extend(["-k".into(), key.to_string().into()]);
    }
    keys.extend(["-k".into(), "Return".into()]);
    ensure!(
        crate::process::output("wtype", &keys, 5, 32768).await?.0,
        "Keyboard injection failed"
    );
    Ok(())
}
async fn until(mut predicate: impl FnMut() -> bool) -> anyhow::Result<()> {
    for _ in 0..1500 {
        if predicate() {
            return Ok(());
        }
        glib::timeout_future(std::time::Duration::from_millis(20)).await;
    }
    anyhow::bail!("RDP condition timed out")
}
async fn mouse_clipboard(
    app: &gtk::Application,
    display: &rdw_rdp::Display,
    probe: &str,
) -> anyhow::Result<()> {
    let scrolls = std::rc::Rc::new(std::cell::RefCell::new(Vec::<(f64, f64)>::new()));
    let events = gtk::EventControllerScroll::new(gtk::EventControllerScrollFlags::BOTH_AXES);
    events.set_propagation_phase(gtk::PropagationPhase::Capture);
    let observed = scrolls.clone();
    events.connect_scroll(move |_, dx, dy| {
        observed.borrow_mut().push((dx, dy));
        glib::Propagation::Proceed
    });
    display.add_controller(events);
    let window = app.active_window().context("No actual Rampi window")?;
    let bounds = display
        .compute_bounds(&window)
        .context("RDP surface not allocated")?;
    let (x, y) = (
        bounds.x() + bounds.width() * 0.5,
        bounds.y() + bounds.height() * 0.5,
    );
    for args in [
        vec![
            "pointer".into(),
            "move".into(),
            "-10000".into(),
            "-10000".into(),
        ],
        vec![
            "pointer".into(),
            "move".into(),
            x.to_string().into(),
            y.to_string().into(),
        ],
        vec!["pointer".into(), "click".into(), "left".into()],
        vec!["pointer".into(), "move".into(), "30".into(), "20".into()],
        vec!["pointer".into(), "click".into(), "middle".into()],
        vec!["pointer".into(), "click".into(), "right".into()],
        vec!["pointer".into(), "scroll".into(), "15".into(), "0".into()],
        vec!["pointer".into(), "scroll".into(), "-15".into(), "0".into()],
        vec!["pointer".into(), "scroll".into(), "0".into(), "15".into()],
        vec!["pointer".into(), "scroll".into(), "0".into(), "-15".into()],
    ] {
        ensure!(
            crate::process::output("wlrctl", &args, 5, 32768).await?.0,
            "Actual Wayland pointer injection failed"
        );
        glib::timeout_future(std::time::Duration::from_millis(100)).await;
    }
    let clipboard = gtk::gdk::prelude::DisplayExt::clipboard(&display.display());
    for round in 0..2 {
        clipboard.set_text(&format!(
            "rampi-local-{probe}-{round}-Grüße 🥧\nsecond line"
        ));
        let expected = format!("rampi-remote-{probe}-{round}-Grüße 🥧\nsecond line");
        glib::future_with_timeout(std::time::Duration::from_secs(20), async {
            loop {
                if let Ok(Some(text)) = clipboard.read_text_future().await
                    && text.replace("\r\n", "\n") == expected
                {
                    break;
                }
                glib::timeout_future(std::time::Duration::from_millis(100)).await;
            }
        })
        .await
        .context("Actual XRDP Unicode clipboard roundtrip failed")?;
    }
    clipboard.set_text("");
    let (width, height) = display
        .display_size()
        .context("No remote desktop dimensions")?;
    let scale = (bounds.width() as f64 / width as f64).min(bounds.height() as f64 / height as f64);
    let report = serde_json::json!({"schema": 1, "probe": probe, "remote_size": [width, height], "scale": scale, "local_delta": [30, 20], "clipboard_roundtrips": 2, "gtk_scroll_deltas": *scrolls.borrow()});
    std::fs::write(
        std::path::Path::new(&std::env::var("RAMPI_TEST_ARTIFACTS")?).join("rdp-input.json"),
        serde_json::to_vec_pretty(&report)?,
    )?;
    println!("RAMPI_RUST_RDP_MOUSE_CLIPBOARD_OK");
    Ok(())
}
pub fn run(app: &gtk::Application, stack: &gtk::Stack, settings: &Shared, feedback: &Feedback) {
    assert_eq!(std::env::var("RAMPI_TEST_CONTAINER").as_deref(), Ok("1"));
    let (app, stack, settings, feedback) = (
        app.clone(),
        stack.clone(),
        settings.clone(),
        feedback.clone(),
    );
    glib::MainContext::default().spawn_local(async move {
        let result: anyhow::Result<()> = async {
            let fixture: serde_json::Value =
                serde_json::from_slice(&std::fs::read(std::env::var("RAMPI_TEST_RDP_FILE")?)?)?;
            let secret = fixture["password"]
                .as_str()
                .context("No fixture password")?;
            settings.borrow_mut().hosts = vec![rampi_core::config::Host {
                address: "rdp-server".into(),
                username: fixture["username"].as_str().unwrap_or("rdpuser").into(),
                ..Default::default()
            }];
            settings.borrow_mut().active_host = 0;
            crate::rdp_view::open(&stack, &settings, &feedback);
            let page = stack.visible_child().unwrap();
            until(|| page.is_mapped()).await?;
            let display = named(&page, "rdp-desktop")
                .unwrap()
                .downcast::<rdw_rdp::Display>()
                .unwrap();
            let pin = named(&page, "rdp-certificate-pin")
                .unwrap()
                .downcast::<gtk::Entry>()
                .unwrap();
            let password = named(&page, "rdp-password")
                .unwrap()
                .downcast::<gtk::PasswordEntry>()
                .unwrap();
            let state = named(&page, "rdp-status")
                .unwrap()
                .downcast::<gtk::Label>()
                .unwrap();
            let connect = find_button(&page, "Mit Windows verbinden").unwrap();
            let stop = find_button(&page, "Verbindung trennen").unwrap();
            let keyboard = gtk::gio::Subprocess::newv(
                &["wtype".as_ref(), "-s".as_ref(), "90000".as_ref()],
                gtk::gio::SubprocessFlags::STDOUT_SILENCE,
            )?;
            pin.set_text(&"0".repeat(64));
            password.set_text(secret);
            connect.emit_clicked();
            ensure!(password.text().is_empty(), "Password retained in form");
            until(|| connect.is_sensitive()).await?;
            ensure!(
                !display.property::<bool>("rdp-connected"),
                "Wrong certificate accepted"
            );
            ensure!(
                state.text().contains("fehlgeschlagen"),
                "Wrong certificate did not fail"
            );
            let certificate = named(&page, "rdp-certificate-status")
                .unwrap()
                .downcast::<gtk::Label>()
                .unwrap();
            ensure!(certificate.text().contains("Anmeldung abgewiesen"));
            println!("RAMPI_RUST_RDP_BAD_CERTIFICATE_OK");
            pin.set_text(
                fixture["fingerprint"]
                    .as_str()
                    .context("No certificate pin")?,
            );
            if fixture["nla"].as_bool() == Some(true) {
                // Additional acceptance against a real FreeRDP/WinPR NLA-only
                // server. The regular XRDP/input/reconnect test remains intact.
                let account = settings.borrow().hosts[0].username.clone();
                for (username, candidate) in [
                    (account.as_str(), "deliberately-incorrect-fixture-password"),
                    ("RAMPI\\missing-account", secret),
                ] {
                    settings.borrow_mut().hosts[0].username = username.into();
                    password.set_text(candidate);
                    connect.emit_clicked();
                    until(|| connect.is_sensitive()).await?;
                    ensure!(
                        !display.property::<bool>("rdp-connected"),
                        "NLA accepted invalid credentials"
                    );
                }
                settings.borrow_mut().hosts[0].username = account;
                for attempt in 0..2 {
                    password.set_text(secret);
                    connect.emit_clicked();
                    until(|| stop.is_sensitive() || connect.is_sensitive()).await?;
                    ensure!(
                        display.property::<bool>("rdp-connected"),
                        "NLA failed: {}",
                        state.text()
                    );
                    until(|| display.display_size() == Some((1280, 720)))
                        .await
                        .with_context(|| {
                            format!("NLA frame/profile resolution: {:?}", display.display_size())
                        })?;
                    display.grab_focus();
                    type_remote(&format!("rampinla{attempt}")).await?;
                    glib::timeout_future(std::time::Duration::from_millis(500)).await;
                    stop.emit_clicked();
                    until(|| connect.is_sensitive()).await?;
                    ensure!(!display.property::<bool>("rdp-connected"));
                }
                keyboard.force_exit();
                println!("RAMPI_RUST_RDP_NLA_BAD_ACCOUNT_REJECT_OK");
                println!("RAMPI_RUST_RDP_NLA_DOMAIN_RECONNECT_OK");
                return Ok(());
            }
            for attempt in 0..2 {
                password.set_text(secret);
                connect.emit_clicked();
                until(|| stop.is_sensitive() || connect.is_sensitive()).await?;
                ensure!(
                    display.property::<bool>("rdp-connected"),
                    "RDP connect failed: {}",
                    state.text()
                );
                glib::timeout_future(std::time::Duration::from_secs(4)).await;
                ensure!(
                    display.property::<bool>("rdp-connected"),
                    "Connection ended: {}",
                    state.text()
                );
                ensure!(
                    display.display_size().is_some(),
                    "No actual remote frame received"
                );
                ensure!(app.windows().len() == 1, "External RDP window opened");
                if attempt == 0 && std::env::args().any(|a| a == "--mixed-soak-check") {
                    crate::mixed_soak::run(&app, &stack, &settings, &feedback, &display).await?;
                }
                display.grab_focus();
                type_remote(&format!("rampirdp{attempt}")).await?;
                glib::timeout_future(std::time::Duration::from_millis(800)).await;
                if attempt == 0 && !std::env::args().any(|a| a == "--mixed-soak-check") {
                    mouse_clipboard(
                        &app,
                        &display,
                        fixture["probe"].as_str().context("No RDP probe nonce")?,
                    )
                    .await?;
                }
                if attempt == 0 {
                    if let Ok(directory) = std::env::var("RAMPI_TEST_ARTIFACTS") {
                        let (ok, _) = crate::process::output(
                            "grim",
                            &[format!("{directory}/rust-rdp.png").into()],
                            5,
                            32768,
                        )
                        .await?;
                        ensure!(ok, "RDP screenshot failed");
                    }
                    let (ok, _) = crate::process::output(
                        "wtype",
                        &[
                            "-M".into(),
                            "ctrl".into(),
                            "-M".into(),
                            "alt".into(),
                            "-k".into(),
                            "Home".into(),
                            "-m".into(),
                            "alt".into(),
                            "-m".into(),
                            "ctrl".into(),
                        ],
                        5,
                        32768,
                    )
                    .await?;
                    ensure!(ok);
                    until(|| stack.visible_child_name().as_deref() == Some("dashboard")).await?;
                    ensure!(
                        display.property::<bool>("rdp-connected"),
                        "Module change ended RDP session"
                    );
                    crate::rdp_view::open(&stack, &settings, &feedback);
                    until(|| page.is_mapped()).await?;
                    if !std::env::args().any(|a| a == "--mixed-soak-check") {
                        display.grab_focus();
                        type_remote("rampiafterhome").await?;
                        glib::timeout_future(std::time::Duration::from_millis(800)).await;
                    }
                }
                if attempt == 0 {
                    stop.emit_clicked();
                } else {
                    std::fs::write(
                        std::path::Path::new(&std::env::var("RAMPI_TEST_ARTIFACTS")?)
                            .join("rdp-disconnect-ready"),
                        "ready",
                    )?;
                }
                until(|| connect.is_sensitive()).await?;
                ensure!(!display.property::<bool>("rdp-connected"));
            }
            ensure!(app.windows().len() == 1);
            println!("RAMPI_RUST_RDP_SERVER_FAILURE_OK");
            keyboard.force_exit();
            println!("RAMPI_RUST_RDP_EMBEDDED_RECONNECT_OK");
            Ok(())
        }
        .await;
        if let Err(error) = result {
            eprintln!("RDP check failed: {error:#}");
            std::process::exit(1);
        }
        app.quit();
    });
}
