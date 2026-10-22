//! Opt-in executable integration checks for the isolated Wayland test container.
use gtk::{gio, glib, prelude::*};
use std::cell::Cell;
use std::rc::Rc;
use vte::prelude::*;
use webkit6::prelude::*;

pub fn bluetooth(app: &gtk::Application, stack: &gtk::Stack, tabs: &gtk::Stack) {
    if std::env::var("RAMPI_TEST_CONTAINER").as_deref() != Ok("1")
        || std::env::var("DBUS_SYSTEM_BUS_ADDRESS").is_err()
    {
        eprintln!("Bluetooth UI check requires an isolated fixture bus");
        std::process::exit(2);
    }
    let (app, stack, tabs) = (app.clone(), stack.clone(), tabs.clone());
    glib::MainContext::default().spawn_local(async move {
        let outcome: anyhow::Result<()> = async {
            use anyhow::{Context, ensure};
            let connection = crate::bus::system().await?;
            let names = async || -> anyhow::Result<Vec<String>> {
                crate::bus::call(
                    &connection,
                    "org.freedesktop.DBus",
                    "/org/freedesktop/DBus",
                    "org.freedesktop.DBus",
                    "ListNames",
                    None,
                )
                .await?
                .child_value(0)
                .get()
                .context("No D-Bus names")
            };
            tabs.set_visible_child_name("bluetooth");
            stack.set_visible_child_name("settings");
            let page = tabs
                .child_by_name("bluetooth")
                .context("No Bluetooth page")?;
            let search = find_button(&page, "Geräte suchen").context("No inline search")?;
            let refresh =
                find_button(&page, "Adapter und Geräte aktualisieren").context("No refresh")?;
            for _ in 0..100 {
                if page.is_mapped() && refresh.is_sensitive() {
                    break;
                }
                glib::timeout_future(std::time::Duration::from_millis(20)).await;
            }
            // Wait for the page's automatic initial adapter discovery to finish.
            glib::timeout_future(std::time::Duration::from_millis(150)).await;
            let before = names().await?;
            search.emit_clicked();
            let mut client = None;
            for _ in 0..100 {
                let added: Vec<String> = names()
                    .await?
                    .into_iter()
                    .filter(|n| !before.contains(n))
                    .collect();
                if search.is_sensitive() && added.len() == 1 {
                    client = Some(added[0].clone());
                    break;
                }
                glib::timeout_future(std::time::Duration::from_millis(20)).await;
            }
            let client = client.context("Actual Bluetooth page did not start its own discovery")?;
            tabs.set_visible_child_name("wifi");
            for _ in 0..100 {
                if !names().await?.contains(&client) {
                    break;
                }
                glib::timeout_future(std::time::Duration::from_millis(20)).await;
            }
            ensure!(
                !names().await?.contains(&client),
                "Changing tabs left discovery running"
            );
            ensure!(app.windows().len() == 1, "Bluetooth opened another window");
            println!("RAMPI_RUST_BLUEZ_PAGE_OK");
            Ok(())
        }
        .await;
        if let Err(error) = outcome {
            eprintln!("Bluetooth page check failed: {error}");
            std::process::exit(1);
        }
        app.quit();
    });
}

fn find_button(widget: &gtk::Widget, title: &str) -> Option<gtk::Button> {
    if let Ok(button) = widget.clone().downcast::<gtk::Button>()
        && button.label().as_deref() == Some(title)
    {
        return Some(button);
    }
    let mut child = widget.first_child();
    while let Some(widget) = child {
        if let Some(button) = find_button(&widget, title) {
            return Some(button);
        }
        child = widget.next_sibling();
    }
    None
}

