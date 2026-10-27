use crate::widgets::*;
use gtk::{glib, prelude::*};
use rampi_core::i18n::text as tr;
use std::{cell::RefCell, rc::Rc};
use vte::prelude::*;

pub fn build(
    stack: &gtk::Stack,
    conf: &Shared,
    status: &gtk::Label,
    field: &gtk::Entry,
    f: &Feedback,
) -> gtk::Box {
    let page = column();
    page.append(&label(&tr("ssh-heading", &[])));
    let generate = button(&tr("ssh-generate", &[]), f);
    let adopt = button(&tr("ssh-adopt", &[]), f);
    let public = button(&tr("ssh-public", &[]), f);
    let scan = button(&tr("ssh-scan", &[]), f);
    let unlock = button(&tr("ssh-unlock", &[]), f);
    let output = label("");
    output.set_selectable(true);
    for b in [&generate, &adopt, &public, &unlock, &scan] {
        page.append(b);
    }
    page.append(&output);
    page.append(&label(&tr("ssh-unlock-description", &[])));
    let (s, c, stat) = (stack.clone(), conf.clone(), status.clone());
    let unlocking = Rc::new(RefCell::new(None::<String>));
    unlock.connect_clicked(move |button| {
        if let Some(key) = unlocking.borrow().as_ref() {
            s.set_visible_child_name(key);
            return;
        }
        let identity = c.borrow().host().map(|h| h.identity.clone());
        let args = identity.and_then(|identity| crate::ssh_setup::unlock_arguments(&identity));
        match args {
            Ok(args) => {
                let name = format!("ssh-unlock-{}", glib::monotonic_time());
                crate::views::terminal(&s, &name, args, &stat);
                let key = format!("terminal-{name}");
                if let Some(term) = s
                    .child_by_name(&key)
                    .and_then(|w| w.downcast::<vte::Terminal>().ok())
                {
                    *unlocking.borrow_mut() = Some(key);
                    button.set_label(&tr("ssh-unlock-resume", &[]));
                    let (state, button, stat) =
                        (unlocking.clone(), button.downgrade(), stat.clone());
                    term.connect_child_exited(move |_, code| {
                        state.borrow_mut().take();
                        if let Some(button) = button.upgrade() {
                            button.set_label(&tr("ssh-unlock", &[]));
                        }
                        stat.set_text(&tr(
                            if code == 0 {
                                "ssh-unlock-done"
                            } else {
                                "ssh-unlock-failed"
                            },
                            &[],
                        ));
                    });
                }
            }
            Err(e) => stat.set_text(&e.to_string()),
        }
    });
    page.append(&label(&tr("ssh-generate-description", &[])));
    let (s, stat) = (stack.clone(), status.clone());
    let running = Rc::new(RefCell::new(None::<String>));
    generate.connect_clicked(move |button| {
        if let Some(key) = running.borrow().as_ref() {
            s.set_visible_child_name(key);
            return;
        }
        match crate::ssh_setup::generate_arguments() {
            Ok(args) => {
                let name = format!("keygen-{}", glib::monotonic_time());
                crate::views::terminal(&s, &name, args, &stat);
                let key = format!("terminal-{name}");
                if let Some(term) = s
                    .child_by_name(&key)
                    .and_then(|w| w.downcast::<vte::Terminal>().ok())
                {
                    *running.borrow_mut() = Some(key);
                    button.set_label(&tr("ssh-generate-resume", &[]));
                    let (state, button) = (running.clone(), button.clone());
                    term.connect_child_exited(move |_, _| {
                        state.borrow_mut().take();
                        button.set_label(&tr("ssh-generate", &[]));
                    });
                }
            }
            Err(e) => stat.set_text(&e.to_string()),
        }
    });
    let (field, stat) = (field.clone(), status.clone());
    adopt.connect_clicked(move |_| {
        let result = crate::ssh_setup::key_path().and_then(|path| {
            anyhow::ensure!(path.is_file(), "{}", tr("ssh-create-first", &[]));
            field.set_text(&path.to_string_lossy());
            Ok(())
        });
        status_result(&stat, result);
    });
    let stat = status.clone();
    public.connect_clicked(move |_| {
        let result = crate::ssh_setup::key_path().and_then(|p| {
            use std::io::Read;
            let mut value = String::new();
            std::fs::File::open(p.with_extension("pub"))?
                .take(16385)
                .read_to_string(&mut value)?;
            anyhow::ensure!(
                value.len() <= 16384 && value.starts_with("ssh-ed25519 "),
                "{}",
                tr("ssh-public-invalid", &[])
            );
            output.set_text(value.trim());
            Ok(())
        });
        status_result(&stat, result);
    });
    let (s, c, stat, feed) = (stack.clone(), conf.clone(), status.clone(), f.clone());
    let source_page = page.downgrade();
    scan.connect_clicked(move |button| {
        let host = match c.borrow().host() {
            Ok(h) => h.clone(),
            Err(e) => {
                stat.set_text(&e.to_string());
                return;
            }
        };
        button.set_sensitive(false);
        let (s, stat, f, button, page, current) = (
            s.clone(),
            stat.clone(),
            feed.clone(),
            button.clone(),
            source_page.clone(),
            c.clone(),
        );
        glib::MainContext::default().spawn_local(async move {
            match crate::ssh_setup::scan(host).await {
                Ok(scanned) => {
                    let same = current.borrow().host().is_ok_and(|h| {
                        h.address == scanned.host.address
                            && h.port == scanned.host.port
                            && h.username == scanned.host.username
                    });
                    if same && page.upgrade().is_some_and(|p| p.is_mapped()) {
                        confirmation(&s, scanned, &stat, &f);
                    }
                }
                Err(e) => stat.set_text(&e.to_string()),
            }
            button.set_sensitive(true);
        });
    });
    page
}

