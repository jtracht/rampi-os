//! BlueZ's application-specific Agent1; never replaces the system default agent.
use crate::{bus, widgets::*};
use glib::variant::ToVariant;
use gtk::{gio, glib, prelude::*};
use rampi_core::i18n::text as tr;
use std::{
    cell::{Cell, RefCell},
    rc::Rc,
};
const PATH: &str = "/org/rampi/PairingAgent";
const XML: &str = r#"<node><interface name="org.bluez.Agent1">
<method name="Release"/><method name="Cancel"/>
<method name="RequestPinCode"><arg type="o" direction="in"/><arg type="s" direction="out"/></method>
<method name="RequestPasskey"><arg type="o" direction="in"/><arg type="u" direction="out"/></method>
<method name="DisplayPinCode"><arg type="o" direction="in"/><arg type="s" direction="in"/></method>
<method name="DisplayPasskey"><arg type="o" direction="in"/><arg type="u" direction="in"/><arg type="q" direction="in"/></method>
<method name="RequestConfirmation"><arg type="o" direction="in"/><arg type="u" direction="in"/></method>
<method name="RequestAuthorization"><arg type="o" direction="in"/></method>
<method name="AuthorizeService"><arg type="o" direction="in"/><arg type="s" direction="in"/></method>
</interface></node>"#;
struct Pending {
    invocation: Option<gio::DBusMethodInvocation>,
    id: u64,
    device: String,
    previous: String,
}
pub struct Agent {
    bus: gio::DBusConnection,
    registration: Option<gio::RegistrationId>,
    subscription: Option<gio::SignalSubscription>,
    pending: Rc<RefCell<Option<Pending>>>,
}
impl Drop for Agent {
    fn drop(&mut self) {
        if let Some(p) = self.pending.borrow_mut().take()
            && let Some(i) = p.invocation
        {
            i.return_dbus_error("org.bluez.Error.Canceled", "Rampi session ended");
        }
        self.subscription.take();
        if let Some(id) = self.registration.take() {
            let _ = self.bus.unregister_object(id);
        }
    }
}
fn finish(
    pending: &Rc<RefCell<Option<Pending>>>,
    stack: &gtk::Stack,
    id: u64,
    answer: Option<glib::Variant>,
    cancel_display: bool,
) {
    if !pending.borrow().as_ref().is_some_and(|p| p.id == id) {
        return;
    }
    let p = pending.borrow_mut().take().unwrap();
    if let Some(page) = stack.child_by_name("pairing") {
        let mut child = page.first_child();
        while let Some(widget) = child {
            if let Ok(input) = widget.clone().downcast::<gtk::PasswordEntry>() {
                input.set_text("");
            }
            child = widget.next_sibling();
        }
    }
    if let Some(invocation) = p.invocation {
        if let Some(answer) = answer {
            invocation.return_value(Some(&answer));
        } else {
            invocation.return_dbus_error("org.bluez.Error.Rejected", "User rejected pairing");
        }
    } else if answer.is_none() && cancel_display {
        let device = p.device.clone();
        glib::MainContext::default().spawn_local(async move {
            let _ = bus::bluetooth_action("cancel-pair", &device, false).await;
        });
    }
    if stack.visible_child_name().is_some_and(|n| n == "pairing") {
        stack.set_visible_child_name(&p.previous);
    }
}
async fn register_owner(
    bus: gio::DBusConnection,
    owner: Rc<RefCell<String>>,
    target: String,
    status: gtk::Label,
) {
    // A newly owned bus name can appear before AgentManager1 is exported.
    // Retry that startup gap, pinned to the same unique service identity.
    for attempt in 0..5 {
        if *owner.borrow() != target {
            return;
        }
        if bus::call(
            &bus,
            &target,
            "/org/bluez",
            "org.bluez.AgentManager1",
            "RegisterAgent",
            Some(&(bus::path(PATH).unwrap(), "KeyboardDisplay").to_variant()),
        )
        .await
        .is_ok()
        {
            return;
        }
        glib::timeout_future(std::time::Duration::from_millis(100 * (1 << attempt))).await;
    }
    if *owner.borrow() == target {
        status.set_text(&tr("pairing-agent-error", &[]));
    }
}
pub async fn register(stack: gtk::Stack, status: gtk::Label, f: Feedback) -> anyhow::Result<Agent> {
    let bus = bus::system().await?;
    let node = gio::DBusNodeInfo::for_xml(XML)?;
    let info = node.lookup_interface("org.bluez.Agent1").unwrap();
    let owner = Rc::new(RefCell::new(String::new()));
    let pending: Rc<RefCell<Option<Pending>>> = Rc::new(RefCell::new(None));
    let serial = Rc::new(Cell::new(0u64));
    let (o, p, s, st, feed, seq) = (
        owner.clone(),
        pending.clone(),
        stack.clone(),
        status.clone(),
        f.clone(),
        serial,
    );
    let registration = bus
        .register_object(PATH, &info)
        .method_call(move |_, sender, _, _, method, parameters, invocation| {
            if sender != Some(o.borrow().as_str()) || o.borrow().is_empty() {
                invocation.return_dbus_error(
                    "org.freedesktop.DBus.Error.AccessDenied",
                    "Only bluetoothd may request pairing",
                );
                return;
            }
            if method == "Cancel" || method == "Release" {
                let id = p.borrow().as_ref().map(|p| p.id);
                if let Some(id) = id {
                    finish(&p, &s, id, None, false);
                }
                invocation.return_value(None);
                return;
            }
            let kind = method.to_string();
            let display = kind.starts_with("Display");
            if p.borrow().is_some() {
                if display {
                    let id = p.borrow().as_ref().unwrap().id;
                    finish(&p, &s, id, Some(().to_variant()), false);
                } else {
                    invocation.return_dbus_error(
                        "org.bluez.Error.Rejected",
                        "A pairing request is already pending",
                    );
                    return;
                }
            }
            let device = parameters.child_value(0).str().unwrap_or("").to_string();
            if !device.starts_with("/org/bluez/hci") || !device.contains("/dev_") {
                invocation.return_dbus_error("org.bluez.Error.Rejected", "Invalid device path");
                return;
            }
            let code = if ["DisplayPasskey", "RequestConfirmation"].contains(&method) {
                format!("{:06}", parameters.child_value(1).get::<u32>().unwrap_or(0))
            } else if method == "DisplayPinCode" {
                parameters.child_value(1).str().unwrap_or("").to_string()
            } else {
                String::new()
            };
            if s.child_by_name("pairing").is_some() {
                let old = s.child_by_name("pairing").unwrap();
                s.remove(&old);
            }
            let previous = s
                .visible_child_name()
                .map(|v| v.to_string())
                .unwrap_or_else(|| "dashboard".into());
            let id = seq.get() + 1;
            seq.set(id);
            let invocation = if display {
                invocation.return_value(None);
                None
            } else {
                Some(invocation)
            };
            *p.borrow_mut() = Some(Pending {
                invocation,
                id,
                device: device.clone(),
                previous,
            });
            let page = column();
            let title = label(&tr("pairing-heading", &[]));
            title.add_css_class("heading");
            page.append(&title);
            page.append(&label(&device));
            page.append(&label(&tr(
                if display {
                    "pairing-type-code"
                } else if kind == "RequestConfirmation" {
                    "pairing-compare"
                } else {
                    "pairing-review"
                },
                &[],
            )));
            let digits = label(&code);
            digits.set_widget_name("pairing-code");
            digits.add_css_class("brand");
            page.append(&digits);
            if method == "DisplayPasskey" {
                let entered = parameters.child_value(2).get::<u16>().unwrap_or(0).min(6);
                let progress = label(&tr("pairing-entered", &[("count", &entered.to_string())]));
                progress.set_widget_name("pairing-entered");
                page.append(&progress);
            }
            if method == "AuthorizeService" {
                page.append(&label(&tr(
                    "pairing-service",
                    &[("service", parameters.child_value(1).str().unwrap_or("?"))],
                )));
            }
            let input = gtk::PasswordEntry::builder()
                .placeholder_text(tr("pairing-pin", &[]))
                .build();
            let needs_input = kind == "RequestPinCode" || kind == "RequestPasskey";
            input.set_widget_name("pairing-input");
            input.set_visible(needs_input);
            page.append(&input);
            let reviewed = gtk::CheckButton::with_label(&tr("pairing-reviewed", &[]));
            reviewed.set_visible(!display && !needs_input);
            reviewed.set_widget_name("pairing-reviewed");
            page.append(&reviewed);
            let reject = button(&tr("action-cancel", &[]), &feed);
            reject.set_widget_name("rampi-back");
            let accept = button(&tr("action-accept", &[]), &feed);
            accept.set_visible(!display);
            page.append(&reject);
            page.append(&accept);
            let (p1, s1) = (p.clone(), s.clone());
            reject.connect_clicked(move |_| finish(&p1, &s1, id, None, true));
            let (p1, s1, stat) = (p.clone(), s.clone(), st.clone());
            accept.connect_clicked(move |_| {
                let value = input.text().to_string();
                let answer = match kind.as_str() {
                    "RequestPinCode"
                        if !value.is_empty()
                            && value.len() <= 16
                            && value.bytes().all(|c| c.is_ascii_alphanumeric()) =>
                    {
                        Some((value,).to_variant())
                    }
                    "RequestPasskey"
                        if !value.is_empty()
                            && value.len() <= 6
                            && value.bytes().all(|c| c.is_ascii_digit()) =>
                    {
                        value.parse::<u32>().ok().map(|n| (n,).to_variant())
                    }
                    "RequestConfirmation" | "RequestAuthorization" | "AuthorizeService"
                        if reviewed.is_active() =>
                    {
                        Some(().to_variant())
                    }
                    _ => None,
                };
                if answer.is_some() {
                    input.set_text("");
                    finish(&p1, &s1, id, answer, false);
                } else {
                    stat.set_text(&tr("pairing-input-needed", &[]));
                }
            });
            s.add_named(&page, Some("pairing"));
            s.set_visible_child_name("pairing");
            reject.grab_focus();
            let (p1, s1) = (p.clone(), s.clone());
            glib::timeout_add_local_once(std::time::Duration::from_secs(60), move || {
                finish(&p1, &s1, id, None, true)
            });
        })
        .build()?;
    let initial_owner = owner.clone();
    let initial_status = status.clone();
    let (o, p, s, stat) = (owner, pending.clone(), stack, status);
    let subscription = bus.subscribe_to_signal(
        Some("org.freedesktop.DBus"),
        Some("org.freedesktop.DBus"),
        Some("NameOwnerChanged"),
        Some("/org/freedesktop/DBus"),
        Some("org.bluez"),
        gio::DBusSignalFlags::NONE,
        move |signal| {
            let bus = signal.connection;
            let args = signal.parameters;
            let new = args.child_value(2).str().unwrap_or("").to_string();
            *o.borrow_mut() = new.clone();
            let id = p.borrow().as_ref().map(|p| p.id);
            if let Some(id) = id {
                finish(&p, &s, id, None, false);
            }
            if !new.is_empty() {
                glib::MainContext::default().spawn_local(register_owner(
                    bus.clone(),
                    o.clone(),
                    new,
                    stat.clone(),
                ));
            }
        },
    );
    // Retain the exported object even if BlueZ starts later; the owner watcher
    // registers this same application agent when the daemon appears.
    let agent = Agent {
        bus: bus.clone(),
        registration: Some(registration),
        subscription: Some(subscription),
        pending,
    };
    if let Ok(get) = bus::call(
        &bus,
        "org.freedesktop.DBus",
        "/org/freedesktop/DBus",
        "org.freedesktop.DBus",
        "GetNameOwner",
        Some(&("org.bluez",).to_variant()),
    )
    .await
        && initial_owner.borrow().is_empty()
    {
        let target = get.child_value(0).str().unwrap_or("").to_string();
        *initial_owner.borrow_mut() = target.clone();
        register_owner(bus, initial_owner, target, initial_status).await;
    }
    Ok(agent)
}
