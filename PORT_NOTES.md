# Port notes: A7 IV 6.02 open gate → FX2 1.01 (in the FX3 kit's shape)

Everything here was read from the FX2 1.01 firmware update (`BODYDATA.DAT`, SHA-256 `7c12d1e4…9c9a`). Every step of the kit was emulated: Unicorn ran the FX2's own code where it mattered, and the built helper libraries ran against a model FX2. **On FX2s the squeezed open gate (issue #1, NTSC) and the true 3840 × 2560 open gate (issue #5, NTSC and PAL) work.**

The reference designs are the A7 IV's default open-gate state. It works on an A7 IV (2026-11-18 onwards): a true 3840 × 2560 file of the whole 3:2 sensor area in XAVC HS 4K and XAVC S 4K at 24p. Since 2026-11-24 its MP4 headers say 3840 × 2560 (Resolve opens the file at 3:2), and the 3:2 rear screen shows the picture with the focus frames. The kit's shape (launchers, the read-only check first, the closing dump, the FX2's own De-Squeeze Display kept and set for the 3:2 picture) is the FX3 kit's, which records open gate on two FX3s.

## First camera result (2026-11-25, issue #1) and the second kit (2026-11-26)

**What ran.** One tester, macOS launchers, firmware 1.01, read helper `fx2read_v1`. Evidence: `a7iv_map/evidence/fx2/tester_2026-11-25/`.
- Checks: READY every time.
- Every write step DONE with every site read back: L13, L5 (stored record of 0x8c0 found at 0x24de78c through the pointer chain), L16, L19 (101 + 6) and S16.
- L13 found no live division ("no unit of the present division exists"), also in a first run that had started on MOVIE.
- That first run's L19 stopped at the service login ("Invalid response: -65528") before anything was sent.

**What failed.** Switching to MOVIE gave a purple flash, then the coprocessor stopped itself and the camera restarted to stock. This happened four times, once without S16.

The kept kprint record is identical each time:
- task CAM_VD_SEQUENCE, data abort at pc 0x507dae, lr 0x507da1, DFAR 0;
- r1 0x190cfc4, r5 0x190cfc0;
- the stack holds 0x50806b, 0x527fab, 0x55f343 and the settings block 0x196aa58.

**Read statically from the FX2 1.01 image:**
- **The abort is deliberate.** 0x507d28 (called from 0x508048) asks 0xba2500(8, 5, 4), "still busy at sync 4", and counts frames in 0x190cfc0. At 11 it prints "FW: S-Ele Refresh ng force exception" (0x507e4c), clears the counters and stores to address 0.
  - This is the A7 IV's F662/F667 signature and the ZV-E1 first test's (whose crash record has the same register shape).
  - On the A7 IV the cause was the raw write buffer (fixed by `dmmwb4688_v1`, F679/F680), and on the ZV-E1 the same.
  - FX2's kprint keeps no lines before the abort (the A7 IV's kept the IsAnyValidForSync lines), and its boot log restarts at boot, so nothing tells which stage was busy.
- **The record was right.** The camera's stored record of 0x8c0 differs from the emulated one only in flag bytes (+0xe7, +0xef, +0x102, +0x11a, +0x153, +0x15b, +0x16e, …), none of them a design byte.
- **The write buffer's id.** It is chosen at run time by 0xbc557c, the A7 IV's 0xa1fefa line for line, into +0x3c0:
  - 0x43e (key 0x57f, enlarged by L13) by default;
  - 0x63d (key 0x704, 73.4 MB) under one condition;
  - **0x608 (key 0x6a3, 27,864,320 bytes = the stock 3,958 rows, not enlarged)** when setting byte 0x18f62d8+0x7d is 1.

  That byte reads 0 in every dump, because the camera core's settings block is zero during a USB session. Which id the FX2 uses in its 4K mode is not known.
- **The snapshot image.** `/cp/tomco.txt` saves a "snapshot debug image" on an exception: `snapshotdbg_addr=0x09A21E00`, 48 MB, tag `SOLID_SSHOT` in the code. It survives a restart without power loss (issue #5 part 4: after the 60p restart the dump found `SOLID_SSHOT` with 11,263 non-zero bytes).

**The second kit: a diagnostic ladder** (`fx2_apply.py test1 | test2`; the full apply is unchanged).
- **Test 1 = L13 + B5.**
  - B5 is `fhband_fx2_v1`, the A7 IV's `fhband_v1` (F658), ported with `build_og_fx2.py`. Its 11 sensor cells are L5's own, so the sensor goes into the same full-height mode.
  - Its two picture records keep the stock 16:9 band, so the stage keeps its stock height. The stored record changes in 29 bytes (not +6/+7).
  - If it runs, the FX2 takes the full-height read-out, and the dump on MOVIE shows which write buffer was opened.
- **Test 2 = L13 + L5 only:** the A7 IV's two-step squeezed baseline (F682).
- **Read helper `fx2read_v2`:**
  - a site may hold a test design's bytes, reported TEST: test 1 shows the two records and the stored record as TEST and the 11 cells as TARGET;
  - the dump also reads the memory manager's workspace (54 pages from 0x21a5000; the pointer 0x192fc28 holds 0x21a5d18 in all three of the tester's dumps). The decoder lists live and left-over unit objects with their sizes, and the write-buffer keys 0x57f / 0x6a3 / 0x704;
  - last, it reads the first 4 pages of the snapshot area 0x9a21000 (CP_HI raised to 0x9b00000).
- **New pins:** check 9dd469a2, dump 1f51dc2a, B5 23e19cbe, B6 ea9c8628. Every other library rebuilt to its old pin.
- **Checks:** emu_fx2 23 cases, emu_fx2_write 57.

## Test 2 works (2026-11-26) and the third kit

