#!/bin/bash
# FX2 (firmware 1.01): apply only the four open-gate steps (raw write buffer, sensor, output size, encoder), without the screen step.
# WRITES into the camera's memory (not firmware, not settings). A cold boot (battery out for 10 seconds) returns it to stock. The power switch alone does NOT on the FX2: it keeps the encoder step (a mixed state not to record in).
cd "$(dirname "$0")" || exit 1
exec "$PWD/run.sh" apply apply --no-screen "$@"
