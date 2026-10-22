//! Asynchronous, bounded read-only invocation of the installed official CLI.
use anyhow::{Context, Result, ensure};
use gtk::{gio, glib, prelude::*};
use std::{cell::Cell, ffi::OsStr, rc::Rc, time::Duration};

pub async fn status() -> Result<String> {
    let Some(program) = glib::find_program_in_path("tailscale") else {
        return Ok("Tailscale ist nicht installiert. Die offizielle Software muss zuerst eingerichtet werden.".into());
    };
    let process = gio::Subprocess::newv(
        &[
            program.as_os_str(),
            OsStr::new("status"),
            OsStr::new("--json"),
            OsStr::new("--peers=false"),
        ],
        gio::SubprocessFlags::STDOUT_PIPE | gio::SubprocessFlags::STDERR_SILENCE,
    )
    .context("Tailscale konnte nicht gestartet werden.")?;
    let expired = Rc::new(Cell::new(false));
    let (flag, child) = (expired.clone(), process.downgrade());
    let timer = glib::timeout_add_local_once(Duration::from_secs(5), move || {
        flag.set(true);
        if let Some(child) = child.upgrade() {
            child.force_exit();
        }
    });
    let read: Result<Vec<u8>> = async {
        let stream = process.stdout_pipe().context("Tailscale-Ausgabe fehlt.")?;
        let mut bytes = vec![];
        loop {
            let chunk = stream
                .read_bytes_future(8192, glib::Priority::DEFAULT)
                .await
                .map_err(|_| anyhow::anyhow!("Tailscale-Antwort konnte nicht gelesen werden."))?;
            if chunk.is_empty() {
                break;
            }
            ensure!(
                bytes.len() + chunk.len() <= 262_144,
                "Tailscale-Antwort ist zu groß."
            );
            bytes.extend_from_slice(&chunk);
        }
        Ok(bytes)
    }
    .await;
    if read.is_err() {
        process.force_exit();
    }
    let waited = process.wait_future().await;
    if !expired.get() {
        timer.remove();
    }
    ensure!(
        !expired.get(),
        "Tailscale antwortet nicht. Dienststatus in der Diagnose prüfen."
    );
    waited.map_err(|_| anyhow::anyhow!("Tailscale-Prozess konnte nicht abgeschlossen werden."))?;
    let bytes = read?;
    ensure!(
        process.is_successful(),
        "Tailscale-Dienst nicht erreichbar oder Zugriff verweigert. Dienst und Berechtigungen prüfen."
    );
    Ok(rampi_core::tailscale::Status::parse(&bytes)?.description())
}

pub fn view(feedback: &crate::widgets::Feedback) -> gtk::Box {
    let page = crate::widgets::column();
    let output = crate::widgets::label("Tailscale-Status wird beim Öffnen geladen.");
    output.set_widget_name("tailscale-status");
    page.append(&output);
    let refresh = crate::widgets::button("Tailscale-Status aktualisieren", feedback);
    let weak_output = output.downgrade();
    refresh.connect_clicked(move |button| {
        if !button.is_sensitive() {
            return;
        }
        button.set_sensitive(false);
        let (button, output) = (button.clone(), weak_output.clone());
        glib::MainContext::default().spawn_local(async move {
            let result = status().await;
            if let Some(output) = output.upgrade() {
                output.set_text(&result.unwrap_or_else(|e| e.to_string()));
            }
            button.set_sensitive(true);
        });
    });
    page.append(&refresh);
    let weak = refresh.downgrade();
    page.connect_map(move |_| {
        if let Some(refresh) = weak.upgrade() {
            refresh.emit_clicked();
        }
    });
    let (weak_page, weak_refresh) = (page.downgrade(), refresh.downgrade());
    glib::timeout_add_seconds_local(5, move || {
        let (Some(page), Some(refresh)) = (weak_page.upgrade(), weak_refresh.upgrade()) else {
            return glib::ControlFlow::Break;
        };
        if page.is_mapped() && refresh.is_sensitive() {
            refresh.emit_clicked();
        }
        glib::ControlFlow::Continue
    });
    page
}