**What ran** (issue #1, second comment; evidence `a7iv_map/evidence/fx2/tester_2026-11-26/`; kit fx2read_v2, macOS). Test 2 = L13 + L5, run twice: once with APS-C on by mistake, then from a cold boot with APS-C off.
- Both DONE. On MOVIE: a steady picture, no purple flash, no restart.
- Clips: HEVC 3840 × 2160 4:2:2 10-bit, 23.98p (the squeezed picture; plays on a Mac).
- **The dump on MOVIE** (`041723`): VERDICT READY.
  - S0–S10 TARGET; the sensor shadow is column 5 (127/129 rows; register row 0 holds 2), the full-height read-out.
  - The 0x8c0 stored record: 31/31 bytes as the design; L13's words 4/4 applied.
  - Sizes in the resize pages: 7008 × 4672 (the whole window) and 4336 × 2438.
  - The memory manager's workspace (at 0x21a5d18 as predicted): the raw write buffer was carved from key 0x57f (id 0x43e) at **33,003,520 bytes**, so L13 takes effect, and nothing of key 0x6a3 (id 0x608): **the id-0x608 lead is ruled out**.
  - Output buffers: 25 left-over objects of key 0x3f1 (id 0x2d9) at 13,271,040 bytes.
  - The snapshot area holds uninitialised RAM (no crash happened).
- **USB quirk:** two dump attempts met HID 054C:096F after the switch; a replug from live view fixed it.

**Conclusion.** The full-height read-out, the 4,688-row stage, the enlarged raw write buffer and the 27/32 squeeze all work on the FX2. The first kit's crash therefore comes from **L16 (output size) or L19 (encoder)**. The tester notes the FX6 kit's bisection also breaks at its L16.

**Read statically since** (FX2 1.01): the output-buffer chooser 0x51cb38 / loop 0x51cc58 (= A7 IV 0xa1fae0) takes the picture bytes from 0x51ee00 (= A7 IV 0x444814: w × h × 1 / 1.25 / 1.5 / 2 for format codes 1–4) for output records 1–3, stride 0x80 in the context.
- **Type 1:** id 0x4c3 below 3,317,761 bytes, else 0x4c4 (13,271,040).
- **Type 2, FX2 only:** id 0x69c below it (no row in the coprocessor's DmmCfg), else 0x2d9 (13,271,040) with the log line "FW: error! rc_out[%d] image data size excerrd mem size".
- **Otherwise** (records holding 0x295 / 0x43f / 0x2d9): 13,271,041 bytes or more gives 0x43f (no row on the FX2, as on the A7 IV; the FX3 and FX6 have one, 53 MB), more than 3,317,760 gives 0x2d9, else 0x295.
- **At 3840 × 2560** a record of format code 2 needs 12,288,000 bytes and fits; one of code 3 needs 14,745,600 bytes, which goes to 0x43f or overflows 0x2d9 / 0x4c4.
- **Where the records live.** The records are copied from a template, the saved copy of the output records: A7 IV 0x11cf838 (whose format code 2 its level 15 read on the camera, F686), FX2 0x15cd7e0 by build/port_addr.py (6 of 6 references). **That address was wrong** (corrected 2026-11-26, fourth kit): the getter 0xbc75de returns **0x15cdef8**. The third kit's decoder therefore showed zeros; the pages it saved hold the records. Per record: stride 0x2c from +4; w, h at +4/+6; format code at +0x20; type at +0x28.

**The third kit** (`fx2read_v3`: check 696c9be6, dump 6a234dde; no write library changed; APK 0.3):
- **The dump** also reads pages 0x15cd000–0x15ce000, and the decoder prints each output record's size, format code, type and picture bytes, and its bytes at 3840 × 2560.
- **Test 3** = L13 + L5 + L16; **test 4** = L13 + L5 + L16 + L19, each followed by the dump on MOVIE.
- **Order asked of the tester:** test 2 again (the output records in a state that does not crash), then tests 3 and 4.
- **Checks:** emu_fx2 23 cases (its model now holds output records), every selftest and dry run.

## Test 3 crashes, why, and the fourth kit (2026-11-26)

**On the camera** (issue #1, third comment; fx2read_v3, macOS, a cold boot before each run):

| Steps | On MOVIE |
|---|---|
| L13 + L5 (test 2) | runs, records |
| L13 + L5 + L16 (test 3) | restart, forced exception pc 0x507dae |
| L13 + L5 + L16 + L19 or N19, 4:2:2 and 4:2:0 | restart |
| L13 + L5 + S16 | runs, the 3:2 rear screen filled, records (pull request 3: `open_gate_squeezed`) |

So L16 is the first failing step. On the A7 IV the same word never crashed (F688: the camera stayed up and a recording stopped after a second).

**Read from the tester's v3 dump pages** (the records at their real address 0x15cdef8, in the working state and after the restart):

- The four output records are 3840 × 2160, 1920 × 1080, 1920 × 1080, 3840 × 2160, each with **format code 2 and type 0**: the A7 IV's values.
- So a 3840 × 2560 picture is 12,288,000 bytes and gets id 0x2d9 (13,271,040). **The output buffer is not the cause**; the type-2 case does not apply.
- The saved resize view at 0x15cd520 (what 0x51fbc0 filled last) has byte +5 = 1.

**The cause: an FX2-only step of the resize set-up** (0x51fbc0, `SyncRCCalc.cpp`; the A7 IV's is 0x4455a4).

- Both read the first scaler's picture size from the mode's two records (FX2 0x7ccd72 → 0x7cccc2: right +0x190 + right +0x1a4 − left +0x1a0, right +0x1a6) into view +0x3c/+0x3e, and the output size from the movie size table into +0x40/+0x42.
- The FX2 then, when view byte +5 is set (0x51fef8: `ldrb r0, [r4, #5]`; `cbz r0, 0x51ff22`), calls **0xbd3a32**. It stores `max(record size, output size × 0x10000 / (0x10000 − margin))` back to +0x3c/+0x3e, limited to the crop at +0x38/+0x3a. The margin comes from 0xbd6f34 (u16 words at 0x190f46e..0x190f47c, 0 unless its mode arguments say otherwise; switch 0x190fcd0).
- Byte +5 is set at 0x51ff52..0x51ff64 when request word +0x1c is not 0, +0x20 is 0, +0x88 is not 1 and +0x6c is 0.
- The chooser 0x51cb38 and 0x51ce14 copy view +0x3c/+0x3e to the context (+0x54c/+0x54e) as the second scaler's input size.
- **Stock:** max(4336 × 2438, 3840 × 2160) = 4336 × 2438. **With L16:** max(4336 × 2438, 3840 × 2560) = **4336 × 2560**, while L5's records make the first scaler deliver 4336 × 2438.
- Our reading of what follows: the second scaler is handed 2,560 rows that never arrive, its stage is still busy after 11 frames, and the firmware forces the exception. The size mismatch is shown; what the hardware does with it is inferred.
- A scan of every extracted image for this function's arithmetic finds it only in the **FX2 (0xbd3a62) and the A1 II (0xbceefc)**. The A7 IV, A7C II, A7S III, FX3, FX30, FX6 and ZV-E1 do not have it.

**Emulated** (`tools/modding/fx2/emu_rcinput_fx2.py`: 0x51fbc0 run alone on the FX2's image; 10 checks):

| State | First scaler in the view | By the records | Output |
|---|---|---|---|
| stock | 4336 × 2438 | 4336 × 2438 | 3840 × 2160 |
| L5 (`ogsq_fx2_v1`) | 4336 × 2438 | 4336 × 2438 | 3840 × 2160 |
| L5 + L16 (the crash state) | **4336 × 2560** | **4336 × 2438** | 3840 × 2560 |
| H5 (`ogh2560_fx2_v1`) + L16 | 4336 × 2560 | 4336 × 2560 | 3840 × 2560 |
| L5 + L16 + F16 (`fehold_fx2_v1`) | 4336 × 2438 | 4336 × 2438 | 3840 × 2560 |

The emulated view equals the view the camera saved, bytes 1 to 0x53, in the stock state (dump 045730) and in the working L13 + L5 + S16 state (dump 051533).

**The fourth kit** (`fx2read_v4`; APK 0.4; nothing of it has run on an FX2):

- **H5 / H6 = `ogh2560_fx2_v1`**: the A7 IV's `ogh2560_v1` (F712, F713: it works on the A7 IV, first scaler 4336 × 2560, the second scaler taking every row), ported by `build_og_fx2.py` like `ogsq_fx2_v1`. It has L5's 11 sensor cells and stored record; only the two records differ (162 bytes). It takes L5's place.
- **F16 / F17 = `fehold_fx2_v1`**, the fallback: one code word, 0x51fef8 `607990b1` → `607912e0` (0x51fefa `cbz r0, 0x51ff22` → `b 0x51ff22`), with the 16 code bytes before and after as guards. The override is skipped, and the second scaler enlarges 2,438 rows to 2,560 as on the A7 IV. It goes with L5, not with H5.
- **Targets:** test5 = L13 + H5; test6 = L13 + H5 + L16; og2560 = L13 + H5 + L16 + L19 + S16 (`open_gate_3840x2560_test`); test7 = L13 + L5 + F16 + L16 + L19. Put back without a cold boot: `fx2_apply.py putback-2560` / `putback-hold`.
- **The dump** reads one more page (0x190f000: the margin words) and decodes the saved resize view, the first-scaler size the records in place give, whether the two agree, the output records at 0x15cdef8, and the state of the fallback's code word. A site holding `ogh2560_fx2_v1`'s bytes is reported TEST2 (compared by SHA-256, so that the library stays within one upload packet).
- **Checks:** emu_rcinput_fx2 10; emu_fx2 22 cases + 3 foreign; emu_fx2_write 72; every selftest and dry run, also from the published tree. Libraries L13 to S17 rebuilt to their earlier pins.

| Library | SHA-256 (fourth kit) |
|---|---|
| check | `97516ead` |
| dump | `f4cb345a` |
| H5 | `47be321c` |
| H6 | `e459d65c` |
| F16 | `73a87e6d` |
| F17 | `6cc77afd` |

**Open (then):** the margin with SteadyShot Active; whether the FX2 takes a first-scaler picture above 2,450 rows; the encoder step L19 on an FX2; PAL. All but PAL are answered in issue #5 (below).

## The 3840 × 2560 open gate works; PAL; the fifth kit (2026-11-27)

**On the cameras** (issue #5; evidence `a7iv_map/evidence/fx2/tester_2026-11-26_issue5_test6/`, `tester_2026-11-26_pal/`; the NTSC og2560 zip was not downloaded):

- **og2560 (L13 + H5 + L16 + L19 + S16) works on an FX2 set to NTSC.** XAVC HS 4K and XAVC S 4K, 4:2:2 10-bit 3840 × 2560 at 23.976p; a 10 min 16 s clip (7.38 GiB) decodes with no error; audio, timecode and the rtmd track are kept; MediaInfo and Resolve read 3:2; in-camera playback, HDMI (the 3:2 frame squeezed into 1080p), monitor remote control and PC Remote work; both base ISOs; rows outside the 16:9 band blend in. The frame of a clip and a full-sensor still have the same framing within about 2%, so the 2,560 rows are the whole sensor height. So the FX2 takes the 4336 × 2560 first-scaler picture, and L19 runs.
- **SteadyShot Active works.** The dump with Active on: view first scaler 4336 × 2877 = 2560 / (1 − 7208/65536), records 4336 × 2560, output 3840 × 2560. The margin word 7208 applied **with the switch word at 3**, so my reading that a non-zero switch makes 0xbd6f34 return 0 was wrong; the dump now judges a margin from the view (pull request 6, second version). Why this mismatch runs while L5 + L16's (4336 × 2560 asked, 2,438 delivered) crashed is not known; maybe the stabiliser's crop path takes the first scaler from the view.
- **Test 6 (L13 + H5 + L16) froze the camera on REC** on another FX2 (the encoder still at 2,160 rows). The kit now calls it a diagnostic step and says not to record in it.
- **The power switch keeps half of the patch:** after off/on, every coprocessor site was stock (L13, H5, L16, S16) and every main-processor site of L19 still applied (101 av-cam, 4 libmpr rows, 2 MP4 heights). The coprocessor restarts; the main processor keeps its memory.
- **PAL, read-only** (a camera set to PAL, fx2read_v4): 4K 25p runs mode **0x880** (index 9; the saved resize view says mode 0x880). Its stored record at 0x24de61c equals the FX2 calculator's record under the **50 Hz input table** except run-time flag bytes (13 bytes). Mode 0x8c0's record there is the 24.00p one: of `ogsq_fx2_v1`'s 31 design bytes 22 are stock, so L5 and H5 refuse on PAL. Every other stage (sensor column 5 after movie entry, 7040 × 3958 stage, 4336 × 2438 first scaler, output records, raw write buffer) is the NTSC one. Every NTSC dump reads mode 0x880's record 22/31 against the PAL design.

**The fifth kit** (`fx2read_v5`; APK 0.5; the PAL steps ran on a camera since, see the next section):

- **Q5 / Q6 = `ogsq880_fx2_v1`**: `ogsq_v3` moved to mode 0x880 (the A7 IV's `ogsq880_v1`, which works on a PAL A7 IV, F965), built by `build_og_fx2.py` with the 50 Hz table: 11 sensor cells of mode 0x880's rows (other addresses than L5's), the shared record pair 0xdf9958 / 0xdfa510 (the same bytes as L5's: 0x880 and 0x8c0 share the pair), and 31 bytes of the stored record at 0x24de61c.
- **P5 / P6 = `ogh2560880_fx2_v1`**: Q5's cells and stored record with H5's two records (`combine()` in `build_og_fx2.py`, which asserts that H5's stored record and cells are L5's and that the pair is the shared one). 13 sites, 6,024 bytes.
- **Emulated on real records:** the write emulation now models a camera with a real FX2's record pages. On the PAL camera's pages Q5 and P5 apply, run again as NOTHING TO DO, put back byte for byte, and undo a lost write; L5 and H5 refuse there. On an NTSC camera's pages Q5 and P5 refuse. Q5 on P5's state and P5 on Q5's state write nothing. emu_fx2_write: 95 checks.
- **fx2read_v5** reads mode 0x880's 11 cells and its stored record too (sites `pal_*`, in the check only: the dump has no room left under the 65,520-byte upload limit, and its record pages show the record anyway). The PC judges each stored record by the design's own bytes, because the camera's run-time bytes make the whole record read OTHER. The report says "camera set to: NTSC / PAL", which sensor step is in place (L5, H5, B5, Q5, P5 or none), the encoder side's state, and **warns of the power-switch state** (L19 applied, every coprocessor site stock). emu_fx2: 28 cases + 3 foreign, including a PAL camera stock, with Q5 and with P5; the state reader gives the right answer on every real result we hold.
- **fx2_apply.py** takes `--pal` / `--ntsc`; without them it takes the family the newest check reads, or asks. With PAL: L5 → Q5, L6 → Q6, H5 → P5, H6 → P6 (test1 has no PAL form). New launchers `open_gate_3840x2560_pal`, `open_gate_squeezed_pal`, `open_gate_putback_3840x2560`.
- The publisher keeps contributed files under `windows/tools` (pull request 4's `fx2_batch.py`) instead of deleting them.

| Library | SHA-256 (fifth kit) |
|---|---|
| check | `a5bfb547` |
| dump | `8ad8e1ff` |
| Q5 | `04c9fd0f` |
| Q6 | `7a8ae584` |
| P5 | `b3b6094d` |
| P6 | `5b892e4c` |

Every other library is rebuilt to its fourth-kit pin.

**Open (then):** PAL on a camera; why the SteadyShot margin runs. PAL is answered below.

## PAL works, and part 4 (2026-11-26, issue #5; the sixth publish, 2026-11-27)

Evidence: `a7iv_map/evidence/fx2/tester_2026-11-27_pal_fifth/` (23 sessions, fx2read_v5, macOS) and `tester_2026-11-27_ntsc_part3-4/` (NTSC, fx2read_v4).

**PAL** (the same FX2 set to PAL, fifth kit, each run from a battery pull, each check READY and "camera set to: PAL"):
- `og2560 --pal` (L13 + P5 + L16 + L19 + S16), twice: XAVC S 4K 4:2:2 **3840 × 2560 at 25.000 fps**, DAR 3:2 with no "original" size in MediaInfo, 133 Mb/s, every frame decodes. Dump `233102` on MOVIE: register column 5, mode 0x880's record 31/31 as the design, raw buffer 4 applied, output record 0 3840 × 2560 format code 2, view first stage 7040 × 4688 → first scaler 4336 × 2560 → output 3840 × 2560 in mode 0x880, agreeing with the records; screen words 18 applied; av-cam 101 target; no exception. So L19's 25p descriptors work.
- SteadyShot Active on PAL (dump `233413`): view first scaler 4336 × 2877, the 11% margin, as on NTSC; it runs.
- `squeeze --pal` (L13 + Q5 + S16): XAVC S 4K 3840 × 2160 at 25 fps, the squeezed file; dump `233942`: view 4336 × 2438 → 3840 × 2160 in mode 0x880, agreeing.
- The guards: a `--pal` dry run refused while the newest check read NTSC; after the power switch the check (`232552`) read 48 coprocessor sites stock with L19 applied and printed the warning; a battery pull cleared it.
- On a PAL FX2, XAVC HS 4K is 50p only: PAL means XAVC S 4K 25p.
- **The closing dump ran before the switch was on MOVIE** in both apply runs (`231939`, `232944`: view of mode 0x5020). On macOS the camera is a USB drive again within seconds of each session (the five steps ran 5 s apart), and the old wait took that re-enumeration for the unplug. The wait now needs the camera seen for 6 s, then gone for 3 s, and the dump asks for a confirmation that the switch is on MOVIE.

**Part 4 (NTSC, og2560):**
- Proxy Recording works in all three settings (XAVC S HD 1280 × 720, XAVC HS HD 1920 × 1080 at two rates); the proxy holds the whole 3:2 picture squeezed into 16:9, same frame count as the main clip.
- SteadyShot **Dynamic Active** works: view first scaler 5486 × 3658 = 3840 × 2560 / (1 − 19660/65536). So **19660 is Dynamic Active's margin word (30%) and 7208 Active's (11%)**, both applied with the switch word at 3. XAVC S 4K takes Dynamic Active and proxy at once.
- **A frame-rate change (24p → 60p) with the patch applied restarted the camera.** Dump `230710` on STILL: every site stock, L19's main-processor sites too (a crash restart clears them, the power switch does not); kprint: CAM_VD_SEQUENCE, data abort, pc 0x507dae, lr 0x507da1, DFAR 0: the forced "S-Ele Refresh ng" exception; the snapshot image survives the restart (`SOLID_SSHOT`, 11,263 non-zero bytes).

**This publish:** the report prints kprint's exception record, names the margin (Active / Dynamic Active), says when the saved view is of another mode (the camera was not on MOVIE), and names P5/Q5 in a dump from mode 0x880's record. `fx2_apply.py` asks for XAVC S 4K 25p on PAL, gives the closing note the family's rate, warns against frame-rate changes, and on macOS says to quit Lightroom, Photos and Image Capture. APK 0.6. No library changed.

**Open:** heat over long recordings (a 30–60 min PAL run is under way); why the SteadyShot margin's view/records mismatch runs while L5 + L16's crashed; HDMI 2160p.

## 5.7K (5760 × 3840) and XAVC S-I (2026-11-27, issue #7; built and emulated, not yet run on an FX2)

The A7 IV's real 5.7K state (its `open_gate_apply_57` default: F906, 300 Mbps F970, M = 1 F981/F986, MP4 headers F989) on the FX2: L13, **K5**
(PAL **J5**), **K16**, **K19**, S16. XAVC S-I 4K is one more encoder step on top of either state: **I19** (3840 × 2560) or **G19** (5760 × 3840).

**Sensor side, K5 / J5** (`og57n_fx2_v1`, `og57n880_fx2_v1`; the A7 IV's `og57n_v1` / `og57n880_v1` through `build_og_fx2.py`): the squeeze
designs' 11 cells and stored record (identical to L5's / Q5's), with the two picture records that make the first scaler give 5760 × 3840. NTSC
and PAL share the records.

**Output side, K16** (`og57cp_fx2_v3`; the A7 IV's `og57cp_v3` through the A7C II's `og57cp_c2_v3`), five words:

| RAM | Stock → new | What |
|---|---|---|
| 0x18f62e8 | 0 → 3 | the unit-count setting: four scaler units (the FX2's split rule 0x509e52.., the A7C II's code, table {1, 2, 4}) |
| 0x24b9c2c | 0x24bbc28 → 0x24bbd00 | id table row of id 0x446 (unopenable): key list → id 0x498's (key 0x5f2, 30,824,400-byte units) |
| 0x24b9c28 | 0x446 → 0x43f | the same row: id 0x43f, the id the FX2 asks for an output plane above 13,271,040 bytes (it has no row of its own) |
| 0x18f60fc | 0x2d9 → 0x43f | size table, the 4K entry's buffer id |
| 0x18f60f8 | 3840 × 2160 → 5760 × 3840 | size table, the 4K entry's output size (written last) |

Guards: the setting's 12 neighbouring bytes (zero in all 24 FX2 dumps we hold, NTSC and PAL), the id row before, id 0x498's row and key list,
the size entry before. In the FX2's own memory manager (emulated) id 0x43f then opens one 30,824,400-byte unit (5760 × 3840 × 1.25 = 27,648,000),
and the other 4K movie ids still open.

**The FX2's first-scaler override** (`emu_rcinput_fx2.py`): with K5 + K16 the view's first scaler is 5760 × 3840, equal to the records', output
5760 × 3840, in mode 0x8c0 and in mode 0x880. With SteadyShot Active the margin would ask for 6472 × 4314: the tests ask for SteadyShot Off.

**Checks:** `emu_fx2_write.py` 118 (K5 / J5 on real NTSC / PAL record pages, refusals across families and designs, K16 on a model with the FX2's
id rows, the allocator after K16); `emu_rcinput_fx2.py` 14. The read helper is unchanged (fx2read_v5): the 5.7K records read OTHER with their
bytes printed, and the PC names them (K5 / J5) by SHA-256; the report shows the output size from the size word.

| Library | SHA-256 |
|---|---|
| K5 | `fb776e4a` |
| K6 | `2acafe84` |
| J5 | `189f919a` |
| J6 | `61f5e86d` |
| K16 | `a175e9a5` |
| K17 | `a50174f7` |

**Encoder side, K19** (`ogfile57r300m1_fx2_v4`; the A7 IV's `ogfile57r300m1_v4` through `build_og57.py --rate300 --m1all --meta --build fx2_101`):
296 av-cam sites (58 descriptor, 116 profile, 33 rate, 29 level, 29 PredMode, 29 MParam, the unit-type row 3, the clip row) and 14 libmpr sites
(the four 4K combination rows as 5760 × 3840, the HEVC edit-list start, nine MP4 size sites). Every site's old and new bytes equal the A7 IV
design's, kind by kind; only the clip code differs (23 on the FX2, as on the A7C II).
- The HEVC edit-list start: 0x11e40c `csel w0, w1, w0, ls` → `mov w0, #0` (the only match of the A7 IV's four instructions); `m_vpcSt` at 0x2e3898.
- The MP4 size sites: the A7 IV's nine at −0x37b4, each unique by 32 bytes of context (the 4K kit's two heights among them, unchanged).
- **M19** (`ogfile57r300m1_fx2_v3`) is the same without the nine MP4 size sites (`--no-meta`); K20 puts back either.

**XAVC S-I 4K, I19 / G19** (`ogfilesi2560_fx2_v1` on top of L19, `ogfilesi57_fx2_v1` on top of K19; the A7 IV's `ogfilesi2560_v1` / `ogfilesi57_v1`):
the FX2's S-I 4K descriptors (indices 110, 111, 113, 114: 25p and 23.98p, profile keys 105205/105206/105208/105209 with their 205xxx twins),
16 + 1 and 24 + 1 sites; neither touches a site of the step it goes on top of. Without the S-I step no S-I descriptor answers the open-gate size:
the "REC stops at once" of issue #7.

**Emulated on the FX2's own code** (`build/run_og57_si_emu_fx2.py`, 34 checks; `emu_elst_site_v3.py --build fx2_101`, 336 cases;
`emu_mp4_meta.py --build fx2_101 --both`, 432 requests):
- the encoder request becomes 5760 × 3840; the FX2's descriptor matcher finds each changed descriptor at that size and every other request as before;
- the memory: the 5.7K picture asks unit-type row 3, whose blocks hold the codec's need (CD 4.98 MB, LD 88.5 MB, multi 12.8 MB); row 2's order would not;
- the builder's own rules on the FX2's tables: the two-core rule against Sony's profiles, PredMode = MParam in all 691 descriptors, Sony's M = 1
  two-core profiles, 11 profiles at 97 Mbps or more given the 300 Mbps figures;
- the edit list: HEVC from one frame to none; AVC, intra and the other path unchanged;
- the MP4 writer: every request the stock writer accepts answers as the A7 IV's, stock and at both sizes;
- S-I: unit type 4 holds the intra need (CD 44.3 MB at 4K, 99.5 MB of 100.8 MB at 5.7K), comb 9's headers say the state's size.

**Write libraries** (`emu_fx2_write.py`, 135 checks in all): K19 / K20 / M19 apply, put back and refuse L19's state (and L19 K19's); I19 / G19
apply on top of L19 / K19 without touching them and come off again.

| Library | SHA-256 |
|---|---|
| K19 | `27278ae5` |
| K20 | `24c7b0be` |
| M19 | `9d78d348` |
| I19 | `2aa88118` |
| I20 | `1065aa61` |
| G19 | `a17334c4` |
| G20 | `37f042b8` |

**Targets** (`fx2_apply.py`): `og57` = L13 K5 K16 K19 S16 (PAL: J5), `og2560si` = og2560 + I19, `og57si` = og57 + G19; `putback-57`, `putback-2560si`,
`putback-57si`; `--no-meta` takes N19 / M19. Launchers `open_gate_5760x3840_test`, `_pal`, `open_gate_3840x2560_si_test`, `open_gate_5760x3840_si_test`
and their putbacks; app 0.7.

**Not known:** anything of it on an FX2; the request word +0x88 a real recording sends (the emulation uses 3, the 4K path that records); 5.7K
with SteadyShot Active; in-camera playback of 5.7K (never on the A7 IV); 3840 × 2560 S-I (not run on the A7 IV either; 5.7K S-I was, F1014).

## What the FX2 is

- **The sensor is the A7 IV's.**
  - The FX2 has the A7 IV's 30 drive modes in the same order, with two more inserted at index 25 (0x2821, 0x28c1). Modes 0x880 (25p) and 0x8c0 (23.98p) keep their indices 9 and 10.
  - The per-mode tables the design touches are the A7 IV's rows: crop, stream-0 and stream-1 windows, LC, read-out (fields 0–17) and the column map.
  - The register matrix is the A7 IV's (129 rows of 24 bytes + a zero row) but for each row's leading pointer, which is relocated.
- **The image processor's software is the A7C II's build** (the A7 IV's code, newer):
  - read-out rows of 20 bytes;
  - 4K timing rows with HMAX 500 (0x8c0: VMAX 3000 at 23.98p; on the 50 Hz table 0x8c0 is 24.00p);
  - stored drive-parameter records of 0x170 bytes;
  - one picture-record pair shared by modes 0x880 and 0x8c0;
  - the DMM layouts numbered 0x8c / 0x8d.
  - Its own calculator gives stored records equal to the A7C II's for all 29 modes the two share but 0x8000.
- **The main processor is the A7 IV's:**
  - libmpr's MP4 writer is the A7 IV's code moved by −0x37b4;
  - av-cam holds the A7 IV's unit-type table, descriptors in the A7 IV's layout (691 rows), profiles and decode set-up;
  - the codec firmware is the same file, and the main-processor memory map is the A7 IV's;
  - av-cam is reserved at physical 0x401000000.
- **USB route:** `libsencore.so` holds the A7 IV's three login keys. `DeviceInfo.xml` is the same file on every body, so the helper checks which camera it is on: the hashes of three libraries and four code pages.

## The steps (A7 IV → FX2)

| Step | FX2 design | A7 IV design | What |
|---|---|---|---|
| L13 / L14 | `dmmwb4688_fx2_v1` | `dmmwb4688_v1` | raw write buffer: 4 words of the DMM's RAM copy |
| L5 / L6 | `ogsq_fx2_v1` | `ogsq_v3` | sensor full height, 13 sites (6,024 bytes) + 31 bytes of the stored record |
| L16 / L17 | `outsz2560_fx2_v1` | `outsz2560_v1` | output size, 1 word |
| L19 / L20 | `ogfile2560_hs_s_fx2_v2` | `ogfile2560_hs_s_v2` | encoder: 101 av-cam + 4 libmpr sites + 2 MP4 height instructions |
| N19 | `ogfile2560_hs_s_fx2_v1` | `ogfile2560_hs_s_v1` | the same without the MP4 heights (`--no-meta`; put back by L20) |
| S16 / S17 | `lcd32dsq_fx2_v1` | `lcdfill_v2` + the FX3 kit's de-squeeze idea | rear screen 3:2 + focus frames + De-Squeeze Display ratios, 18 words |

There is no C step (the FX2 has its own De-Squeeze Display) and no playback step (see "Playback").

### L13: raw write buffer (`dmmwb4688_fx2_v1`)

- **Why it is needed.** Id 0x43e (key 0x57f) holds four records of 27,864,320 bytes (7040 × 3958), as on the A7 IV. On the A7 IV that was the limit of the first stage, and a full-height stage of 4,688 rows restarted the camera until the buffer was enlarged.
- **The layouts** are numbered as on the A7C II: steer 0x8c, grow 0x8d, parent key 0x6fa (4 × 73,400,320).
- **The DMM module did not move as one block** (the A7C II's did): every function was matched one by one.
- **RAM copies:** unit records at 0x247e6dc, each table the A7C II's − 0xfea48.
- **Sites:**
  - 0x24838c8 and 0x24838dc: size 27,864,320 → 33,003,520;
  - 0x2483860 and 0x2483874: key 0x57f → 0x8fe.

  Parent records are 0x2481440, 0x2481454, 0x24814b8 and 0x24814cc. Busy keys: 0x57f, 0x634, 0x635, 0x8fe.
- **Helper constants:** DMM globals page 0x192f000, workspace +0xc28, unit objects +0x77c.
- **Emulated in the FX2's own allocator:**
  - six 33,003,520-byte write buffers fit, inside their parents;
  - 0x4b7 and 0x4b8 still open, and a seventh write buffer is refused;
  - everything frees;
  - written while a stock-division unit is in use, the change has no effect, and the level refuses in that state.

### L5: sensor side (`ogsq_fx2_v1`)

| Table | A7 IV 6.02 | FX2 1.01 | Note |
|---|---|---|---|
| mode ids | 0xc98330 (30) | 0xe944b0 (32) | the A7 IV's + 0x2821, 0x28c1 at index 25 |
| geometry rows (row 6 changed) | 0xc3dc40 | 0xe40700 | the first 16 rows equal |
| crop | 0xc983a8 | 0xe94530 | |
| stream-0 / stream-1 window | 0xd95aac / 0xd95f20 | 0xf98f24 / 0xf993e4 | rows of 0x880/0x8c0 equal |
| LC | 0xd96394 | 0xf998a4 | |
| read-out | 0xd96538 (18-byte rows) | 0xf99a64 (20-byte rows) | fields 0..17 equal |
| sensor column map (0x8c0: 6 → 5) | 0xfb401c | 0x11eb190 | |
| register matrix | 0xfb33ec | 0x11ea560 | equal but for the rows' pointers (shadow 0x12fe864..) |
| timing 60 / 50 Hz | 0xc98ab0 / 0xc98d80 | 0xe94cb0 / 0xe94fb0 | not changed by the design |
| 0x8c0 picture records L / R | 0xbf7638 / 0xbf81f0 | 0xdf9958 / 0xdfa510 (shared with 0x880) | the A7 IV's design records with +0x328, +0x3b8, +0x948..+0x950 kept as the FX2's |
| record selector | 0x255988 | 0x27ab64 | emulated: 0x8c0 and 0x880 → the pair above |
| drive-parameter calculator | 0x348ea4 | 0x3d3024 | |
| table map (constructor caller) | 0x89a07e | 0xa0fa1c | |
| stored records | 0x1fd1224 (0x15c) | 0x24dd92c (0x170) | mode 0x8c0 at 0x24de78c |
| sensor object; drive-parameter pointer | 0x12b9ce0; control +0x684 | 0x1750860; **control +0x6ac** | the FX2's control object puts every field 8 bytes on from the A7C II's |

- **The stored record.** With the design's cells, the FX2's own calculator gives the A7C II port's records exactly, stock and patched: 31 bytes differ, with the vertical sampling ratio 27/32 at +6/+7 (`evidence/fx2/ogsq_fx2_v1_drvparam_records_emu.json`). No other mode's record changes.
- **PAL.** `ogsq880_fx2_v1` (mode 0x880, 25p) is built and emulated as well. Since the fifth kit it is step Q5, and its real-rows form P5 (see "PAL works").

### L16: output size (`outsz2560_fx2_v1`)

- **The set-up 0x4ff894 is not the A7C II's relinked.** It reads a second settings block (0x196aa58), and its fields after +0x1c are moved by 4.
- **Run in emulation:**
  - the table at 0x18f60b0 holds the A7C II's 16 entries;
  - the reader 0x51fca6, case 3 (UHD), loads 0x18f60f8.
- **Site:** 0x18f60f8, 3840 × 2160 → 3840 × 2560, with two guards.
- **Output buffer:** id 0x2d9 is 9 × 13,271,040 bytes, so 3840 × 2560 fits at format code 2 (the A7 IV's).

### L19: encoder side and MP4 headers (`ogfile2560_hs_s_fx2_v2`)

| What | A7 IV | FX2 |
|---|---|---|
| libmpr `g_videoParamComb` | 0x2d32b8 | 0x2cdc58 |
| MP4 track config / stsd / PROF / tkhd | 0x222b18 / 0x2240cc / 0x225db8 / 0x226108 | 0x21f364 / 0x220918 / 0x222604 / 0x222954 |
| MP4 height, AVC / HEVC (`mov w6, #0x870` → `#0xa00`) | 0x222b90 / 0x222bdc | 0x21f3dc / 0x21f428 |
| av-cam unit types / descriptors | 0x38389c / 0x38393c (689) | 0x3acf90 / 0x3ad030 (691 × 0x90) |
| profile tables | 0x39bccc, 0x3b32cc | 0x3c54e0 (376), 0x3dcde0 (315) |
| clip-format table | 0x381af0 (code 16) | 0x3aaeb4 (code 23, as on the A7C II) |

- **The design.** The same 29 descriptors and 29 profiles with the A7 IV's attributes, 101 av-cam sites and 4 libmpr rows, plus the two MP4 height instructions.
- **Emulated on the FX2's own code** (`run_ogfile_emu_fx2.py`, `emu_mp4_meta.py --build fx2_101`):
  - descriptor matcher, clip matcher, memory class, codec memory, start-block builder;
  - 416 MP4 requests: every accepted one gives `tkhd`, `stsd` and PROF 3840 × 2560 with the stock profile id.
- **Sony's XML and the level labels are unchanged**, as on the A7 IV.

### S16: rear screen and De-Squeeze Display (`lcd32dsq_fx2_v1`, 18 words)

- **Panel shape.**
  - The rear panel-type byte is RAM 0x19d98cc (3 = 3:2), the viewfinder's 0x19d99fc.
  - Sony gives the monitor 1,036,800 dots = 720 × 480 = 3:2, the A7 IV's. Not read on a camera yet: the closing dump reads it.
- **Fill and frames: the A7 IV's `lcdfill_v2`, word for word.**
  - The fit function 0x1f9e98 and the three frame tables 0xf796d4 / 0xf7974c / 0xf797c4 are byte-identical to the A7 IV's.
  - Fit word 0x1f9eec: 3 → 0 (a 16:9 picture fills a 3:2 panel).
  - Row 1's 16:9 entry in each frame table: (0, 38, 640, 404) → (0, 0, 640, 480).
- **De-Squeeze Display.** The 1.01 menu sends codes 0, 1 and 5 (Off, 1.3x, 2.0x). The calculator 0x1fa0c0 uses fixed ratios for a 16:9 picture.

  | Code | Stock → new | Shows |
  |---|---|---|
  | 1 (1.3x) | 45/104 → 20/39 | 1.95:1 |
  | 5 (2.0x) | 3/8 → 1/3 | 3:1 |
  | 3 (1.65x, not in the menu) | 15/44 → 15/37 | 2.47:1 |
  | 4 (1.8x, not in the menu) | 5/12 → 10/27 | 2.7:1 |

  - **The 2.0x centre-4:3 input crop is off:** 0x721e3c's two code tests → `cmp r0, #6` (never; codes ≥ 6 are refused by the input command).
  - **The FX2-only output rectangle 0x7214b6** for codes 4/5 gets the same change.
- **Emulated on the FX2's own functions** (`emu_lcd_fx2.py`, 30 cases):
  - the live view on 720 × 480 becomes (0, 0, 720, 480);
  - de-squeeze gives 1.957 / 3.000 / 2.466 / 2.687;
  - the crop is off;
  - the focus-frame check 0x128438 accepts the patched view with the patched tables.

### Playback: no step needed (static)

- **Ordinary MP4 clips.** For them the FX2's decode create-ch takes row 0 of its table 0xc0aed0, 7690 × 4320 (`mov x23, xzr` at 0x229044), with the 8K memory ids 0x47c / 0x47e (0x228ad0). That is the A7 IV's behaviour, and the A7 IV plays its 3840 × 2560 clips.
- **The 4K row** is used only for clip type 14, which the type maker 0x23a2a4 makes only for formats 0x26 / 0x27, as on the A7 IV.
- **The FX3's fault** (the 4K row always) is not in this firmware.
- **Not run.**

## The kit

- **Helpers.**
  - `helper_fx2/fx2read.c` is `fx3read.c` with text changes only.
  - The write libraries are the A7 IV helper's levels 13/14, 5/6, 16/17 and 19/20 (readcheck.c, unchanged), with the FX2's tables and constants (`build_fx2_write.sh`).
- **Read-only emulation** (`emu_fx2.py`, 21 cases):
  - a stock FX2 reads READY and an applied one TARGET (also without the screen step, and with N19);
  - the A7C II, A7 IV and FX3 images are refused (DIFFERS, NOT READY);
  - without the av-cam reservation, av-cam.bin is not read;
  - with an existing result, nothing is done;
  - the FX3, ZV-E1 and A7S III kits' check libraries say NOT READY on an FX2.
- **Write emulation** (`emu_fx2_write.py`, 50 cases):
  - apply, apply again, put back byte for byte, for every step;
  - foreign bytes, lost writes undone, a null records pointer, a mode not in the table;
  - every one of the 2 + 33 guards wrong;
  - L13 refused while the stock division is in use;
  - N19 → L20 and N19 → L19 (only the two heights written);
  - the A7C II, FX3 and ZV-E1 kits' sensor, DMM, words and encoder libraries write nothing on an FX2.
- **Scripts.**
  - `fx2_run.py` and `fx2_apply.py` are `fx3_run.py` / `fx3_apply.py` with this camera's libraries, pins, dump decoder and texts (the Still/Movie switch).
  - Apply: L13, L5, L16, L19, S16, then a read-only dump on MOVIE. Put back: S17, L20, L17, L6, L14.
  - Every library's `--selftest` and every launcher's `--dry-run` pass, also from the published tree.
- **Android app 0.1** (`android/FX2-OpenGate.apk`). Its Python side passed 8 checks on the APK's own payload: setup, both self-test sets (13 and 11 steps), four dry runs, and the apply refused without a READY check. Not run on a phone.

Library pins (fx2read_v1, 2026-11-25):

| Library | SHA-256 |
|---|---|
| check | `e3838945` |
| dump | `5008ec3a` |
| L13 | `c99682a3` |
| L14 | `15ec15af` |
| L5 | `72417443` |
| L6 | `ae85bce1` |
| L16 | `744dd7eb` |
| L17 | `d2d62a12` |
| L19 | `e2a69598` |
| L20 | `decff5bf` |
| N19 | `45a68ca5` |
| S16 | `dd8bb759` |
| S17 | `34075aa0` |

Full hashes are in `fx2_run.py`. A result belongs to this kit only if its header says `fx2read_v1` and each step's manifest names these libraries.

## Not known yet

- **The PAL steps on a camera:** answered (issue #5): they work.
- **The vertical squeeze lever:** answered (issue #5). The squeezed files and the 3840 × 2560 files hold the whole sensor height: a frame and a full-sensor still have the same framing within about 2%.
- **The resize result block's address on the FX2.** Its neighbours moved by different amounts, so the dump decoder searches the resize pages (0x190c000..) for known sizes instead of reading one block.
- **The 4K format code:** read, 2 (the tester's dump pages, 2026-11-26).
- **The encoder request's word +0x88.** The FX2's descriptor matcher has an extra branch: with 2 or 5 it skips these 4K descriptors, so even stock would fail; the emulation uses 3, the A7 IV's path. The value a real recording sends is not traced.
- **The power switch:** answered (issue #5): it puts back the coprocessor steps and keeps L19.
- **Exposure, autofocus, HDMI, long recordings:** a 10-minute clip, HDMI and touch focus work (issue #5); heat over longer use is not known.
- **The rear panel type and focus-frame row 1** (carried over from the A7 IV). Only one of the three frame checks was emulated.
