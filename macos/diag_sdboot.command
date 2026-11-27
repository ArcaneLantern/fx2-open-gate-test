#!/bin/bash
# FX2 SD-boot DIAGNOSTIC (LOCAL): report which /setting files the install created. Read-only. Camera on STILL, USB in.
cd "$(dirname "$0")" || exit 1
exec "$PWD/run.sh" run V19 --go --writes-memory --firmware-shown 1.01 "$@"
