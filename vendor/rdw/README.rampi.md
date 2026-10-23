# RDW source used by Rampi

Upstream: https://gitlab.gnome.org/malureau/rdw
Revision: `d7c38aed1c2cf4743833d587a9135744a745893f` (2026-09-02).
Only rdw4, rdw4-rdp and their build-time source dependencies are included.
RDW is MIT licensed; see LICENSE. Rampi's Apache-2.0 license does not replace
third-party licenses.

Build dependencies preserved from upstream submodules:

* cbindgen: https://github.com/elmarco/cbindgen,
  `0bb9eb6764a78929f3326187e0eef50287c41923`, MPL-2.0, source and license included.
* Generated key maps from https://gitlab.com/keycodemap/keycodemapdb,
  `320f92c36a80bfafc5d57834592a7be5fd79f104`. The generator permits either
  GPL-2.0-or-later or BSD-3-Clause for its output; Rampi uses BSD-3-Clause.
  See keycodemap/LICENSE.BSD and generated-file notices.

Local changes to the pinned source:

* Minimal workspace and explicit license-file package metadata.
* Failed/closed connection channels no longer panic during disconnect or
  cancellation; thread joins run through GIO's blocking pool, off the GTK loop.
* Connection and authentication stages have finite timeouts.
* TCP resolution uses a host/port tuple, including IPv6 addresses.
* Tracing skips the connection configuration, which contains credentials.

Rampi uses the existing GTK widget, IronRDP protocol implementation and GStreamer
audio. The client enables Wayland, without RDW's X11 feature. No USB device or
filesystem redirection backend is enabled for RDP. Clipboard synchronization is
provided by RDW. A SHA-256 certificate pin must be independently checked before
credentials are passed to the server.
