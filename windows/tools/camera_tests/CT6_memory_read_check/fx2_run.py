"""FX2 (ILME-FX2) firmware 1.01: run one of the two READ-ONLY helper libraries, or one write step, and save what it reports.
(Second kit, 2026-11-26: read helper fx2read_v2, the diagnostic ladder's step pair B5/B6, the dump decodes the memory manager's
workspace and the first pages of the crash snapshot image.)

  python fx2_run.py check --dry-run | --selftest
  python fx2_run.py dump  --dry-run | --selftest
  python fx2_run.py check --go --firmware-shown 1.01
  python fx2_run.py dump  --go --firmware-shown 1.01 [--clear-result SHA256]
  (write steps: through fx2_apply.py only)

  check   identity of the camera's software and what every site of the open-gate designs holds now: READY / NOT READY
          (the screen step's words are reported as well, not counted: it is optional)
  dump    the same, plus kernel and memory facts, the coprocessor's logs and some of its tables (sensor registers, stored
          records, the scaler's state, the memory manager's records, the display: panel type, fit word, frame tables, de-squeeze words)

Both read-only libraries only read. Each creates one file, its result, on the camera's RAM disk; this script fetches it. The
library is written to the camera's service partition, loaded once, and deleted again in the same session.

The FX2 counterpart of fx3_run.py (the FX3 kit, whose libraries ran on two FX3s), made from it on 2026-11-25 with this camera's
libraries, pins and result reader. The FX2 is the A7 IV's sensor on the A7C II's platform: its write steps are the A7 IV kit's
designs (which work on an A7 IV), ported. Nothing here can send a memory write unless a write step is named with --writes-memory.
"""
import argparse
import collections
import json
import platform
import re
import struct
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "CT1_usb_first_contact"))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "helper"))
sys.path.insert(0, str(HERE / "helper_fx2"))
import ct1_common as c  # noqa: E402
import ct6_level1_run as R  # noqa: E402

FIRMWARE, MODEL, BUILD = "1.01", "ILME-FX2", "fx2_101"
S3 = HERE / "helper_fx2"                       # this kit's folder (the name S3 is kept from s3_run.py)
PINS = {"check": ("libJit_fx2_check.so", "9dd469a2c4f6ca10f6c99f55df979aec432c1801d7b28b6056904bf340f8a39a"),      # fx2read_v2 (2026-11-26)
        "dump": ("libJit_fx2_dump.so", "1f51dc2a60c5f1c4cd540dd20ce628c52f0e2fdb528fcca7c94c4e9df8e7504c")}
