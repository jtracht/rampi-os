use crate::{bus, widgets::*};
use gtk::{gio, glib, prelude::*};
use rampi_core::i18n::text as tr;
use rampi_core::{
    board::Board,
    config::{self},
};
use std::{
    cell::{Cell, RefCell},
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
    let back = button(&tr("back-dashboard", &[]), f);
    back.set_widget_name("rampi-back");
    let tabs = gtk::Stack::builder()
        .hexpand(true)
        .vexpand(true)
        .transition_type(gtk::StackTransitionType::Crossfade)
        .transition_duration(if conf.borrow().reduce_motion { 0 } else { 150 })
        .build();
    let (s, categories) = (stack.clone(), tabs.clone());
    back.connect_clicked(move |_| {
        let destination = if s
            .child_by_name("setup")
            .is_some_and(|p| p.widget_name() == "setup-return")
        {
            "setup"
        } else if categories.visible_child_name().as_deref() != Some("categories") {
            categories.set_visible_child_name("categories");
            return;
        } else {
            "dashboard"
        };
        s.set_visible_child_name(destination);
    });
    let (root, pages) = (stack.clone(), tabs.clone());
    back.connect_map(move |button| {
        let wizard = root
            .child_by_name("setup")
            .is_some_and(|p| p.widget_name() == "setup-return");
        button.set_label(&tr(
            if wizard {
                "back-setup"
            } else if pages.visible_child_name().as_deref() == Some("categories") {
                "back-dashboard"
            } else {
                "back-settings"
            },
            &[],
        ));
    });
    header.append(&back);
    let title = label(&tr("settings-heading", &[]));
    title.add_css_class("heading");
    header.append(&title);
    page.append(&header);
    let menu = column();
    menu.add_css_class("settings-categories");
    menu.append(&label(&tr("settings-instructions", &[])));
    let mut choices = Vec::new();
    let last_category = Rc::new(Cell::new(0usize));
    for (name, heading, hint, icon) in [
        (
            "host",
            "category-host",
            "category-host-description",
            "computer-symbolic",
        ),
        (
            "wifi",
            "category-wifi",
            "category-wifi-description",
            "network-wireless-symbolic",
        ),
        (
            "bluetooth",
            "category-bluetooth",
            "category-bluetooth-description",
            "bluetooth-symbolic",
        ),
        (
            "vpn",
            "category-vpn",
            "category-vpn-description",
            "network-vpn-symbolic",
        ),
        (
            "board",
            "category-board",
            "category-board-description",
            "view-list-symbolic",
        ),
        (
            "system",
            "category-system",
            "category-system-description",
            "preferences-system-symbolic",
        ),
    ] {
        let choice = button("", f);
        choice.set_widget_name(&format!("settings-category-{name}"));
        choice.add_css_class("settings-category");
        let content = row();
        let image = gtk::Image::from_icon_name(icon);
        image.set_pixel_size(28);
        content.append(&image);
        let text = gtk::Box::new(gtk::Orientation::Vertical, 3);
        text.set_hexpand(true);
        let heading_label = label(&tr(heading, &[]));
        heading_label.add_css_class("preview-title");
        text.append(&heading_label);
        let description = label(&tr(hint, &[]));
        description.add_css_class("status");
        text.append(&description);
        content.append(&text);
        content.append(&label("›"));
        choice.set_child(Some(&content));
        let target = tabs.clone();
        let (last, index) = (last_category.clone(), choices.len());
        choice.connect_clicked(move |_| {
            last.set(index);
            target.set_visible_child_name(name);
        });
        menu.append(&choice);
        choices.push(choice);
    }
    let choices = Rc::new(choices);
    let (focus_choices, selected) = (choices.clone(), last_category.clone());
    menu.connect_map(move |_| {
        focus_choices[selected.get()].grab_focus();
    });
    for (index, choice) in choices.iter().enumerate() {
        let keys = gtk::EventControllerKey::new();
        let buttons = choices.clone();
        keys.connect_key_pressed(move |_, key, _, _| {
            let next = match key {
                gtk::gdk::Key::Down => (index + 1) % buttons.len(),
                gtk::gdk::Key::Up => (index + buttons.len() - 1) % buttons.len(),
                _ => return glib::Propagation::Proceed,
            };
            buttons[next].grab_focus();
            glib::Propagation::Stop
        });
        choice.add_controller(keys);
    }
    tabs.add_named(&scroll(&menu), Some("categories"));
    let (heading, back_button, root, buttons) =
        (title.clone(), back.clone(), stack.clone(), choices);
    tabs.connect_visible_child_name_notify(move |pages| {
        let name = pages.visible_child_name().unwrap_or_default();
        if let Some(index) = ["host", "wifi", "bluetooth", "vpn", "board", "system"]
            .iter()
            .position(|category| *category == name.as_str())
        {
            last_category.set(index);
        }
        let caption = match name.as_str() {
            "host" => "category-host",
            "wifi" => "category-wifi",
            "bluetooth" => "category-bluetooth",
            "vpn" => "category-vpn",
            "board" => "category-board",
            "system" => "category-system",
            _ => "settings-heading",
        };
        heading.set_text(&tr(caption, &[]));
        let wizard = root
            .child_by_name("setup")
            .is_some_and(|p| p.widget_name() == "setup-return");
        back_button.set_label(&tr(
            if wizard {
                "back-setup"
            } else if name == "categories" {
                "back-dashboard"
            } else {
                "back-settings"
            },
            &[],
        ));
        if name == "categories" {
            buttons[last_category.get()].grab_focus();
        }
    });
    page.append(&tabs);
    tabs.add_titled(
        &scroll(&crate::host_view::build(stack, conf, status, f)),
        Some("host"),
        "Host & SSH",
    );
    let system = column();
    let reduce = gtk::CheckButton::with_label(&tr("settings-reduce-motion", &[]));
    reduce.set_active(conf.borrow().reduce_motion);
    system.append(&reduce);
    let sound = gtk::CheckButton::with_label(&tr("settings-sound", &[]));
    sound.set_active(conf.borrow().sound_effects);
    system.append(&sound);
    let (c, s) = (conf.clone(), stack.clone());
    let navigation = tabs.clone();
    reduce.connect_toggled(move |b| {
        c.borrow_mut().reduce_motion = b.is_active();
        s.set_transition_duration(if b.is_active() { 0 } else { 150 });
        navigation.set_transition_duration(if b.is_active() { 0 } else { 150 });
    });
    let c = conf.clone();
    sound.connect_toggled(move |b| c.borrow_mut().sound_effects = b.is_active());
    let save = button(&tr("settings-save", &[]), f);
    let (c, stat) = (conf.clone(), status.clone());
    save.connect_clicked(move |_| {
        status_result(
            &stat,
            config::config_dir().and_then(|p| c.borrow().save(&p.join("settings.json"))),
        )
    });
    system.append(&save);
    crate::system_settings::append(&system, stack, status, f);
    crate::account_view::append(&system, stack, status, f);
    tabs.add_titled(&scroll(&system), Some("system"), "System");
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
    tabs.add_titled(
        &scroll(&crate::board_settings::build(stack, conf, status, f)),
        Some("board"),
        "Kanban & Browser",
    );
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
    crate::wifi_hidden::append(&page, status, f);
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
    picker.set_widget_name("bluetooth-adapters");
    picker.set_selection_mode(gtk::SelectionMode::Single);
    let adapters: Rc<RefCell<Vec<bus::BluetoothAdapter>>> = Rc::new(RefCell::new(vec![]));
    page.append(&picker);
    let list = gtk::ListBox::new();
    list.set_widget_name("bluetooth-devices");
    page.append(&list);
    let devices: Rc<RefCell<Vec<bus::BluetoothDevice>>> = Rc::new(RefCell::new(vec![]));
    let all_devices: Rc<RefCell<Vec<bus::BluetoothDevice>>> = Rc::new(RefCell::new(vec![]));
    let rebuilding = Rc::new(Cell::new(false));
    let select: Rc<dyn Fn()> = {
        let (p, l, a, all, visible, owned, epoch) = (
            picker.downgrade(),
            list.downgrade(),
            adapters.clone(),
            all_devices.clone(),
            devices.clone(),
            discovery.clone(),
            generation.clone(),
        );
        let previous: RefCell<Option<String>> = RefCell::new(None);
        Rc::new(move || {
            let (Some(p), Some(l)) = (p.upgrade(), l.upgrade()) else {
                return;
            };
            let selected_adapter = p
                .selected_row()
                .and_then(|r| a.borrow().get(r.index() as usize).map(|a| a.path.clone()));
            if *previous.borrow() != selected_adapter {
                epoch.set(epoch.get().wrapping_add(1));
                owned.borrow_mut().take();
                *previous.borrow_mut() = selected_adapter.clone();
            }
            let rows: Vec<_> = all
                .borrow()
                .iter()
                .filter(|d| {
                    d.path
                        .rsplit_once('/')
                        .is_some_and(|(parent, _)| Some(parent) == selected_adapter.as_deref())
                })
                .cloned()
                .collect();
            if *visible.borrow() == rows {
                return;
            }
            let selected_device = l.selected_row().and_then(|r| {
                visible
                    .borrow()
                    .get(r.index() as usize)
                    .map(|d| d.path.clone())
            });
            while let Some(child) = l.first_child() {
                l.remove(&child);
            }
            for device in &rows {
                l.append(&label(&device.label));
            }
            if let Some(index) = rows
                .iter()
                .position(|d| Some(&d.path) == selected_device.as_ref())
            {
                l.select_row(l.row_at_index(index as i32).as_ref());
            }
            *visible.borrow_mut() = rows;
        })
    };
    let (update, suppressed) = (select.clone(), rebuilding.clone());
    picker.connect_row_selected(move |_, _| {
        if !suppressed.get() {
            update();
        }
    });
    let (a, all, p, stat, update, suppressed) = (
        adapters.clone(),
        all_devices,
        picker.clone(),
        status.clone(),
        select,
        rebuilding,
    );
    refresh.connect_clicked(move |b| {
        b.set_sensitive(false);
        let (a, all, p, stat, b, update, suppressed) = (
            a.clone(),
            all.clone(),
            p.clone(),
            stat.clone(),
            b.clone(),
            update.clone(),
            suppressed.clone(),
        );
        glib::MainContext::default().spawn_local(async move {
            match bus::bluetooth_snapshot().await {
                Ok((aa, dd)) => {
                    if *a.borrow() != aa {
                        suppressed.set(true);
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
                        *a.borrow_mut() = aa;
                        p.select_row(p.row_at_index(index as i32).as_ref());
                        suppressed.set(false);
                    }
                    *all.borrow_mut() = dd;
                    update();
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
        // Explicit search also renews a session lost when BlueZ/controller
        // restarted. Closing the previous client releases its old discovery.
        owned.borrow_mut().take();
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
    let serial = Rc::new(Cell::new(0u64));
    panel.connect_map(move |_| {
        serial.set(serial.get().wrapping_add(1));
        let ticket = serial.get();
        let serial = serial.clone();
        while let Some(child) = cols.first_child() {
            cols.remove(&child);
        }
        let settings = c.borrow().clone();
        let (cols, current) = (cols.clone(), c.clone());
        glib::MainContext::default().spawn_local(async move {
            let board = if settings.board_source.is_empty() {
                Board::default()
            } else {
                match crate::board_data::preview(settings.clone()).await {
                    Ok(board) => board,
                    Err(_) => {
                        if serial.get() != ticket
                            || crate::board_data::key(&current.borrow())
                                != crate::board_data::key(&settings)
                        {
                            return;
                        }
                        cols.append(&label(
                            "Keine Vorschau verfügbar. Kanban öffnen oder Datenquelle prüfen.",
                        ));
                        return;
                    }
                }
            };
            if serial.get() != ticket
                || crate::board_data::key(&current.borrow()) != crate::board_data::key(&settings)
            {
                return;
            }
            for (index, status) in board
                .columns(&settings.board_columns)
                .iter()
                .take(4)
                .enumerate()
            {
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
    });
    panel
}
pub fn remote(stack: &gtk::Stack, conf: &Shared, _status: &gtk::Label, f: &Feedback) -> gtk::Box {
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
    let b = button("RDP · integrierter Windows-Desktop", f);
    let (host_settings, s, feedback) = (conf.clone(), stack.clone(), f.clone());
    b.connect_clicked(move |_| {
        crate::rdp_view::open(&s, &host_settings, &feedback);
    });
    page.append(&b);
    let streaming = button("Desktop-Streaming · integriert", f);
    let (settings, route, feedback) = (conf.clone(), stack.clone(), f.clone());
    streaming.connect_clicked(move |_| crate::stream_view::open(&route, &settings, &feedback));
    page.append(&streaming);
    page
}
pub fn browser(stack: &gtk::Stack, conf: &Shared, status: &gtk::Label, f: &Feedback) {
    if stack.child_by_name("browser").is_some() {
        stack.set_visible_child_name("browser");
        return;
    }
    let page = column();
    let bar = row();
    bar.set_widget_name("browser-toolbar");
    let back = button("←", f);
    let forward = button("→", f);
    let reload = button("↻", f);
    let address = gtk::Entry::builder()
        .text(&conf.borrow().browser_url)
        .hexpand(true)
        .build();
    address.set_widget_name("browser-address");
    back.set_tooltip_text(Some("Zurück"));
    forward.set_tooltip_text(Some("Vorwärts"));
    reload.set_tooltip_text(Some("Neu laden · F5"));
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
    session.set_tls_errors_policy(webkit6::TLSErrorsPolicy::Fail);
    let Some(cookies) = session.cookie_manager() else {
        status.set_text("Das persönliche Browserprofil konnte nicht geöffnet werden.");
        return;
    };
    cookies.set_persistent_storage(
        &directory.join("cookies.sqlite").to_string_lossy(),
        webkit6::CookiePersistentStorage::Sqlite,
    );
    crate::downloads::install(&session, stack, f);
    let web = webkit6::WebView::builder()
        .network_session(&session)
        .hexpand(true)
        .vexpand(true)
        .build();
    crate::browser_prompts::install(&web, stack, status, f);
    web.set_widget_name("browser-webview");
    let fullscreen = button("Vollbild · F11", f);
    let (chrome, message) = (bar.clone(), status.clone());
    fullscreen.connect_clicked(move |_| {
        chrome.set_visible(false);
        message.set_visible(false);
    });
    bar.append(&fullscreen);
    let (chrome, message) = (bar.clone(), status.clone());
    web.connect_enter_fullscreen(move |_| {
        chrome.set_visible(false);
        message.set_visible(false);
        true // Rampi's existing top-level window is already fullscreen.
    });
    let (chrome, message) = (bar.clone(), status.clone());
    web.connect_leave_fullscreen(move |_| {
        chrome.set_visible(true);
        message.set_visible(true);
        true // Keep the Rampi session itself fullscreen.
    });
    let keys = gtk::EventControllerKey::new();
    keys.set_propagation_phase(gtk::PropagationPhase::Capture);
    let (chrome, message, location, content) =
        (bar.clone(), status.clone(), address.clone(), web.clone());
    keys.connect_key_pressed(move |_, key, _, modifiers| {
        use gtk::{gdk, glib::Propagation};
        if key == gdk::Key::F11 {
            let show = !chrome.is_visible();
            chrome.set_visible(show);
            message.set_visible(show);
            if !show {
                content.grab_focus();
            }
            return Propagation::Stop;
        }
        if key == gdk::Key::Escape && !chrome.is_visible() {
            chrome.set_visible(true);
            message.set_visible(true);
            let web = content.clone();
            glib::MainContext::default().spawn_local(async move {
                let _ = web
                    .evaluate_javascript_future(
                        "if (document.fullscreenElement) document.exitFullscreen(); null",
                        None,
                        None,
                    )
                    .await;
            });
            return Propagation::Stop;
        }
        if key == gdk::Key::F5 {
            content.reload();
            return Propagation::Stop;
        }
        if key == gdk::Key::l && modifiers.contains(gdk::ModifierType::CONTROL_MASK) {
            chrome.set_visible(true);
            message.set_visible(true);
            location.grab_focus();
            location.select_region(0, -1);
            return Propagation::Stop;
        }
        Propagation::Proceed
    });
    page.add_controller(keys);
    let (chrome, message) = (bar.clone(), status.clone());
    page.connect_unmap(move |_| {
        chrome.set_visible(true);
        message.set_visible(true);
    });
    let downloads = button("Downloads", f);
    let s = stack.clone();
    downloads.connect_clicked(move |_| s.set_visible_child_name("browser-downloads"));
    bar.append(&downloads);
    let stat = status.clone();
    web.connect_load_failed_with_tls_errors(move |_, _, _, _| {
        stat.set_text(
            "HTTPS-Zertifikat konnte nicht überprüft werden. Die Verbindung wurde abgewiesen.",
        );
        true
    });
    let stat = status.clone();
    web.connect_decide_policy(move |_, decision, kind| {
        if matches!(
            kind,
            webkit6::PolicyDecisionType::NavigationAction
                | webkit6::PolicyDecisionType::NewWindowAction
        ) && let Some(navigation) = decision.downcast_ref::<webkit6::NavigationPolicyDecision>()
            && let Some(uri) = navigation
                .navigation_action()
                .and_then(|a| a.request())
                .and_then(|r| r.uri())
            && rampi_core::config::validate_https(&uri).is_err()
        {
            decision.ignore();
            stat.set_text("Diese Navigation wurde abgewiesen. Bitte eine HTTPS-Adresse verwenden.");
            return true;
        }
        false
    });
    let entry = address.clone();
    web.connect_uri_notify(move |web| {
        if let Some(uri) = web.uri() {
            entry.set_text(&uri);
        }
    });
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
