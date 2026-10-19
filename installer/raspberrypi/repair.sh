#!/bin/bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
bash "$root/setup.sh" --check
echo 'Für eine ausdrücklich gewünschte Reparatur setup.sh --install ausführen.'
