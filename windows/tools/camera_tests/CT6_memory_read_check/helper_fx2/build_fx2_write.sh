#!/bin/bash
# Build the FX2 1.01 write libraries from the A7 IV helper's source (helper/readcheck.c), with this build's tables and constants
# (FX2 port, 2026-11-25). Run gen_fx2_write.py first.
# usage: build_fx2_write.sh        (writes libJit_fx2_<step>.so into this folder and prints SHA-256, size, step)
# Flags are those of helper/rebuild.sh. Differences from an A7 IV build: the headers of gen_fx2_write.py, the FX2 1.01 libsencore.so to link
# against, and these constants (modding/FX2_PORT.md):
#   L13/L14  the DMM server's page of pointers 0x192f000: workspace +0xc28, unit objects +0x77c (modding/FX2_PORT_DMM_SIZE.md); the four
#            words of dmmwb4688_fx2_v1 with the A7 IV / A7C II texts (fit: two units of 33,003,520 bytes in the parent key 0x6fa)
#   L5/L6    IMAGER 0x1750860 (0xa0d74c returns it; = A7C II 0x18aeb8c), drive-parameter pointer at control +0x6ac (the FX2's control
#            object puts every field 8 bytes on from the A7C II's +0x684: the constructor block 0xa0fab6 stores it at 0xa0fbe8), stored
#            record 0x170 bytes (0xa10ae2)
#   L19/L20, N19   av-cam.bin at physical 0x401000000 (kemco.txt: memrsv=0x01000000@0x401000000:ex, as the A7 IV and A7C II)
# Steps as in the FX3 kit, plus the A7 IV kit's raw write buffer: L = open gate (13/14 raw write buffer, 5/6 sensor side, 16/17 output size,
# 19/20 encoder side with the MP4 header heights), N19 = the encoder side without the heights (--no-meta; put back by L20),
# S = the screen words (16/17). No C step (the FX2's own De-Squeeze Display is kept) and no P step (the FX2's av-cam opens playback
# decodes with the A7 IV's 8K channel: modding/FX2_PORT_ENCODER.md).
set -e
H="$(cd "$(dirname "$0")" && pwd)"
SEN="$H/../../../work/extracted/fx2_101/0700_part_image/dev/nflasha15/lib/libsencore.so"
cd "$H/../helper"
CC=(../../../work/venv_zig/Scripts/python.exe -m ziglang cc -target aarch64-linux-gnu -std=gnu11 -O1 -Wall -Wextra -Werror -fPIC -shared -nostdlib -ffreestanding
    -fno-stack-protector -fno-builtin -fno-asynchronous-unwind-tables -Wl,-soname,libJit.so -Wl,--no-undefined -Wl,-z,now -g0 -s -Wl,-z,max-page-size=4096)
for L in 13 14; do
  "${CC[@]}" -DLEVEL=$L '-DDMM_SITES_H="expected_dmm_dmmwb4688_fx2_v1.h"' -DDMM_GLOBALS=0x0192f000UL -DG_WORKSPACE=0xc28U -DG_UNITS=0x77cU \
    readcheck.c "$SEN" -o "$H/libJit_fx2_L$L.so"
done
for L in 5 6; do
  "${CC[@]}" -DLEVEL=$L '-DSITES_H="expected_sites_ogsq_fx2_v1.h"' '-DDESIGN_LABEL="ogsq_fx2_v1"' -DIMAGER=0x1750860UL -DCTRL_DRVPARAM=0x6acU -DREC=0x170U \
    readcheck.c "$SEN" -o "$H/libJit_fx2_L$L.so"
done
# B5/B6 (second kit, 2026-11-26): the same levels 5/6 with fhband_fx2_v1, the A7 IV's fhband_v1 (full-height read-out, the stock 16:9 band),
# test 1 of the diagnostic ladder after the first FX2 test crashed on movie entry
for L in 5 6; do
  "${CC[@]}" -DLEVEL=$L '-DSITES_H="expected_sites_fhband_fx2_v1.h"' '-DDESIGN_LABEL="fhband_fx2_v1"' -DIMAGER=0x1750860UL -DCTRL_DRVPARAM=0x6acU -DREC=0x170U \
    readcheck.c "$SEN" -o "$H/libJit_fx2_B$L.so"
done
# H5/H6 (fourth kit, 2026-11-26): the same levels 5/6 with ogh2560_fx2_v1, the A7 IV's ogh2560_v1 (ogsq_v3 with records whose first-stage
# scaler gives 4336x2560). On the FX2 the output size 3840x2560 needs it: the resize set-up raises the first-scaler size it hands on to
# the output size (modding/FX2_PORT.md, "Why L16 crashed")
for L in 5 6; do
  "${CC[@]}" -DLEVEL=$L '-DSITES_H="expected_sites_ogh2560_fx2_v1.h"' '-DDESIGN_LABEL="ogh2560_fx2_v1"' -DIMAGER=0x1750860UL -DCTRL_DRVPARAM=0x6acU -DREC=0x170U \
    readcheck.c "$SEN" -o "$H/libJit_fx2_H$L.so"
done
for L in 16 17; do
  "${CC[@]}" -DLEVEL=$L '-DWORDS_H="expected_words_outsz2560_fx2_v1.h"' readcheck.c "$SEN" -o "$H/libJit_fx2_L$L.so"
  "${CC[@]}" -DLEVEL=$L '-DWORDS_H="expected_words_lcd32dsq_fx2_v1.h"' readcheck.c "$SEN" -o "$H/libJit_fx2_S$L.so"
  # F16/F17 (fourth kit, the fallback): fehold_fx2_v1, one code word of the resize set-up
  "${CC[@]}" -DLEVEL=$L '-DWORDS_H="expected_words_fehold_fx2_v1.h"' readcheck.c "$SEN" -o "$H/libJit_fx2_F$L.so"
done
for L in 19 20; do
  "${CC[@]}" -DLEVEL=$L '-DMP_H="expected_mp_ogfile2560_hs_s_fx2_v2.h"' -DAVCAM_PHYS=0x401000000UL readcheck.c -o "$H/libJit_fx2_L$L.so"
done
"${CC[@]}" -DLEVEL=19 '-DMP_H="expected_mp_ogfile2560_hs_s_fx2_v1.h"' -DAVCAM_PHYS=0x401000000UL readcheck.c -o "$H/libJit_fx2_N19.so"
cd "$H"
for N in L13 L14 L5 L6 B5 B6 H5 H6 L16 L17 F16 F17 L19 L20 N19 S16 S17; do echo "$(sha256sum libJit_fx2_$N.so | cut -d' ' -f1) $(stat -c %s libJit_fx2_$N.so) $N"; done
