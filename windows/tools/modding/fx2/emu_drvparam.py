"""Run a build's imager drive-parameter calculator alone and return the stored record of each drive mode.

  C:\\Python313\\python.exe -B build\\emu_drvparam.py <build> [--mode ID] [--json OUT] [VA=u16 ...]

A port of `A7iv Claude\\scripts\\emu_drvparam.py` (A7 IV 6.02) that takes the build's addresses from CONSTS,
so the same run works on the A7S III 5.01 image. It runs the control object's constructor block (which
fills the configuration at control +0x548), builds the parameter object from the table map, and calls the
calculator once per drive mode the way the control object does. `VA=u16` arguments change 16-bit cells of
the in-memory image first (a design's sensor cells). Nothing in any firmware file is changed.

Limits: the same as the original (finding F364 of the earlier work): the record depends only on the static
tables and the configuration block; fields the running camera fills later are not modelled.
"""
import json
import struct
import sys
from pathlib import Path

from unicorn import Uc, UcError, UC_ARCH_ARM, UC_MODE_THUMB, UC_HOOK_CODE, UC_HOOK_MEM_UNMAPPED
from unicorn import arm_const as A

ROOT = Path(__file__).resolve().parent.parent
BASE, REC = 0x108000, 0x15C
MAP_LO, MAP_HI = 0x100000, 0x2600000
CTRL, STACK_TOP, SCRATCH, RET = 0x2300000, 0x2200000, 0x2320000, 0x2400000
CONSTS = {
    "a7iv_602": {"init": (0x89A114, 0x89A254), "calc": 0x348EA4, "stubs": (0xA32386, 0xA310E0), "pobj_off": 0x4E8, "modes": 30,
                 "fields": {0x0: 0xC995A4, 0x8: 0xC98330, 0x10: 0x1FD1224, 0x14: 0xC983A8, 0x18: 0xD95AA8, 0x1C: 0xC99230, 0x20: 0xD96394,
                            0x24: 0xC98600, 0x28: 0xC98948, 0x2C: 0xC98AB0, 0x30: 0xC98D80, 0x34: 0xD95AAC, 0x38: 0xD95F20, 0x3C: 0xC99050,
                            0x40: 0xC99578, 0x44: 0xD96538}},
    # A7S III 5.01: table map read from the constructor caller 0x86d736 (same code as the A7 IV's 0x89a07e), vtable from 0x86eb40,
    # calculator and constructor block by function matching (modding/A7S3_PORT.md)
    "a7s3_501": {"init": (0x86D7CC, 0x86D918), "calc": 0x33625C, "stubs": (0x9FAA12,), "pobj_off": 0x4E8, "modes": 40,
                 "fields": {0x0: 0xC71EB0, 0x8: 0xC70624, 0x10: 0x1FE0504, 0x14: 0xC706C4, 0x18: 0xD67BFC, 0x1C: 0xC71A24, 0x20: 0xD687E0,
                            0x24: 0xC709E4, 0x28: 0xC70E44, 0x2C: 0xC71024, 0x30: 0xC71024 + 0x3C0, 0x34: 0xD67C00, 0x38: 0xD681F0, 0x3C: 0xC717A4,
                            0x40: 0xC71E84, 0x44: 0xD68A10}},
    # A7C II 2.01 (2026-11-24): table map from the constructor caller 0x98bcde (= A7 IV 0x89a07e, diff_consts.py), vtable 0xdeac40+8 from the
    # constructor 0x98ccf4, constructor block 0x98bd74-0x98beb8, calculator 0x39c468 (same arguments; its readout rows are 20 bytes), log print
    # 0xb4457a. The control object's configuration starts 4 bytes later (+0x54c) and the parameter object is at +0x4ec.
    "a7c2_201": {"init": (0x98BD74, 0x98BEB8), "calc": 0x39C468, "stubs": (0xB4457A,), "pobj_off": 0x4EC, "cfg_off": 0x54C, "rec": 0x170, "modes": 30,
                 "fields": {0x0: 0xDEAC48, 0x8: 0xDE99D4, 0x10: 0x25DC04C, 0x14: 0xDE9A4C, 0x18: 0xEE01D2, 0x1C: 0xDEA8D4, 0x20: 0xEE0ABE,
                            0x24: 0xDE9CA4, 0x28: 0xDE9FEC, 0x2C: 0xDEA154, 0x30: 0xDEA424, 0x34: 0xEE01D6, 0x38: 0xEE064A, 0x3C: 0xDEA6F4,
                            0x40: 0xDEAC1C, 0x44: 0xEE0C62}},
    # ZV-E1 2.02 (2026-11-24): table map from the constructor caller 0x96dd12 (= A7S III 0x86d736, diff_consts.py: every table, 39 modes,
    # records base 0x25d9fa4, timing B = A + 0x3a8), vtable 0xdcde44+8 (A7S III 0xc71ea8+8, in 0x96f224 = 0x86eb40), constructor block
    # 0x96dda8-0x96df00 (aligned with 0x86d7cc-0x86d918), calculator 0x390fa0 (= A7C II 0x39c468, match_thumb exact), log print 0xb268ac
    # (= A7C II 0xb4457a). Configuration at control +0x54c and parameter object at +0x4ec as the A7C II; record 0x170 bytes (0x96f2c4).
    # Its read-out rows are 16 bytes (no frame-length fields).
    # FX3 7.02 (2026-11-24): the A7S III 5.01 code relinked. Table map read from the constructor caller 0x857e5c (= A7S III 0x86d736: the same
    # stores, every table byte-identical to the A7S III's), vtable 0xc55014+8 from the constructor 0x859266 (= 0x86eb40), constructor block
    # 0x857ef2-0x85803e (= 0x86d7cc-0x86d918, same instructions), calculator 0x331538 (= 0x33625c), log print 0x9e6684 (= 0x9faa12, the
    # calculator's BL target). Configuration at control +0x548, parameter object at +0x4e8, record 0x15c bytes, 40 modes: as the A7S III.
    "fx3_702": {"init": (0x857EF2, 0x85803E), "calc": 0x331538, "stubs": (0x9E6684,), "pobj_off": 0x4E8, "modes": 40,
                "fields": {0x0: 0xC5501C, 0x8: 0xC53790, 0x10: 0x1FDD574, 0x14: 0xC53830, 0x18: 0xD46FA8, 0x1C: 0xC54B90, 0x20: 0xD47B8C,
                           0x24: 0xC53B50, 0x28: 0xC53FB0, 0x2C: 0xC54190, 0x30: 0xC54190 + 0x3C0, 0x34: 0xD46FAC, 0x38: 0xD4759C, 0x3C: 0xC54910,
                           0x40: 0xC54FF0, 0x44: 0xD47DBC}},
    # FX2 1.01 (2026-11-25, FX2 port): the A7C II's code with two more drive modes (32: 0x2821 and 0x28c1 after 0x8c1). Table map read from
    # the constructor caller 0xa0fa1c (= A7C II 0x98bcde, same stores in the same order: diff_consts.py), vtable 0xe95854+8 from the
    # constructor 0xa10a42 (= 0x98ccf4), constructor block 0xa0fab6-0xa0fbf8 (= 0x98bd74-0x98beb8, the same instructions with every
    # control-object offset 8 bytes on: configuration at +0x554, the parameter object pointer stored at +0x6ac where the A7C II has +0x684),
    # calculator 0x3d3024 (= 0x39c468, match_thumb exact), log print 0xcb73e8 (= 0xb4457a). Record 0x170 bytes (0xa10ae2 mov.w r2, #0x170).
    "fx2_101": {"init": (0xA0FAB6, 0xA0FBF8), "calc": 0x3D3024, "stubs": (0xCB73E8,), "pobj_off": 0x4F4, "cfg_off": 0x554, "rec": 0x170, "modes": 32,
                "fields": {0x0: 0xE9585C, 0x8: 0xE944B0, 0x10: 0x24DD92C, 0x14: 0xE94530, 0x18: 0xF98F20, 0x1C: 0xE954B0, 0x20: 0xF998A4,
                           0x24: 0xE947B0, 0x28: 0xE94B30, 0x2C: 0xE94CB0, 0x30: 0xE94CB0 + 0x300, 0x34: 0xF98F24, 0x38: 0xF993E4, 0x3C: 0xE952B0,
                           0x40: 0xE95830, 0x44: 0xF99A64}},
    "zve1_202": {"init": (0x96DDA8, 0x96DF00), "calc": 0x390FA0, "stubs": (0xB268AC,), "pobj_off": 0x4EC, "cfg_off": 0x54C, "rec": 0x170, "modes": 39,
                 "fields": {0x0: 0xDCDE4C, 0x8: 0xDCC524, 0x10: 0x25D9FA4, 0x14: 0xDCC5C0, 0x18: 0xEB628E, 0x1C: 0xDCD8A4, 0x20: 0xEB6E26,
                            0x24: 0xDCC8CC, 0x28: 0xDCCD10, 0x2C: 0xDCCEE4, 0x30: 0xDCCEE4 + 0x3A8, 0x34: 0xEB6292, 0x38: 0xEB685C, 0x3C: 0xDCD634,
                            0x40: 0xDCDCE8, 0x44: 0xEB7048}},
}


