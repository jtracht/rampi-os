//! WebKit performs all transfers; Rampi supplies one inline destination/queue page.
use crate::widgets::*;
use gtk::{glib, prelude::*};
use rampi_core::i18n::text as tr;
use std::{cell::Cell, rc::Rc};
pub fn install(session: &webkit6::NetworkSession, stack: &gtk::Stack, f: &Feedback) {
    let page = column();
    page.append(&label(&tr("downloads-heading", &[])));
    let back = button(&tr("browser-back", &[]), f);
    back.set_widget_name("rampi-back");
    let s = stack.clone();
    back.connect_clicked(move |_| s.set_visible_child_name("browser"));
    page.append(&back);
    let clear = button(&tr("downloads-clear", &[]), f);
    page.append(&clear);
    let rows = column();
    page.append(&scroll(&rows));
    stack.add_named(&page, Some("browser-downloads"));
    let active = Rc::new(Cell::new(0usize));
    let count = Rc::new(Cell::new(0usize));
    let (a, n, r) = (active.clone(), count.clone(), rows.clone());
    clear.connect_clicked(move |_| {
        if a.get() != 0 {
            return;
        }
        while let Some(row) = r.first_child() {
            r.remove(&row);
        }
        n.set(0);
    });
    let (s, feedback) = (stack.clone(), f.clone());
    session.connect_download_started(move |_, download| {
        if count.get() >= 16 {
            download.cancel();
            return;
        }
        count.set(count.get() + 1);
        active.set(active.get() + 1);
        clear.set_sensitive(false);
        download.set_allow_overwrite(false);
        let section = column();
        rows.append(&section);
        let progress = label(&tr("downloads-wait", &[]));
        section.append(&progress);
        let path = gtk::Entry::builder()
            .placeholder_text(tr("downloads-path", &[]))
            .build();
        path.set_widget_name("download-path");
        section.append(&path);
        let save = button(&tr("downloads-save", &[]), &feedback);
        save.set_sensitive(false);
        section.append(&save);
        let cancel = button(&tr("downloads-cancel", &[]), &feedback);
        section.append(&cancel);
        let started = Rc::new(Cell::new(false));
        let failed = Rc::new(Cell::new(false));
        let finished = Rc::new(Cell::new(false));
        let (p, save1, stat, s1) = (path.clone(), save.clone(), progress.clone(), s.clone());
        download.connect_decide_destination(move |_, suggested| {
            let basename = std::path::Path::new(suggested)
                .file_name()
                .and_then(|p| p.to_str())
                .filter(|p| !p.chars().any(char::is_control))
                .unwrap_or("download.bin");
            let directory = glib::user_special_dir(glib::UserDirectory::Downloads)
                .unwrap_or_else(|| glib::home_dir().join("Downloads"));
            p.set_text(&directory.join(basename).to_string_lossy());
            stat.set_text(&tr("downloads-destination", &[]));
            save1.set_sensitive(true);
            s1.set_visible_child_name("browser-downloads");
            true
        });
        let (d, stat, start) = (download.clone(), progress.clone(), started.clone());
        save.connect_clicked(move |b| {
            if start.get() {
                return;
            }
            let result: anyhow::Result<()> = (|| {
                let text = path.text();
                let destination = std::path::Path::new(text.as_str());
                anyhow::ensure!(
                    destination.is_absolute()
                        && destination.file_name().is_some()
                        && !text.chars().any(char::is_control),
                    "{}",
                    tr("downloads-full-path", &[])
                );
                anyhow::ensure!(
                    !destination.try_exists()? && std::fs::symlink_metadata(destination).is_err(),
                    "{}",
                    tr("downloads-exists", &[])
                );
                let parent = destination
                    .parent()
                    .ok_or_else(|| anyhow::anyhow!(tr("downloads-no-parent", &[])))?;
                if !parent.exists() && parent == glib::home_dir().join("Downloads") {
                    use std::os::unix::fs::DirBuilderExt;
                    std::fs::DirBuilder::new().mode(0o700).create(parent)?;
                }
                anyhow::ensure!(parent.is_dir(), "{}", tr("downloads-no-directory", &[]));
                start.set(true);
                path.set_sensitive(false);
                b.set_sensitive(false);
                d.set_destination(&text);
                stat.set_text(&tr("downloads-running", &[]));
                Ok(())
            })();
            if let Err(e) = result {
                stat.set_text(&e.to_string());
            }
        });
        let d = download.clone();
        cancel.connect_clicked(move |_| d.cancel());
        let stat = progress.clone();
        download.connect_received_data(move |d, _| {
            stat.set_text(&format!(
                "{} % · {} Bytes",
                (100.0 * d.estimated_progress()).round() as u32,
                d.received_data_length()
            ));
        });
        let (stat, bad) = (progress.clone(), failed.clone());
        download.connect_failed(move |_, _| {
            bad.set(true);
            stat.set_text(&tr("downloads-failed", &[]));
        });
        let (a, done, clear1, bad, stat, save1) = (
            active.clone(),
            finished.clone(),
            clear.clone(),
            failed,
            progress,
            save,
        );
        download.connect_finished(move |_| {
            if done.replace(true) {
                return;
            }
            a.set(a.get().saturating_sub(1));
            clear1.set_sensitive(a.get() == 0);
            save1.set_sensitive(false);
            cancel.set_sensitive(false);
            if !bad.get() {
                stat.set_text(&tr("downloads-complete", &[]));
            }
        });
        let (d, start, done) = (download.downgrade(), started, finished);
        glib::timeout_add_seconds_local_once(60, move || {
            if !start.get()
                && !done.get()
                && let Some(d) = d.upgrade()
            {
                d.cancel();
            }
        });
    });
}
