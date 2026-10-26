use anyhow::{Context, Result, ensure};
use serde::{Deserialize, Serialize};
use std::{
    env, fs,
    io::Write,
    path::{Path, PathBuf},
};

// Keep IDs written by published versions stable; removed steps are skipped.
pub const SETUP_STEP_IDS: [usize; 12] = [0, 1, 2, 3, 4, 5, 6, 7, 11, 12, 13, 14];

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct Host {
    pub name: String,
    pub address: String,
    pub username: String,
    pub port: u16,
    pub identity: String,
    pub project: String,
    pub resolution: String,
}
impl Default for Host {
    fn default() -> Self {
        Self {
            name: "Windows".into(),
            address: String::new(),
            username: String::new(),
            port: 22,
            identity: String::new(),
            project: String::new(),
            resolution: "1280x720".into(),
        }
    }
}
impl Host {
    pub fn validate(&self) -> Result<()> {
        ensure!(
            !self.name.trim().is_empty()
                && self.name.chars().count() <= 80
                && !self.name.chars().any(char::is_control),
            "Ungültiger Profilname"
        );
        ensure!(
            !self.address.is_empty()
                && self.address.len() <= 253
                && self
                    .address
                    .bytes()
                    .next()
                    .is_some_and(|c| c.is_ascii_alphanumeric())
                && self
                    .address
                    .bytes()
                    .all(|c| c.is_ascii_alphanumeric() || b".:-".contains(&c)),
            "Ungültiger Hostname oder IP-Adresse"
        );
        ensure!(
            !self.username.is_empty()
                && self.username.len() <= 128
                && !self.username.starts_with('-')
                && self
                    .username
                    .bytes()
                    .all(|c| c.is_ascii_alphanumeric() || b"_.@\\-".contains(&c)),
            "Ungültiger Windows-Benutzername"
        );
        ensure!(self.port > 0, "Ungültiger SSH-Port");
        ensure!(
            !self.project.chars().any(|c| c.is_control()),
            "Ungültiges Projektverzeichnis"
        );
        if !self.identity.is_empty() {
            ensure!(
                expand_home(&self.identity)?.is_file(),
                "SSH-Schlüssel existiert nicht"
            );
        }
        let (w, h) = self
            .resolution
            .split_once('x')
            .context("Ungültige Auflösung")?;
        let (w, h) = (w.parse::<u32>()?, h.parse::<u32>()?);
        ensure!(
            (320..=7680).contains(&w) && (240..=4320).contains(&h),
            "Ungültige Auflösung"
        );
        Ok(())
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct Settings {
    pub language: String,
    pub setup_complete: bool,
    pub setup_step: usize,
    pub active_host: usize,
    pub hosts: Vec<Host>,
    pub browser_url: String,
    pub board_source: String,
    pub board_kind: String,
    pub board_token_key: String,
    pub board_columns: Vec<String>,
    pub reduce_motion: bool,
    pub sound_effects: bool,
}
impl Default for Settings {
    fn default() -> Self {
        Self {
            language: "de".into(),
            setup_complete: false,
            setup_step: 0,
            active_host: 0,
            hosts: vec![],
            browser_url: "https://www.raspberrypi.com".into(),
            board_source: String::new(),
            board_kind: "json".into(),
            board_token_key: String::new(),
            board_columns: vec![],
            reduce_motion: false,
            sound_effects: true,
        }
    }
}
pub fn config_dir() -> Result<PathBuf> {
    Ok(env::var_os("XDG_CONFIG_HOME")
        .map(PathBuf::from)
        .unwrap_or(home()?.join(".config"))
        .join("rampi"))
}
pub fn home() -> Result<PathBuf> {
    env::var_os(if cfg!(windows) { "USERPROFILE" } else { "HOME" })
        .map(PathBuf::from)
        .context("Persönliches Benutzerverzeichnis fehlt")
}
pub fn expand_home(value: &str) -> Result<PathBuf> {
    Ok(if let Some(rest) = value.strip_prefix("~/") {
        home()?.join(rest)
    } else {
        PathBuf::from(value)
    })
}
pub fn validate_https(value: &str) -> Result<()> {
    let authority = value
        .strip_prefix("https://")
        .context("Bitte eine HTTPS-Adresse verwenden")?
        .split('/')
        .next()
        .unwrap_or("");
    ensure!(
        !authority.is_empty()
            && !authority.contains('@')
            && !value
                .chars()
                .any(|c| c.is_control() || c.is_whitespace() || c == '\\'),
        "Ungültige HTTPS-Adresse oder eingebettete Zugangsdaten"
    );
    Ok(())
}
impl Settings {
    pub fn setup_index(&self) -> usize {
        SETUP_STEP_IDS
            .iter()
            .position(|id| *id >= self.setup_step)
            .unwrap_or(SETUP_STEP_IDS.len() - 1)
    }
    pub fn host(&self) -> Result<&Host> {
        let h = self
            .hosts
            .get(self.active_host)
            .context("Zuerst einen Windows-Host einrichten")?;
        h.validate()?;
        Ok(h)
    }
    pub fn validate(&self) -> Result<()> {
        ensure!(
            crate::i18n::locale(&self.language).is_some(),
            "Unbekannte Sprache"
        );
        ensure!(self.setup_step < 15, "Ungültiger Einrichtungsschritt");
        ensure!(self.hosts.len() <= 64, "Zu viele Hostprofile");
        validate_https(&self.browser_url)?;
        ensure!(
            [
                "json", "github", "trello", "jira", "asana", "notion", "gitea"
            ]
            .contains(&self.board_kind.as_str()),
            "Unbekannter Kanban-Anbieter"
        );
        ensure!(self.board_columns.len() <= 32, "Zu viele Kanban-Spalten");
        let mut seen = std::collections::HashSet::new();
        for column in &self.board_columns {
            ensure!(
                !column.is_empty()
                    && column.trim() == column
                    && column.chars().count() <= 80
                    && !column.chars().any(char::is_control)
                    && seen.insert(column),
                "Ungültige oder doppelte Kanban-Spalte"
            );
        }
        for host in &self.hosts {
            host.validate()?;
        }
        if !self.hosts.is_empty() {
            self.host()?;
        }
        Ok(())
    }
    pub fn load(path: &Path) -> Result<Self> {
        if !path.exists() {
            return Ok(Self::default());
        }
        ensure!(
            fs::metadata(path)?.len() < 1_048_576,
            "Konfigurationsdatei ist zu groß"
        );
        let settings: Self = serde_json::from_slice(&fs::read(path)?)?;
        settings.validate()?;
        Ok(settings)
    }
    pub fn save(&self, path: &Path) -> Result<()> {
        self.validate()?;
        if path.try_exists()? {
            Self::load(path).context("Vorhandene Konfiguration ist fehlerhaft. Datei zuerst sichern und korrigieren; sie wurde nicht überschrieben")?;
        }
        let dir = path.parent().context("Konfigurationsordner fehlt")?;
        fs::create_dir_all(dir)?;
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            fs::set_permissions(dir, fs::Permissions::from_mode(0o700))?;
        }
        let mut temp = tempfile::NamedTempFile::new_in(dir)?;
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            temp.as_file()
                .set_permissions(fs::Permissions::from_mode(0o600))?;
        }
        temp.write_all(&serde_json::to_vec_pretty(self)?)?;
        temp.write_all(b"\n")?;
        temp.as_file().sync_all()?;
        temp.persist(path)?;
        #[cfg(unix)]
        fs::File::open(dir)?.sync_all()?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn unsafe_host_is_rejected() {
        let h = Host {
            address: "-oProxyCommand=bad".into(),
            username: "user".into(),
            ..Default::default()
        };
        assert!(h.validate().is_err());
    }
    #[test]
    fn credentials_are_not_urls() {
        for value in [
            "http://example.com",
            "https://user:secret@example.com", // pragma: allowlist secret - deliberately invalid test URL
            "https://example.com\n",
        ] {
            assert!(validate_https(value).is_err());
        }
    }
    #[test]
    fn existing_python_settings_are_compatible() {
        let value = r#"{"language":"de","hosts":[],"board_kind":"json","board_columns":["Review","Offen"],"reduce_motion":true}"#;
        let settings: Settings = serde_json::from_str(value).unwrap();
        settings.validate().unwrap();
        assert!(settings.reduce_motion && settings.sound_effects);
    }
    #[test]
    fn unknown_fields_and_duplicate_columns_fail() {
        assert!(serde_json::from_str::<Settings>(r#"{"password":"secret"}"#).is_err()); // pragma: allowlist secret - dummy rejected configuration
        let s = Settings {
            board_columns: vec!["Offen".into(), "Offen".into()],
            ..Default::default()
        };
        assert!(s.validate().is_err());
    }
    #[test]
    fn personal_settings_roundtrip() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("private/settings.json");
        Settings::default().save(&path).unwrap();
        assert_eq!(Settings::load(&path).unwrap().language, "de");
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            assert_eq!(
                fs::metadata(path).unwrap().permissions().mode() & 0o777,
                0o600
            );
        }
    }
    #[test]
    fn malformed_existing_configuration_is_preserved() {
        let directory = tempfile::tempdir().unwrap();
        let path = directory.path().join("settings.json");
        let original = b"{broken personal configuration";
        fs::write(&path, original).unwrap();
        assert!(Settings::default().save(&path).is_err());
        assert_eq!(fs::read(path).unwrap(), original);
    }

    #[test]
    fn multiple_hosts_and_setup_resume() {
        let directory = tempfile::tempdir().unwrap();
        let path = directory.path().join("settings.json");
        let mut settings = Settings {
            setup_step: 7,
            active_host: 1,
            hosts: vec![
                Host {
                    address: "first.example".into(),
                    username: "alice".into(),
                    ..Host::default()
                },
                Host {
                    name: "Laptop".into(),
                    address: "second.example".into(),
                    username: "bob".into(),
                    port: 2222,
                    ..Host::default()
                },
            ],
            ..Settings::default()
        };
        settings.save(&path).unwrap();
        let loaded = Settings::load(&path).unwrap();
        assert_eq!(loaded.setup_step, 7);
        assert!(!loaded.setup_complete);
        assert_eq!(loaded.host().unwrap().username, "bob");
        settings.setup_step = 15;
        assert!(settings.save(&path).is_err());
        assert_eq!(Settings::load(&path).unwrap().setup_step, 7);
        settings.setup_step = 0;
        settings.active_host = 2;
        assert!(settings.validate().is_err());
    }

    #[test]
    fn published_setup_progress_survives_removed_provider_steps() {
        let directory = tempfile::tempdir().unwrap();
        let path = directory.path().join("settings.json");
        for (old_id, expected_position, expected_next_id) in [
            (7, 7, 11),
            (8, 8, 12),
            (9, 8, 12),
            (10, 8, 12),
            (11, 8, 12),
            (12, 9, 13),
            (13, 10, 14),
            (14, 11, 14),
        ] {
            let original = serde_json::to_vec(&serde_json::json!({
                "setup_step": old_id,
                "hosts": [{"address": "host.example", "username": "alice", "project": "C:\\Personal"}]
            })).unwrap();
            fs::write(&path, &original).unwrap();
            let mut settings = Settings::load(&path).unwrap();
            assert_eq!(settings.setup_step, old_id);
            assert_eq!(settings.setup_index(), expected_position);
            assert_eq!(
                fs::read(&path).unwrap(),
                original,
                "Loading rewrote personal data"
            );
            settings.setup_step =
                SETUP_STEP_IDS[(settings.setup_index() + 1).min(SETUP_STEP_IDS.len() - 1)];
            settings.save(&path).unwrap();
            let saved = Settings::load(&path).unwrap();
            assert_eq!(saved.setup_step, expected_next_id);
            assert_eq!(saved.host().unwrap().project, "C:\\Personal");
            assert!(!saved.setup_complete);
        }
    }
}
