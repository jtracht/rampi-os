//! Actual Secret Service, HTTPS transport and provider response acceptance.
use anyhow::{Context, Result, ensure};
use glib::variant::ToVariant;
use gtk::{gio, glib, prelude::*};
use rampi_core::config::Settings;
fn isolated() -> Result<()> {
    ensure!(
        std::env::var("RAMPI_TEST_CONTAINER").as_deref() == Ok("1")
            && std::path::Path::new("/.dockerenv").exists(),
        "Disposable cloud test container required"
    );
    Ok(())
}
fn credentials() -> Result<serde_json::Value> {
    Ok(serde_json::from_slice(&std::fs::read(std::env::var(
        "RAMPI_TEST_CLOUD_FILE",
    )?)?)?)
}
pub fn run() -> Result<()> {
    isolated()?;
    glib::MainContext::default().block_on(async {
        let credentials = credentials()?;
        let cases = [
            ("github", "organization/fixture/1", 2),
            (
                "gitea",
                "https://gitea.fixture.test#repos/fixture/repo/1",
                2,
            ),
            ("trello", "board1", 1001),
            ("jira", "https://fixture.atlassian.net#RAMPI", 2),
            ("asana", "42", 2),
            ("notion", "0123456789abcdef0123456789abcdef", 2), // pragma: allowlist secret - synthetic Notion data source ID
        ];
        for (kind, source, count) in cases {
            let profile = format!("native-{kind}");
            let token = credentials[kind]["token"]
                .as_str()
                .context("Fixture token missing")?;
            let account = credentials[kind]["account"].as_str().unwrap_or("");
            crate::secret_service::store(&profile, kind, source, account, token).await?;
            let secret = crate::secret_service::load(&profile, kind, source).await?;
            ensure!(secret.contains(token), "Actual keyring roundtrip failed");
            let settings = Settings {
                board_kind: kind.into(),
                board_source: source.into(),
                board_token_key: profile,
                ..Default::default()
            };
            let loaded = crate::board_data::load(settings.clone()).await?;
            ensure!(
                !loaded.cached && loaded.board.cards.len() == count,
                "Wrong provider data: {kind}"
            );
            ensure!(
                loaded.board.cards[0].title == format!("{kind} first"),
                "Provider title lost: {kind}"
            );
            if kind == "gitea" {
                ensure!(
                    loaded.board.columns == ["Review", "Empty"]
                        && loaded.board.cards.iter().all(|c| c.status == "Review"),
                    "Gitea project columns or empty columns lost"
                );
            }
            if kind == "asana" {
                ensure!(
                    loaded.board.cards[0].status == "Review"
                        && loaded.board.cards[1].status == "Erledigt",
                    "Asana used another project's section"
                );
            }
            if kind == "trello" {
                ensure!(
                    loaded.board.columns == ["Review", "Empty"],
                    "Empty provider column lost"
                );
            }
            if kind == "jira" {
                ensure!(
                    loaded.board.cards[0].description == "AlphaBeta",
                    "Jira inline document text changed"
                );
            }
            let control = std::path::PathBuf::from(std::env::var("RAMPI_TEST_CLOUD_CONTROL")?)
                .join("offline");
            std::fs::write(&control, "offline")?;
            let offline = crate::board_data::load(settings.clone()).await?;
            ensure!(
                offline.cached && offline.board.cards.len() == count,
                "Private offline cache missing: {kind}"
            );
            let preview = crate::board_data::preview(settings.clone()).await?;
            ensure!(
                preview.cards.len() == count,
                "Dashboard did not use persistent cache"
            );
            let foreign = Settings {
                board_token_key: "another-profile".into(),
                ..settings
            };
            ensure!(
                crate::board_data::load(foreign).await.is_err(),
                "Cache crossed credential profile boundary"
            );
            std::fs::remove_file(&control)?;
        }
        crate::secret_service::store(
            "native-jira-oauth",
            "jira",
            "https://api.atlassian.com/ex/jira/01234567-89ab-cdef-0123-456789abcdef#RAMPI",
            "",
            credentials["jira"]["token"].as_str().unwrap(),
        )
        .await?;
        let oauth = Settings {
            board_kind: "jira".into(),
            board_source:
                "https://api.atlassian.com/ex/jira/01234567-89ab-cdef-0123-456789abcdef#RAMPI"
                    .into(),
            board_token_key: "native-jira-oauth".into(),
            ..Default::default()
        };
        ensure!(
            crate::board_data::load(oauth).await?.board.cards.len() == 2,
            "Jira OAuth transport failed"
        );
        // Errors cannot commit partial data or forward a token to another host.
        for (number, expected) in [
            (2, "GitHub"),
            (3, "Paginierung"),
            (4, "HTTP 302"),
            (5, "Antwort"),
            (6, "HTTP 401"),
        ] {
            let settings = Settings {
                board_kind: "github".into(),
                board_source: format!("organization/fixture/{number}"),
                board_token_key: "native-github".into(),
                ..Default::default()
            };
            crate::secret_service::store(
                "native-github",
                "github",
                &settings.board_source,
                "",
                credentials["github"]["token"].as_str().unwrap(),
            )
            .await?;
            let error = crate::board_data::load(settings)
                .await
                .err()
                .context("Invalid provider response accepted")?;
            ensure!(
                error.to_string().contains(expected),
                "Provider failure was not classified: {number}: {error}"
            );
        }
        ensure!(
            crate::secret_service::load(
                "native-gitea",
                "gitea",
                "https://other.invalid#repos/fixture/repo/1"
            )
            .await
            .is_err(),
            "Gitea token crossed server origin"
        );
        ensure!(
            crate::secret_service::load(
                "native-github",
                "gitea",
                "https://gitea.fixture.test#repos/fixture/repo/1"
            )
            .await
            .is_err(),
            "Token crossed provider boundary"
        );
        // Reject a symlink before creating anything inside its target.
        let cache_root = glib::user_cache_dir().join("rampi");
        let backup = glib::user_cache_dir().join("rampi-verified-backup");
        std::fs::rename(&cache_root, &backup)?;
        let outside = tempfile::TempDir::new()?;
        std::os::unix::fs::symlink(outside.path(), &cache_root)?;
        let probe = Settings {
            board_kind: "gitea".into(),
            board_source: "https://gitea.fixture.test#repos/fixture/repo/1".into(),
            board_token_key: "native-gitea".into(),
            ..Default::default()
        };
        let rejected = crate::board_data::preview(probe).await.is_err();
        let untouched = !outside.path().join("boards").exists();
        std::fs::remove_file(&cache_root)?;
        std::fs::rename(backup, cache_root)?;
        ensure!(
            rejected && untouched,
            "Cache symlink mutated another directory"
        );
        // A locked collection must fail without ever invoking a GUI Prompt.
        let bus = gio::bus_get_future(gio::BusType::Session).await?;
        let root = "/org/freedesktop/secrets";
        let iface = "org.freedesktop.Secret.Service";
        let collection = bus
            .call_future(
                Some("org.freedesktop.secrets"),
                root,
                iface,
                "ReadAlias",
                Some(&("default",).to_variant()),
                None,
                gio::DBusCallFlags::NONE,
                5000,
            )
            .await?
            .child_value(0)
            .get::<glib::variant::ObjectPath>()
            .context("No default collection")?;
        bus.call_future(
            Some("org.freedesktop.secrets"),
            root,
            iface,
            "Lock",
            Some(&(vec![collection],).to_variant()),
            None,
            gio::DBusCallFlags::NONE,
            5000,
        )
        .await?;
        ensure!(
            crate::secret_service::load("native-github", "github", "organization/fixture/1")
                .await
                .is_err(),
            "Locked keyring was read"
        );
        ensure!(
            crate::secret_service::store(
                "native-github",
                "github",
                "organization/fixture/1",
                "",
                "replacement"
            )
            .await
            .is_err(),
            "Locked keyring was written"
        );
        let files = std::fs::read_dir(glib::user_cache_dir().join("rampi/boards"))?;
        use std::os::unix::fs::PermissionsExt;
        for file in files {
            let file = file?.path();
            ensure!(
                std::fs::metadata(&file)?.permissions().mode() & 0o777 == 0o600,
                "Cache permissions are not private"
            );
            let body = std::fs::read_to_string(file)?;
            for kind in ["github", "trello", "jira", "asana", "notion", "gitea"] {
                ensure!(
                    !body.contains(credentials[kind]["token"].as_str().unwrap()),
                    "Credential leaked into normalized cache"
                );
            }
        }
        println!("RAMPI_RUST_CLOUD_KANBAN_TLS_KEYRING_OK");
        Ok(())
    })
}
pub fn ui(
    app: &gtk::Application,
    stack: &gtk::Stack,
    tabs: &gtk::Stack,
    conf: &crate::widgets::Shared,
) {
    isolated().unwrap();
    let (app, stack, tabs, conf) = (app.clone(), stack.clone(), tabs.clone(), conf.clone());
    glib::MainContext::default().spawn_local(async move {
        let result: Result<()> = async {
            use crate::checks::{find_button, named};
            let credentials = credentials()?;
            let token = credentials["github"]["token"].as_str().unwrap();
            stack.set_visible_child_name("settings");
            tabs.set_visible_child_name("board");
            let page = tabs.child_by_name("board").unwrap();
            named(&page, "board-kind")
                .unwrap()
                .downcast::<gtk::DropDown>()
                .unwrap()
                .set_selected(1);
            for (id, value) in [
                ("board-source", "organization/fixture/1"),
                ("board-token-profile", "native-ui"),
            ] {
                named(&page, id)
                    .unwrap()
                    .downcast::<gtk::Entry>()
                    .unwrap()
                    .set_text(value);
            }
            let input = named(&page, "board-token-input")
                .unwrap()
                .downcast::<gtk::PasswordEntry>()
                .unwrap();
            input.set_text(token);
            let save = find_button(&page, "Zugangsdaten im Schlüsselbund speichern").unwrap();
            save.emit_clicked();
            for _ in 0..300 {
                if save.is_sensitive() {
                    break;
                }
                glib::timeout_future(std::time::Duration::from_millis(20)).await;
            }
            ensure!(
                input.text().is_empty()
                    && crate::secret_service::load("native-ui", "github", "organization/fixture/1")
                        .await?
                        == token,
                "UI did not store the actual keyring secret"
            );
            find_button(&page, "Datenquelle und Startseite speichern")
                .unwrap()
                .emit_clicked();
            ensure!(
                conf.borrow().board_kind == "github"
                    && conf.borrow().board_token_key == "native-ui",
                "Provider configuration not saved"
            );
            stack.set_visible_child_name("kanban");
            let board = stack.child_by_name("kanban").unwrap();
            let summary = named(&board, "board-result")
                .unwrap()
                .downcast::<gtk::Label>()
                .unwrap();
            for _ in 0..400 {
                if summary.text().starts_with("2 von 2") {
                    break;
                }
                glib::timeout_future(std::time::Duration::from_millis(20)).await;
            }
            ensure!(
                summary.text().starts_with("2 von 2"),
                "Actual GTK cloud board did not load: {}",
                summary.text()
            );
            ensure!(
                app.windows().len() == 1,
                "Cloud setup opened an external window"
            );
            // The requested Gitea path uses the same real page and keyring.
            stack.set_visible_child_name("settings");
            tabs.set_visible_child_name("board");
            named(&page, "board-kind")
                .unwrap()
                .downcast::<gtk::DropDown>()
                .unwrap()
                .set_selected(6);
            let hint = named(&page, "board-source-hint")
                .unwrap()
                .downcast::<gtk::Label>()
                .unwrap();
            ensure!(
                hint.text().contains("Gitea") && !hint.text().contains("Asana"),
                "Provider guidance is not contextual"
            );
            for (id, value) in [
                (
                    "board-source",
                    "https://gitea.fixture.test/fixture/repo/projects/1",
                ),
                ("board-token-profile", "native-ui-gitea"),
            ] {
                named(&page, id)
                    .unwrap()
                    .downcast::<gtk::Entry>()
                    .unwrap()
                    .set_text(value);
            }
            input.set_text(credentials["gitea"]["token"].as_str().unwrap());
            save.emit_clicked();
            for _ in 0..300 {
                if save.is_sensitive() {
                    break;
                }
                glib::timeout_future(std::time::Duration::from_millis(20)).await;
            }
            ensure!(input.text().is_empty(), "Gitea token retained in form");
            find_button(&page, "Datenquelle und Startseite speichern")
                .unwrap()
                .emit_clicked();
            ensure!(
                conf.borrow().board_kind == "gitea",
                "Gitea configuration did not persist"
            );
            find_button(&page, "Board öffnen →").unwrap().emit_clicked();
            for _ in 0..400 {
                if summary.text().contains("Gitea fixture") {
                    break;
                }
                glib::timeout_future(std::time::Duration::from_millis(20)).await;
            }
            ensure!(
                summary.text().starts_with("2 von 2") && summary.text().contains("Gitea fixture"),
                "Actual Gitea board page did not load"
            );
            ensure!(app.windows().len() == 1, "Gitea opened another window");
            println!("RAMPI_RUST_CLOUD_KANBAN_PAGE_OK");
            Ok(())
        }
        .await;
        if let Err(error) = result {
            eprintln!("Cloud Kanban UI check failed: {error:#}");
            std::process::exit(1);
        }
        app.quit();
    });
}
