//! Executable measurements on the real GTK frame clock; software rendering only.
use gtk::{glib, prelude::*};
use std::{
    cell::RefCell,
    rc::Rc,
    time::{Duration, Instant},
};
use webkit6::prelude::*;

fn cpu_ns() -> u64 {
    std::fs::read_to_string("/proc/self/schedstat")
        .unwrap()
        .split_whitespace()
        .next()
        .unwrap()
        .parse()
        .unwrap()
}
fn rss_kib() -> u64 {
    std::fs::read_to_string("/proc/self/status")
        .unwrap()
        .lines()
        .find_map(|l| l.strip_prefix("VmRSS:"))
        .unwrap()
        .split_whitespace()
        .next()
        .unwrap()
        .parse()
        .unwrap()
}
pub fn run(
    app: &gtk::Application,
    window: &gtk::ApplicationWindow,
    stack: &gtk::Stack,
    conf: &crate::widgets::Shared,
    feedback: &crate::widgets::Feedback,
    launched: Instant,
) {
    assert_eq!(std::env::var("RAMPI_TEST_CONTAINER").as_deref(), Ok("1"));
    let (app, window, stack, conf, feedback) = (
        app.clone(),
        window.clone(),
        stack.clone(),
        conf.clone(),
        feedback.clone(),
    );
    glib::MainContext::default().spawn_local(async move {
        for _ in 0..500 {
            if window.is_mapped() { break; }
            glib::timeout_future(Duration::from_millis(10)).await;
        }
        let clock = window.frame_clock().expect("Mapped Wayland window has a frame clock");
        let pending = Rc::new(RefCell::new(Some(launched)));
        let samples = Rc::new(RefCell::new(Vec::<f64>::new()));
        let intervals = Rc::new(RefCell::new(Vec::<f64>::new()));
        let previous = Rc::new(RefCell::new(None::<Instant>));
        let (p, s, ticks, prev) = (pending.clone(), samples.clone(), intervals.clone(), previous.clone());
        let handler = clock.connect_after_paint(move |_| {
            let now = Instant::now();
            if let Some(start) = p.borrow_mut().take() { s.borrow_mut().push(start.elapsed().as_secs_f64() * 1000.0); }
            if let Some(last) = prev.replace(Some(now)) { ticks.borrow_mut().push(now.duration_since(last).as_secs_f64() * 1000.0); }
        });
        stack.set_visible_child_name("dashboard"); window.queue_draw();
        glib::timeout_future(Duration::from_secs(2)).await;
        let startup_ms = samples.borrow_mut().pop().expect("First painted frame");
        let status = gtk::Label::new(None);
        for name in ["perf-codex", "perf-claude", "perf-gemini"] {
            crate::views::terminal(&stack, name, vec!["/bin/cat".into()], &status);
        }
        crate::views::browser(&stack, &conf, &status, &feedback);
        fn web(root: &gtk::Widget) -> Option<webkit6::WebView> {
            if let Ok(view) = root.clone().downcast::<webkit6::WebView>() { return Some(view); }
            let mut next = root.first_child(); while let Some(w) = next { if let Some(v) = web(&w) { return Some(v); } next = w.next_sibling(); } None
        }
        web(&stack.child_by_name("browser").unwrap()).unwrap().load_html("<title>Rampi performance fixture</title><h1>Offline browser</h1><script>document.body.dataset.ready='yes'</script>", None);
        let routes = ["dashboard", "kanban", "terminal-perf-codex", "terminal-perf-claude", "terminal-perf-gemini", "remote", "browser", "settings"];
        let cpu_start = cpu_ns(); let wall = Instant::now(); let mut peak_rss = rss_kib();
        let mut warm_rss = 0;
        for index in 0..600 {
            *pending.borrow_mut() = Some(Instant::now());
            assert!(stack.child_by_name(routes[index % routes.len()]).is_some(), "Missing real module page");
            stack.set_visible_child_name(routes[index % routes.len()]); window.queue_draw();
            assert_eq!(stack.visible_child_name().as_deref(), Some(routes[index % routes.len()]));
            glib::timeout_future(Duration::from_millis(300)).await;
            assert!(pending.borrow().is_none(), "No actual paint after module change");
            peak_rss = peak_rss.max(rss_kib());
            if index == 80 { warm_rss = rss_kib(); }
            assert_eq!(app.windows().len(), 1, "Module switch opened another window");
        }
        let final_rss = rss_kib();
        assert!(final_rss <= warm_rss + 64 * 1024, "Resident memory grew excessively after warm-up");
        let switching_cpu = (cpu_ns() - cpu_start) as f64 / wall.elapsed().as_nanos() as f64 * 100.0;
        stack.set_visible_child_name("dashboard"); conf.borrow_mut().reduce_motion = true;
        glib::timeout_future(Duration::from_secs(2)).await;
        let idle_cpu_start = cpu_ns(); let idle_start = Instant::now();
        glib::timeout_future(Duration::from_secs(10)).await;
        let idle_cpu = (cpu_ns() - idle_cpu_start) as f64 / idle_start.elapsed().as_nanos() as f64 * 100.0;
        clock.disconnect(handler);
        let mut sorted = samples.borrow().clone(); sorted.sort_by(f64::total_cmp);
        assert_eq!(sorted.len(), 600);
        let p95 = sorted[(sorted.len() * 95 / 100).min(sorted.len() - 1)];
        assert!(startup_ms < 10000.0 && p95 < 500.0 && peak_rss < 900 * 1024, "Software performance budget exceeded");
        let ticks = intervals.borrow();
        let animation: Vec<_> = ticks.iter().copied().filter(|ms| *ms < 100.0).collect();
        let report = serde_json::json!({"scope":"headless labwc/Pixman; GTK Cairo; not Raspberry Pi timing or GPU proof", "startup_to_observed_paint_ms":startup_ms, "module_switches":sorted.len(), "warm_rss_mib":warm_rss as f64 / 1024.0, "final_rss_mib":final_rss as f64 / 1024.0, "switch_p95_paint_ms":p95, "process_peak_rss_mib":peak_rss as f64 / 1024.0, "switching_process_cpu_percent_of_one_core":switching_cpu, "reduced_motion_idle_process_cpu_percent_of_one_core":idle_cpu, "paint_intervals_under_100ms":animation.len(), "mean_active_paint_interval_ms":animation.iter().sum::<f64>() / animation.len().max(1) as f64});
        if let Some(dir) = std::env::var_os("RAMPI_TEST_ARTIFACTS") {
            let path = std::path::PathBuf::from(dir).join("performance.json");
            std::fs::write(&path, serde_json::to_vec_pretty(&report).unwrap()).unwrap();
            use std::os::unix::fs::PermissionsExt;
            std::fs::set_permissions(path, std::fs::Permissions::from_mode(0o644)).unwrap();
        }
        println!("RAMPI_RUST_PERFORMANCE_OK {report}"); app.quit();
    });
}
