"""Build a memory-only change of the coprocessor's DMM tables that makes the movie raw write buffer taller.

Background (findings F673 to F675): the camera core writes each raw movie frame into a unit of memory id 0x43e (DMM key
0x57f, 27,864,320 bytes = 7040 x 3958), and its port set-up 0x247898 refuses a frame larger than the unit. The unit's
size is read from the DMM server's RAM copy of the configuration each time the parent unit (key 0x6fa, 73,400,320
bytes) is divided. Key 0x57f is offered by two layouts of that parent: group 0x89 (two of them plus keys 0x634 and
0x635: no room to grow) and group 0x8a (two of them and 17.7 MB free). The server tries 0x89 first and does not go
on to 0x8a when 0x89 no longer fits, so the change has two parts, four 32-bit words in all:
  - the size of the two 0x57f records of group 0x8a becomes 7040 x ROWS
  - the key of the two 0x57f records of group 0x89 becomes 0x8fe, a key nothing asks for, so that group still serves
    keys 0x634 and 0x635 (memory ids 0x4b7, 0x4b8) but no longer offers 0x57f
Nothing here writes a firmware file; a cold boot reloads the tables from DmmCfg.bin.

The script checks the change in the firmware's own allocator code (build/emu_dmm_server.py): six opens of id 0x43e
return units of the new size inside their parents without overlap, ids 0x4b7 and 0x4b8 still open, and everything
frees. It also records what happens when the precondition is not met (a unit of the old division still in use).

  C:\\Python313\\python.exe build\\build_dmm_sites.py <name> <rows>
Writes modding/designs/<name>.json and <name>_pokes_ram.txt.
Add --build B for another build (2026-11-24: a7c2_201, where the two groups are 0x8c (steer) and 0x8d (grow)).
"""
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "build"))
import emu_dmm_server as E  # noqa: E402
import parse_dmmcfg as P  # noqa: E402

KEY, GROW, STEER, PARENT, SPARE_KEY, WIDTH = 0x57F, 0x8A, 0x89, 0x6FA, 0x8FE, 7040
BUILD = "a7iv_602"
GROUPS = {"a7iv_602": (0x8A, 0x89), "a7c2_201": (0x8D, 0x8C),      # (grow, steer): the same two layouts, renumbered
          "fx2_101": (0x8D, 0x8C)}                                 # FX2 1.01 (2026-11-25): as the A7C II


