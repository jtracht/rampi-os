//! Bounded asynchronous calls to existing command-line tools through GIO.
use anyhow::{Context, Result, ensure};
use gtk::{gio, glib, prelude::*};
use std::{cell::Cell, ffi::OsString, rc::Rc, time::Duration};

pub async fn output(
    program: &str,
    arguments: &[OsString],
    seconds: u64,
    limit: usize,
) -> Result<(bool, Vec<u8>)> {
    let program = glib::find_program_in_path(program).context("Benötigtes Systemprogramm fehlt")?;
    let mut argv = vec![program.as_os_str()];
    argv.extend(arguments.iter().map(|a| a.as_os_str()));
    let child = gio::Subprocess::newv(
        &argv,
        gio::SubprocessFlags::STDOUT_PIPE | gio::SubprocessFlags::STDERR_SILENCE,
    )
    .context("Systemprogramm konnte nicht gestartet werden")?;
    let expired = Rc::new(Cell::new(false));
    let (flag, process) = (expired.clone(), child.downgrade());
    let timer = glib::timeout_add_local_once(Duration::from_secs(seconds), move || {
        flag.set(true);
        if let Some(process) = process.upgrade() {
            process.force_exit();
        }
    });
    let read: Result<Vec<u8>> = async {
        let stream = child.stdout_pipe().context("Programmausgabe fehlt")?;
        let mut bytes = vec![];
        loop {
            let chunk = stream
                .read_bytes_future(8192, glib::Priority::DEFAULT)
                .await?;
            if chunk.is_empty() {
                break;
            }
            ensure!(
                bytes.len() + chunk.len() <= limit,
                "Programmausgabe ist zu groß"
            );
            bytes.extend_from_slice(&chunk);
        }
        Ok(bytes)
    }
    .await;
    if read.is_err() {
        child.force_exit();
    }
    let waited = child.wait_future().await;
    if !expired.get() {
        timer.remove();
    }
    ensure!(
        !expired.get(),
        "Systemprogramm hat nicht rechtzeitig geantwortet"
    );
    waited.context("Systemprogramm konnte nicht beendet werden")?;
    Ok((child.is_successful(), read?))
}
