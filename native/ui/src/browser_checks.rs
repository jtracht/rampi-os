use anyhow::{Context, ensure};
use gtk::{glib, prelude::*};
use std::{
    cell::{Cell, RefCell},
    rc::Rc,
};
use webkit6::prelude::*;
async fn wait_title(web: &webkit6::WebView, title: &str) -> anyhow::Result<()> {
    for _ in 0..300 {
        if web.title().as_deref() == Some(title) && !web.is_loading() {
            return Ok(());
        }
        glib::timeout_future(std::time::Duration::from_millis(30)).await;
    }
    anyhow::bail!("Trusted HTTPS page did not load: {title}")
}
pub fn run(
    app: &gtk::Application,
    stack: &gtk::Stack,
    conf: &crate::widgets::Shared,
    status: &gtk::Label,
    f: &crate::widgets::Feedback,
) {
    assert_eq!(std::env::var("RAMPI_TEST_CONTAINER").as_deref(), Ok("1"));
    let (app, stack, conf, status, f) = (
        app.clone(),
        stack.clone(),
        conf.clone(),
        status.clone(),
        f.clone(),
    );
    glib::MainContext::default().spawn_local(async move {
        let result: anyhow::Result<()> = async {
            use crate::checks::{find_button, named};
            conf.borrow_mut().browser_url = "https://localhost:22225/start".into();
            crate::views::browser(&stack, &conf, &status, &f);
            let browser = stack.child_by_name("browser").context("Browser missing")?;
            let web = named(&browser, "browser-webview")
                .context("WebKit missing")?
                .downcast::<webkit6::WebView>()
                .unwrap();
            wait_title(&web, "Rampi HTTPS start").await?;
            ensure!(
                web.tls_info().is_some_and(|(_, flags)| flags.is_empty()),
                "Actual TLS was not trusted"
            );
            web.load_uri("https://localhost:22225/second");
            wait_title(&web, "Rampi HTTPS second").await?;
            find_button(&browser, "←").unwrap().emit_clicked();
            wait_title(&web, "Rampi HTTPS start").await?;
            find_button(&browser, "→").unwrap().emit_clicked();
            wait_title(&web, "Rampi HTTPS second").await?;
            for (script, answer) in [
                ("confirm('Confirm fixture')", "true"),
                ("prompt('Prompt fixture','old')", "typed response"),
            ] {
                let result = Rc::new(RefCell::new(None));
                let pending = result.clone();
                let w = web.clone();
                glib::MainContext::default().spawn_local(async move {
                    *pending.borrow_mut() =
                        Some(w.evaluate_javascript_future(script, None, None).await);
                });
                for _ in 0..200 {
                    if stack.visible_child_name().as_deref() == Some("browser-request") {
                        break;
                    }
                    glib::timeout_future(std::time::Duration::from_millis(20)).await;
                }
                ensure!(
                    stack.visible_child_name().as_deref() == Some("browser-request"),
                    "Script prompt escaped application"
                );
                let page = stack.visible_child().unwrap();
                if script.starts_with("prompt") {
                    named(&page, "browser-prompt-input")
                        .unwrap()
                        .downcast::<gtk::Entry>()
                        .unwrap()
                        .set_text(answer);
                }
                find_button(&page, "Bestätigen").unwrap().emit_clicked();
                for _ in 0..200 {
                    if result.borrow().is_some() {
                        break;
                    }
                    glib::timeout_future(std::time::Duration::from_millis(20)).await;
                }
                let reply = result
                    .borrow_mut()
                    .take()
                    .context("No JavaScript reply")??;
                ensure!(reply.to_str() == answer, "Script prompt response mismatch");
            }
            for cancel in [true, false] {
                let download = web
                    .download_uri("https://localhost:22225/download")
                    .context("No actual WebKit download")?;
                let done = Rc::new(Cell::new(false));
                let d = done.clone();
                download.connect_finished(move |_| d.set(true));
                for _ in 0..200 {
                    if stack.visible_child_name().as_deref() == Some("browser-downloads") {
                        break;
                    }
                    glib::timeout_future(std::time::Duration::from_millis(20)).await;
                }
                ensure!(stack.visible_child_name().as_deref() == Some("browser-downloads"));
                let page = stack.visible_child().unwrap();
                // The most recently appended queue entry owns this request.
                let path = last_named(&page, "download-path")
                    .context("No inline destination")?
                    .downcast::<gtk::Entry>()
                    .unwrap();
                let destination = glib::home_dir().join("Downloads/fixture.bin");
                ensure!(
                    !destination.exists(),
                    "Download wrote a file before consent"
                );
                if cancel {
                    find_button(&page, "Download abbrechen")
                        .unwrap()
                        .emit_clicked();
                } else {
                    let existing = glib::home_dir().join("untouched.txt");
                    std::fs::write(&existing, "preserve")?;
                    path.set_text(&existing.to_string_lossy());
                    let row = path.parent().unwrap();
                    find_button(&row, "Download speichern")
                        .unwrap()
                        .emit_clicked();
                    ensure!(std::fs::read_to_string(&existing)? == "preserve");
                    path.set_text(&destination.to_string_lossy());
                    find_button(&row, "Download speichern")
                        .unwrap()
                        .emit_clicked();
                }
                for _ in 0..300 {
                    if done.get() {
                        break;
                    }
                    glib::timeout_future(std::time::Duration::from_millis(20)).await;
                }
                ensure!(done.get(), "Download did not finish/cancel");
                if !cancel {
                    ensure!(std::fs::read(&destination)? == b"Rampi actual HTTPS download\n");
                }
                stack.set_visible_child_name("browser");
            }
            status.set_text("");
            web.load_uri("https://127.0.0.1:22225/start");
            for _ in 0..300 {
                if status.text().contains("Zertifikat") {
                    break;
                }
                glib::timeout_future(std::time::Duration::from_millis(20)).await;
            }
            ensure!(
                status.text().contains("Zertifikat"),
                "Hostname certificate mismatch was accepted"
            );
            web.load_uri("http://localhost:22225/start");
            for _ in 0..100 {
                if status.text().contains("Navigation") {
                    break;
                }
                glib::timeout_future(std::time::Duration::from_millis(20)).await;
            }
            ensure!(
                status.text().contains("Navigation"),
                "Insecure navigation was accepted"
            );
            ensure!(app.windows().len() == 1, "Browser opened another window");
            println!("RAMPI_RUST_BROWSER_HTTPS_DOWNLOADS_OK");
            Ok(())
        }
        .await;
        if let Err(e) = result {
            eprintln!(
                "Browser HTTPS acceptance failed: {e:#}; status={}",
                status.text()
            );
            std::process::exit(1);
        }
        app.quit();
    });
}
fn last_named(root: &gtk::Widget, name: &str) -> Option<gtk::Widget> {
    let mut result = (root.widget_name() == name).then(|| root.clone());
    let mut next = root.first_child();
    while let Some(child) = next {
        if let Some(found) = last_named(&child, name) {
            result = Some(found);
        }
        next = child.next_sibling();
    }
    result
}
