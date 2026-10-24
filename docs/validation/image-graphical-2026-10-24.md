# Graphical acceptance of the installed Pi image

The new image validator starts the candidate's original Pi kernel, initramfs and
installed Rust workstation under the QEMU `raspi3b` machine with 1 GiB and four
virtual CPUs. It verifies actual greetd/wlgreet/PAM login, wrong-password rejection,
two isolated Linux accounts, visible native frames and return to the greeter.

The first image attempts reached the native boot probe, but failed before login.
Protocol-only diagnostics identified the exact error: wlgreet 0.5 requests
`wl_pointer` even when no pointing-device capability has existed. The image's
wlroots 0.20 compositor correctly rejects that request. The original USB error
did not, by itself, establish this cause.

The headless fixture now represents the designated keyboard and mouse through
the existing `wtype` virtual keyboard and `wlrctl` virtual pointer before starting
the real greeter. Login navigation uses actual Wayland keyboard events. This
does not modify wlgreet, weaken PAM or claim USB/physical-driver coverage.
The greeter's upstream dependency on a seat having had a pointing device remains
a documented limitation for a completely pointer-free physical setup.

The compressed original image is checksum-verified before and after the test.
Only a disposable decompressed copy receives official test-input packages,
ephemeral accounts, a test service and headless compositor backend settings.
No workstation executable, assets, launcher, user unit or greeter shortcut
profile is replaced. These installed files are hashed and checked in the guest
after both logins. The original native binary is additionally bound to its
SHA-256 and image producer revision. No generic Debian application install is
substituted for the image's installed workstation.

QEMU's watchdog limitation requires disabling only that peripheral in a temporary
DTB, as in the previous boot check. Physical Wi-Fi, Bluetooth, HDMI and hardware
video decoding remain excluded. Test support is not added to the published image.

## Accepted software evidence

[Image validation 40038000565](https://github.com/jtracht/rampi-os/actions/runs/40038000565)
passed using validator source `5df16f78f8fa0005a0e789c3392454e6ba38b14c`.
Image producer: `bd2a8b70e8bebe812e3491643b776ecc9d4a6847`;
compressed image SHA256:
`68714c83944a5a12de963a21a6eff84a125b88b0ee161289a0e6b656ff94c2f2`.
The installed executable SHA256 is
`42d40c8ab83c796966b547da552b04e1270794172721e088d1c28fab7a5d2837`.

Downloaded image and package checksums, ELF architecture and provenance were
independently checked. Downloaded graphical evidence passes
`check-image-login-evidence.py` with explicit expected source and image hash.
Both normal identities (UID 1001/1002), profile ownership/mode 0700, visible
native frames, wrong-password rejection, logout, unchanged installed files and
synced guest exit code zero are verified. The compressed original remains unchanged.
The final validator waits for an actually responding, visibly painted greeter,
including dynamically numbered Wayland displays after logout.

[Combined native CI 40038006072](https://github.com/jtracht/rampi-os/actions/runs/40038006072)
passed on AMD64 and ARM64, including fresh graphical login and ten-minute mixed
workload. The merged implementation has the exact tested Git tree. Systemimage
therefore moves from three to four points; the total is 80/100. This is a
development candidate. `regular_release` remains false.
