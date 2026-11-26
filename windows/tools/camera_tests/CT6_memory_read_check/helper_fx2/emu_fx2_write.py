"""Run the built FX2 1.01 write libraries (build_fx2_write.sh) in Unicorn against a model camera. Offline; no camera. (FX2 port, 2026-11-25)

  C:\\Python313\\python.exe -B emu_fx2_write.py

helper_c2/emu_c2_write.py (the A7C II kit: the same kind of designs on the same platform) with this camera's models and steps:
  - coprocessor transfers must be whole 64-byte lines to or from the allocated buffer; a transfer TOWARDS the coprocessor may change only
    bytes of a listed site, and only to that site's stock or new bytes;
  - L5/L6: the sensor object 0x1750860 -> control -> +0x6ac -> parameter object {vtable, 32, ids, 0, records} -> the 0x170-byte stored
    records, the one of mode 0x8c0 holding the FX2's emulated stock record (build/emu_drvparam.py fx2_101);
  - L13/L14: the memory manager's pages as the FX2's OWN DMM code leaves them after parsing its DmmCfg.bin (build/emu_dmm_server.py
    --build fx2_101); after L13 the same code must hand out units of the new size;
  - L16/L17, S16/S17: the movie size table as the FX2's set-up fills it (build/emu_size_table.py fx2_101), and the loaded image for the
    screen words;
  - L19/L20, N19: av-cam.bin at its physical address and libmpr.so in the process's own mapping; N19 (the encoder side without the MP4
    header heights) is put back by L20, and L19 on a camera holding N19's state writes only the two heights.
Cases per library: apply on stock, apply again (nothing to do), put back (byte for byte), a site holding foreign bytes, a lost write
(undo), a guard wrong. Safety: the A7C II kit's and the FX3 kit's libraries of the same steps write nothing on an FX2.
"""
import json
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent / "helper"))
sys.path.insert(0, str(ROOT / "build"))
import emu_built as E  # noqa: E402
from unicorn import arm64_const as R  # noqa: E402
import emu_dmm_server  # noqa: E402
import emu_size_table  # noqa: E402
import parse_dmmcfg  # noqa: E402

BASE, CP_HI = 0x108000, 0x10000000
DES = ROOT / "modding/designs"
IMAGER, CTRL, OBJ, CTRL_DRVPARAM = 0x1750860, 0x1500000, 0x1500800, 0x6AC
IDS, RECS, REC, COUNT, VTABLE = 0xE944B0, 0x24DD92C, 0x170, 32, 0xE9585C
LM_AT = 0x7F82D15000
RESULT = E.RESULT
DEFAULT_DESIGN = E.DESIGN


def ex(rel, build="fx2_101"):
    return (ROOT / f"work/extracted/{build}/0700_part_image/dev" / rel).read_bytes()


def design(name):
    return json.loads((DES / f"{name}.json").read_text(encoding="utf8"))


def lib(name, folder="helper_fx2", prefix="fx2"):
    return (HERE.parent / folder / f"libJit_{prefix}_{name}.so").read_bytes()


class Mem:
    """Coprocessor memory: the image at 0x108000, zeros elsewhere, with what the model camera adds."""

    def __init__(self, image):
        self.pages, self.image = {}, image

    def page(self, a):
        a &= ~0xFFF
        if a not in self.pages:
            p = bytearray(4096)
            if BASE <= a < BASE + len(self.image):
                chunk = self.image[a - BASE:a - BASE + 4096]
                p[:len(chunk)] = chunk
            self.pages[a] = p
        return self.pages[a]

    def read(self, a, n):
        return bytes(self.page(a + k)[(a + k) & 0xFFF] for k in range(n))

    def write(self, a, data):
        for k, v in enumerate(data):
            self.page(a + k)[(a + k) & 0xFFF] = v

    def snapshot(self):
        return {a: bytes(p) for a, p in self.pages.items()}


