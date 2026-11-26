#!/bin/bash
# FX2 (firmware 1.01): THE 3840x2560 TEST (fourth kit): raw write buffer, sensor step H5 (first scaler 4336x2560), output size, encoder side with the MP4 headers, rear screen; then one read-only dump on MOVIE. Expected: 3840x2560 clips of the whole 3:2 sensor area. XAVC HS 4K or XAVC S 4K, 23.98p, SteadyShot Off. Start from a cold boot on STILL. NOT YET RUN ON AN FX2.
# WRITES into the camera's memory (not firmware, not settings). A cold boot (battery out for 10 seconds) returns it to stock; whether the power switch alone does on the FX2 is not known.
cd "$(dirname "$0")" || exit 1
exec "$PWD/run.sh" apply og2560 "$@"
