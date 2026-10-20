//! Opt-in contract runner for an isolated system-bus fixture, never a host bus.
use crate::bus;
use anyhow::{Context, Result, ensure};
pub fn run() -> Result<()> {
    ensure!(
        std::env::var("RAMPI_TEST_CONTAINER").as_deref() == Ok("1"),
        "Service checks require their isolated test container"
    );
    ensure!(
        std::env::var("DBUS_SYSTEM_BUS_ADDRESS").is_ok(),
        "An isolated bus address is required"
    );
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
