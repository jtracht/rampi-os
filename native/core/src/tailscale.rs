//! Read the documented status JSON from the official CLI; no VPN protocol code.
use anyhow::{Result, ensure};
use serde::Deserialize;
use std::net::IpAddr;

#[derive(Deserialize)]
pub struct Status {
    #[serde(rename = "BackendState")]
    pub backend: String,
    #[serde(rename = "TailscaleIPs", default)]
    pub addresses: Option<Vec<IpAddr>>,
    #[serde(rename = "Self", default)]
    pub node: Option<Node>,
    #[serde(rename = "Health", default)]
    pub health: Option<Vec<String>>,
}
#[derive(Deserialize)]
pub struct Node {
    #[serde(rename = "Online", default)]
    pub online: Option<bool>,
}
impl Status {
    pub fn parse(bytes: &[u8]) -> Result<Self> {
        ensure!(bytes.len() <= 262_144, "Tailscale-Antwort ist zu groß.");
        let status: Self = serde_json::from_slice(bytes).map_err(|_| {
            anyhow::anyhow!("Tailscale liefert ein nicht unterstütztes Statusformat.")
        })?;
        ensure!(status.backend.len() <= 128, "Ungültiger Tailscale-Status.");
        Ok(status)
    }
    pub fn connected(&self) -> bool {
        self.backend == "Running"
            && self
                .node
                .as_ref()
                .is_some_and(|node| node.online == Some(true))
            && self.addresses.as_ref().is_some_and(|ips| !ips.is_empty())
    }
    pub fn description(&self) -> String {
        let state = match self.backend.as_str() {
            "Running" if self.connected() => "Verbunden",
            "Running" if self.node.as_ref().is_some_and(|n| n.online == Some(false)) => {
                "Dienst aktiv, Verbindung unterbrochen"
            }
            "Running" => "Dienst aktiv, Verbindungsstatus unvollständig",
            "NeedsLogin" => "Anmeldung erforderlich",
            "NeedsMachineAuth" => "Freigabe des Geräts im Tailscale-Konto erforderlich",
            "Stopped" => "Getrennt",
            "Starting" => "Verbindung wird aufgebaut",
            "NoState" => "Dienst wird initialisiert",
            _ => "Unbekannter Status; offizielle Tailscale-Diagnose verwenden",
        };
        let mut text = format!("Tailscale · {state}");
        if self.connected() {
            let ips = self
                .addresses
                .as_ref()
                .unwrap()
                .iter()
                .map(ToString::to_string)
                .collect::<Vec<_>>();
            text.push_str(&format!("\nVPN-Adressen: {}", ips.join(", ")));
        }
        if let Some(health) = &self.health {
            for message in health.iter().take(8) {
                let message: String = message
                    .chars()
                    .filter(|c| !c.is_control())
                    .take(500)
                    .collect();
                if !message.is_empty() {
                    text.push_str(&format!("\nHinweis: {message}"));
                }
            }
        }
        text
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn running_without_online_evidence_is_not_connected() {
        for data in [
            r#"{"BackendState":"Running"}"#,
            r#"{"BackendState":"Running","Self":{"Online":false},"TailscaleIPs":["100.64.0.1"]}"#,
            r#"{"BackendState":"Running","Self":{"Online":true},"TailscaleIPs":null}"#,
            r#"{"BackendState":"FutureState","Self":{"Online":true},"TailscaleIPs":["100.64.0.1"]}"#,
        ] {
            assert!(!Status::parse(data.as_bytes()).unwrap().connected());
        }
        let status = Status::parse(br#"{"BackendState":"Running","Self":{"Online":true},"TailscaleIPs":["100.64.0.1","fd7a:115c:a1e0::1"]}"#).unwrap();
        assert!(status.connected());
        assert!(status.description().contains("100.64.0.1"));
    }
    #[test]
    fn login_states_and_invalid_output_fail_closed() {
        let status = Status::parse(br#"{"BackendState":"NeedsLogin","Self":null,"Health":null,"AuthURL":"https://example.invalid/test-login"}"#).unwrap();
        assert!(status.description().contains("Anmeldung erforderlich"));
        assert!(!status.description().contains("test-login"));
        for invalid in [
            b"{}".as_slice(),
            b"not-json",
            br#"{"BackendState":"Running","TailscaleIPs":["not-an-ip"]}"#,
        ] {
            assert!(Status::parse(invalid).is_err());
        }
        assert!(Status::parse(&vec![b' '; 262_145]).is_err());
    }
}
