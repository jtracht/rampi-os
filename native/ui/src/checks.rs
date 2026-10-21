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
