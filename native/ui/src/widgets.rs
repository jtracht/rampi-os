use gtk::{glib, prelude::*};
use rampi_core::{config::Settings, motion};
use std::{
    cell::{Cell, RefCell},
    path::PathBuf,
    rc::Rc,
    time::Instant,
};
pub type Shared = Rc<RefCell<Settings>>;

pub(crate) fn motion_reduced(settings: &Shared) -> bool {
    settings.borrow().reduce_motion
        || gtk::Settings::default().is_some_and(|s| !s.is_gtk_enable_animations())
}

/// Existing GTK focus/selection with all choices in the current page, no popover.
pub fn inline_choices(values: &[&str], feedback: &Feedback) -> gtk::ListBox {
    let list = gtk::ListBox::new();
    list.set_selection_mode(gtk::SelectionMode::Single);
    list.add_css_class("inline-choices");
    replace_choices(&list, values);
    let click = feedback.clone();
    list.connect_row_activated(move |_, _| click.play(true));
    let feedback = feedback.clone();
    list.connect_row_selected(move |list, row| {
        // Populating a hidden settings page is not a user navigation action.
        if list.is_mapped() && row.is_some() {
            feedback.play(false);
        }
    });
    list
}

pub fn replace_choices(list: &gtk::ListBox, values: &[&str]) {
    while let Some(child) = list.first_child() {
        list.remove(&child);
    }
    for value in values {
        list.append(&label(value));
    }
    list.select_row(list.row_at_index(0).as_ref());
}

