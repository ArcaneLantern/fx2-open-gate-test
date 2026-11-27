#!/bin/bash
# FX2 (firmware 1.01): apply the default state with the encoder step without the MP4 header heights: the files' MP4 headers keep saying 3840x2160.
# WRITES into the camera's memory (not firmware, not settings). A cold boot (battery out for 10 seconds) returns it to stock. The power switch alone does NOT on the FX2: it keeps the encoder step (a mixed state not to record in).
cd "$(dirname "$0")" || exit 1
exec "$PWD/run.sh" apply apply --no-meta "$@"
