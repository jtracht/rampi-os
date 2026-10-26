use crate::widgets::*;
use gtk::{glib, prelude::*};
use rampi_core::config;
const KINDS: [&str; 7] = [
    "json", "github", "trello", "jira", "asana", "notion", "gitea",
];
pub fn build(stack: &gtk::Stack, conf: &Shared, _status: &gtk::Label, f: &Feedback) -> gtk::Box {
    let page = column();
    let status = label("");
    status.set_widget_name("board-setup-status");
    let title = label("Dein Aufgabenboard verbinden");
    title.add_css_class("heading");
    page.append(&title);
    page.append(&label(
        "1 · Quelle wählen  →  2 · Zugang speichern  →  3 · Prüfen und Board öffnen",
    ));
    page.append(&label(
        "Rampi zeigt Aufgaben ausschließlich an. Änderungen bleiben beim Anbieter.",
    ));
    page.append(&label("1 · Wo liegen deine Aufgaben?"));
    let kind = gtk::DropDown::from_strings(&[
        "Lokale JSON-Datei",
        "GitHub Projects",
        "Trello",
        "Jira Cloud",
        "Asana",
        "Notion Data Source",
        "Gitea Projekt",
    ]);
    kind.set_widget_name("board-kind");
    kind.set_selected(
        KINDS
            .iter()
            .position(|k| *k == conf.borrow().board_kind)
            .unwrap_or(0) as u32,
    );
    page.append(&kind);
    let source = gtk::Entry::builder()
        .placeholder_text("Dateipfad oder Anbieter-Projektkennung")
        .text(&conf.borrow().board_source)
        .build();
    source.set_widget_name("board-source");
    page.append(&source);
    let hint = label("");
    hint.set_widget_name("board-source-hint");
    page.append(&hint);
    let credentials = column();
    credentials.append(&label("2 · Persönlichen Zugang hinterlegen"));
    credentials.append(&label(
        "Ein Token mit Lesezugriff genügt. Er bleibt in deinem Linux-Schlüsselbund.",
    ));

    let profile = gtk::Entry::builder()
        .placeholder_text("Persönliches Schlüsselbund-Profil")
        .text(&conf.borrow().board_token_key)
        .build();
    profile.set_widget_name("board-token-profile");
    credentials.append(&label("Name dieses Zugangsprofils"));
    credentials.append(&profile);
    let columns = gtk::Entry::builder()
        .placeholder_text("Spalten in Reihenfolge, durch Komma getrennt")
        .text(conf.borrow().board_columns.join(", "))
        .build();
    page.append(&label(
        "Spaltenreihenfolge · optional, leer übernimmt die Quelle",
    ));
    page.append(&columns);
    let url = gtk::Entry::builder()
        .placeholder_text("Browser-Startseite · HTTPS")
        .text(&conf.borrow().browser_url)
        .build();
    page.append(&label("Browser-Startseite"));
    page.append(&url);
    let save = button("Datenquelle und Startseite speichern", f);
    page.append(&save);
    let (c, stat, k, p) = (conf.clone(), status.clone(), kind.clone(), profile.clone());
    let source_for_save = source.clone();
    save.connect_clicked(move |_| {
        let result = (|| -> anyhow::Result<()> {
            let mut candidate = c.borrow().clone();
            candidate.board_kind = KINDS
                .get(k.selected() as usize)
                .ok_or_else(|| anyhow::anyhow!("Anbieter auswählen"))?
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
        .placeholder_text("Jira: E-Mail · Trello: API-Key · sonst leer")
        .show_peek_icon(true)
        .build();
    credentials.append(&account);
    let token = gtk::PasswordEntry::builder()
        .placeholder_text("API-/OAuth-Token mit möglichst eingeschränktem Lesezugriff")
        .show_peek_icon(true)
        .build();
    token.set_widget_name("board-token-input");
    credentials.append(&token);
    let store = button("Zugangsdaten im Schlüsselbund speichern", f);
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
            let (message, placeholder) = match selected {
                1 => (
                    "GitHub: Eigentümerart, Name und Projektnummer aus der Projektadresse.",
                    "organization/NAME/NUMMER oder user/NAME/NUMMER",
                ),
                2 => (
                    "Trello: Board-ID verwenden; API-Key und Token werden gemeinsam gespeichert.",
                    "Board-ID",
                ),
                3 => (
                    "Jira Cloud: Site und Projektschlüssel. Bei API-Token zusätzlich E-Mail angeben; OAuth benötigt die offizielle Cloud-ID-Adresse.",
                    "https://SITE.atlassian.net#PROJEKT",
                ),
                4 => (
                    "Asana: Numerische Projekt-ID aus der Projektadresse kopieren.",
                    "Projekt-ID",
                ),
                5 => (
                    "Notion: Data Source für deine Integration freigeben und deren ID verwenden.",
                    "Data-Source-ID",
                ),
                6 => (
                    "Gitea: Repository-Projektadresse oder vollständige HTTPS-API-Projektadresse einfügen. Alternativ: https://SERVER#repos/EIGENTÜMER/REPOSITORY/ID, https://SERVER#orgs/ORGANISATION/ID oder https://SERVER#user/ID. Persönliche Projekte verwenden den Eigentümer des Tokens. Spalten und Aufgaben bleiben schreibgeschützt.",
                    "https://git.example.org/team/app/projects/7",
                ),
                _ => (
                    "Lokale JSON-Datei: Pfad angeben. Dafür werden keine Zugangsdaten benötigt.",
                    "~/aufgaben.json",
                ),
            };
            hint.set_text(&format!("{message}\nBeispiel: {placeholder}"));
            account.set_text("");
            token.set_text("");
            credentials.set_visible(selected != 0);
            account.set_visible(selected == 2 || selected == 3);
        }
    };
    update(kind.selected());
    kind.connect_selected_notify(move |k| update(k.selected()));

    let stat = status.clone();
    store.connect_clicked(move |b| {
        let Some(kind) = KINDS.get(kind.selected() as usize) else {
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
    page.append(&label("3 · Verbindung prüfen und Aufgaben anzeigen"));
    let check = button("Gespeichertes Board prüfen", f);
    let (c, stat) = (conf.clone(), status.clone());
    check.connect_clicked(move |b| {
        b.set_sensitive(false);
        stat.set_text("Board wird geprüft …");
        let (b, stat, settings) = (b.clone(), stat.clone(), c.borrow().clone());
        glib::MainContext::default().spawn_local(async move {
            match crate::board_data::load(settings).await {
                Ok(data) => stat.set_text(&format!(
                    "{} Aufgaben · {}. Weiter mit ›Board öffnen‹.",
                    data.board.cards.len(),
                    if data.cached {
                        "Offline-Daten; Verbindung fehlgeschlagen"
                    } else {
                        "Quelle erfolgreich geladen"
                    }
                )),
                Err(e) => stat.set_text(&format!(
                    "Noch nicht verbunden: {e}. Prüfe Quelle und Zugang in Schritt 1 und 2."
                )),
            }
            b.set_sensitive(true);
        });
    });
    page.append(&check);
    page.append(&status);
    let open = button("Board öffnen →", f);
    let s = stack.clone();
    open.connect_clicked(move |_| s.set_visible_child_name("kanban"));
    page.append(&open);
    page.append(&label("Token stehen weder in settings.json noch in Prozessargumenten oder Cache-Dateinamen. Bei gesperrtem Schlüsselbund zuerst die normale PAM-Sitzung entsperren. Rampi öffnet keinen externen Dialog. Ein Quellenwechsel zeigt ausschließlich Daten des gewählten Profils; Offline-Daten bleiben privat im persönlichen Cache."));
    page
}
