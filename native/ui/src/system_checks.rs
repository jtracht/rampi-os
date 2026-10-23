//! Executable GTK + real labwc/wlr-randr acceptance, without physical devices.
use anyhow::{Context, ensure};
use gtk::{glib, prelude::*};
pub fn run(
    app: &gtk::Application,
    stack: &gtk::Stack,
    tabs: &gtk::Stack,
    status: &gtk::Label,
    f: &crate::widgets::Feedback,
) {
    assert_eq!(std::env::var("RAMPI_TEST_CONTAINER").as_deref(), Ok("1"));
    let (app, stack, tabs, status, f) = (
        app.clone(),
        stack.clone(),
        tabs.clone(),
        status.clone(),
        f.clone(),
    );
    glib::MainContext::default().spawn_local(async move {
        let result: anyhow::Result<()> = async {
            use crate::checks::{find_button, named};
            use std::os::unix::fs::PermissionsExt;
            let page = tabs.child_by_name("system").context("No system page")?;
            stack.set_visible_child_name("settings");
            tabs.set_visible_child_name("system");
            let file = crate::system_settings::keyboard_file()?;
            std::fs::create_dir_all(file.parent().unwrap())?;
            std::fs::write(
                &file,
                "# personal settings\nXCURSOR_SIZE=24\nXKB_DEFAULT_LAYOUT=us\n",
            )?;
            let choices = named(&page, "keyboard-layout")
                .context("No keyboard picker")?
                .downcast::<gtk::DropDown>()
                .unwrap();
            choices.set_selected(0);
            let save =
                find_button(&page, "Tastaturbelegung anwenden").context("No keyboard action")?;
            save.emit_clicked();
            for _ in 0..100 {
                if save.is_sensitive() {
                    break;
                }
                glib::timeout_future(std::time::Duration::from_millis(30)).await;
            }
            ensure!(
                save.is_sensitive() && status.text().contains("übergeben"),
                "Compositor reconfigure failed: {}",
                status.text()
            );
            let text = std::fs::read_to_string(&file)?;
            ensure!(
                text.contains("XCURSOR_SIZE=24")
                    && text.contains("XKB_DEFAULT_LAYOUT=de")
                    && !text.contains("XKB_DEFAULT_LAYOUT=us")
            );
            ensure!(std::fs::metadata(&file)?.permissions().mode() & 0o777 == 0o600);
            ensure!(crate::system_settings::save_keyboard("de\nCOMMAND=x").is_err());
            ensure!(std::fs::read_to_string(&file)? == text);
            std::fs::remove_file(&file)?;
            let unrelated = file.parent().unwrap().join("untouched");
            std::fs::write(&unrelated, "unchanged")?;
            std::os::unix::fs::symlink(&unrelated, &file)?;
            ensure!(crate::system_settings::save_keyboard("us").is_err());
            ensure!(std::fs::read_to_string(&unrelated)? == "unchanged");
            std::fs::remove_file(&file)?;
            let outputs = crate::system_settings::outputs().await?;
            let output = outputs.first().context("No actual headless output")?;
            ensure!(!output.current.is_empty());
            ensure!(
                crate::system_settings::apply(&output.name, "99999x99999")
                    .await
                    .is_err()
            );
            crate::system_settings::apply(&output.name, &output.current).await?;
            find_button(&page, "Bildschirme und Auflösungen anzeigen")
                .unwrap()
                .emit_clicked();
            for _ in 0..100 {
                if find_button(&page, &format!("{} · {}", output.name, output.current)).is_some() {
                    break;
                }
                glib::timeout_future(std::time::Duration::from_millis(30)).await;
            }
            ensure!(find_button(&page, &format!("{} · {}", output.name, output.current)).is_some());
            // A headless output advertises one mode. Exercise confirmation and
            // rollback with that real mode, without claiming HDMI mode changes.
            for action in ["timeout", "cancel", "accept"] {
                crate::system_settings::confirm(&stack, output, &output.current, &status, &f);
                let confirm = stack
                    .child_by_name("display-confirm")
                    .context("No confirmation page")?;
                let yes = find_button(&confirm, "Auflösung beibehalten").unwrap();
                for _ in 0..100 {
                    if yes.is_sensitive() {
                        break;
                    }
                    glib::timeout_future(std::time::Duration::from_millis(30)).await;
                }
                ensure!(yes.is_sensitive());
                match action {
                    "cancel" => crate::views::go_back(&stack),
                    "accept" => yes.emit_clicked(),
                    _ => (),
                }
                for _ in 0..600 {
                    if stack.child_by_name("display-confirm").is_none() {
                        break;
                    }
                    glib::timeout_future(std::time::Duration::from_millis(30)).await;
                }
                ensure!(
                    stack.child_by_name("display-confirm").is_none(),
                    "Display confirmation did not resolve: {action}"
                );
                ensure!(crate::system_settings::outputs().await?[0].current == output.current);
                ensure!(app.windows().len() == 1);
            }
            println!("RAMPI_RUST_SYSTEM_SETTINGS_OK");
            Ok(())
        }
        .await;
        if let Err(e) = result {
            eprintln!("System settings acceptance failed: {e:#}");
            std::process::exit(1);
        }
        app.quit();
    });
}
