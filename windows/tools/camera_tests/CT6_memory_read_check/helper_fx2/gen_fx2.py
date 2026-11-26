"""Write fx2_expected.h for fx2read.c from the FX2 1.01 files and the port designs (FX2 port of the FX3 kit's shape, 2026-11-25).

  work/venv/Scripts/python.exe -I -B gen_fx2.py

helper_fx3/gen_fx3.py with this build's files, designs and addresses (modding/FX2_PORT.md). The FX2 is the A7 IV's sensor on the A7C II's
platform, so its designs are the A7 IV's (ported like the A7C II kit's), while the helper and the kit's shape are the FX3 kit's.
Everything the helper compares against is taken here from the extracted 1.01 update and from modding/designs/{ogsq_fx2_v1,
outsz2560_fx2_v1, ogfile2560_hs_s_fx2_v2, lcd32dsq_fx2_v1, dmmwb4688_fx2_v1}.json. The helper holds no other constant about the camera
except the addresses listed at the top of this file.
  - The movie raw write buffer's four words (dmmwb4688_fx2_v1, the memory manager's RAM copy of DmmCfg.bin, filled at start-up) are
    hard sites, as in the ZV-E1 kit, so a check shows them stock or new.
  - The screen design's words are soft sites (reported, not counted), as in the FX3 kit: the screen step is optional (apply --no-screen).
Also writes fx2_expected.json (what the PC checks against) and fx2_reference.json (what the PC needs to read a dump). Read-only on the inputs.
"""
import hashlib
import json
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EX = ROOT / "work/extracted/fx2_101/0700_part_image/dev"
DES = ROOT / "modding/designs"
sys.path.insert(0, str(ROOT / "build"))
import build_ogfile  # noqa: E402
import parse_dmmcfg  # noqa: E402

BASE = 0x108000
LABEL = "fx2read_v3"                                  # v2 (2026-11-26, after the first FX2 test): test-design targets, DMM workspace, snapshot head;
                                                      # v3 (2026-11-26, after test 2 worked): the saved output records (page 0x15cd000)
