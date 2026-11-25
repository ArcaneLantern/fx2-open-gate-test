"""Emulate the FX2 1.01 rear-screen layout pieces, stock and with lcd32dsq_fx2_v1 applied, in Unicorn on the FX2's own code.

  C:\\Python313\\python.exe -B build\\emu_lcd_fx2.py [--save]          (--save writes evidence/fx2/lcd32dsq_fx2_v1_emu.json)

Functions run (cpapp-b.bin 1.01, loaded at 0x108000), each called the way its caller calls it:
  0x1f9e98  fit mode (panel code, picture aspect code)                                   (the A7 IV's 0x1e4b78, byte for byte)
  0x1fa328  picture ratio: (_, w | h << 16, panel code, aspect, [fit, flags, out])       -> out = x, y, w, h     (layout 0x1fa42c)
  0x1fa0c0  de-squeeze:    (_, w | h << 16, panel code, aspect, [fit, flags, out, accessor, device]); the code byte from the accessor's
            slot 0x798; slot 0x688 + 0x1fa024 give the picture record whose source size (+0x36 / +0x38) the pillarbox test of codes 1-3 uses
            (modelled: one record, type 0, 1920 x 1080); slot 0x6d0 is read for device 4 (HDMI) only (not run)
  0x721e3c  input crop (codes 4/5): (crop rect, frame info, accessor, device); 0x73518c (de-squeeze active) -> 1, 0x737bc8 -> the path flag
  0x7214b6  output-device picture rectangle (DevCmdOutv): (device, accessor, out, out2); 0x71f62e -> the output rectangle, slots 0x538 -> 1,
            0x4b8 -> the picture rectangle, 0x4a8 -> 1, 0x737bd6 -> 1, 0x73518c -> 1, slot 0x798 -> the code, 0x1fa024 -> the record
  0x128438  frame check (focus frames; the A7 IV's code relinked): 0x692802 -> 0, 0x6a14da -> output kind (0 rear), 0x6929ea -> the
            live-view rectangle (y0, y1, x0, x1) and the output size, 0x692c6a -> table row (0 or 1); model aspect 4 at +0x1e58 (16:9 column)
Panels: 720 x 480 (3:2: the FX2's rear monitor, panel code 1, frame row 1) and 800 x 600 (4:3: panel code 0, frame row 0, the EVF's kind
of panel). Picture aspect 2 (16:9) is the open-gate live view. Every expected value is asserted. Read-only apart from the evidence file.
"""
import json
import struct
import sys
from pathlib import Path

from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_HOOK_CODE, UC_HOOK_MEM_UNMAPPED
from unicorn import arm_const as A

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "build"))
import locate_file  # noqa: E402

B = 0x108000
FX = locate_file.locate("fx2_101", "cpapp-b.bin").read_bytes()
DESIGN = json.loads((ROOT / "modding/designs/lcd32dsq_fx2_v1.json").read_text(encoding="utf8"))
RET, STK, OBJ, STUBS, REC = 0x2410000, 0x2300000, 0x2440000, 0x2480000, 0x24C0000
PANELS = {"3:2": (720, 480, 1, 1), "4:3": (800, 600, 0, 0)}      # w, h, panel code, frame-table row
SRC = (1920, 1080)                                               # the picture record's source size (a 16:9 live view)


