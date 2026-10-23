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

Accepted head: `f33f7db83315eb850798c5f34a14c2ce934fb5f3`, merged as `b930aac`
in PR #29. [Native CI 40032661668](https://github.com/jtracht/rampi-os/actions/runs/40032661668)
and [general CI 40032661150](https://github.com/jtracht/rampi-os/actions/runs/40032661150)
passed. Both downloaded native evidence sets passed the complete checker, with
the installer requirement on ARM64. The package passed seven checksum checks;
its executable digest equals the one measured in the ARM64 workload:
`1c1c73f12456ce048f09d3180dbf121a266c5f8f4968161d21b806100a098a63`.

| Measurement | AMD64 | ARM64 |
|---|---:|---:|
| Duration | 600.55 s | 600.21 s |
| Actual page paints after switches | 1,050 | 1,050 |
| Different remote pixel hashes | 150 | 150 |
| Switch paint latency p95 | 30.83 ms | 27.83 ms |
| Whole-client-container peak memory | 369.50 MiB | 305.11 MiB |
| Mean container CPU, percent of one core | 32.48 % | 31.69 % |

Ten periodic remote input tokens were received by the actual server on each
architecture. Three PTY and 150 WebKit JavaScript roundtrips also passed.
The independent review included the ARM64 remote capture. The merged implementation
matches the tested head in `native`, `installer`, `system`, `scripts`, `tests`,
workflow and package files; only milestone documentation differs.

Performance moves from three to four points, raising the total from 78 to 79.
The graphical Pi-image milestone remains separate and uncounted here.
