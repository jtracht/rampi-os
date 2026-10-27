//! Acceptance against an actual disposable Gitea, not a response fixture.
use anyhow::{Context, Result, ensure};
use gtk::{glib, prelude::*};
use std::{os::unix::fs::PermissionsExt, path::PathBuf, time::Duration};

async fn wait_for(mut condition: impl FnMut() -> bool, message: &str) -> Result<()> {
    for _ in 0..400 {
        if condition() {
            return Ok(());
        }
        glib::timeout_future(Duration::from_millis(25)).await;
    }
    anyhow::bail!("{message}")
}
async fn phase(name: &str) -> Result<()> {
    let root = PathBuf::from(std::env::var("RAMPI_TEST_ARTIFACTS")?);
    let ready = root.join(format!("gitea-{name}-ready"));
    std::fs::write(&ready, name)?;
    std::fs::set_permissions(&ready, std::fs::Permissions::from_mode(0o644))?;
    wait_for(
        || root.join(format!("gitea-{name}-continue")).is_file(),
        "Actual Gitea controller did not acknowledge phase",
    )
    .await
}
pub fn ui(
    app: &gtk::Application,
    stack: &gtk::Stack,
    pages: &gtk::Stack,
    conf: &crate::widgets::Shared,
) {
    let (app, stack, pages, conf) = (app.clone(), stack.clone(), pages.clone(), conf.clone());
    glib::MainContext::default().spawn_local(async move {
        let result: Result<()> = async {
            ensure!(
                std::env::var("RAMPI_TEST_CONTAINER").as_deref() == Ok("1")
                    && std::path::Path::new("/.dockerenv").exists(),
                "Disposable Gitea acceptance container required"
            );
            use crate::checks::{find_button, named};
            let credential: serde_json::Value =
                serde_json::from_slice(&std::fs::read(std::env::var("RAMPI_TEST_CLOUD_FILE")?)?)?;
            let source = credential["gitea"]["source"]
                .as_str()
                .context("Missing source")?;
            let token = credential["gitea"]["token"]
                .as_str()
                .context("Missing token")?;
            let title = credential["gitea"]["title"]
                .as_str()
                .context("Missing title")?;
            stack.set_visible_child_name("settings");
            pages.set_visible_child_name("board");
            let page = pages
                .child_by_name("board")
                .context("Board settings missing")?;
            {
                let choices = named(&page, "board-kind")
                    .unwrap()
                    .downcast::<gtk::ListBox>()
                    .unwrap();
                choices.select_row(choices.row_at_index(6).as_ref());
            }
            for (name, value) in [
                ("board-source", source),
                ("board-token-profile", "live-gitea"),
            ] {
                named(&page, name)
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
            wait_for(
                || save.is_sensitive() && input.text().is_empty(),
                "Gitea credential not stored",
            )
            .await?;
            ensure!(
                crate::secret_service::load("live-gitea", "gitea", source).await? == token,
                "Keyring mismatch"
            );
            find_button(&page, "Datenquelle und Startseite speichern")
                .unwrap()
                .emit_clicked();
            find_button(&page, "Board öffnen →").unwrap().emit_clicked();
            let board = stack
                .child_by_name("kanban")
                .context("Board page missing")?;
            let summary = named(&board, "board-result")
                .unwrap()
                .downcast::<gtk::Label>()
                .unwrap();
            wait_for(
                || {
                    crate::checks::readable_text(&summary.text()).starts_with("2 von 2")
                        && summary.text().contains(title)
                },
                "Actual Gitea board not loaded",
            )
            .await?;
            let settings = conf.borrow().clone();
            let loaded = crate::board_data::load(settings.clone()).await?;
            ensure!(
                !loaded.cached && loaded.board.cards.len() == 2,
                "Live Gitea data missing"
            );
            ensure!(
                loaded.board.columns.iter().any(|c| c == "Empty"),
                "Empty Gitea column lost"
            );
            ensure!(
                loaded.board.cards.iter().all(|c| c.status == "Review"),
                "Gitea project membership differs"
            );
            let scopes = credential["gitea"]["additional_projects"]
                .as_array()
                .context("Missing actual organization/user project fixtures")?;
            ensure!(scopes.len() == 2, "Incomplete Gitea scope acceptance");
            for scope in scopes {
                let source = scope["source"].as_str().context("Missing scope source")?;
                let title = scope["title"].as_str().context("Missing scope title")?;
                let kind = scope["scope"].as_str().context("Missing project scope")?;
                ensure!(["organization", "individual"].contains(&kind));
                let profile = format!("live-gitea-{kind}");
                crate::secret_service::store(&profile, "gitea", source, "fixture", token).await?;
                let mut selected = settings.clone();
                selected.board_source = source.into();
                selected.board_token_key = profile;
                let scoped = crate::board_data::load(selected).await?;
                ensure!(!scoped.cached && scoped.board.title == title);
                ensure!(scoped.board.cards.len() == 2);
                ensure!(scoped.board.columns.iter().any(|column| column == "Empty"));
                ensure!(
                    scoped
                        .board
                        .cards
                        .iter()
                        .all(|card| card.status == "Review")
                );
                ensure!(
                    crate::secret_service::load("live-gitea", "gitea", source)
                        .await
                        .is_err()
                );
            }
            println!("RAMPI_RUST_GITEA_ORG_USER_PROJECTS_OK");
            phase("refresh").await?;
            find_button(&board, "Aufgaben neu laden")
                .unwrap()
                .emit_clicked();
            let query = named(&board, "board-query")
                .unwrap()
                .downcast::<gtk::Entry>()
                .unwrap();
            query.set_text("updated");
            wait_for(
                || crate::checks::readable_text(&summary.text()).starts_with("1 von 2"),
                "Actual remote update not displayed",
            )
            .await?;
            let refreshed = crate::board_data::load(settings.clone()).await?;
            ensure!(
                refreshed
                    .board
                    .cards
                    .iter()
                    .any(|c| c.title.ends_with("updated")),
                "Server update not loaded"
            );
            phase("offline").await?;
            query.set_text("");
            find_button(&board, "Aufgaben neu laden")
                .unwrap()
                .emit_clicked();
            wait_for(
                || {
                    crate::checks::readable_text(&summary.text()).starts_with("2 von 2")
                        && summary.text().contains("Offline-Cache")
                },
                "Actual offline board not retained",
            )
            .await?;
            let foreign = rampi_core::config::Settings {
                board_token_key: "foreign-profile".into(),
                ..settings
            };
            ensure!(
                crate::board_data::load(foreign).await.is_err(),
                "Gitea cache crossed credential boundary"
            );
            ensure!(app.windows().len() == 1, "Gitea opened another window");
            // Let GTK commit the final offline label before the compositor
            // capture; the condition above checks state, not painted pixels.
            glib::timeout_future(Duration::from_millis(150)).await;
            ensure!(
                summary.text().contains("Offline-Cache"),
                "Offline status changed"
            );
            let image =
                PathBuf::from(std::env::var("RAMPI_TEST_ARTIFACTS")?).join("gitea-live.png");
            let (captured, _) = crate::process::output(
                "grim",
                &[image.to_string_lossy().into_owned().into()],
                5,
                4096,
            )
            .await?;
            ensure!(captured, "Actual Gitea capture failed");
            std::fs::set_permissions(image, std::fs::Permissions::from_mode(0o644))?;
            println!("RAMPI_RUST_GITEA_LIVE_PAGE_OK");
            Ok(())
        }
        .await;
        if let Err(error) = result {
            eprintln!("Actual Gitea acceptance failed: {error:#}");
            std::process::exit(1);
        }
        app.quit();
    });
}
