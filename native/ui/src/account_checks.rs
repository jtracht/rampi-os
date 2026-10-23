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
