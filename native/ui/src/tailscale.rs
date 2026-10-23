//! Asynchronous, bounded read-only invocation of the installed official CLI.
use anyhow::{Result, ensure};
use gtk::{glib, prelude::*};

pub async fn snapshot() -> Result<rampi_core::tailscale::Status> {
    ensure!(
        glib::find_program_in_path("tailscale").is_some(),
        "Tailscale ist nicht installiert. Die offizielle Software muss zuerst eingerichtet werden."
    );
    let (ok, bytes) = crate::process::output(
        "tailscale",
        &["status".into(), "--json".into(), "--peers=false".into()],
        5,
        262_144,
    )
    .await
    .map_err(|e| {
        anyhow::anyhow!("Tailscale antwortet nicht oder liefert eine zu große Antwort: {e}")
    })?;
    ensure!(
        ok,
        "Tailscale-Dienst nicht erreichbar oder Zugriff verweigert. Dienst und Berechtigungen prüfen."
    );
    rampi_core::tailscale::Status::parse(&bytes)
}
pub async fn status() -> Result<String> {
    if glib::find_program_in_path("tailscale").is_none() {
        return Ok("Tailscale ist nicht installiert. Die offizielle Software muss zuerst eingerichtet werden.".into());
    }
    Ok(snapshot().await?.description())
}
pub async fn change(connect: bool) -> Result<rampi_core::tailscale::Status> {
    let args = if connect {
        vec!["up".into(), "--timeout=3s".into(), "--json".into()]
    } else {
        vec!["down".into()]
    };
    let (ok, _) = crate::process::output("tailscale", &args, 8, 262_144).await?;
    let state = snapshot().await?;
    ensure!(
        ok || (connect && state.backend == "NeedsLogin" && state.login_url().is_some()),
        "Tailscale konnte die Änderung nicht ausführen. Ein Administrator muss dein Linux-Konto als Tailscale-Operator freigeben; bestehende Einstellungen werden nicht zurückgesetzt."
    );
    Ok(state)
}

pub fn view(feedback: &crate::widgets::Feedback) -> gtk::Box {
    let page = crate::widgets::column();
    let output = crate::widgets::label("Tailscale-Status wird beim Öffnen geladen.");
    output.set_widget_name("tailscale-status");
    page.append(&output);
    let refresh = crate::widgets::button("Tailscale-Status aktualisieren", feedback);
    let weak_output = output.downgrade();
    refresh.connect_clicked(move |button| {
        if !button.is_sensitive() {
            return;
        }
        button.set_sensitive(false);
        let (button, output) = (button.clone(), weak_output.clone());
        glib::MainContext::default().spawn_local(async move {
            let result = status().await;
            if let Some(output) = output.upgrade() {
                output.set_text(&result.unwrap_or_else(|e| e.to_string()));
            }
            button.set_sensitive(true);
        });
    });
    page.append(&refresh);
    let weak = refresh.downgrade();
    page.connect_map(move |_| {
        if let Some(refresh) = weak.upgrade() {
            refresh.emit_clicked();
        }
    });
    let (weak_page, weak_refresh) = (page.downgrade(), refresh.downgrade());
    glib::timeout_add_seconds_local(5, move || {
        let (Some(page), Some(refresh)) = (weak_page.upgrade(), weak_refresh.upgrade()) else {
            return glib::ControlFlow::Break;
        };
        if page.is_mapped() && refresh.is_sensitive() {
            refresh.emit_clicked();
        }
        glib::ControlFlow::Continue
    });
    page
}

