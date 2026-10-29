# Software completion follow-up — 29 October 2026

This is development evidence, not a complete release or Raspberry Pi hardware
certification. The accepted score remains **91/95 (95.8%)**. The published,
independently verified image remains **v0.6.0-dev.5**; dev.6 is not published.

## Explicit Windows test boundary

The user authorized isolated GitHub-CI Windows component checks. Personal
computers and external Windows test hosts remain excluded. The integration
script refuses execution outside the disposable GitHub-hosted Windows runner
for this repository. Its profile/key/service changes must never be run locally.

The real Windows component job passed in
[CI 40829754253](https://github.com/jtracht/rampi-os/actions/runs/40829754253),
source `12e70937c03677740256cccb4305b5713d541f83`:

- The normal installer rejects the unsupported Server edition. Only the explicit
  existing `AllowNonTarget` diagnostic switch permits the component fixture.
- WhatIf preserves RDP configuration; the actual installer starts the official
  OpenSSH service. Repeating it preserves the existing SSH configuration bytes.
- The official sshd validates its configuration. RDP is enabled with NLA and a
  private-network firewall rule.
- Two actual nonadministrator Windows users receive separate Userenv profiles
  and native OpenSSH keys. Both loopback SSH logins return their actual SIDs.
- The other user's key is explicitly rejected. Each user reads their own
  synthetic private file and receives UnauthorizedAccess for the other file.
- The fixture restores its original SSH configuration and removes only its own
  captured user SIDs. Secret profiles/keys remain private in the disposable VM;
  they are not uploaded.

The subsequent actual Windows run
[40834696904](https://github.com/jtracht/rampi-os/actions/runs/40834696904), source
`596c149f9a1120707507ae5ef43726f0ba214dff`, additionally passed the complete general
CI and these real authentication checks:

- Microsoft's installed RDP ActiveX client imports the actual system type library
  through the installed Microsoft SDK. It requires server authentication and
  CredSSP; certificate validation is not bypassed.
- The existing listener's public certificate is temporarily trusted only inside
  the elevated disposable VM. Only the fixture's own addition is removed.
- OnLoginComplete is followed by a server-side remote-interactive logon with the
  expected actual Windows SID.
- A generated incorrect password produces a real Security event 4625 for the
  fixture account, status `0xc000006d`, substatus `0xc000006a`, logon type 3.
  The client is explicitly cancelled **after that observed server denial**.
  A client deadline alone remains a failure. Original audit policy is restored.

The downloaded result was independently checked using frozen copies of the
checker and both test scripts from that exact commit. The checked-out installer
and test hashes match the actual downloaded JSON and successful GitHub job.
The independent result is retained locally under
`artifacts/windows-final-ci-596c149/accepted.json`.

`scripts/check-windows-components.py` verifies the exact source revision and
installer/test SHA256 hashes in the downloaded JSON. A deliberately mismatched
revision is rejected. These are Windows **component** results; complete Rampi
acceptance remains false. Windows Server component tests do not certify an
actual Windows 11 Pro host. The earlier conservative aggregate authentication
flag is corrected in the follow-up producer; named authentication assertions and
the actual Windows failure record already passed in the independently frozen run.

## Native input and interaction work

The keyboard parser now matches the existing compositor's handling of vertical
tab as C-locale whitespace. Local actual labwc startup and the GTK settings/RDP
layout checks passed with this fixture. Custom values remain preserved.

Settings controls now retain their native GTK Button semantics, labels, sizing,
keyboard actions and accessibility. Cairo paints the shared asymmetric edge
shape already used by the dashboard. The first visual experiment exposed
clipping within GTK CSS padding; moving spacing to GTK child margins corrected
the actual rendered surface. The unsuccessful original captures are retained.

Subsequent actual Wayland screenshots, taken during real keyboard navigation,
showed independent movement on all four settings-control edges (1303/792/52/47
changed contour pixels in the local padding-corrected run). The dashboard's
existing four-edge checks and settings keyboard/page navigation also passed.
A subsequent local run also passed with 1544/1175/62/57 changed pixels and
separate captures proving that both the personal and system-wide GTK reduced
motion preferences freeze the contour. Hidden choice-list setup no
longer triggers selection sounds.

These are component proofs. Current source must still pass final native CI on
both architectures and a fresh release image before publication.

## Remaining complete-area acceptance

1. Real virtual Bluetooth HID keyboard/mouse reports through the kernel input
   path, including reconnect/forget and isolation.
2. Complete input/layout edge cases through that same actual input path.
3. Integrate the now verified native Windows component evidence after final
   source-bound CI; personal and external Windows hosts remain excluded.
4. Complete interaction/accessibility/performance review across supported sizes.

No AI integrations, model calls, physical tests, external Windows host or new
recurring task is introduced by this work. No additional score is claimed.
