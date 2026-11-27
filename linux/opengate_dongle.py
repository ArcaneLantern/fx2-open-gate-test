#!/usr/bin/env python3
"""FX2 open gate dongle (LOCAL, 2026-11-26; not from the kit author). Runs on a Raspberry Pi Zero 2 W as a root systemd service.

Plug the FX2 (switch on STILL, fresh power-on, USB Connection Mode = Mass Storage) into the Pi: it runs the kit's one-connection
apply (fx2_batch.py og2560: the read-only check, then L13 H5 L16 L19 S16) once, shows the outcome on the Pi's green LED, and
waits for the camera to be unplugged before it will run again. Nothing is written unless the check in that same connection says
READY for an ILME-FX2 1.01 (fx2_batch's own rule). RAM only: a battery pull returns the camera to stock.

LED (the Pi's own green ACT LED):
  short blink every 3 s      ready, no camera
  slow blink (1 s)           camera seen, waiting for it to show as a USB drive (pick Mass Storage on the camera if it asks)
  fast blink                 applying: do not unplug (about 10-20 s)
  solid on                   DONE: unplug, set MOVIE, shoot. Do not power the camera off
  3 blinks, pause, repeat    STOPPED: nothing more was written. Unplug, battery out 10 s, plug in again

Only stdlib here; the camera is talked to by the kit's own fx2_batch.py, unchanged.
"""
import argparse
import datetime
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

SONY_VID = "054c"
FX2_MSC_PID = "0f47"                       # ILME-FX2 as a USB drive (Mass Storage)
SERVICE_PIDS = ("02a9", "0336")            # the camera in service mode (only mid-apply)

HERE = Path(__file__).resolve().parent
KIT = HERE.parent
BATCH = KIT / "windows" / "tools" / "camera_tests" / "CT6_memory_read_check" / "fx2_batch.py"


# ------------------------------------------------------------------ LED

class Led:
    """Drives the ACT LED from a pattern name in a background thread. No LED found = patterns only go to the log."""

    PATTERNS = {                           # (on seconds, off seconds) repeated
        "ready": [(0.08, 2.92)],
        "waiting": [(0.5, 0.5)],
        "busy": [(0.08, 0.08)],
        "done": [(1.0, 0.0)],
        "error": [(0.15, 0.2), (0.15, 0.2), (0.15, 1.2)],
        "off": [(0.0, 1.0)],
    }

    def __init__(self, path):
        self.dir = Path(path) if path else None
        self.pattern = "off"
        self._lock = threading.Lock()
        if self.dir and self.dir.is_dir():
            try:
                (self.dir / "trigger").write_text("none")
            except OSError:
                pass
        threading.Thread(target=self._run, daemon=True).start()

    def set(self, name):
        with self._lock:
            if name != self.pattern:
                log("led: %s" % name)
            self.pattern = name

    def _write(self, on):
        if self.dir:
            try:
                (self.dir / "brightness").write_text("1" if on else "0")
            except OSError:
                pass

    def _run(self):
        while True:
            with self._lock:
                steps = self.PATTERNS[self.pattern]
            for on, off in steps:
                if on:
                    self._write(True)
                    time.sleep(on)
                if off:
                    self._write(False)
                    time.sleep(off)


def find_led(override):
    if override is not None:
        return override or None
    for name in ("ACT", "led0"):
        p = Path("/sys/class/leds") / name
        if p.is_dir():
            return str(p)
    return None


# ------------------------------------------------------------------ USB (sysfs, read-only)

def sony_devices(sysfs):
    """[(product id, path)] of every Sony USB device the kernel lists. Reads sysfs only; sends nothing to the camera."""
    out = []
    root = Path(sysfs)
    for dev in root.glob("*"):
        try:
            if (dev / "idVendor").read_text().strip().lower() == SONY_VID:
                out.append(((dev / "idProduct").read_text().strip().lower(), dev.name))
        except OSError:
            continue
    return out


def wait_until(pred, timeout=None, step=0.5):
    end = None if timeout is None else time.time() + timeout
    while not pred():
        if end is not None and time.time() > end:
            return False
        time.sleep(step)
    return True


# ------------------------------------------------------------------ main loop

LOGFILE = None


