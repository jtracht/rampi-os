use anyhow::{Context, ensure};
use gtk::{glib, prelude::*};
use std::{cell::Cell, rc::Rc};
use vte::prelude::*;
async fn prompt(term: &vte::Terminal, wanted: &str) -> anyhow::Result<()> {
    for _ in 0..500 {
        if term
            .text_format(vte::Format::Text)
            .is_some_and(|s| s.contains(wanted))
        {
            return Ok(());
        }
        glib::timeout_future(std::time::Duration::from_millis(20)).await;
    }
    anyhow::bail!("Official passwd prompt not received: {wanted}")
}
pub fn creation(app: &gtk::Application, stack: &gtk::Stack, tabs: &gtk::Stack) {
    assert_eq!(std::env::var("RAMPI_TEST_CONTAINER").as_deref(), Ok("1"));
    let (app, stack, tabs) = (app.clone(), stack.clone(), tabs.clone());
    glib::MainContext::default().spawn_local(async move {
        let result: anyhow::Result<()> = async {
            use crate::checks::{find_button, named};
            ensure!(gtk::gio::Credentials::new().unix_user()? == 1000);
            let fixture: serde_json::Value =
                serde_json::from_slice(&std::fs::read(std::env::var("RAMPI_TEST_ACCOUNT_FILE")?)?)?;
            let mode = std::env::var("RAMPI_TEST_CREATE_MODE")?;
            tabs.set_visible_child_name("system");
            stack.set_visible_child_name("settings");
            find_button(
                &tabs.child_by_name("system").unwrap(),
                "Weiteres Linux-Konto einrichten",
            )
            .unwrap()
            .emit_clicked();
            let page = stack.visible_child().context("No account creation page")?;
            let entry = named(&page, "account-new-name")
                .unwrap()
                .downcast::<gtk::Entry>()
                .unwrap();
            let create = named(&page, "account-create-start")
                .unwrap()
                .downcast::<gtk::Button>()
                .unwrap();
            let password = named(&page, "account-create-password")
                .unwrap()
                .downcast::<gtk::Button>()
                .unwrap();
            let terminal = named(&page, "account-create-terminal")
                .unwrap()
                .downcast::<vte::Terminal>()
                .unwrap();
            let code = Rc::new(Cell::new(None));
            let value = code.clone();
            terminal.connect_child_exited(move |_, status| value.set(Some(status)));
            entry.set_text("root");
            create.emit_clicked();
            ensure!(stack.visible_child_name().as_deref() == Some("account-create"));
            entry.set_text("rampi-created");
            create.emit_clicked();
            find_button(&stack.visible_child().unwrap(), "Abbrechen")
                .unwrap()
                .emit_clicked();
            ensure!(create.is_sensitive() && !password.is_sensitive());
            if mode == "allowed" {
                // Existing users cannot be adopted for an administrator password reset.
                entry.set_text("rampi");
                create.emit_clicked();
                find_button(&stack.visible_child().unwrap(), "Bewusst bestätigen")
                    .unwrap()
                    .emit_clicked();
                wait_exit(&code).await?;
                ensure!(code.get() != Some(0) && !password.is_sensitive());
                ensure!(create.is_sensitive() && entry.is_sensitive());
                code.set(None);
                for name in ["rampi-unsafe", "rampi-symlink"] {
                    entry.set_text(name);
                    create.emit_clicked();
                    find_button(&stack.visible_child().unwrap(), "Bewusst bestätigen")
                        .unwrap()
                        .emit_clicked();
                    wait_exit(&code).await?;
                    ensure!(code.get() == Some(0));
                    let next = find_button(&page, "Weiteres Konto vorbereiten").unwrap();
                    for _ in 0..250 {
                        if next.is_sensitive() {
                            break;
                        }
                        glib::timeout_future(std::time::Duration::from_millis(20)).await;
                    }
                    ensure!(
                        next.is_sensitive() && !password.is_sensitive(),
                        "Unsafe existing home was adopted"
                    );
                    next.emit_clicked();
                    code.set(None);
                }
            }
            entry.set_text("rampi-created");
            create.emit_clicked();
            find_button(&stack.visible_child().unwrap(), "Bewusst bestätigen")
                .unwrap()
                .emit_clicked();
            if mode == "denied" {
                prompt(&terminal, "password for rampi:").await?;
                terminal.feed_child(
                    format!(
                        "{}\n",
                        fixture["new"]
                            .as_str()
                            .context("Missing current password")?
                    )
                    .as_bytes(),
                );
                wait_exit(&code).await?;
                ensure!(code.get() != Some(0) && create.is_sensitive() && !password.is_sensitive());
                println!("RAMPI_RUST_ACCOUNT_CREATE_DENIED_OK");
            } else {
                ensure!(mode == "allowed");
                wait_exit(&code).await?;
                for _ in 0..250 {
                    if password.is_sensitive() {
                        break;
                    }
                    glib::timeout_future(std::time::Duration::from_millis(20)).await;
                }
                ensure!(code.get() == Some(0) && password.is_sensitive() && !entry.is_sensitive());
                code.set(None);
                password.emit_clicked();
                let secret = fixture["created"]
                    .as_str()
                    .context("Missing new-account password")?;
                prompt(&terminal, "New password:").await?;
                terminal.feed_child(format!("{secret}\n").as_bytes());
                prompt(&terminal, "Retype new password:").await?;
                terminal.feed_child(format!("{secret}\n").as_bytes());
                wait_exit(&code).await?;
                ensure!(code.get() == Some(0));
                ensure!(
                    !terminal
                        .text_format(vte::Format::Text)
                        .unwrap_or_default()
                        .contains(secret)
                );
                ensure!(!password.is_sensitive());
                if let Ok(directory) = std::env::var("RAMPI_TEST_ARTIFACTS") {
                    glib::timeout_future(std::time::Duration::from_millis(200)).await;
                    let path = std::path::PathBuf::from(directory).join("account-create.png");
                    let (ok, _) =
                        crate::process::output("grim", &[path.clone().into_os_string()], 5, 1024)
                            .await?;
                    ensure!(ok);
                    use std::os::unix::fs::PermissionsExt;
                    std::fs::set_permissions(path, std::fs::Permissions::from_mode(0o644))?;
                }
                find_button(&page, "Weiteres Konto vorbereiten")
                    .unwrap()
                    .emit_clicked();
                ensure!(entry.is_sensitive() && entry.text().is_empty() && create.is_sensitive());
                println!("RAMPI_RUST_ACCOUNT_CREATE_ALLOWED_OK");
            }
            ensure!(app.windows().len() == 1);
            Ok(())
        }
        .await;
        if let Err(error) = result {
            eprintln!("Account creation acceptance failed: {error:#}");
            std::process::exit(1);
        }
        app.quit();
    });
}
async fn wait_exit(code: &Cell<Option<i32>>) -> anyhow::Result<()> {
    for _ in 0..500 {
        if code.get().is_some() {
            return Ok(());
        }
        glib::timeout_future(std::time::Duration::from_millis(20)).await;
    }
    anyhow::bail!("Account tool did not exit")
}
pub fn run(app: &gtk::Application, stack: &gtk::Stack, tabs: &gtk::Stack) {
    assert_eq!(std::env::var("RAMPI_TEST_CONTAINER").as_deref(), Ok("1"));
    let (app, stack, tabs) = (app.clone(), stack.clone(), tabs.clone());
    glib::MainContext::default().spawn_local(async move {
        let result: anyhow::Result<()> = async {
            use crate::checks::find_button;
            ensure!(
                gtk::gio::Credentials::new().unix_user()? == 1000,
                "Test must use an ordinary account"
            );
            let secrets: serde_json::Value =
                serde_json::from_slice(&std::fs::read(std::env::var("RAMPI_TEST_ACCOUNT_FILE")?)?)?;
            let old = secrets["old"]
                .as_str()
                .context("Missing fixture password")?;
            let new = secrets["new"]
                .as_str()
                .context("Missing fixture password")?;
            let system = tabs.child_by_name("system").context("No system page")?;
            tabs.set_visible_child_name("system");
            stack.set_visible_child_name("settings");
            for valid in [false, true] {
                find_button(&system, "Eigenes Linux-Kennwort ändern")
                    .unwrap()
                    .emit_clicked();
                let term = stack
                    .visible_child()
                    .context("No password terminal")?
                    .downcast::<vte::Terminal>()
                    .unwrap();
                let code = Rc::new(Cell::new(None));
                let result = code.clone();
                term.connect_child_exited(move |_, status| result.set(Some(status)));
                prompt(&term, "Current password:").await?;
                term.feed_child(
                    format!("{}\n", if valid { old } else { "wrong-test-password" }).as_bytes(),
                );
                if valid {
                    prompt(&term, "New password:").await?;
                    term.feed_child(format!("{new}\n").as_bytes());
                    prompt(&term, "Retype new password:").await?;
                    term.feed_child(format!("{new}\n").as_bytes());
                }
                for _ in 0..500 {
                    if code.get().is_some() {
                        break;
                    }
                    glib::timeout_future(std::time::Duration::from_millis(20)).await;
                }
                let status = code.get().context("passwd did not exit")?;
                ensure!(
                    (status == 0) == valid,
                    "passwd authentication outcome mismatch"
                );
                let text = term.text_format(vte::Format::Text).unwrap_or_default();
                ensure!(
                    !text.contains(old) && !text.contains(new),
                    "passwd echoed a password"
                );
                ensure!(app.windows().len() == 1);
                stack.set_visible_child_name("settings");
            }
            find_button(&system, "Von Rampi abmelden")
                .unwrap()
                .emit_clicked();
            ensure!(stack.visible_child_name().as_deref() == Some("logout"));
            crate::views::go_back(&stack);
            ensure!(stack.visible_child_name().as_deref() == Some("settings"));
            find_button(&system, "Von Rampi abmelden")
                .unwrap()
                .emit_clicked();
            let logout = stack.visible_child().unwrap();
            println!("RAMPI_RUST_ACCOUNT_PAGE_OK");
            find_button(&logout, "Jetzt abmelden")
                .unwrap()
                .emit_clicked();
            Ok(())
        }
        .await;
        if let Err(e) = result {
            eprintln!("Account page acceptance failed: {e:#}");
            std::process::exit(1);
        }
        app.quit();
    });
}
