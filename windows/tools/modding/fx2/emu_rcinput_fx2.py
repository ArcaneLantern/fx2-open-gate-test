"""FX2 1.01: run the resize set-up 0x51fbc0 (SyncRCCalc) alone and show which first-scaler size it hands the second scaler (2026-11-26).

  C:\\Python313\\python.exe -B build\\emu_rcinput_fx2.py [--save]

Why. On the FX2, L13 + L5 runs (squeezed 3840x2160 clips) and adding L16 (the 4K output size 3840x2560) ends in the forced
'S-Ele Refresh ng' exception on MOVIE entry (tester, 2026-11-26; on the A7 IV the same step never did that, F688). Read from the code:
0x51fbc0 fills a 0x54-byte view (saved at 0x15cd520). It reads the first scaler's picture size from the mode's two records
(0x7ccd72 -> view +0x3c/+0x3e) and the output size from the movie size table (-> +0x40/+0x42). Then, when view byte +5 is set, the FX2
calls 0xbd3a32, which stores max(record size, output size / (1 - margin)) back to +0x3c/+0x3e, limited to the crop (+0x38/+0x3a).
The A7 IV's 0x4455a4 has no such call; of the extracted builds only the FX2 and the A1 II have the function.

What is run: the function itself on the FX2's image, with RAM zero but for the movie size table (build/emu_size_table.py) and a
request block that takes the path the tester's camera took (view byte +1 = 0, bytes +4/+5 = 1, mode 0x8c0, size class 3). The margin
words are zero (0xbd6f34 returns 0). Nothing here reaches hardware: it shows the SIZES, not what the scaler does with them.

Checks:
  stock, and ogsq_fx2_v1 with the stock size table: the emulated view equals the view the tester's camera saved (bytes 1..0x53), in the
      stock state (dump 045730, after a restart) and in the working L13 + L5 + S16 state (dump 051533)
  ogsq_fx2_v1 + outsz2560_fx2_v1: the view's first-scaler size becomes 4336x2560 while the records give 4336x2438 (the mismatch)
  ogh2560_fx2_v1 (+ outsz2560_fx2_v1): the records give 4336x2560 and the view agrees
  ogsq_fx2_v1 + outsz2560_fx2_v1 + fehold_fx2_v1: the view keeps the records' 4336x2438
"""
import json
import struct
import sys
from pathlib import Path

from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_HOOK_CODE
from unicorn import arm_const as A

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "build"))
import emu_size_table  # noqa: E402
import locate_file  # noqa: E402

BUILD, B = "fx2_101", 0x108000
IMG = locate_file.locate(BUILD, "cpapp-b.bin").read_bytes()
SETUP, RECORD_SIZE, OVERRIDE, PRINT = 0x51FBC0, 0x7CCD72, 0xBD3A32, 0xBDED5A
SAVED_VIEW = 0x15CD520
H = 0x30000000                                      # harness block, outside the firmware's RAM
OBJ, OBJ2, CTX, VIEW, OUT, STACK, RET = H, H + 0x1000, H + 0x10000, H + 0x20000, H + 0x21000, H + 0x80000, H + 0x90000
DUMPS = ROOT / "evidence/fx2/tester_2026-11-26b/zip"
DES = ROOT / "modding/designs"


def design_writes(name):
    d = json.loads((DES / f"{name}.json").read_text(encoding="utf8"))
    assert d["build"] == BUILD
    if d.get("kind") == "ram_words":
        # the memory manager's id rows of og57cp_fx2_v3 are not modelled here (build_ram_words_fx2.py og57cp opens them in the FX2's allocator):
        # the size table and the unit-count setting are
        return [(int(s["ram_address"], 16), bytes.fromhex(s["old"]), bytes.fromhex(s["new"])) for s in d["sites"]
                if 0x18F6000 <= int(s["ram_address"], 16) < 0x18F7000 or 0x500000 <= int(s["ram_address"], 16) < 0x530000]
    return [(int(p["addr"], 16), bytes.fromhex(p["old"]), bytes.fromhex(p["new"])) for p in d["patches"]]


def machine(designs):
    uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    uc.mem_map(0x100000, 0x2500000)
    uc.mem_map(H, 0x100000)
    uc.mem_write(B, IMG)
    t, rows, _ = emu_size_table.table(BUILD)
    assert t == 0x18F60B0 and rows[9] == (3840, 2160, 0x2D9)
    uc.mem_write(t, b"".join(struct.pack("<HHI", *r) for r in rows))
    for name in designs:
        for addr, old, new in design_writes(name):
            assert bytes(uc.mem_read(addr, len(old))) == old, (name, hex(addr))
            uc.mem_write(addr, new)
    calls = {"print": 0, "override": 0}

    def hook(uc_, address, size, _):
        if address == PRINT:                         # the firmware's log print: count it, return
            calls["print"] += 1
            uc_.reg_write(A.UC_ARM_REG_PC, uc_.reg_read(A.UC_ARM_REG_LR))
        elif address == OVERRIDE:
            calls["override"] += 1
    uc.hook_add(UC_HOOK_CODE, hook, begin=PRINT, end=PRINT)
    uc.hook_add(UC_HOOK_CODE, hook, begin=OVERRIDE, end=OVERRIDE)
    return uc, calls


