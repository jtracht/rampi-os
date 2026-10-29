//! Actual Wayland input and compositor screenshots, never fabricated UI images.
use anyhow::{Context, ensure};
use gtk::{glib, prelude::*};
use std::{cell::RefCell, os::unix::fs::PermissionsExt, path::PathBuf, rc::Rc};
use vte::prelude::*;
async fn tool(program: &str, args: &[&str]) -> anyhow::Result<()> {
    let args = args.iter().map(|s| (*s).into()).collect::<Vec<_>>();
    ensure!(
        crate::process::output(program, &args, 5, 32768).await?.0,
        "Input/capture tool failed: {program}"
    );
    Ok(())
}
async fn delay(ms: u64) {
    glib::timeout_future(std::time::Duration::from_millis(ms)).await;
}
async fn settled(stack: &gtk::Stack) -> anyhow::Result<()> {
    // Wait for the framework's real transition, rather than capturing two pages mid-slide.
    for _ in 0..100 {
        if !stack.is_transition_running() {
            delay(35).await;
            return Ok(());
        }
        delay(20).await;
    }
    anyhow::bail!("Page transition did not finish")
}
pub fn run(
    app: &gtk::Application,
    window: &gtk::ApplicationWindow,
    stack: &gtk::Stack,
    tabs: &gtk::Stack,
    conf: &crate::widgets::Shared,
    f: &crate::widgets::Feedback,
) {
    assert_eq!(std::env::var("RAMPI_TEST_CONTAINER").as_deref(), Ok("1"));
    let (app, window, stack, tabs, conf, f) = (
        app.clone(),
        window.clone(),
        stack.clone(),
        tabs.clone(),
        conf.clone(),
        f.clone(),
    );
    glib::MainContext::default().spawn_local(async move {
        let result: anyhow::Result<()> = async {
            use crate::checks::{named, find_button};
            // A headless seat has no physical keyboard. Retain one standard
            // virtual keyboard so device removal cannot drop GTK focus between captures.
            let keyboard = gtk::gio::Subprocess::newv(&["wtype".as_ref(), "-s".as_ref(), "45000".as_ref()], gtk::gio::SubprocessFlags::NONE)?;
            let directory = PathBuf::from(std::env::var("RAMPI_TEST_ARTIFACTS")?);
            let dashboard = stack.child_by_name("dashboard").context("No dashboard")?;
            let blue = named(&dashboard, "Remote Desktop").context("No remote tile")?;
            let records = Rc::new(RefCell::new(serde_json::Map::new()));
            let capture = |name: &'static str| {
                let (window, blue, directory, records) = (window.clone(), blue.clone(), directory.clone(), records.clone());
                async move {
                    let path = directory.join(format!("interaction-{name}.png"));
                    tool("grim", &[path.to_str().context("Capture path")?]).await?;
                    std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o644))?;
                    let bounds = blue.compute_bounds(&window).context("Tile bounds missing")?;
                    records.borrow_mut().insert(name.into(), serde_json::json!({"width":window.width(),"height":window.height(),"tile":{"x":bounds.x(),"y":bounds.y(),"width":bounds.width(),"height":bounds.height()}}));
                    Ok::<(), anyhow::Error>(())
                }
            };
            delay(35).await; capture("startup-a").await?;
            for name in ["startup-c", "startup-d", "startup-e", "startup-f", "startup-b"] {
                delay(15).await; capture(name).await?;
            }
            delay(450).await;
            // Native virtual pointer events exercise hover and cursor restoration.
            let bounds = blue.compute_bounds(&window).context("No bounds")?;
            let x = (bounds.x() + bounds.width() / 2.0) as i32 - window.width() + 1;
            let y = (bounds.y() + bounds.height() / 2.0) as i32 - window.height() + 1;
            tool("wlrctl", &["pointer", "move", "10000", "10000"]).await?;
            tool("wlrctl", &["pointer", "move", &x.to_string(), &y.to_string()]).await?;
            delay(60).await; capture("hover-a").await?;
            delay(280).await; capture("hover-b").await?;
            ensure!(window.cursor().is_none(), "Pointer motion did not restore cursor");
            ensure!(gtk::prelude::RootExt::focus(&window).is_some_and(|w| w == blue || w.is_ancestor(&blue)), "Actual hover did not select tile");
            tool("wlrctl", &["pointer", "move", "10000", "10000"]).await?;
            tool("wtype", &["-k", "Right", "-s", "50", "-k", "Left"]).await?;
            delay(50).await; capture("focus-a").await?;
            for name in ["focus-c", "focus-d", "focus-b"] {
                delay(90).await; capture(name).await?;
            }
            ensure!(window.cursor().is_some_and(|c| c.name().as_deref() == Some("none")), "Keyboard did not hide cursor");
            conf.borrow_mut().reduce_motion = true;
            blue.queue_draw(); delay(300).await; capture("reduced-a").await?;
            delay(250).await; capture("reduced-b").await?;
            conf.borrow_mut().reduce_motion = false;
            // Enter fields through real keyboard events and GTK's Tab order.
            let settings = stack.child_by_name("settings").context("No settings")?;
            find_button(&dashboard, "⚙  Einstellungen").unwrap().grab_focus();
            tool("wtype", &["-k", "Return"]).await?; delay(200).await;
            ensure!(stack.visible_child_name().as_deref() == Some("settings"));
            ensure!(tabs.visible_child_name().as_deref() == Some("categories"), "Settings must open the category overview");
            let category = named(&settings, "settings-category-host").context("Missing category menu")?;
            category.grab_focus();
            tool("wtype", &["-k", "Up"]).await?;
            let system_category = named(&settings, "settings-category-system").unwrap();
            ensure!(gtk::prelude::RootExt::focus(&window).is_some_and(|focus| focus == system_category || focus.is_ancestor(&system_category)), "Up must wrap to the last category");
            tool("wtype", &["-k", "Down"]).await?;
            delay(180).await;
            capture("settings-categories").await?;
            let bluetooth_category = named(&settings, "settings-category-bluetooth").context("No Bluetooth category")?;
            let hover_bounds = bluetooth_category.compute_bounds(&window).context("No category bounds")?;
            let hover_x = (hover_bounds.x() + hover_bounds.width() / 2.0) as i32 - window.width() + 1;
            let hover_y = (hover_bounds.y() + hover_bounds.height() / 2.0) as i32 - window.height() + 1;
            tool("wlrctl", &["pointer", "move", "10000", "10000"]).await?;
            tool("wlrctl", &["pointer", "move", &hover_x.to_string(), &hover_y.to_string()]).await?;
            delay(100).await;
            ensure!(gtk::prelude::RootExt::focus(&window).is_some_and(|focus| focus == bluetooth_category), "Pointer motion must move the single category selection");
            tool("wtype", &["-k", "Up", "-k", "Up"]).await?;
            delay(180).await;
            ensure!(gtk::prelude::RootExt::focus(&window).is_some_and(|focus| focus == category));
            capture("category-pointer-keyboard").await?;
            records.borrow_mut().get_mut("category-pointer-keyboard").unwrap()["control"] = serde_json::json!({"x":hover_bounds.x(),"y":hover_bounds.y(),"width":hover_bounds.width(),"height":hover_bounds.height()});
            tool("wtype", &["-k", "Up", "-k", "Down"]).await?;
            for (name, pause) in [("control-a", 35), ("control-b", 70), ("control-c", 100), ("control-d", 100)] {
                delay(pause).await;
                capture(name).await?;
                let bounds = category.compute_bounds(&window).context("No native control bounds")?;
                records.borrow_mut().get_mut(name).unwrap()["control"] = serde_json::json!({"x":bounds.x(),"y":bounds.y(),"width":bounds.width(),"height":bounds.height()});
            }
            conf.borrow_mut().reduce_motion = true;
            category.queue_draw();
            for name in ["control-reduced-a", "control-reduced-b"] {
                delay(300).await;
                capture(name).await?;
                let bounds = category.compute_bounds(&window).context("No native control bounds")?;
                records.borrow_mut().get_mut(name).unwrap()["control"] = serde_json::json!({"x":bounds.x(),"y":bounds.y(),"width":bounds.width(),"height":bounds.height()});
            }
            conf.borrow_mut().reduce_motion = false;
            let gtk_settings = gtk::Settings::default().context("No GTK animation settings")?;
            let original_animations = gtk_settings.is_gtk_enable_animations();
            gtk_settings.set_gtk_enable_animations(false);
            for name in ["control-system-reduced-a", "control-system-reduced-b"] {
                delay(300).await;
                capture(name).await?;
                let bounds = category.compute_bounds(&window).context("No native control bounds")?;
                records.borrow_mut().get_mut(name).unwrap()["control"] = serde_json::json!({"x":bounds.x(),"y":bounds.y(),"width":bounds.width(),"height":bounds.height()});
            }
            gtk_settings.set_gtk_enable_animations(original_animations);
            tool("wtype", &["-k", "Return"]).await?; delay(150).await;
            ensure!(tabs.visible_child_name().as_deref() == Some("host"));
            let host = tabs.child_by_name("host").unwrap();
            let name = named(&host, "host-name").unwrap(); name.grab_focus();
            tool("wtype", &["-M","ctrl","-k","a","-m","ctrl","Keyboard profile","-k","Tab","localhost","-k","Tab","alice","-k","Tab","-M","ctrl","-k","a","-m","ctrl","2222","-k","Tab","-k","Tab","-M","ctrl","-k","a","-m","ctrl","1280x720","-k","Tab","-k","Tab","-k","Return"]).await?;
            delay(150).await;
            ensure!(conf.borrow().hosts.len() == 1 && conf.borrow().host()?.name == "Keyboard profile" && conf.borrow().host()?.port == 2222, "Actual Tab/typing/Enter did not save host");
            for category in ["host", "wifi", "bluetooth", "vpn", "board", "system"] {
                tool("wtype", &["-k", "Escape"]).await?; delay(160).await;
                ensure!(stack.visible_child_name().as_deref() == Some("settings") && tabs.visible_child_name().as_deref() == Some("categories"), "Back must return to the category overview");
                if category == "host" {
                    named(&settings, "settings-category-host").unwrap().grab_focus();
                } else {
                    tool("wtype", &["-k", "Down"]).await?;
                }
                // Back restores the last category's focus; Down selects the next row.
                let selected = gtk::prelude::RootExt::focus(&window).context("No category focus")?;
                let expected = named(&settings, &format!("settings-category-{category}")).unwrap();
                ensure!(selected == expected || selected.is_ancestor(&expected), "Arrow navigation did not select {category}");
                tool("wtype", &["-k", "Return"]).await?; delay(100).await;
                ensure!(tabs.visible_child_name().as_deref() == Some(category), "Keyboard did not open {category}");
            }
            tabs.set_visible_child_name("host"); settled(&tabs).await?;
            capture("settings-host").await?;
            tool("wtype", &["-k", "Escape"]).await?; delay(150).await;
            ensure!(tabs.visible_child_name().as_deref() == Some("categories"));
            tool("wtype", &["-k", "Escape"]).await?; delay(150).await;
            ensure!(stack.visible_child_name().as_deref() == Some("dashboard"));
            let status = gtk::Label::new(None);
            crate::views::terminal(&stack, "input-proof", vec!["python3".into(),"-c".into(),"import os,tty;tty.setraw(0);print('RAW_READY',flush=True)\nwhile True:\n b=os.read(0,1);print('KEY_'+b.hex(),flush=True)".into()], &status);
            let term = stack.visible_child().unwrap().downcast::<vte::Terminal>().unwrap();
            for _ in 0..200 { if term.text_format(vte::Format::Text).is_some_and(|s| s.contains("RAW_READY")) { break; } delay(20).await; }
            tool("wtype", &["-k", "Escape"]).await?; delay(100).await;
            ensure!(stack.visible_child_name().as_deref() == Some("terminal-input-proof"), "Escape was stolen from terminal");
            ensure!(term.text_format(vte::Format::Text).is_some_and(|s| s.contains("KEY_1b")), "Terminal did not receive actual Escape");
            tool("wtype", &["-M","ctrl","-M","alt","-k","Home","-m","alt","-m","ctrl"]).await?;
            for _ in 0..200 { if stack.visible_child_name().as_deref() == Some("dashboard") { break; } delay(20).await; }
            ensure!(stack.visible_child_name().as_deref() == Some("dashboard"), "Compositor shortcut did not return to Rampi");
            let input = term.text_format(vte::Format::Text).unwrap_or_default();
            ensure!(input.matches("KEY_").count() == 1, "Reserved shortcut leaked into child PTY");
            // A second real compositor mode proves the responsive layout.
            ensure!(crate::system_settings::outputs().await?[0].name == "HEADLESS-1");
            tool("wlr-randr", &["--output","HEADLESS-1","--custom-mode","1600x900"]).await?;
            delay(400).await; capture("dashboard-1600").await?;
            ensure!(window.width() == 1600 && window.height() == 900);
            for tab in ["wifi", "bluetooth", "system", "board"] {
                stack.set_visible_child_name("settings"); tabs.set_visible_child_name(tab); settled(&stack).await?; settled(&tabs).await?;
                if tab == "wifi" {
                    let page = tabs.child_by_name("wifi").context("Missing Wi-Fi page")?;
                    for title in ["Verbinden", "Trennen"] {
                        ensure!(!find_button(&page, title).context("Missing Wi-Fi action")?.is_sensitive(), "Wi-Fi action without a selected network: {title}");
                    }
                }
                if tab == "bluetooth" {
                    let page = tabs.child_by_name("bluetooth").context("Missing Bluetooth page")?;
                    for title in ["Einschalten", "Ausschalten", "Koppeln", "Verbinden", "Trennen", "Geräte suchen"] {
                        ensure!(!find_button(&page, title).context("Missing Bluetooth action")?.is_sensitive(), "Bluetooth action without a selected adapter/device: {title}");
                    }
                }
                let path = directory.join(format!("interaction-settings-{tab}.png")); tool("grim", &[path.to_str().unwrap()]).await?;
                std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o644))?;
            }
            stack.set_visible_child_name("dashboard");
            tool("wlr-randr", &["--output","HEADLESS-1","--custom-mode","1920x1080"]).await?;
            delay(400).await; capture("dashboard-1920").await?;
            ensure!(window.width() == 1920 && window.height() == 1080);
            ensure!(app.windows().len() == 1);
            std::fs::write(directory.join("interaction-geometry.json"), serde_json::to_vec_pretty(&*records.borrow())?)?;
            std::fs::set_permissions(directory.join("interaction-geometry.json"), std::fs::Permissions::from_mode(0o644))?;
            std::fs::remove_file(rampi_core::config::config_dir()?.join("settings.json"))?;
            tool("wlr-randr", &["--output","HEADLESS-1","--custom-mode","1280x720"]).await?;
            let _ = f;
            keyboard.force_exit(); let _ = keyboard.wait_future().await;
            println!("RAMPI_RUST_INTERACTION_KEYBOARD_OK");
            Ok(())
        }.await;
        if let Err(e) = result { eprintln!("Actual input/visual acceptance failed: {e:#}"); std::process::exit(1); }
        app.quit();
    });
}
