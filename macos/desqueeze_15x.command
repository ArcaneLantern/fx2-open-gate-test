#!/bin/bash
# FX2 1.01 (LOCAL, 2026-11-27): add the 1.5x anamorphic preview on its own, after an open gate apply: A16 makes De-Squeeze Display 1.3x
# show 2.25:1 (a 3:2 frame through a 1.5x anamorphic lens). It refuses unless the screen step S16 is already in place. Display only.
# Camera on STILL, USB in (Mass Storage). Undo: A17 (back to 1.95:1) or a cold boot (battery out 10 s, USB unplugged).
cd "$(dirname "$0")" || exit 1
exec "$PWD/run.sh" run A16 --go --writes-memory --firmware-shown 1.01 "$@"
