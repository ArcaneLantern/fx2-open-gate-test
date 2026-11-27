"""FX2 1.01: function-level emulation of the encoder-side designs ogfile2560_hs_s_fx2_v1 and ogfile2560_hs_s_fx2_v2 (build/build_ogfile.py
--build fx2_101 [--meta]), stock against changed, in the FX2's own av-cam.bin and libmpr.so. The changes are applied in emulated memory only.

The A7 IV's run_ogfile_emu.py, pointed at the FX2's functions (found by masked instruction matching, modding/FX2_PORT_ENCODER.md):
  av-cam.bin  descriptor matcher 0x2360ac (A7 IV 0x21b780; walks 0x2b3 = 691 descriptors from 0x3ad030, the request read at the A7 IV's offsets)
              clip-format matcher 0x1a2670 (A7 IV 0x190128; the FX2 takes (object, request) with the raster at request +0x68/+0x6a and the
                kind byte at +0x81, where the A7 IV's single argument held them at +0xa0/+0xa2/+0xb9)
              memory-class function 0x22dfa4 (A7 IV 0x2136c4; the same context offsets): which memory ids it asks for
              start-block builder 0x231db0 (A7 IV 0x2174c0) with each changed profile and a 3840x2560 picture
              helpers: log 0x28dc3c / 0x28dbfc, memset 0x28e170, memcpy 0x28e158, DMM open 0x23db64
  vcd_firmware_imola2.bin   (the A7 IV's file byte for byte) the codec's memory calculation for the changed descriptors against the FX2's
              main-processor blocks of unit-type row 3 after the change (build/emu_vcd_chmem.py with the FX2's tables: frame rates 0x345a80)
  libmpr.so   the encoder request's raster (g_videoParamComb 0x2cdc58 rows +4/+6, what SetEncOpenParam copies) and the MP4 track config
              0x21f364 (build/emu_mp4_meta.py's model) for combs 0, 2, 5, 7: v1 leaves the MP4 height at 2160, v2 makes it 2560
Run with the Python that has Unicorn:  C:\\Python313\\python.exe -B build/run_ogfile_emu_fx2.py      writes evidence/fx2/ogfile2560_emu_fx2.json
Nothing was run on a camera.
"""
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "build"))
import emu_mp4_meta  # noqa: E402
import emu_vcd_chmem as V  # noqa: E402
import locate_file  # noqa: E402
import run_ogfile_emu as E  # noqa: E402

AVB = E.AVB
BUILD = "fx2_101"
DESC, NDESC, UNIT_TABLE, FPS_TABLE = 0x3AD030, 691, 0x3ACF90, 0x345A80
PROFILES = ((0x3C54E0, 376), (0x3DCDE0, 315))
COMB = 0x2CDC58
# the FX2's functions in the A7 IV module's names (its AvCam reads these module globals at call time)
E.DESC = AVB + DESC
E.MATCH, E.CLIPFN, E.UNITFN, E.BUILDER, E.DMM_OPEN = (AVB + x for x in (0x2360AC, 0x1A2670, 0x22DFA4, 0x231DB0, 0x23DB64))
E.LOGF, E.LOGH, E.MEMSET, E.MEMCPY = (AVB + x for x in (0x28DC3C, 0x28DBFC, 0x28E170, 0x28E158))
V.DESC, V.NDESC, V.UNIT_TABLE, V.FPS_TABLE = AVB + DESC, NDESC, AVB + UNIT_TABLE, AVB + FPS_TABLE
D = ROOT / "modding" / "designs"
# The request's +0x88 word. The A7 IV run puts 2 there; the FX2's matcher has a branch the A7 IV's lacks: with +0x88 = 2 or 5 and the list item
# +0x8c = 0xa it skips every descriptor whose +0x24 is 1 (all the 4K descriptors of these formats; 0x23628c-0x2362ac), where the A7 IV skips them
# only for 5 (0x21b970). With 3 the FX2 takes the A7 IV's branch: the same comparisons, +0x24 not read. Which value a recording sends is not traced.
MODE = 3


# 2026-11-27: run_ogfile_emu.AvCam takes a body's function addresses as its `fn` argument (since 2026-11-25; before that it read the module
# globals set above, which it no longer does): the same addresses, given here
FX2_FN = {"DESC": AVB + DESC, "MATCH": E.MATCH, "CLIPFN": E.CLIPFN, "UNITFN": E.UNITFN, "BUILDER": E.BUILDER, "DMM_OPEN": E.DMM_OPEN,
          "LOGF": E.LOGF, "LOGH": E.LOGH, "MEMSET": E.MEMSET, "MEMCPY": E.MEMCPY}


