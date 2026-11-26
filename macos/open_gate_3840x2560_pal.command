#!/bin/bash
# FX2 (firmware 1.01): THE 3840x2560 OPEN GATE FOR A PAL-SET FX2 (fifth kit): raw write buffer, the PAL sensor step P5 (mode 0x880, 25p), output size, encoder side with the MP4 headers, rear screen; then one read-only dump on MOVIE. XAVC HS 4K or XAVC S 4K, 25p, SteadyShot Off. Start from a cold boot on STILL. NOT YET RUN ON A CAMERA (emulated against a PAL FX2's own records).
# WRITES into the camera's memory (not firmware, not settings). A cold boot (battery out for 10 seconds) returns it to stock. The power switch alone does NOT on the FX2: it keeps the encoder step (a mixed state not to record in).
cd "$(dirname "$0")" || exit 1
exec "$PWD/run.sh" apply og2560 --pal "$@"
