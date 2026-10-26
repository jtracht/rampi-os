//! Pairing and authenticated launch/resume through the existing Moonlight SDK.
//! Blocking methods belong on workers; persisted identities belong in the
//! existing personal Secret Service, never a shared configuration or log.
use crate::{
    runtime::{MoonlightRuntime, PendingConnection, RemoteControl},
    transport::CurlClient,
};
use anyhow::{Result, anyhow, ensure};
use moonlight_common::{
    AppId,
    crypto::openssl::OpenSSLCryptoBackend,
    high::std::MoonlightHost,
    http::{
        ClientIdentifier, ClientSecret, ServerIdentifier,
        pair::{PairPin, PairingCryptoBackend},
    },
    stream::{
        AesIv, AesKey, EncryptionFlags, MoonlightStreamSettings, StreamingConfig,
        audio::AudioConfig,
        control::ActiveGamepads,
        video::{ColorRange, ColorSpace, VideoFormats},
    },
};
use openssl::{pkey::PKey, x509::X509};
use pem::Pem;
use serde::{Deserialize, Serialize};
use std::str::FromStr;
use uuid::Uuid;
use zeroize::{Zeroize, Zeroizing};

#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SavedIdentity {
    version: u32,
    address: String,
    port: u16,
    unique_id: String,
    certificate: String,
    key: String,
    server_certificate: String,
}
impl Drop for SavedIdentity {
    fn drop(&mut self) {
        self.key.zeroize();
    }
}
impl SavedIdentity {
    pub fn matches_target(&self, address: &str, port: u16) -> Result<bool> {
        Ok(self.port == port && target(&self.address, self.port)? == target(address, port)?)
    }
    /// Store only with the existing personal secret store. No Debug output.
    pub fn to_secret(&self) -> Result<Zeroizing<String>> {
        Ok(Zeroizing::new(serde_json::to_string(self)?))
    }
    pub fn from_secret(secret: &str) -> Result<Self> {
        ensure!(secret.len() <= 65536, "Streaming-Identität ist zu groß");
        let identity: Self = serde_json::from_str(secret)
            .map_err(|_| anyhow!("Gespeicherte Streaming-Identität ist ungültig"))?;
        ensure!(
            identity.version == 1,
            "Streaming-Identitätsversion wird nicht unterstützt"
        );
        target(&identity.address, identity.port)?;
        Uuid::parse_str(&identity.unique_id)
            .map_err(|_| anyhow!("Streaming-Gerätekennung ist ungültig"))?;
        let key = PKey::private_key_from_pem(identity.key.as_bytes())?;
        let certificate = X509::from_pem(identity.certificate.as_bytes())?;
        ensure!(
            certificate.public_key()?.public_eq(&key),
            "Streaming-Schlüssel und Zertifikat passen nicht zusammen"
        );
        X509::from_pem(identity.server_certificate.as_bytes())?;
        Ok(identity)
    }
}

fn target(address: &str, port: u16) -> Result<String> {
    ensure!(
        port > 0 && address.len() <= 253 && !address.is_empty(),
        "Ungültiger Sunshine-Host"
    );
    let host = parsed_host(address)?;
    Ok(match host {
        url::Host::Ipv6(address) => format!("[{address}]"),
        other => other.to_string(),
    })
}
fn parsed_host(address: &str) -> Result<url::Host<String>> {
    if let Ok(address) = address.parse::<std::net::Ipv6Addr>() {
        return Ok(url::Host::Ipv6(address));
    }
    url::Host::parse(address).map_err(|_| anyhow!("Ungültiger Sunshine-Host"))
}

