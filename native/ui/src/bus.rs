//! Official GIO D-Bus calls. Futures run on GLib; no operation blocks GTK input.
use anyhow::{Context, Result, bail};
use glib::variant::{ObjectPath, ToVariant};
use gtk::{gio, glib};
use std::collections::HashMap;

pub const NM: &str = "org.freedesktop.NetworkManager";
pub const ROOT: &str = "/org/freedesktop/NetworkManager";
pub type Values = HashMap<String, glib::Variant>;
pub type Settings = HashMap<String, Values>;
pub async fn system() -> Result<gio::DBusConnection> {
    gio::bus_get_future(gio::BusType::System)
        .await
        .with_context(|| rampi_core::i18n::text("system-services-unavailable", &[]))
}
pub async fn call(
    bus: &gio::DBusConnection,
    name: &str,
    path: &str,
    interface: &str,
    method: &str,
    parameters: Option<&glib::Variant>,
) -> Result<glib::Variant> {
    bus.call_future(
        Some(name),
        path,
        interface,
        method,
        parameters,
        None,
        // Authorization must use existing policy without launching another
        // application's Polkit dialog. BlueZ's own Agent1 UI remains separate.
        gio::DBusCallFlags::NONE,
        if method == "Pair" { 90_000 } else { 15_000 },
    )
    .await
    .map_err(|_| {
        anyhow::anyhow!(
            "Systemdienst konnte {} nicht ausführen. Dienststatus und Berechtigung prüfen.",
            method
        )
    })
}
pub async fn properties(
    bus: &gio::DBusConnection,
    name: &str,
    path: &str,
    interface: &str,
) -> Result<Values> {
    call(
        bus,
        name,
        path,
        "org.freedesktop.DBus.Properties",
        "GetAll",
        Some(&(interface,).to_variant()),
    )
    .await?
    .child_value(0)
    .get()
    .context("Ungültige Dienstantwort")
}
pub fn text(v: &Values, key: &str) -> String {
    v.get(key).and_then(|v| v.str()).unwrap_or("").to_string()
}
pub fn flag(v: &Values, key: &str) -> bool {
    v.get(key).and_then(|v| v.get::<bool>()).unwrap_or(false)
}
pub fn number(v: &Values, key: &str) -> u32 {
    v.get(key).and_then(|v| v.get::<u32>()).unwrap_or(0)
}
pub fn path(value: &str) -> Result<ObjectPath> {
    ObjectPath::try_from(value).context("Ungültiger D-Bus-Pfad")
}

