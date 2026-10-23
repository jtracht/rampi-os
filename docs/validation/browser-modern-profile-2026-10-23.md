# Native browser input, modern features and personal profile

Development branch: `codex/browser-acceptance`. No physical hardware is used.

The production WebKit page now explicitly persists cookies in the user's private
profile. Ctrl+L, F5, F11 and Escape support address navigation, reload and content
fullscreen. Web fullscreen uses the existing Rampi window and preserves the
fullscreen session. No additional window or browser engine is introduced.

Targeted local software acceptance passed with the actual GTK/WebKit application
under labwc/Wayland, a trusted local HTTPS server and a 1 GiB Docker memory limit:

* Real keyboard address navigation and page key input.
* Real compositor mouse motion, CSS hover and trusted button click.
* Canvas rendering, WebAssembly execution, Web Crypto digest, IndexedDB and CSS Grid.
* Browser fullscreen and DOM-requested fullscreen entered by a real user key;
  Escape restores controls and the existing GTK window stays fullscreen.
* Actual page reload retains localStorage, expiring secure cookies and IndexedDB.
* A second application process loads the same persistent profile successfully.
* A second Linux account is denied access to the first account's cookie database;
  its own application process starts with empty cookies, localStorage and IndexedDB.
* Existing HTTPS hostname rejection, history, inline dialogs, download/upload
  consent and one-window checks still pass.

The Docker fixture creates the standard root-owned `/tmp/.X11-unix` directory
normally supplied by systemd tmpfiles, so independent labwc sessions can initialize
their lazy compatibility sockets. No Xorg/Xwayland process is required or launched.

New required markers: `RAMPI_RUST_BROWSER_MODERN_INPUT_FULLSCREEN_OK`,
`RAMPI_RUST_BROWSER_PROFILE_RESTART_OK`, `RAMPI_RUST_BROWSER_OTHER_ACCOUNT_EMPTY_OK`.
The existing evidence checker requires these in addition to upload/download
markers. Full native regression passed on AMD64 and ARM64 in
[native run 40023113975](https://github.com/jtracht/rampi-os/actions/runs/40023113975).
[General CI 40023114019](https://github.com/jtracht/rampi-os/actions/runs/40023114019)
also passed. The downloaded artifacts were independently checked with
`check-native-evidence.py` on both architectures and `--require-installer` on ARM64;
the installer archives passed all seven checksum checks. Accepted head:
`196b9300f76a552cd0bd9090fc0ff5d66dc292af`, merged in PR #24 as `fc965e7`.
Browser moves from four to five points; the total moves from 76 to 77.
