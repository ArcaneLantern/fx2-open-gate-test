#!/bin/bash
# Runs on the Mac. Copies this kit to the Pi and installs the dongle service there.
#   linux/deploy_to_pi.sh                 (Pi at pi@fx2gate.local)
#   linux/deploy_to_pi.sh user@host
# The Pi's own results (windows/camera_private) are never overwritten or deleted. Re-run after every kit update.
set -euo pipefail
HOST=${1:-pi@fx2gate.local}
KIT="$(cd "$(dirname "$0")/.." && pwd)"
echo "Copying the kit to $HOST:/opt/fx2-opengate/kit ..."
ssh "$HOST" 'sudo mkdir -p /opt/fx2-opengate/kit'
rsync -a --delete --rsync-path="sudo rsync" \
  --exclude '.git' --exclude '.venv' --exclude 'android' --exclude 'macos/FX2 Open Gate.app' --exclude 'macos/menubar' \
  --exclude 'windows/camera_private' --exclude '__pycache__' --exclude '.DS_Store' \
  "$KIT/" "$HOST:/opt/fx2-opengate/kit/"
echo "Installing on the Pi ..."
ssh -t "$HOST" 'sudo bash /opt/fx2-opengate/kit/linux/install_pi.sh'
