//! GTK input and the existing RDW keycode database; no device/protocol driver.
use gtk::{gdk, glib, prelude::*};
use rampi_stream::runtime::{
    KeyAction, KeyModifiers, MouseButton, MouseButtonAction, RemoteControl,
};
use std::{
    cell::RefCell,
    collections::{BTreeMap, BTreeSet},
    rc::Rc,
};
type Active = Rc<RefCell<Option<RemoteControl>>>;

// Translate through the existing generated QEMU/Win32 database used by RDW.
fn virtual_key(keycode: u32) -> Option<(i16, u8)> {
    let qnum = *keycodemap::KEYMAP_XORGEVDEV2QNUM.get(keycode as usize)?;
    if qnum == 0 {
        return None;
    }
    let vk = keycodemap::KEYMAP_WIN322QNUM
        .iter()
        .position(|n| *n == qnum)
        .or_else(|| (qnum == 0x9c).then_some(0x0d))?;
    Some((
        (vk as u16 | 0x8000) as i16,
        if *keycodemap::KEYMAP_XORGEVDEV2XTKBD.get(keycode as usize)? > 0xff {
            0x10
        } else {
            0
        },
    ))
}
fn modifiers(state: gdk::ModifierType) -> u8 {
    [
        (gdk::ModifierType::SHIFT_MASK, 1),
        (gdk::ModifierType::CONTROL_MASK, 2),
        (gdk::ModifierType::ALT_MASK, 4),
        (gdk::ModifierType::SUPER_MASK, 8),
    ]
    .into_iter()
    .fold(0, |bits, (mask, bit)| {
        bits | if state.contains(mask) { bit } else { 0 }
    })
}

fn mouse_button(code: u32) -> Option<MouseButton> {
    match code {
        1 => Some(MouseButton::Left),
        2 => Some(MouseButton::Middle),
        3 => Some(MouseButton::Right),
        _ => None,
    }
}

