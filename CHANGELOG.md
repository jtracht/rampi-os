# Changelog

## 0.6.0-dev.5 — published and independently verified keyboard follow-up

- Interpret duplicate personal keyboard-layout assignments consistently with
  labwc: the last assignment wins, including whitespace around the key/value.
- Use the same bounded, owner-checked configuration reader for the inline
  keyboard choices and Windows RDP layout. Preserve custom layouts and unrelated
  environment settings; do not silently display a different supported layout.
- Require an actual compositor startup check and GTK/RDP-selection checks.

The published dev4 image remains unchanged. The dev5 final-source, fresh-image
and independent public-download checks passed. Progress remains 91/95; one fixed
keyboard edge case does not complete all remaining input/HID requirements.

## 0.6.0-dev.4 — published and independently verified prerelease

- Complete German/English keyboard, display, host and board validation messages
  through the existing Fluent catalogs.
- Require each real PAM account to retain its own language and usable libc locale
  after logout and another login; inspect the actual systemd application process.
- Reuse one preservation-aware installer step for supported locale data, retaining
  other installed languages and system defaults, with real idempotence checks.
- Keep Linux first-account boot preparation off unsupported Windows hosts and
  provide the actual OpenSSL dependency in the Linux test container.

- Bound the cold personal-locale export at 30 seconds after reproducing the
  real three-second startup timeout in an isolated guest.

Final source CI on both architectures, the fresh image and both first-account
reboot procedures passed. Actual public downloads, checksums, sources and
licenses were independently verified. Software acceptance is now 91/95;
this remains a prerelease, with the documented remaining limits unchanged.

## 0.6.0-dev.3 — native development changes

- Restore the stock first-account setup before graphical login; reuse the existing
  PAM/keyring profile installer after the original account is renamed.
- Require first-account login, persisted keyrings and normal reboot for both the
  interactive wizard and the supported stock boot-file account configuration.
- Add personal German/English pages, inline choices and integrated browser
  microphone/camera decisions without additional windows.
- Extend Gitea to repository, organization and individual projects; retain
  read-only access and private offline caches.
- Add NLA-only software authentication checks with existing FreeRDP/WinPR and
  signed manual Tailscale installation through the existing vendor service.
- Assemble full native releases before creating a new tag, and independently
  verify the actual published files with the accepted source's validators.

This remains a prerelease. Physical hardware, Windows testhosts and model calls
are excluded; full Bluetooth HID acceptance remains open. Publication requires
the final source-bound CI, fresh image and complete artifact checks.

## 0.6.0-dev.2 — native development changes

Native Rust/GTK/Wayland now has three main modules. Direct AI integrations are removed.
Sunshine streaming stays inside the existing window, uses personal Secret Service
pairing and supports reconnect, keyboard, scaled mouse and scrolling through Moonlight.
The installer reuses compatible libraries and bundles corresponding C sources.
PAM/keyring and sustained streaming checks remain mandatory before publication.


## [0.5.0](https://github.com/jtracht/rampi-os/compare/v0.4.0...v0.5.0) (2026-10-20)


### Features

