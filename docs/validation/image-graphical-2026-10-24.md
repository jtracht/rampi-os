# Graphical acceptance of the installed Pi image

The new image validator starts the candidate's original Pi kernel, initramfs and
installed Rust workstation under the QEMU `raspi3b` machine with 1 GiB and four
virtual CPUs. It verifies actual greetd/wlgreet/PAM login, wrong-password rejection,
two isolated Linux accounts, visible native frames and return to the greeter.

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

Implementation and evidence guards are present; the actual image workflow
results and independent artifact review remain pending. Systemimage remains
three points until the complete software acceptance succeeds.
