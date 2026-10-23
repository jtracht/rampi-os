//! Real XRDP integration through the production connection page in private Docker.
use crate::{
    checks::{find_button, named},
    widgets::{Feedback, Shared},
};
use anyhow::{Context, ensure};
use gtk::{glib, prelude::*};
use rdw::DisplayExt;
async fn until(mut predicate: impl FnMut() -> bool) -> anyhow::Result<()> {
    for _ in 0..1500 {
        if predicate() {
            return Ok(());
        }
        glib::timeout_future(std::time::Duration::from_millis(20)).await;
    }
    anyhow::bail!("RDP condition timed out")
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
                username: "rdpuser".into(),
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
                display.grab_focus();
                // wtype assigns physical codes in first-use order. Predeclare
                // US evdev positions using release-only commands so this test
                // exercises RDW's physical scan-code path, not Unicode typing.
                let positions = "Escape 1 2 3 4 5 6 7 8 9 0 minus equal BackSpace Tab q w e r t y u i o p bracketleft bracketright Return Control_L a s d f g h j k l semicolon apostrophe grave Shift_L backslash z x c v b n m comma period slash Shift_R KP_Multiply Alt_L space";
                let mut keys: Vec<std::ffi::OsString> = positions.split_whitespace().flat_map(|key| ["-p".into(), key.into()]).collect();
                for key in format!("rampirdp{attempt}").chars() {
                    keys.extend(["-k".into(), key.to_string().into()]);
                }
                keys.extend(["-k".into(), "Return".into()]);
                let (ok, _) = crate::process::output(
                    "wtype",
                    &keys,
                    5,
                    32768,
                )
                .await?;
                ensure!(ok, "Keyboard injection failed");
                glib::timeout_future(std::time::Duration::from_millis(800)).await;
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
                }
                if attempt == 0 {
                    stop.emit_clicked();
                } else {
                    std::fs::write(std::path::Path::new(&std::env::var("RAMPI_TEST_ARTIFACTS")?).join("rdp-disconnect-ready"), "ready")?;
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
