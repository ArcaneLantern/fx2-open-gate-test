"""Build `outsz2560_fx2_v1`: the FX2 1.01 (fx2_101) counterpart of the A7 IV's working `outsz2560_v1` (FX2 port, 2026-11-25).

  C:/Python313/python.exe -B build/build_ram_words_fx2.py      writes modding/designs/outsz2560_fx2_v1.json and _pokes_ram.txt

One word of coprocessor RAM, the 4K movie request's output size: 3840 x 2160 -> 3840 x 2560. How the FX2's address was found:
  - The movie size table is filled at run time by 0x4ff894. It is NOT the A7C II's 0x4b7354 relinked (match_thumb finds nothing; match_seed
    points at it with 12 votes, then read): the same head and the same entry values, but three more saved registers, a second settings block
    0x196aa58 it reads, the fields after +0x1c moved by 4 and a 0x30-byte block cleared at +0x54. build/emu_size_table.py fx2_101 runs it
    alone (calls stubbed, settings zero): base 0x18f6028, table at base + 0x88 = 0x18f60b0, and its 16 entries equal the A7C II's
    (one class more than the A7 IV's: 8192 x 4320 is class 1).
  - The reader that picks the entry for a movie request (0x51fca6, tbh on the request's size class [r5 + 0x9c], as the A7C II's 0x4d436c on
    [r6 + 0x94]) loads base + 0xd0 = 0x18f60f8 in case 3 (UHD), as the A7C II's case 3 loads its base + 0x98 = 0x1a531c8. Both switches are
    decoded below from the files, so the case numbering is checked, not assumed.
  - The output buffer of that entry, memory id 0x2d9, is 9 units of 13,271,040 bytes in the FX2's DmmCfg.bin, as on the A7 IV; a 3840 x 2560
    picture at format code 2 (x 1.25 bytes per pixel, read on the A7 IV camera in its stock 4K, not on an FX2) is 12,288,000 bytes.
Guards, as on the A7 IV and A7C II: the entry before (3840, 2160, memory id 0x43e) and this entry's memory id (0x2d9).
Design only; nothing has run on an FX2.
"""
import hashlib
import json
import struct
import sys
from pathlib import Path

import capstone

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "build"))
import emu_size_table  # noqa: E402
import locate_file  # noqa: E402
import parse_dmmcfg as P  # noqa: E402

B = 0x108000
BUILD, NAME = "fx2_101", "outsz2560_fx2_v1"
IMG = locate_file.locate(BUILD, "cpapp-b.bin").read_bytes()
SHA = hashlib.sha256(IMG).hexdigest()
# (switch address of the tbh, its bound, the base register value, the offset case 3 loads)
READERS = {"fx2_101": (0x51FCA6, 0xC, 0x18F6028, 0xD0), "a7c2_201": (0x4D436C, 0xC, 0x1A53130, 0x98)}


def case_load(build, case):
    """Decode the reader's tbh switch from the file: the address it jumps to for `case`, and the base and offset that case loads."""
    sw, bound, base, _ = READERS[build]
    img = IMG if build == BUILD else locate_file.locate(build, "cpapp-b.bin").read_bytes()
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
    pre = list(md.disasm(img[sw - 4 - B:sw + 4 - B], sw - 4))          # cmp r0, #bound (16-bit); bhi (16-bit); tbh
    assert [i.mnemonic for i in pre] == ["cmp", "bhi", "tbh"] and pre[0].op_str.endswith("#%#x" % bound), pre
    entries = struct.unpack_from("<%dH" % (bound + 1), img, sw + 4 - B)
    target = sw + 4 + 2 * entries[case]
    ins = list(md.disasm(img[target - B:target + 12 - B], target))[:3]
    assert [i.mnemonic for i in ins][:2] == ["movw", "movt"] and ins[2].mnemonic in ("ldr", "ldr.w"), ins
    lo, hi = int(ins[0].op_str.split("#")[1], 0), int(ins[1].op_str.split("#")[1], 0)
    off = int(ins[2].op_str.split("#")[1].rstrip("]"), 0)
    assert (hi << 16 | lo) == base, (build, hex(hi << 16 | lo))
    return target, base, off


