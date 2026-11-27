#!/bin/bash
# FX2 (firmware 1.01): put back the 5760x3840 (5.7K) state without a cold boot: screen, encoder side, output side, sensor step, raw write buffer (NTSC or PAL as the newest check reads it).
# WRITES into the camera's memory (not firmware, not settings). A cold boot (battery out for 10 seconds) returns it to stock. The power switch alone does NOT on the FX2: it keeps the encoder step (a mixed state not to record in).
cd "$(dirname "$0")" || exit 1
exec "$PWD/run.sh" apply putback-57 "$@"
