//! Branding only. wlgreet owns the exclusive keyboard and all greetd/PAM interaction.
use gtk::{gdk, glib, prelude::*};

pub fn run() -> glib::ExitCode {
    let app = gtk::Application::builder()
        .application_id("org.rampi.LoginBranding")
        .build();
    app.connect_activate(|app| {
        if let Some(window) = app.active_window() {
            window.present();
            return;
        }
        let css = gtk::CssProvider::new();
        css.load_from_string("window { background: #09131c; color: #f5f7fa; } .logo { background: #f5f7fa; border-radius: 24px; padding: 12px; } .welcome { font-size: 32px; font-weight: 700; } .hint { font-size: 18px; color: #c1ceda; }");
        if let Some(display) = gdk::Display::default() {
            gtk::style_context_add_provider_for_display(&display, &css, gtk::STYLE_PROVIDER_PRIORITY_APPLICATION);
        }
        let root = gtk::Box::new(gtk::Orientation::Vertical, 20);
        root.set_margin_top(36);
        root.set_margin_bottom(36);
        root.set_margin_start(36);
        root.set_margin_end(36);
        let header = gtk::Box::new(gtk::Orientation::Horizontal, 28);
        let logo = gtk::Picture::new();
        match gtk::gdk_pixbuf::Pixbuf::from_file_at_scale(crate::widgets::assets().join("branding/logo.png"), 184, 184, true) {
            Ok(pixels) => logo.set_paintable(Some(&gdk::Texture::for_pixbuf(&pixels))),
            Err(error) => eprintln!("Anmeldelogo konnte nicht geladen werden: {error}"),
        }
        logo.set_content_fit(gtk::ContentFit::Contain);
        logo.set_size_request(184, 184);
        logo.set_can_shrink(true);
        logo.set_halign(gtk::Align::Start);
        logo.set_valign(gtk::Align::Start);
        logo.add_css_class("logo");
        header.append(&logo);
        let welcome = gtk::Label::new(Some("Dein Arbeitsplatz.\nBereit, wenn du es bist."));
        welcome.set_xalign(0.0);
        welcome.set_hexpand(true);
        welcome.set_wrap(true);
        welcome.add_css_class("welcome");
        header.append(&welcome);
        root.append(&header);
        let space = gtk::Box::new(gtk::Orientation::Vertical, 0);
        space.set_vexpand(true);
        root.append(&space);
        let hint = gtk::Label::new(Some("Linux-Benutzername → Enter → Passwort → Enter\nDeine Einstellungen und Zugänge bleiben in deinem persönlichen Konto."));
        hint.set_xalign(0.0);
        hint.set_wrap(true);
        hint.add_css_class("hint");
        root.append(&hint);
        let window = gtk::ApplicationWindow::builder().application(app)
            .title("Rampi · Anmeldung").decorated(false).child(&root).build();
        window.fullscreen();
        window.present();
    });
    app.run_with_args::<&str>(&[])
}
