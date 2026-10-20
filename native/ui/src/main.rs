#[cfg(target_os = "linux")]
mod audio;
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
mod views;
#[cfg(target_os = "linux")]
mod widgets;

fn main() {
    #[cfg(target_os = "linux")]
    if std::env::args().any(|a| a == "--service-check") {
        if let Err(e) = service_checks::run() {
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
    std::process::exit(linux::run().value());
    #[cfg(not(target_os = "linux"))]
    {
        eprintln!(
            "Die native Rampi-Oberfläche läuft unter Linux/Wayland. Windows ist das Hostsystem."
        );
        std::process::exit(2);
    }
}