# the first kit's read helper (fx2read_v1, 2026-11-25; ran on the first tester's FX2): check e3838945..., dump 5008ec3a...
LEVELS = {"check": 101, "dump": 102}              # numbers outside the A7 IV runner's own levels: none of its level-specific code runs
# THE WRITE STEPS. Each is one library built from the A7 IV helper's write code with this camera's tables (helper_fx2/build_fx2_write.sh).
# They change the running camera's memory until a cold boot. They are run through fx2_apply.py, never by a launcher of the read-only kit,
# and the libraries are not in the published kit unless it was published with --include-write.
WRITE_STEPS = {
    # The A7 IV kit's raw write buffer step (its level 13/14, dmmwb4688_v1): on the FX2, as on the A7 IV, the movie raw write buffer holds the
    # stock 3,958-row stage only (27,864,320 bytes); the full-height stage needs 4,688 rows. Must run first, from a cold boot with the camera on STILL.
    "L13": ("libJit_fx2_L13.so", "c99682a38445ad82974b94527da56f8ac8caec860a7c5b64ae3e6ba2992f1d4f", "apply the raw write buffer dmmwb4688_fx2_v1 (four memory-manager words: the movie raw write buffer holds 4,688 rows)"),
    "L14": ("libJit_fx2_L14.so", "15ec15af57c1590e0b832783c1939c9af41645cf0519a69f72282ad3cd99f991", "put back the raw write buffer dmmwb4688_fx2_v1"),
    "L5": ("libJit_fx2_L5.so", "724174438d0aaeae8c4ba1f611371cade6f7224c11c8b1441bd84e11107cafa9", "apply the sensor-side design ogsq_fx2_v1 (sensor cells, two records, the stored record; the A7 IV's working ogsq_v3)"),
    "L6": ("libJit_fx2_L6.so", "ae85bce19d3d0d73253c03a2fedbdc9e16f2097d5acf751430cf754049a78d5b", "put back the sensor-side design ogsq_fx2_v1"),
    # Second kit (2026-11-26), the diagnostic ladder's test 1: the same levels 5/6 with fhband_fx2_v1 = the A7 IV's fhband_v1 (F658, worked on the
    # A7 IV): the sensor in the same full-height mode as L5 (the 11 cells are L5's), but the picture records keep the stock 16:9 band, so the stage
    # has its stock height. Tells whether the FX2 runs the full-height read-out at all.
    "B5": ("libJit_fx2_B5.so", "23e19cbeac5e4378783abe75a9dde5547ac246912c90b6ec8ea77489a0defefc", "apply the test design fhband_fx2_v1 (full-height read-out with the stock 16:9 band: the A7 IV's fhband_v1)"),
    "B6": ("libJit_fx2_B6.so", "ea9c86281af81203176c9fd2b7d7511a7f85b2c5e6c71df2df0f2434a2eb1377", "put back the test design fhband_fx2_v1"),
    "L16": ("libJit_fx2_L16.so", "744dd7eb1b8f0cd79fde6f508b39988e9c92bc37ef1f10f30783ce2ae2ee441a", "apply the output size outsz2560_fx2_v1 (one word)"),
    "L17": ("libJit_fx2_L17.so", "d2d62a12fc2f99f69423fa42d96e9650be6c8aba30982b11d281a5925d2e5098", "put back the output size outsz2560_fx2_v1"),
    # L19/L20: ogfile2560_hs_s_fx2_v2 = the A7 IV's encoder side (101 + 4 sites) + the two MP4 header heights, so tkhd, stsd and Sony's PROF say
    # 3840x2560 (the A7 IV's working ogfile2560_hs_s_v2). L20 puts back either version. N19 = the same without the heights (apply --no-meta).
    "L19": ("libJit_fx2_L19.so", "e2a695989c05bdb4261892f46414d5b9d9bf42e87f30c6103035834beefb3525", "apply the encoder-side design ogfile2560_hs_s_fx2_v2 (101 + 4 sites, and the MP4 headers say 3840x2560: 2 more)"),
    "L20": ("libJit_fx2_L20.so", "decff5bf679512a5004c133d37b6131c93424e4a52c29e570baf884c119eb4eb", "put back the encoder-side design ogfile2560_hs_s_fx2_v2 (or v1)"),
    "N19": ("libJit_fx2_N19.so", "45a68ca583f6f60f05893f6652a1b7d9556870081c4ec127ed0051527f3e8aec", "apply the encoder-side design ogfile2560_hs_s_fx2_v1 (101 + 4 sites; the MP4 headers keep 3840x2160)"),
    # The rear-screen step (optional, on top of the open-gate state): the same level 16/17 code with the screen words. There is no C step: the
    # FX2's own De-Squeeze Display is kept (its ratios are part of S16).
    "S16": ("libJit_fx2_S16.so", "dd8bb759cef4dc8f9b3c63722d3c51036217bb67bda5967c88ca093d8b8f9df0", "apply the screen words lcd32dsq_fx2_v1 (the 3:2 rear screen filled with the whole picture, the focus-frame rectangles, and De-Squeeze Display ratios for a 3:2 picture: 18 words)"),
    "S17": ("libJit_fx2_S17.so", "34075aa0bf39d67ca5623bc0913599fd3c2ada3916bb2ba99d63bc214339b0d8", "put back the screen words lcd32dsq_fx2_v1"),
}
PINS.update({k: v[:2] for k, v in WRITE_STEPS.items()})
LEVELS.update({k: {"L": 200, "S": 300, "N": 500, "B": 700}[k[0]] + int(k[1:]) for k in WRITE_STEPS})
WHICH = "check"
FULL_HEIGHT_COLUMN = 5          # the register-matrix column of the full-height read-out (ogsq_fx2_v1's S0: mode 0x8c0 column 6 -> 5, as on the A7 IV)


def write_result(data):
    """The facts of a write step's result (the A7 IV helper's report format)."""
    import hashlib
    text = data.decode("utf8", "replace")
    lines = text.split("\n")
    pick = lambda start: next((ln for ln in lines if ln.startswith(start)), None)
    outcome = ("UNDO INCOMPLETE" if pick("!! UNDO INCOMPLETE") or pick("UNDO INCOMPLETE") else "DONE" if pick("DONE: ") else "NOTHING TO DO" if pick("NOTHING TO DO") else
               "NOT DONE (everything put back)" if pick("NOT DONE: ") else "NOTHING WRITTEN" if any("nothing is written" in ln for ln in lines) else "UNKNOWN")
    problems = [ln for ln in lines if ln.startswith("!!")]
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "header_ok": lines[0].startswith("readcheck 1 level %s" % WHICH[1:]),
            "euid": "see the result", "sections": [ln for ln in lines if ln.startswith("== ")], "problems": len(problems),
            "complete": any(ln.startswith("== done") for ln in lines[-3:]),
            "s3": {"step": WHICH, "what": WRITE_STEPS[WHICH][2], "outcome": outcome, "ok": outcome in ("DONE", "NOTHING TO DO"),
                   "outcome_line": pick("DONE: ") or pick("NOTHING TO DO") or pick("NOT DONE: ") or pick("!! UNDO INCOMPLETE") or pick("UNDO INCOMPLETE"), "problem_lines": problems}}


def reference():
    return json.loads((S3 / "fx2_reference.json").read_text(encoding="utf8"))


def expected():
    return json.loads((S3 / "fx2_expected.json").read_text(encoding="utf8"))


# ------------------------------------------------------------ reading a result

