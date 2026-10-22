use crate::{bus, widgets::*};
use gtk::{gio, glib, prelude::*};
use rampi_core::{
    board::Board,
    config::{self},
};
use std::{
    cell::{Cell, RefCell},
    path::PathBuf,
    rc::Rc,
};
use vte::prelude::*;
use webkit6::prelude::*;

pub fn settings(
    stack: &gtk::Stack,
    conf: &Shared,
    status: &gtk::Label,
    f: &Feedback,
) -> (gtk::Box, gtk::Stack) {
    let page = column();
    let header = row();
    let back = button("← Dashboard", f);
    back.set_widget_name("rampi-back");
    let s = stack.clone();
    back.connect_clicked(move |_| {
        let destination = if s
            .child_by_name("setup")
            .is_some_and(|p| p.widget_name() == "setup-return")
        {
            "setup"
        } else {
            "dashboard"
        };
        s.set_visible_child_name(destination);
    });
    header.append(&back);
    let title = label("Einstellungen · persönliches Profil");
    title.add_css_class("heading");
    header.append(&title);
    page.append(&header);
    let tabs = gtk::Stack::builder()
        .hexpand(true)
        .vexpand(true)
        .transition_type(gtk::StackTransitionType::Crossfade)
        .build();
    let switcher = gtk::StackSwitcher::builder().stack(&tabs).build();
    page.append(&switcher);
    page.append(&tabs);
    tabs.add_titled(
        &scroll(&crate::host_view::build(conf, status, f)),
        Some("host"),
        "Host & SSH",
    );
    let system = column();
    let reduce = gtk::CheckButton::with_label("Bewegung reduzieren");
    reduce.set_active(conf.borrow().reduce_motion);
    system.append(&reduce);
    let sound = gtk::CheckButton::with_label("Dezente Klickklänge bei Hover, Fokus und Auswahl");
    sound.set_active(conf.borrow().sound_effects);
    system.append(&sound);
    let (c, s) = (conf.clone(), stack.clone());
    reduce.connect_toggled(move |b| {
        c.borrow_mut().reduce_motion = b.is_active();
        s.set_transition_duration(if b.is_active() { 0 } else { 150 });
    });
    let c = conf.clone();
    sound.connect_toggled(move |b| c.borrow_mut().sound_effects = b.is_active());
    let save = button("Persönliche Einstellungen speichern", f);
    let (c, stat) = (conf.clone(), status.clone());
    save.connect_clicked(move |_| {
        status_result(
            &stat,
            config::config_dir().and_then(|p| c.borrow().save(&p.join("settings.json"))),
        )
    });
    system.append(&save);
    tabs.add_titled(&system, Some("system"), "System");
    tabs.add_titled(&scroll(&wifi(status, f)), Some("wifi"), "WLAN");
    tabs.add_titled(
        &scroll(&bluetooth(stack, status, f)),
        Some("bluetooth"),
        "Bluetooth",
    );
    tabs.add_titled(
        &scroll(&crate::vpn_view::build(stack, f)),
        Some("vpn"),
        "VPN",
    );
    let data = column();
    let source = gtk::Entry::builder()
        .placeholder_text("Persönliche Kanban-JSON-Datei")
        .text(&conf.borrow().board_source)
        .build();
    data.append(&source);
    let board_columns = gtk::Entry::builder()
        .placeholder_text("Spalten in Reihenfolge, durch Komma getrennt")
        .text(conf.borrow().board_columns.join(", "))
        .build();
    data.append(&board_columns);
    let browser_url = gtk::Entry::builder()
        .placeholder_text("Browser-Startseite · HTTPS")
        .text(&conf.borrow().browser_url)
        .build();
    data.append(&browser_url);
    let save = button("Datenquelle und Startseite speichern", f);
    let (c, stat) = (conf.clone(), status.clone());
    save.connect_clicked(move |_| {
        let mut candidate = c.borrow().clone();
        candidate.board_source = source.text().to_string();
        candidate.board_columns = board_columns
            .text()
            .split(',')
            .map(str::trim)
            .filter(|name| !name.is_empty())
            .map(String::from)
            .collect();
        candidate.browser_url = browser_url.text().to_string();
        let result = config::config_dir().and_then(|p| candidate.save(&p.join("settings.json")));
        if result.is_ok() {
            *c.borrow_mut() = candidate;
        }
        status_result(&stat, result);
    });
    data.append(&save);
    tabs.add_titled(&data, Some("board"), "Kanban & Browser");
    let mut child = switcher.first_child();
    while let Some(widget) = child {
        if let Ok(button) = widget.clone().downcast::<gtk::Button>() {
            wire_button(&button, f);
        }
        child = widget.next_sibling();
    }
    (page, tabs)
}
fn wifi(status: &gtk::Label, f: &Feedback) -> gtk::Box {
    let page = column();
    page.append(&label("WLAN · NetworkManager"));
    let controls = row();
    let scan = button("WLANs suchen", f);
    let radio = gtk::Switch::new();
    let state = label("Status noch nicht geprüft");
    controls.append(&scan);
    controls.append(&radio);
    controls.append(&state);
    page.append(&controls);
    let list = gtk::ListBox::new();
    page.append(&list);
    let networks: Rc<RefCell<Vec<bus::Wifi>>> = Rc::new(RefCell::new(vec![]));
    let password = gtk::PasswordEntry::builder()
        .placeholder_text("WLAN-Kennwort")
        .show_peek_icon(true)
        .build();
    page.append(&password);
    let buttons = row();
    let connect = button("Verbinden", f);
    let disconnect = button("Trennen", f);
    buttons.append(&connect);
    buttons.append(&disconnect);
    page.append(&buttons);
    page.append(&label("Suche, Auswahl und Kennworteingabe bleiben auf dieser Seite. Neue Profile gehören ausschließlich deinem Linux-Konto. Unternehmensnetze benötigen ein vorhandenes NetworkManager-Profil."));
    let (l, n, r, st, stat) = (
        list.clone(),
        networks.clone(),
        radio.clone(),
        state.clone(),
        status.clone(),
    );
    scan.connect_clicked(move |b| {
        b.set_sensitive(false);
        let (b, l, n, r, st, stat) = (
            b.clone(),
            l.clone(),
            n.clone(),
            r.clone(),
            st.clone(),
            stat.clone(),
        );
        glib::MainContext::default().spawn_local(async move {
            match bus::wifi_scan(true).await {
                Ok((enabled, rows)) => {
                    while let Some(child) = l.first_child() {
                        l.remove(&child);
                    }
                    for row in &rows {
                        let name = label(&row.label);
                        name.set_margin_top(12);
                        name.set_margin_bottom(12);
                        l.append(&name);
                    }
                    *n.borrow_mut() = rows;
                    r.set_active(enabled);
                    st.set_text(if enabled {
                        "WLAN eingeschaltet"
                    } else {
                        "WLAN ausgeschaltet"
                    });
                }
                Err(e) => stat.set_text(&e.to_string()),
            }
            b.set_sensitive(true);
        });
    });
    let stat = status.clone();
    radio.connect_state_set(move |_, enabled| {
        let stat = stat.clone();
        glib::MainContext::default().spawn_local(async move {
            status_result(&stat, bus::wifi_radio(enabled).await);
        });
        glib::Propagation::Proceed
    });
    let (l, n, p, stat) = (
        list.clone(),
        networks.clone(),
        password.clone(),
        status.clone(),
    );
    connect.connect_clicked(move |b| {
        let selected = l
            .selected_row()
            .and_then(|r| n.borrow().get(r.index() as usize).cloned());
        if let Some(row) = selected {
            let secret = p.text().to_string();
            p.set_text("");
            b.set_sensitive(false);
            let (b, stat) = (b.clone(), stat.clone());
            glib::MainContext::default().spawn_local(async move {
                status_result(&stat, bus::wifi_connect(row, secret).await);
                b.set_sensitive(true);
            });
        }
    });
    let (l, n, stat) = (list, networks, status.clone());
    disconnect.connect_clicked(move |_| {
        if let Some(row) = l
            .selected_row()
            .and_then(|r| n.borrow().get(r.index() as usize).cloned())
        {
            let stat = stat.clone();
            glib::MainContext::default().spawn_local(async move {
                status_result(&stat, bus::wifi_disconnect(&row).await);
            });
        }
    });
    page
}
fn bluetooth(stack: &gtk::Stack, status: &gtk::Label, f: &Feedback) -> gtk::Box {
    let page = column();
    let discovery: Rc<RefCell<Option<bus::BluetoothDiscovery>>> = Rc::new(RefCell::new(None));
    let generation = Rc::new(Cell::new(0u64));
    let (owned, epoch) = (discovery.clone(), generation.clone());
    page.connect_unmap(move |_| {
        epoch.set(epoch.get().wrapping_add(1));
        owned.borrow_mut().take();
    });
    page.append(&label("Bluetooth · BlueZ"));
    let refresh = button("Adapter und Geräte aktualisieren", f);
    page.append(&refresh);
    page.append(&label("Adapter"));
    let picker = gtk::ListBox::new();
    picker.set_selection_mode(gtk::SelectionMode::Single);
    let adapters: Rc<RefCell<Vec<bus::BluetoothAdapter>>> = Rc::new(RefCell::new(vec![]));
    page.append(&picker);
    let list = gtk::ListBox::new();
    page.append(&list);
    let devices: Rc<RefCell<Vec<bus::BluetoothDevice>>> = Rc::new(RefCell::new(vec![]));
    let (a, d, p, l, stat) = (
        adapters.clone(),
        devices.clone(),
        picker.clone(),
        list.clone(),
        status.clone(),
    );
    refresh.connect_clicked(move |b| {
        b.set_sensitive(false);
        let (a, d, p, l, stat, b) = (
            a.clone(),
            d.clone(),
            p.clone(),
            l.clone(),
            stat.clone(),
            b.clone(),
        );
        glib::MainContext::default().spawn_local(async move {
            match bus::bluetooth_snapshot().await {
                Ok((aa, dd)) => {
                    if *a.borrow() != aa {
                        let selected = p.selected_row().and_then(|r| {
                            a.borrow().get(r.index() as usize).map(|a| a.path.clone())
                        });
                        while let Some(child) = p.first_child() {
                            p.remove(&child);
                        }
                        for adapter in &aa {
                            p.append(&label(&format!(
                                "{} · {}",
                                adapter.label,
                                if adapter.powered { "Ein" } else { "Aus" }
                            )));
                        }
                        let index = aa
                            .iter()
                            .position(|a| Some(&a.path) == selected.as_ref())
                            .unwrap_or(0);
                        p.select_row(p.row_at_index(index as i32).as_ref());
                        *a.borrow_mut() = aa;
                    }
                    if *d.borrow() != dd {
                        let selected = l.selected_row().and_then(|r| {
                            d.borrow().get(r.index() as usize).map(|d| d.path.clone())
                        });
                        while let Some(child) = l.first_child() {
                            l.remove(&child);
                        }
                        for device in &dd {
                            l.append(&label(&device.label));
                        }
                        if let Some(index) =
                            dd.iter().position(|d| Some(&d.path) == selected.as_ref())
                        {
                            l.select_row(l.row_at_index(index as i32).as_ref());
                        }
                        *d.borrow_mut() = dd;
                    }
                }
                Err(e) => stat.set_text(&e.to_string()),
            }
            b.set_sensitive(true);
        });
    });
    let controls = gtk::FlowBox::new();
    controls.set_selection_mode(gtk::SelectionMode::None);
    page.append(&controls);
    for (title, op, value) in [
        ("Einschalten", "power", true),
        ("Ausschalten", "power", false),
        ("Koppeln", "pair", false),
        ("Verbinden", "connect", false),
        ("Trennen", "disconnect", false),
        ("Dauerhaft vertrauen", "trust", true),
        ("Kopplung entfernen", "remove", false),
    ] {
        let b = button(title, f);
        controls.insert(&b, -1);
        let (a, l, p, d, stat, s, f) = (
            adapters.clone(),
            list.clone(),
            picker.clone(),
            devices.clone(),
            status.clone(),
            stack.clone(),
            f.clone(),
        );
        b.connect_clicked(move |_| {
            let selected = l
                .selected_row()
                .and_then(|r| d.borrow().get(r.index() as usize).cloned());
            if let Some(device) = &selected
                && ((op == "pair" && device.paired) || (op == "connect" && device.connected))
            {
                stat.set_text("Das Gerät ist bereits gekoppelt beziehungsweise verbunden.");
                return;
            }
            let value = if op == "trust" {
                selected.as_ref().is_some_and(|d| !d.trusted)
            } else {
                value
            };
            let object = if op == "power" {
                a.borrow()
                    .get(p.selected_row().map_or(usize::MAX, |r| r.index() as usize))
                    .map(|a| a.path.clone())
            } else {
                l.selected_row()
                    .and_then(|r| d.borrow().get(r.index() as usize).map(|d| d.path.clone()))
            };
            if let Some(object) = object {
                let stat = stat.clone();
                let execute = move || {
                    let (stat, object) = (stat.clone(), object.clone());
                    glib::MainContext::default().spawn_local(async move {
                        status_result(&stat, bus::bluetooth_action(op, &object, value).await);
                    });
                };
                if op == "trust" || op == "remove" || (op == "power" && !value) {
                    confirm(
                        &s,
                        title,
                        "Diese Änderung gilt systemweit für alle Benutzer.",
                        &f,
                        execute,
                    );
                } else {
                    execute();
                }
            }
        });
    }
    let search = button("Geräte suchen", f);
    let stop = button("Suche beenden", f);
    controls.insert(&search, -1);
    controls.insert(&stop, -1);
    let (owned, epoch, p, a, stat, weak_page) = (
        discovery.clone(),
        generation.clone(),
        picker,
        adapters,
        status.clone(),
        page.downgrade(),
    );
    search.connect_clicked(move |b| {
        if owned.borrow().is_some() {
            return;
        }
        let Some(adapter) = a
            .borrow()
            .get(p.selected_row().map_or(usize::MAX, |r| r.index() as usize))
            .cloned()
        else {
            stat.set_text("Bitte zuerst einen Bluetooth-Adapter auswählen.");
            return;
        };
        epoch.set(epoch.get().wrapping_add(1));
        let ticket = epoch.get();
        b.set_sensitive(false);
        let (owned, epoch, stat, page, b) = (
            owned.clone(),
            epoch.clone(),
            stat.clone(),
            weak_page.clone(),
            b.clone(),
        );
        glib::MainContext::default().spawn_local(async move {
            match bus::BluetoothDiscovery::start(&adapter.path).await {
                Ok(session)
                    if epoch.get() == ticket && page.upgrade().is_some_and(|p| p.is_mapped()) =>
                {
                    *owned.borrow_mut() = Some(session);
                    stat.set_text(
                        "Bluetooth-Suche läuft. Gefundene Geräte erscheinen in dieser Seite.",
                    );
                }
                Ok(_) => {} // Closing this client releases a late discovery reply.
                Err(e) if epoch.get() == ticket => stat.set_text(&e.to_string()),
                Err(_) => {}
            }
            b.set_sensitive(true);
        });
    });
    let stat = status.clone();
    stop.connect_clicked(move |_| {
        generation.set(generation.get().wrapping_add(1));
        let session = discovery.borrow_mut().take();
        if let Some(session) = session {
            let stat = stat.clone();
            glib::MainContext::default().spawn_local(async move {
                status_result(&stat, session.stop().await);
            });
        }
    });
    let weak_refresh = refresh.downgrade();
    page.connect_map(move |_| {
        if let Some(refresh) = weak_refresh.upgrade() {
            refresh.emit_clicked();
        }
    });
    let (weak_page, weak_refresh) = (page.downgrade(), refresh.downgrade());
    glib::timeout_add_seconds_local(2, move || {
        let (Some(page), Some(refresh)) = (weak_page.upgrade(), weak_refresh.upgrade()) else {
            return glib::ControlFlow::Break;
        };
        if page.is_mapped() && refresh.is_sensitive() {
            refresh.emit_clicked();
        }
        glib::ControlFlow::Continue
    });
    page.append(&label("Kopplungen und Vertrauen gelten für das ganze Gerät. Neue Geräte erhalten nicht automatisch dauerhaftes Vertrauen."));
    page
}
pub fn confirm(
    stack: &gtk::Stack,
    title: &str,
    text: &str,
    f: &Feedback,
    action: impl Fn() + 'static,
) {
    if let Some(old) = stack.child_by_name("confirmation") {
        stack.remove(&old);
    }
    let previous = stack
        .visible_child_name()
        .map(|s| s.to_string())
        .unwrap_or_else(|| "dashboard".into());
    let page = column();
    let heading = label(title);
    heading.add_css_class("heading");
    page.append(&heading);
    page.append(&label(text));
    let no = button("Abbrechen", f);
    no.set_widget_name("rampi-back");
    let yes = button("Bewusst bestätigen", f);
    page.append(&no);
    page.append(&yes);
    stack.add_named(&page, Some("confirmation"));
    let (s, p) = (stack.clone(), previous.clone());
    no.connect_clicked(move |_| s.set_visible_child_name(&p));
    let (s, p) = (stack.clone(), previous);
    yes.connect_clicked(move |_| {
        s.set_visible_child_name(&p);
        action();
    });
    stack.set_visible_child_name("confirmation");
    no.grab_focus();
}
pub fn terminal(
    stack: &gtk::Stack,
    name: &str,
    args: Vec<std::ffi::OsString>,
    status: &gtk::Label,
) {
    let key = format!("terminal-{name}");
    if stack.child_by_name(&key).is_some() {
        stack.set_visible_child_name(&key);
        return;
    }
    let term = vte::Terminal::new();
    term.set_hexpand(true);
    term.set_vexpand(true);
    term.set_scrollback_lines(5000);
    let name = key.clone();
    stack.add_named(&term, Some(&key));
    stack.set_visible_child_name(&key);
    let strings: Vec<String> = args
        .iter()
        .map(|s| s.to_string_lossy().to_string())
        .collect();
    let argv: Vec<&str> = strings.iter().map(String::as_str).collect();
    let stat = status.clone();
    term.spawn_async(
        vte::PtyFlags::DEFAULT,
        None,
        &argv,
        &[],
        glib::SpawnFlags::SEARCH_PATH,
        || {},
        -1,
        None::<&gio::Cancellable>,
        move |result| {
            if let Err(e) = result {
                stat.set_text(&format!("Terminal konnte nicht gestartet werden: {e}"));
            }
        },
    );
    let s = stack.downgrade();
    term.connect_child_exited(move |_, code| {
        if let Some(s) = s.upgrade() {
            let was_visible = s.visible_child_name().is_some_and(|key| key == name);
            if let Some(child) = s.child_by_name(&name) {
                s.remove(&child);
            }
            if was_visible {
                s.set_visible_child_name("dashboard");
            }
        }
        println!("RAMPI_TERMINAL_EXIT={code}");
    });
    term.grab_focus();
}
pub fn board_preview(conf: &Shared) -> gtk::Box {
    let panel = column();
    panel.add_css_class("panel");
    let title = label("Kanban Board");
    title.add_css_class("heading");
    panel.append(&title);
    panel.append(&label("Projektübersicht · Nur lesen"));
    let columns = row();
    columns.set_homogeneous(true);
    columns.set_vexpand(true);
    panel.append(&columns);
    let (c, cols) = (conf.clone(), columns.clone());
    panel.connect_map(move |_| {
        while let Some(child) = cols.first_child() {
            cols.remove(&child);
        }
        let conf = c.borrow();
        let board = if conf.board_source.is_empty() {
            Board::default()
        } else {
            match Board::load(&PathBuf::from(&conf.board_source)) {
                Ok(b) => b,
                Err(_) => {
                    cols.append(&label(
                        "Datenquelle nicht verfügbar. In den Einstellungen prüfen.",
                    ));
                    return;
                }
            }
        };
        for (index, status) in board.columns(&conf.board_columns).iter().enumerate() {
            let lane = column();
            lane.set_hexpand(true);
            lane.add_css_class("board-lane");
            lane.add_css_class(&format!("lane-{}", index % 4));
            let heading = label(status);
            heading.set_max_width_chars(10);
            heading.add_css_class("lane-title");
            lane.append(&heading);
            for card in board.cards.iter().filter(|c| c.status == *status).take(3) {
                let text = label(&card.title);
                text.set_max_width_chars(14);
                text.add_css_class("board-card");
                lane.append(&text);
            }
            cols.append(&lane);
        }
    });
    panel
}
pub fn remote(stack: &gtk::Stack, conf: &Shared, status: &gtk::Label, f: &Feedback) -> gtk::Box {
    let page = column();
    let back = button("← Zurück", f);
    back.set_widget_name("rampi-back");
    let s = stack.clone();
    back.connect_clicked(move |_| {
        s.set_visible_child_name(
            if s.child_by_name("setup")
                .is_some_and(|p| p.widget_name() == "setup-return")
            {
                "setup"
            } else {
                "dashboard"
            },
        )
    });
    page.append(&back);
    page.append(&label("Deine Windows-Workstation\nRDP meldet dich mit deinem Windows-Konto an. Sunshine teilt die aktive Windows-Konsole."));
    let b = button("RDP · nativer Wayland-Client", f);
    let (host_settings, s, stat) = (conf.clone(), stack.clone(), status.clone());
    b.connect_clicked(move |_| {
        let result = host_settings
            .borrow()
            .host()
            .and_then(rampi_core::launch::rdp);
        match result {
            Ok(args) => terminal(&s, "rdp", args, &stat),
            Err(e) => stat.set_text(&e.to_string()),
        }
    });
    page.append(&b);
    for (title, pair) in [
        ("Desktop-Streaming öffnen", false),
        ("Streaming-Host koppeln", true),
    ] {
        let b = button(title, f);
        let (conf, s, stat) = (conf.clone(), stack.clone(), status.clone());
        b.connect_clicked(move |_| {
            let result = conf
                .borrow()
                .host()
                .and_then(|h| rampi_core::launch::streaming(h, pair));
            match result {
                Ok(args) => terminal(&s, if pair { "stream-pair" } else { "stream" }, args, &stat),
                Err(e) => stat.set_text(&e.to_string()),
            }
        });
        page.append(&b);
    }
    page
}
pub fn browser(stack: &gtk::Stack, conf: &Shared, status: &gtk::Label, f: &Feedback) {
    if stack.child_by_name("browser").is_some() {
        stack.set_visible_child_name("browser");
        return;
    }
    let page = column();
    let bar = row();
    let back = button("←", f);
    let forward = button("→", f);
    let reload = button("↻", f);
    let address = gtk::Entry::builder()
        .text(&conf.borrow().browser_url)
        .hexpand(true)
        .build();
    bar.append(&back);
    bar.append(&forward);
    bar.append(&reload);
    bar.append(&address);
    page.append(&bar);
    let directory = match config::config_dir() {
        Ok(d) => d.join("browser-native"),
        Err(e) => {
            status.set_text(&e.to_string());
            return;
        }
    };
    if let Err(e) = std::fs::create_dir_all(&directory) {
        status.set_text(&e.to_string());
        return;
    }
    use std::os::unix::fs::PermissionsExt;
    if let Err(e) = std::fs::set_permissions(&directory, std::fs::Permissions::from_mode(0o700)) {
        status.set_text(&e.to_string());
        return;
    }
    let session =
        webkit6::NetworkSession::new(directory.to_str(), directory.join("cache").to_str());
    let web = webkit6::WebView::builder()
        .network_session(&session)
        .hexpand(true)
        .vexpand(true)
        .build();
    crate::browser_prompts::install(&web, stack, status, f);
    let w = web.clone();
    back.connect_clicked(move |_| w.go_back());
    let w = web.clone();
    forward.connect_clicked(move |_| w.go_forward());
    let w = web.clone();
    reload.connect_clicked(move |_| w.reload());
    let (w, stat) = (web.clone(), status.clone());
    address.connect_activate(move |e| {
        let uri = e.text();
        match config::validate_https(&uri) {
            Ok(()) => w.load_uri(&uri),
            Err(error) => stat.set_text(&error.to_string()),
        }
    });
    let w = web.downgrade();
    web.connect_create(move |_, action| {
        if let (Some(view), Some(uri)) = (w.upgrade(), action.request().and_then(|r| r.uri())) {
            view.load_uri(&uri);
        }
        None
    });
    web.load_uri(&conf.borrow().browser_url);
    page.append(&web);
    stack.add_named(&page, Some("browser"));
    stack.set_visible_child_name("browser");
}

pub fn go_back(stack: &gtk::Stack) {
    fn find(root: &gtk::Widget) -> Option<gtk::Button> {
        if root.widget_name() == "rampi-back" {
            return root.clone().downcast().ok();
        }
        let mut next = root.first_child();
        while let Some(child) = next {
            if let Some(b) = find(&child) {
                return Some(b);
            }
            next = child.next_sibling();
        }
        None
    }
    if let Some(b) = stack.visible_child().and_then(|w| find(&w)) {
        b.emit_clicked();
    } else {
        stack.set_visible_child_name("dashboard");
    }
}
