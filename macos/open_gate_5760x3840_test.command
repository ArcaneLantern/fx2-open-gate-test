#!/bin/bash
# FX2 (firmware 1.01): THE 5760x3840 (5.7K) TEST: raw write buffer, the sensor step K5 (first scaler 5760x3840), four scaler units with a 30.8 MB output buffer and the output size 5760x3840 (K16), the encoder side at 300 Mbps on the 100M+ settings with I and P pictures only and the MP4 headers at 5760x3840 (K19), rear screen; then one read-only dump on MOVIE. XAVC HS 4K or XAVC S 4K, 23.98p; on a PAL-set camera the PAL step J5 and XAVC S 4K 25p. SteadyShot Off. A V90 SD card or CFexpress Type A. Start from a cold boot on STILL. NOT YET RUN ON AN FX2 (the A7 IV records 5760x3840 with these steps).
# WRITES into the camera's memory (not firmware, not settings). A cold boot (battery out for 10 seconds) returns it to stock. The power switch alone does NOT on the FX2: it keeps the encoder step (a mixed state not to record in).
cd "$(dirname "$0")" || exit 1
exec "$PWD/run.sh" apply og57 "$@"