def check_result(data):
    """The facts of a result file. Keys the A7 IV runner prints, plus this helper's own under "s3"."""
    if WHICH in WRITE_STEPS:
        return write_result(data)
    text = data.decode("utf8", "replace")
    lines = text.split("\n")
    head = lines[0] if lines else ""
    count = lambda pat: sum(1 for ln in lines if re.search(pat, ln))
    verdict = next((ln for ln in lines if ln.startswith("VERDICT ")), "no verdict line")
    pages = {}
    for ln in lines:
        if ln.startswith("cppage "):
            _, name, addr, hx = ln.split(" ", 3)
            pages[int(addr, 16)] = (name, bytes.fromhex(hx.strip()))
    sites = []
    for ln in lines:
        m = re.match(r"site (\S+) (0x[0-9a-f]+) len (\d+)(?: bytes (?:differing from stock )?(\S+))?  (STOCK|TARGET|TEST|OTHER.*|NOT READ)$", ln)
        if m:
            sites.append({"name": m.group(1), "address": m.group(2), "length": int(m.group(3)), "shown": m.group(4), "state": m.group(5)})
    s3 = {"header": head, "verdict": verdict, "ready": verdict.startswith("VERDICT READY"),
          "identity_same": count(r"SAME as the 1\.01 update$"), "identity_differs": count(r"DIFFERS from the 1\.01 update$"),
          "coprocessor_sites": sites, "libmpr_sites": [ln for ln in lines if ln.startswith("lm ")],
          "avcam_stock": count(r"^av .*  STOCK$"), "avcam_target": count(r"^av .*  TARGET$"), "avcam_other": count(r"^av .*  OTHER$"),
          "avcam_guards": [ln for ln in lines if ln.startswith("guard ")], "problem_lines": [ln for ln in lines if ln.startswith("!!")],
          "pages": len(pages)}
    cmd = re.search(r"== file /proc/cmdline\n(.*?)\n== end", text, re.S)
    ver = re.search(r"== file /proc/version\n(.*?)\n== end", text, re.S)
    s3["kernel_command_line"], s3["kernel_version"] = (cmd.group(1).strip() if cmd else None), (ver.group(1).strip() if ver else None)
    if pages:
        s3["decoded"] = decode_pages(pages)
    import hashlib
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "header_ok": head.startswith("fx2read ") and "ILME-FX2 1.01" in head, "euid": "not read",
            "sections": [ln for ln in lines if ln.startswith("== ")], "problems": len(s3["problem_lines"]), "complete": "== done" in lines[-3:],
            "s3": s3, "_pages": pages}