pub fn board(app: &gtk::Application, stack: &gtk::Stack, conf: &crate::widgets::Shared) {
    if std::env::var("RAMPI_TEST_CONTAINER").as_deref() != Ok("1")
        || !std::path::Path::new("/.dockerenv").exists()
    {
        eprintln!("Kanban UI checks require their disposable test container");
        std::process::exit(2);
    }
    let source =
        std::path::PathBuf::from(std::env::var_os("HOME").unwrap()).join("rampi-board-test.json");
    conf.borrow_mut().board_source = source.to_string_lossy().into_owned();
    conf.borrow_mut().board_kind = "json".into();
    conf.borrow_mut().board_columns = vec!["Review".into(), "Offen".into()];
    let (app, stack) = (app.clone(), stack.clone());
    glib::MainContext::default().spawn_local(async move {
        let outcome: anyhow::Result<()> = async {
            use anyhow::{Context, ensure};
            let original = std::fs::read(&source)?;
            let page = stack
                .child_by_name("kanban")
                .context("Kanban page missing")?;
            let result: gtk::Label = named(&page, "board-result")
                .context("No summary")?
                .downcast()
                .ok()
                .context("Summary type")?;
            let mut entries = vec![];
            for name in [
                "board-query",
                "board-project",
                "board-priority",
                "board-status",
            ] {
                entries.push(
                    named(&page, name)
                        .context("Missing filter")?
                        .downcast::<gtk::Entry>()
                        .ok()
                        .context("Filter type")?,
                );
            }
            stack.set_visible_child_name("kanban");
            for _ in 0..100 {
                if result.text().starts_with("3 von 3") {
                    break;
                }
                glib::timeout_future(std::time::Duration::from_millis(20)).await;
            }
            ensure!(
                result.text().starts_with("3 von 3"),
                "Board did not load on opening: {}",
                result.text()
            );
            entries[0].set_text("VPN");
            ensure!(result.text().starts_with("2 von 3"), "Search failed");
            entries[1].set_text("Infra");
            entries[2].set_text("high");
            ensure!(
                result.text().starts_with("1 von 3"),
                "Combined priority/project failed"
            );
            entries[3].set_text("Offen");
            ensure!(
                result.text().starts_with("0 von 3"),
                "Status did not combine with other filters"
            );
            entries[2].set_text("");
            ensure!(
                result.text().starts_with("1 von 3"),
                "Clearing a filter failed"
            );
            for entry in &entries {
                entry.set_text("");
            }
            ensure!(
                std::fs::read(&source)? == original,
                "Read-only board changed source tasks"
            );
            let mut changed: serde_json::Value = serde_json::from_slice(&original)?;
            changed["cards"]
                .as_array_mut()
                .context("Fixture cards")?
                .push(serde_json::json!({"title":"Delta", "status":"Review"}));
            // Simulate an external provider update to this disposable fixture.
            std::fs::write(&source, serde_json::to_vec(&changed)?)?;
            let reload = find_button(&page, "Aufgaben neu laden").context("No inline reload")?;
            reload.emit_clicked();
            for _ in 0..100 {
                if result.text().starts_with("4 von 4") {
                    break;
                }
                glib::timeout_future(std::time::Duration::from_millis(20)).await;
            }
            ensure!(
                result.text().starts_with("4 von 4"),
                "Updated source was not reloaded"
            );
            std::fs::write(&source, b"invalid JSON")?;
            reload.emit_clicked();
            for _ in 0..100 {
                if result.text().contains("bleiben sichtbar") {
                    break;
                }
                glib::timeout_future(std::time::Duration::from_millis(20)).await;
            }
            ensure!(
                result.text().contains("bleiben sichtbar"),
                "Source failure did not show an inline error"
            );
            entries[0].set_text("Delta");
            ensure!(
                result.text().starts_with("1 von 4"),
                "Source failure discarded loaded tasks"
            );
            ensure!(app.windows().len() == 1, "Kanban opened an external window");
            println!("RAMPI_RUST_KANBAN_PAGE_OK");
            Ok(())
        }
        .await;
        if let Err(error) = outcome {
            eprintln!("Kanban page check failed: {error}");
            std::process::exit(1);
        }
        app.quit();
    });
}

