"""Design lcd32dsq_fx2_v1: the FX2 1.01 rear screen (a 3:2 panel) shows the open-gate live view at 3:2 with the focus frames, and the
FX2's own De-Squeeze Display stays right for that picture.

  work\\venv\\Scripts\\python.exe -I -B build\\build_lcd_fx2.py        writes modding/designs/lcd32dsq_fx2_v1.json

The open-gate live view on the FX2 is the A7 IV's: a 16:9 frame (picture aspect code 2) that holds the whole 3:2 sensor area squeezed
vertically by 32/27. All words are in the FX2's coprocessor image (cpapp-b.bin 1.01, loaded at 0x108000) and are changed in RAM only.
Notes: modding/FX2_PORT_SCREEN.md.

(a) The A7 IV's working lcdfill_v2 (F966/F969), carried over word for word. The FX2's fit-mode function 0x1f9e98 and its tables are
    byte-identical to the A7 IV's 0x1e4b78, and its three frame-widget rectangle tables are byte-identical to the A7 IV's:
      fit word of a 16:9 picture on a 3:2 panel (panel code 1)  0x1f9eec      3 (letterbox) -> 0 (fill)
      cpActAfWindow 0xf796d4, cpActAfWindowRemoteSend 0xf7974c, cpActTrackingFrame 0xf797c4: row 1 (rear output, 3:2 panel), 16:9 entry
        (0, 38, 640, 404) -> (0, 0, 640, 480), so the frame checks 0x128438 / 0x128d60 / 0x1297e8 (the A7 IV's code at the same addresses,
        relinked) accept the filled live view.
    The rear panel's type byte (RAM 0x19d98cc, read by 0x704ab8) gives the panel code through 0x1fad28 / 0xdc64dc: type 3 -> code 1 (3:2),
    type 2 -> code 0 (4:3), type 1 -> code 2 (16:9). Sony gives the FX2's monitor as 1,036,800 dots = 720 x 480 (3:2), the A7 IV's.
    The EVF (type byte 0x19d99fc; a 4:3 Quad-VGA panel) keeps code 0's letterbox and its frame row 0: it still shows the squeezed 16:9
    picture with de-squeeze off, as on the A7 IV.
(b) The de-squeeze calculator 0x1fa0c0 (used instead of the picture-ratio function while De-Squeeze Display is on; code byte from the
    accessor's slot 0x798): full width, centred, height = (width x n + 2d) / d & ~3 with fixed n/d per code and picture shape. For a
    16:9 frame that holds a 3:2 picture:
      code 1 (1.3x, menu)   16:9 case 0x1fa162 / 0x1fa166   45/104 -> 20/39   (shown 1.95:1)
      code 5 (2.0x, menu)   0x1fa120 / 0x1fa124              3/8   ->  1/3    (3:1, the whole 3:2 frame: the owner's choice on the FX3)
      code 3 (1.65x)        16:9 case 0x1fa152               15/44 -> 15/37   (2.467:1 for 2.475; the 15 is shared with code 1's 4:3 case)
      code 4 (1.8x)         default 0x1fa0e6 / 0x1fa0ea      5/12  -> 10/27   (2.7:1; code 4's only ratio, every shape)
    The FX2 1.01 menu sends only codes 0, 1 and 5 (0x1a191c: setting 0/1/2 -> 0x50100 >> 8n). Code 2 (1.5x) has no ratio of its own for
    a 16:9 picture: it branches to code 5's words, so while applied 1.5x would show 3:1 (no menu entry sends it).
(c) The input crop to a centre 4:3 for codes 4 and 5 (0x721e3c, called by 0x721b5e) is turned off, as on the FX3: its two code tests
    go to `cmp r0, #6`, which never matches (VdfInputCmdSetDeSqueeze 0x71b980 refuses a code >= 6):
      0x721e72  cmp r0, #5 -> #6  (path flag set: code 5 only)        0x721eae  cmp r0, #4 -> #6  (after `and r0, #0xfe`: codes 4, 5)
(d) The output-device command's picture rectangle (VDF::DevCmdOutv vfn11 0x723862 -> 0x7214b6) widens the rectangle by (source aspect) /
    (4/3) for codes 4 and 5, to match that crop. With the crop off it must not: its two tests go to `cmp r0, #6` too, so codes 4/5 take the
    rectangle codes 1-3 take:
      0x721556  cmp r0, #4 -> #6                                      0x721568  cmp r0, #5 -> #6
    (the FX3 7.02 has no such step; this is the FX2's own code).
Left stock: the fit words of the other panels and shapes, the picture-ratio function 0x1fa328, the 17:9 and 4:3 de-squeeze cases, the
HDMI-only de-squeeze path 0x1fa728, the device command's factor bytes 0x1fad38 (13/10, 2/1: the factor, not the shape).
While applied, every 16:9 picture on the rear screen fills the 3:2 panel and the de-squeeze ratios are those of a 3:2 picture (other
movie formats look wrong there until the step is put back). Checked by build/emu_lcd_fx2.py (Unicorn, the FX2's own functions).
Nothing here talks to a camera.
"""
import hashlib
import json
import struct
import sys
from pathlib import Path

