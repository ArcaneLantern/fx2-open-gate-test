#!/bin/bash
# FX2 (firmware 1.01): DIAGNOSTIC TEST 4 (third kit): test 3 plus the encoder side (the open gate without the screen step), then one read-only dump on MOVIE. Start from a cold boot on STILL.
# WRITES into the camera's memory (not firmware, not settings). A cold boot (battery out for 10 seconds) returns it to stock; whether the power switch alone does on the FX2 is not known.
cd "$(dirname "$0")" || exit 1
exec "$PWD/run.sh" apply test4 "$@"
