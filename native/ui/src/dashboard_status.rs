//! Read authoritative service state without discovery, connection changes or authentication.
use crate::{bus, widgets::Shared};
use gtk::{gio, glib, prelude::*};
use std::{cell::Cell, rc::Rc, time::Duration};

fn text(button: &gtk::Button, value: &str) {
    if let Some(content) = button.child() {
        let mut next = content.first_child();
        while let Some(child) = next {
            if let Ok(label) = child.clone().downcast::<gtk::Label>() {
                label.set_text(value);
            }
            next = child.next_sibling();
        }
    }
}
async fn network() -> (String, Option<bool>) {
    let result: anyhow::Result<(String, bool)> = async {
        let connection = bus::system().await?;
        let props = bus::properties(&connection, bus::NM, bus::ROOT, bus::NM).await?;
        let radio = props.get("WirelessEnabled").and_then(|v| v.get::<bool>());
        let active = props
            .get("ActiveConnections")
            .and_then(|v| v.get::<Vec<glib::variant::ObjectPath>>())
            .unwrap_or_default();
        let (mut wifi, mut vpn) = (false, false);
        for path in active.iter().take(64) {
            if let Ok(props) = bus::properties(
                &connection,
                bus::NM,
                path,
                "org.freedesktop.NetworkManager.Connection.Active",
            )
            .await
                && props.get("State").and_then(|v| v.get::<u32>()) == Some(2)
            {
                wifi |= bus::text(&props, "Type") == "802-11-wireless";
                vpn |= ["wireguard", "vpn"].contains(&bus::text(&props, "Type").as_str());
            }
        }
        Ok((
            if wifi {
                "WLAN · verbunden"
            } else if radio == Some(false) {
                "WLAN · aus"
            } else if radio == Some(true) {
                "WLAN · bereit"
            } else {
                "WLAN · ungeprüft"
            }
            .into(),
            vpn,
        ))
    }
    .await;
    result
        .map(|(wifi, vpn)| (wifi, Some(vpn)))
        .unwrap_or(("WLAN · nicht verfügbar".into(), None))
}
async fn bluetooth() -> String {
    match bus::bluetooth_snapshot().await {
        Ok((adapters, devices)) => {
            let connected = devices.iter().filter(|d| d.connected).count();
            if connected > 0 {
                format!("Bluetooth · {connected} verbunden")
            } else if adapters.is_empty() {
                "Bluetooth · kein Adapter".into()
            } else if adapters.iter().any(|a| a.powered) {
                "Bluetooth · bereit".into()
            } else {
                "Bluetooth · aus".into()
            }
        }
        Err(_) => "Bluetooth · nicht verfügbar".into(),
    }
}

