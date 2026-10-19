#!/bin/bash
set -euo pipefail
export QT_QPA_PLATFORM=xcb QT_QUICK_BACKEND=software
temporary="$(mktemp -d)"
export XDG_CONFIG_HOME="$temporary/config"
install -d -m 700 "$XDG_CONFIG_HOME" "$XDG_CONFIG_HOME/rampi"
printf '%s\n' '{"setup_complete":true}' > "$XDG_CONFIG_HOME/rampi/settings.json"
openbox --config-file "$(pwd)/system/openbox.xml" > "$temporary/openbox.log" 2>&1 &
wm_pid=$!
python3 -m rampi.app --windowed > "$temporary/client.log" 2>&1 &
client_pid=$!
other_pid=''
probe_pid=''
cleanup() {
    if [[ "${1:-0}" != 0 ]]; then
        cat "$temporary/openbox.log" "$temporary/client.log" >&2
        cat "$temporary/key-events.log" >&2 || true
        wmctrl -l >&2 || true
    fi
    kill "$client_pid" "$wm_pid" ${other_pid:+"$other_pid"} ${probe_pid:+"$probe_pid"} 2>/dev/null || true
    rm -rf -- "$temporary"
}
trap 'cleanup $?' EXIT
dashboard=''
for ((attempt=0; attempt<80; attempt++)); do
    dashboard="$(xdotool search --onlyvisible --name '^Rampi$' 2>/dev/null | head -1 || true)"
    if [[ -n "$dashboard" ]]; then break; fi
    if ! kill -0 "$client_pid" 2>/dev/null; then cat "$temporary/client.log"; exit 1; fi
    sleep 0.25
done
[[ -n "$dashboard" ]] || { cat "$temporary/client.log"; exit 1; }
xmessage -title 'RampiShortcutReceiver' -buttons close:0 'X11 shortcut test' > /dev/null 2>&1 &
other_pid=$!
other=''
for ((attempt=0; attempt<40; attempt++)); do
    other="$(xdotool search --onlyvisible --name '^RampiShortcutReceiver$' 2>/dev/null | head -1 || true)"
    if [[ -n "$other" ]]; then break; fi
    sleep 0.1
done
[[ -n "$other" ]]
timeout 10 xdotool windowactivate --sync "$other"
stdbuf -oL xev -id "$other" -event keyboard > "$temporary/key-events.log" 2>&1 &
probe_pid=$!
sleep 0.3
xdotool key --clearmodifiers ctrl+alt+Home
sleep 0.5
active="$(xdotool getactivewindow)"
if [[ "$active" != "$dashboard" ]]; then
    printf 'Dashboard shortcut failed: expected %s, active %s\n' "$dashboard" "$active" >&2
    cat "$temporary/key-events.log" >&2
    exit 1
fi
# X11 may deliver an unmatched key-up after ending a passive grab. Navigation
# is triggered by key-down; ensure that the reserved Home press never reaches it.
if awk 'BEGIN { RS="\n\n" } /KeyPress event/ && /keysym 0xff50, Home/ { found=1 } END { exit !found }' "$temporary/key-events.log"; then
    echo 'Reserved Home key press was forwarded to the other application.' >&2; exit 1
fi
echo 'PASS: native Qt/X11 window started; Openbox globally selected the exact dashboard and intercepted the reserved shortcut.'
