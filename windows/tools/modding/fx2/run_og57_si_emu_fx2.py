"""FX2 1.01: function-level emulation of the 5760x3840 and XAVC S-I encoder-side designs (2026-11-27, the FX2's 5.7K port, GitHub issue 7),
stock against changed, in the FX2's own av-cam.bin and libmpr.so. The changes are applied in emulated memory only.

  ogfile57r300m1_fx2_v4 / _v3   (build/build_og57.py --build fx2_101 --rate300 --m1all [--meta]) on their own, as build/run_og57_emu.py
                                checks the A7 IV's ogfile57 designs
  ogfilesi2560_fx2_v1           (build/build_ogfile_si.py --build fx2_101) on top of ogfile2560_hs_s_fx2_v2, and
  ogfilesi57_fx2_v1             on top of ogfile57r300m1_fx2_v4, as build/run_ogfile_si_emu.py checks the A7 IV's S-I designs on their states

The FX2's functions are those build/run_ogfile_emu_fx2.py found and points the A7 IV harness (build/run_ogfile_emu.py) at, on import:
  av-cam.bin  descriptor matcher 0x2360ac (request word +0x88 = 3: see run_ogfile_emu_fx2.MODE), clip-format matcher 0x1a2670, memory-class
              function 0x22dfa4, start-block builder 0x231db0; the codec firmware's memory calculation (build/emu_vcd_chmem.py, the codec file is
              the A7 IV's byte for byte) against the FX2's main-processor blocks (its DmmCfg.bin, setting stream)
  libmpr.so   g_videoParamComb 0x2cdc58 (the encoder request's raster), the MP4 writer's track config, stsd entry and PROF entry
              (build/emu_mp4_meta.py's Lib with the FX2's functions)
The edit-list site of the 5.7K designs is emulated by build/emu_elst_site_v3.py --build fx2_101; the MP4 size sites for every request by
build/emu_mp4_meta.py --build fx2_101 --both.

Run with the Python that has Unicorn:  C:\\Python313\\python.exe -B build/run_og57_si_emu_fx2.py     writes evidence/fx2/og57_si_emu_fx2.json
Nothing was run on a camera.
"""
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "build"))
import emu_mp4_meta  # noqa: E402
import locate_file  # noqa: E402
import run_ogfile_emu_fx2 as F  # noqa: E402  (importing it points the A7 IV harness at the FX2's functions)

E, V = F.E, F.V
BUILD, D, DESC, NDESC, UNIT_TABLE, COMB = F.BUILD, F.D, F.DESC, F.NDESC, F.UNIT_TABLE, F.COMB
W0, H0 = 3840, 2160
DEST = ROOT / "evidence/fx2/og57_si_emu_fx2.json"


def design(name):
    d = json.loads((D / f"{name}.json").read_text(encoding="utf8"))
    assert d["build"] == BUILD, name
    return d


def apply(data, binary, *names):
    out = bytearray(data)
    for n in names:
        for off, nb in E.pokes(D / f"{n}_pokes_{binary}.txt"):
            out[off:off + len(nb)] = nb
    return bytes(out)


def profiles(av):
    prof = {}
    for base, n in F.PROFILES:
        for k in range(n):
            prof[struct.unpack_from("<I", av, base + k * 0x100 + 0x20)[0]] = base + k * 0x100
    return prof


def block_sizes():
    cfg = V.parse_dmmcfg.Config(V.parse_dmmcfg.find_file(BUILD, "setting"), BUILD)

    def size_of(i):
        units = [u for kk in cfg.id_json(i).get("keys", []) for u in kk["units"]] if i else []
        return max(u["size_bytes"] for u in units) if units else None
    return size_of


def runs_of(a, b):
    out = []
    for i in (i for i in range(len(a)) if a[i] != b[i]):
        if out and i == out[-1][1] + 1:
            out[-1][1] = i
        else:
            out.append([i, i])
    return [{"offset": hex(x), "bytes": y - x + 1, "first": a[x:y + 1].hex(), "second": b[x:y + 1].hex()} for x, y in out]


