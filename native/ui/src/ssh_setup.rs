//! Trust decisions use OpenSSH's key parser and fingerprints, never our own crypto.
use anyhow::{Context, Result, ensure};
use gtk::gio;
use rampi_core::config::{self, Host};
use std::{
    ffi::OsString,
    fs::{self, OpenOptions},
    io::Write,
    os::unix::fs::{MetadataExt, OpenOptionsExt, PermissionsExt},
    path::PathBuf,
};

pub fn directory() -> Result<PathBuf> {
    let directory = config::home()?.join(".ssh");
    if !directory.exists() {
        fs::create_dir(&directory)?;
    }
    let metadata = fs::symlink_metadata(&directory)?;
    ensure!(
        metadata.is_dir()
            && !metadata.file_type().is_symlink()
            && metadata.uid() == gio::Credentials::new().unix_user()?,
        "SSH-Verzeichnis muss deinem Linux-Konto gehören und ein echtes Verzeichnis sein"
    );
    fs::set_permissions(&directory, fs::Permissions::from_mode(0o700))?;
    Ok(directory)
}
pub fn key_path() -> Result<PathBuf> {
    Ok(directory()?.join("rampi_ed25519"))
}
fn known_hosts() -> Result<PathBuf> {
    let path = directory()?.join("known_hosts");
    if let Ok(metadata) = fs::symlink_metadata(&path) {
        ensure!(
            metadata.is_file()
                && !metadata.file_type().is_symlink()
                && metadata.uid() == gio::Credentials::new().unix_user()?
                && metadata.len() < 8_388_608,
            "Ungültige oder zu große persönliche Hostschlüsseldatei"
        );
    }
    Ok(path)
}
fn lookup(host: &Host) -> String {
    if host.port == 22 {
        host.address.clone()
    } else {
        format!("[{}]:{}", host.address, host.port)
    }
}
async fn existing(host: &Host, file: &std::path::Path) -> Result<bool> {
    if !file.exists() {
        return Ok(false);
    }
    let (found, _) = crate::process::output(
        "ssh-keygen",
        &[
            "-F".into(),
            lookup(host).into(),
            "-f".into(),
            file.as_os_str().into(),
        ],
        5,
        262_144,
    )
    .await?;
    Ok(found)
}
pub struct Scanned {
    pub host: Host,
    pub lines: Vec<u8>,
    pub fingerprint: String,
}
pub async fn scan(host: Host) -> Result<Scanned> {
    host.validate()?;
    let file = known_hosts()?;
    ensure!(
        !existing(&host, &file).await?,
        "Für diesen Host ist bereits ein Schlüssel bekannt. Er wird nicht automatisch ersetzt; bestehende OpenSSH-Konfiguration prüfen."
    );
    let (success, lines) = crate::process::output(
        "ssh-keyscan",
        &[
            "-H".into(),
            "-T".into(),
            "5".into(),
            "-p".into(),
            host.port.to_string().into(),
            "-t".into(),
            "ed25519".into(),
            host.address.clone().into(),
        ],
        8,
        65_536,
    )
    .await?;
    ensure!(
        success && !lines.is_empty(),
        "Kein Ed25519-Hostschlüssel erreichbar"
    );
    let mut snapshot = tempfile::NamedTempFile::new()?;
    snapshot.write_all(&lines)?;
    let (success, fingerprints) = crate::process::output(
        "ssh-keygen",
        &[
            "-l".into(),
            "-E".into(),
            "sha256".into(),
            "-f".into(),
            snapshot.path().as_os_str().into(),
        ],
        5,
        65_536,
    )
    .await?;
    ensure!(
        success,
        "OpenSSH konnte den empfangenen Hostschlüssel nicht prüfen"
    );
    let output = String::from_utf8(fingerprints)?;
    let mut values = output
        .lines()
        .map(|line| line.split_whitespace().nth(1).unwrap_or(""))
        .collect::<Vec<_>>();
    values.sort_unstable();
    values.dedup();
    ensure!(
        values.len() == 1 && values[0].starts_with("SHA256:"),
        "Mehrere unterschiedliche oder ungültige Hostschlüssel empfangen; eindeutige Hostadresse verwenden"
    );
    Ok(Scanned {
        host,
        lines,
        fingerprint: values[0].into(),
    })
}
pub async fn accept(scanned: &Scanned, independently_verified: &str) -> Result<()> {
    ensure!(
        independently_verified.trim() == scanned.fingerprint,
        "Fingerabdruck stimmt nicht überein. Nichts gespeichert."
    );
    let file = known_hosts()?;
    let mut target = OpenOptions::new()
        .create(true)
        .append(true)
        .read(true)
        .mode(0o600)
        .open(&file)?;
    target
        .try_lock()
        .context("Die Hostschlüsseldatei wird gerade verwendet")?;
    ensure!(
        !existing(&scanned.host, &file).await?,
        "Hostschlüssel wurde zwischenzeitlich hinterlegt. Nichts ersetzt."
    );
    target.set_permissions(fs::Permissions::from_mode(0o600))?;
    // A leading newline preserves a pre-existing final line without a newline.
    target.write_all(b"\n")?;
    target.write_all(&scanned.lines)?;
    target.sync_all()?;
    Ok(())
}
pub fn generate_arguments() -> Result<Vec<OsString>> {
    let key = key_path()?;
    ensure!(
        !key.exists() && !key.with_extension("pub").exists(),
        "Ein Rampi-Schlüssel ist bereits vorhanden. Er wird nicht überschrieben."
    );
    Ok(vec![
        "ssh-keygen".into(),
        "-t".into(),
        "ed25519".into(),
        "-a".into(),
        "64".into(),
        "-f".into(),
        key.into_os_string(),
        "-C".into(),
        "Rampi".into(),
    ])
}

pub fn unlock_arguments(identity: &str) -> Result<Vec<OsString>> {
    ensure!(
        !identity.is_empty(),
        "Zuerst einen persönlichen SSH-Schlüssel im Hostprofil auswählen und speichern"
    );
    ensure!(
        std::env::var_os("SSH_AUTH_SOCK").is_some(),
        "Kein OpenSSH-Agent verfügbar. Rampi-Sitzung neu anmelden."
    );
    let path = config::expand_home(identity)?;
    let metadata = fs::symlink_metadata(&path)?;
    ensure!(
        metadata.is_file()
            && !metadata.file_type().is_symlink()
            && metadata.uid() == gio::Credentials::new().unix_user()?
            && metadata.mode() & 0o077 == 0,
        "Der private Schlüssel muss dir gehören und darf nur für dein Konto lesbar sein"
    );
    // Keep the official passphrase prompt inside VTE, even if a parent desktop
    // supplied an external askpass application.
    Ok(vec![
        "/usr/bin/env".into(),
        "SSH_ASKPASS_REQUIRE=never".into(),
        "/usr/bin/ssh-add".into(),
        "--".into(),
        path.into_os_string(),
    ])
}
