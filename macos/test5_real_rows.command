#!/bin/bash
# FX2 (firmware 1.01): TEST 5 (fourth kit): the raw write buffer and the sensor step H5, whose first scaler gives 4336x2560 (the A7 IV's ogh2560_v1), then one read-only dump on MOVIE. Expected: squeezed 3840x2160 clips, as test 2. SteadyShot Off. Start from a cold boot on STILL. NOT YET RUN ON AN FX2.
# WRITES into the camera's memory (not firmware, not settings). A cold boot (battery out for 10 seconds) returns it to stock. The power switch alone does NOT on the FX2: it keeps the encoder step (a mixed state not to record in).
cd "$(dirname "$0")" || exit 1
exec "$PWD/run.sh" apply test5 "$@"
