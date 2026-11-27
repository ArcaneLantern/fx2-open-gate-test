#!/bin/bash
# FX2 (firmware 1.01): THE 5760x3840 STATE WITH XAVC S-I 4K: open_gate_5760x3840_test plus one encoder step for XAVC S-I 4K at 5760x3840 (G19; works on an A7 IV at 24p). Start from a cold boot on STILL. NOT YET RUN ON AN FX2.
# WRITES into the camera's memory (not firmware, not settings). A cold boot (battery out for 10 seconds) returns it to stock. The power switch alone does NOT on the FX2: it keeps the encoder step (a mixed state not to record in).
cd "$(dirname "$0")" || exit 1
exec "$PWD/run.sh" apply og57si "$@"
