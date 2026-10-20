//! Opt-in executable integration checks for the isolated Wayland test container.
use gtk::{gio, glib, prelude::*};
use std::cell::Cell;
use std::rc::Rc;
use vte::prelude::*;
use webkit6::prelude::*;

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