from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "build"))
import locate_file  # noqa: E402

NAME = "lcd32dsq_fx2_v1"
B = 0x108000
FX = locate_file.locate("fx2_101", "cpapp-b.bin").read_bytes()
A4 = locate_file.locate("a7iv_602", "cpapp-b.bin").read_bytes()
SHA = "eba723db657117a36d9593dacf640840aca893c0d6ee5d728de9d1996b8c5e29"
MD = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
fx = lambda a, n: FX[a - B:a - B + n]
a4 = lambda a, n: A4[a - B:a - B + n]

FIT_FN, FIT_TABLE, FIT_SITE = 0x1F9E98, 0x1F9EE8, 0x1F9EEC          # A7 IV 0x1e4b78, 0x1e4bc8, 0x1e4bcc
A4_FIT_FN = 0x1E4B78
DSQ_FN, RATIO_FN, LAYOUT_FN, CROP_FN, OUTV_FN = 0x1FA0C0, 0x1FA328, 0x1FA42C, 0x721E3C, 0x7214B6
TABLES = (("cpActAfWindow (focus area frames)", 0xF796D4, 0xD7B560, 0x128438),
          ("cpActAfWindowRemoteSend (the same frames for a remote viewer)", 0xF7974C, 0xD7B5D8, 0x128D60),
          ("cpActTrackingFrame (tracking and face frames)", 0xF797C4, 0xD7B650, 0x1297E8))
TABLE_LEN = 0x78
ROW, COL = 1, 3                                     # rear output on a 3:2 panel; the 16:9 column
RECT_STOCK, RECT_NEW = (0, 38, 640, 404), (0, 0, 640, 480)
rect = lambda r: struct.pack("<4H", *r)
# (instruction address, stock, new, what)
CODE = [(0x1FA162, ("mov.w", "sb, #0x68"), ("mov.w", "sb, #0x27"), "de-squeeze code 1 (1.3x), 16:9 picture: d 104 -> 39"),
        (0x1FA166, ("mov.w", "sl, #0x2d"), ("mov.w", "sl, #0x14"), "de-squeeze code 1 (1.3x), 16:9 picture: n 45 -> 20 (height = width x 20/39: 1.95:1)"),
        (0x1FA120, ("mov.w", "sb, #8"), ("mov.w", "sb, #3"), "de-squeeze code 5 (2.0x; also code 2's 16:9 case): d 8 -> 3"),
        (0x1FA124, ("mov.w", "sl, #3"), ("mov.w", "sl, #1"), "de-squeeze code 5 (2.0x): n 3 -> 1 (1/3: 3:1, the whole 3:2 frame)"),
        (0x1FA152, ("mov.w", "sb, #0x2c"), ("mov.w", "sb, #0x25"), "de-squeeze code 3 (1.65x), 16:9 picture: d 44 -> 37 (n 15 shared: 15/37, 2.467:1)"),
        (0x1FA0E6, ("mov.w", "sb, #0xc"), ("mov.w", "sb, #0x1b"), "de-squeeze code 4 (1.8x), its only ratio: d 12 -> 27"),
        (0x1FA0EA, ("mov.w", "sl, #5"), ("mov.w", "sl, #0xa"), "de-squeeze code 4 (1.8x): n 5 -> 10 (10/27: 2.7:1)"),
        (0x721E72, ("cmp", "r0, #5"), ("cmp", "r0, #6"), "input crop 0x721e3c, path with the flag set: code 5 -> 6 (never): no centre 4:3 crop"),
        (0x721EAE, ("cmp", "r0, #4"), ("cmp", "r0, #6"), "input crop 0x721e3c, other path (code & 0xfe): 4 -> 6 (never): no centre 4:3 crop for codes 4, 5"),
        (0x721556, ("cmp", "r0, #4"), ("cmp", "r0, #6"), "output-device rectangle 0x7214b6: code 4 -> 6 (never): the rectangle of codes 1-3"),
        (0x721568, ("cmp", "r0, #5"), ("cmp", "r0, #6"), "output-device rectangle 0x7214b6: code 5 -> 6 (never): the rectangle of codes 1-3")]
