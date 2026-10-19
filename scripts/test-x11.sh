#!/bin/bash
set -euo pipefail
export QT_QPA_PLATFORM=xcb QT_QUICK_BACKEND=software
temporary="$(mktemp -d)"
export XDG_CONFIG_HOME="$temporary/config"
mkdir -p -m 700 "$XDG_CONFIG_HOME/rampi"
printf '%s\n' '{"setup_complete":true}' > "$XDG_CONFIG_HOME/rampi/settings.json"
openbox --config-file system/openbox.xml > "$temporary/openbox.log" 2>&1 &
wm_pid=$!
python3 -m rampi.app --windowed > "$temporary/client.log" 2>&1 &
client_pid=$!
other_pid=''
probe_pid=''
cleanup() {
    kill "$client_pid" "$wm_pid" ${other_pid:+"$other_pid"} ${probe_pid:+"$probe_pid"} 2>/dev/null || true
    rm -rf -- "$temporary"
}
trap cleanup EXIT
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
xdotool windowactivate --sync "$other"
stdbuf -oL xev -id "$other" -event keyboard > "$temporary/key-events.log" 2>&1 &
probe_pid=$!
sleep 0.3
xdotool key --clearmodifiers ctrl+alt+Home
sleep 0.5
active="$(xdotool getactivewindow)"
if [[ "$active" != "$dashboard" ]]; then
    cat "$temporary/openbox.log"; echo 'Dashboard shortcut failed.' >&2; exit 1
fi
if grep -q 'keysym 0xff50, Home' "$temporary/key-events.log"; then
    echo 'Reserved Home key was forwarded to the other application.' >&2; exit 1
fi
echo 'PASS: native Qt/X11 window started; Openbox globally selected the exact dashboard and intercepted the reserved shortcut.'