class Run(E.Run):
    """emu_c2_write.py's run: every import is modelled here, against Mem."""

    def __init__(self, libbytes, files, dirs, mem, allowed, lose=None):
        saved, E.DESIGN = E.DESIGN, DEFAULT_DESIGN
        super().__init__(libbytes, 5, files, dirs, cp=b"")
        E.DESIGN = saved
        self.mem, self.allowed, self.lose, self.n_writes = mem, allowed, lose, 0

    def go(self):
        self.uc.reg_write(R.UC_ARM64_REG_SP, E.STACK - 0x1000)
        self.uc.reg_write(R.UC_ARM64_REG_X30, E.RET)
        self.uc.emu_start(self.ctor, E.RET, count=2_000_000_000)
        if not self.bad and self.uc.reg_read(R.UC_ARM64_REG_PC) != E.RET:
            self.bad = "the constructor did not return"
        return self

    def on_import(self, uc, address, size, _):
        x = lambda n: uc.reg_read(getattr(R, "UC_ARM64_REG_X%d" % n))
        name, ret = self.imports.get(address), 0
        if name == "_Z9dmm_allocjPj":
            uc.mem_write(x(1), struct.pack("<I", E.BUF_HANDLE))
            ret = self.buf
        elif name == "_Z8dmm_freej":
            pass
        elif name == "sen_dma_transfer":
            d, src, dst, n = x(0) & 0xFFFFFFFF, x(1), x(2), x(3) & 0xFFFFFFFF
            cp = src if d == 0 else dst
            if d not in (0, 1) or (dst if d == 0 else src) != self.buf or cp & 63 or n & 63 or not 0 < n <= 4096 or cp < BASE or cp + n > CP_HI:
                self.bad = "a transfer that is not whole lines to or from the buffer: dir %d src %#x dst %#x size %d" % (d, src, dst, n)
                uc.emu_stop()
                return
            va = next(v for v, off in self.map_phys.items() if v in self.maps and off <= self.buf < off + self.maps[v]) + self.buf % 4096
            if d == 0:
                uc.mem_write(va, self.mem.read(cp, n))
            else:
                data, now = bytes(uc.mem_read(va, n)), self.mem.read(cp, n)
                for k in range(n):
                    if data[k] != now[k] and data[k] not in self.allowed.get(cp + k, ()):
                        self.bad = "a write that changes %#x to %#x, which is not a listed site's stock or new byte" % (cp + k, data[k])
                        uc.emu_stop()
                        return
                self.n_writes += 1
                if self.lose != self.n_writes:
                    self.mem.write(cp, data)
        else:
            self.bad = "call of an unexpected import %r" % name
            uc.emu_stop()
            return
        uc.reg_write(R.UC_ARM64_REG_X0, ret)
        uc.reg_write(R.UC_ARM64_REG_PC, uc.reg_read(R.UC_ARM64_REG_X30))


def dmm_server(opens=(), frees=()):
    emu_dmm_server.use_build("fx2_101")
    cfg = parse_dmmcfg.Config(parse_dmmcfg.find_file("fx2_101"), "fx2_101")
    srv = emu_dmm_server.Server(cfg.data, cfg)
    assert srv.init() == 0
    for i in opens:
        assert srv.open(i)["ok"]
    for n in frees:
        assert srv.free(n)["ok"]
    return srv


