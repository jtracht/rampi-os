//! Arguments for existing distribution tools; no Rampi account database.
use anyhow::{Result, ensure};
use std::ffi::OsString;

pub fn validate_name(name: &str) -> Result<()> {
    let bytes = name.as_bytes();
    ensure!(
        !bytes.is_empty()
            && bytes.len() <= 32
            && (bytes[0].is_ascii_lowercase() || bytes[0] == b'_')
            && bytes
                .iter()
                .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || b"_-".contains(c)),
        "Benutzername: 1–32 Kleinbuchstaben, Ziffern, _ oder -; mit Buchstabe oder _ beginnen."
    );
    ensure!(
        !["root", "nobody"].contains(&name),
        "Reservierter Systemname"
    );
    Ok(())
}
pub fn create(name: &str) -> Result<Vec<OsString>> {
    validate_name(name)?;
    Ok([
        "/usr/bin/sudo",
        "--",
        "/usr/sbin/useradd",
        "--create-home",
        "--user-group",
        "--shell",
        "/bin/bash",
        "--key",
        "UMASK=077",
        "--",
        name,
    ]
    .map(OsString::from)
    .to_vec())
}
pub fn password(name: &str) -> Result<Vec<OsString>> {
    validate_name(name)?;
    Ok(["/usr/bin/sudo", "--", "/usr/bin/passwd", "--", name]
        .map(OsString::from)
        .to_vec())
}
/// Existing sudo/PAM and the official CLI retain authority; no root Rampi broker.
pub fn tailscale_operator(name: &str) -> Result<Vec<OsString>> {
    validate_name(name)?;
    Ok(vec![
        "/usr/bin/sudo".into(),
        "--".into(),
        "tailscale".into(),
        "set".into(),
        format!("--operator={name}").into(),
    ])
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn only_literal_names_reach_account_tools() {
        for name in [
            "",
            "root",
            "nobody",
            "-admin",
            "../alice",
            "a b",
            "A",
            "a;id",
            "a\nroot",
            "älice",
            "a$()",
            &"a".repeat(33),
        ] {
            assert!(create(name).is_err(), "Accepted {name:?}");
            assert!(password(name).is_err());
            assert!(tailscale_operator(name).is_err());
        }
        assert_eq!(create("alice-2").unwrap().last().unwrap(), "alice-2");
        assert!(create("alice").unwrap().contains(&"UMASK=077".into()));
        assert_eq!(
            password("alice").unwrap(),
            ["/usr/bin/sudo", "--", "/usr/bin/passwd", "--", "alice"].map(OsString::from)
        );
        assert_eq!(
            tailscale_operator("alice-2").unwrap(),
            [
                "/usr/bin/sudo",
                "--",
                "tailscale",
                "set",
                "--operator=alice-2",
            ]
            .map(OsString::from)
        );
    }
}