def mp4_rows(libs, combs, rate_codes=(0, 2)):
    """Track config, stsd entry and PROF entry for each comb, rate code and bit-rate index the stock writer accepts, per library."""
    rows = []
    for comb in combs:
        for rate_code in rate_codes:
            for rate_index in range(2, 0x36):
                row = {"comb": comb, "rate_code": rate_code, "rate_index": rate_index}
                for k, lib in libs.items():
                    r, cfg = lib.config(comb, rate_code, rate_index)
                    rs, sz = lib.stsd(cfg)
                    rp, pf = lib.prof(cfg)
                    row[k] = {"config": [struct.unpack_from("<H", cfg, 0x2A)[0], struct.unpack_from("<H", cfg, 0x28)[0]], "stsd": [rs, list(sz)], "prof": [rp, pf]}
                if row["stock"]["stsd"][0] == 0 and row["stock"]["prof"][0] == 0:
                    rows.append(row)
    return rows


def check_57(name, av, lm, size_of):
    """A 5760x3840 HS/S design on its own (the A7 IV's run_og57_emu.py checks, on the FX2)."""
    dz = design(name)
    W1, H1 = dz["raster"]
    big = f"{W1}x{H1}"
    res, checks = {"design": name, "format": dz["format"], "request_word_0x88": F.MODE}, {}
    # ---- libmpr: the encoder request's raster, and the MP4 track config / stsd / PROF of the four formats
    lmc = apply(lm, "libmpr", name)
    rows = sorted({int(re.search(r"row (\d+)", p["note"]).group(1)) for p in dz["patches"] if p["kind"] == "L1-comb"})
    others = [r for r in (4, 9, 12, 13) if r not in rows]
    comb = {r: {"stock": list(struct.unpack_from("<HH", lm, COMB + 0x18 * r + 4)), "changed": list(struct.unpack_from("<HH", lmc, COMB + 0x18 * r + 4))}
            for r in rows + others}
    checks["encoder request raster: rows %s 3840x2160 -> %s, rows %s unchanged" % (rows, big, others)] = (
        rows == [0, 2, 5, 7] and all(comb[r]["stock"] == [W0, H0] and comb[r]["changed"] == [W1, H1] for r in rows)
        and all(comb[r]["stock"] == comb[r]["changed"] for r in others))
    meta = any(p["kind"] == "L4-mp4size" for p in dz["patches"])
    want = [W1, H1] if meta else [W0, H0]
    mrows = mp4_rows({"stock": emu_mp4_meta.Lib(lm, BUILD), "changed": emu_mp4_meta.Lib(lmc, BUILD)}, (0, 2, 5, 7))
    checks["MP4 track config, stsd and PROF of every request the stock writer accepts: %s with the stock profile id%s" % (
        "x".join(map(str, want)), "" if meta else " (no header sites: the headers keep 3840x2160)")] = bool(mrows) and all(
        r["changed"]["config"] == want and r["changed"]["stsd"] == [0, want] and r["changed"]["prof"][0] == 0
        and r["changed"]["prof"][1]["profile_id"] == r["stock"]["prof"][1]["profile_id"] for r in mrows)
    res["libmpr"] = {"comb_rows": {str(k): v for k, v in comb.items()}, "mp4_requests_checked": len(mrows),
                     "mp4_example": {k: mrows[0][k] for k in ("comb", "rate_code", "rate_index", "stock", "changed")} if mrows else None}
    # ---- av-cam: the matcher
    avc = apply(av, "avcam", name)
    s, c = F.Cam(av), F.Cam(avc)
    sel, good = [], True
    for p in dz["descriptors"]:
        k = p["descriptor"]
        d = s.desc(k)
        row = {"descriptor": k, "format": p["format"], "rate": p["rate"], "quality_class": p["quality_class"], "key": d["key"],
               "stock_3840x2160": s.select(d, W0, H0), f"stock_{big}": s.select(d, W1, H1), f"changed_{big}": c.select(d, W1, H1), "changed_3840x2160": c.select(d, W0, H0)}
        row["as_designed"] = row["stock_3840x2160"] == k and row[f"stock_{big}"] is None and row[f"changed_{big}"] == k and row["changed_3840x2160"] is None
        good &= row["as_designed"]
        sel.append(row)
    checks["matcher: each changed descriptor is found for %s, no longer for 3840x2160" % big] = good
    changed = {p["descriptor"] for p in dz["descriptors"]}
    untouched = []
    for k in range(NDESC):
        d = s.desc(k)
        if d["infr"] or k in changed or d["codec"] not in (4, 0xE, 0x18):
            continue
        if (d["w"], d["h"]) == (W0, H0) or d["w"] >= W1:
            untouched.append({"descriptor": k, "codec": hex(d["codec"]), "raster": [d["w"], d["h"]], "coding_rate_code": d["codfr"],
                              "stock": s.select(d, d["w"], d["h"]), "changed": c.select(d, d["w"], d["h"]), f"changed_{big}": c.select(d, W1, H1)})
    checks["matcher: every other 3840x2160 / 5760-wide AVC, HEVC, S-I request: the same answer; none finds a descriptor at %s" % big] = (
        bool(untouched) and all(u["stock"] == u["changed"] for u in untouched) and all(u[f"changed_{big}"] is None for u in untouched))
    res["encoder_selection"] = {"changed": sel, "untouched_checked": len(untouched), "untouched_examples": untouched[:6]}
    s.mode = 2
    k0 = dz["descriptors"][0]["descriptor"]
    res["request_word_0x88_is_2"] = {"descriptor": k0, "stock_3840x2160": s.select(s.desc(k0), W0, H0),
                                     "note": "with +0x88 = 2 the FX2's matcher refuses even the stock descriptor at its stock size (run_ogfile_emu_fx2.MODE)"}
    s.mode = F.MODE
    # ---- clip-format code
    clips = [{"raster": [w, h], "stock": F.clip(s, w, h), "changed": F.clip(c, w, h)} for w, h in ((W1, H1), (W0, H0), (8192, 4320), (1920, 1080))]
    res["clip_code"] = clips
    checks["clip-format code: %s 0 -> 23 (the 4K code), 3840x2160 23 kept, 8192x4320 3 -> 0 (row 1 rewritten), 1920x1080 kept" % big] = (
        [x["stock"] for x in clips] == [0, 23, 3, 26] and [x["changed"] for x in clips] == [23, 23, 0, 26])
    # ---- memory: which ids the memory function asks for, and the codec's own calculation against row 3
    table = [struct.unpack_from("<4I", avc, UNIT_TABLE + 0x10 * k) for k in range(5)]
    r3 = table[3]
    firsts = {}
    for q in dz["descriptors"]:
        firsts.setdefault(s.desc(q["descriptor"])["codec"], q["descriptor"])
    mem_ids = {}
    ok_ids = True
    for cd, k in sorted(firsts.items()):
        d = s.desc(k)
        mem_ids[hex(cd)] = {"descriptor": k, f"request_{big}": {"stock": s.unit_ids(d, W1, H1), "changed": c.unit_ids(d, W1, H1)},
                            "request_3840x2160": {"stock": s.unit_ids(d, W0, H0), "changed": c.unit_ids(d, W0, H0)}}
        ch = mem_ids[hex(cd)][f"request_{big}"]["changed"]
        ok_ids &= (ch["memory_ids_asked"][:4] == [hex(r3[0]), hex(r3[1]), hex(r3[3]), hex(r3[2])] and not ch["errors_logged"]
                   and mem_ids[hex(cd)]["request_3840x2160"]["changed"] == mem_ids[hex(cd)]["request_3840x2160"]["stock"])
    checks["memory function: a %s request asks row 3 (CD, LD, ES, multi = %s); 3840x2160 asks as stock" % (big, [hex(x) for x in (r3[0], r3[1], r3[3], r3[2])])] = ok_ids
    res["memory_ids_by_codec"] = mem_ids
    fw = V.Firmware()
    have = [size_of(i) for i in r3]
    mem = []
    for dd in V.descriptors(avc):
        if dd["index"] not in changed:
            continue
        need = fw.need(dd)
        t, why = V.unit_type(dd)
        mem.append({"descriptor": dd["index"], "raster": [dd["w"], dd["h"]], "use_core": dd["use_core"], "unit_type": t,
                    "need": {k: need[k] for k in ("cd", "ld", "multi")}, "firmware_asserts": need["asserts"],
                    "fits": need["cd"] <= have[0] and need["ld"] <= have[1] and need["multi"] <= have[2]})
    checks["codec memory: every changed descriptor (two cores, unit type 3) fits the blocks of row 3 %s, no firmware assert" % have] = bool(mem) and all(
        m["fits"] and m["unit_type"] == 3 and m["raster"] == [W1, H1] and m["use_core"] == 2 and not m["firmware_asserts"] for m in mem)
    r2 = table[2]
    res["codec_memory"] = {"row_3": {"ids": [hex(i) for i in r3], "bytes": have}, "largest_need": {k: max(m["need"][k] for m in mem) for k in ("cd", "ld", "multi")},
                           "in_the_stock_order_of_row_2_would_fit": all(m["need"]["cd"] <= size_of(r2[0]) and m["need"]["ld"] <= size_of(r2[1])
                                                                        and m["need"]["multi"] <= size_of(r2[2]) for m in mem), "rows": mem}
    # ---- the start-block builder
    prof = profiles(av)
    starts, sgood = [], True
    for p in dz["descriptors"]:
        d = s.desc(p["descriptor"])
        o, ten = prof[d["key"]], d["bitl"] == 1
        a, seq_a = s.start_block(av[o:o + 0x100], d, W0, H0, ten)
        b, seq_b = c.start_block(avc[o:o + 0x100], d, W1, H1, ten)
        br = 32 if d["codec"] == 0xE else 16
        first = struct.unpack_from("<H", seq_b, 0xC)[0]
        sgood &= (a["returned"] == 1 and not a["errors_logged"] and b["returned"] == 1 and not b["errors_logged"] and b["crop_size"] == [W1, H1]
                  and first == (-(-H1 // br) // 2) * br)
        starts.append({"descriptor": p["descriptor"], "key": d["key"], "stock_3840x2160": a, f"changed_{big}": b, "rows_for_first_core_in_the_block": first,
                       "sequence_block_differs_at": runs_of(seq_a, seq_b)})
    checks["start-block builder: every changed profile accepted at %s (crop, rows for the first core = half the picture in coding-block rows)" % big] = sgood
    res["start_block"] = starts
    comp = []
    for ref in dz["rule_checked_against_sonys_own_two_core_profiles"]["hs"]:
        k_ref, k_4k = int(re.search(r"#(\d+)", ref["reference"]).group(1)), int(re.search(r"#(\d+)", ref["against"]).group(1))
        dr, d4 = s.desc(k_ref), s.desc(k_4k)
        a, seq_a = s.start_block(av[prof[dr["key"]]:prof[dr["key"]] + 0x100], dr, dr["w"], dr["h"], dr["bitl"] == 1)
        b, seq_b = c.start_block(avc[prof[d4["key"]]:prof[d4["key"]] + 0x100], d4, W1, H1, d4["bitl"] == 1)
        comp.append({"sonys": "descriptor #%d, %dx%d" % (k_ref, dr["w"], dr["h"]), "designs": "descriptor #%d at %s" % (k_4k, big), "sonys_result": a,
                     "designs_result": b, "sequence_block_differs_at": runs_of(seq_a, seq_b)})
    res["against_sonys_5760x3240_block"] = comp
    res["checks"] = checks
    return res


def check_si(name, base, av, lm, size_of):
    """An S-I design on top of the HS/S design it goes with (the A7 IV's run_ogfile_si_emu.py checks, on the FX2)."""
    dz, bz = design(name), design(base)
    W1, H1 = dz["raster"]
    big = f"{W1}x{H1}"
    assert dz["apply_after"] == base and bz["raster"] == [W1, H1]
    res, checks = {"design": name, "on_top_of": base, "request_word_0x88": F.MODE}, {}
    # ---- libmpr: comb row 9 and the MP4 headers of an S-I file in the state
    lst, lboth = apply(lm, "libmpr", base), apply(lm, "libmpr", base, name)
    r9 = {k: list(struct.unpack_from("<HH", x, COMB + 0x18 * 9 + 4)) for k, x in (("stock", lm), ("state", lst), ("state_and_step", lboth))}
    others = {r: (list(struct.unpack_from("<HH", lst, COMB + 0x18 * r + 4)), list(struct.unpack_from("<HH", lboth, COMB + 0x18 * r + 4))) for r in (0, 2, 4, 5, 7, 12, 13)}
    checks["comb row 9 (XAVC S-I 4K): 3840x2160 in stock and in the state, %s with the step; every other row as the state has it" % big] = (
        r9["stock"] == r9["state"] == [W0, H0] and r9["state_and_step"] == [W1, H1] and all(a == b for a, b in others.values()))
    meta = any(p["kind"] == "L4-mp4size" for p in bz["patches"])
    want = [W1, H1] if meta else [W0, H0]
    mrows = mp4_rows({"stock": emu_mp4_meta.Lib(lm, BUILD), "state": emu_mp4_meta.Lib(lst, BUILD), "state_and_step": emu_mp4_meta.Lib(lboth, BUILD)}, (9,))
    checks["MP4 headers of an S-I file (comb 9) in the state: %s, stsd and PROF built with the stock profile id" % "x".join(map(str, want))] = bool(mrows) and all(
        r[k]["config"] == want and r[k]["stsd"] == [0, want] and r[k]["prof"][0] == 0 and r[k]["prof"][1]["profile_id"] == r["stock"]["prof"][1]["profile_id"]
        for r in mrows for k in ("state", "state_and_step"))
    res["libmpr"] = {"comb_row_9": r9, "mp4_comb_9_requests_checked": len(mrows),
                     "mp4_example": {k: mrows[0][k] for k in ("rate_code", "rate_index", "stock", "state_and_step")} if mrows else None}
    # ---- av-cam
    ast, aboth = apply(av, "avcam", base), apply(av, "avcam", base, name)
    s, t, c = F.Cam(av), F.Cam(ast), F.Cam(aboth)
    sel, good = [], True
    for p in dz["descriptors"]:
        k = p["descriptor"]
        d = s.desc(k)
        row = {"descriptor": k, "rate": p["rate"], "quality_class": p["quality_class"], "key": d["key"], "twin": p["twin_never_reached"],
               "stock_3840x2160": s.select(d, W0, H0), f"state_{big}": t.select(d, W1, H1), f"state_and_step_{big}": c.select(d, W1, H1),
               "state_and_step_3840x2160": c.select(d, W0, H0)}
        row["as_designed"] = (row["stock_3840x2160"] == k and row[f"state_{big}"] is None and row[f"state_and_step_{big}"] == k
                              and row["state_and_step_3840x2160"] == p["twin_never_reached"])
        good &= row["as_designed"]
        sel.append(row)
    checks["matcher: each changed S-I descriptor is found for %s only with the step (in the state alone: none, the issue-7 symptom); at 3840x2160 its "
           "205xxx twin answers" % big] = good
    changed = {p["descriptor"] for p in dz["descriptors"]}
    twins = {p["twin_never_reached"] for p in dz["descriptors"]}
    same, n, moved = True, 0, []
    for k in range(NDESC):
        d = s.desc(k)
        if k in changed or d["codec"] not in (4, 0xE, 0x18) or d["w"] < 1920:
            continue
        for w, h in ((d["w"], d["h"]), (W1, H1)):
            a, b = t.select(d, w, h), c.select(d, w, h)
            n += 1
            if a == b:
                continue
            moved.append({"built_from": k, "key": d["key"], "raster": [w, h], "state": a, "state_and_step": b})
            same &= (k in twins and (w, h) == (W0, H0) and a in changed and b == k) or ((w, h) == (W1, H1) and d["codec"] == 0x18 and a is None and b in changed)
    checks["matcher: every other AVC/HEVC/S-I request gives the same answer with and without the step, except requests with a changed row's own fields"] = same
    checks["matcher: the state's own HS/S descriptors are still found at %s" % big] = all(c.select(s.desc(q["descriptor"]), W1, H1) == q["descriptor"] for q in bz["descriptors"])
    res["encoder_selection"] = {"changed": sel, "requests_compared": n, "answers_that_moved": moved}
    d0 = s.desc(dz["descriptors"][0]["descriptor"])
    res["memory_ids"] = {"stock_3840x2160": s.unit_ids(d0, W0, H0), f"state_and_step_{big}": c.unit_ids(d0, W1, H1)}
    table = [struct.unpack_from("<4I", aboth, UNIT_TABLE + 0x10 * k) for k in range(10)]
    fw = V.Firmware()
    mem, fit = [], True
    for dd in V.descriptors(aboth):
        if dd["index"] not in changed:
            continue
        need = fw.need(dd)
        ut, why = V.unit_type(dd)
        have = [size_of(i) for i in table[ut]] if ut is not None else [None] * 4
        f = ut == 4 and all(need[x] == 0 or (hv is not None and need[x] <= hv) for x, hv in zip(("cd", "ld", "multi"), have)) and not need["asserts"]
        fit &= f and [dd["w"], dd["h"]] == [W1, H1] and dd["use_core"] == 2
        mem.append({"descriptor": dd["index"], "raster": [dd["w"], dd["h"]], "fps": dd["fps"], "unit_type": ut, "class": why, "row_ids": [hex(i) for i in table[ut]],
                    "row_bytes": have, "need": {x: need[x] for x in ("cd", "ld", "multi")}, "fits": f, "firmware_asserts": need["asserts"]})
    checks["codec memory: the need fits the blocks of unit type 4 (the stock 4K row), no firmware assert"] = fit
    asked, asked0 = res["memory_ids"][f"state_and_step_{big}"]["memory_ids_asked"], res["memory_ids"]["stock_3840x2160"]["memory_ids_asked"]
    r4, r9_ = table[4], table[9]
    checks["memory function: stock asks unit type 9's row, the new size type 4's (CD, LD, ES, multi), the rest the same"] = (
        asked0[:4] == [hex(r9_[0]), hex(r9_[1]), hex(r9_[3]), hex(r9_[2])] and asked[:4] == [hex(r4[0]), hex(r4[1]), hex(r4[3]), hex(r4[2])]
        and asked[4:] == asked0[4:] and not res["memory_ids"][f"state_and_step_{big}"]["errors_logged"])
    res["codec_memory"] = mem
    prof = profiles(av)
    starts, sgood = [], True
    rf = (-(-H1 // 16) // 2) * 16
    for p in dz["descriptors"]:
        d = s.desc(p["descriptor"])
        o = prof[d["key"]]
        a, seq_a = s.start_block(av[o:o + 0x100], d, W0, H0, True)
        b, seq_b = c.start_block(aboth[o:o + 0x100], d, W1, H1, True)
        first = struct.unpack_from("<H", seq_b, 0xC)[0]
        sgood &= b["returned"] == 1 and not b["errors_logged"] and b["crop_size"] == [W1, H1] and first == rf and a["returned"] == 1
        starts.append({"descriptor": p["descriptor"], "key": d["key"], "stock_3840x2160": a, f"changed_{big}": b, "rows_for_first_core_in_the_block": first,
                       "stock_rows_for_first_core": struct.unpack_from("<H", seq_a, 0xC)[0], "sequence_block_differs_at": runs_of(seq_a, seq_b)})
    checks["start-block builder: every changed profile accepted at %s (crop, rows for the first core %d)" % (big, rf)] = sgood
    res["start_block"] = starts
    res["clip_code"] = {big: {"stock": F.clip(s, W1, H1), "state": F.clip(t, W1, H1), "state_and_step": F.clip(c, W1, H1)},
                        "3840x2160": {"stock": F.clip(s, W0, H0), "state_and_step": F.clip(c, W0, H0)}}
    checks["clip-format code of %s is the 4K code 23 (from the state's own step)" % big] = res["clip_code"][big]["state_and_step"] == 23 == res["clip_code"]["3840x2160"]["stock"]
    res["checks"] = checks
    return res


def main():
    av = locate_file.locate(BUILD, "av-cam.bin").read_bytes()
    lm = locate_file.locate(BUILD, "libmpr.so").read_bytes()
    size_of = block_sizes()
    out = {"about": "FX2 1.01: function-level emulation of the 5760x3840 and XAVC S-I designs, stock against changed, in the FX2's own av-cam.bin and "
                    "libmpr.so (build/run_og57_si_emu_fx2.py). The requests are built from the descriptors' own fields, not from a traced caller. "
                    "Nothing was run on a camera.", "designs": []}
    for name in ("ogfile57r300m1_fx2_v4", "ogfile57r300m1_fx2_v3"):
        out["designs"].append(check_57(name, av, lm, size_of))
    for name, base in (("ogfilesi2560_fx2_v1", "ogfile2560_hs_s_fx2_v2"), ("ogfilesi57_fx2_v1", "ogfile57r300m1_fx2_v4")):
        out["designs"].append(check_si(name, base, av, lm, size_of))
    DEST.write_text(json.dumps(out, indent=1) + "\n", encoding="utf8", newline="\n")
    bad = []
    for r in out["designs"]:
        print("==", r["design"], ("on " + r["on_top_of"]) if "on_top_of" in r else "")
        for k, v in r["checks"].items():
            print("   %s  %s" % ("PASS" if v else "FAIL", k))
            if not v:
                bad.append(f"{r['design']}: {k}")
        if "codec_memory" in r and isinstance(r["codec_memory"], dict):
            print("   codec memory: row 3", r["codec_memory"]["row_3"], "largest need", r["codec_memory"]["largest_need"],
                  "| in row 2's order would fit:", r["codec_memory"]["in_the_stock_order_of_row_2_would_fit"])
        elif "codec_memory" in r:
            m = r["codec_memory"][0]
            print("   codec memory e.g. #%d: need %s of %s (type %s)" % (m["descriptor"], m["need"], m["row_bytes"], m["unit_type"]))
        if "request_word_0x88_is_2" in r:
            print("   request word +0x88 = 2:", r["request_word_0x88_is_2"]["stock_3840x2160"])
    print("wrote", DEST)
    print("ALL CHECKS PASS" if not bad else "FAILED: %d" % len(bad))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
