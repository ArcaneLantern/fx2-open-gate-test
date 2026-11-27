#!/bin/bash
# FX2 SD-boot TEST (LOCAL, 2026-11-27): install the preload hook. Delivered by the kit's guarded Jiritsu path.
# *** THIS WRITES THE CAMERA'S FLASH (/setting) — the first persistent write in this kit. A battery pull does NOT undo it. ***
# Undo: uninstall_sdboot_hook.command (or delete /setting/mode/preload over USB service mode, or a firmware update).
# Camera on STILL, USB in (Mass Storage). Then power-cycle and run read_sdboot_marker.command to check if the hook fired.
cd "$(dirname "$0")" || exit 1
echo "This writes /setting on the camera (persistent, survives a battery pull). Undo = uninstall_sdboot_hook.command."
exec "$PWD/run.sh" run V16 --go --writes-memory --firmware-shown 1.01 "$@"
