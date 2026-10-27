//! Actual production GTK page against the isolated Sunshine fixture.
use crate::{
    checks::named,
    widgets::{Feedback, Shared},
};
use anyhow::{Context, Result, ensure};
use gtk::{gdk, glib, prelude::*};
use std::{path::Path, time::Duration};

async fn until(mut predicate: impl FnMut() -> bool) -> Result<()> {
    for _ in 0..3000 {
        if predicate() {
            return Ok(());
        }
        glib::timeout_future(Duration::from_millis(20)).await;
    }
    anyhow::bail!("Actual streaming page timed out")
}
pub fn run(app: &gtk::Application, stack: &gtk::Stack, conf: &Shared, feedback: &Feedback) {
    if std::env::var("RAMPI_TEST_CONTAINER").as_deref() != Ok("1")
        || !Path::new("/.dockerenv").is_file()
    {
        eprintln!("Disposable streaming fixture required");
        std::process::exit(2);
    }
    let (app, stack, conf, feedback) = (app.clone(), stack.clone(), conf.clone(), feedback.clone());
    glib::MainContext::default().spawn_local(async move {
        let outcome: Result<()> = async {
            let address = std::env::var("RAMPI_TEST_SUNSHINE")?;
            let ip: std::net::Ipv4Addr = address.parse()?;
            ensure!(
                ip.is_private() || ip.is_loopback(),
                "Private fixture required"
            );
            conf.borrow_mut().hosts = vec![rampi_core::config::Host {
                name: "Sunshine fixture".into(),
                address,
                username: "fixture".into(),
                ..Default::default()
            }];
            conf.borrow_mut().active_host = 0;
            crate::stream_view::open(&stack, &conf, &feedback);
            let page = stack
                .child_by_name("stream-session")
                .context("No embedded page")?;
            let button = |name| -> Result<gtk::Button> {
                named(&page, name)
                    .context("Missing stream action")?
                    .downcast()
                    .ok()
                    .context("Wrong action type")
            };
            let status: gtk::Label = named(&page, "stream-status")
                .context("No stream state")?
                .downcast()
                .ok()
                .context("Wrong state type")?;
            let picture: gtk::Picture = named(&page, "stream-display")
                .context("No embedded display")?
                .downcast()
                .ok()
                .context("Wrong display type")?;
            // Test-only observation at the actual GTK surface; keep the server
            // packet receipts as the required end-to-end input proof.
            let observed = gtk::EventControllerKey::new();
            observed.set_propagation_phase(gtk::PropagationPhase::Capture);
            observed.connect_key_pressed(|_, _, code, _| {
                println!("RAMPI_STREAM_TEST_KEY_DOWN={code}");
                glib::Propagation::Proceed
            });
            observed.connect_key_released(|_, _, code, _| {
                println!("RAMPI_STREAM_TEST_KEY_UP={code}");
            });
            picture.add_controller(observed);
            let pair = button("stream-pair")?;
            let load = button("stream-load")?;
            let connect = button("stream-connect")?;
            let disconnect = button("stream-disconnect")?;
            pair.emit_clicked();
            until(|| status.text().contains("Diesen PIN")).await?;
            let displayed = crate::checks::readable_text(&status.text());
            let pin = displayed
                .split_whitespace()
                .last()
                .context("No displayed PIN")?
                .to_owned();
            ensure!(
                pin.len() == 4 && pin.bytes().all(|b| b.is_ascii_digit()),
                "Invalid displayed PIN"
            );
            std::fs::write("/run/rampi-acceptance/pairing-pin", pin)?;
            until(|| connect.is_sensitive()).await?;
            ensure!(
                status.text().starts_with("Kopplung bestätigt"),
                "Pairing was not confirmed"
            );
            println!("RAMPI_STREAM_GTK_PRIVATE_PAIRING_OK");
            for connection in 0..2 {
                connect.emit_clicked();
                until(|| {
                    picture.paintable().is_some() && status.text().starts_with("Stream verbunden")
                })
                .await?;
                let texture: gdk::Texture = picture
                    .paintable()
                    .context("No rendered texture")?
                    .downcast()
                    .ok()
                    .context("Wrong texture type")?;
                ensure!(
                    texture.width() == 1280 && texture.height() == 720,
                    "Unexpected real stream size"
                );
                let mut first = vec![0u8; 1280 * 720 * 4];
                texture.download(&mut first, 1280 * 4);
                until(|| {
                    let Some(texture) = picture.paintable().and_downcast::<gdk::Texture>() else {
                        return false;
                    };
                    let mut second = vec![0u8; 1280 * 720 * 4];
                    texture.download(&mut second, 1280 * 4);
                    first != second
                })
                .await?;
                ensure!(app.windows().len() == 1, "Streaming opened another window");
                picture.grab_focus();
                // Let the compositor commit focus before the ephemeral wtype keymap.
                glib::timeout_future(Duration::from_millis(100)).await;
                crate::rdp_checks::type_remote("r").await?;
                let window = app.active_window().context("Actual window missing")?;
                let bounds = picture
                    .compute_bounds(&window)
                    .context("Actual picture allocation missing")?;
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
                        (bounds.x() + bounds.width() / 2.0).to_string().into(),
                        (bounds.y() + bounds.height() / 2.0).to_string().into(),
                    ],
                    vec!["pointer".into(), "click".into(), "left".into()],
                    vec!["pointer".into(), "scroll".into(), "15".into(), "0".into()],
                    vec!["pointer".into(), "scroll".into(), "0".into(), "15".into()],
                ] {
                    ensure!(
                        crate::process::output("wlrctl", &args, 5, 1024).await?.0,
                        "Actual pointer injection failed"
                    );
                }

                let output = format!("/run/rampi-acceptance/gtk-stream-{connection}.png");
                ensure!(
                    crate::process::output("grim", &[output.into()], 5, 1024)
                        .await?
                        .0,
                    "Actual GTK screenshot missing"
                );
                glib::timeout_future(Duration::from_millis(100)).await;
                if connection == 1 {
                    if std::env::args().any(|a| a == "--stream-ui-soak") {
                        crate::stream_soak::run(&picture, &window).await?;
                    }
                    // The reserved shortcut must be handled by the actual capture controller.
                    picture.grab_focus();
                    ensure!(
                        crate::process::output(
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
                                "ctrl".into()
                            ],
                            5,
                            1024
                        )
                        .await?
                        .0,
                        "Actual reserved shortcut injection failed"
                    );
                    until(|| stack.visible_child_name().as_deref() == Some("dashboard")).await?;

                    break;
                }
                disconnect.emit_clicked();
                until(|| connect.is_sensitive()).await?;
                ensure!(
                    picture.paintable().is_none(),
                    "Disconnected page retained a stale frame"
                );
                if connection == 0 {
                    // Reload through the real Secret Service adapter, not an in-memory identity.
                    load.emit_clicked();
                    until(|| connect.is_sensitive()).await?;
                }
            }
            until(|| !page.is_mapped()).await?;
            ensure!(
                picture.paintable().is_none(),
                "Hidden page retained a remote frame"
            );
            println!("RAMPI_STREAM_GTK_FRAMES_RECONNECT_OK");
            Ok(())
        }
        .await;
        if let Err(error) = outcome {
            eprintln!("Actual GTK streaming failed: {error:#}");
            std::process::exit(1);
        }
        app.quit();
    });
}