fn named(root: &gtk::Widget, name: &str) -> Option<gtk::Widget> {
    if root.widget_name() == name {
        return Some(root.clone());
    }
    let mut child = root.first_child();
    while let Some(widget) = child {
        if let Some(found) = named(&widget, name) {
            return Some(found);
        }
        child = widget.next_sibling();
    }
    None
}

pub fn setup(
    app: &gtk::Application,
    stack: &gtk::Stack,
    tabs: &gtk::Stack,
    conf: &crate::widgets::Shared,
) {
    assert_eq!(std::env::var("RAMPI_TEST_CONTAINER").as_deref(), Ok("1"));
    let (app, stack, tabs, conf) = (app.clone(), stack.clone(), tabs.clone(), conf.clone());
    glib::MainContext::default().spawn_local(async move {
        let result: anyhow::Result<()> = async {
            use anyhow::{Context, ensure};
            let setup = stack.child_by_name("setup").context("No wizard")?;
            let click = |root: &gtk::Widget, title: &str| -> anyhow::Result<()> {
                let b = find_button(root, title).context(format!("No button {title}"))?;
                ensure!(b.is_sensitive(), "Button disabled: {title}");
                b.emit_clicked();
                Ok(())
            };
            stack.set_visible_child_name("setup");
            click(&setup, "Weiter / Schritt überspringen")?;
            click(&setup, "Weiter / Schritt überspringen")?;
            click(&setup, "Jetzt einrichten")?;
            ensure!(tabs.visible_child_name().as_deref() == Some("wifi"));
            crate::views::go_back(&stack);
            ensure!(stack.visible_child_name().as_deref() == Some("setup"));
            click(&setup, "Später fortsetzen")?;
            ensure!(!conf.borrow().setup_complete && conf.borrow().setup_step == 2);
            let saved = rampi_core::config::Settings::load(
                &rampi_core::config::config_dir()?.join("settings.json"),
            )?;
            ensure!(saved.setup_step == 2 && !saved.setup_complete);
            let host = tabs.child_by_name("host").context("No host editor")?;
            tabs.set_visible_child_name("host");
            stack.set_visible_child_name("settings");
            let field = |id: &str, value: &str| -> anyhow::Result<()> {
                named(&host, &format!("host-{id}"))
                    .context("Missing field")?
                    .downcast::<gtk::Entry>()
                    .map_err(|_| anyhow::anyhow!("Not entry"))?
                    .set_text(value);
                Ok(())
            };
            for (name, address, user) in [
                ("Office", "office.example", "alice"),
                ("Laptop", "laptop.example", "bob"),
            ] {
                click(&host, "Neues Hostprofil")?;
                field("name", name)?;
                field("address", address)?;
                field("username", user)?;
                field("port", "2222")?;
                click(&host, "Hostprofil speichern")?;
            }
            ensure!(conf.borrow().hosts.len() == 2, "Profiles not saved");
            click(&host, "Ausgewählten Host verwenden")?;
            ensure!(conf.borrow().host()?.username == "bob");
            field("port", "0")?;
            click(&host, "Hostprofil speichern")?;
            ensure!(
                conf.borrow().host()?.port == 2222,
                "Rejected input mutated configuration"
            );
            click(&host, "Entfernen vorbereiten")?;
            click(&host, "Entfernen abbrechen")?;
            ensure!(conf.borrow().hosts.len() == 2);
            click(&host, "Entfernen vorbereiten")?;
            click(&host, "Hostprofil endgültig entfernen")?;
            ensure!(conf.borrow().hosts.len() == 1 && conf.borrow().host()?.username == "alice");
            stack.set_visible_child_name("setup");
            for _ in 2..14 {
                click(&setup, "Weiter / Schritt überspringen")?;
            }
            click(&setup, "Jetzt einrichten")?;
            let diagnostics = stack
                .child_by_name("diagnostics")
                .context("No diagnostics")?;
            click(&diagnostics, "Diagnose aktualisieren")?;
            for _ in 0..200 {
                if find_button(&diagnostics, "Diagnose aktualisieren")
                    .unwrap()
                    .is_sensitive()
                {
                    break;
                }
                glib::timeout_future(std::time::Duration::from_millis(10)).await;
            }
            let output = named(&diagnostics, "diagnostics-result")
                .unwrap()
                .downcast::<gtk::Label>()
                .unwrap();
            ensure!(
                output.text().contains("Linux-Konto:") && output.text().contains("Hostprofile: 1")
            );
            crate::views::go_back(&stack);
            click(&setup, "Einrichtung abschließen")?;
            ensure!(
                conf.borrow().setup_complete
                    && stack.visible_child_name().as_deref() == Some("dashboard")
            );
            ensure!(
                rampi_core::config::Settings::load(
                    &rampi_core::config::config_dir()?.join("settings.json")
                )?
                .setup_complete
            );
            ensure!(app.windows().len() == 1, "Setup opened additional window");
            // Other acceptance stages start with a fresh personal profile.
            std::fs::remove_file(rampi_core::config::config_dir()?.join("settings.json"))?;
            println!("RAMPI_RUST_SETUP_HOSTS_OK");
            Ok(())
        }
        .await;
        if let Err(e) = result {
            eprintln!("Setup/hosts check failed: {e:#}");
            std::process::exit(1);
        }
        app.quit();
    });
}

