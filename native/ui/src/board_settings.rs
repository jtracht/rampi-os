use crate::widgets::*;
use gtk::{glib, prelude::*};
use rampi_core::config;
use rampi_core::i18n::text as tr;
const KINDS: [&str; 7] = [
    "json", "github", "trello", "jira", "asana", "notion", "gitea",
];
pub fn build(stack: &gtk::Stack, conf: &Shared, _status: &gtk::Label, f: &Feedback) -> gtk::Box {
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
    profile.set_widget_name("board-token-profile");
    credentials.append(&label(&tr("board-profile-label", &[])));
    credentials.append(&profile);
    let columns = gtk::Entry::builder()
        .placeholder_text(tr("board-columns-input", &[]))
        .text(conf.borrow().board_columns.join(", "))
        .build();
    page.append(&label(&tr("board-columns-label", &[])));
    page.append(&columns);
    let url = gtk::Entry::builder()
        .placeholder_text(tr("browser-home-input", &[]))
        .text(&conf.borrow().browser_url)
        .build();
    page.append(&label(&tr("browser-home-label", &[])));
    page.append(&url);
    let save = button(&tr("board-save", &[]), f);
    page.append(&save);
    let (c, stat, k, p) = (conf.clone(), status.clone(), kind.clone(), profile.clone());
    let source_for_save = source.clone();
    save.connect_clicked(move |_| {
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
            candidate.board_columns = columns
                .text()
                .split(',')
                .map(str::trim)
                .filter(|s| !s.is_empty())
                .map(String::from)
                .collect();
            candidate.browser_url = url.text().to_string();
            candidate.save(&config::config_dir()?.join("settings.json"))?;
            *c.borrow_mut() = candidate;
            Ok(())
        })();
        status_result(&stat, result);
    });

    let account = gtk::PasswordEntry::builder()
        .placeholder_text(tr("board-account-input", &[]))
        .show_peek_icon(true)
        .build();
    credentials.append(&account);
    let token = gtk::PasswordEntry::builder()
        .placeholder_text(tr("board-token-input", &[]))
        .show_peek_icon(true)
        .build();
    token.set_widget_name("board-token-input");
    credentials.append(&token);
    let store = button(&tr("board-store", &[]), f);
    credentials.append(&store);
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

    let stat = status.clone();
    store.connect_clicked(move |b| {
        let Some(kind) = KINDS.get(choice_index(&kind) as usize) else {
            return;
        };
        let source = source.text().trim().to_string();
        let (name, account_value, secret) = (
            profile.text().trim().to_string(),
            account.text().to_string(),
            token.text().to_string(),
        );
        token.set_text("");
        account.set_text("");
        b.set_sensitive(false);
        let (b, stat) = (b.clone(), stat.clone());
        glib::MainContext::default().spawn_local(async move {
            status_result(
                &stat,
                crate::secret_service::store(&name, kind, &source, &account_value, &secret).await,
            );
            b.set_sensitive(true);
        });
    });
    page.append(&label(&tr("board-check-step", &[])));
    let check = button(&tr("board-check", &[]), f);
    let (c, stat) = (conf.clone(), status.clone());
    check.connect_clicked(move |b| {
        b.set_sensitive(false);
        stat.set_text(&tr("board-checking", &[]));
        let (b, stat, settings) = (b.clone(), stat.clone(), c.borrow().clone());
        glib::MainContext::default().spawn_local(async move {
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
    let s = stack.clone();
    open.connect_clicked(move |_| s.set_visible_child_name("kanban"));
    page.append(&open);
    page.append(&label(&tr("board-privacy", &[])));
    page
}
