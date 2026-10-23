//! Route WebKit requests to application pages instead of GTK dialog windows.
use crate::widgets::*;
use gtk::prelude::*;
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
        let p = page(&s, "Nachricht der Webseite");
        p.append(&label(dialog.message().as_deref().unwrap_or("")));
        let input = gtk::Entry::new();
        if dialog.dialog_type() == webkit6::ScriptDialogType::Prompt {
            input.set_text(dialog.prompt_get_default_text().as_deref().unwrap_or(""));
        }
        input.set_visible(dialog.dialog_type() == webkit6::ScriptDialogType::Prompt);
        input.set_widget_name("browser-prompt-input");
        p.append(&input);
        let no = button("Abbrechen", &feed);
        no.set_widget_name("rampi-back");
        let yes = button("Bestätigen", &feed);
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
        let p = page(&s, "Anmeldung an der Webseite");
        p.append(&label(&format!(
            "{}:{} · {}",
            request.host().as_deref().unwrap_or("Unbekannter Host"),
            request.port(),
            request.realm().as_deref().unwrap_or("")
        )));
        let user = gtk::Entry::builder()
            .placeholder_text("Benutzername")
            .build();
        let password = gtk::PasswordEntry::builder()
            .placeholder_text("Kennwort")
            .build();
        p.append(&user);
        p.append(&password);
        let no = button("Abbrechen", &feed);
        no.set_widget_name("rampi-back");
        let yes = button("Anmelden", &feed);
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
    let (s, feed, stat) = (stack.clone(), f.clone(), status.clone());
    web.connect_run_file_chooser(move |_,request|{
        let p=page(&s,"Datei für die Webseite auswählen");p.append(&label("Vollständigen Pfad zur gewünschten Datei eingeben. Erst mit Bestätigen erhält die Webseite Zugriff."));let path=gtk::Entry::builder().placeholder_text("/home/user/Datei").build();p.append(&path);let no=button("Abbrechen",&feed);no.set_widget_name("rampi-back");let yes=button("Diese Datei auswählen",&feed);p.append(&no);p.append(&yes);
        let(r,back_stack)=(request.clone(),s.clone());no.connect_clicked(move |_|{r.cancel();back_stack.set_visible_child_name("browser");});let(r,s,stat)=(request.clone(),s.clone(),stat.clone());yes.connect_clicked(move |_|{let selected=path.text();let file=std::path::Path::new(selected.as_str());if file.is_absolute()&&file.is_file(){r.select_files(&[selected.as_str()]);s.set_visible_child_name("browser");}else{stat.set_text("Bitte den vollständigen Pfad zu einer vorhandenen Datei eingeben.");}});no.grab_focus();true
    });
    let stat = status.clone();
    web.connect_permission_request(move |_,request|{request.deny();stat.set_text("Die Webseite benötigt eine zusätzliche Geräteberechtigung. Diese ist in diesem Entwicklungsstand noch nicht freigeschaltet.");true});
}
