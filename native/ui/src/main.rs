#[cfg(target_os = "linux")]
mod account_checks;
#[cfg(target_os = "linux")]
mod account_create;
#[cfg(target_os = "linux")]
mod account_view;
#[cfg(target_os = "linux")]
mod audio;
#[cfg(target_os = "linux")]
mod board_data;
#[cfg(target_os = "linux")]
mod board_settings;
#[cfg(target_os = "linux")]
mod board_view;
#[cfg(target_os = "linux")]
mod browser_checks;
#[cfg(target_os = "linux")]
mod browser_modern_checks;
#[cfg(target_os = "linux")]
mod browser_prompts;
#[cfg(target_os = "linux")]
mod bus;
#[cfg(target_os = "linux")]
mod checks;
#[cfg(target_os = "linux")]
mod dashboard_status;
#[cfg(target_os = "linux")]
mod downloads;
#[cfg(target_os = "linux")]
mod gitea_live_checks;
#[cfg(target_os = "linux")]
mod host_view;
#[cfg(target_os = "linux")]
mod interaction_checks;
#[cfg(target_os = "linux")]
mod kanban_checks;
#[cfg(target_os = "linux")]
mod language_checks;
#[cfg(target_os = "linux")]
mod linux;
#[cfg(target_os = "linux")]
mod login_branding;
#[cfg(target_os = "linux")]
mod mixed_soak;
#[cfg(target_os = "linux")]
mod pairing;
#[cfg(target_os = "linux")]
mod pairing_checks;
#[cfg(target_os = "linux")]
mod pam_keyring_checks;
#[cfg(target_os = "linux")]
mod performance;
#[cfg(target_os = "linux")]
mod process;
#[cfg(target_os = "linux")]
mod rdp_checks;
#[cfg(target_os = "linux")]
mod rdp_view;
#[cfg(target_os = "linux")]
mod secret_service;
#[cfg(target_os = "linux")]
mod service_checks;
#[cfg(target_os = "linux")]
mod setup_view;
#[cfg(target_os = "linux")]
mod ssh_setup;
#[cfg(target_os = "linux")]
mod ssh_view;
#[cfg(target_os = "linux")]
mod stream_checks;
#[cfg(target_os = "linux")]
mod stream_input;
#[cfg(target_os = "linux")]
mod stream_soak;
#[cfg(target_os = "linux")]
mod stream_view;
#[cfg(target_os = "linux")]
mod system_checks;
#[cfg(target_os = "linux")]
mod system_settings;
#[cfg(target_os = "linux")]
mod tailscale;
#[cfg(target_os = "linux")]
mod uploads;
#[cfg(target_os = "linux")]
mod views;
#[cfg(target_os = "linux")]
mod vpn_view;
#[cfg(target_os = "linux")]
mod widgets;
#[cfg(target_os = "linux")]
mod wifi_hidden;
#[cfg(target_os = "linux")]
mod wireguard;

fn main() {
    if std::env::args().any(|argument| argument == "--session-locale") {
        let result = rampi_core::config::config_dir()
            .and_then(|path| rampi_core::config::Settings::load(&path.join("settings.json")));
        match result {
            Ok(settings) => {
                if let Some(locale) = rampi_core::i18n::locale(&settings.language) {
                    println!(
                        "LANGUAGE={}\nLANG={locale}\nLC_MESSAGES={locale}\nLC_TIME={locale}",
                        settings.language
                    );
                    return;
                }
                eprintln!("Nicht unterstützte persönliche Sprache.");
            }
            Err(error) => eprintln!("Persönliche Sprache nicht lesbar: {error}"),
        }
        std::process::exit(1);
    }
    #[cfg(target_os = "linux")]
    if std::env::args().any(|a| a == "--stream-runtime-check") {
        if let Err(error) = rampi_stream::runtime::MoonlightRuntime::load() {
            eprintln!("Streaming-Laufzeit: {error}");
            std::process::exit(1);
        }
        println!("RAMPI_STREAM_RUNTIME_LOAD_OK");
        return;
    }
    #[cfg(target_os = "linux")]
    if std::env::args().any(|a| a == "--pam-keyring-check") {
        if let Err(error) = pam_keyring_checks::run() {
            eprintln!("Native PAM keyring acceptance failed: {error:#}");
            std::process::exit(1);
        }
        return;
    }
    #[cfg(target_os = "linux")]
    if std::env::args().any(|a| a == "--login-background") {
        std::process::exit(i32::from(login_branding::run()));
    }
    #[cfg(target_os = "linux")]
    if std::env::args().any(|a| a == "--kanban-cloud-check") {
        if let Err(error) = kanban_checks::run() {
            eprintln!("Cloud Kanban acceptance failed: {error:#}");
            std::process::exit(1);
        }
        return;
    }
    #[cfg(target_os = "linux")]
    if std::env::args().any(|a| a == "--tailscale-check") {
        if let Err(error) = service_checks::tailscale() {
            eprintln!("Tailscale check failed: {error}");
            std::process::exit(1);
        }
        return;
    }
    #[cfg(target_os = "linux")]
    if std::env::args().any(|a| a == "--vpn-action" || a == "--wireguard-check") {
        let result = if std::env::args().any(|a| a == "--vpn-action") {
            service_checks::vpn_action()
        } else {
            service_checks::wireguard()
        };
        if let Err(error) = result {
            eprintln!("VPN check failed: {error}");
            std::process::exit(1);
        }
        return;
    }
    #[cfg(target_os = "linux")]
    if std::env::args().any(|a| a == "--service-check" || a == "--bluetooth-check") {
        let check = if std::env::args().any(|a| a == "--bluetooth-check") {
            service_checks::bluetooth
        } else {
            service_checks::run
        };
        if let Err(e) = check() {
            eprintln!("Service contract failed: {e}");
            std::process::exit(1);
        }
        return;
    }
    if std::env::args().any(|a| a == "--version") {
        println!("Rampi {} (Rust / Wayland)", env!("CARGO_PKG_VERSION"));
        return;
    }
    #[cfg(target_os = "linux")]
    std::process::exit(i32::from(linux::run()));
    #[cfg(not(target_os = "linux"))]
    {
        eprintln!(
            "Die native Rampi-Oberfläche läuft unter Linux/Wayland. Windows ist das Hostsystem."
        );
        std::process::exit(2);
    }
}
