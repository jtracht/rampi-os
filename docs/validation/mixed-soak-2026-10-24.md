# Ten-minute native mixed workload

This acceptance runs the production Rust application under actual headless
labwc/Wayland, Pixman and GTK Cairo with a 1 GiB cgroup limit, no swap and four
CPU cores. It is software validation, not a Raspberry Pi GPU, physical-device
or Windows-host performance measurement.

The workload keeps an actual TLS-authenticated XRDP desktop, a trusted HTTPS
WebKit canvas page and three existing VTE PTYs alive concurrently. Seven real
pages are switched repeatedly for at least ten minutes. It measures observed
GTK paints, whole-container memory and CPU accounting, verifies JavaScript and
PTY roundtrips, hashes cropped compositor output from the remote display, and
requires server-side receipts for input repeatedly sent during the workload.
The fixture hides its remote text cursor and changes a frame counter every
250 ms; a local cursor blink is not counted as remote-video evidence.

`scripts/check-soak-evidence.py` requires the full duration, all workloads,
measured resource limits, paint latency below 500 ms at p95, at least 30 different
remote pixel hashes, memory headroom and bounded growth after warm-up. It also
independently checks all expected input tokens against actual server receipts.
The 16 guard tests reject incomplete or invalid reports. The native CI and local
full-suite harness both require this stage; partial local attempts do not count
as a completed milestone. The accepted executable is bound by SHA-256.

Current status: implementation complete; final runtime and both architecture CI
results pending. Performance remains three points until those pass and are
independently reviewed.
