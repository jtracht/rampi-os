"""Actual GTK pages with an explicit SSH command-contract fixture; no provider auth claim."""
import os
import subprocess
import tempfile
from pathlib import Path

if os.environ.get("RAMPI_TEST_CONTAINER") != "1" or not Path("/.dockerenv").exists():
    raise SystemExit("Disposable container required")

with tempfile.TemporaryDirectory(prefix="rampi-ai-") as directory:
    root = Path(directory)
    state = root / "state"
    state.write_text("running")
    fixture = root / "ssh"
    fixture.write_text('''#!/usr/bin/python3
import base64,json,os,re,sys
from pathlib import Path
args=sys.argv[1:]
assert '-T' in args and 'BatchMode=yes' in args and 'StrictHostKeyChecking=yes' in args
assert args[args.index('-l')+1]=='alice' and 'windows.example' in args
script=base64.b64decode(args[-1]).decode('utf-16-le')
assert "-Project 'C:\\\\Work\\\\O''Brien'" in script
module=re.search("-Module '([a-z]+)'",script)[1]
action=re.search("-Action '([A-Za-z]+)'",script)[1]
assert module in ('codex','claude','antigravity') and action in ('Check','Stop')
state=Path(os.environ['RAMPI_TEST_AI_STATE'])
mode=state.read_text()
if mode=='denied': sys.exit(255)
if mode=='malformed': print('{broken'); sys.exit(0)
if action=='Stop': state.write_text('stopped'); sys.exit(0)
print(json.dumps(dict(schema=1,module=module,installed=module!='antigravity',multiplexer=True,running=mode=='running')))
''')
    fixture.chmod(0o700)
    result = subprocess.run(
        ["/build/target/debug/rampi-native", "--ai-ui-check"],
        env={
            **os.environ,
            "PATH": str(root) + ":" + os.environ["PATH"],
            "RAMPI_TEST_AI_STATE": str(state),
        },
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    assert "RAMPI_RUST_AI_SESSION_PAGES_OK" in result.stdout
    print(result.stdout.strip())
