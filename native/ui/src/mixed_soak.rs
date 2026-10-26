//! Software-only mixed workload: real RDP frames, WebKit and three live PTYs.
use anyhow::{Context, ensure};
use gtk::{glib, prelude::*};
use std::{
    cell::RefCell,
    collections::HashSet,
    rc::Rc,
    time::{Duration, Instant},
};
use vte::prelude::*;
use webkit6::prelude::*;

fn cgroup(name: &str) -> anyhow::Result<u64> {
    Ok(std::fs::read_to_string(format!("/sys/fs/cgroup/{name}"))?
        .trim()
        .parse()?)
}

fn cpu_microseconds() -> anyhow::Result<u64> {
    std::fs::read_to_string("/sys/fs/cgroup/cpu.stat")?
        .lines()
        .find_map(|line| line.strip_prefix("usage_usec "))
        .context("No cgroup CPU accounting")?
        .parse()
        .context("Invalid CPU usage")
}

pub async fn run(
    app: &gtk::Application,
    stack: &gtk::Stack,
    conf: &crate::widgets::Shared,
    feedback: &crate::widgets::Feedback,
    remote: &rdw_rdp::Display,
) -> anyhow::Result<()> {
    ensure!(
        cgroup("memory.max")? == 1024 * 1024 * 1024,
        "Missing 1 GiB cgroup limit"
    );
    ensure!(cgroup("memory.swap.max")? == 0, "Swap must be disabled");
    let window = app.active_window().context("No native window")?;
    let status = gtk::Label::new(None);
    let mut terms = Vec::new();
    for name in ["soak-console-a", "soak-console-b", "soak-console-c"] {
        crate::views::terminal(
            stack,
            name,
            vec![
                "/bin/sh".into(),
                "-c".into(),
                "while IFS= read -r line; do printf 'ACK:%s\\n' \"$line\"; done".into(),
            ],
            &status,
        );
        terms.push(
            stack
                .visible_child()
                .unwrap()
                .downcast::<vte::Terminal>()
                .unwrap(),
        );
    }
    crate::views::browser(stack, conf, &status, feedback);
    let web = crate::checks::named(&stack.visible_child().unwrap(), "browser-webview")
        .context("No embedded browser")?
        .downcast::<webkit6::WebView>()
        .unwrap();
    web.load_uri("https://localhost:22225/soak");
    crate::browser_checks::wait_title(&web, "Rampi mixed workload").await?;
    let clock = window.frame_clock().context("No frame clock")?;
    let pending = Rc::new(RefCell::new(None::<Instant>));
    let paints = Rc::new(RefCell::new(Vec::<f64>::new()));
    let (p, samples) = (pending.clone(), paints.clone());
    let handler = clock.connect_after_paint(move |_| {
        if let Some(start) = p.borrow_mut().take() {
            samples
                .borrow_mut()
                .push(start.elapsed().as_secs_f64() * 1000.0);
        }
    });
    let routes = [
        "rdp-session",
        "browser",
        "terminal-soak-console-a",
        "terminal-soak-console-b",
        "terminal-soak-console-c",
        "dashboard",
        "settings",
    ];
    let started = Instant::now();
    let cpu_start = cpu_microseconds()?;
    let mut frames = HashSet::new();
    let mut records = Vec::new();
    let mut warm = 0;
    let mut cycle = 0;
    let mut input_tokens = Vec::new();
    while started.elapsed() < Duration::from_secs(600) {
        let round = Instant::now();
        for route in routes {
            *pending.borrow_mut() = Some(Instant::now());
            stack.set_visible_child_name(route);
            window.queue_draw();
            glib::timeout_future(Duration::from_millis(300)).await;
            ensure!(
                pending.borrow().is_none(),
                "No painted frame after module change: {route}"
            );
            ensure!(
                remote.property::<bool>("rdp-connected"),
                "RDP ended during mixed workload"
            );
            ensure!(
                app.windows().len() == 1,
                "Mixed workload opened another window"
            );
            if route == "rdp-session" {
                if cycle % 15 == 0 {
                    remote.grab_focus();
                    let token = format!("rampisoak{cycle}");
                    crate::rdp_checks::type_remote(&token).await?;
                    input_tokens.push(token);
                }
                // Read the actual compositor output, not a second GTK snapshot
                // between layout phases while network frames are arriving.
                let bounds = remote.compute_bounds(&window).context("No remote bounds")?;
                let geometry = format!(
                    "{},{} {}x{}",
                    bounds.x().ceil() as i32,
                    bounds.y().ceil() as i32,
                    bounds.width().floor() as i32,
                    bounds.height().floor() as i32
                );
                let path = format!(
                    "{}/mixed-remote.png",
                    std::env::var("RAMPI_TEST_ARTIFACTS")?
                );
                ensure!(
                    crate::process::output(
                        "grim",
                        &["-g".into(), geometry.into(), path.clone().into()],
                        5,
                        32768
                    )
                    .await?
                    .0,
                    "Remote pixel capture failed"
                );
                let bytes = std::fs::read(path)?;
                frames.insert(
                    glib::compute_checksum_for_data(glib::ChecksumType::Sha256, bytes.as_ref())
                        .unwrap()
                        .to_string(),
                );
            }
        }
        for term in &terms {
            term.feed_child(format!("soak{cycle}\n").as_bytes());
        }
        ensure!(web.evaluate_javascript_future(&format!("window.probe = {cycle}; window.probe === {cycle} && document.querySelector('canvas').width === 640"), None, None).await?.to_boolean(), "WebKit stopped processing JavaScript");
        glib::timeout_future(Duration::from_millis(100)).await;
        for term in &terms {
            ensure!(
                term.text_format(vte::Format::Text)
                    .unwrap_or_default()
                    .contains(&format!("ACK:soak{cycle}")),
                "PTY roundtrip failed"
            );
        }
        let memory = cgroup("memory.current")?;
        if started.elapsed() >= Duration::from_secs(60) && warm == 0 {
            warm = memory;
        }
        records.push(serde_json::json!({"elapsed_seconds":started.elapsed().as_secs_f64(), "cgroup_memory_bytes":memory}));
        if cycle % 15 == 0 {
            println!(
                "RAMPI_MIXED_SOAK_PROGRESS elapsed={} cycles={cycle}",
                started.elapsed().as_secs()
            );
        }
        cycle += 1;
        if let Some(rest) = Duration::from_secs(4).checked_sub(round.elapsed()) {
            glib::timeout_future(rest).await;
        }
    }
    clock.disconnect(handler);
    let mut samples = paints.borrow().clone();
    samples.sort_by(f64::total_cmp);
    let p95 = samples[samples.len() * 95 / 100];
    let final_memory = cgroup("memory.current")?;
    let peak = cgroup("memory.peak")?;
    ensure!(
        cycle >= 100 && samples.len() == cycle * routes.len(),
        "Incomplete workload"
    );
    ensure!(frames.len() >= 30, "Changing remote video was not received");
    ensure!(p95 < 500.0, "Paint latency exceeded software budget");
    ensure!(peak < 1000 * 1024 * 1024, "Insufficient memory headroom");
    ensure!(
        warm > 0 && final_memory < warm + 128 * 1024 * 1024,
        "Memory grew after warm-up"
    );
    let cpu_percent =
        (cpu_microseconds()? - cpu_start) as f64 / started.elapsed().as_secs_f64() / 10000.0;
    let binary = std::fs::read(std::env::current_exe()?)?;
    let binary_sha256 =
        glib::compute_checksum_for_data(glib::ChecksumType::Sha256, &binary).unwrap();
    let report = serde_json::json!({"scope":"10 minute headless Wayland/Pixman/Cairo software workload; no Pi GPU or Windows performance claim", "binary_sha256":binary_sha256.as_str(), "duration_seconds":started.elapsed().as_secs_f64(), "cycles":cycle, "module_switches":samples.len(), "switch_p95_paint_ms":p95, "distinct_remote_pixel_hashes":frames.len(), "remote_input_tokens":input_tokens, "cgroup_cpu_percent_of_one_core":cpu_percent, "live_ptys":terms.len(), "webkit_javascript_roundtrips":cycle, "memory_limit_bytes":cgroup("memory.max")?, "swap_limit_bytes":cgroup("memory.swap.max")?, "cgroup_peak_memory_bytes":peak, "warm_memory_bytes":warm, "final_memory_bytes":final_memory, "samples":records});
    let path =
        std::path::PathBuf::from(std::env::var("RAMPI_TEST_ARTIFACTS")?).join("mixed-soak.json");
    std::fs::write(&path, serde_json::to_vec_pretty(&report)?)?;
    use std::os::unix::fs::PermissionsExt;
    std::fs::set_permissions(path, std::fs::Permissions::from_mode(0o644))?;
    println!(
        "RAMPI_RUST_MIXED_SOAK_OK cycles={cycle} changing_remote_frames={} p95_ms={p95:.2}",
        frames.len()
    );
    stack.set_visible_child_name("rdp-session");
    glib::timeout_future(Duration::from_millis(500)).await;
    Ok(())
}
