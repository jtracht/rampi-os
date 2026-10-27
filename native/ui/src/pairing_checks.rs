//! Service owner changes and display-only Agent1 lifecycle on a private bus.
use anyhow::{Context, ensure};
use glib::variant::ToVariant;
use gtk::{gio, glib, prelude::*};
use std::{cell::RefCell, rc::Rc};
async fn call(
    bus: &gio::DBusConnection,
    target: &str,
    method: &str,
    values: Vec<glib::Variant>,
) -> anyhow::Result<glib::Variant> {
    crate::bus::call(
        bus,
        "org.bluez",
        "/",
        "org.bluez.Mock",
        "CallAgent",
        Some(&(target, method, values).to_variant()),
    )
    .await
}
pub async fn extended(bus: &gio::DBusConnection, stack: &gtk::Stack) -> anyhow::Result<()> {
    use crate::checks::{find_button, named};
    let target = bus.unique_name().context("No bus identity")?;
    let device = crate::bus::path("/org/bluez/hci0/dev_02_00_00_00_00_01")?;
    for entered in [2u16, 6] {
        call(
            bus,
            &target,
            "DisplayPasskey",
            vec![
                device.to_variant(),
                42u32.to_variant(),
                entered.to_variant(),
            ],
        )
        .await?;
        let page = stack.child_by_name("pairing").context("No display page")?;
        ensure!(stack.visible_child_name().as_deref() == Some("pairing"));
        ensure!(
            named(&page, "pairing-code")
                .unwrap()
                .downcast::<gtk::Label>()
                .unwrap()
                .text()
                == "000042"
        );
        ensure!(
            crate::checks::readable_text(
                &named(&page, "pairing-entered")
                    .unwrap()
                    .downcast::<gtk::Label>()
                    .unwrap()
                    .text()
            ) == format!("{entered} / 6 Zeichen eingegeben")
        );
        ensure!(!find_button(&page, "Bestätigen").unwrap().is_visible());
    }
    call(bus, &target, "Cancel", vec![]).await?;
    ensure!(stack.visible_child_name().as_deref() != Some("pairing"));
    call(
        bus,
        &target,
        "DisplayPinCode",
        vec![device.to_variant(), "12ab".to_variant()],
    )
    .await?;
    call(bus, &target, "Release", vec![]).await?;
    ensure!(stack.visible_child_name().as_deref() != Some("pairing"));
    // Leave an actual pending method while the fixture process is replaced.
    let result = Rc::new(RefCell::new(None));
    let pending = result.clone();
    let (b, destination, d) = (bus.clone(), target.to_string(), device.clone());
    glib::MainContext::default().spawn_local(async move {
        *pending.borrow_mut() =
            Some(call(&b, &destination, "RequestPinCode", vec![d.to_variant()]).await);
    });
    for _ in 0..200 {
        if stack.visible_child_name().as_deref() == Some("pairing") {
            break;
        }
        glib::timeout_future(std::time::Duration::from_millis(20)).await;
    }
    let page = stack
        .child_by_name("pairing")
        .context("No pending request")?;
    let input = named(&page, "pairing-input")
        .unwrap()
        .downcast::<gtk::PasswordEntry>()
        .unwrap();
    input.set_text("discard-on-restart");
    let directory = std::path::PathBuf::from(std::env::var("RAMPI_TEST_PAIRING_DIR")?);
    std::fs::write(directory.join("restart-request"), "ready")?;
    for _ in 0..400 {
        if directory.join("restart-ready").exists() {
            break;
        }
        glib::timeout_future(std::time::Duration::from_millis(20)).await;
    }
    ensure!(
        directory.join("restart-ready").exists(),
        "Fixture did not restart"
    );
    glib::timeout_future(std::time::Duration::from_millis(500)).await;
    ensure!(
        input.text().is_empty() && stack.visible_child_name().as_deref() != Some("pairing"),
        "Lost service left stale pairing input/page"
    );
    ensure!(
        result.borrow().as_ref().is_some_and(|r| r.is_err()),
        "Lost owner kept its request"
    );
    call(
        bus,
        &target,
        "DisplayPinCode",
        vec![device.to_variant(), "new-owner".to_variant()],
    )
    .await?;
    ensure!(
        stack.visible_child_name().as_deref() == Some("pairing"),
        "New owner was not authorized"
    );
    crate::views::go_back(stack);
    ensure!(stack.visible_child_name().as_deref() != Some("pairing"));
    println!("RAMPI_RUST_PAIRING_RESTART_OK");
    Ok(())
}