pub struct PairRequest {
    host: MoonlightHost<CurlClient>,
    address: String,
    port: u16,
    unique_id: String,
    certificate: ClientIdentifier,
    key: ClientSecret,
    pin: PairPin,
    device_name: String,
}
impl PairRequest {
    /// Generates a new per-profile identity using the existing OpenSSL provider.
    /// Display pin() before running finish() on a worker.
    pub fn new(address: &str, port: u16, device_name: &str) -> Result<Self> {
        let normalized = target(address, port)?;
        ensure!(
            !device_name.is_empty()
                && device_name.len() <= 80
                && !device_name.chars().any(char::is_control),
            "Ungültiger Gerätename"
        );
        let crypto = OpenSSLCryptoBackend;
        let (certificate, key) = crypto.generate_client_identity()?;
        let unique_id = Uuid::new_v4().to_string();
        let host = MoonlightHost::new(normalized, port, Some(unique_id.clone()))?;
        Ok(Self {
            host,
            address: address.to_owned(),
            port,
            unique_id,
            certificate,
            key,
            pin: PairPin::new_random(&crypto)?,
            device_name: device_name.to_owned(),
        })
    }
    pub fn pin(&self) -> String {
        self.pin.to_string()
    }
    pub fn finish(self) -> Result<(PairedHost, SavedIdentity)> {
        self.host
            .pair(
                &self.certificate,
                &self.key,
                self.device_name,
                self.pin,
                OpenSSLCryptoBackend,
            )
            .map_err(|_| anyhow!("Sunshine-Kopplung fehlgeschlagen. PIN und Host prüfen."))?;
        let (certificate, key, server) = self
            .host
            .identity()
            .ok_or_else(|| anyhow!("Sunshine hat keine bestätigte Identität geliefert"))?;
        let saved = SavedIdentity {
            version: 1,
            address: self.address.clone(),
            port: self.port,
            unique_id: self.unique_id,
            certificate: certificate.to_pem().to_string(),
            key: key.to_pem().to_string(),
            server_certificate: server.to_pem().to_string(),
        };
        Ok((
            PairedHost {
                host: self.host,
                address: self.address,
            },
            saved,
        ))
    }
}

pub struct Application {
    pub id: u32,
    pub title: String,
}
pub struct PairedHost {
    host: MoonlightHost<CurlClient>,
    address: String,
}
impl PairedHost {
    /// Existing identity's server public key must match before authenticated use.
    pub fn restore(identity: &SavedIdentity) -> Result<Self> {
        let host = MoonlightHost::new(
            target(&identity.address, identity.port)?,
            identity.port,
            Some(identity.unique_id.clone()),
        )?;
        host.set_identity(
            ClientIdentifier::from_pem(Pem::from_str(&identity.certificate)?),
            ClientSecret::from_pem(Pem::from_str(&identity.key)?),
            ServerIdentifier::from_pem(Pem::from_str(&identity.server_certificate)?),
        )
        .map_err(|_| anyhow!("Sunshine-Identität oder Serverbindung wurde nicht bestätigt"))?;
        Ok(Self {
            host,
            address: identity.address.clone(),
        })
    }
    pub fn applications(&self) -> Result<Vec<Application>> {
        Ok(self
            .host
            .app_list()
            .map_err(|_| anyhow!("Sunshine-Anwendungen nicht erreichbar"))?
            .into_iter()
            .map(|app| Application {
                id: app.id.0,
                title: app.title,
            })
            .collect())
    }
    /// Uses the SDK's authenticated launch/resume and the official C version
    /// query. Run this and the returned pending start on a worker.
    pub fn prepare(
        &self,
        runtime: &MoonlightRuntime,
        app: u32,
        options: StreamOptions,
    ) -> Result<(RemoteControl, PendingConnection)> {
        let mut settings = options.settings()?;
        let reserved = runtime.reserve()?;
        self.host
            .update()
            .map_err(|_| anyhow!("Sunshine-Status nicht erreichbar"))?;
        ensure!(
            self.applications()?.iter().any(|item| item.id == app),
            "Unbekannte Sunshine-Anwendung"
        );
        let current = self.host.current_game()?;
        ensure!(
            current == 0 || current == app,
            "Eine andere Sunshine-Anwendung läuft bereits"
        );
        settings.adjust_for_server(
            self.host.version()?,
            &self.host.gfe_version()?,
            self.host.server_codec_mode_support()?,
        )?;
        let crypto = OpenSSLCryptoBackend;
        let mut config = self
            .host
            .start_stream(
                AppId(app),
                &settings,
                AesKey::new_random(&crypto)?,
                AesIv::new_random(&crypto)?,
                &runtime.launch_query_parameters()?,
            )
            .map_err(|_| {
                anyhow!("Sunshine-Stream konnte nicht gestartet oder fortgesetzt werden")
            })?;
        // HTTP authorities require IPv6 brackets; the C resolver expects the
        // original host address rather than HTTP authority syntax.
        config.address = match parsed_host(&self.address)? {
            url::Host::Ipv6(address) => address.to_string(),
            address => address.to_string(),
        };
        reserved.prepare_config(config, settings)
    }
}

