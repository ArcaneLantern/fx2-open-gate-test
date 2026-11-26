# FX2 open gate: test kit (firmware 1.01)

<p><b>Third kit (2026-11-26): test 2 works; tests 3 and 4 next.</b> Test 2 (raw write buffer + sensor step) runs on the FX2: steady picture, clips recorded, the whole sensor height in the picture. So the crash of the full apply comes from the output-size or the encoder step. Please run <code>test2_squeeze_only</code> once more (its dump now reads the output records), then <code>test3_output_size</code>, then <code>test4_output_size_encoder</code> (see "The diagnostic tests"), and send the folders. This kit ports the open gate that works on the A7 IV to the Sony FX2 (ILME-FX2) firmware 1.01. It records a true 3840 × 2560 picture of the whole 3:2 sensor area at 23.98p and makes the MP4 headers say 3840 × 2560. It also fills the FX2's 3:2 rear screen with the whole picture, and sets the FX2's own De-Squeeze Display for it. The patch only writes to the camera's memory.</p>

**Where it stands (2026-11-26):**

- **First FX2 test (2026-11-25, issue #1).** Every step applied and read back on the camera: raw buffer, sensor, output size, encoder and screen. The USB route, the read-only checks and the macOS launchers all work on the FX2.
  - **The failure.** Entering MOVIE gave a purple flash, then the image processor stopped itself and the camera restarted, with the patch gone. This happened four times, also without the screen step.
  - **What the crash record says.** The code at 0x507da0 prints "FW: S-Ele Refresh ng force exception" and stops on purpose when a stage of the picture pipeline is still busy after 11 frames. That is exactly what the A7 IV did before its raw write buffer was enlarged (its F662/F667). This kit's first step enlarges that buffer, so something else on the FX2 is still in the way. We cannot tell what from the record.
  - **Read on the camera:** rear panel type 3 (3:2), viewfinder type 2 (4:3).
- **Test 2 works (2026-11-26).** L13 + L5 only, on MOVIE: a steady picture, no restart, and two clips recorded (HEVC 3840 × 2160 4:2:2 10-bit, 23.98p; the picture is the whole sensor height, squeezed into 16:9, as on the A7 IV).
  - The dump on MOVIE: sensor in its full-height mode (register column 5), the stage the whole 7008 × 4672 window, the stored record as designed, and the raw write buffer in use at 33,003,520 bytes (the enlarged one).
  - So the full-height read-out, the enlarged buffer and the squeeze all work on the FX2, and **the crash of the full apply comes from L16 (output size) or L19 (encoder)**. The FX6 kit's bisection points the same way (its L16).
  - What the firmware shows: the FX2 chooses each output's buffer by its picture size. It has an output kind the A7 IV lacks, with a small fixed buffer, and at 3840 × 2560 some format codes would not fit the 13,271,040-byte buffers. The camera's own output records tell which applies: the dump now reads them.
- **Third kit: tests 3 and 4** (and test 2 again for the output records). Each applies part of the kit and then reads the camera's state on MOVIE (see "The diagnostic tests").
  - The read-only dump also reads the image processor's memory manager (which write buffer it opened, and at what size), and the first pages of the image it saves when it crashes.
  - The full apply is unchanged; please run the tests first.
- **Built and emulated.** Every step was checked against the FX2 1.01 firmware's own files and code (Unicorn), and every library was run against a model FX2 (`PORT_NOTES.md`).
- **Why it should work.** The FX2 has the A7 IV's sensor:
  - the same video modes (plus two the A7 IV lacks);
  - the same sensor tables and register matrix;
  - the same stored records for every mode the two share, from the FX2's own calculator.

  Its image processor is the A7C II's newer build of the same software. On the A7 IV these steps record a true 3840 × 2560 file in XAVC HS 4K and XAVC S 4K, with MP4 headers that DaVinci Resolve opens at 3:2.
- **The shape of the kit is the FX3 kit's** (`fx3-open-gate-test`, which records open gate on two FX3s): the same launchers, the read-only check before any write, the closing read-only session, Windows, macOS and Android.
- **One step more than the FX3 kit:** the raw write buffer. The FX2's movie raw write buffer holds the stock 16:9 read-out only (7040 × 3958). A full-height read-out needs 4,688 rows, as on the A7 IV, so step 1 enlarges it.
- **No playback step.** The FX2 opens movie playback the A7 IV's way (its 8K decoder channel), and the A7 IV plays its own 3840 × 2560 clips. So in-camera playback should work, but it has not been tried (see "While it is applied").

**What it does.** A true 3840 × 2560 (3:2) recording in XAVC HS 4K and XAVC S 4K at 23.98p, set in the camera's memory only. A battery pull removes it.

**Kits cannot be mixed up.** The FX3, A7S III and ZV-E1 kits' check libraries say NOT READY on an FX2. This kit's check says NOT READY on an A7 IV, an A7C II or an FX3. Every write step writes nothing unless each byte it changes holds exactly the FX2 1.01 stock value. All of this was checked in emulation.

| Launcher | What it does | Writes to the camera? |
|---|---|---|
| `check_readonly.cmd` | Confirms the camera runs the 1.01 software the port was made from and reads what every patch site holds. Verdict READY / NOT READY | No |
| `dump_info.cmd` | The same, plus facts for the port: memory map, the camera's own logs, sensor register state, internal tables, the memory manager's records, the display (panel type, fit word, frame tables, de-squeeze words) | No |
| `open_gate_apply.cmd` | Applies the default state in five steps: raw write buffer, sensor, output size, encoder (with the MP4 headers), then the rear screen at 3:2 with De-Squeeze Display set for it. Ends with one read-only session | **Yes: memory only** |
| `open_gate_apply_no_screen.cmd` | Only the four open-gate steps | **Yes: memory only** |
| `open_gate_apply_no_meta.cmd` | The default state with the encoder step that leaves the MP4 headers at 3840 × 2160 | **Yes: memory only** |
| `open_gate_putback.cmd` | Puts the five steps back | Yes: memory only |
| `screen_putback.cmd` | Puts the screen step back | Yes: memory only |
| `test1_fullheight_band.cmd` | **Diagnostic test 1** (second kit): raw write buffer + full-height sensor read-out with the stock 16:9 picture, then one read-only dump on MOVIE | **Yes: memory only** |
| `test2_squeeze_only.cmd` | **Diagnostic test 2** (second kit): raw write buffer + the full-height sensor step only, then one read-only dump on MOVIE. **Works on the FX2** | **Yes: memory only** |
| `open_gate_squeezed.cmd` | **Squeezed open gate** (ran on an FX2, 2026-11-26): raw write buffer + full-height sensor step + rear-screen step, then one read-only dump on MOVIE. A 3840 × 2160 file holding the whole 3:2 sensor area squeezed 27/32 vertically (stretch the height by 32/27 in the editor); the rear screen shows it at 3:2. No output-size or encoder step | **Yes: memory only** |
| `test3_output_size.cmd` | **Diagnostic test 3** (third kit): test 2 + the output size (3840 × 2560), then one read-only dump on MOVIE | **Yes: memory only** |
| `test4_output_size_encoder.cmd` | **Diagnostic test 4** (third kit): test 3 + the encoder side (the open gate without the screen step), then one read-only dump on MOVIE | **Yes: memory only** |

Nothing in this kit writes to the camera's firmware or to its settings.

## Before you start

1. The camera's menu must show **Ver. 1.01**. On any other version, stop and tell us the version.
2. **USB Connection Mode: Mass Storage.**
3. A charged battery. Do not record or play back while a step runs.
4. **The Still/Movie switch** on the FX2 chooses stills or movie. Below, "STILL" and "MOVIE" mean the switch's two positions.

## Windows, once

1. Install Python 3.10 or later from python.org (with the "py launcher").
2. Run `windows/setup.cmd`.
3. Install the libusb-win32 driver for the camera with [Zadig](https://zadig.akeo.ie): Options, List All Devices, pick the camera, choose libusb-win32, Replace Driver. The first run switches the camera to service mode, where it shows up as a new device (054C:0336 on the other bodies): install the driver for that one too, then run the step again.

## macOS, once (ran with an FX2 on 2026-11-25)

The macOS kit is the A7 IV kit's macOS port, carried over unchanged apart from the launcher names. It runs the same scripts as Windows (`windows/tools`).

1. Python 3.9 or later: the one macOS offers with the Xcode Command Line Tools (run `xcode-select --install` in Terminal) works, or install it from python.org.
2. Double-click `macos/setup.command`. It sets up Python and the USB library the scripts use. No Homebrew and no driver are needed.
3. Each Windows launcher has a macOS twin with the same name: `macos/check_readonly.command`, `dump_info.command`, `open_gate_apply.command`, `open_gate_apply_no_screen.command`, `open_gate_apply_no_meta.command`, `open_gate_putback.command`, `screen_putback.command`, `test1_fullheight_band.command`, `test2_squeeze_only.command`, `test3_output_size.command`, `test4_output_size_encoder.command`, `open_gate_squeezed.command`. Everything below that says `.cmd` works the same with the `.command` file. (The first FX2 tester ran the macOS launchers: they work.)

Each live run asks for your Mac password: macOS keeps its own driver on the camera's USB connection, and only an administrator can hand the camera over to the script. The script unmounts the camera's memory card first; it does not erase anything on it. The results go to the same `windows/camera_private` folder.

If macOS refuses to open a .command file ("unidentified developer" or "could not verify"), open System Settings > Privacy & Security, scroll down and click "Open Anyway". Or open Terminal, type `bash` and a space, drag the .command file into the window, and press Return.

## Android (not run on a phone or camera yet)

`android/FX2-OpenGate.apk` runs this kit from a phone connected to the camera by USB-C (or an OTG adapter). It carries exactly the files in `windows/tools` of this commit and runs them unchanged; only the USB access, the dialogs and the folder for the results are the phone's.

1. Install the APK (allow installing from unknown sources). It installs beside the A7 IV, A7S III and FX3 apps; they do not share anything on the phone.
2. Set the camera as for the PC (below), and also **USB Power Supply: Off**, or it charges from the phone.
3. **1. Read-only check** first: the apply starts only after a check on this phone said READY. Then **2. Apply to camera**. The "Screen step" box chooses between the five-step apply (ticked) and the four open-gate steps only.
4. When Android asks to open *FX2 Open Gate* for the camera, tick **Always** and press OK. It comes up twice: once in Mass Storage, once in service mode.
5. When the log says **unplug and plug in again**, do that with the phone cable. Never switch the camera off.
6. **Stop waiting** ends a wait for the camera. It never interrupts a step that is talking to the camera.
7. Afterwards, **Export logs** writes a zip to `Download/FX2-OpenGate/` on the phone: send that zip back.

**Test 1: band**, **Test 2: squeeze**, **Test 3: + output size** and **Test 4: + encoder** run the diagnostic tests (app 0.3); like the apply, they start only after a check on this phone said READY.

**Self-test** and **Dry run** need no camera and send nothing.

## The read-only steps

Each launcher asks for the firmware version the menu shows. Each run makes a new folder in `windows/camera_private`.

- **Check or dump in the stills state:** switch on STILL, connect, run the launcher.
- **Dump of the 4K state:** set File Format XAVC S 4K (or XAVC HS 4K) at 24p, S&Q off, APS-C/Super 35 off. Set MOVIE, record a few seconds, stop. **Stay on MOVIE**, connect, run `dump_info.cmd`.

What they do to the camera: they switch it to service mode, write one small program file to the service partition, which the camera loads once, and delete that file again in the same session. The program only reads and creates one file, its report, on the camera's RAM disk. Its source is `windows/tools/camera_tests/CT6_memory_read_check/helper_fx2/fx2read.c`.

## The diagnostic tests

The first test showed that the whole kit applies but the FX2 cannot run the result. These tests split it, as was done on the A7 IV. **Test 2 works on the FX2** (2026-11-26). Now please run, each from a cold boot: **test 2 again** (its dump now reads the camera's output records: their size, format code and kind), then **test 3**, then **test 4**. Test 1 is no longer needed.

| Test | Launcher | What it applies | The A7 IV did | If the FX2 runs it | If the FX2 crashes |
|---|---|---|---|---|---|
| 1 | `test1_fullheight_band.cmd` | raw write buffer; the sensor in the same full-height mode as the full kit, but the picture keeps the stock 16:9 band (so the pipeline's stage keeps its stock height) | a normal 16:9 picture and clip (F658) | the full-height read-out works; the dump shows which write buffer the camera opened, and its size | the FX2 does not take the sensor's full-height mode itself |
| 2 | `test2_squeeze_only.cmd` | raw write buffer + the full kit's sensor step, nothing else (no output size, encoder or screen step) | a squeezed 16:9 picture of the whole sensor height (F682) | **seen on the FX2 (2026-11-26)**: the problem is in the output-size or encoder step | the problem is in the taller stage (4,688 rows) |
| 3 | `test3_output_size.cmd` | test 2 + the output size: the picture the pipeline delivers becomes 3840 × 2560 | the picture stayed squeezed on the screen, and a recording stopped by itself after a second, because the encoder was still set for 2160 rows (F688) | the output size is fine; run test 4 | the output size is the problem (the dump of test 2 tells which buffer) |
| 4 | `test4_output_size_encoder.cmd` | test 3 + the encoder side | a true 3840 × 2560 file (F698) | the open gate works without the screen step; a clip is 3840 × 2560 | the encoder side, or its combination with the output size, is the problem |

**How to run each test**

1. Set File Format XAVC S 4K (or XAVC HS 4K) at 24p, APS-C/Super 35 off, S&Q off, Proxy off, De-Squeeze Display off.
2. Set the switch to STILL, pull the battery for 10 seconds, put it back and switch on. Do not go to MOVIE yet.
3. Connect USB (Mass Storage) and run `windows/check_readonly.cmd`: VERDICT READY.
4. Run the test's launcher. It asks for the firmware version and a typed YES, and runs two steps with a replug between them.
5. When it asks: **unplug, set MOVIE, watch the rear screen for ten seconds.**
   - **If there is a steady picture:** press REC, record about five seconds, stop.
   - **If the camera restarts by itself:** do not pull the battery; wait until it is on again and leave the switch on MOVIE.
6. **Plug in again** (choose Mass Storage if asked). The script runs the read-only dump by itself.
7. Write down what the screen did: a picture (its shape?), purple flashing, a restart?
8. Battery out for 10 seconds before the next test.

**Please send** the zipped `windows/camera_private` folder and, for each test, what the screen did. If a test recorded, add the clip or its properties.

## The write steps

**What they change.** Five groups of bytes in the running camera's memory, one per step:

1. **Raw write buffer** (4 words of the image processor's memory manager): the movie raw write buffer holds 4,688 rows instead of 3,958, enough for the full sensor height (the A7 IV's `dmmwb4688_v1`).
2. **Sensor** (11 table cells, the two 4K picture records, 31 bytes of the stored mode record): full sensor height instead of the 16:9 band, kept whole and squeezed into the stock 4K picture (the A7 IV's `ogsq_v3`).
3. **Output size** (one word): 3840 × 2160 becomes 3840 × 2560.
4. **Encoder** (101 + 6 sites): the encoder's tables for XAVC HS 4K and XAVC S 4K at 23.98p and 25p, and the two height values the MP4 writer puts in the file's headers, 2160 → 2560 (the A7 IV's `ogfile2560_hs_s_v2`). `open_gate_apply_no_meta.cmd` leaves the headers at 2160.
5. **Screen** (18 words):
   - the 16:9 live view fills the 3:2 rear screen (it holds the whole sensor area, so it is shown at its true 3:2 shape, as on the A7 IV);
   - the focus and tracking frames are told where the picture now is;
   - De-Squeeze Display's shapes are set for the 3:2 picture (below).

Each step first checks that every byte it is about to change holds its stock value, writes, reads back, and undoes its own writes if anything does not match. `open_gate_apply_no_screen.cmd` runs only the first four.

**De-Squeeze Display** (Sony's own feature, in the menu's Display Option; on 1.01 it offers Off, 1.3x and 2.0x). The camera works out each shape for a 16:9 picture. With the open-gate picture, which is 3:2, every shape would be about 18% off, so step 5 gives it the shapes of the 3:2 frame:

| Setting | Stock FX2, 16:9 picture | With this kit, the 3:2 open-gate picture |
|---|---|---|
| 1.3x | 2.31:1 | **1.95:1** |
| 2.0x | 2.67:1 (the centre 4:3 of the frame) | **3:1: the whole frame** (the centre crop is turned off) |

It changes only the preview, not the recorded file. The firmware also has 1.65x and 1.8x shapes, which the 1.01 menu never selects; they are set for the 3:2 picture as well (2.47:1, 2.7:1).

**What we do not know yet.** Everything on an FX2. The points that worry us most:

- **The vertical squeeze.** On the A7 IV, step 2 tells the scaler that the full-height picture is squeezed by 32/27, so it keeps the whole window. The FX2's scaler calculation is a newer revision of that code and was not run alone in emulation. If it does not act the same way, the file shows a 16:9 cut of the full-height picture instead of all of it. It would not crash.
- **The raw write buffer step** refuses while the movie memory is laid out the stock way. On the A7 IV it never is, after a cold boot with the camera on stills. The FX2 should be the same.
- **The power switch.** On the A7 IV switching off and on keeps the patch; on the A7S III it removes it. Not known on the FX2: keep it switched on during the apply.
- **The rear panel** is 3:2: the first test's dump read type 3 (viewfinder: type 2, 4:3).
- **Exposure, autofocus, long recordings, heat:** the sensor reads 18% more rows per frame.

**While it is applied**

- Use only XAVC HS 4K or XAVC S 4K at 24p (23.98p). Other 4K formats, frame rates, S&Q and APS-C/Super 35 are not set up and are likely to fail.
- On the rear screen every 16:9 picture takes the 3:2 shape, and De-Squeeze Display uses the 3:2 shapes, so other movie formats look wrong there. The viewfinder (a 4:3 panel) keeps the squeezed picture, as on the A7 IV. HDMI output is not part of this kit and has not been checked.
- **In-camera playback** should work (see above), but has not been tried on an FX2. If a clip says "Unable to display", **do not try again**: on an FX3 a second try froze the camera. Check the clips on a computer and tell us.

**How to run it**

1. In the menu, set File Format XAVC S 4K (or XAVC HS 4K) and 24p. APS-C/Super 35 off, S&Q off. De-Squeeze Display Off for now. Set Proxy Recording to Off.
2. Set the switch to STILL. Then pull the battery for 10 seconds and switch on, so that nothing of an earlier run is left. Do not go to MOVIE yet.
3. Connect USB and run `windows/check_readonly.cmd`. It must say VERDICT READY.
4. Run `windows/open_gate_apply.cmd`. It starts only if your newest saved check or dump says READY. It asks for the firmware version and for a typed YES.
5. It runs five steps. Between steps it asks you to **unplug and replug the USB cable. Do not switch the camera off and do not pull the battery** until the script says it is finished.
6. After the five steps the script asks for one more session, which only reads. **Unplug USB, set MOVIE, look at the screen, and plug in again.** The script then runs the read-only dump by itself and prints the rear panel's type.
7. When it says so, unplug. The rear screen should show the whole picture at 3:2.
8. Record 20 to 30 seconds and stop. Check the clip on a computer. Then try De-Squeeze Display at 1.3x and 2.0x.
9. To return to stock: battery out for 10 seconds, or `open_gate_putback.cmd`.

**If the camera restarts by itself** at any point: do not pull the battery. Set the switch to STILL, connect USB, run `windows/dump_info.cmd`, and only then pull the battery for 10 seconds. The image processor keeps its own log across a restart without power loss, and the dump reads it.

**Please send back**

- The zipped `windows/camera_private` folder, with the closing dump of the apply in it.
- The clip, or its properties: size, frame rate, codec. Do the same with XAVC S 4K if you can.
  - **Field of view:** a still photo of the same scene from a tripod, so we can see whether the clip has the whole sensor height.
  - **MediaInfo:** `mediainfo --Output="Video;%Width%x%Height% original %Width_Original%x%Height_Original%" FILE` should give 3840x2560 with no "original" size. ffprobe cannot show the header change: it reads the size from the stream.
  - **Editors:** whether Resolve or Premiere opens the original file at 3:2.
- The rear screen with De-Squeeze Display Off, 1.3x and 2.0x: a phone photo with something round in the picture helps.
- Whether the focus and tracking frames sit on the subject with De-Squeeze Display Off.
- **One check after a power-off.** When you are done: switch the camera off and on with the power switch (no battery pull), set STILL, run `windows/check_readonly.cmd`, and include that folder. It tells us whether the power switch removes the patch on the FX2.
- Your settings: file format and record setting, frame rate, NTSC or PAL, SteadyShot, Log shooting.

**If the camera misbehaves** (grey lines, flicker, restart, freeze, recording that stops by itself): do not pull the battery straight away if the camera still responds. Set STILL, connect USB, run `dump_info.cmd`, and send the folder. Then pull the battery for 10 seconds. If the camera does not respond at all, just pull the battery. `open_gate_apply_no_screen.cmd` applies open gate without the screen step.

**If the apply stops part-way:** it says at which step. Pull the battery for 10 seconds to be sure of the camera's state, and send the folder. If step 1 (raw write buffer) refuses, the camera was probably on MOVIE since it was switched on: battery out, switch on STILL, and run it again.

**To remove only the screen step:** set STILL and run `windows/screen_putback.cmd`.

## If something stops

Every stop prints a reason and "Nothing was sent" or what was sent. Please send that text. Common ones:

- *the camera is in service mode but that device has no libusb driver yet*: expected on the first run. Do the Zadig step for the new device and run again.
- *DeviceInfo.xml is not the file of the 1.01 update*: another firmware or model. Nothing further is sent.
- *DIFFERS from the 1.01 update* in a check: not an FX2 on 1.01 (an A7 IV, A7C II or FX3 gives this too). The apply will not start.
- *a libJit.so is already on the service partition*: a session broke half-way. Replug, and run the same step with `--remove-only`.

## What is in here

- `windows/`: the launchers, `setup.cmd`, and `tools/`:
  - the scripts, the pinned program files and their source;
  - the patch designs of every step;
  - the builders and emulations of the designs (`tools/modding/fx2`).
- `macos/`: `setup.command` and one `.command` launcher per Windows launcher; they run `windows/tools`.
- `android/FX2-OpenGate.apk`: the phone app, carrying `windows/tools` as published here.
- `PORT_NOTES.md`: how the A7 IV kit maps onto the FX2, what was checked and how, and what is not known.

Built on [Sony-PMCA-RE](https://github.com/ma1co/Sony-PMCA-RE) (vendored under `windows/tools/third_party`, MIT licence).
