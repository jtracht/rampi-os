//! Opt-in contract runner for an isolated system-bus fixture, never a host bus.
use crate::bus;
use anyhow::{Context, Result, ensure};
fn isolated() -> Result<()> {
    ensure!(
        std::env::var("RAMPI_TEST_CONTAINER").as_deref() == Ok("1"),
        "Service checks require their isolated test container"
    );
    ensure!(
        std::env::var("DBUS_SYSTEM_BUS_ADDRESS").is_ok(),
        "An isolated bus address is required"
    );
    Ok(())
}
pub fn run() -> Result<()> {
    isolated()?;
    gtk::glib::MainContext::default().block_on(async {
        let (enabled, rows) = bus::wifi_scan(true).await?;
        ensure!(enabled && rows.len() == 1, "Fixture WLAN missing");
        let keyfile = std::env::var("RAMPI_TEST_SECRET_FILE")?;
        let password = std::fs::read_to_string(&keyfile)?;
        bus::wifi_connect(rows[0].clone(), password).await?;
        let (_, rows) = bus::wifi_scan(false).await?;
        ensure!(rows[0].active, "Fixture did not activate WLAN");
        bus::wifi_disconnect(&rows[0]).await?;
        let (_, rows) = bus::wifi_scan(false).await?;
        ensure!(
            !rows[0].active && !rows[0].profile.is_empty(),
            "Profile reuse metadata missing"
        );
        bus::wifi_connect(
            rows.into_iter().next().context("Missing WLAN")?,
            String::new(),
        )
        .await?;
        bus::wifi_radio(false).await?;
        ensure!(!bus::wifi_scan(false).await?.0, "Radio did not switch off");
        bus::wifi_radio(true).await?;
        println!("RAMPI_RUST_NM_CONTRACT_OK");
        Ok(())
    })
}

pub fn bluetooth() -> Result<()> {
    isolated()?;
    gtk::glib::MainContext::default().block_on(async {
        let (adapters, devices) = bus::bluetooth_snapshot().await?;
        ensure!(
            adapters.len() == 1 && devices.len() == 1,
            "BlueZ fixture missing"
        );
        let adapter = &adapters[0].path;
        let device = &devices[0].path;
        ensure!(
            !devices[0].paired && !devices[0].trusted,
            "Fixture already paired"
        );
        ensure!(
            bus::BluetoothDiscovery::start("/org/bluez/missing")
                .await
                .is_err(),
            "Unknown adapter accepted"
        );
        ensure!(
            bus::bluetooth_action("trust", "/org/bluez/missing", true)
                .await
                .is_err(),
            "Unknown device accepted"
        );
        bus::bluetooth_action("power", adapter, true).await?;
        bus::BluetoothDiscovery::start(adapter)
            .await?
            .stop()
            .await?;

        // Observe the extra D-Bus client and its disappearance after leaving a
        // page drops the session. This checks actual GIO connection lifetime.
        let connection = bus::system().await?;
        let names = async || -> Result<Vec<String>> {
            bus::call(
                &connection,
                "org.freedesktop.DBus",
                "/org/freedesktop/DBus",
                "org.freedesktop.DBus",
                "ListNames",
                None,
            )
            .await?
            .child_value(0)
            .get()
            .context("No D-Bus names")
        };
        // Allow the explicit stop's asynchronous connection close to finish.
        gtk::glib::timeout_future(std::time::Duration::from_millis(100)).await;
        let before = names().await?;
        let session = bus::BluetoothDiscovery::start(adapter).await?;
        let added: Vec<String> = names()
            .await?
            .into_iter()
            .filter(|n| !before.contains(n))
            .collect();
        ensure!(
            added.len() == 1,
            "Discovery did not get its own D-Bus client"
        );
        drop(session);
        for _ in 0..50 {
            if !names().await?.contains(&added[0]) {
                break;
            }
            gtk::glib::timeout_future(std::time::Duration::from_millis(20)).await;
        }
        ensure!(
            !names().await?.contains(&added[0]),
            "Page departure left discovery client open"
        );
        bus::bluetooth_action("pair", device, false).await?;
        let (_, rows) = bus::bluetooth_snapshot().await?;
        ensure!(
            rows[0].paired && !rows[0].trusted,
            "Pairing silently changed trust"
        );
        bus::bluetooth_action("connect", device, false).await?;
        ensure!(
            bus::bluetooth_snapshot().await?.1[0].connected,
            "Connect failed"
        );
        bus::bluetooth_action("disconnect", device, false).await?;
        ensure!(
            !bus::bluetooth_snapshot().await?.1[0].connected,
            "Disconnect failed"
        );
        bus::bluetooth_action("trust", device, true).await?;
        ensure!(
            bus::bluetooth_snapshot().await?.1[0].trusted,
            "Trust failed"
        );
        bus::bluetooth_action("trust", device, false).await?;
        ensure!(
            !bus::bluetooth_snapshot().await?.1[0].trusted,
            "Untrust failed"
        );
        bus::bluetooth_action("remove", device, false).await?;
        ensure!(
            bus::bluetooth_snapshot().await?.1.is_empty(),
            "Remove failed"
        );
        bus::bluetooth_action("power", adapter, false).await?;
        ensure!(
            bus::BluetoothDiscovery::start(adapter).await.is_err(),
            "Powered-off discovery accepted"
        );
        println!("RAMPI_RUST_BLUEZ_CONTRACT_OK");
        Ok(())
    })
}
