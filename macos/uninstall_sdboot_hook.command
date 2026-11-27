#!/bin/bash
# FX2 SD-boot TEST (LOCAL): remove the preload hook, the marker .so and the test marker from /setting. Back to stock.
# Camera on STILL, USB in (Mass Storage). This is also the RECOVERY step if the hook ever misbehaves.
cd "$(dirname "$0")" || exit 1
exec "$PWD/run.sh" run V17 --go --writes-memory --firmware-shown 1.01 "$@"
