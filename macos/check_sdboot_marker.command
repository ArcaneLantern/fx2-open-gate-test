#!/bin/bash
# FX2 SD-boot TEST (LOCAL): after a power-cycle, read /setting/fx2_preload_ran and report whether the hook fired.
# Reads /setting; writes nothing there. Camera on STILL, USB in (Mass Storage).
cd "$(dirname "$0")" || exit 1
exec "$PWD/run.sh" run V18 --go --writes-memory --firmware-shown 1.01 "$@"
