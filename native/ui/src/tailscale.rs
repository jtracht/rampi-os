//! Asynchronous, bounded integration with the installed official Tailscale CLI.
use anyhow::{Result, ensure};
use gtk::{glib, prelude::*};
use rampi_core::i18n::text as tr;

pub async fn snapshot() -> Result<rampi_core::tailscale::Status> {
    ensure!(
        glib::find_program_in_path("tailscale").is_some(),
        "{}",
        tr("tailscale-missing", &[])
    );
    let (ok, bytes) = crate::process::output(
        "tailscale",
        &["status".into(), "--json".into(), "--peers=false".into()],
        5,
        262_144,
    )
    .await
    .map_err(|e| anyhow::anyhow!(tr("tailscale-response-error", &[("error", &e.to_string())])))?;
    ensure!(ok, "{}", tr("tailscale-unavailable", &[]));
    rampi_core::tailscale::Status::parse(&bytes)
}
pub async fn status() -> Result<String> {
    if glib::find_program_in_path("tailscale").is_none() {
        return Ok(tr("tailscale-missing", &[]));
    }
    Ok(snapshot().await?.description())
}
pub async fn change(connect: bool) -> Result<rampi_core::tailscale::Status> {
    let args = if connect {
        let state = snapshot().await?;
        if matches!(state.backend.as_str(), "Stopped" | "Running") {
            // The official CLI's flag-free up preserves every existing
            // non-default preference. Adding even JSON/timeout flags asks it
            // to reconcile flags and rejects custom DNS/hostname/operator.
            // Our existing subprocess deadline still bounds this operation.
            vec!["up".into()]
        } else {
            vec!["up".into(), "--timeout=3s".into(), "--json".into()]
        }
    } else {
        vec!["down".into()]
    };
    let (ok, _) = crate::process::output("tailscale", &args, 8, 262_144).await?;
    let state = snapshot().await?;
    ensure!(
        ok || (connect && state.backend == "NeedsLogin" && state.login_url().is_some()),
        "{}",
        tr("tailscale-action-error", &[])
    );
    Ok(state)
}

pub fn view(feedback: &crate::widgets::Feedback) -> gtk::Box {
    let page = crate::widgets::column();
    let output = crate::widgets::label(&tr("tailscale-loading", &[]));
    output.set_widget_name("tailscale-status");
    page.append(&output);
    let refresh = crate::widgets::button(&tr("tailscale-refresh", &[]), feedback);
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
    page.append(&label(&tr("tailscale-steps", &[])));
    let install = button(&tr("tailscale-install", &[]), feedback);
    install.set_widget_name("tailscale-install");
    let available = || {
        glib::find_program_in_path("tailscale").is_none()
            && std::path::Path::new("/usr/local/libexec/rampi-tailscale-install").is_file()
            && glib::find_program_in_path("sudo").is_some()
    };
    install.set_sensitive(available());
    install.connect_map(move |button| button.set_sensitive(available()));
    let (route, output, f) = (stack.clone(), status.clone(), feedback.clone());
    install.connect_clicked(move |_| {
        let (destination, output, feedback) = (route.clone(), output.clone(), f.clone());
        crate::views::confirm(
            &route,
            &tr("tailscale-install", &[]),
            &tr("tailscale-install-confirm", &[]),
            &f,
            move || {
                crate::views::terminal_review(
                    &destination,
                    "tailscale-install",
                    vec![
                        "/usr/bin/sudo".into(),
                        "--".into(),
                        "/usr/local/libexec/rampi-tailscale-install".into(),
                        "--install".into(),
                    ],
                    &output,
                    &feedback,
                );
            },
        );
    });
    page.append(&install);
    let operator = button(&tr("tailscale-operator", &[]), feedback);
    operator.set_widget_name("tailscale-operator");
    operator.set_sensitive(
        glib::find_program_in_path("tailscale").is_some()
            && glib::find_program_in_path("sudo").is_some(),
    );
    let (route, stat, f) = (stack.clone(), status.clone(), feedback.clone());
    operator.connect_map(|button| {
        button.set_sensitive(
            glib::find_program_in_path("tailscale").is_some()
                && glib::find_program_in_path("sudo").is_some(),
        )
    });
    operator.connect_clicked(move |_| {
        let account = glib::user_name();
        let args = match rampi_core::accounts::tailscale_operator(&account.to_string_lossy()) {
            Ok(args) => args,
            Err(error) => {
                stat.set_text(&error.to_string());
                return;
            }
        };
        let (destination, output, args) = (route.clone(), stat.clone(), args.clone());
        crate::views::confirm(
            &route,
            &tr("tailscale-operator-heading", &[]),
            &tr(
                "tailscale-operator-confirm",
                &[("account", &account.to_string_lossy())],
            ),
            &f,
            move || {
                crate::views::terminal(&destination, "tailscale-operator", args.clone(), &output)
            },
        );
    });
    page.append(&operator);
    let busy = std::rc::Rc::new(std::cell::Cell::new(false));
    for (message, connect) in [("tailscale-connect", true), ("tailscale-disconnect", false)] {
        let title = tr(message, &[]);
        let action = button(&title, feedback);
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
                stat.set_text(&tr("tailscale-updating", &[]));
                let (stat, busy) = (stat.clone(), busy.clone());
                glib::MainContext::default().spawn_local(async move {
                    match change(connect).await {
                        Ok(state) => stat.set_text(&format!(
                            "{}{}",
                            state.description(),
                            if state.login_url().is_some() {
                                format!("\n{}", tr("tailscale-login-next", &[]))
                            } else {
                                String::new()
                            }
                        )),
                        Err(e) => stat.set_text(&e.to_string()),
                    }
                    busy.set(false);
                });
            };
            crate::views::confirm(
                &route,
                &title,
                &tr("tailscale-global-confirm", &[]),
                &f,
                execute,
            );
        });
        page.append(&action);
    }
    let login = button(&tr("tailscale-open-login", &[]), feedback);
    let (s, stat, f) = (stack.clone(), status.clone(), feedback.clone());
    login.connect_clicked(move |b| {
        if !b.is_sensitive() {
            return;
        }
        b.set_sensitive(false);
        let (b, s, stat, f) = (b.clone(), s.clone(), stat.clone(), f.clone());
        glib::MainContext::default().spawn_local(async move {
            let state = snapshot().await;
            if !b.is_mapped() {
                b.set_sensitive(true);
                return;
            }
            match state {
                Ok(state) => match state.login_url() {
                    Some(url) => login_page(&s, url, &stat, &f),
                    None => stat.set_text(&tr("tailscale-no-login", &[])),
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
    page.append(&label(&tr("tailscale-login-description", &[])));
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
    let back = button(&tr("tailscale-back", &[]), feedback);
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
        stat.set_text(&tr("tailscale-certificate-invalid", &[]));
        true
    });
    web.load_uri(url);
    page.append(&web);
    stack.add_named(&page, Some("tailscale-login"));
    stack.set_visible_child_name("tailscale-login");
}
