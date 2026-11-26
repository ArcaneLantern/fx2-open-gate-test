#!/bin/bash
# FX2 (firmware 1.01): TEST 6 (fourth kit): test 5 plus the output size (3840x2560), then one read-only dump on MOVIE. A DIAGNOSTIC STEP ONLY: do NOT press REC (no encoder step yet; on an FX2 a recording in this state froze the camera until the battery was pulled). SteadyShot Off. Start from a cold boot on STILL. NOT YET RUN ON AN FX2.
# WRITES into the camera's memory (not firmware, not settings). A cold boot (battery out for 10 seconds) returns it to stock. The power switch alone does NOT on the FX2: it keeps the encoder step (a mixed state not to record in).
cd "$(dirname "$0")" || exit 1
exec "$PWD/run.sh" apply test6 "$@"
