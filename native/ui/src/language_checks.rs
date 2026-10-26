//! Actual GTK navigation/personal language persistence; not a full translation audit.
use anyhow::{Context, Result, ensure};
use gtk::{glib, prelude::*};

pub fn run(
    app: &gtk::Application,
    stack: &gtk::Stack,
    pages: &gtk::Stack,
    feedback: &crate::widgets::Feedback,
) {
    assert_eq!(std::env::var("RAMPI_TEST_CONTAINER").as_deref(), Ok("1"));
    assert!(std::path::Path::new("/.dockerenv").is_file());
    let (app, stack, pages, feedback) =
        (app.clone(), stack.clone(), pages.clone(), feedback.clone());
    glib::MainContext::default().spawn_local(async move {
        let result: Result<()> = async {
            use crate::checks::{find_button, named};
            ensure!(feedback.settings_language() == "en", "English fixture not loaded");
            ensure!(rampi_core::i18n::text("settings-heading", &[]) == "Settings");
            let dashboard = stack.child_by_name("dashboard").context("No dashboard")?;
            ensure!(find_button(&dashboard, "⚙  Settings").is_some());
            ensure!(find_button(&dashboard, "Resume setup").is_some());
            let setup = stack.child_by_name("setup").context("No setup")?;
            let title = named(&setup, "setup-title").unwrap().downcast::<gtk::Label>().unwrap();
            ensure!(title.text().contains("Language and keyboard"));
            stack.set_visible_child_name("settings");
            pages.set_visible_child_name("system");
            let system = pages.child_by_name("system").context("No system page")?;
            let keyboard = named(&system, "keyboard-layout").context("No inline layouts")?;
            ensure!(keyboard.is::<gtk::ListBox>(), "Keyboard choices opened a popup");
            ensure!(find_button(&system, "Apply keyboard layout").is_some());
            let languages = named(&system, "language-choices").unwrap()
                .downcast::<gtk::ListBox>().unwrap();
            languages.select_row(languages.row_at_index(0).as_ref());
            find_button(&system, "Save language for the next login").unwrap().emit_clicked();
            let path = rampi_core::config::config_dir()?.join("settings.json");
            ensure!(rampi_core::config::Settings::load(&path)?.language == "de");
            // A pending choice must not partially translate the running session.
            ensure!(rampi_core::i18n::text("settings-heading", &[]) == "Settings");
            let preserved = std::fs::read(&path)?;
            ensure!(feedback.save_language("../unsupported").is_err());
            ensure!(std::fs::read(&path)? == preserved);
            feedback.save_language("en")?;
            ensure!(rampi_core::config::Settings::load(&path)?.language == "en");
            let locale = std::process::Command::new("/build/target/debug/rampi-native")
                .arg("--session-locale").output()?;
            ensure!(locale.status.success());
            ensure!(locale.stdout == b"LANGUAGE=en\nLANG=en_US.UTF-8\nLC_MESSAGES=en_US.UTF-8\nLC_TIME=en_US.UTF-8\n");
            ensure!(app.windows().len() == 1);
            println!("RAMPI_RUST_LANGUAGE_NAVIGATION_PERSISTENCE_OK");
            Ok(())
        }.await;
        if let Err(error) = result {
            eprintln!("Language/navigation check failed: {error:#}");
            std::process::exit(1);
        }
        app.quit();
    });
}