def main():
    t, rows, writes = emu_size_table.table(BUILD)
    t_c, rows_c, _ = emu_size_table.table("a7c2_201")
    assert t == 0x18F60B0 and rows == rows_c, "the FX2's table differs from the A7C II's"
    assert rows[8] == (3840, 2160, 0x43E) and rows[9] == (3840, 2160, 0x2D9)
    site = t + 8 * 9
    tgt, base, off = case_load(BUILD, 3)
    tgt_c, base_c, off_c = case_load("a7c2_201", 3)
    assert base + off == site and base_c + off_c == 0x1A531C8 == t_c + 8 * 9, "case 3 does not load the second 3840 x 2160 entry"
    others = {c: case_load(BUILD, c)[2] for c in range(6)}
    others_c = {c: case_load("a7c2_201", c)[2] for c in range(6)}
    assert all(base + others[c] - t == base_c + others_c[c] - t_c for c in range(6)), "the two switches pick different entries"
    cfg = P.Config(P.find_file(BUILD), BUILD)
    out_units = sorted(u["size"] for k in cfg.id_rows[0x2D9]["keys"] for u in cfg.units_by_key[k])
    assert out_units == [13271040] * 9 and 3840 * 2560 * 5 // 4 <= out_units[0]
    ref = json.loads((ROOT / "modding/designs/outsz2560_v1.json").read_text(encoding="utf8"))
    ref_c = json.loads((ROOT / "modding/designs/outsz2560_c2_v1.json").read_text(encoding="utf8"))
    sites = [{"ram_address": hex(site), "old": struct.pack("<HH", 3840, 2160).hex(), "new": struct.pack("<HH", 3840, 2560).hex(),
              "note": "the second 3840x2160 entry (output width and height; class 4 of the FX2's table as the emulator counts it, the A7 IV's "
                      "class 3) [A7 IV 0x143c7bc, A7C II 0x1a531c8]"}]
    guards = [{"ram_address": hex(site - 8), "bytes": struct.pack("<HHI", 3840, 2160, 0x43E).hex(),
               "note": "the entry before: 3840, 2160, memory id 0x43e [A7 IV 0x143c7b4, A7C II 0x1a531c0]"},
              {"ram_address": hex(site + 4), "bytes": struct.pack("<I", 0x2D9).hex(), "note": "this entry's memory id, 0x2d9 [A7 IV 0x143c7c0, A7C II 0x1a531cc]"}]
    for mine, theirs in ((sites, ref["sites"]), (guards, ref["guards"]), (sites, ref_c["sites"]), (guards, ref_c["guards"])):
        assert [(x.get("old"), x.get("new"), x.get("bytes")) for x in mine] == [(x.get("old"), x.get("new"), x.get("bytes")) for x in theirs]
    res = {"design": NAME, "build": BUILD, "camera": "ILME-FX2 (FX2), firmware 1.01",
           "title": "Output size of the stock 4K size class: 3840x2160 to 3840x2560, in the coprocessor's movie size table (RAM) (FX2 1.01 port)",
           "kind": "ram_words", "artifact": "cpapp-b.bin, RAM only: these bytes are not in the file",
           "emulated_image_sha256": SHA,
           "generated_by": "build/build_ram_words_fx2.py", "ported_from": {"design": "outsz2560_v1", "build": "a7iv_602", "also_as": "outsz2560_c2_v1 (a7c2_201)"},
           "status": "addresses from emulating and reading the FX2's own code; never read or written on an FX2. The same word change (outsz2560_v1) "
                     "works on the A7 IV (requests 26 to 29, F688, F698, F700)",
           "table": f"movie size table {t:#x} (base {base:#x} + 0x88; 0x4ff894 fills it; the reader 0x51fca6, case 3, loads base + {off:#x} = {site:#x})",
           "summary": dict(ref["summary"], goes_with=["dmmwb4688_fx2_v1", "the FX2 sensor-side design (A7 IV ogsq_v3)"]),
           "emulated": {"function": "0x4ff894", "bytes": 0x42A, "base": hex(base), "table": hex(t), "stores_into_block": len(writes),
                        "entries_equal_a7c2_201": True, "entries": [[w, h, hex(m)] for w, h, m in rows],
                        "reader": {"switch": hex(READERS[BUILD][0]), "case_3_code": hex(tgt), "case_3_loads": hex(base + off),
                                   "cases_0_to_5_entry_offsets": [hex(base + others[c] - t) for c in range(6)],
                                   "a7c2_201_switch": hex(READERS["a7c2_201"][0]), "a7c2_201_case_3_loads": hex(base_c + off_c)},
                        "output_buffer_id_0x2d9_units": out_units},
           "sites": sites, "guards": guards,
           "precondition": "none of its own: the table is read when a movie request is set up; write it with the camera in stills, as on the A7 IV",
           "restore": "write the old word back, or cold boot (the set-up fills the table again at start-up)",
           "checked_against": ["build/emu_size_table.py fx2_101 (the FX2's set-up run alone; entries equal the A7C II's)",
                               "the tbh switches of the FX2 (0x51fca6) and A7C II (0x4d436c) readers, decoded from the files: cases 0 to 5 pick the same entries",
                               "the FX2's DmmCfg.bin: id 0x2d9 = 9 x 13,271,040 bytes, as the A7 IV's"],
           "not_shown": ["anything on an FX2",
                         "the FX2's format code in 4K (2 on the A7 IV camera, request 25; at code 3 a 3840x2560 picture would need 14,745,600 bytes, "
                         "more than the 13,271,040-byte unit)",
                         "that the reader is the only one: the scan for MOVW/MOVT of the base found one load of base + 0xd0 (0x51fcf6)"]}
    dd = ROOT / "modding/designs"
    (dd / f"{NAME}.json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf8", newline="\n")
    (dd / f"{NAME}_pokes_ram.txt").write_text("".join(f"{x['ram_address']} {x['new']}\n" for x in sites), encoding="utf8", newline="\n")
    print(f"{NAME}: site {site:#x} {sites[0]['old']} -> {sites[0]['new']}; guards {[g['ram_address'] for g in guards]}; table {t:#x} = A7C II's; "
          f"reader case 3 at {tgt:#x} loads {base + off:#x} (A7C II {base_c + off_c:#x})")


