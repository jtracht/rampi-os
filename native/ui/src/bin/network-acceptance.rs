//! QEMU-only acceptance using the exact production NetworkManager adapter.
#[cfg(target_os = "linux")]
#[allow(dead_code)]
#[path = "../bus.rs"]
mod bus;

#[cfg(target_os = "linux")]
async fn network() -> anyhow::Result<bus::Wifi> {
    for _ in 0..30 {
        let (_, mut rows) = bus::wifi_scan(false).await?;
        if rows.is_empty()
            && let Ok((_, scanned)) = bus::wifi_scan(true).await
        {
            rows = scanned;
        }
        if let Some(row) = rows.into_iter().find(|r| r.ssid == b"RampiVirtualPrivate") {
            return Ok(row);
        }
        gtk::glib::timeout_future_seconds(1).await;
    }
    anyhow::bail!("Virtual hostapd access point not discovered")
}

#[cfg(target_os = "linux")]
async fn forget() -> anyhow::Result<()> {
    use gtk::glib::variant::ObjectPath;
    let conn = bus::system().await?;
    let paths: Vec<ObjectPath> = bus::call(
        &conn,
        bus::NM,
        &format!("{}/Settings", bus::ROOT),
        &format!("{}.Settings", bus::NM),
        "ListConnections",
        None,
    )
    .await?
    .child_value(0)
    .get()
    .unwrap();
    for path in paths {
        let Ok(reply) = bus::call(
            &conn,
            bus::NM,
            &path,
            &format!("{}.Settings.Connection", bus::NM),
            "GetSettings",
            None,
        )
        .await
        else {
            continue;
        };
        let settings: bus::Settings = reply.child_value(0).get().unwrap();
        if settings
            .get("802-11-wireless")
            .and_then(|v| v.get("ssid"))
            .and_then(|v| v.get::<Vec<u8>>())
            .as_deref()
            == Some(b"RampiVirtualPrivate")
            && settings
                .get("connection")
                .and_then(|v| v.get("permissions"))
                .and_then(|v| v.get::<Vec<String>>())
                == Some(vec!["user:rampi:".into()])
        {
            bus::call(
                &conn,
                bus::NM,
                &path,
                &format!("{}.Settings.Connection", bus::NM),
                "Delete",
                None,
            )
            .await?;
        }
    }
    Ok(())
}

#[cfg(target_os = "linux")]
fn run() -> anyhow::Result<()> {
    use anyhow::ensure;
    use gtk::{gio, glib};
    ensure!(
        std::path::Path::new("/etc/rampi-acceptance-vm").is_file()
            && gio::Credentials::new().unix_user()? != 0
            && std::process::Command::new("systemd-detect-virt")
                .arg("--vm")
                .status()?
                .success(),
        "Designated unprivileged QEMU guest required"
    );
    glib::MainContext::default().block_on(async {
        if std::env::args().any(|a| a == "--other") {
            ensure!(
                network().await?.profile.is_empty(),
                "Another Linux user can reuse the private profile"
            );
            println!("RAMPI_RUST_WIFI_OTHER_USER_OK");
            return Ok(());
        }
        ensure!(
            glib::user_name() == "rampi",
            "Designated test account required"
        );
        let secret = std::fs::read_to_string("/run/rampi-acceptance-user/wifi-key")?;
        forget().await?;
        bus::wifi_connect(network().await?, secret.trim().into()).await?;
        let row = network().await?;
        ensure!(
            row.active && !row.profile.is_empty(),
            "WPA2 did not activate a saved personal profile"
        );
        let conn = bus::system().await?;
        let device =
            bus::properties(&conn, bus::NM, &row.device, &format!("{}.Device", bus::NM)).await?;
        let ip = bus::text(&device, "Ip4Config");
        let addresses =
            bus::properties(&conn, bus::NM, &ip, &format!("{}.IP4Config", bus::NM)).await?;
        let addresses: Vec<bus::Values> = addresses
            .get("AddressData")
            .and_then(|v| v.get())
            .unwrap_or_default();
        ensure!(
            addresses
                .iter()
                .any(|v| bus::text(v, "address").starts_with("198.18.55.")),
            "DHCP lease missing"
        );
        ensure!(
            std::process::Command::new("ping")
                .args(["-I", "wlan0", "-c", "2", "-W", "3", "198.18.55.1"])
                .output()?
                .status
                .success(),
            "Actual WLAN IP roundtrip failed"
        );
        bus::wifi_disconnect(&row).await?;
        glib::timeout_future_seconds(1).await;
        forget().await?;
        ensure!(
            bus::wifi_connect(network().await?, format!("{}wrong", secret.trim()))
                .await
                .is_err(),
            "WPA2 accepted a wrong credential"
        );
        ensure!(
            !network().await?.active,
            "Wrong credential left WLAN connected"
        );
        forget().await?;
        bus::wifi_connect(network().await?, secret.trim().into()).await?;
        ensure!(
            network().await?.active,
            "Reconnect failed after wrong credential"
        );
        println!("RAMPI_RUST_WIFI_LIVE_OK");
        Ok(())
    })
}

fn main() {
    #[cfg(target_os = "linux")]
    if let Err(e) = run() {
        eprintln!("Native WLAN acceptance failed: {e}");
        std::process::exit(1);
    }
    #[cfg(not(target_os = "linux"))]
    panic!("Linux QEMU guest required");
}