ENC = {("mov.w", "sb, #0x27"): "4ff02709", ("mov.w", "sl, #0x14"): "4ff0140a", ("mov.w", "sb, #3"): "4ff00309", ("mov.w", "sl, #1"): "4ff0010a",
       ("mov.w", "sb, #0x25"): "4ff02509", ("mov.w", "sb, #0x1b"): "4ff01b09", ("mov.w", "sl, #0xa"): "4ff00a0a", ("cmp", "r0, #6"): "0628"}


def insn(data, addr):
    i = next(MD.disasm(data, addr), None)
    return (i.mnemonic, i.op_str, i.size) if i else None


def movw_movt(addr):
    """the 32-bit constant a MOVW at addr and the MOVT of the same register right after it (within 16 bytes) form"""
    i = list(MD.disasm(fx(addr, 24), addr))
    assert i[0].mnemonic == "movw"
    rd, lo = i[0].op_str.split(", #")
    hi = next(x for x in i[1:] if x.mnemonic == "movt" and x.op_str.startswith(rd + ","))
    return int(hi.op_str.split("#")[1], 16) << 16 | int(lo, 16)


def check_context():
    """Facts the design rests on, each read from the image (and the A7 IV 6.02 image where it is the reference)."""
    assert hashlib.sha256(FX).hexdigest() == SHA
    # (a) the fit function and its tables are the A7 IV's, byte for byte; a 16:9 picture: 3, 3, 0, 0, 0, 2 for panel codes 0..5
    assert fx(FIT_FN, 0x94) == a4(A4_FIT_FN, 0x94)
    assert struct.unpack("<6I", fx(FIT_TABLE, 24)) == (3, 3, 0, 0, 0, 2)
    # the panel code of the rear output: type byte [0x19d98b0 + 0x1c] (0x704ab8; >= 4 -> 1), then 0x1fad28 and 0xdc64dc: 3 -> 1 (3:2)
    assert movw_movt(0x704AB8) == 0x19D98B0 and fx(0x704AC0, 2) == bytes.fromhex("007f")
    assert movw_movt(0x704ACA) == 0x19D99E0                                # the EVF's type byte
    t1, t2 = struct.unpack("<4I", fx(0x1FAD28, 16)), struct.unpack("<3I", fx(0xDC64DC, 12))
    assert [t2[t1[k]] for k in (1, 2, 3)] == [2, 0, 1]
    # the layout 0x1fa42c calls the fit function, then the de-squeeze calculator when de-squeeze is on (0x73518c), else the ratio function
    calls = [i.op_str for i in MD.disasm(fx(LAYOUT_FN, 0x2F4), LAYOUT_FN) if i.mnemonic == "bl"]
    for target in (FIT_FN, 0x73518C, DSQ_FN, RATIO_FN):
        assert "#%#x" % target in calls, hex(target)
    # frame tables: the A7 IV's, byte for byte, holding the stock 16:9 entry in row 1; each check function forms its table's address
    for _, t, t4, chk in TABLES:
        assert fx(t, TABLE_LEN) == a4(t4, TABLE_LEN)
        assert fx(t + 8 * (5 * ROW + COL), 8) == rect(RECT_STOCK)
    assert movw_movt(0x128558) == 0xF796D4 and movw_movt(0x128E28) == 0xF7974C and movw_movt(0x12994A) == 0xF797C4
    assert struct.unpack("<2d", fx(0x128628, 16)) == (480.0, 640.0) and fx(0x128578, 4) == bytes.fromhex("b1ee044b")   # 640 x 480 grid, 5.0
    assert struct.unpack("<8I", fx(0xD68940, 32)) == (2, 1, 0, 3, 0, 3, 0, 4)                                          # model aspect -> column
    # (b) the calculator reads the code at slot 0x798, tbb over codes 1..5 (code 4 lands on the defaults, code 5 on 0x1fa120)
    assert fx(0x1FA0D2, 4) == bytes.fromhex("d0f89817") and fx(0x1FA0E0, 6) == bytes.fromhex("01380428" "2ad8")
    assert fx(0x1FA0EE, 10) == bytes.fromhex("dfe800f0" "030d1c411700")
    assert struct.unpack("<3d", fx(0x1FA310, 24)) == (1.3, 1.5, 1.65)                                                 # the pillarbox factors
    assert fx(0x1FA110, 2) == bytes.fromhex("06d0")                        # code 2, 16:9: beq 0x1fa120 (code 5's ratio)
    assert insn(fx(0x1FA15C, 4), 0x1FA15C)[:2] == ("mov.w", "sl, #0xf")    # n 15: code 1's 4:3 case and code 3's 16:9 case
    # the menu sends codes 0, 1, 5: 0x1a191c builds 0x50100 >> 8 * setting
    assert movw_movt(0x1A1950) == 0x50100 and fx(0x1A194C, 2) == bytes.fromhex("022d")
    # the input command refuses a code >= 6 (VdfInputCmdSetDeSqueeze slot 4, 0x71b980): `cmp r0, #6` never matches a stored code
    assert fx(0x71B990, 6) == bytes.fromhex("0178062938bf")
    # (c) the crop function and (d) the device rectangle read the code at slot 0x798 just before each test
    assert fx(0x721E64, 4) == bytes.fromhex("d0f89817") and fx(0x721EAA, 4) == bytes.fromhex("00f0fe00")
    assert fx(0x72154C, 4) == bytes.fromhex("d0f89817") and fx(0x72155E, 4) == bytes.fromhex("d0f89817")
    # the FX3's form of the de-squeeze code tests is not the FX2's (its crop is 0x5faf04 with `cmp r0, #4` twice; no 0x7214b6 step)
    assert FX.count(bytes.fromhex("0078042809d0")) == 1