class Cp:
    def __init__(self, patched):
        img = bytearray(FX)
        if patched:
            for s in DESIGN["sites"]:
                a = int(s["ram_address"], 16)
                assert img[a - B:a - B + 4] == bytes.fromhex(s["old"])
                img[a - B:a - B + 4] = bytes.fromhex(s["new"])
            for g in DESIGN["guards"]:
                a = int(g["ram_address"], 16)
                assert img[a - B:a - B + len(g["bytes"]) // 2] == bytes.fromhex(g["bytes"])
        self.uc = uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
        try:
            uc.ctl_set_cpu_model(A.UC_CPU_ARM_CORTEX_A15)
        except Exception:
            pass
        uc.mem_map(0x100000, 0x2500000)
        uc.mem_write(B, bytes(img))
        uc.reg_write(A.UC_ARM_REG_C1_C0_2, uc.reg_read(A.UC_ARM_REG_C1_C0_2) | (0xF << 20))
        uc.reg_write(A.UC_ARM_REG_FPEXC, 0x40000000)
        self.stubs, self.log = {}, []
        uc.hook_add(UC_HOOK_MEM_UNMAPPED, lambda u, acc, addr, sz, v, _: self.log.append(f"unmapped {addr:#x} pc={u.reg_read(A.UC_ARM_REG_PC):#x}") or False)
        # the picture record 0x1fa024 hands back (StandardDataStructureParser): count 1, entry type 0, its data's source size at +0x36 / +0x38
        uc.mem_write(REC, bytes(0x100))
        uc.mem_write(REC + 0xC, struct.pack("<II", 1, 0x20))
        uc.mem_write(REC + 0x20, struct.pack("<IIII", 0, 0, 0, 0x40))
        uc.mem_write(REC + 0x40 + 0x36, struct.pack("<HH", *SRC))

        def parser(u):
            p = u.reg_read(A.UC_ARM_REG_R0)
            u.mem_write(p, struct.pack("<II", 0, REC))
            return p
        self.stub(0x1FA024, parser)

    def stub(self, addr, fn):
        """fn(uc) -> r0 (or None to leave r0); the stubbed function returns to LR at once"""
        if addr not in self.stubs:
            self.uc.hook_add(UC_HOOK_CODE, lambda u, ad, sz, _: self._run_stub(ad), begin=addr, end=addr)
        self.stubs[addr] = fn

    def _run_stub(self, addr):
        u = self.uc
        r0 = self.stubs[addr](u)
        if r0 is not None:
            u.reg_write(A.UC_ARM_REG_R0, r0 & 0xFFFFFFFF)
        u.reg_write(A.UC_ARM_REG_PC, u.reg_read(A.UC_ARM_REG_LR))

    def call(self, fn, regs, stack=()):
        u = self.uc
        sp = STK - 0x800
        for i, v in enumerate(stack):
            u.mem_write(sp + 4 * i, struct.pack("<I", v & 0xFFFFFFFF))
        for r, v in zip((A.UC_ARM_REG_R0, A.UC_ARM_REG_R1, A.UC_ARM_REG_R2, A.UC_ARM_REG_R3), regs):
            u.reg_write(r, v & 0xFFFFFFFF)
        u.reg_write(A.UC_ARM_REG_SP, sp)
        u.reg_write(A.UC_ARM_REG_LR, RET | 1)
        u.emu_start(fn | 1, RET, count=200000)
        assert not self.log, self.log
        return u.reg_read(A.UC_ARM_REG_R0)

    def rect(self, a, signed=False):
        return list(struct.unpack("<4h" if signed else "<4H", bytes(self.uc.mem_read(a, 8))))

    # ---- the accessor object: [OBJ] = vtable; slots as listed in the module text
    def accessor(self, code, slots=None):
        u, vt, ptr = self.uc, OBJ + 0x1000, OBJ + 0x3000
        u.mem_write(OBJ, struct.pack("<I", vt))
        u.mem_write(ptr, bytes([code, 1]))                                # code, enable
        def r688(uc):
            uc.reg_write(A.UC_ARM_REG_R1, 0)
            return 0x1000                                                 # a non-zero 64-bit record handle (the parser is stubbed)
        table = {0x798: lambda uc: ptr, 0x688: r688, 0x6D0: lambda uc: 0}
        table.update(slots or {})
        for slot, fn in table.items():
            a = STUBS + slot * 4
            u.mem_write(a, b"\x70\x47")                                   # bx lr (the stub hook returns first)
            u.mem_write(vt + slot, struct.pack("<I", a | 1))
            self.stub(a, fn)
        return OBJ

    def fit(self, panel, aspect):
        return self.call(0x1F9E98, (panel, aspect))

    def ratio(self, w, h, panel, aspect):
        out = OBJ + 0x8000
        self.uc.mem_write(out, bytes(8))
        self.call(0x1FA328, (0, w | h << 16, panel, aspect), (self.fit(panel, aspect), 0, out))
        return self.rect(out)

    def desqueeze(self, w, h, panel, aspect, code, device=1):
        out = OBJ + 0x8000
        self.uc.mem_write(out, bytes(8))
        acc = self.accessor(code)
        self.call(0x1FA0C0, (0, w | h << 16, panel, aspect), (self.fit(panel, aspect), 0, out, acc, device))
        return self.rect(out)

    def crop(self, code, path, full_w=1920, h=1080, x=0, aspect=2):
        r, f = OBJ + 0x9000, OBJ + 0x9100
        self.uc.mem_write(r, bytes(0x20))
        self.uc.mem_write(r + 8, struct.pack("<H", full_w))
        self.uc.mem_write(r + 0xC, struct.pack("<HHHH", x, 0, full_w - 2 * x, h))
        self.uc.mem_write(f, bytes(0x20))
        self.uc.mem_write(f + 0x1E, bytes([aspect]))
        acc = self.accessor(code)
        self.stub(0x73518C, lambda uc: 1)
        self.stub(0x737AC0, lambda uc: None)
        self.stub(0x737BC8, lambda uc: path)
        self.call(0x721E3C, (r, f, acc, 1))
        x_, _, w_, h_ = struct.unpack("<4H", bytes(self.uc.mem_read(r + 0xC, 8)))
        return [x_, w_, h_]

    def outv(self, code, w=720, h=480):
        """0x7214b6 for the rear output: returns the picture rectangle it gives (x, y, w, h; signed)"""
        out3, out4, pic = OBJ + 0xA000, OBJ + 0xA100, OBJ + 0xA200
        u = self.uc
        u.mem_write(out3, bytes(16))
        u.mem_write(out4, bytes(16))
        u.mem_write(pic, struct.pack("<4H", 0, 0, w, h))
        acc = self.accessor(code, {0x538: lambda uc: 1, 0x4B8: lambda uc: pic, 0x4A8: lambda uc: 1})

        def outrect(uc):
            uc.mem_write(uc.reg_read(A.UC_ARM_REG_R0), struct.pack("<4H", 0, 0, w, h))
            return None
        self.stub(0x71F62E, outrect)
        self.stub(0x737AC0, lambda uc: None)
        self.stub(0x737BD6, lambda uc: 1)
        self.stub(0x73518C, lambda uc: 1)
        self.call(0x7214B6, (1, acc, out3, out4))
        return self.rect(out3, signed=True)

    def frame_check(self, live, out_w, out_h, kind, row_sel, model_aspect=4):
        """live = (x, y, w, h) in output pixels; returns 1 when the widgets accept it"""
        m = OBJ + 0x10000
        u = self.uc
        u.mem_write(m, bytes(0x3000))
        u.mem_write(m + 0x1E58, struct.pack("<I", model_aspect))
        x, y, w, h = live

        def lv(uc):
            sp = uc.reg_read(A.UC_ARM_REG_SP)
            p_h = struct.unpack("<I", bytes(uc.mem_read(sp, 4)))[0]
            uc.mem_write(uc.reg_read(A.UC_ARM_REG_R1), struct.pack("<4i", y, y + h, x, x + w))
            uc.mem_write(uc.reg_read(A.UC_ARM_REG_R3), struct.pack("<H", out_w))
            uc.mem_write(p_h, struct.pack("<H", out_h))
            return 1
        self.stub(0x692802, lambda uc: 0)
        self.stub(0x6A14DA, lambda uc: kind)
        self.stub(0x6929EA, lv)
        self.stub(0x692C6A, lambda uc: row_sel)
        return self.call(0x128438, (m,))


def run():
    st, pa = Cp(False), Cp(True)
    res = {"design": DESIGN["design"], "image_sha256": DESIGN["artifact_sha256"], "source_size_in_the_record": list(SRC), "cases": []}
    case = lambda **k: res["cases"].append(k)
    # ---- fit mode of a 16:9 picture: letterbox on both shapes stock; fill on the 3:2 panel patched, the 4:3 panel (EVF) unchanged
    want_fit = {"3:2": (3, 0), "4:3": (3, 3)}
    for name, (w, h, pc, _) in PANELS.items():
        s, p = st.fit(pc, 2), pa.fit(pc, 2)
        assert (s, p) == want_fit[name], (name, s, p)
        case(what="fit mode, 16:9 picture", panel=name, stock=s, patched=p)
        for asp in (0, 1, 3, 5):
            assert st.fit(pc, asp) == pa.fit(pc, asp)
    assert st.fit(2, 2) == pa.fit(2, 2) == 0                              # a 16:9 panel: fill, stock and patched
    # ---- the live view, de-squeeze off
    want = {"3:2": ([0, 38, 720, 404], [0, 0, 720, 480]), "4:3": ([0, 75, 800, 450], [0, 75, 800, 450])}
    for name, (w, h, pc, _) in PANELS.items():
        s, p = st.ratio(w, h, pc, 2), pa.ratio(w, h, pc, 2)
        assert [s, p] == list(want[name]), (name, s, p)
        shown = p[2] / p[3]
        if name == "3:2":
            assert abs(shown - 1.5) < 0.001, shown
        case(what="live view, de-squeeze off, 16:9 picture (the open-gate frame)", panel=name, stock=s, patched=p, shown_aspect=round(shown, 4),
             true_shape_of_the_picture=1.5, note="squeezed 32/27 in the 16:9 frame, so the 4:3 panel's letterbox shows it squeezed (as the A7 IV's EVF)"
             if name == "4:3" else "the whole 3:2 panel: the true shape")
        for asp in (0, 1, 3, 5):                                          # every other picture shape is untouched
            assert st.ratio(w, h, pc, asp) == pa.ratio(w, h, pc, asp), (name, asp)
        case(what="live view, other picture aspect codes 0, 1, 3, 5", panel=name, stock_equals_patched=True)
    # ---- the built-in de-squeeze, against the shape the recorded 3:2 frame has once de-squeezed
    factors = {1: 1.3, 2: 1.5, 3: 1.65, 4: 1.8, 5: 2.0}
    want_s = {"3:2": {1: [0, 84, 720, 312], 2: [0, 104, 720, 272], 3: [0, 118, 720, 244], 4: [0, 90, 720, 300], 5: [0, 104, 720, 272]},
              "4:3": {1: [0, 126, 800, 348], 2: [0, 150, 800, 300], 3: [0, 164, 800, 272], 4: [0, 134, 800, 332], 5: [0, 150, 800, 300]}}
    want_p = {"3:2": {1: [0, 56, 720, 368], 2: [0, 120, 720, 240], 3: [0, 94, 720, 292], 4: [0, 106, 720, 268], 5: [0, 120, 720, 240]},
              "4:3": {1: [0, 94, 800, 412], 2: [0, 166, 800, 268], 3: [0, 138, 800, 324], 4: [0, 152, 800, 296], 5: [0, 166, 800, 268]}}
    for name, (w, h, pc, _) in PANELS.items():
        assert st.desqueeze(w, h, pc, 2, 0) == pa.desqueeze(w, h, pc, 2, 0) == [0, 0, w, h]
        for code, fac in factors.items():
            s, p = st.desqueeze(w, h, pc, 2, code), pa.desqueeze(w, h, pc, 2, code)
            assert s == want_s[name][code] and p == want_p[name][code], (name, code, s, p)
            # stock: the shape a 16:9 picture gets (codes 4 and 5 after their 4:3 centre crop); patched: the shape the 3:2 picture gets
            stock_target = 16 / 9 * fac if code in (1, 2, 3) else 4 / 3 * fac
            target = 1.5 * fac
            shown_s, shown_p = s[2] / s[3], p[2] / p[3]
            assert abs(shown_s / stock_target - 1) < 0.02, (name, code, shown_s, stock_target)
            if code != 2:                                                 # code 2's 16:9 case is code 5's words (3:1); no menu entry sends it
                assert abs(shown_p / target - 1) < 0.012, (name, code, shown_p, target)
            else:
                assert p == want_p[name][5]
            for asp in (5, 0, 1):
                a_s, a_p = st.desqueeze(w, h, pc, asp, code), pa.desqueeze(w, h, pc, asp, code)
                if code in (1, 2, 3):                                     # 17:9, 4:3 and 3:2 pictures: untouched
                    assert a_s == a_p, (name, code, asp, a_s, a_p)
                else:                                                     # codes 4 and 5: the one ratio for every shape, changed for all
                    assert a_p == p, (name, code, asp)
            case(what=f"de-squeeze code {code} ({fac}x), 16:9 picture" + (" (in the FX2 1.01 menu)" if code in (1, 5) else " (not in the 1.01 menu)"),
                 panel=name, stock=s, patched=p, shown_stock=round(shown_s, 4), shown_patched=round(shown_p, 4),
                 right_for_the_3_2_frame=round(target, 4), stock_with_the_3_2_frame_is_off_by=round(shown_s / target, 4))
    # ---- the centre 4:3 input crop of codes 4 and 5
    for path in (0, 1):
        for code in (4, 5):
            s, p = st.crop(code, path), pa.crop(code, path)
            want_c = [240, 1440, 1080] if (path == 0 or code == 5) else [0, 1920, 1080]
            assert s == want_c and p == [0, 1920, 1080], (path, code, s, p)
            case(what=f"input crop, code {code}, path flag {path}, 1920 x 1080 live view", stock=s, patched=p)
        for code in (1, 2, 3):
            assert st.crop(code, path) == pa.crop(code, path) == [0, 1920, 1080]
    s, p = st.crop(5, 1, x=96), pa.crop(5, 1, x=96)                       # path 1 with an existing offset (the 3/4 branch)
    assert s == [312, 1296, 1080] and p == [96, 1728, 1080], (s, p)
    case(what="input crop, code 5, path flag 1, an existing offset 96", stock=s, patched=p)
    s, p = st.crop(5, 1, aspect=5), pa.crop(5, 1, aspect=5)               # a 17:9 picture, path 1
    assert s == [240, 1440, 1080] and p == [0, 1920, 1080], (s, p)
    case(what="input crop, code 5, path flag 1, 17:9 picture", stock=s, patched=p)
    # ---- the output-device picture rectangle (DevCmdOutv)
    for code in (1, 2, 3, 4, 5):
        s, p = st.outv(code), pa.outv(code)
        if code in (4, 5):
            assert s == [-120, 0, 960, 480] and p == [0, 0, 720, 480], (code, s, p)
        else:
            assert s == p == [0, 0, 720, 480], (code, s, p)
        case(what=f"output-device picture rectangle, code {code}, 720 x 480", stock=s, patched=p)
    # ---- the frame check: the patched tables take the patched live view on the 3:2 panel; the 4:3 row is untouched
    w, h, pc, row = PANELS["3:2"]
    s_live, p_live = want["3:2"]
    ok = lambda cp, live, rs=row, ow=w, oh=h: cp.frame_check(live, ow, oh, 0, rs)
    r = {"stock_tables_stock_view": ok(st, s_live), "patched_tables_patched_view": ok(pa, p_live),
         "stock_tables_patched_view": ok(st, p_live), "patched_tables_stock_view": ok(pa, s_live)}
    assert r == {"stock_tables_stock_view": 1, "patched_tables_patched_view": 1, "stock_tables_patched_view": 0, "patched_tables_stock_view": 0}, r
    case(what="frame check (cpActAfWindow 0x128438), rear output, table row 1", panel="3:2", **r)
    w4, h4, _, row4 = PANELS["4:3"]
    r4 = {"stock": ok(st, want["4:3"][0], row4, w4, h4), "patched": ok(pa, want["4:3"][1], row4, w4, h4)}
    assert r4 == {"stock": 1, "patched": 1}, r4
    case(what="frame check, 4:3 panel (row 0: the letterbox, unchanged)", panel="4:3", **r4)
    dsq = {code: (ok(st, st.desqueeze(w, h, pc, 2, code)), ok(pa, pa.desqueeze(w, h, pc, 2, code))) for code in (1, 5)}
    assert all(a == b == 0 for a, b in dsq.values()), dsq                 # de-squeeze: no frame check passes, stock or patched
    case(what="frame check while de-squeeze is on (stock and patched alike)", panel="3:2", results={str(k): list(v) for k, v in dsq.items()})
    return res


if __name__ == "__main__":
    res = run()
    for c in res["cases"]:
        print(json.dumps(c))
    print(f"{len(res['cases'])} cases as expected")
    if "--save" in sys.argv:
        out = ROOT / "evidence" / "fx2" / "lcd32dsq_fx2_v1_emu.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(res, indent=1) + "\n", encoding="utf8", newline="\n")
        print("wrote", out)
