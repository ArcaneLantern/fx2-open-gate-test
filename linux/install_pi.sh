#!/bin/bash
# Runs ON the Pi, as root (deploy_to_pi.sh calls it). Installs the FX2 open gate dongle:
#   - libusb + a Python venv with the kit's pinned packages (windows/requirements.txt)
#   - the Pi's micro-USB data port forced into USB HOST mode (dtoverlay=dwc2,dr_mode=host), so any USB-C to micro-USB cable works
#   - a systemd service that starts at boot and waits for the FX2
#   - a few boot-time trims (no Bluetooth, no splash) so the Pi is ready sooner
# Safe to re-run after every kit update. Reboot once after the first install (host mode needs it).
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "run as root (sudo)"; exit 1; }
BASE=/opt/fx2-opengate
KIT=$BASE/kit
[ -f "$KIT/linux/opengate_dongle.py" ] || { echo "kit not found in $KIT (run deploy_to_pi.sh from the Mac)"; exit 1; }

echo "== packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3-venv libusb-1.0-0 >/dev/null

echo "== python venv"
[ -x "$BASE/venv/bin/python" ] || python3 -m venv "$BASE/venv"
"$BASE/venv/bin/pip" install -q --disable-pip-version-check -r "$KIT/windows/requirements.txt"

echo "== USB host mode"
CFG=/boot/firmware/config.txt; [ -f "$CFG" ] || CFG=/boot/config.txt
REBOOT=0
if ! grep -qx 'dtoverlay=dwc2,dr_mode=host' "$CFG"; then
  cp "$CFG" "$CFG.before-fx2-opengate"
  sed -i '/^dtoverlay=dwc2/d' "$CFG"
  printf '\n[all]\n# FX2 open gate dongle: the data port is always a USB host\ndtoverlay=dwc2,dr_mode=host\n' >> "$CFG"
  REBOOT=1
fi
for line in 'dtoverlay=disable-bt' 'disable_splash=1' 'boot_delay=0'; do
  grep -qx "$line" "$CFG" || { echo "$line" >> "$CFG"; REBOOT=1; }
done
systemctl disable --now hciuart.service bluetooth.service >/dev/null 2>&1 || true

echo "== offline check of the kit (pinned libraries + simulated batch)"
"$BASE/venv/bin/python" -I -B "$KIT/windows/tools/camera_tests/CT6_memory_read_check/fx2_batch.py" og2560 --dry-run | tail -n 3

echo "== service"
install -m 644 "$KIT/linux/fx2-opengate.service" /etc/systemd/system/fx2-opengate.service
mkdir -p /var/log/fx2-opengate "$KIT/windows/camera_private"
systemctl daemon-reload
systemctl enable fx2-opengate.service >/dev/null
systemctl restart fx2-opengate.service
sleep 2
systemctl --no-pager --lines=5 status fx2-opengate.service || true

if [ $REBOOT -eq 1 ]; then
  echo; echo ">>> First install: reboot the Pi once (sudo reboot). After that the green LED blinks briefly every 3 s = ready."
else
  echo; echo ">>> Installed. Green LED: short blink every 3 s = ready for the FX2."
fi