class Cam(E.AvCam):
    mode = MODE

    def __init__(self, img, fn=None):
        super().__init__(img, dict(FX2_FN, **(fn or {})))

    def request(self, d, w, h):
        req = super().request(d, w, h)
        struct.pack_into("<I", req, 0x88, self.mode)
        return req


def clip(cam, w, h):
    """The FX2's clip-format matcher: x0 an object whose +8 leads to a record read only on the failure path, x1 the request."""
    E_CTX, E_REQ = E.CTX, E.REQ
    cam.uc.mem_write(E_CTX, struct.pack("<QQ", 0, E_CTX + 0x40) + bytes(0x30) + struct.pack("<Q", E_CTX + 0x80) + bytes(0x40))
    req = bytearray(0x100)
    struct.pack_into("<HH", req, 0x68, w, h)
    req[0x81] = 1
    cam.uc.mem_write(E_REQ, bytes(req))
    return cam.call(E.CLIPFN, E_CTX, E_REQ) & 0xFFFFFFFF


def avcam_checks(name, av):
    design = json.loads((D / f"{name}.json").read_text(encoding="utf8"))
    assert design["build"] == BUILD
    changed = bytearray(av)
    for off, new_bytes in E.pokes(D / f"{name}_pokes_avcam.txt"):
        changed[off:off + len(new_bytes)] = new_bytes
    changed = bytes(changed)
    s, c = Cam(av), Cam(changed)
    res = {"design": name, "format": design["format"], "request_word_0x88": MODE}
    k0 = design["descriptors"][0]["descriptor"]
    s.mode = 2
    res["request_word_0x88_is_2"] = {"descriptor": k0, "stock_3840x2160": s.select(s.desc(k0), 3840, 2160),
                                     "note": "the A7 IV run's value: the FX2's matcher then refuses the stock descriptor for its stock size too "
                                             "(descriptor +0x24 = %d), so the value is a property of the request, not of the design" % struct.unpack_from("<I", av, DESC + k0 * 0x90 + 0x24)[0]}
    s.mode = MODE
    sel, ok = [], True
    for p in design["descriptors"]:
        k = p["descriptor"]
        d = s.desc(k)
        row = {"descriptor": k, "format": p["format"], "rate": p["rate"], "quality_class": p["quality_class"], "key": d["key"],
               "stock_3840x2160": s.select(d, 3840, 2160), "stock_3840x2560": s.select(d, 3840, 2560),
               "changed_3840x2560": c.select(d, 3840, 2560), "changed_3840x2160": c.select(d, 3840, 2160)}
        row["as_designed"] = (row["stock_3840x2160"] == k and row["stock_3840x2560"] is None and row["changed_3840x2560"] == k and row["changed_3840x2160"] is None)
        ok &= row["as_designed"]
        sel.append(row)
    untouched = []
    changed_set = {p["descriptor"] for p in design["descriptors"]}
    codecs = {s.desc(k)["codec"] for k in changed_set}
    for k in range(NDESC):
        d = s.desc(k)
        if (d["w"], d["h"]) != (3840, 2160) or d["infr"] or k in changed_set:
            continue
        if d["codec"] in codecs and d["codfr"] in (0, 1, 2):          # the same formats at the other frame rates (29.97p, 50p, 59.94p ...)
            a, b = s.select(d, 3840, 2160), c.select(d, 3840, 2160)
            untouched.append({"descriptor": k, "codec": hex(d["codec"]), "coding_rate_code": d["codfr"], "stock": a, "changed": b,
                              "changed_3840x2560": c.select(d, 3840, 2560)})
    res["encoder_selection"] = {"every_changed_descriptor_as_designed": ok, "changed": sel, "untouched_checked": len(untouched),
                                "untouched_same_answer": all(u["stock"] == u["changed"] for u in untouched),
                                "untouched_refuse_2560": all(u["changed_3840x2560"] is None for u in untouched), "untouched_examples": untouched[:6]}
    res["clip_code"] = [{"raster": [w, h], "stock": clip(s, w, h), "changed": clip(c, w, h)} for w, h in ((3840, 2560), (3840, 2160), (8192, 4320), (1920, 1080))]
    firsts = {}
    for q in design["descriptors"]:
        firsts.setdefault(s.desc(q["descriptor"])["codec"], q["descriptor"])
    res["memory_class_by_codec"] = {hex(cd): {"descriptor": k,
                                              "request_3840x2560": {"stock": s.unit_ids(s.desc(k), 3840, 2560), "changed": c.unit_ids(s.desc(k), 3840, 2560)},
                                              "request_3840x2160": {"stock": s.unit_ids(s.desc(k), 3840, 2160), "changed": c.unit_ids(s.desc(k), 3840, 2160)}}
                                    for cd, k in sorted(firsts.items())}
    # the codec's memory calculation (vcd_firmware_imola2.bin is the A7 IV's file) against the FX2's main-processor blocks
    assert locate_file.locate(BUILD, "vcd_firmware_imola2.bin").read_bytes() == locate_file.locate("a7iv_602", "vcd_firmware_imola2.bin").read_bytes()
    fw = V.Firmware()
    table = [struct.unpack_from("<4I", changed, UNIT_TABLE + 0x10 * k) for k in range(4)]
    cfg = V.parse_dmmcfg.Config(V.parse_dmmcfg.find_file(BUILD, "setting"), BUILD)

    def size_of(i):
        units = [u for kk in cfg.id_json(i).get("keys", []) for u in kk["units"]] if i else []
        return max(u["size_bytes"] for u in units) if units else None

    have = [size_of(i) for i in table[3]]
    mem = []
    for dd in V.descriptors(changed):
        if dd["index"] not in changed_set:
            continue
        need = fw.need(dd)
        t, why = V.unit_type(dd)
        mem.append({"descriptor": dd["index"], "vsize": dd["h"], "unit_type": t, "need": {k: need[k] for k in ("cd", "ld", "multi")},
                    "fits": need["cd"] <= have[0] and need["ld"] <= have[1] and need["multi"] <= have[2], "firmware_asserts": need["asserts"]})
    res["codec_memory"] = {"blocks_of_row_3_after_the_change": {"ids": [hex(i) for i in table[3]], "bytes": have},
                           "every_changed_descriptor_fits": bool(mem) and all(m["fits"] and m["unit_type"] == 3 and m["vsize"] == 2560 for m in mem),
                           "largest_need": {k: max(m["need"][k] for m in mem) for k in ("cd", "ld", "multi")}, "rows": mem}
    prof = {}
    for base, n in PROFILES:
        for k in range(n):
            prof[struct.unpack_from("<I", av, base + k * 0x100 + 0x20)[0]] = base + k * 0x100
    starts, good = [], True
    for p in design["descriptors"]:
        d = s.desc(p["descriptor"])
        o = prof[d["key"]]
        ten = d["bitl"] == 1
        try:
            a, seq_a = s.start_block(av[o:o + 0x100], d, 3840, 2160, ten)
            b, seq_b = c.start_block(changed[o:o + 0x100], d, 3840, 2560, ten)
        except RuntimeError as e:
            starts.append({"descriptor": p["descriptor"], "error": str(e)})
            good = False
            continue
        diff = [i for i in range(0x1C0) if seq_a[i] != seq_b[i]]
        runs = []
        for i in diff:
            if runs and i == runs[-1][1] + 1:
                runs[-1][1] = i
            else:
                runs.append([i, i])
        starts.append({"descriptor": p["descriptor"], "key": d["key"], "stock_2160": a, "changed_2560": b,
                       "sequence_block_differs_at": [{"offset": hex(x), "bytes": y - x + 1, "stock": seq_a[x:y + 1].hex(), "changed": seq_b[x:y + 1].hex()} for x, y in runs]})
        good &= a["returned"] == 1 and not a["errors_logged"] and a["crop_size"] == [3840, 2160]
        good &= b["returned"] == 1 and not b["errors_logged"] and b["crop_size"] == [3840, 2560]
    res["start_block"] = {"every_changed_profile_accepted": good, "rows": starts}
    return res


