#!/bin/bash
# FX2 (firmware 1.01): DIAGNOSTIC TEST 1 (second kit): the raw write buffer and the full-height sensor read-out with the stock 16:9 picture (the A7 IV's fhband_v1), then one read-only dump on MOVIE. Start from a cold boot on STILL.
# WRITES into the camera's memory (not firmware, not settings). A cold boot (battery out for 10 seconds) returns it to stock. The power switch alone does NOT on the FX2: it keeps the encoder step (a mixed state not to record in).
cd "$(dirname "$0")" || exit 1
exec "$PWD/run.sh" apply test1 "$@"