#[derive(Clone, Copy)]
pub struct StreamOptions {
    pub width: u32,
    pub height: u32,
    pub fps: u32,
    pub bitrate: u32,
}
impl Default for StreamOptions {
    fn default() -> Self {
        Self {
            width: 1280,
            height: 720,
            fps: 30,
            bitrate: 8000,
        }
    }
}
impl StreamOptions {
    fn settings(self) -> Result<MoonlightStreamSettings> {
        ensure!(
            (32..=1920).contains(&self.width)
                && (32..=1080).contains(&self.height)
                && self.width.is_multiple_of(2)
                && self.height.is_multiple_of(2)
                && (1..=60).contains(&self.fps)
                && (100..=50000).contains(&self.bitrate),
            "Ungültiges Streaming-Profil"
        );
        Ok(MoonlightStreamSettings {
            width: self.width,
            height: self.height,
            fps: self.fps,
            fps_x100: self.fps * 100,
            bitrate: self.bitrate,
            packet_size: 1024,
            encryption_flags: EncryptionFlags::all(),
            streaming_remotely: StreamingConfig::Auto,
            sops: true,
            hdr: false,
            supported_video_formats: VideoFormats::H264,
            color_space: ColorSpace::Rec709,
            color_range: ColorRange::Limited,
            local_audio_play_mode: false,
            audio_config: AudioConfig::STEREO,
            gamepads_attached: ActiveGamepads::empty(),
            gamepads_persist_after_disconnect: false,
            enable_mic: false,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::{
        fs,
        os::unix::fs::PermissionsExt,
        path::Path,
        thread,
        time::{Duration, Instant},
    };

    #[test]
    fn identity_key_binding_and_target_validation() -> Result<()> {
        let first = PairRequest::new("127.0.0.1", 47989, "first")?;
        let second = PairRequest::new("127.0.0.1", 47989, "second")?;
        let mut identity = SavedIdentity {
            version: 1,
            address: "127.0.0.1".into(),
            port: 47989,
            unique_id: first.unique_id.clone(),
            certificate: first.certificate.to_pem().to_string(),
            key: first.key.to_pem().to_string(),
            server_certificate: second.certificate.to_pem().to_string(),
        };
        let encoded = identity.to_secret()?;
        let recovered = SavedIdentity::from_secret(&encoded)?;
        ensure!(
            recovered.unique_id == identity.unique_id,
            "Personal identifier changed"
        );
        identity.key = second.key.to_pem().to_string();
        ensure!(
            SavedIdentity::from_secret(&identity.to_secret()?).is_err(),
            "Mismatched real key accepted"
        );
        ensure!(target("::1", 47989)? == "[::1]", "IPv6 authority invalid");
        for invalid in [
            "https://host",
            "user@host",
            "host/path",
            "host?query",
            "host\n",
        ] {
            ensure!(
                target(invalid, 47989).is_err(),
                "Invalid authority accepted"
            );
        }
        ensure!(target("host", 0).is_err(), "Zero port accepted");
        Ok(())
    }

    /// Run only against the existing disposable Sunshine fixture. This does
    /// not claim GTK presentation, input delivery or Windows-host acceptance.
    #[test]
    #[ignore = "requires the actual isolated Sunshine server and PIN approval fixture"]
    fn actual_sunshine_pair_restore_and_video() -> Result<()> {
        ensure!(
            Path::new("/.dockerenv").exists()
                && std::env::var("RAMPI_TEST_CONTAINER").as_deref() == Ok("1"),
            "Disposable container required"
        );
        let address = std::env::var("RAMPI_TEST_SUNSHINE")?;
        let pairing = PairRequest::new(&address, 47989, "Rampi isolated acceptance")?;
        let directory = Path::new("/run/rampi-acceptance");
        fs::create_dir_all(directory)?;
        fs::set_permissions(directory, fs::Permissions::from_mode(0o700))?;
        let pin = directory.join("pairing-pin");
        fs::write(&pin, pairing.pin())?;
        fs::set_permissions(&pin, fs::Permissions::from_mode(0o600))?;
        let (paired, identity) = pairing.finish()?;
        fs::remove_file(pin)?;
        let secret = identity.to_secret()?;
        let restored = SavedIdentity::from_secret(&secret)?;
        // A valid but different public certificate must fail the actual pinned
        // TLS handshake. No private key or raw protocol URL is printed.
        let foreign = PairRequest::new(&address, 47989, "different unpaired identity")?;
        let mut wrong_server = restored.clone();
        wrong_server.server_certificate = foreign.certificate.to_pem().to_string();
        ensure!(
            PairedHost::restore(&wrong_server).is_err(),
            "Changed server key was accepted"
        );
        let apps = paired.applications()?;
        let desktop = apps
            .iter()
            .find(|app| app.title.to_lowercase().contains("desktop"))
            .ok_or_else(|| anyhow!("Fixture Desktop application missing"))?
            .id;
        let runtime = MoonlightRuntime::load()?;
        for _ in 0..2 {
            let host = PairedHost::restore(&restored)?;
            let (control, pending) = host.prepare(&runtime, desktop, StreamOptions::default())?;
            let worker = thread::spawn(move || pending.start().map(|session| session.wait()));
            let outcome = (|| -> Result<()> {
                let started = Instant::now();
                let deadline = started + Duration::from_secs(60);
                let mut seen = [false; 2];
                while Instant::now() < deadline
                    && (!seen.iter().all(|seen| *seen)
                        || started.elapsed() < Duration::from_secs(4))
                {
                    ensure!(
                        !worker.is_finished(),
                        "Actual C stream ended: {:?}",
                        control.phase()
                    );
                    if let Some(frame) = control.take_frame()? {
                        ensure!(
                            frame.width == 1280 && frame.height == 720,
                            "Unexpected actual frame size"
                        );
                        let pixel = &frame.rgba[350 * frame.stride + 500 * 4..][..3];
                        for (index, expected) in
                            [[38u8, 123, 189], [211, 53, 106]].iter().enumerate()
                        {
                            if pixel.iter().zip(expected).all(|(a, b)| a.abs_diff(*b) < 20) {
                                seen[index] = true;
                            }
                        }
                    }
                    thread::sleep(Duration::from_millis(25));
                }
                ensure!(
                    seen.iter().all(|seen| *seen),
                    "Changing Sunshine pixels did not arrive: {seen:?}"
                );
                Ok(())
            })();
            control.stop();
            let deadline = Instant::now() + Duration::from_secs(20);
            while !worker.is_finished() && Instant::now() < deadline {
                thread::sleep(Duration::from_millis(20));
            }
            ensure!(worker.is_finished(), "Actual C cleanup timed out");
            worker
                .join()
                .map_err(|_| anyhow!("Stream worker panicked"))??;
            outcome?;
        }
        println!(
            "RAMPI_STREAM_SUNSHINE_VIDEO_OK: actual pairing, server-key rejection, restored identity and two changing video connections"
        );
        Ok(())
    }
}
