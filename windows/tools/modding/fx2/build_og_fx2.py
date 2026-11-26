"""FX2 1.01 (fx2_101) versions of the A7 IV 6.02 sensor-and-record designs (FX2 port, 2026-11-25).

  work/venv/Scripts/python.exe -I -B build/build_og_fx2.py     (needs Unicorn: run with C:\\Python313\\python.exe -B if the venv lacks it)

writes ogsq_fx2_v1 (mode 0x8c0, 23.98p) and ogsq880_fx2_v1 (mode 0x880, PAL 25p) to modding/designs/, and their stored-record evidence
to evidence/fx2/<name>_drvparam_records_emu.json.

The FX2 is the A7 IV's sensor on the A7C II's platform. What is carried over, and why it is allowed (all asserted below against the
A7 IV 6.02 and FX2 1.01 cpapp-b.bin):
  - The FX2 has the A7 IV's 30 drive modes in the same order with two more inserted at index 25 (0x2821, 0x28c1, after 0x8c1).
    Modes 0x880 and 0x8c0 keep their indices (9 and 10), so every per-mode table row of the design is the same row number.
  - The crop, stream-0 window, stream-1 window, LC rows and the sensor column map rows of modes 0x880/0x8c0 equal the A7 IV's; the
    read-out table has 20-byte rows (one more field, 8, as on the A7C II) whose fields 0..17 equal the A7 IV's; the first 16 geometry
    rows (the design changes row 6) equal the A7 IV's. The register matrix equals the A7 IV's but for each row's leading pointer
    (relocated); the design changes only the column map.
  - The record selector 0x27ab64 (= A7C II 0x2731f8; build/emu_record_selector.py fx2_101) gives modes 0x8c0 AND 0x880 the same
    pair of image-mode records, 0xdf9958 (left) / 0xdfa510 (right). They equal the A7 IV's stock 0x8c0 records except five words:
    +0x328 and +0x3b8 (line-length words, unset as on the A7C II) and +0x948..+0x950 (pointers into the image). The A7 IV designs
    change none of those five, so the FX2 record = the A7 IV design's new record with those five words kept.
  - The stored drive-parameter record is 0x170 bytes (as on the A7C II); it is emulated with the FX2's own calculator 0x3d3024
    (build/emu_drvparam.py fx2_101), stock and with the design's S cells. Its 29 stock records of the modes the A7C II also has
    equal the A7C II's but for mode 0x8000.
  - Timing: the FX2's 4K rows are the A7C II's (HMAX 500; 0x8c0 VMAX 3000 at 23.98p). The design does not change timing; the
    full-height read-out (2,382 line periods) fits 3000 lines. On the FX2's 50 Hz table mode 0x8c0 is 24.00p (VMAX 3000, no fraction).
NOT known: anything on a camera; nothing has run on an FX2.
"""
import hashlib
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "build"))
import locate_file  # noqa: E402
import emu_drvparam  # noqa: E402

B = 0x108000
A = locate_file.locate("a7iv_602", "cpapp-b.bin").read_bytes()
F = locate_file.locate("fx2_101", "cpapp-b.bin").read_bytes()
SHA_F = hashlib.sha256(F).hexdigest()
SHA_A = hashlib.sha256(A).hexdigest()
IDS_A, IDS_F = 0xC98330, 0xE944B0
NEW_MODES = (0x2821, 0x28C1)                  # inserted at index 25 on the FX2
# (A7 IV base, FX2 base, A7 IV row bytes, FX2 row bytes, rows, name)
TABLES = [(0xC3DC40, 0xE40700, 12, 12, 16, "geometry rows"),
          (0xC983A8, 0xE94530, 20, 20, 25, "crop"),
          (0xD95AAC, 0xF98F24, 38, 38, 25, "stream-0 window"),
          (0xD95F20, 0xF993E4, 38, 38, 25, "stream-1 (aux) window"),
          (0xD96394, 0xF998A4, 14, 14, 25, "LC"),
          (0xD96538, 0xF99A64, 18, 20, 25, "readout"),
          (0xFB401C, 0x11EB190, 4, 4, 25, "sensor column map")]
REC_A = {0x8C0: (0xBF7638, 0xBF81F0), 0x880: (0xBF5EC8, 0xBF6A80)}
REC_F = (0xDF9958, 0xDFA510)                  # both modes on the FX2
KEEP = (0x328, 0x3B8, 0x948, 0x94C, 0x950)    # record words that are the FX2's own


def a(buf, addr, n):
    return buf[addr - B:addr - B + n]


