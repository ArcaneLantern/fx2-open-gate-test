#!/bin/bash
# FX2 (firmware 1.01): TEST 6 (fourth kit): test 5 plus the output size (3840x2560), then one read-only dump on MOVIE. Expected: a steady picture; a recording may stop after a second (no encoder step yet). SteadyShot Off. Start from a cold boot on STILL. NOT YET RUN ON AN FX2.
# WRITES into the camera's memory (not firmware, not settings). A cold boot (battery out for 10 seconds) returns it to stock; whether the power switch alone does on the FX2 is not known.
cd "$(dirname "$0")" || exit 1
exec "$PWD/run.sh" apply test6 "$@"
