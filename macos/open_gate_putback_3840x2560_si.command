#!/bin/bash
# FX2 (firmware 1.01): put back open_gate_3840x2560_si_test without a cold boot.
# WRITES into the camera's memory (not firmware, not settings). A cold boot (battery out for 10 seconds) returns it to stock. The power switch alone does NOT on the FX2: it keeps the encoder step (a mixed state not to record in).
cd "$(dirname "$0")" || exit 1
exec "$PWD/run.sh" apply putback-2560si "$@"
