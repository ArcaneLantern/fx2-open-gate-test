"""FX2 (ILME-FX2) firmware 1.01: apply, or put back, the open-gate state in the camera's MEMORY.

  python fx2_apply.py apply    [--no-screen] [--no-meta] [--dry-run] [--no-movie-session]
  python fx2_apply.py putback  [--no-screen] [--dry-run]
  python fx2_apply.py screen | screen-putback  [--dry-run]
  python fx2_apply.py test1 | test2 | test3 | test4  [--dry-run]       (second and third kit, 2026-11-26: the diagnostic ladder)
  python fx2_apply.py squeeze  [--dry-run]             (the squeezed open gate: ran on an FX2, 2026-11-26)
  python fx2_apply.py test5 | test6 | og2560 | test7  [--dry-run]      (fourth kit, 2026-11-26: the path to a true 3840x2560 file)
  python fx2_apply.py putback-2560 | putback-hold  [--dry-run]         (put back og2560 / test7 without a cold boot)

The FX2 counterpart of fx3_apply.py (the FX3 kit, which records open gate on two FX3s). The FX2 is the A7 IV's sensor (IMX710 class)
on the A7C II's platform, so its open-gate steps are the A7 IV kit's (its default state since 2026-11-18, true 3840x2560 files of the
whole 3:2 sensor area in XAVC HS 4K and XAVC S 4K at 24p, with the MP4 header fix since 2026-11-24), ported to the FX2 1.01 and
checked against the FX2's own code in emulation. NOTHING OF THIS KIT HAS RUN ON AN FX2.

  apply    five steps, each its own USB session: L13 raw write buffer (dmmwb4688_fx2_v1), L5 sensor side (ogsq_fx2_v1), L16 output size
           (outsz2560_fx2_v1), L19 encoder side with the MP4 headers (ogfile2560_hs_s_fx2_v2), S16 rear screen at 3:2 with the focus frames
           and the camera's own De-Squeeze Display set for the 3:2 picture (lcd32dsq_fx2_v1). Afterwards: XAVC HS 4K or XAVC S 4K at
           23.98p only. With --no-screen only the first four; with --no-meta the encoder step without the MP4 header heights (N19).
           A step that finds its bytes already applied says NOTHING TO DO and counts as passed.
  putback  the reverse: S17, L20, L17, L6, L14 (with --no-screen the last four). A cold boot (battery out for 10 seconds) also undoes everything.
  screen / screen-putback   only the screen step (S16) or its put back (S17).
  test1    SECOND KIT (2026-11-26), after the first FX2 test: every step applied, but entering MOVIE ended in the coprocessor's forced
           exception "FW: S-Ele Refresh ng force exception" (0x507da0: a stage still busy for 11 frames, the A7 IV's F662 signature) and a
           restart. Test 1 = L13 + B5 (fhband_fx2_v1, the A7 IV's fhband_v1, F658): the sensor in the same full-height mode as L5, but the
           stage keeps its stock 16:9 height. Then one read-only dump on MOVIE (sensor mode, the memory manager's workspace: which write
           buffer was opened, and at what size).
  test2    L13 + L5 only (the A7 IV's two-step squeezed baseline, F682): the 4,688-row stage, no output-size, encoder or screen step. Then
           one read-only dump on MOVIE, or, if the camera restarts, after the restart (the kprint record and the snapshot image's head).
           Tests start from a cold boot on STILL. To undo: battery out for 10 seconds.
  test3    THIRD KIT (2026-11-26), after test 2 worked on the FX2 (steady picture, clips recorded, sensor column 5, the 4,688-row stage with the
           whole 7008x4672 window, L13's 33,003,520-byte write buffer in use): L13 + L5 + L16, the output size. Then the dump on MOVIE (v3 reads the
           saved output records: size, format code, type) or, after a restart, the crash record.
  test4    L13 + L5 + L16 + L19: test 3 and the encoder side (the full open gate without the screen step).
  squeeze  L13 + L5 + S16 (a tester's pull request, 2026-11-26; ran on an FX2): test 2 plus the screen step. The file is 3840x2160 holding the
           whole 3:2 sensor area squeezed 27/32 vertically; the 3:2 rear screen shows it at its true shape. No output-size or encoder step.

  FOURTH KIT (2026-11-26). Test 3 crashed on the FX2: L16 is the first failing step (on the A7 IV it never crashed). Read from the FX2's
  code and emulated (build/emu_rcinput_fx2.py): its resize set-up 0x51fbc0 raises the first-scaler size it hands the second scaler to at
  least the output size (0xbd3a32; only the FX2 and the A1 II have that code). With L16 that is 4336x2560, while L5's records make the
  first scaler give 4336x2438. The A7 IV's design for a 4336x2560 first scaler, ogh2560_v1 (F712, F713), is ported as H5 and takes L5's place.
  test5    L13 + H5: the taller first-scaler picture with the stock output size. Expected: what test 2 gives (squeezed 3840x2160 clips).
  test6    L13 + H5 + L16: plus the output size. Expected: a steady picture; a recording may stop after about a second, because the
           encoder is still set for 2,160 rows (the A7 IV did that at this stage, F688).
  og2560   L13 + H5 + L16 + L19 + S16: THE 3840x2560 PATH. Expected: clips of 3840x2560 with 2,560 real rows, the 3:2 rear screen filled.
  test7    L13 + L5 + F16 + L16 + L19, THE FALLBACK, for the case that test5 does not run: F16 is one code word that makes the resize
           set-up keep the records' first-scaler size, so the second scaler enlarges 2,438 rows to 2,560 as on the A7 IV. No screen step.
  For all four: SteadyShot Off (with Active the FX2 asks the first scaler for more rows still), APS-C/Super 35 Off, S&Q and Proxy off.

There is no preview-key routine in this kit: the FX2's own De-Squeeze Display (Off, 1.3x, 2.0x on 1.01) is kept, and S16 sets its ratios
for the 3:2 picture.

The closing session (apply and screen): one read-only dump taken with the switch on MOVIE, so that the first FX2 results show the sensor
in its full-height mode and the rear panel's type. Nothing is written in that session.

Rules it keeps:
- It starts only if the newest saved read-only check of this kit says VERDICT READY.
- It stops at the first step that does not end in DONE or NOTHING TO DO, and says what state that leaves.
- Each step is one pinned library; the runner (fx2_run.py) refuses any other bytes.
Nothing is written to a firmware file or to the camera's settings. What is written lives in the running camera's memory. A cold
boot (battery out for 10 seconds) removes it. Whether the power switch alone does is not known on the FX2 (on the A7 IV it does not,
on the A7S III it does), so keep the FX2 switched on from the first step to the last.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "CT1_usb_first_contact"))
sys.path.insert(0, str(HERE))
import ct1_common as c  # noqa: E402
import fx2_run  # noqa: E402

FIRMWARE = fx2_run.FIRMWARE
STEPS = {"apply": ("L13", "L5", "L16", "L19"), "putback": ("L20", "L17", "L6", "L14"), "screen": ("S16",), "screen-putback": ("S17",),
         "test1": ("L13", "B5"), "test2": ("L13", "L5"), "test3": ("L13", "L5", "L16"), "test4": ("L13", "L5", "L16", "L19"),
         # squeeze (2026-11-26, a tester's pull request; ran on an FX2): test 2 plus the screen step. The file is 3840x2160 holding the whole 3:2
         # sensor area squeezed 27/32 vertically, and the 3:2 rear screen shows it at its true shape. No output-size or encoder step.
         "squeeze": ("L13", "L5", "S16"),
         # fourth kit (2026-11-26): the path to a true 3840x2560 file (H5 = ogh2560_fx2_v1 in L5's place), and the fallback (F16)
         "test5": ("L13", "H5"), "test6": ("L13", "H5", "L16"), "og2560": ("L13", "H5", "L16", "L19", "S16"),
         "test7": ("L13", "L5", "F16", "L16", "L19"),
         "putback-2560": ("S17", "L20", "L17", "H6", "L14"), "putback-hold": ("L20", "L17", "F17", "L6", "L14")}
TESTS = ("test1", "test2", "test3", "test4", "squeeze", "test5", "test6", "og2560", "test7")
FOURTH = {"test5": "the taller first-scaler picture (4336x2560) with the stock output size. Expected: what test 2 gives, a steady picture and squeezed 3840x2160 clips.",
          "test6": "test 5 plus the output size 3840x2560. Expected: a steady picture; a recording may stop after about a second (the encoder is still set for 2,160 rows).",
          "og2560": "the path to a true 3840x2560 file: raw write buffer, the sensor side with a 4336x2560 first scaler, output size, encoder side, rear screen. "
                    "Expected: clips of 3840x2560.",
          "test7": "the fallback: the squeeze design with one code word that keeps the first-scaler size, then output size and encoder side. Expected: clips of 3840x2560 "
                   "(2,438 rows enlarged, as on the A7 IV). Run it only if test 5 does not give a picture."}
RUNNER = HERE / "fx2_run.py"
LISTER = HERE.parent / "CT1_usb_first_contact" / "ct1_stage2_service.py"
STILL = "STILL (the Still/Movie switch on STILL)"
MOVIE = "MOVIE (the Still/Movie switch on MOVIE; File Format XAVC HS 4K or XAVC S 4K, 24p)"


def say(text=""):
    print(text, flush=True)


def sessions():
    """Saved sessions of this kit, newest first: (folder, manifest)."""
    root = c.PRIVATE_ROOT
    out = []
    if root.is_dir():
        for folder in sorted((p for p in root.iterdir() if p.is_dir() and p.name.startswith("CT6_")), reverse=True):
            try:
                out.append((folder, json.loads((folder / "manifest.json").read_text(encoding="utf8"))))
            except (OSError, ValueError):
                continue
    return out


def last_check():
    """The newest saved read-only check of this kit that fetched a result: (folder name, ready?) or None. A check that stopped before the
    camera answered (no driver yet, no camera seen, an old result on the RAM disk) says nothing and is skipped. A check made with another
    kit (the FX3's fx3read, the A7S III's s3read, the ZV-E1's zvread) does not count: its header is not this helper's."""
    for folder, man in sessions():
        res = man.get("results", {})
        f = (res.get("ct6", {}).get("result") or {}).get("s3")
        if res.get("which") in ("check", "dump") and f:       # a dump makes every check the check makes, and gives the same verdict
            current = any(v in f.get("header", "") for v in ("fx2read_v1 ", "fx2read_v2 ", "fx2read_v3 ", "fx2read_v4 ")) and "ILME-FX2 1.01" in f.get("header", "")
            return folder.name, current and bool(f.get("ready")) and not f.get("identity_differs")
    return None


def last_result_sha():
    """The SHA-256 of the result the newest session fetched: the runner deletes a result left on the RAM disk only if it has this hash."""
    for _, man in sessions():
        try:
            return man["results"]["ct6"]["result"]["sha256"]
        except (KeyError, TypeError):
            continue
    return None


def usb_state():
    r = subprocess.run([sys.executable, "-I", "-B", str(LISTER), "--list"], capture_output=True, text=True, encoding="utf8", errors="replace", cwd=str(LISTER.parent))
    import re
    m = re.search(r"libusb sees: (\d+) Sony mass-storage device\(s\).*?, (\d+) Sony service device\(s\)", r.stdout)
    if not m:
        return "other"
    return "drive" if int(m.group(1)) == 1 and int(m.group(2)) == 0 else "service" if int(m.group(2)) else "other"


def wait_for_drive(first, timeout=600):
    asked, end = False, time.time() + timeout
    while usb_state() != "drive":
        if not asked:
            say()
            if first:
                say("The camera is not showing as a USB drive. Turn it on with the switch on %s, connect USB (USB Connection Mode: Mass Storage)." % STILL)
            else:
                say(">>> Unplug the USB cable from the camera and plug it in again.")
                say(">>> Do NOT power the camera off or pull the battery: that would leave the steps half done.")
            say("Waiting for the camera (Ctrl+C to stop) ...")
            asked = True
        if time.time() > end:
            return False
        time.sleep(2)
    return True


def wait_for_replug(timeout=900):
    """Wait until the camera has been unplugged and shows up as a USB drive again. False on timeout."""
    end = time.time() + timeout
    while usb_state() != "other":                    # still plugged in, as a drive or in service mode
        if time.time() > end:
            return False
        time.sleep(1)
    while usb_state() != "drive":
        if time.time() > end:
            return False
        time.sleep(2)
    return True


def movie_session(test=None):
    """The closing read-only session, taken in movie mode: it shows the sensor in the open-gate mode and the panel type."""
    say()
    say("=" * 78)
    say("One more session, and it only READS: it records the sensor's state in Movie, the memory manager's state and the rear panel's type.")
    say(">>> 1. Unplug the USB cable.")
    say(">>> 2. Set %s." % MOVIE)
    if test:
        say("       Watch the rear screen for ten seconds. Write down: a picture? purple flashing? does the camera switch itself off and on?")
        say("       If there is a steady picture: press REC, record about five seconds, press REC again.")
        say("       If the camera restarts by itself: do NOT pull the battery. Wait until it is on again, leave the switch on MOVIE.")
    else:
        say("       Look at the rear screen for five seconds and remember what it shows (the whole 3:2 picture? anything wrong?).")
    say(">>> 3. Plug the USB cable in again, still on MOVIE (after a restart too; choose Mass Storage if the camera asks).")
    say(">>> Do NOT switch the camera off: that may remove the patch.")
    say("Waiting for the unplug and the replug (Ctrl+C to stop; the patch stays applied either way) ...")
    if not wait_for_replug():
        say("The camera did not come back as a USB drive. The steps are applied all the same.")
        return
    cmd = [sys.executable, "-I", "-B", str(RUNNER), "dump", "--go", "--firmware-shown", FIRMWARE]
    clear = last_result_sha()
    if clear:
        cmd += ["--clear-result", clear]
    rc = subprocess.run(cmd).returncode
    which, f = step_outcome()
    say()
    if rc or which != "dump" or not f:
        say("The read-only session did not finish. The steps are applied all the same.")
        return
    decoded = f.get("decoded") or {}
    column = (decoded.get("sensor_registers") or {}).get("closest_column")
    if column != fx2_run.FULL_HEIGHT_COLUMN:         # the open-gate 4K 24p mode reads the sensor with register column 5 (as on the A7 IV)
        say("NOTE: before this session the sensor was not in the full-height 4K 24p mode (register column %s, not %d)." % (column, fx2_run.FULL_HEIGHT_COLUMN))
        say("      Was the camera on MOVIE, at 4K 24p? If not: set it, replug, and run dump_info once more.")
    panel = (decoded.get("display") or {}).get("panel_types")
    if panel:
        say("The rear panel reports type %d (%s). Please send this folder: it settles the FX2's panel shape." % (panel["rear_0x19d98cc"], panel["rear_aspect"]))
    say(">>> Unplug USB now.")


def step_outcome():
    for _, man in sessions():
        f = man.get("results", {}).get("ct6", {}).get("result", {}).get("s3")
        return (man.get("results", {}).get("which"), f) if f else (None, None)
    return None, None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=sorted(STEPS))
    ap.add_argument("--dry-run", action="store_true", help="show the steps and what each would send; nothing is sent")
    ap.add_argument("--no-screen", action="store_true", help="with apply or putback: only the four open-gate steps, without the screen step")
    ap.add_argument("--no-movie-session", action="store_true", help="with apply or screen: leave out the closing read-only session in movie mode")
    ap.add_argument("--no-meta", action="store_true", help="with apply: the encoder step without the MP4 header heights (N19); the headers keep saying 3840x2160")
    a = ap.parse_args()
    steps = STEPS[a.what]
    if a.no_screen and a.what not in ("apply", "putback"):
        raise SystemExit("--no-screen goes with apply or putback. Nothing was sent.")
    if a.no_meta and a.what != "apply":
        raise SystemExit("--no-meta goes with apply (the put back L20 puts back either encoder step). Nothing was sent.")
    if a.no_meta:
        steps = tuple("N19" if k == "L19" else k for k in steps)
    with_screen = not a.no_screen
    if a.what in ("apply", "putback") and with_screen:
        steps = steps + STEPS["screen"] if a.what == "apply" else STEPS["screen-putback"] + steps
    applying = a.what in ("apply", "screen") + TESTS
    closing = a.what in ("apply", "screen") + TESTS
    for k in steps:                                  # every library must be the pinned one before anything starts
        name, sha, _ = fx2_run.WRITE_STEPS[k]
        p = fx2_run.S3 / name
        if not p.is_file() or c.sha256(p.read_bytes()) != sha:
            raise SystemExit("%s is missing or is not the pinned build. Nothing was sent." % name)
    say("FX2 1.01, %s: %d steps" % (a.what, len(steps)))
    for n, k in enumerate(steps, 1):
        say("  %d. %s  %s  (library %s...)" % (n, k, fx2_run.WRITE_STEPS[k][2], fx2_run.WRITE_STEPS[k][1][:16]))
    if closing and not a.no_movie_session:
        say("  then one read-only session (dump) on MOVIE: the sensor's state and the panel type for the first FX2 results. Nothing is written in it.")
    if a.dry_run:
        for k in steps:
            say()
            say("--- %s, what the session would send:" % k)
            r = subprocess.run([sys.executable, "-I", "-B", str(RUNNER), k, "--dry-run"], capture_output=True, text=True, encoding="utf8", errors="replace")
            say(r.stdout.rstrip() or r.stderr.rstrip())
        say()
        say("Dry run only: nothing was sent to any device.")
        return
    chk = last_check()
    if applying and (chk is None or not chk[1]):
        raise SystemExit("The newest saved read-only check of this kit %s. Run check_readonly first and get VERDICT READY. Nothing was sent."
                         % ("does not exist" if chk is None else "(%s) does not say READY" % chk[0]))
    say()
    say("This WRITES into the running camera's memory (not its firmware, not its settings).")
    if a.what in FOURTH:
        say("This is %s of the fourth kit (%s)." % (a.what, " + ".join(steps)))
        say("  %s" % FOURTH[a.what])
        say("  Why: with the output size 3840x2560 the FX2 hands its second scaler a first-scaler size of 4336x2560, and the earlier sensor step (L5)")
        say("  delivers 4336x2438: that was the crash of L13 + L5 + L16. %s" % ("H5 delivers 4336x2560." if "H5" in steps else "F16 keeps the size the records give."))
        say("  NOT YET RUN ON AN FX2. A restart is possible and harmless (the patch is gone after it). Each step writes nothing unless its bytes are")
        say("  exactly the stock bytes.")
        say("  Camera settings for this test: SteadyShot Off, APS-C/Super 35 Off, S&Q off, Proxy off, File Format XAVC HS 4K, 23.98p.")
    elif a.what in TESTS:
        say("This is %s of the diagnostic ladder. On the first FX2 test the whole apply worked, but MOVIE ended in a forced" % a.what)
        say("  exception and a restart. This test applies only %s, so that the result says which part the FX2 does not take." % " + ".join(steps))
        say("  A restart is possible and harmless (the patch is gone after it). Each step writes nothing unless its bytes are exactly the stock bytes.")
    elif applying:
        say("On the FX2 this state CRASHES on MOVIE entry (2026-11-25 and 2026-11-26: a forced exception and a restart to stock). The first failing")
        say("  step is L16 after L5. Use open_gate_squeezed (works) or the fourth kit's open_gate_3840x2560_test instead.")
        say("  Each step writes nothing unless its bytes are exactly the FX2 1.01 stock bytes.")
    else:
        say("It has to follow an apply of this kit.")
    say("A cold boot (battery out for 10 seconds) returns the camera to stock. Whether the power switch alone does on the FX2 is not known:")
    say("so KEEP THE CAMERA SWITCHED ON from now until the script says it is finished.")
    if a.what == "apply" or a.what in TESTS:
        say("Before you go on: the switch on %s, a charged battery," % STILL)
        say("and a camera that was cold booted and has not been on MOVIE or S&Q since. (If it starts on MOVIE: set the switch to STILL,")
        say("pull the battery for 10 seconds, put it back and switch on.) Step L13 changes the memory manager and needs that state.")
        say("(If the open-gate state is already applied in this power-on, its steps will say NOTHING TO DO: that is fine.)")
    else:
        say("Before you go on: a charged battery, and the switch on %s." % STILL)
    if input("Firmware version in the camera's menu: ").strip() != FIRMWARE:
        raise SystemExit("Not %s. Nothing was sent." % FIRMWARE)
    if input("Type YES to write to the camera's memory: ").strip() != "YES":
        raise SystemExit("Not confirmed. Nothing was sent.")
    for n, k in enumerate(steps, 1):
        if not wait_for_drive(n == 1):
            raise SystemExit("The camera did not show up as a USB drive. Stopped before step %d (%s)." % (n, k))
        say()
        say("=" * 78)
        say("Step %d of %d: %s, %s" % (n, len(steps), k, fx2_run.WRITE_STEPS[k][2]))
        cmd = [sys.executable, "-I", "-B", str(RUNNER), k, "--go", "--writes-memory", "--firmware-shown", FIRMWARE]
        clear = last_result_sha()
        if clear:
            cmd += ["--clear-result", clear]
        rc = subprocess.run(cmd).returncode
        which, f = step_outcome()
        if rc or which != k or not f or not f.get("ok"):
            say()
            say("STOPPED at step %d (%s): %s" % (n, k, "the session did not finish" if rc or which != k or not f else "outcome " + f["outcome"]))
            say("Steps before it are %s. To be sure of the camera's state: cold boot it (battery out for 10 seconds)." % ("applied" if applying else "put back"))
            if k == "L13" and f and "nothing is written" in " ".join(f.get("problem_lines", []) + [str(f.get("outcome_line"))]):
                say("L13 refuses while the movie memory is still laid out the stock way: cold boot with the switch on STILL, then apply again.")
            say("Please send the newest folders in camera_private.")
            raise SystemExit(1)
    say()
    say("All %d steps passed (%s)." % (len(steps), a.what))
    if a.what == "apply":
        if a.no_meta:
            say("The files' MP4 headers say 3840x2160 (--no-meta): editors may open them squeezed; a remux to 3840x2560 fixes that.")
        else:
            say("The files' MP4 headers (tkhd, stsd, Sony's PROF) now say 3840x2560: editors should open them at 3:2 without a remux.")
            say("  Sony's XML (in the file and the sidecar) still says 3840x2160, 16:9.")
        say("In-camera playback: the FX2 opens playback with the A7 IV's decoder channel, which plays these clips on an A7 IV. Not tried on an FX2:")
        say("  if a clip says 'Unable to display', do NOT try again (on an FX3 a retry froze the camera); check the clips on a computer and report it.")
    if "S16" in steps:
        say("The screen step: on MOVIE the 3:2 rear screen should now be filled with the whole picture at its true shape. A circle should look round.")
        say("  The viewfinder (a 4:3 panel) keeps showing the picture squeezed, as on the A7 IV.")
        say("  De-Squeeze Display (in the menu's Display Option) now de-squeezes the 3:2 picture: 1.3x shows 1.95:1, 2.0x 3:1 (the whole frame;")
        say("  the stock centre crop is off). The file does not change. While it is applied every 16:9 picture is shown stretched to 3:2")
        say("  (other movie formats look wrong on the rear screen). Please report: the screen with De-Squeeze Display Off, 1.3x and 2.0x,")
        say("  and whether the focus and tracking frames sit on the subject.")
    if a.what in TESTS:
        if a.no_movie_session:
            say(">>> Unplug USB, set %s, then run dump_info on MOVIE (after a restart too)." % MOVIE)
        else:
            movie_session(a.what)
        say()
        say("Please send the newest folders in camera_private, and what the screen did on MOVIE: a picture (which shape?), purple flashing,")
        say("  a restart? If it recorded: the clip's properties (size, frame rate), or the clip. To return to stock: battery out for 10 seconds.")
        if a.what in ("og2560", "test7"):
            say("  For a clip of this test: the size MediaInfo shows (3840x2560 expected), whether it plays on a computer, and whether a recording")
            say("  stops by itself. In-camera playback is not tried on an FX2: if a clip says 'Unable to display', do NOT try again.")
        say("  Before the next test: battery out for 10 seconds, switch on with the switch on STILL.")
        return
    if closing:
        if a.no_movie_session:
            say(">>> Unplug USB, then set %s." % MOVIE)
        else:
            movie_session()
        say()
        say("Use only XAVC HS 4K or XAVC S 4K at 24p (23.98p) while it is applied: other 4K formats and frame rates are not set up and fail.")
        say("If the camera stops or restarts: do NOT pull the battery yet. Set the switch to STILL, replug USB and run dump_info, then send camera_private.")
        say("To return to stock: battery out for 10 seconds.")


if __name__ == "__main__":
    main()
