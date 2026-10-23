//! Actual browser engine capabilities and user input, not simulated DOM events.
use anyhow::{Context, ensure};
use gtk::{glib, prelude::*};
use webkit6::prelude::*;

pub fn profile(
    app: &gtk::Application,
    stack: &gtk::Stack,
    conf: &crate::widgets::Shared,
    status: &gtk::Label,
    feedback: &crate::widgets::Feedback,
    expected: bool,
) {
    assert_eq!(std::env::var("RAMPI_TEST_CONTAINER").as_deref(), Ok("1"));
    conf.borrow_mut().browser_url = "https://localhost:22225/modern".into();
    crate::views::browser(stack, conf, status, feedback);
    let page = stack.visible_child().unwrap();
    let web = crate::checks::named(&page, "browser-webview")
        .unwrap()
        .downcast::<webkit6::WebView>()
        .unwrap();
    let app = app.clone();
    glib::MainContext::default().spawn_local(async move {
        let result: anyhow::Result<()> = async {
            crate::browser_checks::wait_title(&web, "Rampi modern ready").await?;
            let expression = if expected {
                "localStorage.getItem('rampi-proof') === 'personal-profile' && document.cookie.includes('rampi-proof=personal-profile') && window.indexedProof === 'personal-profile'"
            } else {
                "localStorage.getItem('rampi-proof') === null && !document.cookie.includes('rampi-proof=') && window.indexedProof === null"
            };
            truth(&web, expression).await?;
            ensure!(app.windows().len() == 1);
            if expected { println!("RAMPI_RUST_BROWSER_PROFILE_RESTART_OK"); }
            else { println!("RAMPI_RUST_BROWSER_OTHER_ACCOUNT_EMPTY_OK"); }
            Ok(())
        }.await;
        if let Err(error) = result { eprintln!("Browser profile acceptance failed: {error:#}"); std::process::exit(1); }
        app.quit();
    });
}

async fn command(program: &str, args: &[&str]) -> anyhow::Result<()> {
    let args = args
        .iter()
        .map(std::ffi::OsString::from)
        .collect::<Vec<_>>();
    ensure!(
        crate::process::output(program, &args, 5, 32768).await?.0,
        "Input command failed: {program}"
    );
    glib::timeout_future(std::time::Duration::from_millis(120)).await;
    Ok(())
}
async fn truth(web: &webkit6::WebView, expression: &str) -> anyhow::Result<()> {
    for _ in 0..150 {
        if web
            .evaluate_javascript_future(expression, None, None)
            .await?
            .to_boolean()
        {
            return Ok(());
        }
        glib::timeout_future(std::time::Duration::from_millis(30)).await;
    }
    anyhow::bail!("Actual browser condition failed: {expression}")
}
pub async fn interactive(
    app: &gtk::Application,
    browser: &gtk::Widget,
    web: &webkit6::WebView,
) -> anyhow::Result<()> {
    use crate::checks::named;
    let keyboard = gtk::gio::Subprocess::newv(
        &["wtype".as_ref(), "-s".as_ref(), "30000".as_ref()],
        gtk::gio::SubprocessFlags::STDOUT_SILENCE,
    )?;
    glib::timeout_future(std::time::Duration::from_millis(200)).await;
    let address = named(browser, "browser-address")
        .context("No address field")?
        .downcast::<gtk::Entry>()
        .unwrap();
    web.grab_focus();
    command("wtype", &["-M", "ctrl", "-k", "l", "-m", "ctrl"]).await?;
    let root = web
        .root()
        .context("No browser root")?
        .downcast::<gtk::Window>()
        .unwrap();
    ensure!(
        gtk::prelude::RootExt::focus(&root)
            .is_some_and(|focus| focus == address || focus.is_ancestor(&address)),
        "Ctrl+L did not focus address field"
    );
    command("wtype", &["https://localhost:22225/modern", "-k", "Return"]).await?;
    crate::browser_checks::wait_title(web, "Rampi modern ready").await?;
    ensure!(address.text().as_str() == "https://localhost:22225/modern");
    truth(web, "window.modernReady === true").await?;
    let root = web
        .root()
        .context("No browser root")?
        .downcast::<gtk::Window>()
        .unwrap();
    let bounds = web.compute_bounds(&root).context("No WebKit geometry")?;
    // Clamp at the output origin, then move to the real CSS button's center.
    command("wlrctl", &["pointer", "move", "-10000", "-10000"]).await?;
    let x = (bounds.x() as i32 + 140).to_string();
    let y = (bounds.y() as i32 + 60).to_string();
    command("wlrctl", &["pointer", "move", &x, &y]).await?;
    truth(
        web,
        "getComputedStyle(document.getElementById('save')).backgroundColor === 'rgb(20, 160, 80)'",
    )
    .await?;
    command("wlrctl", &["pointer", "click", "left"]).await?;
    truth(web, "window.clicks === 1 && window.modernSaved === true").await?;
    web.grab_focus();
    command("wtype", &["-k", "g"]).await?;
    truth(web, "window.keyboardSeen === true").await?;
    let chrome = named(browser, "browser-toolbar").unwrap();
    command("wtype", &["-k", "F11"]).await?;
    ensure!(!chrome.is_visible(), "F11 did not hide browser chrome");
    ensure!(root.is_fullscreen() && app.windows().len() == 1);
    command("wtype", &["-k", "Escape"]).await?;
    ensure!(chrome.is_visible() && root.is_fullscreen());
    // Enter the standard DOM fullscreen API using a real user key activation.
    web.evaluate_javascript_future("document.getElementById('full').focus(); null", None, None)
        .await?;
    command("wtype", &["-k", "Return"]).await?;
    truth(web, "!!document.fullscreenElement").await?;
    ensure!(!chrome.is_visible() && root.is_fullscreen() && app.windows().len() == 1);
    command("wtype", &["-k", "Escape"]).await?;
    truth(web, "!document.fullscreenElement").await?;
    ensure!(chrome.is_visible() && root.is_fullscreen());
    command("wtype", &["-k", "F5"]).await?;
    crate::browser_checks::wait_title(web, "Rampi modern ready").await?;
    truth(web, "localStorage.getItem('rampi-proof') === 'personal-profile' && document.cookie.includes('rampi-proof=personal-profile') && window.indexedProof === 'personal-profile'").await?;
    keyboard.force_exit();
    println!("RAMPI_RUST_BROWSER_MODERN_INPUT_FULLSCREEN_OK");
    Ok(())
}
