//! Route WebKit requests to application pages instead of GTK dialog windows.
use crate::widgets::*;
use gtk::prelude::*;
use rampi_core::i18n::text as tr;
use std::{cell::Cell, rc::Rc};
use webkit6::prelude::*;

fn page(stack: &gtk::Stack, title: &str) -> gtk::Box {
    if let Some(old) = stack.child_by_name("browser-request") {
        stack.remove(&old);
    }
    let p = column();
    let heading = label(title);
    heading.add_css_class("heading");
    p.append(&heading);
    stack.add_named(&p, Some("browser-request"));
    stack.set_visible_child_name("browser-request");
    p
}
pub fn install(web: &webkit6::WebView, stack: &gtk::Stack, status: &gtk::Label, f: &Feedback) {
    let (s, feed) = (stack.clone(), f.clone());
    web.connect_script_dialog(move |_, dialog| {
        let p = page(&s, &tr("browser-message", &[]));
        p.append(&label(dialog.message().as_deref().unwrap_or("")));
        let input = gtk::Entry::new();
        if dialog.dialog_type() == webkit6::ScriptDialogType::Prompt {
            input.set_text(dialog.prompt_get_default_text().as_deref().unwrap_or(""));
        }
        input.set_visible(dialog.dialog_type() == webkit6::ScriptDialogType::Prompt);
        input.set_widget_name("browser-prompt-input");
        p.append(&input);
        let no = button(&tr("action-cancel", &[]), &feed);
        no.set_widget_name("rampi-back");
        let yes = button(&tr("action-accept", &[]), &feed);
        p.append(&no);
        p.append(&yes);
        let done = Rc::new(Cell::new(false));
        let (d, back_stack, done1) = (dialog.clone(), s.clone(), done.clone());
        no.connect_clicked(move |_| {
            if !done1.replace(true) {
                d.close();
            }
            back_stack.set_visible_child_name("browser");
        });
        let (d, s) = (dialog.clone(), s.clone());
        yes.connect_clicked(move |_| {
            if !done.replace(true) {
                match d.dialog_type() {
                    webkit6::ScriptDialogType::Confirm
                    | webkit6::ScriptDialogType::BeforeUnloadConfirm => {
                        d.confirm_set_confirmed(true)
                    }
                    webkit6::ScriptDialogType::Prompt => d.prompt_set_text(&input.text()),
                    _ => (),
                }
                d.close();
            }
            s.set_visible_child_name("browser");
        });
        no.grab_focus();
        true
    });
    let (s, feed) = (stack.clone(), f.clone());
    web.connect_authenticate(move |_, request| {
        let p = page(&s, &tr("browser-auth", &[]));
        p.append(&label(&format!(
            "{}:{} · {}",
            request
                .host()
                .as_deref()
                .unwrap_or(&tr("browser-host-unknown", &[])),
            request.port(),
            request.realm().as_deref().unwrap_or("")
        )));
        let user = gtk::Entry::builder()
            .placeholder_text(tr("browser-username", &[]))
            .build();
        let password = gtk::PasswordEntry::builder()
            .placeholder_text(tr("browser-credential-placeholder", &[]))
            .build();
        p.append(&user);
        p.append(&password);
        let no = button(&tr("action-cancel", &[]), &feed);
        no.set_widget_name("rampi-back");
        let yes = button(&tr("browser-sign-in", &[]), &feed);
        p.append(&no);
        p.append(&yes);
        let (r, back_stack) = (request.clone(), s.clone());
        no.connect_clicked(move |_| {
            r.cancel();
            back_stack.set_visible_child_name("browser");
        });
        let (r, s) = (request.clone(), s.clone());
        yes.connect_clicked(move |_| {
            let credential = webkit6::Credential::new(
                &user.text(),
                &password.text(),
                webkit6::CredentialPersistence::None,
            );
            r.authenticate(Some(&credential));
            password.set_text("");
            s.set_visible_child_name("browser");
        });
        no.grab_focus();
        true
    });
    crate::uploads::install(web, stack, f);
    install_permissions(web, stack, status, f);
}

