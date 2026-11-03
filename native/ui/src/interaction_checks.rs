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
            settled(&tabs).await?;
            let entry_bounds = name.compute_bounds(&window).context("No actual entry bounds")?;
            tool("wlrctl", &["pointer", "move", "-10000", "-10000"]).await?;
            tool("wlrctl", &["pointer", "move", &(entry_bounds.x() + 30.0).to_string(), &(entry_bounds.y() + 20.0).to_string()]).await?;
            delay(50).await;
            let surface = window.surface().context("No actual native surface")?;
            let pointer = gtk::prelude::WidgetExt::display(&window).default_seat().and_then(|seat| seat.pointer()).context("No actual pointer")?;
            let pointer_name = || surface.device_cursor(&pointer).or_else(|| surface.cursor()).and_then(|cursor| cursor.name()).map(|name| name.to_string());
            ensure!(pointer_name().as_deref() != Some("none"), "Actual entry cursor was not visible");
            tool("wtype", &["x"]).await?; delay(80).await;
            ensure!(pointer_name().as_deref() == Some("none"), "Actual entry cursor remained visible during keyboard input");
            tool("wlrctl", &["pointer", "move", "5", "0"]).await?; delay(50).await;
            ensure!(pointer_name().as_deref() != Some("none"), "Actual entry cursor did not return on pointer motion");
            tool("wtype", &["-M","ctrl","-k","a","-m","ctrl","Keyboard profile","-k","Tab","localhost","-k","Tab","alice","-k","Tab","-M","ctrl","-k","a","-m","ctrl","2222","-k","Tab","-k","Tab","-M","ctrl","-k","a","-m","ctrl","1280x720","-k","Tab"]).await?;
            delay(550).await;
            ensure!(conf.borrow().hosts.len() == 1 && conf.borrow().host()?.name == "Keyboard profile" && conf.borrow().host()?.port == 2222, "Actual typing/focus-leave did not automatically save host");
            ensure!(crate::checks::find_button(&host, "Hostprofil speichern").is_none());
            let config_path = rampi_core::config::config_dir()?.join("settings.json");
            let saved_bytes = std::fs::read(&config_path)?;
            let port = named(&host, "host-port").unwrap().downcast::<gtk::Entry>().unwrap();
            port.set_text("0"); delay(550).await;
            ensure!(std::fs::read(&config_path)? == saved_bytes && conf.borrow().host()?.port == 2222, "Invalid autosave replaced a valid profile");
            port.set_text("2200");
            tabs.set_visible_child_name("categories");
            ensure!(rampi_core::config::Settings::load(&config_path)?.host()?.port == 2200, "Page exit lost a pending automatic edit");
            tabs.set_visible_child_name("host"); settled(&tabs).await?;
            port.set_text("2222"); delay(550).await;
            ensure!(conf.borrow().hosts.len() == 1, "Typing created duplicate host profiles");
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
                    ensure!(!named(&page, "bluetooth-power").context("Missing Bluetooth slide switch")?.is_sensitive(), "Power enabled without a selected adapter");
                    let actions = named(&page, "bluetooth-actions").context("Missing Bluetooth actions")?;
                    let mut cell = actions.first_child();
                    while let Some(item) = cell {
                        ensure!(!item.is_focusable(), "Empty action wrappers must not receive keyboard focus");
                        cell = item.next_sibling();
                    }

                    for title in ["Koppeln", "Verbinden", "Trennen", "Geräte suchen"] {
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
            tool("wlr-randr", &["--output","HEADLESS-1","--custom-mode","1280x720"]).await?;
            stack.set_visible_child_name("settings");
            tabs.set_visible_child_name("system");
            tool("wlrctl", &["pointer", "move", "-10000", "-10000"]).await?;
            let toggle = named(&stack.clone().upcast(), "settings-motion-switch")
                .context("No motion slide switch")?.downcast::<gtk::Switch>().unwrap();
            toggle.grab_focus();
            for icon in ["accessibility", "volume-2", "monitor", "wifi", "bluetooth", "shield-check", "columns-3", "settings"] {
                let image = named(&stack.clone().upcast(), &format!("rampi-icon-{icon}"))
                    .context("Bundled navigation icon missing")?.downcast::<gtk::Image>().unwrap();
                ensure!(image.storage_type()==gtk::ImageType::Paintable,
                    "Bundled icon silently fell back to a missing-image symbol: {icon}");
            }
            conf.borrow_mut().reduce_motion = false;
            delay(600).await;
            let idle_start = crate::widgets::motion_counts();
            delay(600).await;
            let idle_end = crate::widgets::motion_counts();
            ensure!(idle_start == idle_end, "Idle controls kept a frame callback alive");
            tabs.set_visible_child_name("categories");
            named(&stack.clone().upcast(), "settings-category-host").unwrap().grab_focus();
            delay(600).await;
            let active_start = crate::widgets::motion_counts();
            let active_wall = std::time::Instant::now();
            delay(600).await;
            let active_end = crate::widgets::motion_counts();
            let active_paints = active_end.1 - active_start.1;
            let active_ms = active_wall.elapsed().as_secs_f64() * 1000.0;
            ensure!(active_paints >= 2 && active_paints as f64 <= (active_ms * 31.0 / 1000.0).ceil() + 2.0, "Active surface paint budget exceeded: {active_paints}");
            conf.borrow_mut().reduce_motion = true;
            window.queue_draw();
            delay(400).await;
            let reduced_start = crate::widgets::motion_counts();
            delay(600).await;
            let reduced_end = crate::widgets::motion_counts();
            ensure!(reduced_start == reduced_end, "Reduced motion retained a frame callback");
            conf.borrow_mut().reduce_motion = false;
            let executable = std::fs::read("/proc/self/exe")?;
            let animation = serde_json::json!({"schema":1,
                "scope":"actual GTK frame callbacks in headless Wayland; not Raspberry Pi timing",
                "idle_ticks":idle_end.0-idle_start.0,"reduced_ticks":reduced_end.0-reduced_start.0,
                "active_paints":active_paints,"active_window_ms":active_ms,"native_elf_sha256":
                glib::compute_checksum_for_data(glib::ChecksumType::Sha256,&executable).unwrap().as_str(),
                "single_window":app.windows().len()==1,"complete_product_acceptance":false});
            let receipt = directory.join("animation-scheduling.json");
            std::fs::write(&receipt, serde_json::to_vec_pretty(&animation)?)?;
            std::fs::set_permissions(&receipt, std::fs::Permissions::from_mode(0o644))?;
            println!("RAMPI_ANIMATION_IDLE_AND_PAINT_BUDGET_OK {animation}");
            let system = tabs.child_by_name("system").context("No system page")?;
            for caption in ["Persönliche Einstellungen speichern", "Sprache für die nächste Anmeldung speichern", "Tastaturbelegung anwenden"] {
                ensure!(crate::checks::find_button(&system, caption).is_none(), "Settings retained a save action");
            }
            let reduce = named(&system, "settings-motion-switch").unwrap().downcast::<gtk::Switch>().unwrap();
            let previous = conf.borrow().reduce_motion;
            let path = rampi_core::config::config_dir()?.join("settings.json");
            let original = std::fs::read(&path)?;
            std::fs::write(&path, b"{")?;
            reduce.set_active(!previous);
            ensure!(conf.borrow().reduce_motion == previous && reduce.is_active() == previous, "Failed automatic save changed the live switch");
            ensure!(std::fs::read(&path)? == b"{", "Failed automatic save overwrote an existing unreadable file");
            std::fs::write(&path, original)?;
            reduce.set_active(!previous);
            ensure!(rampi_core::config::Settings::load(&path)?.reduce_motion == !previous, "Switch did not automatically persist after recovery");
            reduce.set_active(previous);
            println!("RAMPI_AUTOSAVE_VALIDATION_PAGE_FLUSH_AND_WRITE_FAILURE_OK");
            std::fs::remove_file(&path)?;
            let _ = f;
            keyboard.force_exit(); let _ = keyboard.wait_future().await;
            println!("RAMPI_RUST_INTERACTION_KEYBOARD_OK");
            Ok(())
        }.await;
        if let Err(e) = result { eprintln!("Actual input/visual acceptance failed: {e:#}"); std::process::exit(1); }
        app.quit();
    });
}
