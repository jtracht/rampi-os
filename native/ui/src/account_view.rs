//! Native account actions. PAM/passwd and the session supervisor retain authority.
use crate::widgets::*;
use gtk::prelude::*;
pub fn append(page: &gtk::Box, stack: &gtk::Stack, status: &gtk::Label, f: &Feedback) {
    let uid = gtk::gio::Credentials::new()
        .unix_user()
        .map(|v| v.to_string())
        .unwrap_or_else(|_| "unbekannt".into());
    page.append(&label(&format!(
        "Linux-Konto: {} · UID {uid}",
        gtk::glib::user_name().to_string_lossy()
    )));
    page.append(&label("Linux-PAM und dein Systemkonto verwalten Anmeldung und Kennwort. Rampi speichert keine Linux-Kennwörter. Weitere Konten benötigen vorhandene Administratorrechte."));
    let create = button("Weiteres Linux-Konto einrichten", f);
    let (route, feedback) = (stack.clone(), f.clone());
    create.connect_clicked(move |_| crate::account_create::open(&route, &feedback));
    page.append(&create);
    let password = button("Eigenes Linux-Kennwort ändern", f);
    let (s, stat) = (stack.clone(), status.clone());
    password.connect_clicked(move |_| {
        crate::views::terminal(&s, "linux-password", vec!["passwd".into()], &stat);
    });
    page.append(&password);
    let logout = button("Von Rampi abmelden", f);
    let (s, feedback) = (stack.clone(), f.clone());
    logout.connect_clicked(move |_| {
        if let Some(old) = s.child_by_name("logout") { s.remove(&old); }
        let p = column();
        p.append(&label("Von Rampi abmelden? Lokale Anwendungen und Verbindungen werden geschlossen. Persistente Windows-Sitzungen laufen auf dem Host weiter."));
        let cancel = button("Abbrechen", &feedback); cancel.set_widget_name("rampi-back");
        let confirm = button("Jetzt abmelden", &feedback);
        p.append(&cancel); p.append(&confirm);
        let route = s.clone(); cancel.connect_clicked(move |_| route.set_visible_child_name("settings"));
        let route = s.clone(); confirm.connect_clicked(move |_| {
            if let Some(window) = route.root().and_downcast::<gtk::Window>() && let Some(app) = window.application() { app.quit(); }
        });
        s.add_named(&p, Some("logout")); s.set_visible_child_name("logout"); cancel.grab_focus();
    });
    page.append(&logout);
}