pub fn choice_index(list: &gtk::ListBox) -> u32 {
    list.selected_row()
        .map_or(u32::MAX, |row| row.index() as u32)
}
#[derive(Clone)]
pub struct Feedback {
    settings: Shared,
    audio: Rc<Option<crate::audio::Sound>>,
    last: Rc<Cell<Instant>>,
}
impl Feedback {
    pub fn settings_language(&self) -> String {
        self.settings.borrow().language.clone()
    }
    pub fn save_language(&self, language: &str) -> anyhow::Result<()> {
        anyhow::ensure!(
            rampi_core::i18n::locale(language).is_some(),
            "{}",
            rampi_core::i18n::text("language-invalid", &[])
        );
        let mut updated = self.settings.borrow().clone();
        updated.language = language.into();
        updated.save(&rampi_core::config::config_dir()?.join("settings.json"))?;
        *self.settings.borrow_mut() = updated;
        Ok(())
    }
    pub fn prepared(&self) -> bool {
        self.audio.is_some()
    }
    pub fn new(settings: Shared) -> Self {
        let audio = Rc::new(crate::audio::Sound::new(
            &assets().join("sounds/select.wav"),
            &assets().join("sounds/click.wav"),
        ));
        Self {
            settings,
            audio,
            last: Rc::new(Cell::new(Instant::now())),
        }
    }
    pub fn play(&self, click: bool) {
        if !self.settings.borrow().sound_effects
            || (!click && self.last.get().elapsed().as_millis() < 65)
        {
            return;
        }
        self.last.set(Instant::now());
        if let Some(audio) = self.audio.as_ref() {
            let code = audio.play(click);
            if code < 0 && std::env::var("RAMPI_TEST_CONTAINER").as_deref() == Ok("1") {
                eprintln!("Audio playback unavailable: canberra error {code}");
            }
        }
    }
}
pub fn button(text: &str, feedback: &Feedback) -> gtk::Button {
    let b = crate::liquid_button::LiquidButton::with_settings(text, feedback.settings.clone());
    wire_button(&b, feedback);
    b
}
pub fn wire_button(b: &gtk::Button, feedback: &Feedback) {
    let f = feedback.clone();
    b.connect_clicked(move |_| f.play(true));
    let m = gtk::EventControllerMotion::new();
    let f = feedback.clone();
    m.connect_enter(move |_, _, _| f.play(false));
    b.add_controller(m);
    let c = gtk::EventControllerFocus::new();
    let f = feedback.clone();
    c.connect_enter(move |_| f.play(false));
    b.add_controller(c);
}
pub fn icon_button(text: &str, icon: &str, f: &Feedback) -> gtk::Button {
    let b = button("", f);
    let content = row();
    content.set_halign(gtk::Align::Center);
    let image = icon_image(icon, 24);
    content.append(&image);
    let text = label(text);
    text.set_max_width_chars(18);
    content.append(&text);
    b.set_child(Some(&content));
    b.set_valign(gtk::Align::Center);
    b
}
fn icon_image(name: &str, size: i32) -> gtk::Image {
    let image = match gtk::gdk_pixbuf::Pixbuf::from_file_at_scale(
        assets().join("icons").join(format!("{name}.svg")),
        size,
        size,
        true,
    ) {
        Ok(pixbuf) => gtk::Image::from_paintable(Some(&gtk::gdk::Texture::for_pixbuf(&pixbuf))),
        Err(_) => gtk::Image::from_icon_name("image-missing-symbolic"),
    };
    image.set_pixel_size(size);
    image
}
pub fn label(text: &str) -> gtk::Label {
    let l = gtk::Label::new(Some(text));
    l.set_xalign(0.0);
    l.set_wrap(true);
    l
}
pub fn column() -> gtk::Box {
    gtk::Box::new(gtk::Orientation::Vertical, 14)
}
pub fn row() -> gtk::Box {
    gtk::Box::new(gtk::Orientation::Horizontal, 14)
}
pub fn scroll(child: &impl IsA<gtk::Widget>) -> gtk::ScrolledWindow {
    gtk::ScrolledWindow::builder()
        .child(child)
        .hexpand(true)
        .vexpand(true)
        .build()
}
pub fn status_result(status: &gtk::Label, result: anyhow::Result<()>) {
    status.set_text(&match result {
        Ok(()) => rampi_core::i18n::text("action-completed", &[]),
        Err(e) => e.to_string(),
    });
}
pub struct TileSpec<'a> {
    pub title: &'a str,
    pub subtitle: &'a str,
    pub color: (f64, f64, f64),
    pub dark: bool,
    pub delay: f64,
}
pub fn tile(spec: TileSpec<'_>, settings: &Shared, feedback: &Feedback) -> gtk::Button {
    let TileSpec {
        title,
        subtitle,
        color,
        dark,
        delay,
    } = spec;
    // Dashboard tiles already paint their own liquid surface below. Keep a
    // native button here rather than adding a second skin and its child margins.
    let b = gtk::Button::new();
    wire_button(&b, feedback);
    b.add_css_class("tile");
    b.set_hexpand(true);
    b.set_vexpand(true);
    b.set_widget_name(title);
    let overlay = gtk::Overlay::new();
    let area = gtk::DrawingArea::new();
    area.set_content_width(180);
    area.set_content_height(230);
    area.set_hexpand(true);
    area.set_vexpand(true);
    overlay.set_child(Some(&area));
    let content = column();
    content.set_halign(gtk::Align::Center);
    content.set_valign(gtk::Align::Center);
    content.set_margin_start(12);
    content.set_margin_end(12);
    let icon = match title {
        "Kanban Board" => "columns-3",
        "Remote Desktop" => "monitor",
        _ => "globe",
    };
    let image = icon_image(icon, 76);
    content.append(&image);
    let heading = label(title);
    heading.add_css_class("tile-title");
    heading.set_xalign(0.5);
    heading.set_max_width_chars(12);
    heading.set_justify(gtk::Justification::Center);
    content.append(&heading);
    let sub = label(subtitle);
    sub.set_xalign(0.5);
    sub.set_max_width_chars(17);
    sub.set_justify(gtk::Justification::Center);
    content.append(&sub);
    content.add_css_class(if dark { "dark-ink" } else { "light-ink" });
    overlay.add_overlay(&content);
    b.set_child(Some(&overlay));
    let start = Rc::new(Cell::new(Instant::now()));
    let first_map = Rc::new(Cell::new(true));
    let (clock, first) = (start.clone(), first_map);
    b.connect_map(move |_| {
        if first.replace(false) {
            clock.set(Instant::now());
        }
    });
    let pulse = Rc::new(Cell::new(-10.0));
    let selected = Rc::new(Cell::new(false));
    let settings = settings.clone();
    let (p, s, conf, clock) = (
        pulse.clone(),
        selected.clone(),
        settings.clone(),
        start.clone(),
    );
    area.set_draw_func(move |_, cr, width, height| {
        let t = clock.get().elapsed().as_secs_f64();
        let impulse = if t < delay + 0.24 && t >= delay {
            Some(t - delay)
        } else {
            Some(t - p.get())
        };
        let [a, b, c, d] = motion::shape(t, s.get(), impulse, motion_reduced(&conf));
        let (w, h, r) = (width as f64 - 20.0, height as f64 - 20.0, 26.0);
        cr.translate(10.0, 10.0);
        wave_path(cr, w, h, r, [a, b, c, d]);
        let light = if s.get() { 1.1 } else { 1.0 };
        cr.set_source_rgb(
            (color.0 * light).min(1.0),
            (color.1 * light).min(1.0),
            (color.2 * light).min(1.0),
        );
        let _ = cr.fill();
    });
    let (p, s) = (pulse.clone(), selected.clone());
    let focus = gtk::EventControllerFocus::new();
    let draw = area.clone();
    let clock = start.clone();
    focus.connect_enter(move |_| {
        p.set(clock.get().elapsed().as_secs_f64());
        s.set(true);
        draw.queue_draw();
    });
    let s = selected.clone();
    let draw = area.clone();
    focus.connect_leave(move |_| {
        s.set(false);
        draw.queue_draw();
    });
    b.add_controller(focus);
    let hover = gtk::EventControllerMotion::new();
    let weak = b.downgrade();
    hover.connect_enter(move |_, _, _| {
        if let Some(b) = weak.upgrade() {
            b.grab_focus();
        }
    });
    b.add_controller(hover);
    let previous_reduced = Cell::new(motion_reduced(&settings));
    area.add_tick_callback(move |area, _| {
        let t = start.get().elapsed().as_secs_f64();
        let reduced = motion_reduced(&settings);
        if previous_reduced.replace(reduced) != reduced {
            area.queue_draw();
        }
        if !reduced && (selected.get() || t < delay + 0.3 || t - pulse.get() < 0.3) {
            area.queue_draw();
        }
        glib::ControlFlow::Continue
    });
    b
}
pub fn assets() -> PathBuf {
    std::env::var_os("RAMPI_ASSETS")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("/usr/share/rampi"))
}

pub(crate) fn wave_path(
    cr: &gtk::cairo::Context,
    w: f64,
    h: f64,
    radius: f64,
    [a, b, c, d]: [[f64; 2]; 4],
) {
    let r = radius.min(w / 2.0).min(h / 2.0);
    cr.move_to(r, 0.0);
    cr.curve_to(w * 0.23, a[0], w * 0.71, a[1], w - r, 0.0);
    cr.curve_to(w, 0.0, w, 0.0, w, r);
    cr.curve_to(w + b[0], h * 0.29, w + b[1], h * 0.73, w, h - r);
    cr.curve_to(w, h, w, h, w - r, h);
    cr.curve_to(w * 0.68, h + c[0], w * 0.31, h + c[1], r, h);
    cr.curve_to(0.0, h, 0.0, h, 0.0, h - r);
    cr.curve_to(d[0], h * 0.64, d[1], h * 0.24, 0.0, r);
    cr.curve_to(0.0, 0.0, 0.0, 0.0, r, 0.0);
    cr.close_path();
}