# coprocessor addresses a read may have: its logs (tomco.txt, the A7 IV's), image and RAM tables, and (v2) the snapshot debug image's first
# pages (/cp/tomco.txt: snapshotdbg_addr=0x09A21E00, snapshotdbg_size=0x03000000, inside memcfg=0x7000000@0x09000000:uc)
CP_LO, CP_HI = 0xC0000, 0x9B00000
AVCAM_PHYS, AVCAM_RESERVE = 0x401000000, "@0x401000000"   # kemco.txt: memrsv=0x01000000@0x401000000:ex, as on the A7 IV and A7C II
ID_FILES = {"/libmpr.so": "nflasha15/lib/libmpr.so", "/libsencore.so": "nflasha15/lib/libsencore.so", "/libJiritsu.so": "nflasha15/lib/libJiritsu.so"}
# four 4 KB pages of coprocessor CODE that no design touches: a low code page, the record selector's (0x27ab64), the movie size table's
# set-up (0x4ff894) and the drive-parameter table map (constructor caller 0xa0fa1c); each differs from every other kit's body
ID_PAGES = (0x128000, 0x27A000, 0x4FF000, 0xA0F000)
# The A7 IV sensor's register matrix: 129 rows of 24 bytes (the register shadow's address, then one byte per column) and a zero row, then
# the column map (32 words, one per drive mode). Shadow addresses 0x12fe864..0x12fec5c.
MATRIX, MATRIX_ROWS, COLMAP, IDS, NMODES = 0x11EA560, 129, 0x11EB190, 0xE944B0, 32
RECS, REC = 0x24DD92C, 0x170
SIZE_TABLE = 0x18F60B0
DESIGNS = ("ogsq_fx2_v1", "outsz2560_fx2_v1", "ogfile2560_hs_s_fx2_v2", "lcd32dsq_fx2_v1", "dmmwb4688_fx2_v1")
OB = build_ogfile.OTHER_BUILDS["fx2_101"]
UNIT, DESC, DSIZE, CLIP = OB["unit"], OB["desc"], OB["dsize"], OB["clip"]
# The display pages the dump reads (the screen design's own addresses, build/build_lcd_fx2.py): taken from the design's sites and guards
# below, one page each. The rest, ported from the A7 IV's (build/port_addr.py a7iv_602 fx2_101):
DUMP_FIXED = (("shadow", 0x12FE000, 1), ("matrix", 0x11EA000, 2), ("sizetable", 0x18F6000, 1), ("records", 0x24DD000, 4),
              ("kprint", 0xE0000, 32), ("bootlog", 0xC0000, 8),
              # the resize state (A7 IV 0x1450000 + 3 pages: result 0x145091c, drive-parameter copy 0x1450bc4, module settings 0x1452480;
              # FX2 0x190cf38.. / 0x190d014 / 0x190ea40, the block's own layout moved, so the dump decoder searches it for known sizes) and
              # the resize working structure (A7 IV 0x11e1510, FX2 0x15e4298 / 0x15e42d0)
              ("resizestate", 0x190C000, 3), ("resizework", 0x15E4000, 1),
              # the memory manager (dmmwb4688_fx2_v1): its page of pointers 0x192f000, the unit records with the four sites 0x2483860.. and the
              # parent records 0x2481440..
              ("dmmglobals", 0x192F000, 1), ("dmmrecs", 0x2483000, 1), ("dmmparents", 0x2481000, 1),
              # the panel records: rear panel type byte 0x19d98cc (3 = a 3:2 panel), viewfinder 0x19d99fc (build/build_lcd_fx2.py)
              ("paneltype", 0x19D9000, 1),
              # v2: the memory manager's workspace, [0x192fc28] = 0x21a5d18 on the camera (the first test's L13 report), 0x35230 bytes as on the
              # A7 IV (build/dmm_dump.py): handle records, the unit objects at +0x107e0 (0x21b64f8, the L13 report), scene and group counters.
              # Objects of divisions merged back keep their contents for a while: which ids and sizes were opened lately, e.g. in movie.
              ("dmmworkspace", 0x21A5000, 54),
              # v3: the saved copy of the camera core's output records (A7 IV 0x11cf838, read by its level 15: format code 2 in 4K, F686), ported
              # by code reference to 0x15cd7e0 (build/port_addr.py, 6 of 6 references; 0xbc75de returns it to the output-buffer chooser 0x51cb38),
              # and the parameter view before it (A7 IV 0x11cf578 -> 0x15cd520). Per output (stride 0x2c from +4): w, h at +4/+6, format code at
              # +0x20 (picture bytes x1 / x1.25 / x1.5 / x2 for codes 1-4, 0x51ee00), type word at +0x28 (2: the FX2-only "rc_out" case, 1: 0x4c3/0x4c4)
              ("outrecs", 0x15CD000, 2))
# v2: read LAST, because a failed read stops every read after it: the first four pages of the snapshot debug image, which the coprocessor
# saves on an exception ('Snapshot Debug Image Saved' in the first test's kprint record; the code's tag 'SOLID_SSHOT')
DUMP_LAST = (("snapshot", 0x9A21000, 4),)
TEST_DESIGNS = ("fhband_fx2_v1",)                    # v2: a sensor site may hold a test design's bytes instead (reported TEST)


def c_bytes(b):
    return "{" + ",".join(str(x) for x in b) + "}"


def design(n):
    return json.loads((DES / f"{n}.json").read_text(encoding="utf8"))


