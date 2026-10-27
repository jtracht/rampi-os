//! NetworkManager owns parsing, key storage, permissions and tunnel operation.
use crate::bus::{self, NM, ROOT, Settings, Values};
use anyhow::{Context, Result, ensure};
use glib::{
    object::ObjectType,
    translate::from_glib_full,
    variant::{ObjectPath, ToVariant},
};
use gtk::{gio, glib};
use rampi_core::i18n::text as tr;
use std::{
    ffi::{CString, c_char, c_void},
    fs::{File, OpenOptions},
    io::{Read, Write},
    os::unix::{ffi::OsStrExt, fs::OpenOptionsExt},
    path::Path,
};

const SETTINGS: &str = "/org/freedesktop/NetworkManager/Settings";
const SETTINGS_API: &str = "org.freedesktop.NetworkManager.Settings";
const CONNECTION_API: &str = "org.freedesktop.NetworkManager.Settings.Connection";
const ACTIVE_API: &str = "org.freedesktop.NetworkManager.Connection.Active";

#[link(name = "nm")]
unsafe extern "C" {
    fn nm_conn_wireguard_import(
        filename: *const c_char,
        error: *mut *mut glib::ffi::GError,
    ) -> *mut glib::gobject_ffi::GObject;
    fn nm_connection_to_dbus(connection: *mut c_void, flags: u32) -> *mut glib::ffi::GVariant;
}

/// Parse a bounded private snapshot using libnm. No configuration or key data
/// is ever passed in argv, logged, or persisted by Rampi outside this tempdir.
pub fn prepare(filename: &Path) -> Result<Settings> {
    ensure!(
        filename.extension().is_some_and(|s| s == "conf"),
        "{}",
        tr("wireguard-extension", &[])
    );
    let file = File::open(filename).context(tr("wireguard-unreadable", &[]))?;
    let metadata = file.metadata()?;
    ensure!(
        metadata.is_file() && metadata.len() <= 65_536,
        "{}",
        tr("wireguard-regular-file", &[])
    );
    let mut data = Vec::new();
    file.take(65_537).read_to_end(&mut data)?;
    ensure!(data.len() <= 65_536, "{}", tr("wireguard-too-large", &[]));
    let directory = tempfile::tempdir()?;
    let snapshot = directory.path().join(
        filename
            .file_name()
            .context(tr("wireguard-filename", &[]))?,
    );
    let mut copy = OpenOptions::new()
        .write(true)
        .create_new(true)
        .mode(0o600)
        .open(&snapshot)?;
    copy.write_all(&data)?;
    drop(copy);
    let name = CString::new(snapshot.as_os_str().as_bytes())?;
    let mut error = std::ptr::null_mut();
    // SAFETY: NUL-terminated owned filename and a valid writable GError slot.
    // libnm returns one owned GObject reference, released by glib::Object.
    let raw = unsafe { nm_conn_wireguard_import(name.as_ptr(), &mut error) };
    if !error.is_null() {
        // Importer diagnostics can contain key material; free without displaying.
        unsafe { glib::ffi::g_error_free(error) };
    }
    ensure!(!raw.is_null(), "{}", tr("wireguard-import-error", &[]));
    let connection: glib::Object = unsafe { from_glib_full(raw) };
    // NM_CONNECTION_SERIALIZE_ALL = 0. The returned GVariant has transfer-full
    // ownership; glib::Variant frees it once the parsed settings are extracted.
    let raw = unsafe { nm_connection_to_dbus(connection.as_ptr().cast(), 0) };
    ensure!(
        !raw.is_null(),
        "{}",
        tr("wireguard-profile-unreadable", &[])
    );
    let variant: glib::Variant = unsafe { from_glib_full(raw) };
    let mut settings: Settings = variant
        .get()
        .context(tr("wireguard-profile-invalid", &[]))?;
    let general = settings
        .get_mut("connection")
        .context(tr("wireguard-connection-missing", &[]))?;
    ensure!(
        bus::text(general, "type") == "wireguard",
        "{}",
        tr("wireguard-wrong-type", &[])
    );
    general.insert(
        "permissions".into(),
        vec![format!("user:{}:", glib::user_name().to_string_lossy())].to_variant(),
    );
    general.insert("autoconnect".into(), false.to_variant());
    Ok(settings)
}

