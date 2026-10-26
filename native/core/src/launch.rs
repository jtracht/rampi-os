use crate::config::{Host, config_dir};
use anyhow::Result;
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
}
