#!/bin/sh
# Shared installer for disposable Linux test images, never a personal host.
set -eu
test "${RAMPI_FIXTURE_BUILD:-}" = 1
expected='2026.914.233613-1+debiantrixie'
installed=$(dpkg-query -W -f='${Version}' sunshine 2>/dev/null || true)
if [ -n "$installed" ]; then
    test "$installed" = "$expected"
    exit 0
fi
case "$(dpkg --print-architecture)" in
    amd64) digest=a86f858cbae57f60ecebd445402ee0295c1c057b857bd45d44c2ea2d255cbbfb ;;
    arm64) digest=45f250a6bae3629bd67d6856356e5d838569fbe4f6128440124c727a3d5fef5e ;;
    *) exit 1 ;;
esac
package=$(mktemp /tmp/rampi-sunshine.XXXXXX.deb)
trap 'rm -f "$package"' EXIT HUP INT TERM
curl -fL "https://github.com/LizardByte/Sunshine/releases/download/v2026.914.233613/sunshine_2026.914.233613-1%2Bdebiantrixie_$(dpkg --print-architecture).deb" -o "$package"
printf '%s  %s\n' "$digest" "$package" | sha256sum -c -
apt-get install -y "$package"