def main():
    fail = []
    ok = lambda cond, text: (print(("PASS  " if cond else "FAIL  ") + text), fail.append(text) if not cond else None)
    image = ex("nflasha8/cpapp-b.bin")
    files = E.tree()
    files["/dev/mem"] = b""
    dirs = {"/tmp_wbshd", "/sys/module/liro/parameters", "/proc/driver/pcie"}

    def go(libbytes, mem, allowed, **kw):
        r = Run(libbytes, files, dirs, mem, allowed, **kw).go()
        return r, r.writes.get(RESULT, b"").decode("utf8", "replace")

    def changed_only(mem, before, allowed):
        for a, p in mem.pages.items():
            b = before.get(a)
            if b is None:
                b = image[a - BASE:a - BASE + 4096].ljust(4096, b"\0") if BASE <= a < BASE + len(image) else bytes(4096)
            if any(p[k] != b[k] and (a + k) not in allowed for k in range(4096)):
                return False
        return True

    # ---- L5 / L6: sensor sites and the stored record
    d = design("ogsq_fx2_v1")
    index = d["mode_index"]
    st, nw = bytes.fromhex(d["stored_record"]["stock"]), bytes.fromhex(d["stored_record"]["design"])
    allowed = {}
    for p in d["patches"]:
        a = int(p["addr"], 16)
        for k, (o, n) in enumerate(zip(bytes.fromhex(p["old"]), bytes.fromhex(p["new"]))):
            allowed[a + k] = (o, n)
    for k in range(REC):
        if st[k] != nw[k]:
            allowed[RECS + index * REC + k] = (st[k], nw[k])

    def camera(img=image, imager=IMAGER):
        m = Mem(img)
        m.write(imager, struct.pack("<I", CTRL))
        m.write(CTRL + CTRL_DRVPARAM, struct.pack("<I", OBJ))
        m.write(OBJ, struct.pack("<6I", VTABLE, COUNT, IDS, 0, RECS, 0xE94530))
        for i in range(COUNT):
            m.write(RECS + i * REC, bytes([i]) * REC)
        m.write(RECS + index * REC, st)
        return m

    def state(mem):
        vals = [(mem.read(a, 1)[0], pr) for a, pr in allowed.items()]
        return "stock" if all(v == pr[0] for v, pr in vals) else "new" if all(v == pr[1] for v, pr in vals) else "mixed"
    L5, L6 = lib("L5"), lib("L6")
    mem = camera()
    before = mem.snapshot()
    r, t = go(L5, mem, allowed)
    ok(not r.bad and "DONE: all 14 sites hold the target bytes (apply)" in t and state(mem) == "new" and changed_only(mem, before, allowed),
       f"L5 on a stock FX2: 13 sites and the stored record of mode {d['mode_id']} new, nothing else changed ({r.n_writes} line writes)")
    r, t = go(L5, mem, allowed)
    ok(not r.bad and "NOTHING TO DO" in t and r.n_writes == 0, "L5 again: nothing to do, no write")
    r, t = go(L6, mem, allowed)
    ok(not r.bad and "(put back)" in t and "DONE" in t and state(mem) == "stock" and changed_only(mem, before, {}), "L6: everything stock again, byte for byte")
    r, t = go(L6, mem, allowed)
    ok(not r.bad and "NOTHING TO DO" in t and r.n_writes == 0, "L6 on a stock camera: nothing to do, no write")
    mem = camera()
    mem.write(int(d["patches"][0]["addr"], 16), b"\x55")
    r, t = go(L5, mem, allowed)
    ok(not r.bad and r.n_writes == 0 and "holds neither the stock nor the new bytes; nothing is written" in t, "L5 with a site holding other bytes: nothing is written")
    for lose in (1, 7, 14):
        mem = camera()
        before = mem.snapshot()
        r, t = go(L5, mem, allowed, lose=lose)
        ok(not r.bad and "NOT DONE: a step failed; every site this run touched was put back" in t and state(mem) == "stock" and changed_only(mem, before, {}),
           f"L5 with line write {lose} lost: reported, every site put back")
    mem = camera()
    mem.write(OBJ + 0x10, bytes(4))
    r, t = go(L5, mem, allowed)
    ok(not r.bad and r.n_writes == 0 and "the stored record was not found" in t, "L5 with a null records pointer: nothing is written")
    mem = camera()
    mem.write(IDS + 4 * index, struct.pack("<I", 0x1234))
    r, t = go(L5, mem, allowed)
    ok(not r.bad and r.n_writes == 0, "L5 when mode 0x8c0 is not in the id table: nothing is written")
    mem = camera(imager=0x18AEB8C)                         # the pointer where the A7C II has it, not where the FX2 has it
    mem.write(IMAGER, bytes(4))
    r, t = go(L5, mem, allowed)
    ok(not r.bad and r.n_writes == 0 and "the stored record was not found" in t, "L5 with the FX2's sensor object empty (the chain at the A7C II's address): nothing is written")
    # the other kits' sensor steps on an FX2: they must write nothing (an FX2 owner might run another kit)
    foreign = [("A7C II kit level 5 (ogsq_c2_v1)", HERE.parent / "helper_c2/libJit_c2_level5_ogsq_c2_v1.so", 0x18AEB8C),
               ("FX3 kit L5 (ogsq_fx3_v1)", HERE.parent / "helper_fx3/libJit_fx3_L5.so", 0x127AB68),
               ("ZV-E1 kit L5 (ogsq_zv_v2)", HERE.parent / "helper_zv/libJit_zv_L5.so", 0x17F1F64)]
    for label, path, their_imager in foreign:
        if not path.is_file():
            print("NOTE  %s not built: skipped" % label)
            continue
        mem = camera(imager=their_imager)                  # even with its pointer chain made to reach the FX2's real parameter object
        for off in (0x684, 0x698):
            mem.write(CTRL + off, struct.pack("<I", OBJ))
        before = mem.snapshot()
        r, t = go(path.read_bytes(), mem, {})
        ok(not r.bad and r.n_writes == 0 and changed_only(mem, before, {}), f"{label} on an FX2, its chain led to the FX2's records: nothing is written")

    # ---- B5 / B6 (second kit, test 1): fhband_fx2_v1, the A7 IV's fhband_v1, at the same sites as L5 with other new bytes
    db = design("fhband_fx2_v1")
    assert db["mode_index"] == index and db["stored_record"]["stock"] == d["stored_record"]["stock"]
    bst, bnw = bytes.fromhex(db["stored_record"]["stock"]), bytes.fromhex(db["stored_record"]["design"])
    b_allowed = {}
    for p in db["patches"]:
        a = int(p["addr"], 16)
        for k, (o, n) in enumerate(zip(bytes.fromhex(p["old"]), bytes.fromhex(p["new"]))):
            if o != n:
                b_allowed[a + k] = (o, n)
    for k in range(REC):
        if bst[k] != bnw[k]:
            b_allowed[RECS + index * REC + k] = (bst[k], bnw[k])

    def bstate(mem):
        vals = [(mem.read(a, 1)[0], pr) for a, pr in b_allowed.items()]
        return "stock" if all(v == pr[0] for v, pr in vals) else "new" if all(v == pr[1] for v, pr in vals) else "mixed"
    B5, B6 = lib("B5"), lib("B6")
    mem = camera()
    before = mem.snapshot()
    r, t = go(B5, mem, b_allowed)
    ok(not r.bad and "DONE: all 14 sites hold the target bytes (apply)" in t and bstate(mem) == "new" and changed_only(mem, before, b_allowed),
       f"B5 (fhband_fx2_v1) on a stock FX2: 13 sites and the stored record new, nothing else changed ({r.n_writes} line writes)")
    r, t = go(B5, mem, b_allowed)
    ok(not r.bad and "NOTHING TO DO" in t and r.n_writes == 0, "B5 again: nothing to do, no write")
    r, t = go(L5, mem, allowed)
    ok(not r.bad and r.n_writes == 0 and "nothing is written" in t, "L5 on a camera holding B5's state: refused, nothing written")
    r, t = go(B6, mem, b_allowed)
    ok(not r.bad and "(put back)" in t and "DONE" in t and bstate(mem) == "stock" and changed_only(mem, before, {}), "B6: everything stock again, byte for byte")
    mem = camera()
    r, t = go(L5, mem, allowed)
    r, t = go(B5, mem, b_allowed)
    ok(not r.bad and r.n_writes == 0 and "nothing is written" in t, "B5 on a camera holding L5's state: refused, nothing written")
    for lose in (1, 14):
        mem = camera()
        before = mem.snapshot()
        r, t = go(B5, mem, b_allowed, lose=lose)
        ok(not r.bad and "NOT DONE" in t and bstate(mem) == "stock" and changed_only(mem, before, {}), f"B5 with line write {lose} lost: every site put back")

    # ---- L13 / L14: the memory manager
    dd = design("dmmwb4688_fx2_v1")
    E.DESIGN = "dmmwb4688_fx2_v1"
    sites = [(int(s["ram_address"], 16), bytes.fromhex(s["old"]), bytes.fromhex(s["new"])) for s in dd["sites"]]
    d_allowed = {a + k: (o[k], n[k]) for a, o, n in sites for k in range(4)}

    def dmm_mem(srv):
        m = Mem(image)
        for a, b in srv.snapshot().values():
            m.write(a, b)
        return m

    srv = dmm_server()
    mem = dmm_mem(srv)
    before = mem.snapshot()
    L13, L14 = lib("L13"), lib("L14")
    r, t = go(L13, mem, d_allowed)
    ok(not r.bad and "DONE" in t and all(mem.read(a, 4) == n for a, _, n in sites) and changed_only(mem, before, d_allowed),
       f"L13 on the FX2's own DMM state (nothing open): the four words new, nothing else changed ({r.n_writes} line writes)")
    srv2 = dmm_server()
    for a, _, n in sites:
        srv2.uc.mem_write(a, n)
    o = srv2.open(0x43E)
    ok(o["ok"] and [e["size"] for e in o["extents"]] == [dd["summary"]["unit_size"]], "after L13 the FX2's allocator code hands out a write buffer of %s bytes" % format(dd["summary"]["unit_size"], ","))
    r, t = go(L13, mem, d_allowed)
    ok(not r.bad and r.n_writes == 0 and ("NOTHING TO DO" in t or "already" in t), "L13 again: no write")
    r, t = go(L14, mem, d_allowed)
    ok(not r.bad and "DONE" in t and all(mem.read(a, 4) == o_ for a, o_, _ in sites) and changed_only(mem, before, {}), "L14: the four words stock again, byte for byte")
    busy = dmm_server(opens=(0x43E, 0x43E, 0x4B8), frees=(0, 1))
    mem = dmm_mem(busy)
    r, t = go(L13, mem, d_allowed)
    ok(not r.bad and r.n_writes == 0 and "nothing is written" in t, "L13 while a block is still divided as the old layout (one unit in use): refused, nothing written")
    mem = dmm_mem(dmm_server())
    a0 = sites[0][0]
    mem.write(a0 - 12 + 4, b"\x99")                          # a byte of the record that is not the site: not as in the file
    r, t = go(L13, mem, d_allowed)
    ok(not r.bad and r.n_writes == 0 and "nothing is written" in t, "L13 with a unit record not as in the file: nothing is written")
    for lose in (1, 3):
        mem = dmm_mem(dmm_server())
        r, t = go(L13, mem, d_allowed, lose=lose)
        ok(not r.bad and "NOT DONE" in t and all(mem.read(a, 4) == o_ for a, o_, _ in sites), f"L13 with line write {lose} lost: everything put back")
    c2_l13 = HERE.parent / "helper_c2/libJit_c2_level13_dmmwb4688_c2_v1.so"
    if c2_l13.is_file():
        mem = dmm_mem(dmm_server())
        before = mem.snapshot()
        r, t = go(c2_l13.read_bytes(), mem, {})
        ok(not r.bad and r.n_writes == 0 and changed_only(mem, before, {}), "the A7C II kit's level 13 on an FX2's DMM state: nothing is written")

    # ---- L16 / L17 (output size) and S16 / S17 (screen words)
    t_, srows, _ = emu_size_table.table("fx2_101")

    def words_mem():
        m = Mem(image)
        for k, (w, h, mid) in enumerate(srows):
            m.write(t_ + 8 * k, struct.pack("<2HI", w, h, mid))
        return m
    steps = [("outsz2560_fx2_v1", "L16", "L17")]
    if (HERE / "libJit_fx2_S16.so").is_file():
        steps.append(("lcd32dsq_fx2_v1", "S16", "S17"))
    for name, s_apply, s_back in steps:
        dw = design(name)
        w_allowed = {}
        for s in dw["sites"]:
            a = int(s["ram_address"], 16)
            for k, (o, n) in enumerate(zip(bytes.fromhex(s["old"]), bytes.fromhex(s["new"]))):
                w_allowed[a + k] = (o, n)
        La, Lb = lib(s_apply), lib(s_back)

        def wstate(mem):
            vals = [(mem.read(a, 1)[0], pr) for a, pr in w_allowed.items()]
            return "stock" if all(v == pr[0] for v, pr in vals) else "new" if all(v == pr[1] for v, pr in vals) else "mixed"
        mem = words_mem()
        before = mem.snapshot()
        r, t = go(La, mem, w_allowed)
        ok(not r.bad and "DONE" in t and wstate(mem) == "new" and changed_only(mem, before, w_allowed),
           f"{s_apply} ({name}) on the model: {len(dw['sites'])} word(s) new, nothing else changed ({r.n_writes} line writes)")
        r, t = go(La, mem, w_allowed)
        ok(not r.bad and "NOTHING TO DO" in t and r.n_writes == 0, f"{s_apply} again: nothing to do")
        r, t = go(Lb, mem, w_allowed)
        ok(not r.bad and "DONE" in t and wstate(mem) == "stock" and changed_only(mem, before, {}), f"{s_back}: stock again, byte for byte")
        bad_guard = None
        for g in dw["guards"]:
            mem = words_mem()
            ga = int(g["ram_address"], 16)
            mem.write(ga, bytes([mem.read(ga, 1)[0] ^ 1]))
            r, t = go(La, mem, w_allowed)
            if r.bad or r.n_writes:
                bad_guard = ga
                break
        ok(bad_guard is None, f"{s_apply} with any one of its {len(dw['guards'])} guards wrong: nothing is written")
        mem = words_mem()
        a0 = int(dw["sites"][0]["ram_address"], 16)
        mem.write(a0, b"\x5a\x5a\x5a\x5a")
        r, t = go(La, mem, w_allowed)
        ok(not r.bad and r.n_writes == 0, f"{s_apply} with its first word holding other bytes: nothing is written")
        mem = words_mem()
        r, t = go(La, mem, w_allowed, lose=1)
        ok(not r.bad and "NOT DONE" in t and wstate(mem) == "stock", f"{s_apply} with the first line write lost: everything put back")
    for label, path in (("FX3 kit S16 (lcd32dsq_fx3_v1)", HERE.parent / "helper_fx3/libJit_fx3_S16.so"),
                        ("A7C II kit level 16 (lcdfill_c2_v2)", HERE.parent / "helper_c2/libJit_c2_level16_lcdfill_c2_v2.so"),
                        ("A7C II kit level 16 (outsz2560_c2_v1)", HERE.parent / "helper_c2/libJit_c2_level16_outsz2560_c2_v1.so")):
        if path.is_file():
            mem = words_mem()
            before = mem.snapshot()
            r, t = go(path.read_bytes(), mem, {})
            ok(not r.bad and r.n_writes == 0 and changed_only(mem, before, {}), f"{label} on an FX2: nothing is written")

    # ---- L19 / L20 / N19: encoder side
    av, lm = ex("nflasha3/av-cam.bin"), ex("nflasha15/lib/libmpr.so")
    av = bytes([0x5A]) * 0x1000 + av[0x1000:]
    phoff, phentsize, phnum = struct.unpack_from("<Q", lm, 0x20)[0], *struct.unpack_from("<HH", lm, 0x36)
    span = next(struct.unpack_from("<IIQQQQQQ", lm, phoff + k * phentsize) for k in range(phnum) if struct.unpack_from("<I", lm, phoff + k * phentsize)[0] == 1)[5]
    lspan = (span + 0xFFF) & ~0xFFF
    lm0 = lm[:span].ljust(lspan, b"\0")
    mfiles = dict(files)
    mfiles["/proc/self/mem"] = b""
    mfiles["/proc/self/maps"] = (b"00400000-00409000 r-xp 00000000 fc:8f 81970                              /usr/bin/im.elf\n"
                                 + b"%x-%x r-xp 00000000 fc:8f 55354                          /usr/lib/libmpr.so\n" % (LM_AT, LM_AT + lspan)
                                 + b"%x-%x ---p %08x fc:8f 55354                          /usr/lib/libmpr.so\n" % (LM_AT + lspan, LM_AT + lspan + 0x10000, lspan)
                                 + b"7f8b936000-7f8b991000 r-xp 00000000 fc:8f 55344                          /usr/lib/libsencore.so\n")
    sts = {}
    for dn in ("ogfile2560_hs_s_fx2_v2", "ogfile2560_hs_s_fx2_v1"):
        fl = design(dn)
        sts[dn] = {"av-cam.bin": [], "libmpr.so": []}
        for p in fl["patches"]:
            sts[dn][p["binary"]].append((int(p["file_off"], 16), bytes.fromhex(p["old"]), bytes.fromhex(p["new"])))

    def applied(blob, dn, which):
        b = bytearray(blob)
        for o, old, new in sts[dn][which]:
            b[o:o + len(new)] = new
        return bytes(b)

    def mp(step, av_mem, lm_mem, libpath=None, **wrong):
        r = E.Run(libpath.read_bytes() if libpath else lib(step), int(step[1:]), mfiles, dirs, {E.AVCAM_PHYS: av_mem}, own={LM_AT: lm_mem})
        r.kview_fail = False
        r.stale = {E.AVCAM_PHYS + o for o in wrong.get("stale", ())}
        r.pwrite_lost = {LM_AT + o for o in wrong.get("pwrite_lost", ())}
        r.go()
        return r, r.writes.get(RESULT, b"").decode("utf8", "replace"), bytes(r.phys[E.AVCAM_PHYS]), bytes(r.uc.mem_read(LM_AT, lspan))
    V2, V1 = "ogfile2560_hs_s_fx2_v2", "ogfile2560_hs_s_fx2_v1"
    av2, lm2 = applied(av, V2, "av-cam.bin"), applied(lm0, V2, "libmpr.so")
    av1, lm1 = applied(av, V1, "av-cam.bin"), applied(lm0, V1, "libmpr.so")
    ok(av1 == av2 and lm1 != lm2, "the two encoder designs differ only in libmpr.so (the two MP4 header heights)")
    r, t, a, m = mp("L19", av, lm0)
    ok(not r.bad and a == av2 and m == lm2 and "DONE" in t, f"L19 ({V2}): {len(sts[V2]['av-cam.bin'])} + {len(sts[V2]['libmpr.so'])} sites new, every other byte unchanged")
    r, t, a, m = mp("L19", av2, lm2)
    ok(not r.bad and a == av2 and m == lm2 and not r.pwrites and not r.map_writes, "L19 again: no write")
    r, t, a, m = mp("L20", av2, lm2)
    ok(not r.bad and a == av and m == lm0 and "DONE" in t, "L20: both stock again, byte for byte")
    r, t, a, m = mp("N19", av, lm0)
    ok(not r.bad and a == av1 and m == lm1 and "DONE" in t, f"N19 ({V1}, --no-meta): its {len(sts[V1]['av-cam.bin'])} + {len(sts[V1]['libmpr.so'])} sites new, the heights stock")
    r, t, a, m = mp("L20", av1, lm1)
    ok(not r.bad and a == av and m == lm0 and "DONE" in t, "L20 on a camera holding N19's state: both stock again, byte for byte")
    r, t, a, m = mp("L19", av1, lm1)
    ok(not r.bad and a == av2 and m == lm2 and "DONE" in t and len(r.pwrites) == 2 and not r.map_writes, "L19 on a camera holding N19's state: only the two heights written")
    bad_av = bytearray(av)
    bad_av[design(V2)["descriptors"][0]["descriptor"] * 0x90 + 0x3AD030 + 0x28] ^= 1
    r, t, a, m = mp("L19", bytes(bad_av), lm0)
    ok(not r.bad and a == bytes(bad_av) and m == lm0 and not r.pwrites and not r.map_writes, "L19 with a guard of av-cam.bin wrong (a descriptor's profile key): nothing is written")
    r, t, a, m = mp("L19", av, lm0, pwrite_lost=[sts[V2]["libmpr.so"][0][0]])
    ok(not r.bad and a == av and m == lm0 and "NOT DONE" in t, "L19 with a libmpr.so write lost: everything put back")
    r, t, a, m = mp("L19", av, lm0, stale=[sts[V2]["av-cam.bin"][3][0]])
    ok(not r.bad and a == av and m == lm0 and "NOT DONE" in t, "L19 with the kernel's view not following a write: everything put back")
    for label, path in (("A7C II kit level 19 (ogfile2560_hs_s_c2_v1)", HERE.parent / "helper_c2/libJit_c2_level19_ogfile2560_hs_s_c2_v1.so"),
                        ("FX3 kit L19 (ogfile2560_hs_s_fx3_v2)", HERE.parent / "helper_fx3/libJit_fx3_L19.so")):
        if path.is_file():
            r, t, a, m = mp("L19", av, lm0, libpath=path)
            ok(not r.bad and a == av and m == lm0 and not r.pwrites and not r.map_writes, f"{label} on an FX2: nothing is written")
    print("ALL PASS" if not fail else "FAILED: %d" % len(fail))
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
