#!/bin/bash
# Runs on the Mac. Copies the Pi's apply logs and session folders into this kit (windows/camera_private_pi/), for bug reports.
#   linux/fetch_results.sh [user@host]
set -euo pipefail
HOST=${1:-pi@fx2gate.local}
KIT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$KIT/windows/camera_private_pi"
mkdir -p "$DEST/logs"
rsync -a --rsync-path="sudo rsync" "$HOST:/opt/fx2-opengate/kit/windows/camera_private/" "$DEST/"
rsync -a --rsync-path="sudo rsync" "$HOST:/var/log/fx2-opengate/" "$DEST/logs/"
echo "Copied to $DEST"
tail -n 8 "$DEST/logs/dongle.log" 2>/dev/null || true