def fehold():
    """fehold_fx2_v1 (fourth kit, 2026-11-26): one code word of the resize set-up 0x51fbc0 (SyncRCCalc), so that the first-scaler size it
    hands the second scaler stays the one the mode's records give.

    Why. After reading that size from the records (0x7ccd72 -> view +0x3c/+0x3e, 4336 x 2438 with ogsq_fx2_v1), the FX2 calls 0xbd3a32
    when view byte +5 is set, and stores max(record size, output size / (1 - margin)) back. With the output size 3840 x 2560 (L16) that is
    4336 x 2560, while the records make the first scaler give 2,438 rows: L13 + L5 + L16 ends in the forced 'S-Ele Refresh ng' exception
    on MOVIE (tester, 2026-11-26). The A7 IV has no such call (its 0x4455a4), and there the second scaler enlarges 2,438 rows to 2,560.
    The site: 0x51fefa `cbz r0, 0x51ff22` (taken when byte +5 is 0) becomes `b 0x51ff22`, so the call is always skipped.
    This is the FALLBACK. The main path is ogh2560_fx2_v1 (records that give 4336 x 2560), which needs no code word."""
    name = "fehold_fx2_v1"
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
    ins = list(md.disasm(IMG[0x51FEF8 - B:0x51FF24 - B], 0x51FEF8))
    text = [(i.address, i.mnemonic, i.op_str) for i in ins]
    assert text[0] == (0x51FEF8, "ldrb", "r0, [r4, #5]") and text[1] == (0x51FEFA, "cbz", "r0, #0x51ff22"), text[:2]
    call = next(i for i in ins if i.mnemonic == "bl")
    assert call.address == 0x51FF16 and call.op_str == "#0xbd3a32", (hex(call.address), call.op_str)
    # between the branch and its target: only the call's arguments, the call and the two stores of its result
    assert [(i.mnemonic, i.op_str) for i in ins if i.address in (0x51FF1C, 0x51FF20)] == [("strh", "r0, [r4, #0x3c]"), ("strh", "r0, [r4, #0x3e]")]
    assert ins[-1].address == 0x51FF22 and (ins[-1].mnemonic, ins[-1].op_str) == ("ldr", "r0, [r5, #0x20]")
    old = IMG[0x51FEF8 - B:0x51FEFC - B]
    new = old[:2] + struct.pack("<H", 0xE000 | ((0x51FF22 - (0x51FEFA + 4)) // 2))
    assert old.hex() == "607990b1" and new.hex() == "607912e0"
    chk = list(md.disasm(new, 0x51FEF8))
    assert [(i.mnemonic, i.op_str) for i in chk] == [("ldrb", "r0, [r4, #5]"), ("b", "#0x51ff22")], chk
    sites = [{"ram_address": hex(0x51FEF8), "old": old.hex(), "new": new.hex(),
              "note": "0x51fef8 ldrb r0, [r4, #5] (kept); 0x51fefa cbz r0, 0x51ff22 -> b 0x51ff22: the call of 0xbd3a32 and the two stores of "
                      "its result (view +0x3c, +0x3e) are skipped"}]
    guards = [{"ram_address": hex(0x51FEE8), "bytes": IMG[0x51FEE8 - B:0x51FEF8 - B].hex(), "note": "the 16 code bytes before the site (the call of 0x7ccd72)"},
              {"ram_address": hex(0x51FEFC), "bytes": IMG[0x51FEFC - B:0x51FF0C - B].hex(), "note": "the 16 code bytes after the site (the call's arguments)"}]
    res = {"design": name, "build": BUILD, "camera": "ILME-FX2 (FX2), firmware 1.01",
           "title": "Resize set-up 0x51fbc0: keep the first-scaler size the records give (skip the FX2's 0xbd3a32 override) (FX2 1.01)",
           "kind": "ram_words", "artifact": "cpapp-b.bin, the loaded image in coprocessor RAM: a CODE word", "emulated_image_sha256": SHA,
           "generated_by": "build/build_ram_words_fx2.py",
           "status": "read from the FX2's code and emulated (build/emu_rcinput_fx2.py); never written on an FX2. A fallback: the main path is ogh2560_fx2_v1",
           "summary": {"goes_with": ["dmmwb4688_fx2_v1", "ogsq_fx2_v1", "outsz2560_fx2_v1"], "not_with": ["ogh2560_fx2_v1 (not needed there)"]},
           "sites": sites, "guards": guards,
           "precondition": "write it with the switch on STILL, before the first MOVIE entry",
           "restore": "write the old word back, or cold boot",
           "not_shown": ["anything on an FX2", "that a code word written this way is taken up at once: 0x51fbc0 runs every frame (the screen step's "
                         "code words did take effect on the FX2)", "the margin words 0x190f46e.. (zero assumed: SteadyShot Off)"]}
    dd = ROOT / "modding/designs"
    (dd / f"{name}.json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf8", newline="\n")
    (dd / f"{name}_pokes_ram.txt").write_text("".join(f"{x['ram_address']} {x['new']}\n" for x in sites), encoding="utf8", newline="\n")
    print(f"{name}: site {sites[0]['ram_address']} {sites[0]['old']} -> {sites[0]['new']}; guards {[g['ram_address'] for g in guards]}")


# og57cp_fx2_v3 (2026-11-27, GitHub issue 7: 5.7K on the FX2). The A7 IV's og57cp_v3 (F906: the real 5760x3840 file), through the A7C II's
# og57cp_c2_v3; the FX2's addresses:
#   - unit-count setting: the FX2's split rule (0x509e5a: movw/movt 0x18f62d8, ldrb [r2, #0x10], the table {1, 2, 4} at 0x509ebc: the A7C II's
#     0x4c0e14.. instruction for instruction) reads byte 0x18f62e8. Every FX2 dump so far (three cameras, NTSC and PAL, stock and applied)
#     reads 0x18f62e0..0x18f62f0 as zero: the guards are read, not assumed as on the A7C II.
#   - the memory manager's id rows (0x24b94a0): the FX2 has the A7C II's rows; id 0x446 cannot be opened (key 0x587), id 0x498 (key 0x5f2) opens
#     30,824,400 bytes, there is no row of id 0x43f (build/emu_dmm_server.py --build fx2_101).
#   - movie size table: 0x18f60f8 (size) / 0x18f60fc (memory id), the words outsz2560_fx2_v1 changes / guards.
SETTING_FX2, SETTING_C2 = 0x18F62E8, 0x1A533B4
SIZE_C2_TO_FX2 = 0x18F60F8 - 0x1A531C8


def og57cp():
    import emu_dmm_server as E
    name, src = "og57cp_fx2_v3", "og57cp_c2_v3"
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
    # the split rule: the A7C II's instructions, loading the FX2's setting
    rule = [(i.address, i.mnemonic, i.op_str) for i in md.disasm(IMG[0x509E52 - B:0x509E6C - B], 0x509E52)]
    assert rule[:3] == [(0x509E52, "movw", "r2, #0x62d8"), (0x509E56, "movt", "r2, #0x18f"), (0x509E5A, "ldrb", "r2, [r2, #0x10]")], rule[:3]
    c2img = locate_file.locate("a7c2_201", "cpapp-b.bin").read_bytes()
    assert IMG[0x509E5A - B:0x509E6C - B] == c2img[0x4C0E1C - B:0x4C0E2E - B], "the setting's use is not the A7C II's"
    assert struct.unpack_from("<3I", IMG, 0x509EBC - B) == (1, 2, 4)
    # what the FX2 holds: the size table (emulated), the id rows and key lists (its own DMM set-up, emulated), the setting (camera dumps)
    t, rows, _ = emu_size_table.table(BUILD)
    known = {}
    for k, (w, h, mid) in enumerate(rows):
        for j, b in enumerate(struct.pack("<2HI", w, h, mid)):
            known[t + 8 * k + j] = b
    dumps = sorted((ROOT / "evidence/fx2").glob("**/cp_sizetable_018f6000.bin"))
    assert len(dumps) >= 20
    for dp in dumps:
        assert dp.read_bytes()[0x2E0:0x2F0] == bytes(16), dp
    for j in range(16):
        known[0x18F62E0 + j] = 0
    E.use_build(BUILD)
    cfg = P.Config(P.find_file(BUILD), BUILD)

    def server():
        s = E.Server(cfg.data, cfg)
        assert s.init() == 0 and not s.fatal
        return s
    s = server()
    rows_f, a = [], P.RAM[BUILD]["id_rows"]
    while True:
        i, ptr = struct.unpack("<II", s.uc.mem_read(a, 8))
        if i == 0xFFFFFFFF:
            break
        rows_f.append((a, i, ptr))
        a += 8
    by_id = {i: (ra, ptr) for ra, i, ptr in rows_f}
    for ra, i, ptr in rows_f:
        for j, b in enumerate(struct.pack("<II", i, ptr)):
            known[ra + j] = b
        q = ptr
        while True:
            k = struct.unpack("<I", s.uc.mem_read(q, 4))[0]
            for j, b in enumerate(struct.pack("<I", k)):
                known[q + j] = b
            q += 4
            if k == 0xFFFFFFFF:
                break
    assert 0x43F not in by_id and not s.open(0x446)["ok"] and s.open(0x498)["extents"][0]["size"] == 30824400
    c2 = json.loads((ROOT / "modding/designs" / f"{src}.json").read_text(encoding="utf8"))
    rows_c2 = {0x25B8670: 0x446, 0x25B8668: 0x445, 0x25B8748: 0x498}       # the A7C II rows its design names (build_ram_words_c2.py)
    keylists_c2 = {0x25BA748: 0x498}

    def addr(a, n):
        if SETTING_C2 - 8 <= a and a + n <= SETTING_C2 + 8:
            return a - SETTING_C2 + SETTING_FX2
        if 0x1A53180 <= a < 0x1A53200:
            return a + SIZE_C2_TO_FX2
        for r, i in rows_c2.items():
            if r <= a < r + 8:
                return by_id[i][0] + (a - r)
        for kl, i in keylists_c2.items():
            if a == kl:
                return by_id[i][1]
        raise SystemExit(f"no FX2 counterpart for {a:#x}")

    def value(a, b):
        """key-list pointers are addresses: the FX2's own"""
        if len(b) == 4 and a == 0x25B8674:                                 # the key-list pointer of the row: id 0x446's (old) / 0x498's (new)
            v = struct.unpack("<I", b)[0]
            return struct.pack("<I", by_id[0x446][1] if v == by_id_c2_ptr[0x446] else by_id[0x498][1])
        if len(b) == 8 and a in rows_c2:                                   # a guard row: id and its key-list pointer
            return struct.pack("<II", rows_c2[a], by_id[rows_c2[a]][1])
        return b
    by_id_c2_ptr = {0x446: 0x25BA670, 0x498: 0x25BA748}
    held = lambda a, b, what: [hex(a + j) for j, x in enumerate(b) if known.get(a + j) != x] == [] or (_ for _ in ()).throw(AssertionError(f"{what} {a:#x}"))
    sites, guards = [], []
    for x in c2["sites"]:
        a0, old, new = int(x["ram_address"], 16), bytes.fromhex(x["old"]), bytes.fromhex(x["new"])
        fa, o2, n2 = addr(a0, 4), value(a0, old), value(a0, new)
        held(fa, o2, "site")
        note = x["note"].split(" [A7 IV")[0]
        sites.append({"ram_address": hex(fa), "old": o2.hex(), "new": n2.hex(), "note": note + f" [A7C II {a0:#x}, A7 IV {x['note'].split('[A7 IV ')[-1].rstrip(']')}]"})
    for g in c2["guards"]:
        a0, b = int(g["ram_address"], 16), bytes.fromhex(g["bytes"])
        fa, b2 = addr(a0, len(b)), value(a0, b)
        held(fa, b2, "guard")
        note = g["note"].split(" [A7 IV")[0]
        guards.append({"ram_address": hex(fa), "bytes": b2.hex(), "note": note + f" [A7C II {a0:#x}]"})
    sa = [int(x["ram_address"], 16) for x in sites]
    assert len(set(sa)) == len(sa) == 5 and all(v % 4 == 0 for v in sa)
    assert sites[0]["ram_address"] == hex(SETTING_FX2) and sites[-1]["ram_address"] == "0x18f60f8" and sites[-1]["new"] == struct.pack("<HH", 5760, 3840).hex()
    for g in guards:
        ga, gn = int(g["ram_address"], 16), len(g["bytes"]) // 2
        assert not any(ga < v + 4 and v < ga + gn for v in sa), "a guard overlaps a site"
    # the new id in the FX2's own allocator, with the change in place: 0x43f opens one unit of 30,824,400 bytes (a 5760x3840 plane at format
    # code 2 is 27,648,000), and the other 4K movie ids still open beside it
    s2 = server()
    for x in sites:
        a = int(x["ram_address"], 16)
        if P.RAM[BUILD]["id_rows"] <= a < P.RAM[BUILD]["id_keys"]:
            assert bytes(s2.uc.mem_read(a, 4)) == bytes.fromhex(x["old"])
            s2.uc.mem_write(a, bytes.fromhex(x["new"]))
    o = s2.open(0x43F)
    assert o["ok"] and [e["size"] for e in o["extents"]] == [30824400], o
    beside = {}
    for other in (0x43E, 0x2D9, 0x4B8, 0x60C):
        r = s2.open(other)
        beside[hex(other)] = [e["size"] for e in r.get("extents", [])] if r.get("ok") else "refused"
    assert all(v != "refused" for v in beside.values()), beside
    res = {"design": name, "build": BUILD, "camera": "ILME-FX2 (FX2), firmware 1.01",
           "title": c2["title"].replace(" (A7C II 2.01 port)", "") + " (FX2 1.01 port)", "kind": "ram_words", "artifact": c2["artifact"],
           "emulated_image_sha256": SHA, "generated_by": "build/build_ram_words_fx2.py og57cp",
           "ported_from": {"design": src, "build": "a7c2_201", "a7iv": "og57cp_v3 (works on the A7 IV: F906, the real 5760x3840 file)"},
           "status": "addresses from the FX2's own code and its emulated tables; the setting's neighbours read on FX2 cameras; never written on an FX2",
           "table": "unit-count setting 0x18f62e8 (split rule 0x509e5a), the memory manager's id rows 0x24b94a0, the movie size table 0x18f60b0",
           "summary": dict(c2["summary"], goes_with=["dmmwb4688_fx2_v1", "og57n_fx2_v1 (PAL: og57n880_fx2_v1)", "ogfile57r300m1_fx2_v4"]),
           "sites": sites, "guards": guards,
           "checked_in_the_firmware_allocator": {"tool": "build/emu_dmm_server.py --build fx2_101", "open_0x43f": o["extents"], "then_open": beside},
           "checked_against": ["the FX2 split rule 0x509e5a: the A7C II's 0x4c0e1c.. bytes, table {1, 2, 4}",
                               f"{len(dumps)} FX2 dumps: 0x18f62e0..0x18f62f0 zero", "build/emu_size_table.py fx2_101", "build/emu_dmm_server.py --build fx2_101 (id rows, key lists)"],
           "precondition": "write it with the switch on STILL, before the first MOVIE entry; instead of outsz2560_fx2_v1 (the same size word)",
           "restore": "write the old words back (in the reverse order), or cold boot",
           "not_shown": ["anything on an FX2", "the FX2's output chooser 0x51cb38 for its other outputs at this size (they keep the stock sizes)"]}
    dd = ROOT / "modding/designs"
    (dd / f"{name}.json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf8", newline="\n")
    (dd / f"{name}_pokes_ram.txt").write_text("".join(f"{x['ram_address']} {x['new']}\n" for x in sites), encoding="utf8", newline="\n")
    print(f"{name}: sites {[(x['ram_address'], x['old'], x['new']) for x in sites]}; {len(guards)} guards; 0x43f opens {o['extents'][0]['size']}; beside {beside}")


if __name__ == "__main__":
    if sys.argv[1:] == ["og57cp"]:
        og57cp()
        raise SystemExit
    main()
    fehold()
    og57cp()