def main():
    global BUILD, GROW, STEER
    name, rows = sys.argv[1], int(sys.argv[2], 0)
    if "--build" in sys.argv:
        BUILD = sys.argv[sys.argv.index("--build") + 1]
        E.use_build(BUILD)
        GROW, STEER = GROUPS[BUILD]
    size = WIDTH * rows
    cfg = P.Config(P.find_file(BUILD), BUILD)
    assert SPARE_KEY not in cfg.units_by_key and SPARE_KEY not in cfg.region_by_key and all(SPARE_KEY not in r["keys"] for r in cfg.ids), "the spare key is in use"
    parent = min(cfg.parent_sizes(PARENT))
    grow = [u for u in cfg.units_by_key[KEY] if u["group"]["gid"] == GROW]
    steer = [u for u in cfg.units_by_key[KEY] if u["group"]["gid"] == STEER]
    assert len(grow) == 2 and len(steer) == 2 and all(u["size"] == 27864320 for u in grow + steer)
    assert [u["key"] for u in grow[0]["group"]["units"]] == [KEY, KEY], "group 0x8a holds something else too"
    assert size % 128 == 0 and 2 * size <= parent, f"two units of {size:,} do not fit the parent ({parent:,})"
    sites = []
    for u in grow:
        a = cfg.ram("unit_records", u["seq"] * 0x14) + 12
        sites.append({"ram_address": hex(a), "what": f"size of a key {KEY:#x} record of group {GROW:#x}", "file_offset_of_the_same_field": hex(u["at"] + 12),
                      "old": struct.pack("<I", u["size"]).hex(), "new": struct.pack("<I", size).hex(), "old_value": u["size"], "new_value": size})
    for u in steer:
        a = cfg.ram("unit_records", u["seq"] * 0x14) + 8
        sites.append({"ram_address": hex(a), "what": f"key of a key {KEY:#x} record of group {STEER:#x}", "file_offset_of_the_same_field": hex(u["at"] + 8),
                      "old": struct.pack("<I", KEY).hex(), "new": struct.pack("<I", SPARE_KEY).hex(), "old_value": hex(KEY), "new_value": hex(SPARE_KEY)})

    def run(plan, apply_first=True):
        s = E.Server(cfg.data, cfg)
        assert s.init() == 0 and s.cur == len(cfg.data) and not s.fatal
        if apply_first:
            s.set_size(KEY, GROW, size)
            s.drop(KEY, STEER, SPARE_KEY)
            for st in sites:                                     # the harness wrote exactly the design's words
                assert bytes(s.uc.mem_read(int(st["ram_address"], 16), 4)).hex() == st["new"], st
        out = []
        for step in plan:
            if step == "apply":
                s.set_size(KEY, GROW, size)
                s.drop(KEY, STEER, SPARE_KEY)
                out.append({"step": "apply"})
            elif step[0] == "open":
                out.append(s.open(step[1]))
            else:
                out.append(s.free(step[1]))
        return s, out

    # 1. the change in place before the first open
    plan = [("open", 0x43E)] * 6 + [("open", 0x4B7), ("open", 0x4B8), ("open", 0x43E)] + [("free", n) for n in range(8)]
    s, out = run(plan)
    opens = [o for o in out if o["step"] == "open"]
    wb = [o for o in opens[:6]]
    assert all(o["ok"] and [x["size"] for x in o["extents"]] == [size] for o in wb), "an open of 0x43e did not return the new size"
    assert opens[6]["ok"] and opens[6]["extents"][0]["size"] == 3317760 and opens[7]["ok"] and opens[7]["extents"][0]["size"] == 13271040, "ids 0x4b7 / 0x4b8 no longer open"
    assert not opens[8]["ok"], "a seventh write buffer was expected to be refused (group 0x8a's limit is 3)"
    spans = sorted((int(x["address"], 16), int(x["address"], 16) + x["size"]) for o in opens if o["ok"] for x in o["extents"])
    assert all(a[1] <= b[0] for a, b in zip(spans, spans[1:])), "opened units overlap"
    bases = sorted(cfg.bases(PARENT))
    assert all(any(b <= lo and hi <= b + parent for b in bases) for lo, hi in spans), "a unit lies outside its parent"
    assert all(o["ok"] for o in out if o["step"] == "free") and not s.fatal
    left = [o for o in s.objects() if o["in_use"]]
    assert not left, "something stayed in use after the frees"
    # 2. the precondition: a stock division with a sibling still in use keeps handing out the old units
    s2, out2 = run([("open", 0x43E), ("open", 0x43E), ("open", 0x4B8), ("free", 0), ("free", 1), "apply", ("open", 0x43E), ("open", 0x43E)], apply_first=False)
    late = [o for o in out2 if o.get("step") == "open"][-2:]
    stale = [x["size"] for o in late for x in o["extents"]]
    # 3. stock control
    s3, out3 = run([("open", 0x43E)] * 2, apply_first=False)
    stock = [x["size"] for o in out3 for x in o["extents"]]
    assert stock == [27864320, 27864320]
    design = {"design": name,
              "title": f"Memory-only DMM change: the movie raw write buffer (memory id 0x43e) grows from 7040 x 3958 to 7040 x {rows} bytes",
              "artifact": "coprocessor RAM (the DMM server's copy of /cp/DmmCfg.bin); no file is changed", "generated_by": f"build/build_dmm_sites.py {name} {rows}" + (f" --build {BUILD}" if BUILD != "a7iv_602" else ""),
              **({"build": BUILD, "groups": {"grow": hex(GROW), "steer": hex(STEER)}} if BUILD != "a7iv_602" else {}),
              "summary": {"sites": len(sites), "bytes": 4 * len(sites), "rows": rows, "unit_size": size, "stock_unit_size": 27864320, "parent_key": hex(PARENT), "parent_size": parent,
                          "left_free_in_the_parent": parent - 2 * size,
                          "cache_lines_64": sorted({hex(int(st["ram_address"], 16) & ~63) for st in sites}),
                          "largest_rows_that_fit": parent // 2 // WIDTH},
              "precondition": "no unit object of key 0x57f, 0x634 or 0x635 exists when the words are written (every 0x6fa parent undivided, or divided as another group): "
                              "an existing division keeps its old units and the server reuses them",
              "restore": "write the old words back while the same precondition holds, or cold boot (the tables are rebuilt from /cp/DmmCfg.bin)",
              "checked_in_the_firmware_allocator": {
                  "tool": "build/emu_dmm_server.py (the server's own code, alone; see its header for what is made up)",
                  "applied_before_any_open": {"six_opens_of_0x43e": [o["extents"] for o in wb], "open_0x4b7": opens[6]["extents"], "open_0x4b8": opens[7]["extents"],
                                              "seventh_open_of_0x43e": opens[8]["result"], "all_inside_a_parent_and_disjoint": True, "all_freed": True},
                  "applied_while_a_sibling_of_the_old_division_is_in_use": {"sizes_returned_afterwards": stale,
                                                                           "meaning": "the old division stays and its stock-size units are handed out again: the change has no effect, and no error is reported"},
                  "stock_control": stock},
              "not_shown": ["what the camera has open when the words would be written, and which scene it is in (a read on the camera)",
                            "that the image hardware accepts the taller first stage once the buffer is large enough (only the camera can show it)",
                            "the first stage's throughput at 18% more rows"],
              "sites": sites}
    d = ROOT / "modding/designs"
    (d / f"{name}.json").write_text(json.dumps(design, indent=1) + "\n", encoding="utf8", newline="\n")
    (d / f"{name}_pokes_ram.txt").write_text("".join(f"{st['ram_address']} {st['new']}\n" for st in sites), encoding="ascii", newline="\n")
    print(f"{name}: {len(sites)} sites, unit {size:,} bytes ({rows} rows), parent left {parent - 2 * size:,}; cache lines {design['summary']['cache_lines_64']}")
    for st in sites:
        print(f"  {st['ram_address']}  {st['old']} -> {st['new']}   {st['what']}")
    print("  write made while a sibling is in use returns", stale, "(no effect)")


if __name__ == "__main__":
    main()
