"""Run the built FX2 read-only helper in Unicorn against a model camera. Offline; no camera. (FX2 port, 2026-11-25)

  C:/Python313/python.exe -B emu_fx2.py [--show]

helper_fx3/emu_fx3.py with this camera's model (same harness: helper/emu_built.py; the same coprocessor model: only a transfer of one
whole page, direction 0, into the allocated buffer is accepted). Cases, for both libraries (check and dump):
  stock        an FX2 with the 1.01 files and stock memory                          -> every check same, verdict READY
  applied      every design site holding its new bytes, the screen step included    -> TARGET everywhere, verdict READY
  no-screen    the open-gate state without the screen step                          -> open-gate TARGET, screen words STOCK, READY
  no-meta      the encoder side without the MP4 header heights (N19)                -> its sites TARGET, the two heights STOCK, READY
  test1        v2: the diagnostic ladder's test 1 (L13 + fhband_fx2_v1)            -> raw buffer TARGET, records TEST, cells TARGET, READY
  a7c2         the A7C II 2.01 files and coprocessor image (the same platform)      -> identity DIFFERS, verdict NOT READY
  a7iv         the A7 IV 6.02 files and coprocessor image (the same sensor)         -> identity DIFFERS, verdict NOT READY
  fx3          the FX3 7.02 files and coprocessor image                             -> identity DIFFERS, verdict NOT READY
  no-reserve   a command line without the av-cam reservation                        -> av-cam.bin not read, NOT READY
  exists       a result file already present                                        -> nothing done
and the other way round, the published check libraries of the FX3, ZV-E1 and A7S III kits run on a stock FX2: each must say NOT READY
(an FX2 owner might run one of those kits; their apply scripts start only after a READY check).
"""
import json
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent / "helper"))
import emu_built as E  # noqa: E402
from unicorn import arm64_const as R  # noqa: E402

BASE = 0x108000
FACTS = json.loads((HERE / "fx2_expected.json").read_text(encoding="utf8"))
DES = ROOT / "modding/designs"
CP_RANGE = (0xC0000, 0x9B00000)                 # v2 reads the snapshot debug image's first pages (0x9a21000); a foreign helper is modelled too


def ex(build, rel):
    return (ROOT / "work/extracted" / build / "0700_part_image/dev" / rel).read_bytes()


def design(name):
    return json.loads((DES / f"{name}.json").read_text(encoding="utf8"))


class Run(E.Run):
    """E.Run with this helper's coprocessor model: cp_image (bytes at 0x108000) and cp_ram {address: bytes} over zeros."""

    def on_import(self, uc, address, size, _):
        x = lambda n: uc.reg_read(getattr(R, "UC_ARM64_REG_X%d" % n))
        name, ret = self.imports.get(address), 0
        if name == "_Z9dmm_allocjPj":
            self.lib_calls.append(("alloc", x(0) & 0xFFFFFFFF))
            uc.mem_write(x(1), struct.pack("<I", E.BUF_HANDLE))
            ret = self.buf
        elif name == "_Z8dmm_freej":
            self.lib_calls.append(("free", x(0) & 0xFFFFFFFF))
        elif name == "sen_dma_transfer":
            direction, src, dst, n = x(0) & 0xFFFFFFFF, x(1), x(2), x(3) & 0xFFFFFFFF
            self.lib_calls.append(("transfer", direction, src, dst, n))
            if direction != 0 or dst != self.buf or n != 4096 or src & 0xFFF or not CP_RANGE[0] <= src < CP_RANGE[1]:
                self.bad = "a transfer that is not a read of one whole page in range: dir %d src %#x dst %#x size %d" % (direction, src, dst, n)
                uc.emu_stop()
                return
            page = bytearray(4096)
            img = self.cp["image"]
            if BASE <= src < BASE + len(img):
                chunk = img[src - BASE:src - BASE + 4096]
                page[:len(chunk)] = chunk
            for a, blob in self.cp["ram"].items():
                lo, hi = max(a, src), min(a + len(blob), src + 4096)
                if lo < hi:
                    page[lo - src:hi - src] = blob[lo - a:hi - a]
            va = next(v for v, off in self.map_phys.items() if v in self.maps and off <= self.buf < off + self.maps[v]) + self.buf % 4096
            uc.mem_write(va, bytes(page))
        else:
            self.bad = "call of an unexpected import %r" % name
            uc.emu_stop()
            return
        uc.reg_write(R.UC_ARM64_REG_X0, ret)
        uc.reg_write(R.UC_ARM64_REG_PC, uc.reg_read(R.UC_ARM64_REG_X30))

    def go(self):
        self.uc.reg_write(R.UC_ARM64_REG_SP, E.STACK - 0x1000)
        self.uc.reg_write(R.UC_ARM64_REG_X30, E.RET)
        self.uc.emu_start(self.ctor, E.RET, count=3_000_000_000)
        if not self.bad and self.uc.reg_read(R.UC_ARM64_REG_PC) != E.RET:
            self.bad = "the constructor did not return (pc %#x)" % self.uc.reg_read(R.UC_ARM64_REG_PC)
        return self


