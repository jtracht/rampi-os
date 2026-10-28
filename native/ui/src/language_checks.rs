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
            let invalid_host = rampi_core::config::Host {
                address: "host.example".into(), username: "fixture".into(), port: 0,
                ..Default::default()
            };
            ensure!(invalid_host.validate().is_err_and(|error| error.to_string() == "The SSH port is invalid"));
            let invalid_board = rampi_core::board::Board {
                columns: vec!["\n".into()], ..Default::default()
            };
            ensure!(invalid_board.validate().is_err_and(|error| error.to_string() == "The source column is invalid"));

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
            let invalid_layout = crate::system_settings::save_keyboard("invalid\nlayout");
            ensure!(invalid_layout.is_err_and(|error| error.to_string() == "Unknown keyboard layout"));
            let unavailable_mode = crate::system_settings::apply("missing-output", "99999x99999").await;
            ensure!(unavailable_mode.is_err_and(|error| error.to_string() == "This display mode is no longer available"));
            let wifi = pages.child_by_name("wifi").context("No Wi-Fi page")?;
            pages.set_visible_child_name("wifi");
            named(&wifi, "hidden-network-form").context("No hidden-network section")?
                .downcast::<gtk::Expander>().ok().context("Hidden-network section type")?.set_expanded(true);
            glib::timeout_future(std::time::Duration::from_millis(50)).await;
            ensure!(named(&wifi, "hidden-adapter").is_some_and(|item| item.is::<gtk::ListBox>()));
            ensure!(named(&wifi, "hidden-security").is_some_and(|item| item.is::<gtk::ListBox>()));
            let board = pages.child_by_name("board").context("No board setup page")?;
            let providers = named(&board, "board-kind").context("No provider choices")?
                .downcast::<gtk::ListBox>().ok().context("Provider choices must stay inline")?;
            providers.select_row(providers.row_at_index(6).as_ref());
            ensure!(find_button(&board, "Check saved board").is_some());
            ensure!(named(&board, "board-source-hint").unwrap().downcast::<gtk::Label>().unwrap().text().contains("Gitea"));
            let vpn = pages.child_by_name("vpn").context("No VPN page")?;
            ensure!(find_button(&vpn, "Refresh VPN profiles").is_some());
            ensure!(find_button(&vpn, "Connect WireGuard").is_some());
            ensure!(find_button(&vpn, "Disconnect WireGuard").is_some());
            ensure!(find_button(&vpn, "Import WireGuard profile").is_some());
            let path = named(&vpn, "vpn-import-path").context("No inline WireGuard path")?
                .downcast::<gtk::Entry>().ok().context("WireGuard path type")?;
            ensure!(path.placeholder_text().as_deref() == Some("Path to your personal WireGuard file (.conf)"));
            let rejected = crate::wireguard::prepare(std::path::Path::new("invalid.txt"));
            ensure!(rejected.is_err_and(|error| error.to_string() == "Select a WireGuard file ending in .conf."));
            ensure!(find_button(&vpn, "Refresh Tailscale status").is_some());
            ensure!(find_button(&vpn, "Connect Tailscale").is_some());
            ensure!(find_button(&vpn, "Open Tailscale sign-in").is_some());
            pages.set_visible_child_name("vpn");
            find_button(&vpn, "Set up my Tailscale permissions").unwrap().emit_clicked();
            ensure!(stack.visible_child_name().as_deref() == Some("confirmation"));
            let confirmation = stack.child_by_name("confirmation").context("No permissions page")?;
            ensure!(find_button(&confirmation, "Confirm change").is_some());
            find_button(&confirmation, "Cancel").unwrap().emit_clicked();
            ensure!(stack.visible_child_name().as_deref() == Some("settings"));
            ensure!(rampi_core::tailscale::Status::parse(
                br#"{"BackendState":"NeedsLogin"}"#
            )?.description() == "Tailscale · Sign-in required");
            pages.set_visible_child_name("host");
            let host = pages.child_by_name("host").context("No host page")?;
            find_button(&host, "New host profile").context("No English new-profile action")?.emit_clicked();
            for (id, value) in [("name", "English fixture"), ("address", "host.example"),
                ("username", "fixture"), ("port", "2222"), ("resolution", "1280x720")] {
                named(&host, &format!("host-{id}")).context("Missing host field")?
                    .downcast::<gtk::Entry>().ok().context("Host field type")?.set_text(value);
            }
            find_button(&host, "Save host profile").unwrap().emit_clicked();
            let saved = rampi_core::config::Settings::load(&rampi_core::config::config_dir()?.join("settings.json"))?;
            ensure!(saved.hosts.len() == 1 && saved.hosts[0].port == 2222
                && saved.hosts[0].address == "host.example", "English editor did not save the actual profile");
            find_button(&host, "Use selected host").unwrap().emit_clicked();
            find_button(&host, "Prepare removal").unwrap().emit_clicked();
            find_button(&host, "Cancel removal").unwrap().emit_clicked();
            ensure!(rampi_core::config::Settings::load(&rampi_core::config::config_dir()?.join("settings.json"))?.hosts.len() == 1);
            find_button(&host, "Prepare removal").unwrap().emit_clicked();
            find_button(&host, "Remove host profile permanently").unwrap().emit_clicked();
            ensure!(rampi_core::config::Settings::load(&rampi_core::config::config_dir()?.join("settings.json"))?.hosts.is_empty());
            pages.set_visible_child_name("system");
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