pub fn vpn(app: &gtk::Application, stack: &gtk::Stack, tabs: &gtk::Stack) {
    if std::env::var("RAMPI_TEST_CONTAINER").as_deref() != Ok("1")
        || std::env::var("DBUS_SYSTEM_BUS_ADDRESS").is_err()
        || !std::path::Path::new("/.dockerenv").exists()
    {
        eprintln!("VPN page check requires its private fixture container");
        std::process::exit(2);
    }
    let (app, stack, tabs) = (app.clone(), stack.clone(), tabs.clone());
    glib::MainContext::default().spawn_local(async move {
        let result: anyhow::Result<()> = async {
            use anyhow::{Context, ensure};
            let page = tabs.child_by_name("vpn").context("No VPN page")?;
            let list: gtk::ListBox = named(&page, "vpn-profiles")
                .context("No profile list")?
                .downcast()
                .ok()
                .context("List type")?;
            let refresh = find_button(&page, "VPN-Profile aktualisieren").context("No refresh")?;
            let status: gtk::Label = named(&page, "vpn-status")
                .context("No VPN status")?
                .downcast()
                .ok()
                .context("Status type")?;
            tabs.set_visible_child_name("vpn");
            stack.set_visible_child_name("settings");
            for _ in 0..100 {
                if list.row_at_index(0).is_some() && refresh.is_sensitive() {
                    break;
                }
                glib::timeout_future(std::time::Duration::from_millis(20)).await;
            }
            ensure!(
                list.row_at_index(0).is_some() && list.row_at_index(1).is_none(),
                "Shared/foreign profiles visible or personal profile missing"
            );
            list.select_row(list.row_at_index(0).as_ref());
            find_button(&page, "WireGuard verbinden")
                .context("No connect")?
                .emit_clicked();
            let mut active = false;
            for _ in 0..100 {
                if crate::wireguard::profiles()
                    .await?
                    .first()
                    .is_some_and(|p| p.state == 2)
                {
                    active = true;
                    break;
                }
                glib::timeout_future(std::time::Duration::from_millis(20)).await;
            }
            ensure!(
                active,
                "Actual connect button did not activate selected profile"
            );
            for _ in 0..100 {
                if refresh.is_sensitive() && status.text() == "Vorgang abgeschlossen." {
                    break;
                }
                glib::timeout_future(std::time::Duration::from_millis(20)).await;
            }
            ensure!(
                list.selected_row().is_some(),
                "Refresh lost profile selection"
            );
            let path: gtk::Entry = named(&page, "vpn-import-path")
                .context("No inline import")?
                .downcast()
                .ok()
                .context("Path type")?;
            path.set_text(&std::env::var("RAMPI_TEST_WG_FILE")?);
            find_button(&page, "WireGuard-Profil importieren")
                .context("No import button")?
                .emit_clicked();
            let mut imported = false;
            for _ in 0..100 {
                if list.row_at_index(1).is_some() {
                    imported = true;
                    break;
                }
                glib::timeout_future(std::time::Duration::from_millis(20)).await;
            }
            ensure!(
                imported && list.row_at_index(2).is_none(),
                "Inline import did not update the private picker"
            );
            let selected = list.selected_row().context("Import lost prior selection")?;
            ensure!(selected.index() == 0, "Import changed selected UUID");
            find_button(&page, "WireGuard trennen")
                .context("No disconnect")?
                .emit_clicked();
            let mut disconnected = false;
            for _ in 0..100 {
                if crate::wireguard::profiles()
                    .await?
                    .iter()
                    .all(|p| p.active.is_empty())
                {
                    disconnected = true;
                    break;
                }
                glib::timeout_future(std::time::Duration::from_millis(20)).await;
            }
            ensure!(
                disconnected,
                "Actual disconnect button did not release tunnel"
            );
            ensure!(app.windows().len() == 1, "VPN opened a second app window");
            println!("RAMPI_RUST_VPN_PAGE_OK");
            Ok(())
        }
        .await;
        if let Err(error) = result {
            eprintln!("VPN page check failed: {error}");
            std::process::exit(1);
        }
        app.quit();
    });
}

