use crate::{views, widgets::*};
use gtk::{gdk, gio, glib, prelude::*};
use rampi_core::config::{self, Settings};
use std::{cell::RefCell, rc::Rc};

pub fn run() {
    let app = gtk::Application::builder()
        .application_id("org.rampi.Workstation")
        .build();
    app.connect_activate(|app| {
        if let Some(window) = app.active_window() {
            app.activate_action("dashboard", None);
            window.present();
        } else {
            build(app);
        }
    });
    app.run_with_args::<&str>(&[]);
}
fn build(app: &gtk::Application) {
    let css = gtk::CssProvider::new();
    css.load_from_string(include_str!("style.css"));
    if let Some(display) = gdk::Display::default() {
        gtk::style_context_add_provider_for_display(
            &display,
            &css,
            gtk::STYLE_PROVIDER_PRIORITY_APPLICATION,
        );
    }
    let status = label("");
    status.add_css_class("status");
    let loaded = config::config_dir().and_then(|p| Settings::load(&p.join("settings.json")));
    let settings = Rc::new(RefCell::new(match loaded {
        Ok(s) => s,
        Err(e) => {
            status.set_text(&format!(
                "Konfiguration: {e}. Vorhandene Datei bleibt erhalten."
            ));
            Settings::default()
        }
    }));
    let feedback = Feedback::new(settings.clone());
    let window = gtk::ApplicationWindow::builder()
        .application(app)
        .title("Rampi")
        .default_width(1600)
        .default_height(900)
        .build();
    let focus_feedback = feedback.clone();
    window.connect_focus_widget_notify(move |_| focus_feedback.play(false));
    let root = column();
    root.set_margin_top(24);
    root.set_margin_bottom(20);
    root.set_margin_start(24);
    root.set_margin_end(24);
    let stack = gtk::Stack::builder()
        .hexpand(true)
        .vexpand(true)
        .vhomogeneous(false)
        .hhomogeneous(false)
        .transition_type(gtk::StackTransitionType::Crossfade)
        .transition_duration(if settings.borrow().reduce_motion {
            0
        } else {
            150
        })
        .build();
    root.append(&stack);
    let dashboard_action = gio::SimpleAction::new("dashboard", None);
    let route = stack.clone();
    dashboard_action.connect_activate(move |_, _| {
        views::go_back(&route);
        route.set_visible_child_name("dashboard");
    });
    app.add_action(&dashboard_action);
    root.append(&status);
    window.set_child(Some(&root));
    let dashboard = column();
    let header = row();
    let logo = gtk::DrawingArea::new();
    logo.set_content_width(80);
    logo.set_content_height(80);
    if let Ok(pixbuf) = gtk::gdk_pixbuf::Pixbuf::from_file(assets().join("branding/logo.png")) {
        logo.set_draw_func(move |_, cr, w, h| {
            let scale = (w as f64 / 1100.0).min(h as f64 / 730.0);
            cr.translate(
                (w as f64 - 1100.0 * scale) / 2.0,
                (h as f64 - 730.0 * scale) / 2.0,
            );
            cr.scale(scale, scale);
            cr.rectangle(0.0, 0.0, 1100.0, 730.0);
            cr.clip();
            cr.set_source_pixbuf(&pixbuf, -75.0, -100.0);
            let _ = cr.paint();
        });
    }
    header.append(&logo);
    let brand = label("Rampi");
    brand.add_css_class("brand");
    brand.set_hexpand(true);
    header.append(&brand);
    let wifi = icon_button("WLAN", "wifi", &feedback);
    wifi.set_valign(gtk::Align::Center);
    wifi.set_widget_name("dashboard-wifi");
    let bluetooth = icon_button("Bluetooth", "bluetooth", &feedback);
    bluetooth.set_valign(gtk::Align::Center);
    bluetooth.set_widget_name("dashboard-bluetooth");
    header.append(&wifi);
    header.append(&bluetooth);
    dashboard.append(&header);
    let modules = [
        (
            "Kanban Board",
            "Projekte im Blick",
            (1.0, 0.23, 0.38),
            false,
            "kanban",
        ),
        ("ChatGPT", "Codex", (0.03, 0.49, 0.96), false, "codex"),
        ("Claude", "Claude Code", (1.0, 0.83, 0.24), true, "claude"),
        (
            "Gemini",
            "Antigravity CLI",
            (0.08, 0.80, 0.73),
            true,
            "antigravity",
        ),
        (
            "Remote Desktop",
            "Windows-Workstation",
            (0.29, 0.20, 0.78),
            false,
            "remote",
        ),
        (
            "Webbrowser",
            "Dein Fenster ins Web",
            (0.11, 0.20, 0.28),
            false,
            "browser",
        ),
    ];
    let tiles = row();
    tiles.set_homogeneous(true);
    tiles.set_vexpand(true);
    let mut tile_buttons = vec![];
    for (i, (title, sub, color, dark, name)) in modules.into_iter().enumerate() {
        let b = tile(
            TileSpec {
                title,
                subtitle: sub,
                color,
                dark,
                delay: i as f64 * 0.035,
            },
            &settings,
            &feedback,
        );
        tiles.append(&b);
        let (s, conf, stat, f) = (
            stack.clone(),
            settings.clone(),
            status.clone(),
            feedback.clone(),
        );
        b.connect_clicked(move |_| {
            if name == "browser" {
                views::browser(&s, &conf, &stat, &f);
            } else if ["codex", "claude", "antigravity"].contains(&name) {
                let args = conf
                    .borrow()
                    .host()
                    .and_then(|h| rampi_core::launch::ssh(h, name));
                match args {
                    Ok(args) => views::terminal(&s, name, args, &stat),
                    Err(e) => stat.set_text(&e.to_string()),
                }
            } else {
                s.set_visible_child_name(name);
            }
        });
        tile_buttons.push(b);
    }
    dashboard.append(&tiles);
    let previews = row();
    previews.set_homogeneous(true);
    previews.append(&views::board_preview(&settings));
    let assistant_previews = gtk::Grid::new();
    assistant_previews.set_column_homogeneous(true);
    assistant_previews.set_row_homogeneous(true);
    assistant_previews.set_column_spacing(14);
    assistant_previews.set_row_spacing(14);
    for (i, title) in [
        "ChatGPT / Codex",
        "Claude / Claude Code",
        "Gemini / Antigravity",
        "Webbrowser",
    ]
    .iter()
    .enumerate()
    {
        let host = settings
            .borrow()
            .hosts
            .get(settings.borrow().active_host)
            .map(|h| format!("{} · {}@{}", h.name, h.username, h.address))
            .unwrap_or_else(|| "Windows-Host noch nicht eingerichtet".into());
        let text = if i == 3 {
            format!("{} · Lokaler Browser", settings.borrow().browser_url)
        } else {
            host
        };
        let panel = column();
        panel.add_css_class("panel");
        panel.set_hexpand(true);
        panel.set_vexpand(true);
        let heading = label(title);
        heading.set_single_line_mode(true);
        heading.set_ellipsize(gtk::pango::EllipsizeMode::End);
        heading.add_css_class("preview-title");
        panel.append(&heading);
        let detail = label(&text);
        detail.set_max_width_chars(25);
        detail.set_lines(2);
        detail.set_ellipsize(gtk::pango::EllipsizeMode::End);
        panel.append(&detail);
        assistant_previews.attach(&panel, (i % 2) as i32, (i / 2) as i32, 1, 1);
    }
    previews.append(&assistant_previews);
    dashboard.append(&previews);
    let footer = row();
    let open_settings = button("⚙  Einstellungen", &feedback);
    footer.append(&open_settings);
    let console = button("Konsole", &feedback);
    footer.append(&console);
    let version = label(&format!(
        "Rampi {} · Rust / Wayland",
        env!("CARGO_PKG_VERSION")
    ));
    version.set_hexpand(true);
    version.set_xalign(1.0);
    footer.append(&version);
    dashboard.append(&footer);
    stack.add_named(&dashboard, Some("dashboard"));
    let (s, stat) = (stack.clone(), status.clone());
    console
        .connect_clicked(move |_| views::terminal(&s, "console", vec!["/bin/bash".into()], &stat));
    let (settings_page, tabs) = views::settings(&stack, &settings, &status, &feedback);
    stack.add_named(&settings_page, Some("settings"));
    for (b, page) in [
        (&wifi, "wifi"),
        (&bluetooth, "bluetooth"),
        (&open_settings, "host"),
    ] {
        let (s, t) = (stack.clone(), tabs.clone());
        b.connect_clicked(move |_| {
            t.set_visible_child_name(page);
            s.set_visible_child_name("settings");
        });
    }
    stack.add_named(
        &views::board(&stack, &settings, &status, &feedback),
        Some("kanban"),
    );
    stack.add_named(
        &views::remote(&stack, &settings, &status, &feedback),
        Some("remote"),
    );
    let agent = Rc::new(RefCell::new(None));
    let retained = agent.clone();
    app.connect_shutdown(move |_| {
        retained.borrow_mut().take();
    });
    let (s, stat, f) = (stack.clone(), status.clone(), feedback.clone());
    glib::MainContext::default().spawn_local(async move {
        match crate::pairing::register(s, stat.clone(), f).await {
            Ok(value) => *agent.borrow_mut() = Some(value),
            Err(_) => stat
                .set_text("Bluetooth-Dienst nicht verfügbar; die übrigen Module bleiben nutzbar."),
        }
    });
    let keys = gtk::EventControllerKey::new();
    keys.set_propagation_phase(gtk::PropagationPhase::Capture);
    let (s, buttons, weak) = (stack.clone(), tile_buttons.clone(), window.downgrade());
    keys.connect_key_pressed(move |_, key, _, mods| {
        if (key == gdk::Key::Escape
            || (key == gdk::Key::Home
                && mods.contains(gdk::ModifierType::CONTROL_MASK | gdk::ModifierType::ALT_MASK)))
            && s.visible_child_name().is_some_and(|n| n != "dashboard")
        {
            views::go_back(&s);
            return glib::Propagation::Stop;
        }
        if let Some(w) = weak.upgrade() {
            w.set_cursor_from_name(Some("none"));
        }
        if s.visible_child_name().is_some_and(|n| n == "dashboard")
            && [gdk::Key::Left, gdk::Key::Right].contains(&key)
        {
            let current = weak
                .upgrade()
                .and_then(|w| gtk::prelude::RootExt::focus(&w))
                .and_then(|focused| {
                    buttons.iter().position(|b| {
                        &focused == b.upcast_ref::<gtk::Widget>() || focused.is_ancestor(b)
                    })
                })
                .unwrap_or(0);
            let next = if key == gdk::Key::Right {
                (current + 1) % 6
            } else {
                (current + 5) % 6
            };
            buttons[next].grab_focus();
            return glib::Propagation::Stop;
        }
        glib::Propagation::Proceed
    });
    window.add_controller(keys);
    let pointer = gtk::EventControllerMotion::new();
    let weak = window.downgrade();
    pointer.connect_motion(move |_, _, _| {
        if let Some(w) = weak.upgrade() {
            w.set_cursor_from_name(None);
        }
    });
    window.add_controller(pointer);
    stack.set_visible_child_name("dashboard");
    if !std::env::args().any(|a| a == "--windowed") {
        window.fullscreen();
    }
    window.present();
    tile_buttons[0].grab_focus();
    if std::env::args().any(|a| a == "--keyboard-test") {
        crate::checks::keyboard(app, &stack);
    }
    if std::env::args().any(|a| a == "--sound-test") {
        let (app, f) = (app.clone(), feedback.clone());
        glib::timeout_add_local(std::time::Duration::from_millis(150), move || {
            if !f.prepared() {
                return glib::ControlFlow::Continue;
            }
            f.play(true);
            let app = app.clone();
            glib::timeout_add_local_once(std::time::Duration::from_millis(2500), move || {
                println!("RAMPI_RUST_SOUND_PREPARED_OK");
                app.quit();
            });
            glib::ControlFlow::Break
        });
    }
    if std::env::args().any(|a| a == "--embedded-test") {
        let (a, s) = (app.clone(), stack.clone());
        glib::timeout_add_local_once(std::time::Duration::from_millis(300), move || {
            crate::checks::embedded(&a, &s)
        });
    }
    if std::env::args().any(|a| a == "--smoke-test") {
        let app = app.clone();
        glib::timeout_add_local_once(std::time::Duration::from_millis(1000), move || {
            println!("RAMPI_RUST_SMOKE_OK");
            app.quit();
        });
    }
    if std::env::args().any(|a| a == "--self-test") {
        let (app, w, s, t, b) = (
            app.clone(),
            window.clone(),
            stack.clone(),
            tabs.clone(),
            tile_buttons,
        );
        glib::timeout_add_local_once(std::time::Duration::from_millis(1000), move || {
            assert_eq!(app.windows().len(), 1);
            assert_eq!(b.len(), 6);
            for name in ["wifi", "bluetooth", "host", "system", "vpn", "board"] {
                t.set_visible_child_name(name);
                s.set_visible_child_name("settings");
                assert_eq!(t.visible_child_name().as_deref(), Some(name));
                assert_eq!(app.windows().len(), 1);
            }
            s.set_visible_child_name("dashboard");
            glib::timeout_add_local_once(std::time::Duration::from_millis(250), move || {
                let focused = b[2].grab_focus();
                if !focused || !w.is_visible() {
                    eprintln!(
                        "Rust UI focus check failed: focused={focused} mapped={}",
                        b[2].is_mapped()
                    );
                    std::process::exit(1);
                }
                println!(
                    "RAMPI_RUST_UI_OK backend={} windows=1 modules=6 settings=6",
                    gdk::Display::default()
                        .map(|d| d.type_().name().to_string())
                        .unwrap_or_default()
                );
                app.quit();
            });
        });
    }
}
