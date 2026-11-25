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


if __name__ == "__main__":
    main()
