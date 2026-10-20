use crate::config::{Host, expand_home};
use anyhow::{Result, ensure};
use base64::{Engine, engine::general_purpose::STANDARD};
use std::ffi::OsString;

pub const MODULES: [&str; 3] = ["codex", "claude", "antigravity"];
pub fn ps_literal(value: &str) -> String {
    format!("'{}'", value.replace('\'', "''"))
}
pub fn ssh(host: &Host, module: &str) -> Result<Vec<OsString>> {
    host.validate()?;
    ensure!(MODULES.contains(&module), "Unbekanntes KI-Modul");
    let script = format!(
        "$ErrorActionPreference='Stop'; $s=Join-Path $env:LOCALAPPDATA 'Rampi\\rampi-session.ps1'; & $s -Module {} -Project {}; exit $LASTEXITCODE",
        ps_literal(module),
        ps_literal(&host.project)
    );
    let encoded = STANDARD.encode(
        script
            .encode_utf16()
            .flat_map(u16::to_le_bytes)
            .collect::<Vec<u8>>(),
    );
    let mut args: Vec<OsString> = [
        "ssh",
        "-tt",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "ServerAliveInterval=15",
        "-o",
        "ServerAliveCountMax=3",
        "-o",
        "ConnectTimeout=8",
        "-p",
        &host.port.to_string(),
    ]
    .iter()
    .map(OsString::from)
    .collect();
    if !host.identity.is_empty() {
        args.push("-i".into());
        args.push(expand_home(&host.identity)?.into_os_string());
    }
    args.extend([
        OsString::from("-l"),
        host.username.clone().into(),
        host.address.clone().into(),
        "powershell.exe".into(),
        "-NoLogo".into(),
        "-NoProfile".into(),
        "-EncodedCommand".into(),
        encoded.into(),
    ]);
    Ok(args)
}
pub fn rdp(host: &Host) -> Result<Vec<OsString>> {
    host.validate()?;
    Ok([
        "wlfreerdp3".into(),
        format!("/v:{}", host.address).into(),
        format!("/u:{}", host.username).into(),
        "/f".into(),
        "/cert:tofu".into(),
        "/dynamic-resolution".into(),
        "/network:auto".into(),
    ]
    .to_vec())
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn projects_are_encoded_and_host_keys_remain_required() {
        let h = Host {
            address: "host.tailnet.ts.net".into(),
            username: "julia".into(),
            project: "C:\\Projects\\O'Brien".into(),
            ..Default::default()
        };
        let args = ssh(&h, "codex").unwrap();
        assert!(args.contains(&"StrictHostKeyChecking=yes".into()));
        assert!(!args.contains(&h.project.clone().into()));
        assert_eq!(ps_literal("O'Brien"), "'O''Brien'");
        assert!(ssh(&h, "invented-cli").is_err());
        assert!(rdp(&h).unwrap().contains(&"/cert:tofu".into()));
    }
}
