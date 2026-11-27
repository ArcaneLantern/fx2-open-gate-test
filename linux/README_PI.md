# FX2 open gate dongle (Raspberry Pi Zero 2 W)

A pocket box that applies the FX2 3840x2560 open gate when you plug the camera in. No Mac, no phone. LOCAL build, 2026-11-26.

It runs the kit's own one-connection apply (`fx2_batch.py og2560`: read-only check, then L13 H5 L16 L19 S16), unchanged.
Nothing is written unless the check in that same connection says READY for an ILME-FX2 1.01. RAM only: a battery pull returns
the camera to stock.

## Parts (about 65 x 30 x 15 mm stacked)

| Part | Why |
|---|---|
| Raspberry Pi Zero 2 W (no headers) | runs the kit |
| PiSugar 3 (1200 mAh, USB-C charging, pogo pins, power button) | battery under the Pi, same footprint, 8-10 h |
| microSD 16 GB+ | the OS |
| Short USB-C (male) to micro-USB (male) **data** cable, 10-15 cm | camera to the Pi's **USB** port (not PWR) |

Any USB-C to micro-USB data cable works: the installer forces the Pi's port into host mode, so no special OTG cable is needed.

## One-time setup (about 20 minutes)

1. Raspberry Pi Imager: **Raspberry Pi OS Lite (64-bit)**. In its settings: hostname `fx2gate`, user `pi`, your Wi-Fi, SSH on.
2. Boot the Pi once (on Wi-Fi), then on the Mac: `linux/deploy_to_pi.sh` (or `linux/deploy_to_pi.sh user@host`).
3. `ssh pi@fx2gate.local sudo reboot` (first install only: host mode needs it).
4. On the camera, once: USB Connection Mode = **Mass Storage**. If the menu has **USB Power Supply**, set it **Off** so the camera
   does not charge from the Pi's small battery.

After a kit update: run `linux/deploy_to_pi.sh` again.

## Every shoot (about 30 s)

1. Pi on (PiSugar button). Wait for the green LED's short blink every 3 s (about 25 s after power-on).
2. FX2: battery out 10 s, dial on **STILL**, power on.
3. Plug the cable into the camera.
4. Wait for the LED to go **solid** (about 10-20 s). Unplug.
5. Dial to MOVIE, shoot. Do not power the camera off (that clears it).

| Green LED | Meaning |
|---|---|
| short blink every 3 s | ready, no camera |
| slow blink | camera seen, waiting for it as a USB drive (pick Mass Storage if the camera asks) |
| fast blink | applying, do not unplug |
| solid | DONE |
| 3 blinks, pause | STOPPED, nothing more written: unplug, battery out 10 s, plug in again |

## When it stops

- Most common: the camera still holds a result from an earlier session (the power switch does not clear it). Battery out 10 s and
  plug in again.
- Logs and the camera's session folders: `linux/fetch_results.sh` copies them to `windows/camera_private_pi/` on the Mac.
- On the Pi: `journalctl -u fx2-opengate -f`, logs in `/var/log/fx2-opengate/`.

## Files

- `opengate_dongle.py` the service: watches USB (sysfs, read-only), runs the apply once per plug-in, drives the LED
- `install_pi.sh` runs on the Pi: libusb, venv with the kit's pinned packages, host mode, service
- `deploy_to_pi.sh` / `fetch_results.sh` run on the Mac
- `fx2-opengate.service` the systemd unit

Tested so far: the service's plug-in, failure and wrong-mode paths with a simulated USB tree, its startup offline check with the real
pinned libraries, and that the pinned packages have aarch64 Linux wheels. Not yet tested: on a real Pi with the camera.