def libmpr_checks(name, lm):
    design = json.loads((D / f"{name}.json").read_text(encoding="utf8"))
    pk = E.pokes(D / f"{name}_pokes_libmpr.txt")
    changed = bytearray(lm)
    for off, new_bytes in pk:
        changed[off:off + len(new_bytes)] = new_bytes
    changed = bytes(changed)
    rows = {}
    for comb in (0, 2, 5, 7, 9, 12):
        rows[comb] = {"stock": list(struct.unpack_from("<HH", lm, COMB + 0x18 * comb + 4)), "changed": list(struct.unpack_from("<HH", changed, COMB + 0x18 * comb + 4))}
    mp4 = {}
    libs = {"stock": emu_mp4_meta.Lib(lm, BUILD), "changed": emu_mp4_meta.Lib(changed, BUILD)}
    for comb in (0, 2, 5, 7):
        for rate_code in (0, 2):
            got = {}
            for k, lib in libs.items():
                r, cfg = lib.config(comb, rate_code, 0x20)
                got[k] = [struct.unpack_from("<H", cfg, 0x2A)[0], struct.unpack_from("<H", cfg, 0x28)[0]]
            mp4[f"comb {comb} rate code {rate_code}"] = got
    want_h = 2560 if any(p["kind"] == "L4-mp4size" for p in design["patches"]) else 2160
    ok = (all(rows[c]["stock"] == [3840, 2160] and rows[c]["changed"] == [3840, 2560] for c in (0, 2, 5, 7))
          and all(rows[c]["stock"] == rows[c]["changed"] for c in (9, 12))
          and all(v["stock"] == [3840, 2160] and v["changed"] == [3840, want_h] for v in mp4.values()))
    return {"encoder_request_raster_by_comb": {str(k): v for k, v in rows.items()}, "mp4_track_config_by_comb": mp4,
            "mp4_height_expected": want_h, "as_designed": ok}


