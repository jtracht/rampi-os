# Embedded Rust RDP software acceptance

Development branch: `codex/embedded-rdp`. Physical hardware tests are excluded.
This evidence does not establish Windows 11 Pro/NLA or Pi decoding performance.

The actual Rampi connection page embeds the existing RDW GTK4 widget using
IronRDP. It does not launch FreeRDP or create another application window.
The source is pinned and carries its original licenses and documented local
integration fixes in `vendor/rdw/README.rampi.md`.

Command from the checkout, after a native build:

```
python tests/rust/test-rdp.py --image rampi-rust-rdp --server-image rampi-rdp-fixture
```

The fixture runs two disposable containers on a private internal Docker network.
The server runs actual XRDP, PAM authentication, an Xorg server desktop and xterm.
The client runs as UID 1000 using labwc/headless/Pixman, GTK/Cairo and Wayland,
under a 1 GiB memory limit. X11 remains on the test server only. The client has
one GTK application window and no Xorg process.

Passed locally on 2026-10-23:

* Incorrect SHA-256 certificate pin rejects the connection before credentials.
* Correct pin authenticates and receives real remote frames.
* Physical scan-code keyboard events traverse Wayland, RDW and RDP. The server
  writes receipts `rampirdp0` and `rampirdp1`; this is not a local text echo.
* Ctrl+Alt+Home returns to Dashboard while the RDP connection remains active.
* Explicit disconnect and reconnect retain the server session.
* Killing the actual server connection returns the page to a usable login form.
* No password appears in the captured application log or process arguments.
* No GTK critical or Rust panic occurs.

Markers: `RAMPI_RUST_RDP_BAD_CERTIFICATE_OK`,
`RAMPI_RUST_RDP_EMBEDDED_RECONNECT_OK`, `RAMPI_RUST_RDP_SERVER_FAILURE_OK`,
`RAMPI_RUST_RDP_SERVER_RECEIPTS_OK`.

Evidence is in `artifacts/rust-rdp/`, including the screenshot, client/server
logs and server keyboard receipts. The isolated test may report missing optional
click-audio playback; actual click playback remains covered by the full suite.

Dynamic remote resizing is disabled: an early headless resize produced an
IronRDP display-control encoding error. The established desktop is scaled by GTK.
The fixed upstream initial desktop is 1920×1080. Configurable initial resolution,
mouse/clipboard integration acceptance, Windows NLA and integrated Moonlight
streaming remain open. No additional progress point is awarded before the
complete native regression and ARM64 checks pass.