def main():
    cp = (EX / "nflasha8/cpapp-b.bin").read_bytes()
    av = (EX / "nflasha3/av-cam.bin").read_bytes()
    lm = (EX / "nflasha15/lib/libmpr.so").read_bytes()
    og, oz, fl, sc, dm = (design(n) for n in DESIGNS)
    dcfg = parse_dmmcfg.Config(parse_dmmcfg.find_file("fx2_101"), "fx2_101")
    sha_cp = hashlib.sha256(cp).hexdigest()
    assert og["artifact_sha256"] == sha_cp and og["build"] == "fx2_101"
    assert all(d.get("build") == "fx2_101" for d in (oz, fl, sc, dm))
    assert fl["artifact_sha256"] == {"libmpr.so": hashlib.sha256(lm).hexdigest(), "av-cam.bin": hashlib.sha256(av).hexdigest()}
    out, blobs = [], []

    def blob(b):
        blobs.append(f"static const unsigned char B{len(blobs)}[] = {c_bytes(b)};")
        return f"B{len(blobs) - 1}"

    out.append(f'#define FX2_LABEL "{LABEL}"\n#define CP_LO {CP_LO:#x}U\n#define CP_HI {CP_HI:#x}U\n#define AVCAM_PHYS {AVCAM_PHYS:#x}UL\n'
               f'#define AVCAM_RESERVE "{AVCAM_RESERVE}"')
    out.append("struct id_file { const char *name; unsigned char sha256[32]; };\nstruct id_page { unsigned int address; unsigned char sha256[32]; };\n"
               "struct cp_site { const char *name; unsigned int address, length; const unsigned char *stock, *target; int soft; const unsigned char *alt; };\n"
               "struct mp_site { unsigned long offset; unsigned int length; const unsigned char *stock, *target; };\n"
               "struct av_guard { const char *name; unsigned long offset; unsigned int length; unsigned char sha256[32]; };\n"
               "struct dump_range { const char *name; unsigned int address, pages; };")
    rows = [f'    {{"{n}", {c_bytes(hashlib.sha256((EX / p).read_bytes()).digest())}}},' for n, p in ID_FILES.items()]
    out.append("static const struct id_file id_files[] = {\n" + "\n".join(rows) + "\n};")
    # ---- coprocessor sites
    sites, alt = [], {}
    for tn in TEST_DESIGNS:                              # the test design's new bytes at the same sites (the same 13 sites and the stored record)
        td = design(tn)
        assert td["artifact_sha256"] == sha_cp and td["mode_index"] == og["mode_index"]
        assert sorted(int(q["addr"], 16) for q in td["patches"]) == sorted(int(q["addr"], 16) for q in og["patches"])
        for q in td["patches"]:
            alt[int(q["addr"], 16)] = bytes.fromhex(q["new"])
        alt[int(td["stored_record"]["address"], 16)] = bytes.fromhex(td["stored_record"]["design"])
    for p in og["patches"]:
        a, old, new = int(p["addr"], 16), bytes.fromhex(p["old"]), bytes.fromhex(p["new"])
        assert cp[a - BASE:a - BASE + len(old)] == old and len(old) == len(new)
        name = p["note"].split(" ")[0] if p["kind"] == "S" else ("record_left" if "left" in p["note"] else "record_right")
        sites.append((name, a, old, new, 0))
    sr = og["stored_record"]
    assert int(sr["address"], 16) == RECS + og["mode_index"] * REC
    # soft: the camera fills parts of this record at run time, so it need not equal the emulated one; reported, not counted
    sites.append(("stored_record", int(sr["address"], 16), bytes.fromhex(sr["stock"]), bytes.fromhex(sr["design"]), 1))
    for s in oz["sites"]:                                 # soft: the size table is zero until a movie mode has run
        sites.append(("outsize", int(s["ram_address"], 16), bytes.fromhex(s["old"]), bytes.fromhex(s["new"]), 1))
    for k, g in enumerate(oz["guards"]):
        sites.append((f"outsize_guard{k}", int(g["ram_address"], 16), bytes.fromhex(g["bytes"]), None, 1))
    for k, s in enumerate(sc["sites"]):                   # soft: the screen step is optional (apply --no-screen); reported, not counted
        a, old = int(s["ram_address"], 16), bytes.fromhex(s["old"])
        if BASE <= a < BASE + len(cp):
            assert cp[a - BASE:a - BASE + 4] == old
        sites.append((f"screen{k}", a, old, bytes.fromhex(s["new"]), 1))
    for k, s in enumerate(dm["sites"]):                   # the memory manager's RAM copy is filled from DmmCfg.bin at start-up: not soft
        kind = "size" if int.from_bytes(bytes.fromhex(s["old"]), "little") == 27864320 else "key"
        sites.append((f"rawbuf_{kind}{k}", int(s["ram_address"], 16), bytes.fromhex(s["old"]), bytes.fromhex(s["new"]), 0))
    pages = {x & ~0xFFF for _, a, o, _, _ in sites for x in (a, a + len(o) - 1) if a < BASE + len(cp)}
    assert not any(p in pages for p in ID_PAGES), "an identity page holds a design site"
    rows = [f"    {{{a:#x}, {c_bytes(hashlib.sha256(cp[a - BASE:a - BASE + 4096]).digest())}}}," for a in ID_PAGES]
    out.append("static const struct id_page id_pages[] = {\n" + "\n".join(rows) + "\n};")
    rows = []
    for name, a, old, new, soft in sites:
        assert CP_LO <= a and a + len(old) <= CP_HI and len(old) <= 3072
        al = alt.get(a) if not name.startswith(("outsize", "screen", "rawbuf")) else None
        assert al is None or len(al) == len(old)
        rows.append(f'    {{"{name}", {a:#x}, {len(old)}, {blob(old)}, {blob(new) if new is not None else "0"}, {soft}, {blob(al) if al is not None else "0"}}},')
    out.append("static const struct cp_site cp_sites[] = {\n" + "\n".join(rows) + "\n};")
    # ---- main-processor sites
    lmr, avr, av_hi = [], [], 0
    for p in fl["patches"]:
        o, old, new = int(p["file_off"], 16), bytes.fromhex(p["old"]), bytes.fromhex(p["new"])
        src = lm if p["binary"] == "libmpr.so" else av
        assert src[o:o + len(old)] == old
        (lmr if p["binary"] == "libmpr.so" else avr).append(f"    {{{o:#x}UL, {len(old)}, {blob(old)}, {blob(new)}}},")
        if p["binary"] == "av-cam.bin":
            av_hi = max(av_hi, o + len(old))
    out.append("static const struct mp_site lm_sites[] = {\n" + "\n".join(lmr) + "\n};")
    out.append("static const struct mp_site av_sites[] = {\n" + "\n".join(avr) + "\n};")
    spans = [(int(p["file_off"], 16), len(p["old"]) // 2) for p in fl["patches"] if p["binary"] == "av-cam.bin"]
    # four descriptors in a row that no site touches (on the FX2 descriptors 0..3 hold sites: its table has another order than the FX3's)
    free = lambda k: all(DESC + DSIZE * (k + 4) <= so or so + sn <= DESC + DSIZE * k for so, sn in spans)
    d0 = next(k for k in range(OB["ndesc"] - 4) if free(k))
    guards = (("unit_rows_0_2", UNIT, 0x30), ("clip_rows_2_7", CLIP + 0x20, 0x60), (f"descriptors_{d0}_{d0 + 3}", DESC + DSIZE * d0, 4 * DSIZE))
    rows = []
    for name, o, n in guards:
        assert all(o + n <= so or so + sn <= o for so, sn in spans), name
        rows.append(f'    {{"{name}", {o:#x}UL, {n}, {c_bytes(hashlib.sha256(av[o:o + n]).digest())}}},')
        av_hi = max(av_hi, o + n)
    out.append("static const struct av_guard av_guards[] = {\n" + "\n".join(rows) + "\n};")
    av_lo = min([so for so, _ in spans] + [o for _, o, _ in guards]) & ~0xFFF
    out.append(f"#define AV_LO {av_lo:#x}UL\n#define AV_HI {av_hi:#x}UL")
    # the dump's display pages: every page holding a screen site or guard
    disp_pages = sorted({int(x["ram_address"], 16) & ~0xFFF for x in sc["sites"] + sc["guards"]})
    dump_ranges = list(DUMP_FIXED) + [(f"display{k}", p, 1) for k, p in enumerate(disp_pages)] + list(DUMP_LAST)
    rows = [f'    {{"{n}", {a:#x}, {k}}},' for n, a, k in dump_ranges]
    assert all(CP_LO <= a and a + 4096 * k <= CP_HI for _, a, k in dump_ranges)
    starts = sorted((a, a + 4096 * k) for _, a, k in dump_ranges)
    assert all(e <= s for (_, e), (s, _) in zip(starts, starts[1:])), "two dump ranges overlap"
    out.append("#if DUMP\nstatic const struct dump_range dump_ranges[] = {\n" + "\n".join(rows) + "\n};\n#endif")
    text = ("/* Generated by gen_fx2.py from the FX2 1.01 files and the port designs. Do not edit. */\n#ifndef DUMP\n#define DUMP 0\n#endif\n"
            + "\n".join(blobs) + "\n" + "\n".join(out) + "\n")
    (HERE / "fx2_expected.h").write_text(text, encoding="utf8", newline="\n")
    facts = {"label": LABEL, "cp_lo": CP_LO, "cp_hi": CP_HI, "avcam_phys": AVCAM_PHYS, "avcam_reserve": AVCAM_RESERVE,
             "id_files": {n: hashlib.sha256((EX / p).read_bytes()).hexdigest() for n, p in ID_FILES.items()},
             "id_pages": {hex(a): hashlib.sha256(cp[a - BASE:a - BASE + 4096]).hexdigest() for a in ID_PAGES},
             "cp_sites": [{"name": n, "address": hex(a), "length": len(o), "soft": s} for n, a, o, _, s in sites],
             "lm_sites": len(lmr), "av_sites": len(avr), "av_guards": [g[0] for g in guards], "dump_ranges": [[n, hex(a), k] for n, a, k in dump_ranges],
             "designs": {d["design"]: hashlib.sha256((DES / (d["design"] + ".json")).read_bytes()).hexdigest() for d in (og, oz, fl, sc, dm)}}
    (HERE / "fx2_expected.json").write_text(json.dumps(facts, indent=1) + "\n", encoding="utf8", newline="\n")
    # ---- what the PC needs to read a dump without the firmware files
    matrix = []
    for k in range(MATRIX_ROWS):
        a = struct.unpack_from("<I", cp, MATRIX - BASE + 24 * k)[0]
        assert 0x12FE000 <= a < 0x12FF000
        matrix.append([a, cp[MATRIX - BASE + 24 * k + 4:MATRIX - BASE + 24 * k + 24].hex()])
    assert not any(cp[MATRIX - BASE + 24 * MATRIX_ROWS:MATRIX - BASE + 24 * MATRIX_ROWS + 24]) and MATRIX + 24 * (MATRIX_ROWS + 1) == COLMAP
    emu = json.loads((ROOT / "evidence/fx2/drvparam_stock_fx2_101.json").read_text(encoding="utf8"))["modes"]
    ref = {"about": "FX2 1.01 reference data for reading an fx2read dump; from cpapp-b.bin and build/emu_drvparam.py fx2_101", "matrix_address": hex(MATRIX),
           "matrix_row_bytes": 24, "matrix": matrix, "column_map": list(struct.unpack_from("<%dI" % NMODES, cp, COLMAP - BASE)),
           "mode_ids": [hex(x) for x in struct.unpack_from("<%dI" % NMODES, cp, IDS - BASE)], "records_address": hex(RECS), "record_size": REC,
           "emulated_stock_records": {m: v["record"] for m, v in emu.items()}, "size_table_address": hex(SIZE_TABLE),
           "stored_record_design": {"mode": og["mode_id"], "index": og["mode_index"], "stock": sr["stock"], "design": sr["design"]},
           "screen_words": [{"address": s["ram_address"], "stock": s["old"], "new": s["new"], "note": s.get("note", "")} for s in sc["sites"]],
           "screen_design": sc["design"],
           "raw_write_buffer": [{"address": s["ram_address"], "stock": s["old"], "new": s["new"]} for s in dm["sites"]],
           "ram": {"resize_result_a7iv": "0x145091c (FX2 not confirmed; the dump searches 0x190c000.. for known sizes)",
                   "resize_settings": "0x190ea40", "resize_work": "0x15e4298", "shadow_reg_0x01_a7iv": "0x1033c7e"},
           # v2: the test designs' stored-record bytes, and what the PC needs to read the memory manager's workspace without the firmware files
           "test_designs": {tn: {"stored_record_design": design(tn)["stored_record"]["design"], "title": design(tn)["title"]} for tn in TEST_DESIGNS},
           "dmm": {"workspace_pointer": "0x192fc28", "units_pointer": "0x192f77c", "workspace_expected": "0x21a5d18", "units_at": 0x107E0,
                   "workspace_bytes": 0x35230, "objects": 0x580, "object_bytes": 0x50, "handles": 0x3FF, "handle_bytes": 0x40,
                   "scene_index_at": 0x33410, "scene_stack_at": 0x33418, "group_use_at": 0x33428,
                   "ids_by_key": {hex(k): [hex(i) for i in v] for k, v in sorted(dcfg.ids_by_key.items())},
                   "unit_sizes_by_key": {hex(k): sorted({u["size"] for u in v}) for k, v in sorted(dcfg.units_by_key.items())},
                   "note": "unit objects of 0x50 bytes: +0 index u16, +2 flags u16 (bit 0 divided), +8 base u64, +0x10 offset, +0x14 size, +0x20 parent object, "
                           "+0x24 key, +0x28 owner handle, +0x30 group it is divided as (build/dmm_dump.py, A7 IV layout; on the FX2 the unit objects' offset "
                           "+0x107e0 was confirmed by the first test's L13 report)"},
           "output_records": {"template": "0x15cd7e0", "first_record": "0x15cd7e4", "stride": 0x2C, "records": 4, "w_at": 4, "h_at": 6, "code_at": 0x20,
                              "type_at": 0x28, "factor_by_code": {"1": 1.0, "2": 1.25, "3": 1.5, "4": 2.0},
                              "buffers": {"0x2d9": 13271040, "0x4c4": 13271040, "0x4c3": 3317760, "0x295": 3317760, "0x43f": None, "0x69c": None},
                              "note": "0x51cb38 / 0x51cc58 (FX2): records 1-3 choose their buffer id from w x h x factor: type 1 -> 0x4c3 below 3,317,761 bytes else 0x4c4; type 2 -> 0x69c below it else 0x2d9 with the log line FW: error! rc_out[%d] image data size excerrd mem size; otherwise for 0x295/0x43f/0x2d9: 13,271,041 or more -> 0x43f (no row in the FX2 DmmCfg.bin), more than 3,317,760 -> 0x2d9, else 0x295"},
           "snapshot": {"address": "0x9a21e00", "size": "0x3000000", "tag": "SOLID_SSHOT",
                        "note": "the coprocessor's snapshot debug image (/cp/tomco.txt); its format is not known: the dump copies its first pages"}}
    assert len(ref["emulated_stock_records"]) == NMODES
    (HERE / "fx2_reference.json").write_text(json.dumps(ref) + "\n", encoding="utf8", newline="\n")
    print(f"fx2_expected.h: {len(sites)} coprocessor sites ({len(sc['sites'])} of the screen, {len(dm['sites'])} of the raw write buffer), "
          f"{len(lmr)} libmpr sites, {len(avr)} av-cam sites, {len(dump_ranges)} dump ranges, {len(text)} bytes of header")


if __name__ == "__main__":
    main()