/// WebKit owns capture and sandboxing. Consent belongs to this request only;
/// navigation, leaving the page or expiry deny the pending request.
fn install_permissions(
    web: &webkit6::WebView,
    stack: &gtk::Stack,
    status: &gtk::Label,
    feedback: &Feedback,
) {
    use std::cell::RefCell;
    type Pending = Rc<RefCell<Option<(i64, webkit6::PermissionRequest, String)>>>;
    let pending: Pending = Rc::new(RefCell::new(None));
    let (state, route, view, output) = (
        pending.clone(),
        stack.downgrade(),
        web.downgrade(),
        status.downgrade(),
    );
    let finish: Rc<dyn Fn(i64, bool)> = Rc::new(move |id, allow| {
        if !state
            .borrow()
            .as_ref()
            .is_some_and(|(current, _, _)| *current == id)
        {
            return;
        }
        let (_, request, uri) = state.borrow_mut().take().unwrap();
        let route = route.upgrade();
        let allowed = allow
            && route
                .as_ref()
                .is_some_and(|s| s.visible_child_name().as_deref() == Some("browser-permission"))
            && view
                .upgrade()
                .is_some_and(|v| v.uri().as_deref() == Some(uri.as_str()));
        if let Some(output) = output.upgrade() {
            output.set_text(&tr(
                if allowed {
                    "browser-permission-allowed"
                } else {
                    "browser-permission-denied"
                },
                &[],
            ));
        }
        if let Some(route) = route {
            if route.visible_child_name().as_deref() == Some("browser-permission") {
                route.set_visible_child_name("browser");
            }
            if let Some(page) = route.child_by_name("browser-permission") {
                route.remove(&page);
            }
        }
        if allowed {
            request.allow();
        } else {
            request.deny();
        }
    });
    let (state, end) = (pending.clone(), finish.clone());
    stack.connect_visible_child_name_notify(move |stack| {
        let id = state.borrow().as_ref().map(|(id, _, _)| *id);
        if stack.visible_child_name().as_deref() != Some("browser-permission")
            && let Some(id) = id
        {
            end(id, false);
        }
    });
    let (state, end) = (pending.clone(), finish.clone());
    web.connect_load_changed(move |_, event| {
        if event == webkit6::LoadEvent::Started {
            let id = state.borrow().as_ref().map(|(id, _, _)| *id);
            if let Some(id) = id {
                end(id, false);
            }
        }
    });
    let (route, output, feedback) = (stack.clone(), status.clone(), feedback.clone());
    web.connect_permission_request(move |view, request| {
        let old = pending.borrow().as_ref().map(|(id, _, _)| *id);
        if let Some(id) = old {
            finish(id, false);
        }
        let Some(media) = request.downcast_ref::<webkit6::UserMediaPermissionRequest>() else {
            request.deny();
            output.set_text(&tr("browser-permission-unsupported", &[]));
            return true;
        };
        let uri = view.uri().unwrap_or_default().to_string();
        if rampi_core::config::validate_https(&uri).is_err() || uri.len() > 8192 {
            request.deny();
            output.set_text(&tr("browser-permission-https", &[]));
            return true;
        }
        let scope = match (media.is_for_audio_device(), media.is_for_video_device()) {
            (true, true) => "browser-media-both",
            (true, false) => "browser-media-audio",
            (false, true) => "browser-media-video",
            _ => {
                request.deny();
                output.set_text(&tr("browser-permission-unsupported", &[]));
                return true;
            }
        };
        let id = gtk::glib::monotonic_time();
        *pending.borrow_mut() = Some((id, request.clone(), uri.clone()));
        let page = column();
        page.append(&label(&tr("browser-permission-heading", &[])));
        page.append(&label(&uri));
        page.append(&label(&tr(scope, &[])));
        page.append(&label(&tr("browser-permission-description", &[])));
        let no = button(&tr("action-cancel", &[]), &feedback);
        no.set_widget_name("rampi-back");
        let yes = button(&tr("browser-permission-allow", &[]), &feedback);
        page.append(&no);
        page.append(&yes);
        let done = finish.clone();
        no.connect_clicked(move |_| done(id, false));
        let done = finish.clone();
        yes.connect_clicked(move |_| done(id, true));
        route.add_named(&page, Some("browser-permission"));
        route.set_visible_child_name("browser-permission");
        no.grab_focus();
        let done = finish.clone();
        gtk::glib::timeout_add_seconds_local_once(60, move || done(id, false));
        true
    });
}
