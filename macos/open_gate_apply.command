#!/bin/bash
# FX2 (firmware 1.01): apply the A7 IV's default state ported to the FX2: 3840x2560 open gate, MP4 headers at 3840x2560, and the 3:2 rear screen filled, with De-Squeeze Display set for it (five steps, then one read-only session). ON THE FX2 THIS CRASHES ON MOVIE ENTRY (2026-11-25, 2026-11-26): use open_gate_squeezed, or the fourth kit's open_gate_3840x2560_test.
# WRITES into the camera's memory (not firmware, not settings). A cold boot (battery out for 10 seconds) returns it to stock; whether the power switch alone does on the FX2 is not known.
cd "$(dirname "$0")" || exit 1
exec "$PWD/run.sh" apply apply "$@"
