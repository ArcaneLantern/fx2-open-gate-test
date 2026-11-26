#!/bin/bash
# FX2 (firmware 1.01): the squeezed open gate for a PAL-set FX2 (fifth kit): raw write buffer, the PAL sensor step Q5 (mode 0x880, 25p), rear screen; then one read-only dump on MOVIE. A 3840x2160 file holding the whole 3:2 sensor area squeezed (stretch by 32/27). Start from a cold boot on STILL. NOT YET RUN ON A CAMERA.
# WRITES into the camera's memory (not firmware, not settings). A cold boot (battery out for 10 seconds) returns it to stock. The power switch alone does NOT on the FX2: it keeps the encoder step (a mixed state not to record in).
cd "$(dirname "$0")" || exit 1
exec "$PWD/run.sh" apply squeeze --pal "$@"
