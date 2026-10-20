#!/bin/bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
revision="$(cat "$root/image/pi-gen-revision")"
version="$(sed -n 's/^__version__ = "\([^"]*\)".*/\1/p' "$root/client/rampi/__init__.py")"
work="$root/.tools/pi-gen-build"
if [[ ! "$revision" =~ ^[a-f0-9]{40}$ || -z "$version" ]]; then exit 1; fi
if [[ -e "$work" ]]; then
    echo "Vorhandener Build-Pfad $work. Für einen neuen Build einen sauberen Checkout verwenden." >&2; exit 1
fi
git clone --branch arm64 https://github.com/RPi-Distro/pi-gen.git "$work"
git -C "$work" checkout --detach "$revision"
mkdir -p "$work/stage-rampi/00-rampi/files/source"
git -C "$root" archive HEAD | tar -x -C "$work/stage-rampi/00-rampi/files/source"
cp "$root/image/stage-rampi/00-run.sh" "$work/stage-rampi/00-rampi/00-run.sh"
cp "$root/image/stage-rampi/prerun.sh" "$work/stage-rampi/prerun.sh"
chmod +x "$work/stage-rampi/00-rampi/00-run.sh"
chmod +x "$work/stage-rampi/prerun.sh"
touch "$work/stage2/SKIP_IMAGES" "$work/stage-rampi/EXPORT_IMAGE"
cat > "$work/config" <<EOF
IMG_NAME='rampi-os-rpi3bplus-v$version'
PI_GEN_RELEASE='Rampi OS development candidate'
RELEASE='trixie'
ARCH='arm64'
TARGET_HOSTNAME='rampi'
FIRST_USER_NAME='pi'
FIRST_USER_PASS=''
DISABLE_FIRST_BOOT_USER_RENAME=0
PASSWORDLESS_SUDO=0
ENABLE_SSH=0
ENABLE_CLOUD_INIT=0
LOCALE_DEFAULT='de_DE.UTF-8'
KEYBOARD_KEYMAP='de'
TIMEZONE_DEFAULT='Europe/Berlin'
DEPLOY_COMPRESSION='xz'
STAGE_LIST='stage0 stage1 stage2 stage-rampi'
EOF
cd "$work"
./build-docker.sh
mkdir -p "$root/artifacts/image"
find deploy -maxdepth 1 -name '*.img.xz' -exec cp '{}' "$root/artifacts/image/" \;
shopt -s nullglob
images=("$root"/artifacts/image/*.img.xz)
if ((${#images[@]} != 1)); then echo 'Genau ein Image erwartet.' >&2; exit 1; fi
xz -t "${images[0]}"
printf '%s\n' "$revision" > "$root/artifacts/image/pi-gen-revision.txt"
cp "$root/packaging/readiness.json" "$root/artifacts/image/readiness.json"
sha256sum "${images[0]}" > "$root/artifacts/image/SHA256SUMS"
