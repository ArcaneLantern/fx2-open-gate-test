# Port notes: A7 IV 6.02 open gate → FX2 1.01 (in the FX3 kit's shape)

Everything here was read from the FX2 1.01 firmware update (`BODYDATA.DAT`, SHA-256 `7c12d1e4…9c9a`). Every step of the kit was emulated: Unicorn ran the FX2's own code where it mattered, and the built helper libraries ran against a model FX2. **Nothing has run on an FX2.**

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
- **The snapshot image.** `/cp/tomco.txt` saves a "snapshot debug image" on an exception: `snapshotdbg_addr=0x09A21E00`, 48 MB, tag `SOLID_SSHOT` in the code. Whether it survives the restart is not known.

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
- **PAL.** `ogsq880_fx2_v1` (mode 0x880, 25p) is built and emulated as well. The kit does not ship it, as in the FX3 kit.

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

- **Anything on a camera.**
- **The vertical squeeze lever.** On the A7 IV, the stored record's +6/+7 = 27/32 makes the resize calculation keep the whole 3:2 window. Without it the second scaler took a 16:9 cut (F680, F681).
  - The FX2's resize code (CalcRC 0x5200da, RC calc 0xbd38ba, working structure 0x15e42d0) is a newer revision with other structure offsets. It was compared with the A7 IV's but not run alone, because its input block differs.
  - If it does not act the same way, the file shows a 16:9 cut of the full-height picture (no crash expected).
  - The closing dump searches the resize pages for the sizes involved.
- **The resize result block's address on the FX2.** Its neighbours moved by different amounts, so the dump decoder searches the resize pages (0x190c000..) for known sizes instead of reading one block.
- **The 4K format code** (2 on the A7 IV; at code 3 the output buffer would be too small).
- **The encoder request's word +0x88.** The FX2's descriptor matcher has an extra branch: with 2 or 5 it skips these 4K descriptors, so even stock would fail; the emulation uses 3, the A7 IV's path. The value a real recording sends is not traced.
- **The power switch:** whether it removes the patch.
- **Exposure, autofocus, HDMI, long recordings.**
- **The rear panel type and focus-frame row 1** (carried over from the A7 IV). Only one of the three frame checks was emulated.
