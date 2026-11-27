#!/bin/bash
# FX2 (firmware 1.01): THE 3840x2560 OPEN GATE (fourth kit; WORKS on an FX2 set to NTSC, GitHub issue 5): raw write buffer, sensor step H5 (first scaler 4336x2560), output size, encoder side with the MP4 headers, rear screen; then one read-only dump on MOVIE. 3840x2560 clips of the whole 3:2 sensor area. XAVC HS 4K or XAVC S 4K, 23.98p (on a PAL-set camera it takes the PAL step P5: XAVC S 4K, 25p). SteadyShot Off for a first run. Start from a cold boot on STILL.
# WRITES into the camera's memory (not firmware, not settings). A cold boot (battery out for 10 seconds) returns it to stock. The power switch alone does NOT on the FX2: it keeps the encoder step (a mixed state not to record in).
cd "$(dirname "$0")" || exit 1
exec "$PWD/run.sh" apply og2560 "$@"
