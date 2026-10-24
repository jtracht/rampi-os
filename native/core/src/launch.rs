use crate::config::{Host, config_dir, expand_home};
use anyhow::{Result, ensure};
use base64::{Engine, engine::general_purpose::STANDARD};
use sha2::{Digest, Sha256};
use std::ffi::OsString;

pub fn streaming_identity(host: &Host) -> Result<String> {
    host.validate()?;
    // Preserve the existing profile identity, including Python JSON spacing.
    // Host and username validation restrict these identity fields to ASCII.
    let identity = format!(
        "[{}, {}, {}]",
        serde_json::to_string(&host.address.to_ascii_lowercase())?,
        host.port,
        serde_json::to_string(&host.username.to_ascii_lowercase())?
    );
    Ok(Sha256::digest(identity.as_bytes())
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect())
}
pub fn streaming(host: &Host, pair: bool) -> Result<Vec<OsString>> {
    let profile = config_dir()?
        .join("streaming")
        .join(streaming_identity(host)?);
    std::fs::create_dir_all(&profile)?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        std::fs::set_permissions(&profile, std::fs::Permissions::from_mode(0o700))?;
    }
    let mut args: Vec<OsString> = vec![
        "moonlight".into(),
        if pair { "pair".into() } else { "stream".into() },
        "-keydir".into(),
        profile.into_os_string(),
    ];
    if !pair {
        let (w, h) = host.resolution.split_once('x').unwrap();
        args.extend(
            [
                "-platform",
                "sdl",
                "-width",
                w,
                "-height",
                h,
                "-fps",
                "30",
                "-bitrate",
                "5000",
                "-app",
                "Desktop",
            ]
            .iter()
            .map(OsString::from),
        );
    }
    args.push(host.address.clone().into());
    Ok(args)
}

pub const MODULES: [&str; 3] = ["codex", "claude", "antigravity"];
pub fn ps_literal(value: &str) -> String {
    format!("'{}'", value.replace('\'', "''"))
}
pub fn ssh(host: &Host, module: &str) -> Result<Vec<OsString>> {
    ssh_action(host, module, "Attach")
}
/// A fixed adapter action; never interpolate arbitrary commands from settings.
pub fn ssh_action(host: &Host, module: &str, action: &str) -> Result<Vec<OsString>> {
    host.validate()?;
    ensure!(MODULES.contains(&module), "Unbekanntes KI-Modul");
    ensure!(
        ["Attach", "Check", "Status", "Stop"].contains(&action),
        "Unbekannte Sitzungsaktion"
    );
    let script = format!(
        "$ErrorActionPreference='Stop'; $s=Join-Path $env:LOCALAPPDATA 'Rampi\\rampi-session.ps1'; & $s -Module {} -Project {} -Action {}; exit $LASTEXITCODE",
        ps_literal(module),
        ps_literal(&host.project),
        ps_literal(action)
    );
    let encoded = STANDARD.encode(
        script
            .encode_utf16()
            .flat_map(u16::to_le_bytes)
            .collect::<Vec<u8>>(),
    );
    let mut args: Vec<OsString> = [
        "ssh",
        if action == "Attach" { "-tt" } else { "-T" },
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
    if action != "Attach" {
        args.extend(["-o".into(), "BatchMode=yes".into()]);
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
    fn streaming_credentials_are_bound_to_windows_account() {
        let first = Host {
            address: "Host.Example".into(),
            username: "julia".into(),
            ..Default::default()
        };
        assert_eq!(
            streaming_identity(&first).unwrap(),
            "c8d855b8451b6e98fd494d80f3f894664f4d0931dd9ce6e14a152543aa63d70a", // pragma: allowlist secret - public profile compatibility digest
        );
        let mut other = first.clone();
        other.username = "other".into();
        assert_ne!(
            streaming_identity(&first).unwrap(),
            streaming_identity(&other).unwrap()
        );
        let mut same = first.clone();
        same.address = "host.example".into();
        same.username = "JULIA".into();
        assert_eq!(
            streaming_identity(&first).unwrap(),
            streaming_identity(&same).unwrap()
        );
    }
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
    #[test]
    fn session_controls_cannot_inject_actions_or_prompt_in_background() {
        let host = Host {
            address: "windows.example".into(),
            username: "alice".into(),
            project: "C:\\Work\\O'Brien;$value".into(),
            ..Default::default()
        };
        for action in ["Check", "Status", "Stop"] {
            let args = ssh_action(&host, "antigravity", action).unwrap();
            assert!(args.contains(&"-T".into()));
            assert!(args.contains(&"BatchMode=yes".into()));
            assert!(args.contains(&"StrictHostKeyChecking=yes".into()));
            let bytes = STANDARD
                .decode(args.last().unwrap().to_str().unwrap())
                .unwrap();
            let words: Vec<u16> = bytes
                .as_chunks::<2>()
                .0
                .iter()
                .map(|p| u16::from_le_bytes([p[0], p[1]]))
                .collect();
            let script = String::from_utf16(&words).unwrap();
            assert!(script.contains(&format!("-Action '{action}'")));
            assert!(script.contains("-Project 'C:\\Work\\O''Brien;$value'"));
        }
        assert!(ssh_action(&host, "codex", "Stop; whoami").is_err());
        assert!(ssh_action(&host, "invented", "Check").is_err());
    }
}