#[derive(Clone)]
pub struct Wifi {
    pub ssid: Vec<u8>,
    pub device: String,
    pub ap: String,
    pub label: String,
    pub mode: String,
    pub profile: String,
    pub active: bool,
}
impl Wifi {
    pub fn supported(&self) -> bool {
        self.mode != "unsupported" || !self.profile.is_empty()
    }
}
pub async fn wifi_scan(scan: bool) -> Result<(bool, Vec<Wifi>)> {
    let bus = system().await?;
    let root = properties(&bus, NM, ROOT, NM).await?;
    let enabled = flag(&root, "WirelessEnabled");
    if !enabled {
        return Ok((false, vec![]));
    }
    let devices: Vec<ObjectPath> = call(&bus, NM, ROOT, NM, "GetDevices", None)
        .await?
        .child_value(0)
        .get()
        .context("Keine Geräteantwort")?;
    let mut found = vec![];
    for device in devices {
        let d = properties(&bus, NM, &device, &format!("{NM}.Device")).await?;
        if number(&d, "DeviceType") != 2 || !flag(&d, "Managed") {
            continue;
        }
        let wi = format!("{NM}.Device.Wireless");
        if scan {
            call(
                &bus,
                NM,
                &device,
                &wi,
                "RequestScan",
                Some(&(Values::new(),).to_variant()),
            )
            .await?;
            glib::timeout_future_seconds(2).await;
        }
        let wireless = properties(&bus, NM, &device, &wi).await?;
        let mut saved = vec![];
        for profile in d
            .get("AvailableConnections")
            .and_then(|v| v.get::<Vec<ObjectPath>>())
            .unwrap_or_default()
        {
            if let Ok(reply) = call(
                &bus,
                NM,
                &profile,
                &format!("{NM}.Settings.Connection"),
                "GetSettings",
                None,
            )
            .await
                && let Some(s) = reply.child_value(0).get::<Settings>()
            {
                let permissions = s
                    .get("connection")
                    .and_then(|v| v.get("permissions"))
                    .and_then(|v| v.get::<Vec<String>>())
                    .unwrap_or_default();
                if permissions.is_empty()
                    || permissions
                        .contains(&format!("user:{}:", glib::user_name().to_string_lossy()))
                {
                    saved.push((profile.to_string(), s));
                }
            }
        }
        let aps: Vec<ObjectPath> = call(&bus, NM, &device, &wi, "GetAllAccessPoints", None)
            .await?
            .child_value(0)
            .get()
            .unwrap_or_default();
        for ap in aps {
            let a = properties(&bus, NM, &ap, &format!("{NM}.AccessPoint")).await?;
            let ssid = a
                .get("Ssid")
                .and_then(|v| v.get::<Vec<u8>>())
                .unwrap_or_default();
            if ssid.is_empty() {
                continue;
            }
            let rsn = number(&a, "RsnFlags");
            let mode = if rsn & 0x100 != 0 {
                "wpa-psk"
            } else if rsn & 0x400 != 0 {
                "sae"
            } else if number(&a, "Flags") & 1 == 0 && rsn == 0 && number(&a, "WpaFlags") == 0 {
                "open"
            } else {
                "unsupported"
            };
            let profile = saved
                .iter()
                .find(|(_, s)| {
                    s.get("802-11-wireless")
                        .and_then(|v| v.get("ssid"))
                        .and_then(|v| v.get::<Vec<u8>>())
                        .as_ref()
                        == Some(&ssid)
                })
                .map(|(p, _)| p.clone())
                .unwrap_or_default();
            let active =
                text(&wireless, "ActiveAccessPoint") == ap.as_str() && number(&d, "State") == 100;
            let label = format!(
                "{} · {} %{}{}",
                String::from_utf8_lossy(&ssid)
                    .chars()
                    .filter(|c| !c.is_control())
                    .collect::<String>(),
                a.get("Strength").and_then(|v| v.get::<u8>()).unwrap_or(0),
                if active { " · Verbunden" } else { "" },
                if !profile.is_empty() {
                    " · Gespeichert"
                } else {
                    ""
                }
            );
            found.push(Wifi {
                ssid,
                device: device.to_string(),
                ap: ap.to_string(),
                label,
                mode: mode.into(),
                profile,
                active,
            });
        }
    }
    found.sort_by_key(|w| (!w.active, w.label.clone()));
    Ok((enabled, found))
}
pub async fn wifi_radio(enabled: bool) -> Result<()> {
    let bus = system().await?;
    call(
        &bus,
        NM,
        ROOT,
        "org.freedesktop.DBus.Properties",
        "Set",
        Some(&(NM, "WirelessEnabled", enabled.to_variant()).to_variant()),
    )
    .await?;
    Ok(())
}
pub async fn wifi_disconnect(row: &Wifi) -> Result<()> {
    let bus = system().await?;
    call(
        &bus,
        NM,
        &row.device,
        &format!("{NM}.Device"),
        "Disconnect",
        None,
    )
    .await?;
    Ok(())
}
pub async fn wifi_connect(row: Wifi, password: String) -> Result<()> {
    wifi_connect_inner(row, password, false).await
}
pub async fn wifi_devices() -> Result<Vec<(String, String)>> {
    let bus = system().await?;
    let devices: Vec<ObjectPath> = call(&bus, NM, ROOT, NM, "GetDevices", None)
        .await?
        .child_value(0)
        .get()
        .context("Keine Geräteantwort")?;
    let mut result = vec![];
    for device in devices.into_iter().take(64) {
        let props = properties(&bus, NM, &device, &format!("{NM}.Device")).await?;
        if number(&props, "DeviceType") == 2 && flag(&props, "Managed") {
            result.push((device.to_string(), text(&props, "Interface")));
        }
    }
    Ok(result)
}
pub async fn wifi_hidden(device: &str, ssid: &str, mode: &str, password: String) -> Result<()> {
    anyhow::ensure!(
        !ssid.is_empty() && ssid.len() <= 32,
        "SSID muss 1 bis 32 UTF-8-Bytes lang sein"
    );
    anyhow::ensure!(
        ["open", "wpa-psk", "sae"].contains(&mode),
        "Unbekannte WLAN-Sicherheit"
    );
    let devices = wifi_devices().await?;
    anyhow::ensure!(
        devices.iter().any(|(p, _)| p == device),
        "WLAN-Adapter nicht verfügbar"
    );
    let bus = system().await?;
    let paths: Vec<ObjectPath> = call(
        &bus,
        NM,
        &format!("{ROOT}/Settings"),
        &format!("{NM}.Settings"),
        "ListConnections",
        None,
    )
    .await?
    .child_value(0)
    .get()
    .context("Profilliste fehlt")?;
    anyhow::ensure!(paths.len() <= 4096, "Zu viele Netzwerkprofile");
    let mut saved = vec![];
    for path in paths {
        if let Ok(reply) = call(
            &bus,
            NM,
            &path,
            &format!("{NM}.Settings.Connection"),
            "GetSettings",
            None,
        )
        .await
            && let Some(settings) = reply.child_value(0).get::<Settings>()
            && let Some(wifi) = settings.get("802-11-wireless")
            && wifi.get("ssid").and_then(|v| v.get::<Vec<u8>>()).as_deref() == Some(ssid.as_bytes())
        {
            let connection = settings.get("connection");
            let permissions = connection
                .and_then(|v| v.get("permissions"))
                .and_then(|v| v.get::<Vec<String>>())
                .unwrap_or_default();
            let own = format!("user:{}:", glib::user_name().to_string_lossy());
            let interface = connection
                .map(|v| text(v, "interface-name"))
                .unwrap_or_default();
            let security = settings
                .get("802-11-wireless-security")
                .map(|v| text(v, "key-mgmt"))
                .unwrap_or_else(|| "open".into());
            if (permissions.is_empty() || permissions.contains(&own))
                && security == mode
                && (interface.is_empty()
                    || devices
                        .iter()
                        .any(|(p, name)| p == device && name == &interface))
            {
                saved.push(path.to_string());
            }
        }
    }
    anyhow::ensure!(
        saved.len() <= 1,
        "Mehrere passende Profile vorhanden. Das gewünschte vorhandene Profil zuerst bereinigen."
    );
    wifi_connect_inner(
        Wifi {
            ssid: ssid.as_bytes().to_vec(),
            device: device.into(),
            ap: "/".into(),
            label: ssid.into(),
            mode: mode.into(),
            profile: saved.into_iter().next().unwrap_or_default(),
            active: false,
        },
        password,
        true,
    )
    .await
}
async fn wifi_connect_inner(row: Wifi, password: String, hidden: bool) -> Result<()> {
    if !row.supported() {
        bail!("Dieses Unternehmensnetz benötigt ein vorhandenes NetworkManager-Profil");
    }
    let bus = system().await?;
    let active = if !row.profile.is_empty() {
        call(
            &bus,
            NM,
            ROOT,
            NM,
            "ActivateConnection",
            Some(&(path(&row.profile)?, path(&row.device)?, path(&row.ap)?).to_variant()),
        )
        .await?
        .child_value(0)
        .get::<ObjectPath>()
        .context("Aktive Verbindung fehlt")?
    } else {
        if row.mode != "open" && (password.is_empty() || password.len() > 256) {
            bail!("Ein gültiges WLAN-Kennwort eingeben");
        }
        let mut settings = Settings::new();
        settings.insert(
            "connection".into(),
            HashMap::from([
                (
                    "id".into(),
                    format!("Rampi · {}", String::from_utf8_lossy(&row.ssid)).to_variant(),
                ),
                ("uuid".into(), glib::uuid_string_random().to_variant()),
                ("type".into(), "802-11-wireless".to_variant()),
                ("autoconnect".into(), false.to_variant()),
                (
                    "permissions".into(),
                    vec![format!("user:{}:", glib::user_name().to_string_lossy())].to_variant(),
                ),
            ]),
        );
        settings.insert(
            "802-11-wireless".into(),
            HashMap::from([
                ("ssid".into(), row.ssid.to_variant()),
                ("mode".into(), "infrastructure".to_variant()),
                ("hidden".into(), hidden.to_variant()),
            ]),
        );
        settings.insert(
            "ipv4".into(),
            HashMap::from([("method".into(), "auto".to_variant())]),
        );
        settings.insert(
            "ipv6".into(),
            HashMap::from([("method".into(), "auto".to_variant())]),
        );
        if row.mode != "open" {
            settings.insert(
                "802-11-wireless-security".into(),
                HashMap::from([
                    ("key-mgmt".into(), row.mode.to_variant()),
                    ("psk".into(), password.to_variant()),
                    ("psk-flags".into(), 0u32.to_variant()),
                    ("proto".into(), vec!["rsn"].to_variant()),
                ]),
            );
        }
        call(
            &bus,
            NM,
            ROOT,
            NM,
            "AddAndActivateConnection2",
            Some(&(settings, path(&row.device)?, path(&row.ap)?, Values::new()).to_variant()),
        )
        .await?
        .child_value(1)
        .get::<ObjectPath>()
        .context("Aktive Verbindung fehlt")?
    };
    for _ in 0..60 {
        glib::timeout_future_seconds(1).await;
        let state = properties(&bus, NM, &active, &format!("{NM}.Connection.Active")).await?;
        match number(&state, "State") {
            2 => return Ok(()),
            4 => bail!("WLAN-Verbindung fehlgeschlagen. Kennwort und Netzwerk prüfen."),
            _ => (),
        }
    }
    let _ = call(
        &bus,
        NM,
        ROOT,
        NM,
        "DeactivateConnection",
        Some(&(active,).to_variant()),
    )
    .await;
    bail!("WLAN-Verbindung hat zu lange gedauert")
}

