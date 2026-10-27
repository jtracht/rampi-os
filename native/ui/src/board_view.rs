//! Read-only local Kanban view; GTK owns layout, scrolling and input.
use crate::widgets::*;
use gtk::{glib, prelude::*};
use rampi_core::board::Board;
use rampi_core::i18n::text as tr;
use std::{
    cell::{Cell, RefCell},
    rc::Rc,
};

pub fn build(stack: &gtk::Stack, conf: &Shared, feedback: &Feedback) -> gtk::Box {
    let page = column();
    let toolbar = row();
    let back = button(&tr("back-dashboard", &[]), feedback);
    let route = stack.clone();
    back.connect_clicked(move |_| route.set_visible_child_name("dashboard"));
    let reload = button(&tr("board-reload", &[]), feedback);
    let title = label(&tr("board-title", &[]));
    title.add_css_class("heading");
    toolbar.append(&back);
    toolbar.append(&title);
    toolbar.append(&reload);
    page.append(&toolbar);

    let filters = row();
    let entries: Vec<gtk::Entry> = [
        ("board-query", "board-search", "board-search-hint"),
        ("board-project", "board-project", "board-project-hint"),
        ("board-priority", "board-priority", "board-priority-hint"),
        ("board-status", "board-status-label", "board-status-hint"),
    ]
    .into_iter()
    .map(|(name, title, hint)| {
        let group = column();
        group.set_hexpand(true);
        group.append(&label(&tr(title, &[])));
        let entry = gtk::Entry::builder()
            .placeholder_text(tr(hint, &[]))
            .hexpand(true)
            .width_chars(12)
            .build();
        entry.set_widget_name(name);
        group.append(&entry);
        filters.append(&group);
        entry
    })
    .collect();
    page.append(&filters);
    page.append(&label(&tr("board-filter-description", &[])));
    let message = label("");
    message.set_widget_name("board-result");
    page.append(&message);
    let columns = row();
    columns.set_homogeneous(true);
    columns.set_vexpand(true);
    page.append(&scroll(&columns));
    let board = Rc::new(RefCell::new(Board::default()));
    let cached = Rc::new(Cell::new(false));
    let identity = Rc::new(RefCell::new(String::new()));
    let (b, c, cols, e, summary) = (
        board.clone(),
        conf.clone(),
        columns.clone(),
        entries.iter().map(|e| e.downgrade()).collect::<Vec<_>>(),
        message.clone(),
    );
    let feedback = feedback.clone();
    let render_cached = cached.clone();
    let render: Rc<dyn Fn()> = Rc::new(move || {
        while let Some(child) = cols.first_child() {
            cols.remove(&child);
        }
        let board = b.borrow();
        let values: Vec<String> = e
            .iter()
            .filter_map(|e| e.upgrade())
            .map(|e| e.text().to_string())
            .collect();
        if values.len() != 4 {
            return;
        }
        let cards = board.filtered(&values[0], &values[1], &values[2], &values[3]);
        summary.set_text(&tr(
            "board-summary",
            &[
                ("count", &cards.len().to_string()),
                ("total", &board.cards.len().to_string()),
                ("title", &board.title),
                (
                    "cache",
                    &if render_cached.get() {
                        tr("board-cache-suffix", &[])
                    } else {
                        String::new()
                    },
                ),
            ],
        ));
        for (index, name) in board
            .columns(&c.borrow().board_columns)
            .into_iter()
            .enumerate()
        {
            let lane = column();
            lane.set_hexpand(true);
            lane.set_size_request(210, -1);
            lane.add_css_class("board-lane");
            lane.add_css_class(&format!("lane-{}", index % 4));
            let count = cards.iter().filter(|card| card.status == name).count();
            let heading = label(&format!("{name} · {count}"));
            heading.add_css_class("heading");
            lane.append(&heading);
            // Load a bounded batch of widgets, then use an inline continuation.
            let matching: Vec<_> = cards
                .iter()
                .filter(|card| card.status == name)
                .map(|card| (*card).clone())
                .collect();
            let shown = Rc::new(Cell::new(0));
            let body = column();
            lane.append(&body);
            append_batch(&body, &matching, &shown);
            if matching.len() > shown.get() {
                let more = button(&tr("board-more", &[]), &feedback);
                let (body, shown) = (body.clone(), shown.clone());
                more.connect_clicked(move |button| {
                    append_batch(&body, &matching, &shown);
                    button.set_visible(shown.get() < matching.len());
                });
                lane.append(&more);
            }
            cols.append(&lane);
        }
    });
    for entry in &entries {
        let render = render.clone();
        entry.connect_changed(move |_| render());
    }
    let serial = Rc::new(Cell::new(0u64));
    let (c, msg) = (conf.clone(), message.clone());
    let load_filters = entries.iter().map(|e| e.downgrade()).collect::<Vec<_>>();
    let load: Rc<dyn Fn()> = Rc::new(move || {
        serial.set(serial.get().wrapping_add(1));
        let ticket = serial.get();
        let settings = c.borrow().clone();
        let key = crate::board_data::key(&settings);
        if *identity.borrow() != key {
            *identity.borrow_mut() = key.clone();
            *board.borrow_mut() = Board::default();
            cached.set(false);
            for filter in &load_filters {
                if let Some(filter) = filter.upgrade() {
                    filter.set_text("");
                }
            }
            render();
        }
        let current = c.clone();
        let cache_state = cached.clone();
        let (b, serial, render, msg) = (board.clone(), serial.clone(), render.clone(), msg.clone());
        msg.set_text(&tr("board-loading", &[]));
        glib::MainContext::default().spawn_local(async move {
            let loaded = crate::board_data::load(settings).await;
            if serial.get() != ticket || crate::board_data::key(&current.borrow()) != key {
                return;
            }
            match loaded {
                Ok(loaded) => {
                    cache_state.set(loaded.cached);
                    *b.borrow_mut() = loaded.board;
                    render();
                }
                Err(error) => {
                    msg.set_text(&tr("board-load-error", &[("error", &error.to_string())]))
                }
            }
        });
    });
    let l = load.clone();
    reload.connect_clicked(move |_| l());
    page.connect_map(move |_| load());
    page
}

fn append_batch(body: &gtk::Box, cards: &[rampi_core::board::Card], shown: &Cell<usize>) {
    let end = (shown.get() + 100).min(cards.len());
    for card in &cards[shown.get()..end] {
        let text = label(&format!(
            "{}\n{} · {}\n{}",
            card.title, card.project, card.priority, card.description
        ));
        text.set_wrap(true);
        text.set_max_width_chars(36);
        text.set_selectable(true);
        text.add_css_class("board-card");
        body.append(&text);
    }
    shown.set(end);
}
