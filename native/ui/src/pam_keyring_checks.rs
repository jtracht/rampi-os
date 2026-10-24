//! Exercise the production Secret Service adapter after actual graphical PAM login.
use anyhow::{Context, Result, ensure};
use gtk::glib;
use std::io::Read;

pub fn run() -> Result<()> {
    let designated = std::path::Path::new("/etc/rampi-acceptance-vm").is_file();
    let vm = std::process::Command::new("systemd-detect-virt")
        .args(["--vm", "--quiet"])
        .status()?
        .success();
    let image_vm = std::path::Path::new("/etc/rampi-image-acceptance-vm").is_file()
        && std::fs::read_to_string("/proc/cmdline")?.contains("rampi.image_acceptance=1");
    ensure!(
        designated && (vm || image_vm),
        "Designated QEMU guest required"
    );
    let mut input = Vec::new();
    std::io::stdin().take(16385).read_to_end(&mut input)?;
    ensure!(input.len() <= 16384, "Acceptance input too large");
    let request: serde_json::Value = serde_json::from_slice(&input)?;
    let mode = request["mode"]
        .as_str()
        .context("Acceptance mode missing")?;
    let profile = request["profile"]
        .as_str()
        .context("Acceptance profile missing")?;
    let token = request["token"]
        .as_str()
        .context("Acceptance token missing")?;
    ensure!(
        profile.starts_with("pam-acceptance-"),
        "Acceptance profile required"
    );
    crate::secret_service::validate_profile(profile)?;
    ensure!(
        !token.is_empty() && token.len() <= 8192,
        "Acceptance token required"
    );
    glib::MainContext::default().block_on(async {
        let source = "organization/fixture/1";
        if mode == "store" {
            crate::secret_service::store(profile, "github", source, "", token).await?;
        } else {
            ensure!(mode == "check", "Unknown acceptance mode");
        }
        let value = crate::secret_service::load(profile, "github", source).await?;
        ensure!(
            value == token,
            "Personal native Secret Service value mismatch"
        );
        println!("RAMPI_NATIVE_PAM_KEYRING_OK");
        Ok(())
    })
}
