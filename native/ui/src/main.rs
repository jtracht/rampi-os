#[cfg(target_os = "linux")]
mod audio;
#[cfg(target_os = "linux")]
mod board_view;
#[cfg(target_os = "linux")]
mod browser_prompts;
#[cfg(target_os = "linux")]
mod bus;
#[cfg(target_os = "linux")]
mod checks;
#[cfg(target_os = "linux")]
mod linux;
#[cfg(target_os = "linux")]
mod pairing;
#[cfg(target_os = "linux")]
mod service_checks;
#[cfg(target_os = "linux")]
mod tailscale;
#[cfg(target_os = "linux")]
mod views;
#[cfg(target_os = "linux")]
mod vpn_view;
#[cfg(target_os = "linux")]
mod widgets;
#[cfg(target_os = "linux")]
mod wireguard;

fn main() {
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