* add personal WLAN settings with NetworkManager and keyboard setup ([#14](https://github.com/jtracht/rampi-os/issues/14)) ([aa35263](https://github.com/jtracht/rampi-os/commit/aa3526377e775de51a88930d0325d7b035b55ac2))

## [0.4.0](https://github.com/jtracht/rampi-os/compare/v0.3.0...v0.4.0) (2026-10-20)


### Features

* add Kanban filters, personal VPN selection and streaming audio validation ([#12](https://github.com/jtracht/rampi-os/issues/12)) ([8926ed5](https://github.com/jtracht/rampi-os/commit/8926ed51eb0a7bb9907e288d9adddde4e42bf631))

## [0.3.0](https://github.com/jtracht/rampi-os/compare/v0.2.2...v0.3.0) (2026-10-20)


### Features

* graphical host profiles and persistent AI session management ([#9](https://github.com/jtracht/rampi-os/issues/9)) ([06ffbfc](https://github.com/jtracht/rampi-os/commit/06ffbfc2b279ea0d64870ed63243f8f99b67f0b9))


### Bug Fixes

* wait for RDP certificate generation before pinning the test server ([#10](https://github.com/jtracht/rampi-os/issues/10)) ([323e184](https://github.com/jtracht/rampi-os/commit/323e1841e4a3da0980a079408f66f240d453e8b0))

## [0.2.2](https://github.com/jtracht/rampi-os/compare/v0.2.1...v0.2.2) (2026-10-20)


### Bug Fixes

* isolate streaming credentials and validate real WireGuard connections ([b937932](https://github.com/jtracht/rampi-os/commit/b937932a655e9dda2fc1125cd5aef8fa655577bf))

## [0.2.1](https://github.com/jtracht/rampi-os/compare/v0.2.0...v0.2.1) (2026-10-20)


### Bug Fixes

* constrain preview headings to their panel width ([1a8c2f5](https://github.com/jtracht/rampi-os/commit/1a8c2f53019f4c13d2dcd780f6b0f7ebf8f21d53))
* readable dashboard typography and protected installed code ([241e5ce](https://github.com/jtracht/rampi-os/commit/241e5cef442c2b431394358db2e8f38e8d3ebed8))

## [0.2.0](https://github.com/jtracht/rampi-os/compare/v0.1.0...v0.2.0) (2026-10-20)


### Features

* add ARM64 container acceptance and verified VPN and streaming dependencies ([d19be97](https://github.com/jtracht/rampi-os/commit/d19be976bc6d0db46be0e253d623de9c29e85c6f))
* add guided setup and native UI navigation verification ([c2abcff](https://github.com/jtracht/rampi-os/commit/c2abcffad20a16453896229429d2e0ab86f8687f))
* add verified standalone installers and real terminal previews ([07b8fb7](https://github.com/jtracht/rampi-os/commit/07b8fb7354d62cd43907b142756c6620aeb86ec0))
* complete verified SSH enrollment and personal credential setup ([a1f3373](https://github.com/jtracht/rampi-os/commit/a1f3373012b7086fc712b60ae86bc7c61ac40fb6))
* deliver native Rampi workstation with installers and software validation ([95e964c](https://github.com/jtracht/rampi-os/commit/95e964c36f0086a180afc87464a718b95e61713b))
* implement native workstation client and system integration foundation ([c6d26aa](https://github.com/jtracht/rampi-os/commit/c6d26aa42517eaa82a9baa1916f1d0024dcb13eb))
* polish native module artwork and ship complete license and installation metadata ([e24e2c6](https://github.com/jtracht/rampi-os/commit/e24e2c6d8ebf1644980be33efdd1636708ad94e5))
* use native AccountsService and preserve image build artifacts for separate validation ([d365bf4](https://github.com/jtracht/rampi-os/commit/d365bf44cb39d1e84c746b565a995e8b241e6ae2))
* validate provider contracts and adopt software-only acceptance scope ([0b0fbe9](https://github.com/jtracht/rampi-os/commit/0b0fbe980741a75117bf4f9cd36b2ed245e22c57))
* validate VPN profiles with libnm and add software image boot tests ([74f0799](https://github.com/jtracht/rampi-os/commit/74f0799d4ca5f80425211ccd2ce8584328852524))
* verify native account authentication in disposable ARM64 containers ([2c873f0](https://github.com/jtracht/rampi-os/commit/2c873f0db0d442ea8066fb2c715137f24dafdbf0))


### Bug Fixes

* authorize native system operations and replace unsafe Windows adapter ACLs ([4a8468d](https://github.com/jtracht/rampi-os/commit/4a8468d9757daf13ebb295f92869a715ed68d995))
* classify the public acceptance document path correctly in secret scanning ([f75f957](https://github.com/jtracht/rampi-os/commit/f75f957a294ff98ccb52e9811a5dbddf50f12dfd))
* complete native session defaults and build releases from immutable commits ([dc38dbb](https://github.com/jtracht/rampi-os/commit/dc38dbb9af2c77122fa85cb6998c5e1b0142ed6f))
* isolate diagnostic image runs and preserve minimal reusable workflow permissions ([8ecdcf7](https://github.com/jtracht/rampi-os/commit/8ecdcf7f23b0130f76afce52621148020fac5812))
* isolate SSH test credentials and verify second-user authentication ([147d799](https://github.com/jtracht/rampi-os/commit/147d799f4725fb1674690e90687891087b0010ef))
* keep release and installer artifact versions consistent ([e622b85](https://github.com/jtracht/rampi-os/commit/e622b8556c8a55c50654960ac544e36fa151dea2))
* keep release, package and runtime versions identical ([2ba3a37](https://github.com/jtracht/rampi-os/commit/2ba3a3703b4e42cf4dc129eefc426bf9d8325c8d))
* make rootfs security checks fail closed ([d63664d](https://github.com/jtracht/rampi-os/commit/d63664d52fd4b3d534edd90a113d7a6673050bd0))
* reserve dashboard switching and keep streaming in the existing X11 session ([b530e5b](https://github.com/jtracht/rampi-os/commit/b530e5bb72916707278b35d95adddb379e30e15d))
* restrict secret scanner exception to the published dependency checksum ([890cb06](https://github.com/jtracht/rampi-os/commit/890cb063a6fad99b00e2080cbc275d86fe216333))
* reuse existing login and SSH services and record verified isolation boundaries ([6e3062e](https://github.com/jtracht/rampi-os/commit/6e3062eacac0a8ea81c12c536fccb15343d272eb))
* type the strict QML validation result collection ([518cd86](https://github.com/jtracht/rampi-os/commit/518cd8632d1f0faa4a4d8ad6b207dcdc7cdd2b56))

## Changelog

## Unreleased

- Native Qt-Quick-Dashboard-Struktur anhand der gelieferten Referenzen.
- Persönliche Konfiguration, asynchrone Systemadapter und bedarfsgerechte Module.
- Lesende Kanban-Adapter, Offline-Cache und Suche.
- Native Windows-CLI-Sitzungen über OpenSSH und vorhandenes psmux/ConPTY.
- Audit-/Installationsskripte, CI, Paketierung und pi-gen-Kandidatenworkflow.
- Reguläre Releasefreigabe bis zu dokumentierten Hardwaretests gesperrt.
