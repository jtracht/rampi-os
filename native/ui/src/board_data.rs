//! Existing curl/Secret Service transport and a private normalized offline cache.
use anyhow::{Context, Result, ensure};
use gtk::{gio, glib};
use rampi_core::{
    board::Board,
    config::Settings,
    connectors::{Connector, Request},
};
use std::{
    io::Write,
    os::unix::fs::{MetadataExt, PermissionsExt},
    path::PathBuf,
};
pub struct Loaded {
    pub board: Board,
    pub cached: bool,
}
pub fn key(settings: &Settings) -> String {
    serde_json::to_string(&(
        &settings.board_kind,
        &settings.board_source,
        &settings.board_token_key,
    ))
    .expect("String tuple serialization")
}
fn cache(settings: &Settings) -> Result<PathBuf> {
    let root = glib::user_cache_dir().join("rampi");
    let folder = root.join("boards");
    std::fs::create_dir_all(glib::user_cache_dir())?;
    let uid = gio::Credentials::new().unix_user()?;
    for dir in [&root, &folder] {
        match std::fs::symlink_metadata(dir) {
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => std::fs::create_dir(dir)?,
            Err(e) => return Err(e.into()),
            Ok(_) => (),
        }
        let meta = std::fs::symlink_metadata(dir)?;
        ensure!(
            meta.is_dir() && !meta.file_type().is_symlink() && meta.uid() == uid,
            "Unsicherer persönlicher Kanban-Cache"
        );
        std::fs::set_permissions(dir, std::fs::Permissions::from_mode(0o700))?;
    }
    let bytes = serde_json::to_vec(&(
        &settings.board_kind,
        &settings.board_source,
        &settings.board_token_key,
    ))?;
    let digest = glib::compute_checksum_for_data(glib::ChecksumType::Sha256, &bytes)
        .context("Cache-Kennung fehlt")?;
    Ok(folder.join(format!("{digest}.json")))
}
fn read_cache(settings: &Settings) -> Result<Board> {
    let file = cache(settings)?;
    let meta = std::fs::symlink_metadata(&file)?;
    ensure!(
        meta.is_file()
            && !meta.file_type().is_symlink()
            && meta.uid() == gio::Credentials::new().unix_user()?
            && meta.permissions().mode() & 0o077 == 0,
        "Unsichere persönliche Cache-Datei"
    );
    Board::load(&file)
}
fn store_cache(settings: &Settings, board: &Board) -> Result<()> {
    board.validate()?;
    let path = cache(settings)?;
    let dir = path.parent().context("Cache-Verzeichnis fehlt")?;
    let mut temp = tempfile::NamedTempFile::new_in(dir)?;
    temp.as_file()
        .set_permissions(std::fs::Permissions::from_mode(0o600))?;
    temp.write_all(&serde_json::to_vec(board)?)?;
    temp.as_file().sync_all()?;
    temp.persist(&path)?;
    std::fs::File::open(dir)?.sync_all()?;
    Ok(())
}
fn quoted(value: &str) -> Result<String> {
    ensure!(
        !value.chars().any(char::is_control),
        "Ungültiger API-Parameter"
    );
    Ok(format!(
        "\"{}\"",
        value.replace('\\', "\\\\").replace('"', "\\\"")
    ))
}
pub async fn request(request: Request) -> Result<serde_json::Value> {
    rampi_core::config::validate_https(&request.url)?;
    let mut config = format!("url = {}\n", quoted(&request.url)?);
    for (name, value) in request.headers {
        ensure!(
            name.bytes().all(|c| c.is_ascii_alphanumeric() || c == b'-'),
            "Ungültiger API-Header"
        );
        config.push_str(&format!(
            "header = {}\n",
            quoted(&format!("{name}: {value}"))?
        ));
    }
    if let Some(body) = request.body {
        config.push_str("header = \"Content-Type: application/json\"\n");
        config.push_str(&format!("data = {}\n", quoted(&body.to_string())?));
    }
    let mut args = vec![
        "--disable".into(),
        "--config".into(),
        "-".into(),
        "--silent".into(),
        "--globoff".into(),
        "--proto".into(),
        "=https".into(),
        "--disallow-username-in-url".into(),
        "--max-time".into(),
        "20".into(),
        "--connect-timeout".into(),
        "5".into(),
        "--max-filesize".into(),
        "4194304".into(),
        "--write-out".into(),
        "\n%{http_code}".into(),
    ];
    // Test DNS routes retain the actual provider URL and real certificate checks.
    // They can only address the local TLS fixture in a disposable test container.
    if std::env::var("RAMPI_TEST_CLOUD_TLS").as_deref() == Ok("1") {
        ensure!(
            std::env::var("RAMPI_TEST_CONTAINER").as_deref() == Ok("1")
                && std::path::Path::new("/.dockerenv").exists(),
            "Cloud fixture requires a disposable container"
        );
        let host = glib::Uri::parse(&request.url, glib::UriFlags::NONE)?
            .host()
            .context("API-Hostname fehlt")?;
        ensure!(
            [
                "api.github.com",
                "api.trello.com",
                "app.asana.com",
                "api.notion.com",
                "fixture.atlassian.net",
                "api.atlassian.com",
                "gitea.fixture.test"
            ]
            .contains(&host.as_str()),
            "Unbekannter Testhost"
        );
        args.extend([
            "--noproxy".into(),
            "*".into(),
            "--resolve".into(),
            format!("{host}:443:127.0.0.1").into(),
        ]);
    }
    let (ok, body) =
        crate::process::output_with_input("curl", &args, Some(config.into_bytes()), 23, 4_194_308)
            .await?;
    ensure!(
        ok,
        "Anbieter nicht erreichbar, Zertifikat ungültig oder Antwort zu groß"
    );
    let split = body
        .iter()
        .rposition(|b| *b == b'\n')
        .context("API-Status fehlt")?;
    let status = std::str::from_utf8(&body[split + 1..])?
        .parse::<u16>()
        .context("API-Status ungültig")?;
    ensure!(
        (200..300).contains(&status),
        "Anbieteranfrage fehlgeschlagen (HTTP {status}); Weiterleitungen werden nicht verfolgt"
    );
    serde_json::from_slice(&body[..split]).context("Anbieterantwort hat ein ungültiges Datenformat")
}
async fn fresh(settings: &Settings) -> Result<Board> {
    ensure!(
        !settings.board_source.is_empty(),
        "Keine Datenquelle eingerichtet"
    );
    let board = if settings.board_kind == "json" {
        let path = rampi_core::config::expand_home(&settings.board_source)?;
        gio::spawn_blocking(move || Board::load(&path))
            .await
            .map_err(|_| anyhow::anyhow!("Kanban-Datei konnte nicht geladen werden"))??
    } else {
        let token = crate::secret_service::load(
            &settings.board_token_key,
            &settings.board_kind,
            &settings.board_source,
        )
        .await?;
        let mut connector = Connector::new(&settings.board_kind, &settings.board_source, token)?;
        loop {
            let response = request(connector.request()?).await?;
            let (next, complete) = gio::spawn_blocking(move || -> Result<_> {
                let done = connector.accept(&response)?;
                Ok((connector, done))
            })
            .await
            .map_err(|_| anyhow::anyhow!("Anbieterantwort konnte nicht verarbeitet werden"))??;
            connector = next;
            if complete {
                break;
            }
        }
        connector.finish()?
    };
    let (s, b) = (settings.clone(), board.clone());
    gio::spawn_blocking(move || store_cache(&s, &b))
        .await
        .map_err(|_| anyhow::anyhow!("Cache konnte nicht gespeichert werden"))??;
    Ok(board)
}
pub async fn load(settings: Settings) -> Result<Loaded> {
    let result =
        glib::future_with_timeout(std::time::Duration::from_secs(120), fresh(&settings)).await;
    if let Ok(Ok(board)) = result {
        return Ok(Loaded {
            board,
            cached: false,
        });
    }
    let s = settings.clone();
    if let Ok(Ok(board)) = gio::spawn_blocking(move || read_cache(&s)).await {
        return Ok(Loaded {
            board,
            cached: true,
        });
    }
    match result {
        Ok(Err(e)) => Err(e),
        Err(_) => anyhow::bail!("Kanban-Aktualisierung hat nicht rechtzeitig geantwortet"),
        _ => unreachable!(),
    }
}
/// Dashboard previews never start a second cloud synchronization.
pub async fn preview(settings: Settings) -> Result<Board> {
    gio::spawn_blocking(move || {
        if settings.board_kind == "json" {
            Board::load(&rampi_core::config::expand_home(&settings.board_source)?)
        } else {
            read_cache(&settings)
        }
    })
    .await
    .map_err(|_| anyhow::anyhow!("Kanban-Vorschau nicht verfügbar"))?
}
