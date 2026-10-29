//! GTK keeps button semantics, focus, sizing and accessibility; Cairo paints the surface.
use gtk::{glib, prelude::*, subclass::prelude::*};
use std::{cell::RefCell, time::Instant};

mod imp {
    use super::*;
    #[derive(Default)]
    pub struct LiquidButton {
        pub state: RefCell<Option<(crate::widgets::Shared, Instant, Instant)>>,
    }
    #[glib::object_subclass]
    impl ObjectSubclass for LiquidButton {
        const NAME: &'static str = "RampiLiquidButton";
        type Type = super::LiquidButton;
        type ParentType = gtk::Button;
    }
    impl ObjectImpl for LiquidButton {}
    impl WidgetImpl for LiquidButton {
        fn snapshot(&self, snapshot: &gtk::Snapshot) {
            let object = self.obj();
            let state = self.state.borrow();
            if let Some((settings, start, pulse)) = state.as_ref() {
                let flags = object.state_flags();
                let selected = object.surface_selected();
                let category = object.has_css_class("settings-category");
                if !category || selected {
                    let reduced = crate::widgets::motion_reduced(settings);
                    let mut edges = rampi_core::motion::shape(
                        start.elapsed().as_secs_f64(),
                        selected,
                        Some(pulse.elapsed().as_secs_f64()),
                        reduced,
                    );
                    for edge in &mut edges {
                        for point in edge {
                            *point *= 0.25;
                        }
                    }
                    let width = object.width() as f64;
                    let height = object.height() as f64;
                    if width > 8.0 && height > 8.0 {
                        let cr = snapshot.append_cairo(&gtk::graphene::Rect::new(
                            0.0,
                            0.0,
                            width as f32,
                            height as f32,
                        ));
                        cr.translate(4.0, 4.0);
                        crate::widgets::wave_path(&cr, width - 8.0, height - 8.0, 8.0, edges);
                        let color = if category {
                            (0.07, 0.33, 0.54)
                        } else if flags.contains(gtk::StateFlags::ACTIVE) {
                            (0.24, 0.39, 0.49)
                        } else if selected {
                            (0.20, 0.33, 0.43)
                        } else {
                            (0.125, 0.216, 0.275)
                        };
                        cr.set_source_rgb(color.0, color.1, color.2);
                        let _ = cr.fill();
                    }
                }
            }
            drop(state);
            self.parent_snapshot(snapshot);
        }
    }
    impl ButtonImpl for LiquidButton {}
}
glib::wrapper! {
    pub struct LiquidButton(ObjectSubclass<imp::LiquidButton>)
        @extends gtk::Button, gtk::Widget,
        @implements gtk::Accessible, gtk::Buildable, gtk::ConstraintTarget, gtk::Actionable;
}
impl LiquidButton {
    fn surface_selected(&self) -> bool {
        let flags = self.state_flags();
        if self.has_css_class("settings-category") {
            // Category navigation has one selection across mouse and keyboard.
            flags.contains(gtk::StateFlags::FOCUSED)
        } else {
            flags.intersects(gtk::StateFlags::PRELIGHT | gtk::StateFlags::FOCUSED)
        }
    }
    fn pad_child(&self) {
        if let Some(child) = self.child() {
            // Keep spacing in GTK's layout, outside the surface snapshot coordinates.
            let horizontal = if self.has_css_class("settings-category") {
                22
            } else {
                18
            };
            child.set_margin_top(12);
            child.set_margin_bottom(12);
            child.set_margin_start(horizontal);
            child.set_margin_end(horizontal);
        }
    }
    pub fn with_settings(text: &str, settings: crate::widgets::Shared) -> gtk::Button {
        let object: Self = glib::Object::builder().property("label", text).build();
        object.add_css_class("liquid");
        object.pad_child();
        object.connect_child_notify(|object| object.pad_child());
        object.connect_notify_local(Some("css-classes"), |object, _| object.pad_child());
        *object.imp().state.borrow_mut() = Some((settings, Instant::now(), Instant::now()));
        object.connect_state_flags_changed(|object, previous| {
            let now = object.state_flags();
            if now != previous {
                if let Some((_, _, pulse)) = object.imp().state.borrow_mut().as_mut() {
                    *pulse = Instant::now();
                }
                object.queue_draw();
            }
        });
        let previous_reduced = std::cell::Cell::new(false);
        object.add_tick_callback(move |object, _| {
            if let Some((settings, _, pulse)) = object.imp().state.borrow().as_ref() {
                let selected = object.surface_selected();
                let reduced = crate::widgets::motion_reduced(settings);
                if previous_reduced.replace(reduced) != reduced {
                    object.queue_draw();
                }
                if object.is_mapped() && !reduced && (selected || pulse.elapsed().as_millis() < 250)
                {
                    object.queue_draw();
                }
            }
            glib::ControlFlow::Continue
        });
        object.upcast()
    }
}
