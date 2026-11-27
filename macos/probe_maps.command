#!/bin/bash
cd "$(dirname "$0")" || exit 1
exec "$PWD/run.sh" run V23 --go --writes-memory --firmware-shown 1.01 "$@"