WS, UNITS = 0x21A5D18, 0x21A5D18 + 0x107E0          # the memory manager's workspace and unit objects (the first FX2 test's L13 report)


def workspace():
    """A small model of the workspace after a movie look with L13 applied: a parent 0x6fa divided as group 0x8d with two 33,003,520-byte
    0x57f units (one held by handle 0, memory id 0x43e), and a left-over 0x6a3 object of an earlier division. Read by fx2_run.py's decoder."""
    import struct as S
    ws = bytearray(0x35230)
    S.pack_into("<II", ws, 0, 0x43E, 7)                              # handle 0: memory id 0x43e, serial 7
    S.pack_into("<I", ws, 0x10, UNITS + 1 * 0x50)                    # its unit: object 1
    for h in range(1, 0x3FF):
        S.pack_into("<I", ws, h * 0x40, 0xFFFFFFFF)

    def obj(i, flags, base, off, size, parent, key, owner, group):
        o = 0x107E0 + i * 0x50
        S.pack_into("<HH", ws, o, i, flags)
        S.pack_into("<Q", ws, o + 8, base)
        S.pack_into("<II", ws, o + 0x10, off, size)
        S.pack_into("<III", ws, o + 0x20, parent, key, owner)
        S.pack_into("<I", ws, o + 0x30, group)
    obj(0, 1, 0x4A0000000, 0, 73400320, 0, 0x6FA, 0, 0x8D)
    obj(1, 0, 0x4A0000000, 0, 33003520, UNITS, 0x57F, WS, 0)
    obj(2, 0, 0x4A0000000, 33003520, 33003520, UNITS, 0x57F, 0, 0)
    obj(3, 0, 0x4B0000000, 0, 27864320, UNITS + 9 * 0x50, 0x6A3, 0, 0)     # left over: its parent object is not divided now
    S.pack_into("<H", ws, 0x33410, 0)
    S.pack_into("<H", ws, 0x33428 + 2 * 0x8D, 1)
    return bytes(ws)


