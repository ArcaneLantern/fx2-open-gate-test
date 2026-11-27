#!/bin/bash
# FX2 (firmware 1.01): TEST 7, THE FALLBACK (fourth kit): raw write buffer, the squeeze sensor step L5, one code word that keeps the first-scaler size (F16), output size, encoder side; then one read-only dump on MOVIE. Run it only if test 5 gives no picture. SteadyShot Off. Start from a cold boot on STILL. NOT YET RUN ON AN FX2.
# WRITES into the camera's memory (not firmware, not settings). A cold boot (battery out for 10 seconds) returns it to stock. The power switch alone does NOT on the FX2: it keeps the encoder step (a mixed state not to record in).
cd "$(dirname "$0")" || exit 1
exec "$PWD/run.sh" apply test7 "$@"
