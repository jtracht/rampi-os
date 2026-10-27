//! Upload consent page backed by GTK's asynchronous directory/selection models.
use crate::widgets::*;
use gtk::{gio, prelude::*};
use rampi_core::i18n::text as tr;
use std::{cell::RefCell, rc::Rc};
use webkit6::prelude::*;

fn folder(directory: &gtk::DirectoryList, path: &gtk::Entry, file: &gio::File) {
    if let Some(local) = file.path() {
        path.set_text(&local.to_string_lossy());
        directory.set_file(Some(file));
    }
}

pub fn install(web: &webkit6::WebView, stack: &gtk::Stack, f: &Feedback) {
    let pending: Rc<RefCell<Option<webkit6::FileChooserRequest>>> = Rc::new(RefCell::new(None));
    let page = column();
    let title = label(&tr("upload-heading", &[]));
    title.add_css_class("heading");
    page.append(&title);
    let site = label("");
    page.append(&site);
    let location = row();
    let up = button(&tr("upload-up", &[]), f);
    let home = button(&tr("upload-home", &[]), f);
    location.append(&up);
    location.append(&home);
    page.append(&location);
    page.append(&label(&tr("upload-location", &[])));
    let path = gtk::Entry::builder()
        .placeholder_text(tr("upload-path", &[]))
        .hexpand(true)
        .build();
    path.set_widget_name("browser-upload-folder");
    page.append(&path);
    let state = label("");
    state.set_widget_name("browser-upload-status");
    let directory = gtk::DirectoryList::new(
        Some(
            "standard::name,standard::display-name,standard::type,standard::content-type,standard::is-hidden",
        ),
        None::<&gio::File>,
    );
    let mime: Rc<RefCell<Option<gtk::FileFilter>>> = Rc::new(RefCell::new(None));
    let all = gtk::CheckButton::with_label(&tr("upload-all-types", &[]));
    page.append(&all);
    let (types, show_all) = (mime.clone(), all.clone());
    let filter = gtk::CustomFilter::new(move |object| {
        let Some(info) = object.downcast_ref::<gio::FileInfo>() else {
            return false;
        };
        !info.is_hidden()
            && (info.file_type() == gio::FileType::Directory
                || show_all.is_active()
                || types
                    .borrow()
                    .as_ref()
                    .is_none_or(|filter| filter.match_(info)))
    });
    let filtered = gtk::FilterListModel::new(Some(directory.clone()), Some(filter.clone()));
    let sorter = gtk::CustomSorter::new(|left, right| {
        let a = left.downcast_ref::<gio::FileInfo>().unwrap();
        let b = right.downcast_ref::<gio::FileInfo>().unwrap();
        let order = (b.file_type() == gio::FileType::Directory)
            .cmp(&(a.file_type() == gio::FileType::Directory))
            .then_with(|| a.display_name().cmp(&b.display_name()));
        order.into()
    });
    let sorted = gtk::SortListModel::new(Some(filtered), Some(sorter));
    let selection = gtk::SingleSelection::new(Some(sorted.clone()));
    selection.set_autoselect(false);
    selection.set_can_unselect(true);
    let factory = gtk::SignalListItemFactory::new();
    factory.connect_setup(|_, item| {
        let item = item.downcast_ref::<gtk::ListItem>().unwrap();
        let content = row();
        content.set_margin_top(10);
        content.set_margin_bottom(10);
        content.append(&gtk::Image::new());
        content.append(&label(""));
        item.set_child(Some(&content));
    });
    factory.connect_bind(|_, item| {
        let item = item.downcast_ref::<gtk::ListItem>().unwrap();
        let info = item.item().and_downcast::<gio::FileInfo>().unwrap();
        let content = item.child().unwrap();
        content
            .first_child()
            .and_downcast::<gtk::Image>()
            .unwrap()
            .set_icon_name(Some(if info.file_type() == gio::FileType::Directory {
                "folder-symbolic"
            } else {
                "text-x-generic-symbolic"
            }));
        content
            .last_child()
            .and_downcast::<gtk::Label>()
            .unwrap()
            .set_text(&info.display_name());
    });
    let list = gtk::ListView::new(Some(selection), Some(factory));
    list.set_widget_name("browser-upload-files");
    list.add_css_class("upload-files");
    page.append(&scroll(&list));
    page.append(&state);
    let (dir, entry) = (directory.clone(), path.clone());
    list.connect_activate(move |list, position| {
        if let Some(info) = list
            .model()
            .and_then(|model| model.item(position))
            .and_downcast::<gio::FileInfo>()
            && info.file_type() == gio::FileType::Directory
            && let Some(current) = dir.file()
        {
            folder(&dir, &entry, &current.child(info.name()));
        }
    });
    let (dir, entry) = (directory.clone(), path.clone());
    up.connect_clicked(move |_| {
        if let Some(parent) = dir.file().and_then(|current| current.parent()) {
            folder(&dir, &entry, &parent);
        }
    });
    let (dir, entry) = (directory.clone(), path.clone());
    home.connect_clicked(move |_| {
        folder(&dir, &entry, &gio::File::for_path(gtk::glib::home_dir()))
    });
    let (dir, stat) = (directory.clone(), state.clone());
    path.connect_activate(move |entry| {
        let text = entry.text();
        if std::path::Path::new(text.as_str()).is_absolute() {
            folder(&dir, entry, &gio::File::for_path(text.as_str()));
        } else {
            stat.set_text(&tr("upload-absolute", &[]));
        }
    });
    let stat = state.clone();
    directory.connect_error_notify(move |dir| {
        if dir.error().is_some() {
            stat.set_text(&tr("upload-unreadable", &[]));
        }
    });
    let changed = filter.clone();
    all.connect_toggled(move |_| changed.changed(gtk::FilterChange::Different));
    let actions = row();
    let cancel = button(&tr("action-cancel", &[]), f);
    cancel.set_widget_name("rampi-back");
    let accept = button(&tr("upload-select", &[]), f);
    actions.append(&cancel);
    actions.append(&accept);
    page.append(&actions);
    let (active, back) = (pending.clone(), stack.clone());
    cancel.connect_clicked(move |_| {
        let request = active.borrow_mut().take();
        if let Some(request) = request {
            request.cancel();
        }
        back.set_visible_child_name("browser");
    });
    let (active, back, files, dir, stat) = (
        pending.clone(),
        stack.clone(),
        list.clone(),
        directory.clone(),
        state.clone(),
    );
    accept.connect_clicked(move |_| {
        if dir.is_loading() || dir.error().is_some() {
            stat.set_text(&tr("upload-wait", &[]));
            return;
        }
        let multiple = match active.borrow().as_ref() {
            Some(request) => request.selects_multiple(),
            None => return,
        };
        let Some(model) = files.model() else {
            return;
        };
        let positions: Vec<_> = (0..model.n_items())
            .filter(|i| model.is_selected(*i))
            .take(129)
            .collect();
        if positions.is_empty() || positions.len() > 128 || (!multiple && positions.len() != 1) {
            stat.set_text(&tr("upload-count", &[]));
            return;
        }
        let Some(current) = dir.file() else {
            return;
        };
        let count = positions.len();
        let selected: Vec<_> = positions
            .into_iter()
            .filter_map(|i| {
                model
                    .item(i)
                    .and_downcast::<gio::FileInfo>()
                    .and_then(|info| current.child(info.name()).path())
            })
            .collect();
        if selected.len() != count
            || selected.iter().any(|file| {
                !file.is_absolute()
                    || !file.is_file()
                    || std::fs::File::open(file).is_err()
                    || file.to_str().is_none()
            })
        {
            stat.set_text(&tr("upload-files", &[]));
            return;
        }
        let paths: Vec<_> = selected.iter().map(|file| file.to_str().unwrap()).collect();
        let request = active.borrow_mut().take();
        if let Some(request) = request {
            request.select_files(&paths);
        }
        back.set_visible_child_name("browser");
    });
    let active = pending.clone();
    page.connect_unmap(move |_| {
        let request = active.borrow_mut().take();
        if let Some(request) = request {
            request.cancel();
        }
    });
    stack.add_named(&page, Some("browser-upload"));
    let (active, weak) = (pending.clone(), stack.downgrade());
    web.connect_load_changed(move |_, event| {
        if event != webkit6::LoadEvent::Started {
            return;
        }
        let request = active.borrow_mut().take();
        if let Some(request) = request {
            request.cancel();
            if let Some(route) = weak.upgrade()
                && route.visible_child_name().as_deref() == Some("browser-upload")
            {
                route.set_visible_child_name("browser");
            }
        }
    });
    let route = stack.clone();
    web.connect_run_file_chooser(move |web, request| {
        let old = pending.borrow_mut().take();
        if let Some(old) = old {
            old.cancel();
        }
        if request.selects_multiple() {
            list.set_model(Some(&gtk::MultiSelection::new(Some(sorted.clone()))));
        } else {
            let selection = gtk::SingleSelection::new(Some(sorted.clone()));
            selection.set_autoselect(false);
            selection.set_can_unselect(true);
            selection.unselect_all();
            list.set_model(Some(&selection));
        }
        *mime.borrow_mut() = request.mime_types_filter();
        all.set_active(false);
        filter.changed(gtk::FilterChange::Different);
        folder(
            &directory,
            &path,
            &gio::File::for_path(gtk::glib::home_dir()),
        );
        site.set_text(&tr(
            "upload-origin",
            &[("site", web.uri().as_deref().unwrap_or("—"))],
        ));
        state.set_text(&tr("upload-instructions", &[]));
        *pending.borrow_mut() = Some(request.clone());
        route.set_visible_child_name("browser-upload");
        cancel.grab_focus();
        true
    });
}