def image(build):
    return next(p for p in (ROOT / "work/extracted" / build).rglob("cpapp-b.bin") if "nflasha8" in p.as_posix()).read_bytes()


def records(build, patches=()):
    """{mode id: (index, record bytes, error or None)} for every drive mode of the build."""
    c = CONSTS[build]
    REC = c.get("rec", 0x15C)                        # stored record size: 0x15c on the A7 IV and A7S III, 0x170 on the A7C II (0x98cd94)
    data = bytearray(image(build))
    for va, val in patches:                          # a 16-bit value, or the bytes to put there
        if isinstance(val, (bytes, bytearray)):
            data[va - BASE:va - BASE + len(val)] = val
        else:
            struct.pack_into("<H", data, va - BASE, val)
    uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    try:
        uc.ctl_set_cpu_model(A.UC_CPU_ARM_CORTEX_A15)
    except Exception:
        pass
    uc.mem_map(MAP_LO, MAP_HI - MAP_LO)
    uc.mem_write(BASE, bytes(data))
    uc.reg_write(A.UC_ARM_REG_C1_C0_2, uc.reg_read(A.UC_ARM_REG_C1_C0_2) | (0xF << 20))
    uc.reg_write(A.UC_ARM_REG_FPEXC, 0x40000000)
    log = []

    def on_code(u, addr, size, _):
        if addr in c["stubs"]:
            u.reg_write(A.UC_ARM_REG_R0, 0)
            u.reg_write(A.UC_ARM_REG_PC, u.reg_read(A.UC_ARM_REG_LR))
        elif addr == RET:
            u.emu_stop()

    def on_unmapped(u, access, addr, size, value, _):
        log.append(f"unmapped access {access} at {addr:#x} pc={u.reg_read(A.UC_ARM_REG_PC):#x}")
        return False

    uc.hook_add(UC_HOOK_CODE, on_code)
    uc.hook_add(UC_HOOK_MEM_UNMAPPED, on_unmapped)

    def run(start, end, regs, stack_args=(), limit=2_000_000):
        sp = STACK_TOP - 0x400
        for i, v in enumerate(stack_args):
            uc.mem_write(sp + 4 * i, struct.pack("<I", v))
        uc.reg_write(A.UC_ARM_REG_SP, sp)
        uc.reg_write(A.UC_ARM_REG_LR, RET | 1)
        for r, v in regs.items():
            uc.reg_write(r, v)
        uc.emu_start(start | 1, end, count=limit)

    run(*c["init"], {A.UC_ARM_REG_R4: CTRL, A.UC_ARM_REG_R5: 1})
    cfg, pobj = CTRL + c.get("cfg_off", 0x548), CTRL + 0x10000
    for off, v in c["fields"].items():
        uc.mem_write(pobj + off, struct.pack("<I", v))
    uc.mem_write(pobj + 4, struct.pack("<I", c["modes"]))
    uc.mem_write(pobj + 0xC, b"\x00")
    f = c["fields"]
    ids = struct.unpack_from("<%dI" % c["modes"], data, f[0x8] - BASE)
    out = {}
    for idx, mid in enumerate(ids):
        rec = f[0x10] + idx * REC
        uc.mem_write(SCRATCH, bytes(uc.mem_read(f[0x2C] + idx * 24, 24)))
        uc.mem_write(rec, bytes(REC))
        err = None
        try:
            run(c["calc"], RET, {A.UC_ARM_REG_R0: pobj, A.UC_ARM_REG_R1: cfg, A.UC_ARM_REG_R2: SCRATCH, A.UC_ARM_REG_R3: idx},
                stack_args=(rec, SCRATCH + 0x100))
        except UcError as e:
            err = f"{e} pc={uc.reg_read(A.UC_ARM_REG_PC):#x}"
        out[mid] = (idx, bytes(uc.mem_read(rec, REC)), err)
    return out, log


def main():
    v = sys.argv[1:]
    build = v[0]
    only = int(v[v.index("--mode") + 1], 16) if "--mode" in v else None
    out_json = v[v.index("--json") + 1] if "--json" in v else None
    patches = [(int(a, 0), int(b, 0)) for a, b in (p.split("=") for p in v[1:] if "=" in p)]
    recs, log = records(build, patches)
    res = {"build": build, "image_patches": [[hex(a), b] for a, b in patches], "log": log, "modes": {}}
    for mid, (idx, r, err) in recs.items():
        if only is not None and mid != only:
            continue
        res["modes"][hex(mid)] = {"index": idx, "error": err, "record": r.hex()}
        print(f"{mid:#06x} idx {idx:2} {'ERR ' + err if err else 'ok'}  {r[:0x30].hex()}")
    for line in log[:5]:
        print("log:", line)
    if out_json:
        Path(out_json).write_text(json.dumps(res, indent=1) + "\n", encoding="utf8", newline="\n")


if __name__ == "__main__":
    main()