pub fn install(
    page: &gtk::Box,
    conf: &Shared,
    wifi: &gtk::Button,
    bt: &gtk::Button,
    vpn: &gtk::Button,
    clock: &gtk::Label,
    previews: &[gtk::Label],
) {
    if let Ok(now) = glib::DateTime::now_local() {
        clock.set_text(now.format("%H:%M").as_deref().unwrap_or(""));
    }
    let weak = clock.downgrade();
    glib::timeout_add_seconds_local(1, move || {
        let Some(clock) = weak.upgrade() else {
            return glib::ControlFlow::Break;
        };
        if let Ok(now) = glib::DateTime::now_local() {
            clock.set_text(now.format("%H:%M").as_deref().unwrap_or(""));
            clock.set_tooltip_text(now.format("%d.%m.%Y").ok().as_deref());
        }
        glib::ControlFlow::Continue
    });
    let busy = Rc::new(Cell::new(false));
    let (page, c, w, b, v, labels) = (
        page.downgrade(),
        conf.clone(),
        wifi.downgrade(),
        bt.downgrade(),
        vpn.downgrade(),
        previews.iter().map(|l| l.downgrade()).collect::<Vec<_>>(),
    );
    let refresh_page = page.clone();
    let refresh: Rc<dyn Fn()> = Rc::new(move || {
        let settings = c.borrow().clone();
        let host_label = settings
            .host()
            .map(|h| {
                format!(
                    "{} · {}@{}\nSSH-Port wird geprüft",
                    h.name, h.username, h.address
                )
            })
            .unwrap_or_else(|_| "Windows-Host noch nicht eingerichtet".into());
        for (index, label) in labels.iter().enumerate() {
            if let Some(label) = label.upgrade() {
                label.set_text(if index == 1 {
                    &settings.browser_url
                } else {
                    &host_label
                });
            }
        }
        if busy.replace(true) {
            return;
        }
        let (page, c, w, b, v, labels, busy) = (
            refresh_page.clone(),
            c.clone(),
            w.clone(),
            b.clone(),
            v.clone(),
            labels.clone(),
            busy.clone(),
        );
        glib::MainContext::default().spawn_local(async move {
            let (wifi, wireguard) = glib::future_with_timeout(Duration::from_secs(3), network())
                .await
                .unwrap_or(("WLAN · ungeprüft".into(), None));
            let bluetooth = glib::future_with_timeout(Duration::from_secs(3), bluetooth())
                .await
                .unwrap_or_else(|_| "Bluetooth · ungeprüft".into());
            let tailscale = if glib::find_program_in_path("tailscale").is_some() {
                match crate::process::output(
                    "tailscale",
                    &["status".into(), "--json".into(), "--peers=false".into()],
                    5,
                    262144,
                )
                .await
                {
                    Ok((true, bytes)) => rampi_core::tailscale::Status::parse(&bytes)
                        .ok()
                        .map(|s| s.connected()),
                    _ => None,
                }
            } else {
                Some(false)
            };
            let vpn = if wireguard == Some(true) {
                "VPN · aktiv (System)"
            } else if tailscale == Some(true) {
                "VPN · Tailscale aktiv"
            } else if wireguard.is_some() && tailscale.is_some() {
                "VPN · getrennt"
            } else {
                "VPN · ungeprüft"
            };
            let host = if let Ok(host) = settings.host() {
                let client = gio::SocketClient::new();
                client.set_timeout(2);
                client.set_enable_proxy(false);
                let reachable = glib::future_with_timeout(
                    Duration::from_secs(3),
                    client.connect_to_host_future(&host.address, host.port),
                )
                .await;
                let connected = matches!(&reachable, Ok(Ok(_)));
                if let Ok(Ok(socket)) = reachable {
                    let _ = socket.close_future(glib::Priority::DEFAULT).await;
                }
                format!(
                    "{} · {}@{}\nSSH-Port {} · Anmeldung ungeprüft",
                    host.name,
                    host.username,
                    host.address,
                    if connected {
                        "erreichbar"
                    } else {
                        "nicht erreichbar"
                    }
                )
            } else {
                "Windows-Host noch nicht eingerichtet".into()
            };
            // Ignore replies for a profile that changed while the check was running.
            let same_host = c
                .borrow()
                .hosts
                .get(c.borrow().active_host)
                .map(|h| (&h.address, h.port, &h.username))
                .map(|(a, p, u)| (a.clone(), p, u.clone()))
                == settings
                    .hosts
                    .get(settings.active_host)
                    .map(|h| (h.address.clone(), h.port, h.username.clone()));
            if page.upgrade().is_some_and(|p| p.is_mapped()) && same_host {
                if let Some(w) = w.upgrade() {
                    text(&w, &wifi);
                }
                if let Some(b) = b.upgrade() {
                    text(&b, &bluetooth);
                }
                if let Some(v) = v.upgrade() {
                    v.set_label(vpn);
                }
                for (index, label) in labels.iter().enumerate() {
                    if let Some(label) = label.upgrade() {
                        label.set_text(if index == 1 {
                            &settings.browser_url
                        } else {
                            &host
                        });
                    }
                }
            }
            busy.set(false);
        });
    });
    let on_map = refresh.clone();
    if let Some(page) = page.upgrade() {
        page.connect_map(move |_| on_map());
    }
    let page = page.clone();
    glib::timeout_add_seconds_local(10, move || {
        let Some(page) = page.upgrade() else {
            return glib::ControlFlow::Break;
        };
        if page.is_mapped() {
            refresh();
        }
        glib::ControlFlow::Continue
    });
}
