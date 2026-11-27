#!/bin/bash
# FX2 (firmware 1.01): THE 5760x3840 (5.7K) TEST FOR A PAL-SET FX2: as open_gate_5760x3840_test with the PAL sensor step J5 (mode 0x880). XAVC S 4K, 25p. SteadyShot Off. A V90 SD card or CFexpress Type A. Start from a cold boot on STILL. NOT YET RUN ON AN FX2.
# WRITES into the camera's memory (not firmware, not settings). A cold boot (battery out for 10 seconds) returns it to stock. The power switch alone does NOT on the FX2: it keeps the encoder step (a mixed state not to record in).
cd "$(dirname "$0")" || exit 1
exec "$PWD/run.sh" apply og57 --pal "$@"