def log(text):
    line = "%s %s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), text)
    print(line, flush=True)
    if LOGFILE:
        try:
            with open(LOGFILE, "a") as f:
                f.write(line + "\n")
        except OSError:
            pass


def prune(private, keep):
    """Keep the newest `keep` session folders of the kit (the apply writes one per run), so the SD card never fills."""
    if not private.is_dir():
        return
    folders = sorted((p for p in private.iterdir() if p.is_dir() and p.name.startswith("CT6_")), reverse=True)
    for old in folders[keep:]:
        subprocess.run(["rm", "-rf", str(old)])


def apply_once(args):
    cmd = args.command or [sys.executable, "-I", "-B", str(BATCH), "og2560", "--go", "--firmware-shown", "1.01"]
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = Path(args.log_dir) / ("apply_%s.log" % stamp)
    log("applying: %s (output in %s)" % (" ".join(cmd[-4:]), out_path))
    t0 = time.time()
    with open(out_path, "w") as out:
        try:
            r = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT, timeout=args.apply_timeout,
                               cwd=str(BATCH.parent))
            code = r.returncode
        except subprocess.TimeoutExpired:
            code = "timeout"
    log("apply finished: %s in %.1f s" % ("OK" if code == 0 else "STOPPED (%s)" % code, time.time() - t0))
    return code == 0


def main():
    global LOGFILE
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sysfs", default="/sys/bus/usb/devices", help="where to look for USB devices (tests use a fake folder)")
    ap.add_argument("--led", default=None, help="LED sysfs folder; empty string = no LED (default: ACT or led0)")
    ap.add_argument("--log-dir", default="/var/log/fx2-opengate")
    ap.add_argument("--apply-timeout", type=int, default=240)
    ap.add_argument("--drive-timeout", type=int, default=120, help="seconds to wait for the camera to show as a USB drive")
    ap.add_argument("--keep", type=int, default=60, help="session folders to keep in camera_private")
    ap.add_argument("--once", action="store_true", help="handle one plug-in, then exit (tests)")
    ap.add_argument("--command", nargs=argparse.REMAINDER, help="run this instead of fx2_batch (tests)")
    args = ap.parse_args()

    Path(args.log_dir).mkdir(parents=True, exist_ok=True)
    LOGFILE = str(Path(args.log_dir) / "dongle.log")
    led = Led(find_led(args.led))
    log("FX2 open gate dongle started (kit %s)" % KIT)

    if not args.command:
        led.set("busy")
        r = subprocess.run([sys.executable, "-I", "-B", str(BATCH), "og2560", "--dry-run"], capture_output=True, text=True,
                           cwd=str(BATCH.parent))
        if r.returncode != 0:
            log("offline checks FAILED, will not touch any camera:\n" + (r.stdout + r.stderr)[-2000:])
            led.set("error")
            while True:
                time.sleep(3600)
        log("offline checks passed (every library pinned, simulated batch ran)")

    def present():
        return bool(sony_devices(args.sysfs))

    def is_drive():
        devs = sony_devices(args.sysfs)
        return any(pid == FX2_MSC_PID for pid, _ in devs) and not any(pid in SERVICE_PIDS for pid, _ in devs)

    if present():
        log("a Sony device is already connected at start: waiting for it to be unplugged first")
        led.set("waiting")
        wait_until(lambda: not present())

    while True:
        led.set("ready")
        wait_until(present)
        log("camera connected: %s" % sony_devices(args.sysfs))
        led.set("waiting")
        if wait_until(is_drive, timeout=args.drive_timeout):
            time.sleep(1.5)                        # let the kernel finish binding the drive before the kit takes it over
            led.set("busy")
            ok = apply_once(args)
            prune(KIT / "windows" / "camera_private", args.keep)
        else:
            log("the camera never showed as an FX2 USB drive (Mass Storage) in %d s: nothing was sent" % args.drive_timeout)
            ok = False
        led.set("done" if ok else "error")
        # wait for a real unplug: no Sony device at all for 3 s (the camera re-enumerates on its own after the apply)
        while True:
            wait_until(lambda: not present())
            time.sleep(3)
            if not present():
                break
        log("camera unplugged")
        if args.once:
            return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