def model(build="fx2_101", applied=False, screen=True, reserve=True, exists=False, enc="ogfile2560_hs_s_fx2_v2", test=None):
    cp = bytearray(ex(build, "nflasha8/cpapp-b.bin"))
    av = bytearray(ex(build, "nflasha3/av-cam.bin"))
    libs = {n: ex(build, "nflasha15/lib" + n) for n in ("/libmpr.so", "/libsencore.so", "/libJiritsu.so")}
    lm = bytearray(libs["/libmpr.so"])
    og, oz, fl, sc, dm = design("ogsq_fx2_v1"), design("outsz2560_fx2_v1"), design(enc), design("lcd32dsq_fx2_v1"), design("dmmwb4688_fx2_v1")
    ram = {}
    if build == "fx2_101":                       # the FX2's RAM tables; a foreign body keeps its own image and zeros
        sr = og["stored_record"]
        ram[int(sr["address"], 16)] = bytes.fromhex(sr["design" if applied else "stock"])
        for g in oz["guards"]:
            ram[int(g["ram_address"], 16)] = bytes.fromhex(g["bytes"])
        for s in oz["sites"]:
            ram[int(s["ram_address"], 16)] = bytes.fromhex(s["new" if applied else "old"])
        for s in dm["sites"]:                     # the memory manager's RAM copy of DmmCfg.bin
            ram[int(s["ram_address"], 16)] = bytes.fromhex(s["new" if applied or test else "old"])
        ram[0x192FC28] = struct.pack("<I", WS)    # the page of pointers: workspace and unit objects
        ram[0x192F77C] = struct.pack("<I", UNITS)
        ram[WS] = workspace()
        # v3: a model of the saved output records: four records 3840x2160 / 1920x1080 / 1920x1080 / 3840x2160, format code 2, types 0 (the
        # A7 IV camera's values, F686, and what the tester's FX2 holds). v4: at 0x15cdef8, where 0xbc75de says they are (v3 had 0x15cd7e0)
        orec = bytearray(4 + 4 * 0x2C)
        for k, (w, h) in enumerate(((3840, 2160), (1920, 1080), (1920, 1080), (3840, 2160))):
            struct.pack_into("<HH", orec, 4 + 0x2C * k + 4, w, h)
            struct.pack_into("<I", orec, 4 + 0x2C * k + 0x20, 2)
        ram[0x15CDEF8] = bytes(orec)
        # v4: the saved resize view (0x15cd520) as the tester's FX2 held it in the stock state (dump 045730, byte 0 clear), and the margin
        # words of 0xbd6f34 (the model has none set)
        view = bytearray(0x54)
        view[4], view[5] = 1, 1
        for off, (w, h) in ((0x14, (7040, 3958)), (0x1C, (7032, 3958)), (0x20, (12, 8)), (0x24, (7008, 3942)),
                            (0x28, (7040, 3958)), (0x30, (7032, 3958)), (0x34, (12, 8)), (0x38, (7008, 3942)), (0x3C, (4336, 2438)), (0x40, (3840, 2160))):
            struct.pack_into("<HH", view, off, w, h)
        struct.pack_into("<II", view, 0x44, 0x8C0, 1)
        ram[0x15CD520] = bytes(view)
        ram[0x190F46E] = bytes(16)
        if test:                                  # a test design at the sensor sites and in the stored record
            td = design(test)
            ram[int(td["stored_record"]["address"], 16)] = bytes.fromhex(td["stored_record"]["design"])
            for q in td["patches"]:
                a, new = int(q["addr"], 16), bytes.fromhex(q["new"])
                cp[a - BASE:a - BASE + len(new)] = new
    if applied:
        for p in og["patches"]:
            a, new = int(p["addr"], 16), bytes.fromhex(p["new"])
            cp[a - BASE:a - BASE + len(new)] = new
        for p in fl["patches"]:
            o, new = int(p["file_off"], 16), bytes.fromhex(p["new"])
            (lm if p["binary"] == "libmpr.so" else av)[o:o + len(new)] = new
        if screen:
            for s in sc["sites"]:
                a = int(s["ram_address"], 16)
                cp[a - BASE:a - BASE + 4] = bytes.fromhex(s["new"])
    lm_at = 0x7F82D15000
    maps = b"".join(b"%x-%x r-xp 00000000 b3:0f 100 /usr/lib%s\n" % (a, a + ((len(libs[n]) + 0xFFF) & ~0xFFF), n.encode())
                    for n, a in (("/libsencore.so", 0x7F80000000), ("/libJiritsu.so", 0x7F81000000), ("/libmpr.so", lm_at)))
    files = E.tree()
    files["/proc/self/maps"] = maps
    files["/proc/meminfo"] = b"MemTotal: 1 kB\n"
    files["/dev/mem"] = b""
    files["/proc/cmdline"] = b"console=ttyS0 " + (b"memrsv=0x01000000@0x401000000:ex " if reserve else b"") + b"warm.mode=2"
    for n, b in libs.items():
        files["/usr/lib" + n] = b
    dirs = {"/tmp_wbshd", "/proc", "/proc/self", "/sys/module/liro/parameters", "/log", "/usr/lib"}
    if exists:
        files[E.RESULT] = b"earlier result\n"
    phys = {FACTS["avcam_phys"]: bytes([0x5A]) * 0x1000 + bytes(av[0x1000:]),      # the first page is not as in the file on a camera (A7S III, 2026-11-21)
            E.BUF_PHYS & ~0xFFF: bytes(0x2000)}
    own = {lm_at: bytes(lm)}
    return files, dirs, phys, {"image": bytes(cp), "ram": ram}, own


