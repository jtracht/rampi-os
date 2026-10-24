//! UI contract checks. Windows process persistence is tested separately on Windows.
use crate::{
    checks::{find_button, named},
    widgets::*,
};
use anyhow::{Context, ensure};
use gtk::{glib, prelude::*};
use std::{path::PathBuf, time::Duration};

pub fn run(app: &gtk::Application, stack: &gtk::Stack, conf: &Shared, feedback: &Feedback) {
    assert_eq!(std::env::var("RAMPI_TEST_CONTAINER").as_deref(), Ok("1"));
    let (app, stack, conf, feedback) = (app.clone(), stack.clone(), conf.clone(), feedback.clone());
    glib::MainContext::default().spawn_local(async move {
        let result: anyhow::Result<()> = async {
            let fixture = PathBuf::from(std::env::var("RAMPI_TEST_AI_STATE")?);
            let status = label("");
            conf.borrow_mut().hosts.clear();
            crate::ai_view::open(&stack, &conf, "codex", &status, &feedback);
            let page = stack.visible_child().context("Missing AI page")?;
            let check = named(&page, "ai-check")
                .unwrap()
                .downcast::<gtk::Button>()
                .unwrap();
            check.emit_clicked();
            let output = named(&page, "ai-session-status")
                .unwrap()
                .downcast::<gtk::Label>()
                .unwrap();
            ensure!(!check.is_sensitive() || !output.text().contains("wird über OpenSSH geprüft"));
            conf.borrow_mut().hosts = vec![rampi_core::config::Host {
                name: "Provider contract host".into(),
                address: "windows.example".into(),
                username: "alice".into(),
                project: "C:\\Work\\O'Brien".into(),
                ..Default::default()
            }];
            conf.borrow_mut().active_host = 0;
            for module in rampi_core::launch::MODULES {
                std::fs::write(&fixture, "running")?;
                crate::ai_view::open(&stack, &conf, module, &status, &feedback);
                let page = stack.visible_child().context("Missing module page")?;
                let check = named(&page, "ai-check")
                    .unwrap()
                    .downcast::<gtk::Button>()
                    .unwrap();
                let output = named(&page, "ai-session-status")
                    .unwrap()
                    .downcast::<gtk::Label>()
                    .unwrap();
                check.emit_clicked();
                wait(&check).await?;
                ensure!(
                    output.text().contains("alice@windows.example")
                        && output.text().contains("Anbieteranmeldung bleibt ungeprüft"),
                    "False auth claim: {}",
                    output.text()
                );
                ensure!(output.text().contains(if module == "antigravity" {
                    "CLI: fehlt"
                } else {
                    "CLI: vorhanden"
                }));
                ensure!(output.text().contains("läuft auf Windows"));
                if let Ok(directory) = std::env::var("RAMPI_TEST_ARTIFACTS") {
                    glib::timeout_future(Duration::from_millis(250)).await;
                    let path = PathBuf::from(directory).join(format!("ai-session-{module}.png"));
                    let (ok, _) =
                        crate::process::output("grim", &[path.clone().into_os_string()], 5, 1024)
                            .await?;
                    ensure!(ok, "Actual compositor capture failed");
                    use std::os::unix::fs::PermissionsExt;
                    std::fs::set_permissions(path, std::fs::Permissions::from_mode(0o644))?;
                }
                named(&page, "ai-stop")
                    .unwrap()
                    .downcast::<gtk::Button>()
                    .unwrap()
                    .emit_clicked();
                ensure!(stack.visible_child_name().as_deref() == Some("confirmation"));
                let confirm = stack.visible_child().unwrap();
                find_button(&confirm, "Abbrechen").unwrap().emit_clicked();
                ensure!(
                    std::fs::read_to_string(&fixture)? == "running",
                    "Cancel stopped the session"
                );
                named(&page, "ai-stop")
                    .unwrap()
                    .downcast::<gtk::Button>()
                    .unwrap()
                    .emit_clicked();
                let confirm = stack.visible_child().unwrap();
                find_button(&confirm, "Bewusst bestätigen")
                    .unwrap()
                    .emit_clicked();
                for _ in 0..200 {
                    if output.text().starts_with("Windows-Sitzung beendet.") {
                        break;
                    }
                    glib::timeout_future(Duration::from_millis(10)).await;
                }
                ensure!(
                    output.text().starts_with("Windows-Sitzung beendet."),
                    "Stop failed: {}",
                    output.text()
                );
                check.emit_clicked();
                wait(&check).await?;
                ensure!(output.text().contains("Sitzung: nicht gestartet"));
                std::fs::write(&fixture, "malformed")?;
                check.emit_clicked();
                wait(&check).await?;
                ensure!(
                    !output.text().contains("CLI: vorhanden")
                        && !output.text().contains("läuft auf Windows")
                );
                std::fs::write(&fixture, "denied")?;
                check.emit_clicked();
                wait(&check).await?;
                ensure!(output.text().contains("Windows-Prüfung fehlgeschlagen"));
                ensure!(app.windows().len() == 1);
            }
            println!("RAMPI_RUST_AI_SESSION_PAGES_OK");
            Ok(())
        }
        .await;
        if let Err(error) = result {
            eprintln!("AI page contract failed: {error:#}");
            std::process::exit(1);
        }
        app.quit();
    });
}
async fn wait(button: &gtk::Button) -> anyhow::Result<()> {
    for _ in 0..200 {
        if button.is_sensitive() {
            return Ok(());
        }
        glib::timeout_future(Duration::from_millis(10)).await;
    }
    anyhow::bail!("AI check did not complete")
}