def main():
    av = locate_file.locate(BUILD, "av-cam.bin").read_bytes()
    lm = locate_file.locate(BUILD, "libmpr.so").read_bytes()
    out = {"about": "FX2 1.01: function-level emulation of ogfile2560_hs_s_fx2_v1 and _v2, stock against changed, in the FX2's own av-cam.bin and libmpr.so "
                    "(build/run_ogfile_emu_fx2.py, the A7 IV's run_ogfile_emu.py pointed at the FX2's functions). The requests are built from the descriptors' "
                    "own fields, not from a traced caller. Nothing was run on a camera.", "designs": []}
    for name in ("ogfile2560_hs_s_fx2_v1", "ogfile2560_hs_s_fx2_v2"):
        r = avcam_checks(name, av)
        r["libmpr"] = libmpr_checks(name, lm)
        out["designs"].append(r)
    dst = ROOT / "evidence/fx2/ogfile2560_emu_fx2.json"
    dst.parent.mkdir(exist_ok=True)
    dst.write_text(json.dumps(out, indent=1) + "\n", encoding="utf8", newline="\n")
    for r in out["designs"]:
        e = r["encoder_selection"]
        print("==", r["design"])
        print("   matcher: changed descriptors as designed:", e["every_changed_descriptor_as_designed"], "| untouched checked:", e["untouched_checked"],
              "same answer:", e["untouched_same_answer"], "refuse 2560:", e["untouched_refuse_2560"])
        for row in e["changed"]:
            if not row["as_designed"]:
                print("      NOT as designed:", row)
        print("   clip code:", r["clip_code"])
        print("   memory class:", json.dumps({k: {q: v[q] for q in ("request_3840x2560",)} for k, v in r["memory_class_by_codec"].items()}))
        m = r["codec_memory"]
        print("   codec memory: blocks", m["blocks_of_row_3_after_the_change"], "fits:", m["every_changed_descriptor_fits"], "largest need:", m["largest_need"])
        print("   start block: accepted:", r["start_block"]["every_changed_profile_accepted"], [x.get("error") for x in r["start_block"]["rows"] if "error" in x][:2])
        print("   libmpr:", "as designed:", r["libmpr"]["as_designed"], r["libmpr"]["mp4_track_config_by_comb"])
        print("   request word +0x88 = 2:", r["request_word_0x88_is_2"])
    print("wrote", dst)
    bad = []
    for r in out["designs"]:
        e, mc = r["encoder_selection"], r["memory_class_by_codec"]
        checks = {"matcher": e["every_changed_descriptor_as_designed"] and e["untouched_same_answer"] and e["untouched_refuse_2560"] and e["untouched_checked"] > 0,
                  "clip": [x["changed"] for x in r["clip_code"]] == [23, 23, 0, 26] and [x["stock"] for x in r["clip_code"]] == [0, 23, 3, 26],
                  "memory class": all(v["request_3840x2560"]["changed"]["memory_ids_asked"][:4] == ["0x486", "0x474", "0x47a", "0x477"]
                                      and v["request_3840x2160"]["changed"] == v["request_3840x2160"]["stock"] for v in mc.values()),
                  "codec memory": r["codec_memory"]["every_changed_descriptor_fits"], "start block": r["start_block"]["every_changed_profile_accepted"],
                  "libmpr": r["libmpr"]["as_designed"]}
        bad += [f"{r['design']}: {k}" for k, v in checks.items() if not v]
    print("ALL CHECKS PASS" if not bad else "FAILED: " + "; ".join(bad))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
