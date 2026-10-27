//! Personal host profiles; no shell commands or credentials in configuration.
use crate::widgets::*;
use gtk::prelude::*;
use rampi_core::config::{self, Host};
use rampi_core::i18n::text as tr;
use std::{cell::Cell, rc::Rc};

fn persist(conf: &Shared, candidate: rampi_core::config::Settings) -> anyhow::Result<()> {
    candidate.save(&config::config_dir()?.join("settings.json"))?;
    *conf.borrow_mut() = candidate;
    Ok(())
}

pub fn build(stack: &gtk::Stack, conf: &Shared, status: &gtk::Label, f: &Feedback) -> gtk::Box {
    let page = column();
    page.append(&label(&tr("host-heading", &[])));
    let profiles = gtk::ListBox::new();
    profiles.set_widget_name("host-profiles");
    page.append(&profiles);
    let editing: Rc<Cell<Option<usize>>> = Rc::new(Cell::new(None));
    let mut fields = vec![];
    for (name, id) in [
        (&tr("host-name", &[]), "name"),
        (&tr("host-address", &[]), "address"),
        (&tr("host-username", &[]), "username"),
        (&tr("host-port", &[]), "port"),
        (&tr("host-identity", &[]), "identity"),
        (&tr("host-resolution", &[]), "resolution"),
    ] {
        page.append(&label(name));
        let field = gtk::Entry::new();
        field.set_widget_name(&format!("host-{id}"));
        page.append(&field);
        fields.push(field);
    }
    let fields = Rc::new(fields);
    let load: Rc<dyn Fn(&Host)> = {
        let fields = fields.clone();
        Rc::new(move |host| {
            for (field, value) in fields.iter().zip([
                host.name.clone(),
                host.address.clone(),
                host.username.clone(),
                host.port.to_string(),
                host.identity.clone(),
                host.resolution.clone(),
            ]) {
                field.set_text(&value);
            }
        })
    };
    let refresh: Rc<dyn Fn()> = {
        let (profiles, conf) = (profiles.clone(), conf.clone());
        Rc::new(move || {
            while let Some(child) = profiles.first_child() {
                profiles.remove(&child);
            }
            for (i, host) in conf.borrow().hosts.iter().enumerate() {
                profiles.append(&label(&format!(
                    "{}{} · {}@{}:{}",
                    if i == conf.borrow().active_host {
                        "● "
                    } else {
                        ""
                    },
                    host.name,
                    host.username,
                    host.address,
                    host.port
                )));
            }
        })
    };
    let (c, e, l) = (conf.clone(), editing.clone(), load.clone());
    profiles.connect_row_selected(move |_, row| {
        if let Some(row) = row {
            let index = row.index() as usize;
            if let Some(host) = c.borrow().hosts.get(index) {
                e.set(Some(index));
                l(host);
            }
        }
    });
    refresh();
    load(&Host::default());
    profiles.select_row(
        profiles
            .row_at_index(conf.borrow().active_host as i32)
            .as_ref(),
    );
    let actions = column();
    let new = button(&tr("host-new", &[]), f);
    let save = button(&tr("host-save", &[]), f);
    let activate = button(&tr("host-activate", &[]), f);
    let remove = button(&tr("host-remove", &[]), f);
    let confirm = button(&tr("host-remove-confirm", &[]), f);
    let cancel = button(&tr("host-remove-cancel", &[]), f);
    confirm.set_visible(false);
    cancel.set_visible(false);
    for b in [&new, &save, &activate, &remove, &confirm, &cancel] {
        actions.append(b);
    }
    page.append(&actions);
    page.append(&label(&tr("host-remove-description", &[])));
    page.append(&label(&tr("host-ssh-description", &[])));
    let (e, l, p, yes, no) = (
        editing.clone(),
        load,
        profiles.clone(),
        confirm.clone(),
        cancel.clone(),
    );
    new.connect_clicked(move |_| {
        p.unselect_all();
        e.set(None);
        l(&Host::default());
        yes.set_visible(false);
        no.set_visible(false);
    });
    let identity_field = fields[4].clone();
    let (c, e, stat, r, p) = (
        conf.clone(),
        editing.clone(),
        status.clone(),
        refresh.clone(),
        profiles.clone(),
    );
    save.connect_clicked(move |_| {
        let result = (|| -> anyhow::Result<()> {
            let project = e
                .get()
                .and_then(|index| c.borrow().hosts.get(index).map(|host| host.project.clone()))
                .unwrap_or_default();
            let host = Host {
                name: fields[0].text().trim().into(),
                address: fields[1].text().trim().into(),
                username: fields[2].text().trim().into(),
                port: fields[3].text().parse()?,
                identity: fields[4].text().trim().into(),
                project,
                resolution: fields[5].text().trim().into(),
            };
            let mut candidate = c.borrow().clone();
            let index = if let Some(index) = e.get() {
                candidate.hosts[index] = host;
                index
            } else {
                candidate.hosts.push(host);
                candidate.hosts.len() - 1
            };
            persist(&c, candidate)?;
            r();
            p.select_row(p.row_at_index(index as i32).as_ref());
            Ok(())
        })();
        status_result(&stat, result);
    });
    let (c, e, stat, r, p) = (
        conf.clone(),
        editing.clone(),
        status.clone(),
        refresh.clone(),
        profiles.clone(),
    );
    activate.connect_clicked(move |_| {
        let result = (|| -> anyhow::Result<()> {
            let index = e
                .get()
                .ok_or_else(|| anyhow::anyhow!(tr("host-select-saved", &[])))?;
            let mut candidate = c.borrow().clone();
            candidate.active_host = index;
            persist(&c, candidate)?;
            r();
            p.select_row(p.row_at_index(index as i32).as_ref());
            Ok(())
        })();
        status_result(&stat, result);
    });
    let pending = Rc::new(Cell::new(None));
    let (e, q, yes, no, stat) = (
        editing.clone(),
        pending.clone(),
        confirm.clone(),
        cancel.clone(),
        status.clone(),
    );
    remove.connect_clicked(move |_| {
        q.set(e.get());
        yes.set_visible(q.get().is_some());
        no.set_visible(q.get().is_some());
        stat.set_text(&tr("host-remove-prompt", &[]));
    });
    let (yes, no, q) = (confirm.clone(), cancel.clone(), pending.clone());
    cancel.connect_clicked(move |_| {
        q.set(None);
        yes.set_visible(false);
        no.set_visible(false);
    });
    let (c, stat, r, p, e, q, no) = (
        conf.clone(),
        status.clone(),
        refresh,
        profiles,
        editing,
        pending,
        cancel,
    );
    confirm.connect_clicked(move |yes| {
        let result = (|| -> anyhow::Result<()> {
            let index = q
                .take()
                .ok_or_else(|| anyhow::anyhow!(tr("host-no-confirmed-selection", &[])))?;
            anyhow::ensure!(
                e.get() == Some(index),
                "{}",
                tr("host-selection-changed", &[])
            );
            let mut candidate = c.borrow().clone();
            candidate.hosts.remove(index);
            candidate.active_host = if candidate.active_host == index {
                0
            } else if candidate.active_host > index {
                candidate.active_host - 1
            } else {
                candidate.active_host
            };
            persist(&c, candidate)?;
            e.set(None);
            r();
            p.select_row(p.row_at_index(c.borrow().active_host as i32).as_ref());
            Ok(())
        })();
        yes.set_visible(false);
        no.set_visible(false);
        status_result(&stat, result);
    });
    page.append(&crate::ssh_view::build(
        stack,
        conf,
        status,
        &identity_field,
        f,
    ));
    page
}