def check_modes():
    ia = list(struct.unpack_from("<30I", A, IDS_A - B))
    iF = list(struct.unpack_from("<32I", F, IDS_F - B))
    assert iF == ia[:25] + list(NEW_MODES) + ia[25:], "the FX2's mode table is not the A7 IV's with 0x2821/0x28c1 at index 25"
    return iF


def map_site(addr, n):
    for ba, bf, ra, rf, rows, name in TABLES:
        if ba <= addr < ba + ra * rows:          # rows: only rows below the insertion point (or the checked geometry rows)
            row, field = divmod(addr - ba, ra)
            dst = bf + rf * row + field
            ra_row, rf_row = a(A, ba + ra * row, ra), a(F, bf + rf * row, rf)
            assert rf_row[:ra] == ra_row, f"{name} row {row}: the rows differ ({ra_row.hex()} / {rf_row.hex()})"
            assert field + n <= ra
            return dst, name, row
    raise SystemExit(f"site {addr:#x} is in no known table")


def build(src, mode, name):
    d = json.loads((ROOT / "modding/designs" / f"{src}.json").read_text(encoding="utf8"))
    assert d["artifact_sha256"] == SHA_A
    ids = check_modes()
    idx = ids.index(mode)
    assert idx == struct.unpack_from("<30I", A, IDS_A - B).index(mode)
    # the first 16 geometry rows, and the register matrix but for each row's leading pointer
    assert a(A, 0xC3DC40, 12 * 16) == a(F, 0xE40700, 12 * 16)
    ma, mf = a(A, 0xFB401C - 130 * 24, 130 * 24), a(F, 0x11EB190 - 130 * 24, 130 * 24)
    assert all(ma[24 * r + 4:24 * r + 24] == mf[24 * r + 4:24 * r + 24] for r in range(130)), "the register matrices differ"
    patches, cells = [], []
    for p in d["patches"]:
        ad, old, new = int(p["addr"], 16), bytes.fromhex(p["old"]), bytes.fromhex(p["new"])
        assert a(A, ad, len(old)) == old
        if p["kind"] == "S":
            dst, tname, row = map_site(ad, len(old))
            assert a(F, dst, len(old)) == old, (p["note"], hex(dst))
            if tname != "geometry rows":
                assert row == idx, f"{p['note']}: row {row}, mode index {idx}"
            patches.append({**p, "addr": hex(dst), "note": p["note"] + f" [A7 IV {ad:#x}; {tname} row {row}]"})
            cells.append((dst, new))
        elif p["kind"] == "R":
            side = REC_A[mode].index(ad)
            dst = REC_F[side]
            fold = bytearray(a(F, dst, 3000))
            for o in range(0, 3000, 4):
                if o not in KEEP:
                    assert fold[o:o + 4] == old[o:o + 4], f"record {dst:#x} +{o:#x} differs from the A7 IV's stock"
            assert all(old[o:o + 4] == new[o:o + 4] for o in KEEP), "the A7 IV design changes a word the FX2 keeps"
            fnew = bytearray(new)
            for o in KEEP:
                fnew[o:o + 4] = fold[o:o + 4]
            patches.append({**p, "addr": hex(dst), "old": bytes(fold).hex(), "new": bytes(fnew).hex(),
                            "note": p["note"] + f" [A7 IV {ad:#x}; on the FX2 this pair serves modes 0x8c0 and 0x880; words "
                                                f"{', '.join(hex(o) for o in KEEP)} kept as the FX2's]"})
        else:
            raise SystemExit(p["kind"])
    assert len(patches) == 13 and sum(len(p["old"]) // 2 for p in patches) == 6024
    pal = mode == 0x880
    base = []
    if pal:                                     # PAL family: the 50 Hz timing table over the 60 Hz one, as a camera set to PAL reads it
        f = emu_drvparam.CONSTS["fx2_101"]["fields"]
        base = [(f[0x2C], a(F, f[0x30], 24 * 32))]
    stock, log1 = emu_drvparam.records("fx2_101", base)
    des, log2 = emu_drvparam.records("fx2_101", base + cells)
    assert not log1 and not log2, (log1, log2)
    s_rec, d_rec = bytearray(stock[mode][1]), bytearray(des[mode][1])
    assert stock[mode][2] is None and des[mode][2] is None
    assert any(stock[m][1] != des[m][1] for m in (mode,)), "the S cells do not reach the stored record"
    for x in d.get("stored_record_extra", []):
        o = int(x["offset"], 16)
        assert s_rec[o] == int(x["old"], 16) and d_rec[o] == int(x["old"], 16)
        d_rec[o] = int(x["new"], 16)
    offs = [k for k in range(len(s_rec)) if s_rec[k] != d_rec[k]]
    # the A7C II's port of the same design: the FX2's stock record of this mode equals the A7C II's, so its design record must too
    c2 = ROOT / "evidence/pipeline" / f"{name.replace('_fx2_v1', '_c2_v1')}_drvparam_records_emu.json"
    same_as_c2 = None
    if c2.exists():
        r = json.loads(c2.read_text(encoding="utf8"))
        same_as_c2 = (r["stock_record_10"] == bytes(s_rec).hex(), r["design_record_10"] == bytes(d_rec).hex())
    other_modes_changed = [hex(m) for m in stock if m != mode and stock[m][1] != des[m][1]]
    rec_json = {"about": f"Stored drive-parameter record of mode {mode:#x} (index {idx}) for {name} on the FX2 1.01: the FX2's own calculator "
                         f"0x3d3024 run alone (build/emu_drvparam.py fx2_101), stock and with the design's S cells"
                         + (", with the PAL (50 Hz) timing table in place of the 60 Hz one" if pal else "") + "; plus the design's stored_record_extra bytes",
                "build": "fx2_101", "mode_id": hex(mode), "mode_index": idx, "record_bytes": len(s_rec),
                "records_base_in_emulation": hex(emu_drvparam.CONSTS["fx2_101"]["fields"][0x10]),
                "mode_ids_at": hex(IDS_F), "stock_record_10": bytes(s_rec).hex(), "design_record_10": bytes(d_rec).hex(),
                "bytes_that_differ": len(offs), "offsets_that_differ": str([hex(k) for k in offs]),
                "equal_to_a7c2_port_stock_and_design": same_as_c2,
                "other_modes_whose_record_the_cells_change": other_modes_changed}
    ev = ROOT / "evidence/fx2"
    ev.mkdir(exist_ok=True)
    (ev / f"{name}_drvparam_records_emu.json").write_text(json.dumps(rec_json, indent=1) + "\n", encoding="utf8", newline="\n")
    out = {k: v for k, v in d.items() if k not in ("patches", "artifact_sha256", "generated_by", "moved_from", "mode_id", "mode_index")}
    out.update({"design": name, "build": "fx2_101", "title": d["title"] + " (FX2 1.01 port)", "artifact_sha256": SHA_F,
                "generated_by": f"build/build_og_fx2.py (from {src} of a7iv_602)", "ported_from": {"design": src, "build": "a7iv_602"},
                "mode_id": hex(mode), "mode_index": idx, "patches": patches, "record_size": len(s_rec),
                "stored_record": {"bytes": len(s_rec), "offsets_that_differ": [hex(k) for k in offs],
                                  "address": hex(emu_drvparam.CONSTS["fx2_101"]["fields"][0x10] + idx * len(s_rec)),
                                  "address_note": "records base 0x24dd92c (the table map's +0x10, constructor caller 0xa0fa1c) + index x 0x170; "
                                                  "RAM, filled by the camera at start-up; level 5 finds it through the pointer chain",
                                  "stock": bytes(s_rec).hex(), "design": bytes(d_rec).hex(),
                                  "evidence": f"evidence/fx2/{name}_drvparam_records_emu.json"}})
    (ROOT / "modding/designs" / f"{name}.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf8", newline="\n")
    print(f"{name}: from {src}, mode {mode:#x} index {idx}; 13 sites, 6024 bytes; stored record {len(s_rec):#x} bytes, {len(offs)} differ: "
          f"{[hex(k) for k in offs]}; equal to the A7C II port (stock, design): {same_as_c2}; other modes changed: {other_modes_changed}")
    return offs


if __name__ == "__main__":
    # fhband_fx2_v1 (2026-11-26, after the first FX2 test crashed on movie entry): the A7 IV's fhband_v1 (F658: full-height read-out, the stock
    # 16:9 band kept, stage height stock), the second kit's test 1. It needs no stored_record_extra.
    # ogh2560_fx2_v1 (2026-11-26, fourth kit): the A7 IV's ogh2560_v1 (F712, F713: the first-stage scaler gives 4336x2560 instead of 4336x2438).
    # It differs from ogsq_v3 only in the two records. Why the FX2 needs it: its resize set-up 0x51fbc0 raises the first-scaler size it hands
    # the second scaler to at least the output size (0xbd3a32, FX2 and A1 II only), so with the 3840x2560 output size the records must give
    # 2,560 rows too (modding/FX2_PORT.md, "Why L16 crashed").
    for src, mode, name in (("ogsq_v3", 0x8C0, "ogsq_fx2_v1"), ("ogsq880_v1", 0x880, "ogsq880_fx2_v1"), ("fhband_v1", 0x8C0, "fhband_fx2_v1"),
                            ("ogh2560_v1", 0x8C0, "ogh2560_fx2_v1")):
        build(src, mode, name)