def call(uc, addr, r0, r1=0, r2=0, r3=0, stack=()):
    sp = STACK - 0x100
    uc.mem_write(sp, b"".join(struct.pack("<I", x) for x in stack))
    for reg, v in ((A.UC_ARM_REG_R0, r0), (A.UC_ARM_REG_R1, r1), (A.UC_ARM_REG_R2, r2), (A.UC_ARM_REG_R3, r3),
                   (A.UC_ARM_REG_SP, sp), (A.UC_ARM_REG_LR, RET | 1)):
        uc.reg_write(reg, v)
    uc.emu_start(addr | 1, RET, count=400000)
    assert uc.reg_read(A.UC_ARM_REG_PC) == RET, hex(uc.reg_read(A.UC_ARM_REG_PC))


def run(designs, mode=0x8C0):
    uc, calls = machine(designs)
    # the request block the function reads, P = context + 0x20 (context +0xa68 set, byte +0x9ec clear: view byte +1 = 0, as on the camera)
    p = CTX + 0x20
    uc.mem_write(OBJ + 0xC, struct.pack("<I", CTX))
    uc.mem_write(OBJ + 0x38, struct.pack("<I", OBJ2))
    uc.mem_write(CTX + 0xA68, struct.pack("<I", 1))
    for off, v in ((0x00, mode),       # drive mode (view +0x44): 0x8c0 (NTSC 23.98p) or 0x880 (PAL 25p)
                   (0x18, 1),          # not zero: the request is live
                   (0x1C, 1),          # with +0x20 = 0, +0x88 != 1 and +0x6c = 0: view bytes +4, +5 = 1 (0x51ff52..0x51ff64)
                   (0x9C, 3),          # size class 3: the second 3840x2160 entry, 0x18f60f8
                   (0xEC, 1)):         # view +0x48 (1 on the camera)
        uc.mem_write(p + off, struct.pack("<I", v))
    call(uc, SETUP, OBJ, VIEW)
    view = bytes(uc.mem_read(VIEW, 0x54))
    # the records' own first-scaler size, by the firmware's reader (what view +0x3c/+0x3e held before the override)
    call(uc, RECORD_SIZE, mode, 0, 0, 0, stack=(OUT, 0, 0))
    rec = struct.unpack("<HH", uc.mem_read(OUT, 4))
    u = lambda o: struct.unpack_from("<HH", view, o)
    return {"designs": list(designs), "view": view.hex(), "flags_4_5": [view[4], view[5]], "first_stage": list(u(0x14)), "crop": list(u(0x38)),
            "first_scaler_in_view": list(u(0x3C)), "first_scaler_by_records": list(rec), "output": list(u(0x40)), "mode": hex(struct.unpack_from("<I", view, 0x44)[0]),
            "override_calls": calls["override"], "log_prints": calls["print"], "sizes_agree": list(u(0x3C)) == list(rec)}


def camera_view(folder):
    p = DUMPS / folder / "cp_outrecs_015cd000.bin"
    return p.read_bytes()[SAVED_VIEW - 0x15CD000:SAVED_VIEW - 0x15CD000 + 0x54] if p.is_file() else None