pub fn attach(picture: &gtk::Picture, active: &Active) {
    let down = Rc::new(RefCell::new(BTreeMap::<u32, (i16, u8)>::new()));
    let mouse_down = Rc::new(RefCell::new(BTreeSet::<u32>::new()));
    let keys = gtk::EventControllerKey::new();
    let (a, pressed) = (active.clone(), down.clone());
    keys.connect_key_pressed(move |_, key, code, state| {
        // The top-level capture controller handles this before remote input.
        if key == gdk::Key::Home
            && state.contains(gdk::ModifierType::CONTROL_MASK | gdk::ModifierType::ALT_MASK)
        {
            return glib::Propagation::Proceed;
        }
        if let Some(control) = a.borrow().as_ref()
            && let Some((vk, ext)) = virtual_key(code)
        {
            let bits = modifiers(state) | ext;
            if control
                .keyboard(
                    vk,
                    KeyAction::Down,
                    KeyModifiers::from_bits_truncate(bits as i8),
                )
                .is_ok()
            {
                pressed.borrow_mut().insert(code, (vk, bits));
            }
            return glib::Propagation::Stop;
        }
        glib::Propagation::Proceed
    });
    let (a, pressed) = (active.clone(), down.clone());
    keys.connect_key_released(move |_, _, code, _| {
        if let Some((vk, bits)) = pressed.borrow_mut().remove(&code)
            && let Some(control) = a.borrow().as_ref()
        {
            let _ = control.keyboard(
                vk,
                KeyAction::Up,
                KeyModifiers::from_bits_truncate(bits as i8),
            );
        }
    });
    picture.add_controller(keys);
    let focus = gtk::EventControllerFocus::new();
    let (a, pressed, buttons) = (active.clone(), down, mouse_down.clone());
    let release: Rc<dyn Fn()> = Rc::new(move || {
        for (_, (vk, bits)) in std::mem::take(&mut *pressed.borrow_mut()) {
            if let Some(control) = a.borrow().as_ref() {
                let _ = control.keyboard(
                    vk,
                    KeyAction::Up,
                    KeyModifiers::from_bits_truncate(bits as i8),
                );
            }
        }
        for button in std::mem::take(&mut *buttons.borrow_mut()) {
            if let (Some(control), Some(button)) = (a.borrow().as_ref(), mouse_button(button)) {
                let _ = control.mouse_button(button, MouseButtonAction::Release);
            }
        }
    });
    let on_leave = release.clone();
    focus.connect_leave(move |_| on_leave());
    let on_unmap = release.clone();
    picture.connect_unmap(move |_| on_unmap());
    picture.add_controller(focus);
    let motion = gtk::EventControllerMotion::new();
    let (a, weak) = (active.clone(), picture.downgrade());
    motion.connect_motion(move |_, x, y| {
        let Some(picture) = weak.upgrade() else {
            return;
        };
        if let Some(control) = a.borrow().as_ref()
            && let Some(paintable) = picture.paintable()
        {
            let (width, height) = (paintable.intrinsic_width(), paintable.intrinsic_height());
            if width <= 0 || height <= 0 {
                return;
            }
            let scale = (picture.width() as f64 / width as f64)
                .min(picture.height() as f64 / height as f64);
            if scale <= 0.0 {
                return;
            }
            let left = (picture.width() as f64 - width as f64 * scale) / 2.0;
            let top = (picture.height() as f64 - height as f64 * scale) / 2.0;
            let (x, y) = ((x - left) / scale, (y - top) / scale);
            if x >= 0.0 && y >= 0.0 && x < width as f64 && y < height as f64 {
                let _ = control.mouse_position(x as i16, y as i16, width as i16, height as i16);
            }
        }
    });
    picture.add_controller(motion);
    let clicks = gtk::GestureClick::new();
    clicks.set_button(0);
    for press in [true, false] {
        let (a, weak, held) = (active.clone(), picture.downgrade(), mouse_down.clone());
        let send = move |gesture: &gtk::GestureClick, _: i32, _: f64, _: f64| {
            if let Some(picture) = weak.upgrade() {
                picture.grab_focus();
            }
            let code = gesture.current_button();
            let Some(button) = mouse_button(code) else {
                return;
            };
            if press {
                held.borrow_mut().insert(code);
            } else if !held.borrow_mut().remove(&code) {
                return;
            }
            if let Some(control) = a.borrow().as_ref() {
                let _ = control.mouse_button(
                    button,
                    if press {
                        MouseButtonAction::Press
                    } else {
                        MouseButtonAction::Release
                    },
                );
            }
        };
        if press {
            clicks.connect_pressed(send);
        } else {
            clicks.connect_released(send);
        }
    }
    clicks.connect_cancel(move |_, _| release());
    picture.add_controller(clicks);
    let scroll = gtk::EventControllerScroll::new(
        gtk::EventControllerScrollFlags::BOTH_AXES | gtk::EventControllerScrollFlags::DISCRETE,
    );
    let a = active.clone();
    scroll.connect_scroll(move |_, dx, dy| {
        if let Some(control) = a.borrow().as_ref() {
            let _ = control.scroll(
                (-dy * 120.0).clamp(-32767.0, 32767.0) as i16,
                (dx * 120.0).clamp(-32767.0, 32767.0) as i16,
            );
            return glib::Propagation::Stop;
        }
        glib::Propagation::Proceed
    });
    picture.add_controller(scroll);
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn existing_database_preserves_extended_physical_keys() {
        assert_eq!(virtual_key(38), Some((0x8041_u16 as i16, 0))); // physical A
        assert_eq!(virtual_key(105), Some((0x80a3_u16 as i16, 0x10))); // right Control
        assert_eq!(virtual_key(104), Some((0x800d_u16 as i16, 0x10))); // numpad Enter
        assert_eq!(virtual_key(36), Some((0x800d_u16 as i16, 0))); // main Enter
        assert_eq!(virtual_key(u32::MAX), None);
        assert_eq!(virtual_key(0), None);
    }
}