pub fn actions(
    stack: &gtk::Stack,
    status: &gtk::Label,
    feedback: &crate::widgets::Feedback,
) -> gtk::Box {
    use crate::widgets::*;
    let page = column();
    page.append(&label("1 · Dienst prüfen  →  2 · Verbinden  →  3 · Bei Bedarf anmelden\nEin Administrator muss dein Linux-Konto einmalig als Tailscale-Operator freigeben. VPN und Anmeldung gelten systemweit."));
    let busy = std::rc::Rc::new(std::cell::Cell::new(false));
    for (title, connect) in [("Tailscale verbinden", true), ("Tailscale trennen", false)] {
        let action = button(title, feedback);
        let (s, stat, f, busy) = (
            stack.clone(),
            status.clone(),
            feedback.clone(),
            busy.clone(),
        );
        action.connect_clicked(move |_| {
            let (s, stat, busy, f) = (s.clone(), stat.clone(), busy.clone(), f.clone());
            let route = s.clone();
            let execute = move || {
                if busy.replace(true) {
                    return;
                }
                stat.set_text("Tailscale wird aktualisiert …");
                let (stat, busy) = (stat.clone(), busy.clone());
                glib::MainContext::default().spawn_local(async move {
                    match change(connect).await {
                        Ok(state) => stat.set_text(&format!(
                            "{}{}",
                            state.description(),
                            if state.login_url().is_some() {
                                "\nWeiter mit ›Tailscale-Anmeldung öffnen‹."
                            } else {
                                ""
                            }
                        )),
                        Err(e) => stat.set_text(&e.to_string()),
                    }
                    busy.set(false);
                });
            };
            crate::views::confirm(
                &route,
                title,
                "Diese Aktion ändert die VPN-Verbindung für alle Benutzer dieses Geräts.",
                &f,
                execute,
            );
        });
        page.append(&action);
    }
    let login = button("Tailscale-Anmeldung öffnen", feedback);
    let (s, stat, f) = (stack.clone(), status.clone(), feedback.clone());
    login.connect_clicked(move |b| {
        if !b.is_sensitive() { return; }
        b.set_sensitive(false);
        let (b, s, stat, f) = (b.clone(), s.clone(), stat.clone(), f.clone());
        glib::MainContext::default().spawn_local(async move {
            match snapshot().await {
                Ok(state) => match state.login_url() {
                    Some(url) => login_page(&s, url, &stat, &f),
                    None => stat.set_text("Kein offizieller Anmeldelink verfügbar. Zuerst ›Tailscale verbinden‹ wählen und Dienststatus prüfen."),
                },
                Err(e) => stat.set_text(&e.to_string()),
            }
            b.set_sensitive(true);
        });
    });
    page.append(&login);
    page
}

fn login_page(
    stack: &gtk::Stack,
    url: &str,
    status: &gtk::Label,
    feedback: &crate::widgets::Feedback,
) {
    use crate::widgets::*;
    use webkit6::prelude::*;
    if let Some(old) = stack.child_by_name("tailscale-login") {
        stack.remove(&old);
    }
    let page = column();
    page.append(&label("Tailscale anmelden · danach zurück zum VPN-Status\nAnmeldung erfolgt beim Anbieter. Rampi speichert keine Kennwörter oder Anmelde-URLs."));
    let session = webkit6::NetworkSession::new_ephemeral();
    session.set_tls_errors_policy(webkit6::TLSErrorsPolicy::Fail);
    session.connect_download_started(|_, download| download.cancel());
    let web = webkit6::WebView::builder()
        .network_session(&session)
        .hexpand(true)
        .vexpand(true)
        .build();
    web.set_widget_name("tailscale-login-webview");
    crate::browser_prompts::install(&web, stack, status, feedback);
    let back = button("← Zurück zu VPN", feedback);
    back.set_widget_name("rampi-back");
    let (s, w) = (stack.clone(), web.downgrade());
    back.connect_clicked(move |_| {
        if let Some(w) = w.upgrade() {
            w.stop_loading();
        }
        s.set_visible_child_name("settings");
        if let Some(page) = s.child_by_name("tailscale-login") {
            s.remove(&page);
        }
    });
    page.append(&back);
    web.connect_decide_policy(|_, decision, kind| {
        if matches!(
            kind,
            webkit6::PolicyDecisionType::NavigationAction
                | webkit6::PolicyDecisionType::NewWindowAction
        ) && let Some(nav) = decision.downcast_ref::<webkit6::NavigationPolicyDecision>()
            && let Some(uri) = nav
                .navigation_action()
                .and_then(|a| a.request())
                .and_then(|r| r.uri())
            && rampi_core::config::validate_https(&uri).is_err()
        {
            decision.ignore();
            return true;
        }
        false
    });
    let weak = web.downgrade();
    web.connect_create(move |_, action| {
        if let (Some(web), Some(uri)) = (weak.upgrade(), action.request().and_then(|r| r.uri()))
            && rampi_core::config::validate_https(&uri).is_ok()
        {
            web.load_uri(&uri);
        }
        None
    });
    let stat = status.clone();
    web.connect_load_failed_with_tls_errors(move |_, _, _, _| {
        stat.set_text("Das Anmeldezertifikat ist ungültig. Die Verbindung wurde abgewiesen.");
        true
    });
    web.load_uri(url);
    page.append(&web);
    stack.add_named(&page, Some("tailscale-login"));
    stack.set_visible_child_name("tailscale-login");
}