def run(lib, **kw):
    files, dirs, phys, cp, own = model(**kw)
    r = Run(lib, 22, files, dirs, phys=phys, cp=cp, own=own)      # level 22: the A7 IV harness's rules for a read-only helper that maps /dev/mem
    r.go()
    return r, r.writes.get(E.RESULT, b"").decode("utf8", "replace")


def main():
    ok = True
    screen_n = sum(1 for s in FACTS["cp_sites"] if s["name"].startswith("screen"))
    # sites the applied state changes: not the output-size guards, and not the fallback's code word (v4: its own optional step, F16)
    hard = [s for s in FACTS["cp_sites"] if not s["name"].startswith(("outsize_guard", "fehold"))]
    for which in ("check", "dump"):
        lib = (HERE / f"libJit_fx2_{which}.so").read_bytes()
        for case, kw, want in (("stock", {}, ("VERDICT READY", "STOCK")), ("applied", {"applied": True}, ("VERDICT READY", "TARGET")),
                               ("no-screen", {"applied": True, "screen": False}, ("VERDICT READY", "TARGET")),
                               ("no-meta", {"applied": True, "enc": "ogfile2560_hs_s_fx2_v1"}, ("VERDICT READY", "TARGET")),
                               ("test1", {"test": "fhband_fx2_v1"}, ("VERDICT READY", "  TEST")),
                               ("test5", {"test": "ogh2560_fx2_v1"}, ("VERDICT READY", "  TEST2")),
                               ("a7c2", {"build": "a7c2_201"}, ("VERDICT NOT READY", "DIFFERS from the 1.01 update")),
                               ("a7iv", {"build": "a7iv_602"}, ("VERDICT NOT READY", "DIFFERS from the 1.01 update")),
                               ("fx3", {"build": "fx3_702"}, ("VERDICT NOT READY", "DIFFERS from the 1.01 update")),
                               ("no-reserve", {"reserve": False}, ("VERDICT NOT READY", "av-cam.bin is not read")), ("exists", {"exists": True}, ())):
            r, text = run(lib, **kw)
            problems = []
            if r.bad:
                problems.append("stopped: " + r.bad)
            if set(r.writes) - {E.RESULT}:
                problems.append("wrote other files: %s" % sorted(set(r.writes) - {E.RESULT}))
            if any(c[0] == "transfer" and c[1] != 0 for c in r.lib_calls):
                problems.append("a transfer towards the coprocessor")
            if case == "exists":
                if r.writes or r.lib_calls:
                    problems.append("did something although a result existed")
            else:
                problems += ["missing %r" % w for w in want if w not in text]
                if "== done" not in text:
                    problems.append("result not complete")
                if case == "stock" and ("OTHER" in text.replace("OTHER (not counted", "") or "DIFFERS" in text or "!!" in text.split("== identity")[1]):
                    problems.append("a stock camera is not reported as all stock")
                if case == "applied" and text.count("TARGET") < len(hard) + FACTS["lm_sites"] + FACTS["av_sites"]:
                    problems.append("not every site reported TARGET: %d" % text.count("TARGET"))
                if case == "no-screen":
                    st = sum(1 for ln in text.split("\n") if ln.startswith("site screen") and ln.endswith("  STOCK"))
                    if st != screen_n or text.count("TARGET") < len(hard) - screen_n + FACTS["lm_sites"] + FACTS["av_sites"]:
                        problems.append("no-screen: %d screen words stock (want %d)" % (st, screen_n))
                if case == "no-meta":                      # N19: its sites TARGET, the two header heights STOCK
                    lm = [ln for ln in text.split("\n") if ln.startswith("lm ")]
                    if sum(ln.endswith("TARGET") for ln in lm) != 4 or sum(ln.endswith("STOCK") for ln in lm) != 2:
                        problems.append("no-meta: libmpr lines %s" % lm)
                if case in ("stock", "applied", "test1", "test5"):  # the raw write buffer's four words are hard sites
                    rb = [ln for ln in text.split("\n") if ln.startswith("site rawbuf_")]
                    if len(rb) != 4 or not all(ln.endswith("  " + ("STOCK" if case == "stock" else "TARGET")) for ln in rb):
                        problems.append("raw write buffer words: %s" % rb)
                if case == "test1":                        # the 13 sensor sites and the stored record hold the test design
                    tl = [ln for ln in text.split("\n") if ln.startswith("site ") and ln.endswith("  TEST")]
                    tg = [ln for ln in text.split("\n") if ln.startswith("site S") and ln.endswith("  TARGET")]
                    if len(tl) != 3 or len(tg) != 11:      # the records and the stored record differ from the squeeze design; the 11 cells are the same
                        problems.append("test1: %d sites TEST (want 3), %d cells TARGET (want 11)" % (len(tl), len(tg)))
                if case == "test5":                        # v4: ogh2560_fx2_v1 = the squeeze design with other records: 2 sites TEST2, the rest TARGET
                    t2 = [ln.split(" ")[1] for ln in text.split("\n") if ln.startswith("site ") and ln.endswith("  TEST2")]
                    tg = [ln for ln in text.split("\n") if (ln.startswith("site S") or ln.startswith("site stored_record")) and ln.endswith("  TARGET")]
                    if t2 != ["record_left", "record_right"] or len(tg) != 12 or "  TEST\n" in text:
                        problems.append("test5: TEST2 at %s (want the two records), %d sites TARGET (want 12)" % (t2, len(tg)))
                if case == "stock":                        # v4: the fallback's code word is reported, stock
                    fl_ = [ln for ln in text.split("\n") if ln.startswith("site fehold ")]
                    if len(fl_) != 1 or not fl_[0].endswith("  STOCK"):
                        problems.append("fehold: %s" % fl_)
                if which == "dump" and case == "stock" and text.count("cppage ") != sum(k for _, _, k in FACTS["dump_ranges"]):
                    problems.append("dump pages: %d" % text.count("cppage "))
            n_tr = sum(1 for c in r.lib_calls if c[0] == "transfer")
            print(f"{which:5} {case:10} {'ok' if not problems else 'FAILED'}  result {len(text):7} bytes, {n_tr:3} page reads  {'; '.join(problems)}")
            ok &= not problems
            if "--show" in sys.argv and case == "stock":
                print("\n".join(ln[:150] for ln in text.split("== identity")[1].splitlines()[:80]))
    # ---- the other kits' check libraries on an FX2
    for kit, path, verdict in (("FX3 kit", HERE.parent / "helper_fx3/libJit_fx3_check.so", "DIFFERS from the 7.02 update"),
                               ("ZV-E1 kit", HERE.parent / "helper_zv/libJit_zv_check.so", "DIFFERS from the 2.02 update"),
                               ("A7S III kit", HERE.parent / "helper_s3/libJit_s3_check.so", "DIFFERS from the 5.01 update")):
        if not path.is_file():
            print(f"foreign {kit}: library not here, skipped")
            continue
        r, text = run(path.read_bytes())
        good = not r.bad and "VERDICT NOT READY" in text and verdict in text and not (set(r.writes) - {E.RESULT})
        print(f"foreign {kit:12} on a stock FX2: {'ok, NOT READY' if good else 'FAILED'}  {r.bad or ''}")
        ok &= good
    print("ALL PASS" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