#[derive(Clone, PartialEq, Eq)]
pub struct Profile {
    pub uuid: String,
    pub name: String,
    pub path: String,
    pub active: Vec<String>,
    pub state: u32,
}

pub async fn profiles() -> Result<Vec<Profile>> {
    let connection = bus::system().await?;
    let root = bus::properties(&connection, NM, ROOT, NM).await?;
    let active: Vec<ObjectPath> = root
        .get("ActiveConnections")
        .and_then(|v| v.get())
        .unwrap_or_default();
    let mut active_profiles = vec![];
    for path in active {
        if let Ok(values) = bus::properties(&connection, NM, &path, ACTIVE_API).await {
            active_profiles.push((
                bus::text(&values, "Uuid"),
                path.to_string(),
                bus::number(&values, "State"),
            ));
        }
    }
    let paths: Vec<ObjectPath> = bus::call(
        &connection,
        NM,
        SETTINGS,
        SETTINGS_API,
        "ListConnections",
        None,
    )
    .await?
    .child_value(0)
    .get()
    .context(tr("wireguard-list-missing", &[]))?;
    let own = vec![format!("user:{}:", glib::user_name().to_string_lossy())];
    let mut rows = vec![];
    for path in paths {
        // Profiles may disappear or become inaccessible during a refresh.
        let Ok(reply) =
            bus::call(&connection, NM, &path, CONNECTION_API, "GetSettings", None).await
        else {
            continue;
        };
        let Some(settings) = reply.child_value(0).get::<Settings>() else {
            continue;
        };
        let Some(general) = settings.get("connection") else {
            continue;
        };
        let permissions: Vec<String> = general
            .get("permissions")
            .and_then(|v| v.get())
            .unwrap_or_default();
        if bus::text(general, "type") != "wireguard" || permissions != own {
            continue;
        }
        let uuid = bus::text(general, "uuid");
        if uuid.is_empty() {
            continue;
        }
        let matches: Vec<_> = active_profiles
            .iter()
            .filter(|(id, _, _)| *id == uuid)
            .collect();
        rows.push(Profile {
            name: bus::text(general, "id"),
            path: path.to_string(),
            uuid,
            active: matches.iter().map(|(_, path, _)| path.clone()).collect(),
            state: if matches.iter().any(|(_, _, state)| *state == 2) {
                2
            } else {
                matches.first().map_or(0, |(_, _, state)| *state)
            },
        });
    }
    rows.sort_by_key(|p| p.name.to_lowercase());
    Ok(rows)
}

pub async fn import(filename: std::path::PathBuf) -> Result<()> {
    let settings = gio::spawn_blocking(move || prepare(&filename))
        .await
        .map_err(|_| anyhow::anyhow!(tr("wireguard-import-cancelled", &[])))??;
    let connection = bus::system().await?;
    bus::call(
        &connection,
        NM,
        SETTINGS,
        SETTINGS_API,
        "AddConnection2",
        Some(&(settings, 1u32, Values::new()).to_variant()),
    )
    .await?;
    Ok(())
}

pub async fn change(uuid: &str, connect: bool) -> Result<()> {
    // Re-read ownership and paths at the time of every operation. UUID and
    // paths from a stale widget are never treated as permission evidence.
    let profile = profiles()
        .await?
        .into_iter()
        .find(|p| p.uuid == uuid)
        .context(tr("wireguard-no-longer-available", &[]))?;
    let connection = bus::system().await?;
    if connect {
        if !profile.active.is_empty() {
            return Ok(());
        }
        bus::call(
            &connection,
            NM,
            ROOT,
            NM,
            "ActivateConnection",
            Some(&(bus::path(&profile.path)?, bus::path("/")?, bus::path("/")?).to_variant()),
        )
        .await?;
    } else {
        for active in profile.active {
            bus::call(
                &connection,
                NM,
                ROOT,
                NM,
                "DeactivateConnection",
                Some(&(bus::path(&active)?,).to_variant()),
            )
            .await?;
        }
    }
    Ok(())
}
