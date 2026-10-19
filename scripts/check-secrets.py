import json
import sys
from pathlib import Path

results = json.loads(Path(sys.argv[1]).read_text())["results"]
if results:
    # Never print the potential secret itself.
    raise SystemExit("Potential secrets detected in: " + ", ".join(sorted(results)))
print("No potential secrets detected by detect-secrets.")