def main():
    cases = {"stock": (), "ogsq": ("ogsq_fx2_v1",), "ogsq+outsz (the crash state)": ("ogsq_fx2_v1", "outsz2560_fx2_v1"),
             "ogh2560": ("ogh2560_fx2_v1",), "ogh2560+outsz (the main path)": ("ogh2560_fx2_v1", "outsz2560_fx2_v1"),
             "ogsq+outsz+fehold (the fallback)": ("ogsq_fx2_v1", "outsz2560_fx2_v1", "fehold_fx2_v1"), "stock+fehold": ("fehold_fx2_v1",)}
    res = {k: run(v) for k, v in cases.items()}
    # 2026-11-27 (GitHub issue 7, 5.7K): the A7 IV's og57n_v1 / og57n880_v1 records (first scaler 5760x3840) and og57cp_v3's size word
    # (output 5760x3840), FX2 forms; PAL in mode 0x880
    res["og57n"] = run(("og57n_fx2_v1",))
    res["og57n+og57cp (the 5.7K path)"] = run(("og57n_fx2_v1", "og57cp_fx2_v3"))
    res["og57n880+og57cp (the 5.7K path, PAL, mode 0x880)"] = run(("og57n880_fx2_v1", "og57cp_fx2_v3"), 0x880)
    res["ogh2560880+outsz (the PAL 4K path, mode 0x880)"] = run(("ogh2560880_fx2_v1", "outsz2560_fx2_v1"), 0x880)
    for k, r in res.items():
        print("%-34s first scaler: view %dx%d, records %dx%d (%s); output %dx%d; stage %dx%d; override calls %d; prints %d"
              % (k, *r["first_scaler_in_view"], *r["first_scaler_by_records"], "agree" if r["sizes_agree"] else "DIFFER", *r["output"], *r["first_stage"],
                 r["override_calls"], r["log_prints"]))
    checks = []

    def check(name, ok):
        checks.append((name, bool(ok)))
        print("  %s  %s" % ("PASS" if ok else "FAIL", name))
    for case, folder, what in (("stock", "CT6_20261126T045730Z_fx2_dump", "after the restart (stock)"),
                               ("ogsq", "CT6_20261126T051533Z_fx2_dump", "working L13 + L5 + S16 state")):
        cam = camera_view(folder)
        if cam is None:
            print("  (no dump %s: the comparison with the camera's saved view is left out)" % folder)
            continue
        check("the emulated view of '%s' equals the camera's saved view, bytes 1..0x53 (%s, %s)" % (case, what, folder),
              bytes.fromhex(res[case]["view"])[1:] == cam[1:])
    check("stock and ogsq: first scaler 4336x2438 in the view and by the records", all(res[k]["first_scaler_in_view"] == [4336, 2438] and res[k]["sizes_agree"] for k in ("stock", "ogsq")))
    c = res["ogsq+outsz (the crash state)"]
    check("the crash state: output 3840x2560, the view says 4336x2560, the records give 4336x2438 (the sizes DIFFER)",
          c["output"] == [3840, 2560] and c["first_scaler_in_view"] == [4336, 2560] and c["first_scaler_by_records"] == [4336, 2438] and c["override_calls"] == 1)
    for k in ("ogh2560", "ogh2560+outsz (the main path)"):
        check("%s: the records give 4336x2560 and the view agrees" % k, res[k]["first_scaler_by_records"] == [4336, 2560] and res[k]["sizes_agree"])
    check("the main path: output 3840x2560", res["ogh2560+outsz (the main path)"]["output"] == [3840, 2560])
    f = res["ogsq+outsz+fehold (the fallback)"]
    check("the fallback: output 3840x2560, the view keeps the records' 4336x2438, 0xbd3a32 is not called",
          f["output"] == [3840, 2560] and f["first_scaler_in_view"] == [4336, 2438] and f["sizes_agree"] and f["override_calls"] == 0)
    check("fehold alone leaves the stock view unchanged", res["stock+fehold"]["view"] == res["stock"]["view"])
    for k in ("og57n+og57cp (the 5.7K path)", "og57n880+og57cp (the 5.7K path, PAL, mode 0x880)"):
        r = res[k]
        check("%s: output 5760x3840, the records give 5760x3840, the view agrees (the override asks for no more)" % k,
              r["output"] == [5760, 3840] and r["first_scaler_by_records"] == [5760, 3840] and r["sizes_agree"] and r["override_calls"] == 1)
    check("og57n alone (stock output size): the view takes the records' 5760x3840, output 3840x2160",
          res["og57n"]["first_scaler_in_view"] == [5760, 3840] and res["og57n"]["output"] == [3840, 2160])
    check("the PAL 4K path in mode 0x880 (P5 + L16, which records on an FX2): 4336x2560, agrees",
          res["ogh2560880+outsz (the PAL 4K path, mode 0x880)"]["first_scaler_in_view"] == [4336, 2560] and res["ogh2560880+outsz (the PAL 4K path, mode 0x880)"]["sizes_agree"])
    check("no case reaches a log print (FATAL lines)", all(r["log_prints"] == 0 for r in res.values()))
    ok = all(v for _, v in checks)
    print("%d of %d checks pass" % (sum(v for _, v in checks), len(checks)))
    if "--save" in sys.argv:
        out = {"about": "FX2 1.01, 0x51fbc0 (SyncRCCalc) run alone: the first-scaler size the view hands on, against the size the mode's records give "
                        "(build/emu_rcinput_fx2.py). Sizes only; nothing here reaches hardware.",
               "cases": res, "checks": [{"check": n, "pass": v} for n, v in checks]}
        (ROOT / "evidence/fx2/rcinput_emu_fx2.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf8", newline="\n")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
