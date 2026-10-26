//! Sustained real GTK/GStreamer flow under the fixture's enforced 1 GiB/4 CPU limit.
use anyhow::{Context, Result, ensure};
use gtk::{gdk, glib, prelude::*};
use std::{
    cell::{Cell, RefCell},
    rc::Rc,
    time::{Duration, Instant},
};

pub async fn run(picture: &gtk::Picture, window: &gtk::Window) -> Result<()> {
    let clock = window
        .frame_clock()
        .context("Actual stream frame clock missing")?;
    let frames = Rc::new(Cell::new(0u64));
    let pending = Rc::new(RefCell::new(None::<Instant>));
    let latencies = Rc::new(RefCell::new(Vec::<f64>::new()));
    let (count, queued) = (frames.clone(), pending.clone());
    let texture_handler = picture.connect_paintable_notify(move |widget| {
        if widget.paintable().is_some() {
            count.set(count.get() + 1);
            queued.borrow_mut().get_or_insert_with(Instant::now);
        }
    });
    let (queued, measured) = (pending, latencies.clone());
    let paint_handler = clock.connect_after_paint(move |_| {
        if let Some(ready) = queued.borrow_mut().take() {
            let mut measured = measured.borrow_mut();
            if measured.len() < 36000 {
                measured.push(ready.elapsed().as_secs_f64() * 1000.0);
            }
        }
    });
    let started = Instant::now();
    let rss_start = crate::performance::rss_kib();
    let mut peak = rss_start;
    let mut previous = None;
    let mut changes = 0;
    while started.elapsed() < Duration::from_secs(600) {
        glib::timeout_future(Duration::from_millis(500)).await;
        ensure!(
            picture.is_mapped(),
            "Streaming surface disappeared during sustained load"
        );
        peak = peak.max(crate::performance::rss_kib());
        let texture = picture
            .paintable()
            .and_downcast::<gdk::Texture>()
            .context("Stream lost its texture during sustained load")?;
        ensure!(
            texture.width() == 1280 && texture.height() == 720,
            "Stream dimensions changed"
        );
        let mut pixels = vec![0u8; 1280 * 720 * 4];
        texture.download(&mut pixels, 1280 * 4);
        let digest = glib::compute_checksum_for_data(glib::ChecksumType::Sha256, &pixels)
            .context("Frame digest unavailable")?;
        if previous.as_ref().is_some_and(|old| old != &digest) {
            changes += 1;
        }
        previous = Some(digest);
    }
    picture.disconnect(texture_handler);
    clock.disconnect(paint_handler);
    let duration = started.elapsed().as_secs_f64();
    let rss_end = crate::performance::rss_kib();
    let mut samples = latencies.borrow().clone();
    samples.sort_by(f64::total_cmp);
    ensure!(!samples.is_empty(), "Actual GTK paint samples missing");
    let p95 = samples[((samples.len() as f64 * 0.95).ceil() as usize - 1).min(samples.len() - 1)];
    let report = serde_json::json!({"duration_secs":duration, "frames":frames.get(),
        "changing_samples":changes, "painted_samples":samples.len(), "paint_p95_ms":p95,
        "rss_start_kib":rss_start, "rss_end_kib":rss_end, "rss_peak_kib":peak,
        "physical_hardware":false, "windows_host":false});
    std::fs::write(
        "/run/rampi-acceptance/gtk-soak.json",
        serde_json::to_vec_pretty(&report)?,
    )?;
    ensure!(
        frames.get() >= 12000 && changes >= 1000,
        "Sustained real 720p stream missed its frame/change budget"
    );
    ensure!(
        samples.len() as u64 * 10 >= frames.get() * 9 && p95 <= 80.0,
        "GTK painting missed its sustained frame/latency budget"
    );
    ensure!(
        peak <= 512 * 1024 && rss_end.saturating_sub(rss_start) <= 64 * 1024,
        "Sustained streaming exceeded its memory budget"
    );
    println!("RAMPI_STREAM_GTK_SOAK_OK {report}");
    Ok(())
}
