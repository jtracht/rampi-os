//! Exact production GIO adapter against BlueZ and kernel VHCI in QEMU.
use super::bus;
use anyhow::{Context, Result, ensure};
use gtk::glib;

pub async fn run(cleanup: bool) -> Result<()> {
    let conn = bus::system().await?;
    let (adapters, _) = bus::bluetooth_snapshot().await?;
    ensure!(
        adapters.len() == 2,
        "Expected exactly two virtual controllers"
    );
    let local = "/org/bluez/hci0";
    let remote = "/org/bluez/hci1";
    let peer = bus::properties(&conn, "org.bluez", remote, "org.bluez.Adapter1").await?;
    let address = bus::text(&peer, "Address");
    let device = format!("{local}/dev_{}", address.replace(':', "_"));
    if cleanup {
        ensure!(
            bus::bluetooth_snapshot()
                .await?
                .1
                .iter()
                .any(|d| d.path == device && d.paired && d.trusted)
        );
        bus::bluetooth_action("trust", &device, false).await?;
        ensure!(
            !bus::bluetooth_snapshot()
                .await?
                .1
                .iter()
                .find(|d| d.path == device)
                .context("Paired device disappeared")?
                .trusted
        );
        bus::bluetooth_action("remove", &device, false).await?;
        ensure!(
            !bus::bluetooth_snapshot()
                .await?
                .1
                .iter()
                .any(|d| d.path == device)
        );
        ensure!(
            bus::bluetooth_action("pair", &device, false).await.is_err(),
            "Removed path remained actionable"
        );
        bus::bluetooth_action("power", local, false).await?;
        ensure!(
            !bus::bluetooth_snapshot()
                .await?
                .0
                .iter()
                .find(|a| a.path == local)
                .context("Local adapter disappeared")?
                .powered
        );
        bus::bluetooth_action("power", local, true).await?;
        println!("RAMPI_RUST_BLUEZ_VHCI_REMOVE_POWER_OK");
        return Ok(());
    }
    bus::bluetooth_action("power", local, true).await?;
    bus::bluetooth_action("power", remote, true).await?;
    let discovery = bus::BluetoothDiscovery::start(local).await?;
    let mut found = false;
    for _ in 0..45 {
        if bus::bluetooth_snapshot()
            .await?
            .1
            .iter()
            .any(|d| d.path == device)
        {
            found = true;
            break;
        }
        glib::timeout_future_seconds(1).await;
    }
    ensure!(found, "Peer was not discovered over virtual HCI");
    discovery.stop().await?;
    let local_properties = bus::properties(&conn, "org.bluez", local, "org.bluez.Adapter1").await?;
    ensure!(!bus::flag(&local_properties, "Discovering"));
    bus::bluetooth_action("pair", &device, false).await?;
    ensure!(
        bus::bluetooth_snapshot()
            .await?
            .1
            .iter()
            .any(|d| d.path == device && d.paired),
        "Actual BlueZ pairing did not complete"
    );
    bus::bluetooth_action("trust", &device, true).await?;
    ensure!(
        bus::bluetooth_snapshot()
            .await?
            .1
            .iter()
            .any(|d| d.path == device && d.trusted)
    );
    // Ask the peer adapter too: both controller directions must report a bond.
    let local_address = bus::text(&local_properties, "Address");
    let reverse = format!("{remote}/dev_{}", local_address.replace(':', "_"));
    let reverse = bus::properties(&conn, "org.bluez", &reverse, "org.bluez.Device1").await?;
    ensure!(
        bus::flag(&reverse, "Paired"),
        "Peer did not confirm the bond"
    );
    println!("RAMPI_RUST_BLUEZ_VHCI_PAIR_TRUST_OK");
    Ok(())
}