pub fn tailscale(app: &gtk::Application, stack: &gtk::Stack, tabs: &gtk::Stack) {
    if std::env::var("RAMPI_TEST_CONTAINER").as_deref() != Ok("1")
        || !std::path::Path::new("/.dockerenv").exists()
    {
        std::process::exit(2);
    }
    let (app, stack, tabs) = (app.clone(), stack.clone(), tabs.clone());
    glib::MainContext::default().spawn_local(async move {
        let result: anyhow::Result<()> = async {
            use anyhow::{Context, ensure};
            let page = tabs.child_by_name("vpn").context("No VPN page")?;
            let output: gtk::Label = named(&page, "tailscale-status")
                .context("No inline Tailscale status")?
                .downcast()
                .ok()
                .context("Status type")?;
            let refresh = find_button(&page, "Tailscale-Status aktualisieren")
                .context("No inline refresh")?;
            tabs.set_visible_child_name("vpn");
            stack.set_visible_child_name("settings");
            for _ in 0..250 {
                if refresh.is_sensitive() && output.text().contains("Anmeldung erforderlich") {
                    break;
                }
                glib::timeout_future(std::time::Duration::from_millis(20)).await;
            }
            ensure!(
                output.text().contains("Anmeldung erforderlich"),
                "Actual daemon status was not shown in the page"
            );
            refresh.emit_clicked();
            ensure!(
                !refresh.is_sensitive(),
                "Refresh did not start an asynchronous query"
            );
            for _ in 0..250 {
                if refresh.is_sensitive() {
                    break;
                }
                glib::timeout_future(std::time::Duration::from_millis(20)).await;
            }
            ensure!(
                refresh.is_sensitive() && output.text().contains("Anmeldung erforderlich"),
                "Actual status refresh failed"
            );
            ensure!(
                app.windows().len() == 1,
                "Tailscale status opened a second app window"
            );
            println!("RAMPI_RUST_TAILSCALE_PAGE_OK");
            Ok(())
        }
        .await;
        if let Err(error) = result {
            eprintln!("Tailscale page check failed: {error}");
            std::process::exit(1);
        }
        app.quit();
    });
}

