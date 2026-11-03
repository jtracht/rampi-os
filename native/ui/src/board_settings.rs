use crate::widgets::*;
use gtk::{glib, prelude::*};
use rampi_core::config;
use rampi_core::i18n::text as tr;
use std::{cell::Cell, rc::Rc};
const KINDS: [&str; 7] = [
    "json", "github", "trello", "jira", "asana", "notion", "gitea",
];
pub fn build(
    stack: &gtk::Stack,
    navigation: &gtk::Stack,
    conf: &Shared,
    _status: &gtk::Label,
    f: &Feedback,
) -> gtk::Box {
    let page = column();
    let status = label("");
    status.set_widget_name("board-setup-status");
    let title = label(&tr("board-connect-heading", &[]));
    title.add_css_class("heading");
    page.append(&title);
    page.append(&label(&tr("board-connect-steps", &[])));
    page.append(&label(&tr("board-readonly-description", &[])));
    page.append(&label(&tr("board-source-step", &[])));
    let kind = inline_choices(
        &[
            &tr("board-json", &[]),
            "GitHub Projects",
            "Trello",
            "Jira Cloud",
            "Asana",
            "Notion Data Source",
            &tr("board-gitea", &[]),
        ],
        f,
    );
    kind.set_widget_name("board-kind");
    kind.select_row(
        kind.row_at_index(
            KINDS
                .iter()
                .position(|k| *k == conf.borrow().board_kind)
                .unwrap_or(0) as i32,
        )
        .as_ref(),
    );
    page.append(&kind);
    let source = gtk::Entry::builder()
        .placeholder_text(tr("board-source-input", &[]))
        .text(&conf.borrow().board_source)
        .build();
    accessible_name(&source, &tr("board-source-input", &[]));
    source.set_widget_name("board-source");
    page.append(&source);
    let hint = label("");
    hint.set_widget_name("board-source-hint");
    page.append(&hint);
    let credentials = column();
    credentials.append(&label(&tr("board-access-step", &[])));
    credentials.append(&label(&tr("board-token-description", &[])));

    let profile = gtk::Entry::builder()
        .placeholder_text(tr("board-profile-input", &[]))
        .text(&conf.borrow().board_token_key)
        .build();
    accessible_name(&profile, &tr("board-profile-label", &[]));
    profile.set_widget_name("board-token-profile");
    credentials.append(&label(&tr("board-profile-label", &[])));
    credentials.append(&profile);
    let columns = gtk::Entry::builder()
        .placeholder_text(tr("board-columns-input", &[]))
        .text(conf.borrow().board_columns.join(", "))
        .build();
    accessible_name(&columns, &tr("board-columns-label", &[]));
    page.append(&label(&tr("board-columns-label", &[])));
    page.append(&columns);
    let url = gtk::Entry::builder()
        .placeholder_text(tr("browser-home-input", &[]))
        .text(&conf.borrow().browser_url)
        .build();
    accessible_name(&url, &tr("browser-home-label", &[]));
    page.append(&label(&tr("browser-home-label", &[])));
    page.append(&url);
    page.append(&label(&tr("autosave-description", &[])));
    let (c, stat, k, p) = (conf.clone(), status.clone(), kind.clone(), profile.clone());
    let source_for_save = source.clone();
    let cols = columns.clone();
    let autosave = AutoSave::new(Rc::new(Cell::new(false)), move || {
        let result = (|| -> anyhow::Result<()> {
            let mut candidate = c.borrow().clone();
            candidate.board_kind = KINDS
                .get(choice_index(&k) as usize)
                .ok_or_else(|| anyhow::anyhow!(tr("board-select-provider", &[])))?
                .to_string();
            candidate.board_source = source_for_save.text().trim().to_string();
            candidate.board_token_key = p.text().trim().to_string();
            if candidate.board_kind != "json" {
                crate::secret_service::validate_profile(&candidate.board_token_key)?;
                // Construction validates the source; it performs no request and stores no credentials.
                rampi_core::connectors::Connector::new(
                    &candidate.board_kind,
                    &candidate.board_source,
                    "source-validation".into(),
                )?;
            }
            candidate.board_columns = cols
                .text()
                .split(',')
                .map(str::trim)
                .filter(|s| !s.is_empty())
                .map(String::from)
                .collect();
            candidate.save(&config::config_dir()?.join("settings.json"))?;
            *c.borrow_mut() = candidate;
            Ok(())
        })();
        autosave_result(&stat, result)
    });
    autosave.watch(&page, &[source.clone(), profile.clone(), columns.clone()]);
    autosave.routes(&[stack.clone(), navigation.clone()]);
    let save = autosave.clone();
    kind.connect_row_selected(move |_, _| save.changed());
    let (c, stat, home) = (conf.clone(), status.clone(), url.clone());
    let browser_save = AutoSave::new(Rc::new(Cell::new(false)), move || {
        let mut candidate = c.borrow().clone();
        candidate.browser_url = home.text().trim().into();
        persist_settings(&c, candidate, &stat)
    });
    browser_save.watch(&page, &[url]);
    browser_save.routes(&[stack.clone(), navigation.clone()]);

    let account = gtk::PasswordEntry::builder()
        .placeholder_text(tr("board-account-input", &[]))
        .show_peek_icon(true)
        .build();
    accessible_name(&account, &tr("board-account-input", &[]));
    credentials.append(&account);
    let token = gtk::PasswordEntry::builder()
        .placeholder_text(tr("board-token-input", &[]))
        .show_peek_icon(true)
        .build();
    accessible_name(&token, &tr("board-token-input", &[]));
    token.set_widget_name("board-token-input");
    credentials.append(&token);
    credentials.append(&label(&tr("autosave-secret", &[])));
    page.insert_child_after(&credentials, Some(&hint));
    let update = {
        let (hint, account, credentials, token) = (
            hint.clone(),
            account.clone(),
            credentials.clone(),
            token.clone(),
        );
        move |selected: u32| {
            let (message, placeholder): (String, &str) = match selected {
                1 => (
                    tr("board-hint-github", &[]),
                    "organization/OWNER/NUMBER | user/OWNER/NUMBER",
                ),
                2 => (tr("board-hint-trello", &[]), "Board-ID"),
                3 => (
                    tr("board-hint-jira", &[]),
                    "https://SITE.atlassian.net#PROJEKT",
                ),
                4 => (tr("board-hint-asana", &[]), "Projekt-ID"),
                5 => (tr("board-hint-notion", &[]), "Data-Source-ID"),
                6 => (
                    tr("board-hint-gitea", &[]),
                    "https://git.example.org/team/app/projects/7",
                ),
                _ => (tr("board-hint-json", &[]), "~/aufgaben.json"),
            };
            hint.set_text(&tr(
                "board-source-example",
                &[("description", &message), ("example", placeholder)],
            ));
            account.set_text("");
            token.set_text("");
            credentials.set_visible(selected != 0);
            account.set_visible(selected == 2 || selected == 3);
        }
    };
    update(choice_index(&kind));
    kind.connect_row_selected(move |k, _| update(choice_index(k)));

    let busy = Rc::new(Cell::new(false));
    let commit_secret: Rc<dyn Fn()> = {
        let busy = busy.clone();
        let (stat, kind, source, profile, account, token, credentials) = (
            status.clone(),
            kind.clone(),
            source.clone(),
            profile.clone(),
            account.clone(),
            token.clone(),
            credentials.clone(),
        );
        Rc::new(move || {
            if busy.get() || token.text().is_empty() {
                return;
            }
            let Some(kind) = KINDS.get(choice_index(&kind) as usize).copied() else {
                return;
            };
            if kind == "json" {
                return;
            }
            let (source_value, name, account_value, secret) = (
                source.text().trim().to_string(),
                profile.text().trim().to_string(),
                account.text().to_string(),
                token.text().to_string(),
            );
            busy.set(true);
            credentials.set_sensitive(false);
            let (busy, stat, account, token, credentials) = (
                busy.clone(),
                stat.clone(),
                account.clone(),
                token.clone(),
                credentials.clone(),
            );
            glib::MainContext::default().spawn_local(async move {
                match crate::secret_service::store(
                    &name,
                    kind,
                    &source_value,
                    &account_value,
                    &secret,
                )
                .await
                {
                    Ok(()) => {
                        if token.text().as_str() == secret
                            && account.text().as_str() == account_value
                        {
                            token.set_text("");
                            account.set_text("");
                        }
                        autosave_result(&stat, Ok(()));
                    }
                    Err(error) => {
                        autosave_result(&stat, Err(error));
                    }
                }
                busy.set(false);
                credentials.set_sensitive(true);
            });
        })
    };
    let focus = gtk::EventControllerFocus::new();
    let commit = commit_secret.clone();
    focus.connect_leave(move |_| commit());
    token.add_controller(focus);
    let commit = commit_secret.clone();
    page.connect_unmap(move |_| commit());
    let keys = gtk::EventControllerKey::new();
    let commit = commit_secret.clone();
    keys.connect_key_pressed(move |_, key, _, _| {
        if key == gtk::gdk::Key::Return {
            commit();
            glib::Propagation::Stop
        } else {
            glib::Propagation::Proceed
        }
    });
    token.add_controller(keys);
    page.append(&label(&tr("board-check-step", &[])));
    let check = button(&tr("board-check", &[]), f);
    let (c, stat) = (conf.clone(), status.clone());
    let (save, home_save) = (autosave.clone(), browser_save.clone());
    let (commit, writing, secret_input) = (commit_secret.clone(), busy.clone(), token.clone());
    check.connect_clicked(move |b| {
        if !save.flush() || !home_save.flush() {
            return;
        }
        commit();
        b.set_sensitive(false);
        let (b, stat, settings, writing, secret_input) = (
            b.clone(),
            stat.clone(),
            c.borrow().clone(),
            writing.clone(),
            secret_input.clone(),
        );
        glib::MainContext::default().spawn_local(async move {
            while writing.get() {
                glib::timeout_future(std::time::Duration::from_millis(20)).await;
            }
            if !secret_input.text().is_empty() {
                b.set_sensitive(true);
                return;
            }
            stat.set_text(&tr("board-checking", &[]));
            match crate::board_data::load(settings).await {
                Ok(data) => stat.set_text(&tr(
                    "board-checked",
                    &[
                        ("count", &data.board.cards.len().to_string()),
                        (
                            "state",
                            &tr(
                                if data.cached {
                                    "board-cached"
                                } else {
                                    "board-loaded"
                                },
                                &[],
                            ),
                        ),
                    ],
                )),
                Err(e) => stat.set_text(&tr("board-not-connected", &[("error", &e.to_string())])),
            }
            b.set_sensitive(true);
        });
    });
    page.append(&check);
    page.append(&status);
    let open = button(&tr("board-open", &[]), f);
    let (s, routes) = (stack.clone(), navigation.clone());
    open.connect_clicked(move |b| {
        if !autosave.flush() || !browser_save.flush() {
            return;
        }
        commit_secret();
        let (s, routes, b, writing, secret_input) = (
            s.clone(),
            routes.clone(),
            b.clone(),
            busy.clone(),
            token.clone(),
        );
        b.set_sensitive(false);
        glib::MainContext::default().spawn_local(async move {
            while writing.get() {
                glib::timeout_future(std::time::Duration::from_millis(20)).await;
            }
            b.set_sensitive(true);
            if secret_input.text().is_empty()
                && s.visible_child_name().as_deref() == Some("settings")
                && routes.visible_child_name().as_deref() == Some("board")
            {
                s.set_visible_child_name("kanban");
            }
        });
    });
    page.append(&open);
    page.append(&label(&tr("board-privacy", &[])));
    page
}