def decode_pages(pages):
    """What the dump's coprocessor pages say, set against the firmware file's tables."""
    ref, out = reference(), {}

    def mem(addr, n):
        b = bytearray()
        while n:
            page = pages.get(addr & ~0xFFF)
            if page is None:
                return None
            take = min(n, 4096 - (addr & 0xFFF))
            b += page[1][addr & 0xFFF:(addr & 0xFFF) + take]
            addr, n = addr + take, n - take
        return bytes(b)

    # the sensor register shadow against each column of the register matrix (the A7 IV sensor's: 24-byte rows, one byte per column)
    rows = [(a, bytes.fromhex(h)) for a, h in ref["matrix"]]
    ncol = max(ref["column_map"]) + 1
    shadow = [(a, mem(a, 1)) for a, _ in rows]
    if all(v is not None for _, v in shadow):
        score = [sum(1 for (a, cols), (_, v) in zip(rows, shadow) if cols[k] == v[0]) for k in range(ncol)]
        best = max(range(ncol), key=lambda k: score[k])
        users = [ref["mode_ids"][i] for i, col in enumerate(ref["column_map"]) if col == best]
        out["sensor_registers"] = {"rows": len(rows), "rows_equal_per_column": score, "closest_column": best, "modes_using_it": users,
                                   "rows_differing_from_it": [[i, hex(a), cols[best], v[0]] for i, ((a, cols), (_, v)) in enumerate(zip(rows, shadow)) if cols[best] != v[0]][:64],
                                   "register_row0": shadow[0][1][0],
                                   "full_height_column": FULL_HEIGHT_COLUMN}
    # the matrix itself as the camera holds it
    m0 = int(ref["matrix_address"], 16)
    got = mem(m0, 24 * len(rows))
    if got is not None:
        want = b"".join(struct.pack("<I", a) + cols for a, cols in rows)
        out["matrix_equals_file"] = got == want
    # the stored drive-parameter records against the emulated ones
    r0, size = int(ref["records_address"], 16), ref["record_size"]
    recs = {}
    for i, mid in enumerate(ref["mode_ids"]):
        b = mem(r0 + i * size, size)
        if b is None:
            continue
        emu = bytes.fromhex(ref["emulated_stock_records"][mid])
        diff = [o for o in range(size) if b[o] != emu[o]]
        recs[mid] = {"index": i, "all_zero": not any(b), "bytes_differing_from_emulation": len(diff), "offsets": [hex(o) for o in diff[:48]], "record": b.hex()}
    out["stored_records"] = recs
    sd = ref["stored_record_design"]
    v = recs.get(sd["mode"])
    if v:
        b, st, dz = bytes.fromhex(v["record"]), bytes.fromhex(sd["stock"]), bytes.fromhex(sd["design"])
        offs = [k for k in range(size) if st[k] != dz[k]]
        out["stored_record_design_bytes"] = {"stock": sum(b[k] == st[k] for k in offs), "design": sum(b[k] == dz[k] for k in offs), "of": len(offs)}
    t = mem(int(ref["size_table_address"], 16), 128)
    if t is not None:
        out["size_table"] = [list(struct.unpack_from("<HHI", t, 8 * k)) for k in range(16)]
    # The resize state. The A7 IV's second scaler block (0x145091c: in w, in h, start x, y, w-1, h-1, fractions) moved on the FX2 with a changed
    # layout (build/port_addr.py a7iv_602 fx2_101: its neighbours went to 0x190cf38.. and 0x190d014, not by one shift), so the dump's pages are
    # searched for the sizes that matter instead; the resize working structure is read where the FX2's code builds it (0x15e4298 / 0x15e42d0).
    st_ = {}
    seen = {}
    pairs = {(7008, 4672), (7008, 3942), (7032, 4688), (7032, 3958), (4336, 2438), (4336, 2560), (3840, 2560), (3840, 2160), (1920, 1080),
             (2176, 2438), (2160, 2438), (1928, 2560), (1912, 2560)}
    for addr, (name, blob) in sorted(pages.items()):
        if name not in ("resizestate", "resizework"):
            continue
        for o in range(0, 4096 - 3, 2):
            p = struct.unpack_from("<HH", blob, o)
            if p in pairs:
                seen.setdefault("%dx%d" % p, []).append(hex(addr + o))
    st_["where_sizes_occur"] = {k: v[:40] for k, v in sorted(seen.items())}
    se = mem(0x190EA40, 0x20)
    if se is not None:
        st_["resize_settings_0x190ea40"] = se.hex()
    if any(n in ("resizestate", "resizework") for n, _ in pages.values()):
        out["scaler_state"] = st_
    # the memory manager's RAM copy: the raw write buffer's four words
    rb = ref.get("raw_write_buffer", [])
    if rb and all(mem(int(w["address"], 16), 4) is not None for w in rb):
        got = [mem(int(w["address"], 16), 4).hex() for w in rb]
        out["raw_write_buffer_words"] = {"stock": sum(g == w["stock"] for g, w in zip(got, rb)), "new": sum(g == w["new"] for g, w in zip(got, rb)),
                                         "other": sum(g not in (w["stock"], w["new"]) for g, w in zip(got, rb))}
    # The display (modding/FX2_PORT_SCREEN.md): panel-type bytes 0x19d98cc (rear; 3 = a 3:2 panel, 2 = 4:3, 1 = 16:9; 4 or more counts as 1)
    # and 0x19d99fc (viewfinder). Fit words of a 16:9 picture 0x1f9ee8 (4:3 panel) / 0x1f9eec (3:2 panel): 3 letterbox, 0 fill (screen step).
    disp = {}
    types = mem(0x19D98CC, 1), mem(0x19D99FC, 1)
    if None not in types:
        name = {1: "16:9", 2: "4:3", 3: "3:2"}
        rear, evf = (1 if types[0][0] >= 4 else types[0][0]), (1 if types[1][0] >= 4 else types[1][0])
        disp["panel_types"] = {"rear_0x19d98cc": types[0][0], "rear_aspect": name.get(rear, "none"), "viewfinder_0x19d99fc": types[1][0], "viewfinder_aspect": name.get(evf, "none")}
    fit = mem(0x1F9EE8, 8)
    if fit is not None:
        disp["fit_16x9_picture"] = {"on_4x3_panel": struct.unpack_from("<I", fit, 0)[0], "on_3x2_panel": struct.unpack_from("<I", fit, 4)[0]}
    frames = {}
    for t in (0xF796D4, 0xF7974C, 0xF797C4):
        b = mem(t, 0x78)
        if b is not None:
            frames[hex(t)] = {"row%d" % r: list(struct.unpack_from("<4H", b, 8 * (5 * r + 3))) for r in range(3)}
    if frames:
        disp["frame_rectangles_16x9_picture"] = frames
    sw = ref.get("screen_words", [])
    if sw and all(mem(int(w["address"], 16), 4) is not None for w in sw):
        got = [mem(int(w["address"], 16), 4).hex() for w in sw]
        disp["screen_words"] = {"stock": sum(g == w["stock"] for g, w in zip(got, sw)), "new": sum(g == w["new"] for g, w in zip(got, sw)),
                                "other": sum(g not in (w["stock"], w["new"]) for g, w in zip(got, sw))}
        dsq = [w for w in sw if w["note"].startswith("de-squeeze")]
        if dsq:
            g2 = [mem(int(w["address"], 16), 4).hex() for w in dsq]
            disp["desqueeze_words"] = "stock" if all(g == w["stock"] for g, w in zip(g2, dsq)) else "3:2 picture (screen step applied)" if all(g == w["new"] for g, w in zip(g2, dsq)) else "mixed or unknown"
    if disp:
        out["display"] = disp
    # v2: the memory manager's workspace (build/dmm_dump.py's layout; unit objects of 0x50 bytes at +0x107e0). Live objects are those of the
    # divisions in force; objects of divisions merged back keep their contents for a while: what was opened lately (e.g. the last movie look).
    dm = ref.get("dmm")
    g = mem(int(dm["workspace_pointer"], 16), 4) if dm else None
    if dm and g is not None:
        ws = struct.unpack("<I", g)[0]
        units = ws + dm["units_at"]
        raw = mem(units, dm["objects"] * dm["object_bytes"]) if ws == int(dm["workspace_expected"], 16) else None
        w = {"workspace": hex(ws), "as_expected": raw is not None}
        if raw is not None:
            objs, by_addr = [], {}
            for i in range(dm["objects"]):
                o = raw[i * 0x50:(i + 1) * 0x50]
                flags = struct.unpack_from("<H", o, 2)[0]
                base = struct.unpack_from("<Q", o, 8)[0]
                off, size = struct.unpack_from("<II", o, 0x10)
                parent, key, owner = struct.unpack_from("<III", o, 0x20)
                group = struct.unpack_from("<I", o, 0x30)[0]
                if size == 0 and key == 0:
                    continue
                by_addr[units + i * 0x50] = key
                objs.append({"n": i, "key": key, "address": base + off, "size": size, "owner": owner, "split": bool(flags & 1), "group": group, "parent": parent})
            split = {units + o["n"] * 0x50 for o in objs if o["split"]}
            live = [o for o in objs if not o["parent"] or o["parent"] in split]
            hraw = mem(ws, dm["handles"] * dm["handle_bytes"]) or b""
            hid = {}
            for h in range(len(hraw) // 0x40):
                mem_id = struct.unpack_from("<I", hraw, h * 0x40)[0]
                if mem_id != 0xFFFFFFFF and any(struct.unpack_from("<12I", hraw, h * 0x40 + 0x10)):
                    hid[ws + h * 0x40] = mem_id
            ids = dm["ids_by_key"]
            name = lambda k: "%#x (ids %s)" % (k, ", ".join(ids.get(hex(k), [])) or "-")
            w["live_objects"] = [{"key": name(o["key"]), "size": o["size"], "in_use": o["owner"] != 0,
                                  "opened_as": hex(hid[o["owner"]]) if o["owner"] in hid else None,
                                  "divided_as_group": hex(o["group"]) if o["split"] and o["group"] < 0x400 else None} for o in live]
            left = collections.Counter((o["key"], o["size"]) for o in objs if o not in live)
            w["left_over_objects"] = [{"key": name(k), "size": s, "count": n} for (k, s), n in sorted(left.items())]
            w["left_over_divisions"] = sorted({"%#x as group %#x" % (o["key"], o["group"]) for o in objs if o not in live and 0 < o["group"] < 0x400})
            # the raw write buffer: id 0x43e is key 0x57f (27,864,320 stock, 33,003,520 with L13); id 0x608 is key 0x6a3 (27,864,320, not changed)
            sizes = lambda key: sorted({o["size"] for o in objs if o["key"] == key})
            w["raw_write_buffer_units_seen"] = {"0x57f (id 0x43e)": sizes(0x57F), "0x6a3 (id 0x608)": sizes(0x6A3), "0x704 (id 0x63d)": sizes(0x704)}
        out["memory_manager"] = w
    # v2: the snapshot debug image's first pages (its format is not known): the tag, whether anything is there, and its printable strings
    sn = ref.get("snapshot")
    if sn:
        a0 = int(sn["address"], 16)
        head = mem(a0, 0x3200)
        if head is not None:
            strings = re.findall(rb"[ -~]{6,}", head)
            out["snapshot_head"] = {"address": sn["address"], "all_zero": not any(head), "first_bytes": head[:64].hex(),
                                    "tag_found": sn["tag"].encode() in head, "nonzero_bytes": sum(1 for x in head if x),
                                    "strings": [s.decode("ascii", "replace") for s in strings[:40]]}
    return out


# ------------------------------------------------------------ the A7 IV runner, pointed at this camera

def known_answer(session, camera):
    want = (S3 / "DeviceInfo.xml").read_bytes()
    there, data = R.read(camera, R.KNOWN_PATH)
    if not there or data != want:
        raise c.StopTest("DeviceInfo.xml is not the file of the 1.01 update (%s); nothing else is sent"
                         % ("the camera returned no file" if not there else "%d bytes, SHA-256 %s" % (len(data), c.sha256(data)[:16])))
    session.say("Known-answer read: DeviceInfo.xml equals the 1.01 file (the A7 IV, A7C II, FX3 and others have the same file: the helper itself checks which camera this is)")


def run_helper(data):
    """What loading the uploaded bytes gives on a model FX2: the real AArch64 code in Unicorn if it is installed, else a canned text."""
    if WHICH in WRITE_STEPS:                        # the write libraries are emulated by helper_fx2/emu_fx2_write.py; here only the session flow is simulated
        text = "readcheck 1 level %s\neuid 0\n== level %s\nDONE: every site holds the target bytes (canned)\n== done, bytes written before this line: 0\n" % (WHICH[1:], WHICH[1:])
        return text.encode(), "canned"
    try:
        import emu_fx2
    except Exception:
        text = "fx2read fx2read_v1 %s for ILME-FX2 1.01; read-only\n== file /proc/version\nLinux (simulated)\n\n== end 18 bytes\n== summary\nVERDICT READY (canned)\n== done\n" % WHICH
        return text.encode(), "canned"
    r, text = emu_fx2.run(bytes(data))
    if r.bad:
        raise AssertionError("the emulated helper stopped: %s" % r.bad)
    return text.encode(), "emulated"


def make_sim(lib, files=None, fault=None):
    sim = _make_sim(lib, files, fault)
    if "/usr/share/pmbp/DeviceInfo.xml" not in (files or {}):
        sim.fs["/usr/share/pmbp/DeviceInfo.xml"] = (S3 / "DeviceInfo.xml").read_bytes()
    return sim


def use(which):
    """Point the runner's module state at one of this camera's libraries."""
    global WHICH
    WHICH = which
    name, sha = PINS[which]
    if not (S3 / name).is_file():
        raise SystemExit("%s is not in this kit%s. Nothing was sent." % (name, " (the write steps are not published yet)" if which in WRITE_STEPS else ""))
    R.LEVEL, R.DESIGN, R.LIB, R.LIB_SHA256 = LEVELS[which], "og4k_data_v1", S3 / name, sha
    R.check_result, R.known_answer, R.run_helper, R.make_sim = check_result, known_answer, run_helper, make_sim
    c.EXPECTED_FIRMWARE = FIRMWARE
    return R.library()


_make_sim = R.make_sim


def selftest(lib):
    done = []

    def check(cond, what):
        if not cond:
            raise AssertionError("self-test failed: " + what)
        done.append(what)

    W, D = "SET_FILE2", "FILE_DELETE2"
    s, sim, stopped = R.simulate(lib, R.body_run)
    r = s.results.get("ct6", {})
    check(not stopped and not sim.unexpected and R.sent(s).count(W) == 1 and R.sent(s).count(D) == 1, "normal run: one write, one delete, nothing off the list")
    check(R.sent(s).index(D) < len(R.sent(s)) - 2 and R.sent(s)[-1] == "GET_FILE2", "normal run: the delete comes before the result is read")
    check(R.LIB_PATH.decode() not in sim.fs and sim.loads == 1, "normal run: the library was loaded once and is gone afterwards")
    f = r.get("result", {}).get("s3", {})
    if WHICH in WRITE_STEPS:
        check(f.get("ok") and r["result"]["header_ok"], "normal run: the step's result is read as DONE")
    else:
        check(f.get("ready") and not f.get("identity_differs"), "normal run: the %s helper reports a stock 1.01 camera as READY" % sim.how)
    if sim.how == "emulated":
        check(len(f["coprocessor_sites"]) == len(expected()["cp_sites"]) and f["avcam_stock"] == 101 and len(f["libmpr_sites"]) == expected()["lm_sites"] == 6,
              "normal run: every coprocessor site, 6 libmpr (4 rows, 2 MP4 header heights) and 101 av-cam sites are reported")
        check(sum(1 for x in f["coprocessor_sites"] if x["name"].startswith("rawbuf_") and x["state"] == "STOCK") == 4,
              "normal run: the raw write buffer's four memory-manager words are reported STOCK")
        if WHICH == "dump":
            d = f.get("decoded", {})
            check(d.get("matrix_equals_file") and len(d.get("stored_records", {})) == 32 and d.get("size_table"), "dump: the pages decode (matrix, 32 records, size table)")
            check(d.get("raw_write_buffer_words") == {"stock": 4, "new": 0, "other": 0}, "dump: the raw write buffer's words decode as stock")
            mm = d.get("memory_manager", {})
            check(mm.get("as_expected") and mm.get("raw_write_buffer_units_seen", {}).get("0x57f (id 0x43e)") == [33003520]
                  and any(o["opened_as"] == "0x43e" for o in mm.get("live_objects", [])) and mm.get("left_over_objects"),
                  "dump: the memory manager's workspace decodes (model: a 0x43e unit of 33,003,520 bytes open, a left-over 0x6a3 object)")
            check(d.get("snapshot_head", {}).get("all_zero") is True, "dump: the snapshot area's first pages are read (all zero in the model)")
            dp = d.get("display", {})
            check(dp.get("fit_16x9_picture") == {"on_4x3_panel": 3, "on_3x2_panel": 3}
                  and all(v == {"row0": [0, 60, 640, 360], "row1": [0, 38, 640, 404], "row2": [0, 60, 640, 360]} for v in dp.get("frame_rectangles_16x9_picture", {"x": 0}).values())
                  and len(dp.get("frame_rectangles_16x9_picture", {})) == 3 and dp.get("desqueeze_words") == "stock"
                  and dp.get("screen_words") == {"stock": 18, "new": 0, "other": 0} and "panel_types" in dp,
                  "dump: the display pages decode (fit words, the three tables' rows, de-squeeze words, the 18 screen words, panel types)")
    s, sim, stopped = R.simulate(lib, R.body_run, files={R.LIB_PATH.decode(): b"someone else's"})
    check(stopped and W not in R.sent(s) and D not in R.sent(s), "a foreign libJit.so on the camera: stops, nothing written, nothing deleted")
    s, sim, stopped = R.simulate(lib, R.body_run, files={"/tmp_wbshd/readcheck_result.txt": b"old"})
    check(stopped and W not in R.sent(s), "a result already on the RAM disk: stops, nothing written")
    s, sim, stopped = R.simulate(lib, R.body_run, files={"/tmp/jbusy": b""})
    check(stopped and W not in R.sent(s), "/tmp/jbusy present: stops, nothing written")
    s, sim, stopped = R.simulate(lib, R.body_run, files={"/usr/share/pmbp/DeviceInfo.xml": b"<other camera/>"})
    check(stopped and len(R.sent(s)) == 2, "another DeviceInfo.xml: stops after the known-answer read")
    s, sim, stopped = R.simulate(lib, R.body_run, fault="load")
    check(stopped and R.sent(s).count(D) == 1 and R.LIB_PATH.decode() not in sim.fs, "a camera that cannot load the library: it is still deleted")
    check(len(R.refusals(lib)) == 15, "the guard refuses the 15 listed packets (changed library, other paths, backup, flash and debug writes ...)")
    return done


def report(session, facts, which):
    f = facts["s3"]
    if which in WRITE_STEPS:
        lines = ["FX2 1.01 step %s: %s" % (which, f["what"]), "OUTCOME: %s" % f["outcome"], str(f["outcome_line"])] + ["  " + ln for ln in f["problem_lines"]]
        session.save_bytes("fx2_report.txt", ("\n".join(lines) + "\n").encode())
        for ln in lines:
            session.say(ln)
        return
    lines = ["FX2 1.01 %s, %s" % (which, time.strftime("%Y-%m-%d %H:%M:%S")), f["header"], f["verdict"],
             "identity: %d same, %d differ" % (f["identity_same"], f["identity_differs"]),
             "kernel: %s" % f["kernel_version"], "command line: %s" % f["kernel_command_line"]]
    for s in f["coprocessor_sites"]:
        lines.append("  coprocessor %-16s %s len %-4d %s%s" % (s["name"], s["address"], s["length"], s["state"], "" if s["shown"] is None else "  (" + s["shown"] + ")"))
    lines += ["  " + ln for ln in f["libmpr_sites"]] + ["  " + ln for ln in f["avcam_guards"]]
    lines.append("  av-cam.bin sites: %d stock, %d target, %d other" % (f["avcam_stock"], f["avcam_target"], f["avcam_other"]))
    lines += ["problem lines:"] + ["  " + ln for ln in f["problem_lines"]] if f["problem_lines"] else ["no problem lines"]
    d = f.get("decoded")
    if d:
        sr = d.get("sensor_registers")
        if sr:
            lines.append("sensor register shadow: closest matrix column %d (%d of %d rows equal; modes %s); register row 0 holds %d (column %d is the full-height read-out)"
                         % (sr["closest_column"], sr["rows_equal_per_column"][sr["closest_column"]], sr["rows"], ", ".join(sr["modes_using_it"]), sr["register_row0"], sr["full_height_column"]))
        lines.append("register matrix equals the file: %s" % d.get("matrix_equals_file"))
        zero = [m for m, v in d.get("stored_records", {}).items() if v["all_zero"]]
        same = [m for m, v in d.get("stored_records", {}).items() if not v["bytes_differing_from_emulation"]]
        lines.append("stored drive-parameter records: %d read, %d equal to the emulated ones, %d all zero" % (len(d.get("stored_records", {})), len(same), len(zero)))
        v = d.get("stored_records", {}).get("0x8c0")
        if v:
            lines.append("  mode 0x8c0: %d bytes differ from the emulation at %s" % (v["bytes_differing_from_emulation"], ", ".join(v["offsets"])))
        if d.get("stored_record_design_bytes"):
            lines.append("  mode 0x8c0, the design's %(of)d bytes: %(stock)d stock, %(design)d as the design" % d["stored_record_design_bytes"])
        if d.get("size_table"):
            lines.append("movie size table: " + "; ".join("%dx%d id %#x" % tuple(r) for r in d["size_table"]))
        if d.get("raw_write_buffer_words"):
            lines.append("raw write buffer words (memory manager): %(stock)d stock, %(new)d applied, %(other)d other" % d["raw_write_buffer_words"])
        mm = d.get("memory_manager")
        if mm:
            lines.append("memory manager workspace %s (%s)" % (mm["workspace"], "decoded" if mm["as_expected"] else "NOT at the expected address: not decoded"))
            if mm.get("as_expected"):
                lines.append("  raw write buffer units seen (live or left over): %s" % mm["raw_write_buffer_units_seen"])
                for o in mm["live_objects"]:
                    if o["in_use"] or o["divided_as_group"]:
                        lines.append("  live: key %s size %d%s%s" % (o["key"], o["size"], ", open as %s" % o["opened_as"] if o["opened_as"] else "",
                                                                   ", divided as group %s" % o["divided_as_group"] if o["divided_as_group"] else ""))
                for o in mm["left_over_objects"][:30]:
                    lines.append("  left over: key %s size %d x %d" % (o["key"], o["size"], o["count"]))
                if mm["left_over_divisions"]:
                    lines.append("  left-over divisions: %s" % ", ".join(mm["left_over_divisions"][:20]))
        sh = d.get("snapshot_head")
        if sh:
            lines.append("snapshot debug image at %s: %s; tag SOLID_SSHOT %s; %d non-zero bytes in its first pages; first bytes %s"
                         % (sh["address"], "all zero" if sh["all_zero"] else "HOLDS DATA", "found" if sh["tag_found"] else "not found", sh["nonzero_bytes"], sh["first_bytes"][:48]))
            for s in sh["strings"][:20]:
                lines.append("  snapshot string: %s" % s[:120])
        ss = d.get("scaler_state")
        if ss:
            lines.append("resize state (pages ported from the A7 IV's by code reference; the block's layout is not confirmed, so sizes are searched):")
            for k, v in ss.get("where_sizes_occur", {}).items():
                lines.append("  %s at %s%s" % (k, ", ".join(v[:10]), " ..." if len(v) > 10 else ""))
            if "resize_settings_0x190ea40" in ss:
                lines.append("  module settings 0x190ea40: %s" % ss["resize_settings_0x190ea40"])
        dp = d.get("display")
        if dp:
            lines.append("display (what the screen step changes):")
            if "panel_types" in dp:
                t = dp["panel_types"]
                lines.append("  panel types: rear %d (%s), viewfinder %d (%s)" % (t["rear_0x19d98cc"], t["rear_aspect"], t["viewfinder_0x19d99fc"], t["viewfinder_aspect"]))
            if "fit_16x9_picture" in dp:
                ft = dp["fit_16x9_picture"]
                lines.append("  a 16:9 picture: fit word on a 4:3 panel %d, on a 3:2 panel %d (3 letterbox, 0 fill)" % (ft["on_4x3_panel"], ft["on_3x2_panel"]))
            if "desqueeze_words" in dp:
                lines.append("  De-Squeeze Display ratio and crop words: %s" % dp["desqueeze_words"])
            if "screen_words" in dp:
                lines.append("  screen step words: %(stock)d stock, %(new)d applied, %(other)d other" % dp["screen_words"])
            for t, rw in dp.get("frame_rectangles_16x9_picture", {}).items():
                lines.append("  frame table %s: row 0 %s, row 1 %s, row 2 %s" % (t, rw["row0"], rw["row1"], rw["row2"]))
    session.save_bytes("fx2_report.txt", ("\n".join(lines) + "\n").encode())
    for ln in lines[:8] + lines[-6:]:
        session.say(ln)


def last_saved_sha():
    """The SHA-256 of the result the newest saved session of this kit fetched, or None."""
    root = c.PRIVATE_ROOT
    if not root.is_dir():
        return None
    for folder in sorted((p for p in root.iterdir() if p.is_dir() and p.name.startswith("CT6_")), reverse=True):
        try:
            return json.loads((folder / "manifest.json").read_text(encoding="utf8"))["results"]["ct6"]["result"]["sha256"]
        except (OSError, KeyError, TypeError, ValueError):
            continue
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("which", choices=sorted(PINS))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--go", action="store_true")
    ap.add_argument("--remove-only", action="store_true")
    ap.add_argument("--clear-result", metavar="SHA256", help="first delete the result file of an earlier run from the RAM disk, only if its SHA-256 is this")
    ap.add_argument("--firmware-shown")
    ap.add_argument("--writes-memory", action="store_true", help="needed for a write step (L13, L14, L5, L6, B5, B6, L16, L17, L19, L20, N19, S16, S17): it changes the running camera's memory")
    a = ap.parse_args()
    if a.which in WRITE_STEPS and a.go and not (a.dry_run or a.selftest) and not a.writes_memory:
        raise SystemExit("%s is a write step: %s. It needs --writes-memory as well. Use fx2_apply.py. Nothing was sent." % (a.which, WRITE_STEPS[a.which][2]))
    lib = use(a.which)
    if a.dry_run or a.selftest:
        if a.selftest:                              # --dry-run and --selftest win over --go (the launchers always pass --go): nothing is sent
            for line in selftest(lib):
                print("PASS  " + line)
            print("all checks passed; nothing was sent to any device")
        else:
            print("\n".join(R.dry_run_lines(lib)))
        return
    if not a.go or a.firmware_shown != FIRMWARE:
        raise SystemExit("A live run needs --go and --firmware-shown %s (the version the camera's menu shows). Nothing was sent." % FIRMWARE)
    R.refusals(lib)
    selftest(lib)                                   # the flow must pass on the simulated camera on the day, before the real one
    import ct1_stage2_service as service
    # A result left on the RAM disk by the run before stops a new run. Without --clear-result the newest result saved on this PC is named: the
    # runner deletes the camera's file only if its SHA-256 is that one, i.e. only a result already here.
    R.CLEAR_SHA = a.clear_result or last_saved_sha()
    body = R.body_remove_only if a.remove_only else R.body_run
    with c.Session("remove_only" if a.remove_only else "fx2_%s" % a.which, test="CT6") as session:
        session.results.update(firmware_shown_on_camera=a.firmware_shown, model=MODEL, which=a.which, library_sha256=PINS[a.which][1],
                               pc={"platform": platform.platform(), "python": sys.version.split()[0]})
        inner = service.connect(session)
        try:
            R.service_session(session, inner, lambda cam: body(session, cam, lib), lib)
            facts = session.results.get("ct6", {}).get("result")
            if facts and not a.remove_only:
                pages = facts.pop("_pages", {})
                for addr, (name, blob) in sorted(pages.items()):
                    session.save_bytes("cp_%s_%08x.bin" % (name, addr), blob)
                report(session, facts, a.which)
        finally:
            time.sleep(3)
            c.print_pnp(session, "after the stop request")
            out = session.results.get("ct6", {})
            print("Library sent: %s. On the camera now: %s." % (
                "yes" if out.get("library_sent") else "no",
                {False: "no (confirmed)", True: "YES", None: "not sent" if not out.get("library_sent") and not a.remove_only else "UNKNOWN"}[out.get("library_on_camera_after")]))
            if a.which in WRITE_STEPS:
                print("This was a WRITE step. A cold boot (battery out for 10 seconds) undoes everything written. Whether the power switch alone does on the FX2 is not known (on the A7 IV it does not, on the A7S III it does): keep the camera on between steps.")
            else:
                print("Nothing on the camera was changed. Unplug and replug the USB cable before another run; a cold boot (battery out) clears the result file.")


if __name__ == "__main__":
    main()
