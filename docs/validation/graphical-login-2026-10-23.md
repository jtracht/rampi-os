# Graphical native login with greetd, wlgreet and PAM

Physical hardware tests are excluded. This test uses the actual existing login
services and the production Rampi session launcher in an isolated Debian QEMU VM.
It does not replace PAM or simulate a successful login response.

The guest has 1 GiB RAM, four emulated CPUs, headless labwc/Pixman and emulated
keyboard/mouse input through the ordinary libinput/logind path. No host device
is forwarded. The greeter and the authenticated application use separate native
Wayland sessions. Xorg/Xwayland processes are not needed.

Locally observed:

* A fresh unprepared Debian guest reached the greeter, rejected an incorrect
  password, started the actual Rust application as two distinct ordinary Linux
  accounts and returned to the greeter after each application closed.
* The final instrumented development rerun additionally checked the PAM rejection
  in the system journal, actual executable SHA-256, configuration ownership/mode,
  and that Ctrl+Alt+Home cannot start Rampi under the greeter account.
* The development rerun is deliberately not final evidence: the checker rejects
  its prepared/resumed flags. The fresh immutable CI runs on both architectures
  must pass before accepting the Linux-login milestone.

The test-only backend settings and fixture users are not installed on a real Pi.
The VM installs the same Rampi binary, assets, session scripts and user service;
its profile permissions match the real installer. Screenshots capture the actual
greeter and first-run setup page of each authenticated application.

Product change: the greeter has its own minimal labwc configuration and no
workstation-launch shortcut. Normal installs migrate only the unchanged legacy
Rampi profile, after verifying the recorded greetd configuration hash. Custom
greetd configurations, custom profiles and symlinked profiles remain untouched.
No extra compositor termination code is introduced: labwc's existing `-S`
session option already returns to greetd when Rampi exits successfully.

Repeat after building the native binary:

```sh
docker build -f tests/virtual/Dockerfile -t rampi-virtual-tools .
docker run --rm --memory=3g --memory-swap=3g --cpus=4 \
  -v "$PWD:/app" -v rampi-rust-build:/build:ro rampi-virtual-tools \
  python3 scripts/test-virtual-linux.py \
  --native-session-binary /build/target/debug/rampi-native --timeout 1800
python3 scripts/check-login-evidence.py artifacts/virtual-login
```

The evidence checker requires fresh guest flags, the 1 GiB/four-CPU budget,
all four executable markers, two ordinary authenticated identities, matching
guest/producer binary hashes, private configuration and three actual captures.
Sixteen negative/positive checker cases and Linux profile-migration cases protect
against stale binaries, wrong identities, missing rejection and changed profiles.

Remaining limits: this is a generic Debian VM, not the Raspberry Pi image or
physical HDMI/Bluetooth validation. A usable keyboard must be available to the
existing greeter; initial Bluetooth pairing and further account-management UI
are separate open work. A larger-window account screenshot does not certify
the supplied logo's login presentation or the final image boot experience.

## Accepted software evidence

The initial PR #26 captures were insufficient on ARM64: they showed the
compositor before GTK had painted the application. They are not the accepted
graphical proof. PR #27 waits for the mapped workstation and actual nonblank
pixels, and the independent checker rejects the old blank captures.

Accepted head: `356bd2024863ee29178b2ff04dd809383e44170e`; merged as `107b0be`.
[Native run 40030456947](https://github.com/jtracht/rampi-os/actions/runs/40030456947)
passed on AMD64 and ARM64; [general CI 40030456834](https://github.com/jtracht/rampi-os/actions/runs/40030456834)
also passed. Both downloaded graphical artifacts independently passed
`scripts/check-login-evidence.py`; the ARM64 frames were visually inspected.
Its executed binary SHA-256 is
`57946d53f0af39f4aff9bc9d7affd92b90d252874564c425e493dd896dae0843`.
The two session identities and configuration owners were UID 1001 and 1002,
with mode 0700. The guest was freshly created, not resumed or prepared.

This completes the Linux login software milestone at four points, raising the
total from 77 to 78. The image and longer mixed-workload milestones remain
separate and uncounted here.
