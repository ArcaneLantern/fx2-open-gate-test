#!/bin/bash
# FX2 (firmware 1.01): THE 3840x2560 OPEN GATE WITH XAVC S-I 4K: open_gate_3840x2560_test plus one encoder step for XAVC S-I 4K (AVC intra 4:2:2 10-bit) at 3840x2560 (I19). 23.98p (PAL: 25p). Start from a cold boot on STILL. The S-I step is NOT YET RUN ON AN FX2.
# WRITES into the camera's memory (not firmware, not settings). A cold boot (battery out for 10 seconds) returns it to stock. The power switch alone does NOT on the FX2: it keeps the encoder step (a mixed state not to record in).
cd "$(dirname "$0")" || exit 1
exec "$PWD/run.sh" apply og2560si "$@"