fn confirmation(
    stack: &gtk::Stack,
    scanned: crate::ssh_setup::Scanned,
    status: &gtk::Label,
    f: &Feedback,
) {
    if let Some(previous) = stack.child_by_name("ssh-trust") {
        stack.remove(&previous);
    }
    let page = column();
    page.append(&label(&tr(
        "ssh-host-heading",
        &[
            ("host", &scanned.host.address),
            ("port", &scanned.host.port.to_string()),
        ],
    )));
    let fingerprint = label(&scanned.fingerprint);
    fingerprint.set_selectable(true);
    fingerprint.set_widget_name("ssh-fingerprint");
    page.append(&fingerprint);
    page.append(&label(&tr("ssh-fingerprint-description", &[])));
    let expected = gtk::Entry::builder()
        .placeholder_text(tr("ssh-fingerprint-input", &[]))
        .build();
    expected.set_widget_name("ssh-expected");
    page.append(&expected);
    let no = button(&tr("action-cancel", &[]), f);
    no.set_widget_name("rampi-back");
    let yes = button(&tr("ssh-trust", &[]), f);
    page.append(&no);
    page.append(&yes);
    let pending = Rc::new(RefCell::new(Some(scanned)));
    let (s, p) = (stack.clone(), pending.clone());
    no.connect_clicked(move |_| {
        p.borrow_mut().take();
        s.set_visible_child_name("settings");
    });
    let (s, stat) = (stack.clone(), status.clone());
    yes.connect_clicked(move |button| {
        let Some(scan) = pending.borrow_mut().take() else {
            return;
        };
        button.set_sensitive(false);
        let (s, stat, button, p, value) = (
            s.clone(),
            stat.clone(),
            button.clone(),
            pending.clone(),
            expected.text().to_string(),
        );
        glib::MainContext::default().spawn_local(async move {
            match crate::ssh_setup::accept(&scan, &value).await {
                Ok(()) => {
                    stat.set_text(&tr("ssh-trusted", &[]));
                    if s.visible_child_name().as_deref() == Some("ssh-trust") {
                        s.set_visible_child_name("settings");
                    }
                }
                Err(e) => {
                    stat.set_text(&e.to_string());
                    *p.borrow_mut() = Some(scan);
                }
            }
            button.set_sensitive(true);
        });
    });
    stack.add_named(&page, Some("ssh-trust"));
    stack.set_visible_child_name("ssh-trust");
    no.grab_focus();
}