pub fn keyboard(app: &gtk::Application, stack: &gtk::Stack) {
    let s = stack.clone();
    glib::timeout_add_local_once(std::time::Duration::from_millis(1600), move || {
        if s.visible_child_name().as_deref() != Some("kanban") {
            eprintln!(
                "Wayland arrow/Enter input did not open Kanban: {:?}",
                s.visible_child_name()
            );
            std::process::exit(1);
        }
    });
    let (a, s) = (app.clone(), stack.clone());
    glib::timeout_add_local_once(std::time::Duration::from_millis(3200), move || {
        if s.visible_child_name().as_deref() != Some("dashboard") {
            eprintln!("Wayland Escape did not return to dashboard");
            std::process::exit(1);
        }
        println!("RAMPI_RUST_WAYLAND_KEYBOARD_OK");
        a.quit();
    });
}

pub fn embedded(app: &gtk::Application, stack: &gtk::Stack) {
    if std::env::var("RAMPI_TEST_CONTAINER").as_deref() != Ok("1") {
        eprintln!("Embedded checks require their isolated test container");
        std::process::exit(2);
    }
    let term = vte::Terminal::new();
    stack.add_named(&term, Some("test-terminal"));
    stack.set_visible_child_name("test-terminal");
    let done = Rc::new(Cell::new(false));
    let (d, t) = (done.clone(), term.clone());
    term.spawn_async(
        vte::PtyFlags::DEFAULT,
        None,
        &[
            "/bin/sh",
            "-c",
            "printf 'RAMPI_PTY_READY\\n'; read -r answer; printf 'PTY:%s\\n' \"$answer\"",
        ],
        &[],
        glib::SpawnFlags::SEARCH_PATH,
        || {},
        -1,
        None::<&gio::Cancellable>,
        move |result| {
            if let Err(e) = result {
                eprintln!("PTY spawn failed: {e}");
                std::process::exit(1);
            }
            t.feed_child(b"rust-input\n");
        },
    );
    let (a, s) = (app.clone(), stack.clone());
    term.connect_child_exited(move |term, code| {
        let screen = term.text_format(vte::Format::Text).unwrap_or_default();
        if code != 0 || !screen.contains("PTY:rust-input") {
            eprintln!("Actual VTE PTY roundtrip failed");
            std::process::exit(1);
        }
        d.set(true);
        println!("RAMPI_RUST_VTE_PTY_OK");
        let web = webkit6::WebView::builder()
            .network_session(&webkit6::NetworkSession::new_ephemeral())
            .hexpand(true)
            .vexpand(true)
            .build();
        let a = a.clone();
        web.connect_load_changed(move |web, event| {
            if event == webkit6::LoadEvent::Finished {
                let (a, w) = (a.clone(), web.clone());
                glib::MainContext::default().spawn_local(async move {
                    match w
                        .evaluate_javascript_future(
                            "document.getElementById('rampi').textContent + ':' + (21*2)",
                            None,
                            None,
                        )
                        .await
                    {
                        Ok(value) if value.to_str() == "RustBrowserOK:42" => {
                            if a.windows().len() != 1 {
                                eprintln!("Browser created a second window");
                                std::process::exit(1);
                            }
                            println!("RAMPI_RUST_WEBKIT_DOM_JS_OK");
                            a.quit();
                        }
                        _ => {
                            eprintln!("Actual WebKit DOM/JavaScript roundtrip failed");
                            std::process::exit(1);
                        }
                    }
                });
            }
        });
        s.add_named(&web, Some("test-browser"));
        s.set_visible_child_name("test-browser");
        web.load_html(
            "<!doctype html><html><body><h1 id='rampi'>RustBrowserOK</h1></body></html>",
            Some("https://rampi.test/"),
        );
    });
    let timeout_app = app.downgrade();
    glib::timeout_add_local_once(std::time::Duration::from_secs(25), move || {
        if timeout_app.upgrade().is_some_and(|a| a.is_registered()) {
            eprintln!("Embedded test timed out");
            std::process::exit(1);
        }
    });
}