#[derive(Clone, PartialEq, Eq)]
pub struct BluetoothDevice {
    pub path: String,
    pub label: String,
    pub paired: bool,
    pub connected: bool,
    pub trusted: bool,
}
#[derive(Clone, PartialEq, Eq)]
pub struct BluetoothAdapter {
    pub path: String,
    pub label: String,
    pub powered: bool,
}
/// A separate D-Bus client owns exactly this discovery session. Closing it
/// releases the session in BlueZ even after page changes or a failed stop.
pub struct BluetoothDiscovery {
    connection: gio::DBusConnection,
    adapter: String,
}
impl BluetoothDiscovery {
    pub async fn start(adapter: &str) -> Result<Self> {
        let (adapters, _) = bluetooth_snapshot().await?;
        if !adapters.iter().any(|a| a.path == adapter && a.powered) {
            bail!("Bluetooth-Adapter ist nicht verfügbar oder ausgeschaltet");
        }
        // System-bus address resolution reads local configuration; all actual
        // connection establishment and service operations remain asynchronous.
        let address =
            gio::dbus_address_get_for_bus_sync(gio::BusType::System, None::<&gio::Cancellable>)?;
        let connection = gio::DBusConnection::for_address_future(
            &address,
            gio::DBusConnectionFlags::AUTHENTICATION_CLIENT
                | gio::DBusConnectionFlags::MESSAGE_BUS_CONNECTION,
            None,
        )
        .await?;
        connection.set_exit_on_close(false);
        let session = Self {
            connection,
            adapter: adapter.into(),
        };
        call(
            &session.connection,
            "org.bluez",
            adapter,
            "org.bluez.Adapter1",
            "StartDiscovery",
            None,
        )
        .await?;
        Ok(session)
    }
    pub async fn stop(self) -> Result<()> {
        call(
            &self.connection,
            "org.bluez",
            &self.adapter,
            "org.bluez.Adapter1",
            "StopDiscovery",
            None,
        )
        .await?;
        Ok(())
    }
}
impl Drop for BluetoothDiscovery {
    fn drop(&mut self) {
        self.connection.close(None::<&gio::Cancellable>, |_| {});
    }
}
pub async fn bluetooth_snapshot() -> Result<(Vec<BluetoothAdapter>, Vec<BluetoothDevice>)> {
    let bus = system().await?;
    let reply = call(
        &bus,
        "org.bluez",
        "/",
        "org.freedesktop.DBus.ObjectManager",
        "GetManagedObjects",
        None,
    )
    .await?;
    let objects: HashMap<ObjectPath, Settings> =
        reply.child_value(0).get().context("BlueZ-Objekte fehlen")?;
    let (mut adapters, mut devices) = (vec![], vec![]);
    for (path, interfaces) in objects {
        if let Some(a) = interfaces.get("org.bluez.Adapter1") {
            adapters.push(BluetoothAdapter {
                path: path.to_string(),
                label: text(a, "Alias"),
                powered: flag(a, "Powered"),
            });
        }
        if let Some(d) = interfaces.get("org.bluez.Device1") {
            devices.push(BluetoothDevice {
                path: path.to_string(),
                label: format!(
                    "{} · {}{}",
                    text(d, "Alias"),
                    text(d, "Address"),
                    if flag(d, "Connected") {
                        " · Verbunden"
                    } else if flag(d, "Paired") {
                        " · Gekoppelt"
                    } else {
                        ""
                    }
                ),
                paired: flag(d, "Paired"),
                connected: flag(d, "Connected"),
                trusted: flag(d, "Trusted"),
            });
        }
    }
    adapters.sort_by(|a, b| a.path.cmp(&b.path));
    devices.sort_by(|a, b| a.label.cmp(&b.label));
    Ok((adapters, devices))
}
pub async fn bluetooth_action(operation: &str, object: &str, value: bool) -> Result<()> {
    let (adapters, devices) = bluetooth_snapshot().await?;
    let bus = system().await?;
    if operation == "power" && adapters.iter().any(|a| a.path == object) {
        call(
            &bus,
            "org.bluez",
            object,
            "org.freedesktop.DBus.Properties",
            "Set",
            Some(&("org.bluez.Adapter1", "Powered", value.to_variant()).to_variant()),
        )
        .await?;
    } else if devices.iter().any(|d| d.path == object) {
        match operation {
            "pair" | "connect" | "disconnect" | "cancel-pair" => {
                call(
                    &bus,
                    "org.bluez",
                    object,
                    "org.bluez.Device1",
                    match operation {
                        "pair" => "Pair",
                        "connect" => "Connect",
                        "disconnect" => "Disconnect",
                        _ => "CancelPairing",
                    },
                    None,
                )
                .await?;
            }
            "trust" => {
                call(
                    &bus,
                    "org.bluez",
                    object,
                    "org.freedesktop.DBus.Properties",
                    "Set",
                    Some(&("org.bluez.Device1", "Trusted", value.to_variant()).to_variant()),
                )
                .await?;
            }
            "remove" => {
                let adapter = object.rsplit_once('/').context("Gerätepfad fehlt")?.0;
                call(
                    &bus,
                    "org.bluez",
                    adapter,
                    "org.bluez.Adapter1",
                    "RemoveDevice",
                    Some(&(path(object)?,).to_variant()),
                )
                .await?;
            }
            _ => bail!("Unbekannte Bluetooth-Aktion"),
        }
    } else {
        bail!("Bluetooth-Gerät nicht mehr verfügbar");
    }
    Ok(())
}