def design():
    check_context()
    new_img = bytearray(FX)
    notes = {}
    for a, old, new, what in CODE:
        got = insn(fx(a, 4), a)
        assert got and got[:2] == old, (hex(a), got, old)
        enc = bytes.fromhex(ENC[new])
        assert len(enc) == got[2] and insn(enc + b"\x00\x00", a)[:2] == new, (hex(a), new)
        new_img[a - B:a - B + len(enc)] = enc
        for k in range(len(enc)):
            if enc[k] != FX[a - B + k]:
                notes.setdefault((a + k) & ~3, []).append(what)
    sites = []
    for w in sorted(notes):
        old, new = fx(w, 4), bytes(new_img[w - B:w - B + 4])
        assert old != new
        sites.append({"ram_address": hex(w), "old": old.hex(), "new": new.hex(), "note": "; ".join(dict.fromkeys(notes[w]))})
    # every changed byte is in a site word, and nothing else changed
    changed = {k for k in range(len(FX)) if FX[k] != new_img[k]}
    assert changed == {k for s in sites for k in range(int(s["ram_address"], 16) - B, int(s["ram_address"], 16) - B + 4)
                       if FX[k] != new_img[k]}
    sites.insert(0, {"ram_address": hex(FIT_SITE), "old": "03000000", "new": "00000000",
                     "note": "VDF fit mode of a 16:9 picture (picture code 2) on a 3:2 panel (panel code 1): 3 letterbox -> 0 fill. The rear screen then "
                             "shows the squeezed 16:9 live view over the whole 3:2 panel, i.e. stretched x32/27 vertically: the 3:2 sensor area at "
                             "its true shape [A7 IV 0x1e4bcc, lcdfill_v2]"})
    assert fx(FIT_SITE, 4) == bytes.fromhex("03000000")
    for what, t, t4, chk in TABLES:
        e = t + 8 * (5 * ROW + COL)
        old, new = rect(RECT_STOCK), rect(RECT_NEW)
        for off, part in ((0, "x, y"), (4, "w, h")):
            sites.append({"ram_address": hex(e + off), "old": old[off:off + 4].hex(), "new": new[off:off + 4].hex(),
                          "note": "%s, check %#x: expected live-view rectangle for a 16:9 picture on the rear 3:2 panel (row 1), %s: stock letterbox "
                                  "%s -> the whole panel %s [A7 IV %#x, lcdfill_v2]" % (what, chk, part, RECT_STOCK, RECT_NEW, t4 + 8 * (5 * ROW + COL) + off)})
    G = lambda a, n, note: {"ram_address": hex(a), "bytes": fx(a, n).hex(), "note": note + ", as in the file"}
    guards = [G(FIT_FN, 16, "first 16 bytes of the fit-mode function 0x1f9e98 [A7 IV 0x1e4b78]"),
              G(0x1F9ED8, 16, "last 16 bytes of the fit-mode function before its tables [A7 IV 0x1e4bb8]"),
              G(FIT_TABLE, 4, "picture code 2 (16:9), panel code 0 (4:3: the EVF): 3 letterbox, left alone [A7 IV 0x1e4bc8]"),
              G(0x1F9EF0, 16, "picture code 2, panel codes 2 to 5: 0, 0, 0, 2 [A7 IV 0x1e4bd0]"),
              G(0x1F9F00, 16, "the table for picture code 1 (3:2), panel codes 0 to 3: 3, 0, 2, 0 [A7 IV 0x1e4be0]"),
              G(DSQ_FN, 16, "first 16 bytes of the de-squeeze calculator 0x1fa0c0"),
              G(0x1FA0D0, 16, "the calculator's read of the code (accessor slot 0x798)"),
              G(0x1FA0E0, 8, "the code's range check (code - 1 > 4: whole output) before code 4's ratio"),
              G(0x1FA0F0, 16, "the code table (tbb) and code 1's shape tests"),
              G(0x1FA100, 16, "code 1's 17:9 ratio and code 2's shape tests"),
              G(0x1FA110, 16, "code 2's 16:9 branch to code 5's ratio, and its 17:9 ratio"),
              G(0x1FA128, 16, "code 3's shape tests and 17:9 ratio"),
              G(0x1FA13C, 16, "the whole-output path for codes with no ratio"),
              G(0x1FA150, 4, "the branch before code 3's 16:9 ratio"),
              G(0x1FA158, 12, "code 1's 4:3 ratio (26, 15: the 15 code 3's 16:9 case shares)"),
              G(0x1FA16C, 8, "code 2's 4:3 ratio (2, 1)"),
              G(0x1FA28C, 16, "the height calculation (width x n + 2d) / d"),
              G(0x1FA310, 16, "the pillarbox factors 1.3, 1.5 (doubles)"),
              G(CROP_FN, 16, "first 16 bytes of the input-crop function 0x721e3c"),
              G(0x721E60, 16, "the crop function's read of the code and the path flag test"),
              G(0x721E74, 12, "the first crop path after its code test"),
              G(0x721EA0, 12, "the end of the first path before the second code test"),
              G(0x721EB0, 16, "the second crop path after its code test"),
              G(0x721EFC, 16, "the centre 4:3 width (4h + 6) / 3"),
              G(0x721544, 16, "the device rectangle's read of the code before its first test (0x7214b6)"),
              G(0x721558, 16, "between the device rectangle's two code tests"),
              G(0x72156C, 16, "the device rectangle's path after its code tests")]
    for what, t, t4, _ in TABLES:
        e = t + 8 * (5 * ROW + COL)
        guards += [G(e - 8, 8, "%s row 1, the entry before the 16:9 entry (1:1 on the rear panel: 107, 0, 426, 480)" % what.split(" ")[0]),
                   G(e + 8, 8, "%s row 1, the entry after the 16:9 entry (fifth aspect: 0, 50, 640, 380)" % what.split(" ")[0])]
    spans = sorted([(int(s["ram_address"], 16), 4, "s") for s in sites] + [(int(g["ram_address"], 16), len(g["bytes"]) // 2, "g") for g in guards])
    assert all(a + n <= b for (a, n, _), (b, _, _) in zip(spans, spans[1:])), "a guard overlaps a site or a guard"
    assert all(int(s["ram_address"], 16) % 4 == 0 and fx(int(s["ram_address"], 16), 4) == bytes.fromhex(s["old"]) and s["old"] != s["new"] for s in sites)
    assert all(int(g["ram_address"], 16) % 4 == 0 and len(g["bytes"]) // 2 <= 16 for g in guards)
    assert len(sites) == 18, len(sites)
    return {"design": NAME, "build": "fx2_101", "camera": "ILME-FX2 (FX2), firmware 1.01",
            "title": "FX2 1.01: rear screen (3:2 panel) shows the open-gate live view at 3:2 with the focus frames (the A7 IV's lcdfill_v2: fit word "
                     "and the frame widgets' 16:9 entries), and the built-in De-Squeeze Display ratios set for a 3:2 picture (1.3x 1.95:1, 2.0x the "
                     "whole frame at 3:1 with the centre 4:3 crop off; 1.65x 2.467:1, 1.8x 2.7:1)",
            "kind": "ram_words", "artifact": "cpapp-b.bin 1.01 (ILME-FX2), its loaded image in coprocessor RAM: the words are in the file, the change is made in RAM only",
            "artifact_sha256": SHA, "generated_by": "build/build_lcd_fx2.py",
            "ported_from": "lcdfill_v2 (A7 IV 6.02; works on that camera, F966/F969: the same seven words at the FX2's addresses, its fit function and "
                           "frame tables byte-identical) + the FX3 kit's de-squeeze part (lcd32dsq_fx3_v1), redone on the FX2's own calculator, crop "
                           "and device-rectangle code",
            "summary": {"sites": len(sites), "bytes": 4 * len(sites), "guards": len(guards),
                        "panel": "rear LCD, 3:2 (720 x 480, panel code 1 from type byte 3)",
                        "picture": "16:9 live view (aspect code 2) holding the whole 3:2 sensor area",
                        "fit_stock": "letterbox (3)", "fit_new": "fill (0)", "frame_rectangle_stock": list(RECT_STOCK), "frame_rectangle_new": list(RECT_NEW),
                        "desqueeze": {"code 1 (1.3x, menu)": "45/104 -> 20/39", "code 5 (2.0x, menu)": "3/8 -> 1/3, centre crop off",
                                      "code 3 (1.65x, not in the 1.01 menu)": "15/44 -> 15/37", "code 4 (1.8x, not in the menu)": "5/12 -> 10/27, centre crop off",
                                      "code 2 (1.5x, not in the menu)": "its 16:9 case uses code 5's words: 3:1 while applied"},
                        "goes_with": ["the FX2 open-gate state (A7 IV form: ogsq/outsz/ogfile steps of fx2_101)"]},
            "while_applied": "every 16:9 picture on the rear screen fills the 3:2 panel and the de-squeeze ratios are those of a 3:2 picture (other movie "
                             "formats look wrong there). Codes 4 and 5's ratios are the calculator's only ratio for every picture shape and their crop is off "
                             "for every shape. The EVF (4:3) shows the squeezed 16:9 picture with de-squeeze off, as on the A7 IV; with de-squeeze on it uses "
                             "the same new ratios. HDMI's own layout path (0x1fa728) and the device command's factor bytes (0x1fad38) are unchanged",
            "not_checked": ["on a camera: nothing of this design has run on an FX2",
                            "the FX2's rear panel type byte 0x19d98cc (expected 3 = 3:2 from Sony's 1,036,800 dots; a dump should read it)",
                            "that the frame widgets use row 1 on the FX2's rear panel (as on the A7 IV; the row comes from the widget object at run time)",
                            "what the output-device rectangle of 0x7214b6 is used for (inferred: the picture's place on the output for codes 4/5)",
                            "whether the focus frames are drawn while de-squeeze is on (stock behaves the same either way)"],
            "sites": sites, "guards": guards}


if __name__ == "__main__":
    d = design()
    out = ROOT / "modding" / "designs" / f"{NAME}.json"
    out.write_text(json.dumps(d, indent=1) + "\n", encoding="utf8", newline="\n")
    print("%s: %d sites, %d guards" % (out.name, len(d["sites"]), len(d["guards"])))
    for s in d["sites"]:
        print("  %s %s -> %s  %s" % (s["ram_address"], s["old"], s["new"], s["note"][:100]))
