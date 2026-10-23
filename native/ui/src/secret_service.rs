//! Standard Secret Service on the personal session bus. Never invokes Prompt.
use anyhow::{Context, Result, ensure};
use glib::variant::{ObjectPath, ToVariant};
use gtk::{gio, glib};
use std::collections::HashMap;
const NAME: &str = "org.freedesktop.secrets";
const ROOT: &str = "/org/freedesktop/secrets";
const SERVICE: &str = "org.freedesktop.Secret.Service";
type Secret = (ObjectPath, Vec<u8>, Vec<u8>, String);
pub fn validate_profile(profile: &str) -> Result<()> {
    ensure!(
        !profile.is_empty()
            && profile.len() <= 64
            && profile
                .bytes()
                .all(|b| b.is_ascii_alphanumeric() || b"_.-".contains(&b)),
        "Schlüsselbund-Profil: 1–64 Buchstaben, Ziffern, _, . oder -"
    );
    Ok(())
}
async fn call(
    bus: &gio::DBusConnection,
    path: &str,
    interface: &str,
    method: &str,
    args: &glib::Variant,
) -> Result<glib::Variant> {
    bus.call_future(
        Some(NAME),
        path,
        interface,
        method,
        Some(args),
        None,
        gio::DBusCallFlags::NONE,
        5000,
    )
    .await
    .map_err(|_| anyhow::anyhow!("Persönlicher Schlüsselbund nicht verfügbar oder gesperrt"))
}
async fn session(bus: &gio::DBusConnection) -> Result<ObjectPath> {
    call(
        bus,
        ROOT,
        SERVICE,
        "OpenSession",
        &("plain", "".to_variant()).to_variant(),
    )
    .await?
    .child_value(1)
    .get()
    .context("Schlüsselbund-Sitzung fehlt")
}
async fn close(bus: &gio::DBusConnection, path: &ObjectPath) {
    let _ = call(
        bus,
        path,
        "org.freedesktop.Secret.Session",
        "Close",
        &().to_variant(),
    )
    .await;
}
fn attributes(profile: &str, kind: &str, source: &str) -> HashMap<String, String> {
    HashMap::from([
        ("application".into(), "rampi".into()),
        ("profile".into(), profile.into()),
        ("provider".into(), kind.into()),
        ("source".into(), source.into()),
    ])
}
pub async fn load(profile: &str, kind: &str, source: &str) -> Result<String> {
    validate_profile(profile)?;
    rampi_core::connectors::Connector::new(kind, source, "source-validation".into())?;
    let bus = gio::bus_get_future(gio::BusType::Session).await?;
    let found = call(
        &bus,
        ROOT,
        SERVICE,
        "SearchItems",
        &(attributes(profile, kind, source),).to_variant(),
    )
    .await?;
    let unlocked: Vec<ObjectPath> = found
        .child_value(0)
        .get()
        .context("Ungültige Schlüsselbundantwort")?;
    let locked: Vec<ObjectPath> = found
        .child_value(1)
        .get()
        .context("Ungültige Schlüsselbundantwort")?;
    ensure!(
        locked.is_empty(),
        "Schlüsselbund ist gesperrt. Mit der normalen PAM-Sitzung entsperren; Rampi öffnet keinen externen Dialog."
    );
    ensure!(
        unlocked.len() == 1,
        "Schlüsselbund-Profil fehlt oder ist mehrdeutig"
    );
    let session = session(&bus).await?;
    let result = async {
        let values: HashMap<ObjectPath, Secret> = call(
            &bus,
            ROOT,
            SERVICE,
            "GetSecrets",
            &(unlocked.clone(), session.clone()).to_variant(),
        )
        .await?
        .child_value(0)
        .get()
        .context("Ungültige Schlüsselbundantwort")?;
        let (returned, parameters, value, _) =
            values.get(&unlocked[0]).context("Zugriffstoken fehlt")?;
        ensure!(
            returned == &session
                && parameters.is_empty()
                && !value.is_empty()
                && value.len() <= 16384,
            "Ungültiger Schlüsselbundinhalt"
        );
        String::from_utf8(value.clone()).context("Schlüsselbundinhalt ist kein Text")
    }
    .await;
    close(&bus, &session).await;
    result
}
pub async fn store(
    profile: &str,
    kind: &str,
    source: &str,
    account: &str,
    token: &str,
) -> Result<()> {
    validate_profile(profile)?;
    rampi_core::connectors::Connector::new(kind, source, "source-validation".into())?;
    ensure!(
        !token.is_empty()
            && token.len() <= 8192
            && !token.chars().any(char::is_control)
            && account.len() <= 8192
            && !account.chars().any(char::is_control),
        "Gültige Zugangsdaten eingeben"
    );
    let value = match kind {
        "trello" => {
            ensure!(
                !account.is_empty(),
                "Trello benötigt zusätzlich den API-Key"
            );
            serde_json::json!({"key":account,"token":token}).to_string()
        }
        "jira" if !account.is_empty() => {
            serde_json::json!({"email":account,"token":token}).to_string()
        }
        "github" | "asana" | "notion" | "jira" | "gitea" => token.into(),
        _ => anyhow::bail!("Unbekannter Anbieter"),
    };
    let bus = gio::bus_get_future(gio::BusType::Session).await?;
    let collection: ObjectPath = call(&bus, ROOT, SERVICE, "ReadAlias", &("default",).to_variant())
        .await?
        .child_value(0)
        .get()
        .context("Schlüsselbund fehlt")?;
    ensure!(
        collection.as_str() != "/",
        "Persönlichen Standardschlüsselbund zuerst mit der PAM-Sitzung einrichten"
    );
    let locked = call(
        &bus,
        &collection,
        "org.freedesktop.DBus.Properties",
        "Get",
        &("org.freedesktop.Secret.Collection", "Locked").to_variant(),
    )
    .await?
    .child_value(0)
    .get::<glib::Variant>()
    .and_then(|v| v.get::<bool>())
    .context("Schlüsselbundstatus fehlt")?;
    ensure!(
        !locked,
        "Schlüsselbund ist gesperrt. Rampi öffnet keinen externen Entsperrdialog."
    );
    let session = session(&bus).await?;
    let result = async {
        let props = HashMap::from([
            (
                "org.freedesktop.Secret.Item.Label".to_string(),
                format!("Rampi Kanban · {profile}").to_variant(),
            ),
            (
                "org.freedesktop.Secret.Item.Attributes".into(),
                attributes(profile, kind, source).to_variant(),
            ),
        ]);
        let secret: Secret = (
            session.clone(),
            vec![],
            value.into_bytes(),
            "text/plain; charset=utf-8".into(),
        );
        let response = call(
            &bus,
            &collection,
            "org.freedesktop.Secret.Collection",
            "CreateItem",
            &(props, secret, true).to_variant(),
        )
        .await?;
        let prompt: ObjectPath = response
            .child_value(1)
            .get()
            .context("Ungültige Schlüsselbundantwort")?;
        if prompt.as_str() != "/" {
            let _ = call(
                &bus,
                &prompt,
                "org.freedesktop.Secret.Prompt",
                "Dismiss",
                &().to_variant(),
            )
            .await;
            anyhow::bail!(
                "Schlüsselbund verlangt eine Entsperrung. Zugangsdaten wurden nicht bestätigt."
            );
        }
        ensure!(
            response.child_value(0).str().is_some_and(|p| p != "/"),
            "Schlüsselbund hat keinen Eintrag gespeichert"
        );
        Ok(())
    }
    .await;
    close(&bus, &session).await;
    result
}
