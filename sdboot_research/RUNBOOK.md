# FX2 SD/preload boot hook — moderately-safe test runbook (2026-11-27, LOCAL)

Goal of this first test: prove Sony's own `/setting/mode/preload` LD_PRELOAD hook fires at boot,
using a **harmless no-op payload**. No open-gate code, no SD reading yet — just "does the hook run?".

## Why this is moderately safe (all verified read-only from the firmware)
1. **A bad/missing preload is NON-FATAL.** The FX2's dynamic linker is stock glibc 2.25; on a
   preload it cannot load it prints `object '...' cannot be preloaded (...): ignored.` and the app
   **boots normally**. So even a broken payload cannot brick boot. (Only a payload that loads AND
   crashes in its constructor could wedge the app — ours does one marker write and returns.)
2. **The payload is a verified no-op**: `fx2_preload_marker.so` writes `/setting/fx2_preload_ran`
   and returns. Nothing else.
3. **The hook is on a WRITABLE data partition** (`/setting` = nflasha2, rw vfat) and only affects the
   camera app (`im.elf`, launched by `bootin.elf`) — not early boot.
4. **Recovery is reachable even in the worst case** (see below), because the USB service daemon
   `sen.elf` is started by `init2` **before** `bootin.elf` runs the preload.
5. **If my reading of `bootin.elf` is wrong**, writing the hook file simply does nothing and the
   marker never appears — a null result, not a brick.

## What is NOT yet proven / the one real step
- Exact instruction trace of `bootin.elf` (string→setenv LD_PRELOAD→execve) — blocked by PIE/GOT
  relocations; evidence is strings + `setenv`/`execve` imports + Sony's debug preload libs. **This
  test is itself the confirmation.**
- **The first write to `/setting` is the first persistent (flash) write in the whole FX2 project.**
  Everything before this was RAM-only (battery-pull reverts). This file persists until removed.

## Artifacts (built, aarch64, offline-verified — SHA256SUMS.txt)
- `fx2_preload_marker.so`  — the no-op payload (writes the marker).
- `fx2_sdboot_install.so`  — loaded-in-camera installer: writes the payload to `/setting/` and sets
  `/setting/mode/preload` = `/setting/fx2_preload_marker.so`.
- `fx2_sdboot_uninstall.so`— removes `/setting/mode/preload`, the payload, and the marker.

## INTEGRATION DONE — the test is runnable through the kit's guarded path
Registered as steps V16/V17/V18 in `fx2_run.py` (SHA-pinned libs in `helper_fx2/`), delivered by the
same Jiritsu path as every other step (one write + deletes, auto-removed), each emitting the kit's
result so `run.sh` reports OUTCOME DONE. All three pass `--selftest`. Launchers in `macos/`:
`install_sdboot_hook.command` (V16), `check_sdboot_marker.command` (V18), `uninstall_sdboot_hook.command` (V17).

## Test procedure (one command each; the user's explicit go is the only gate)
1. Battery out 10 s (known-stock). Switch on, **STILL**, USB in (Mass Storage).
2. **Install** — `macos/install_sdboot_hook.command` → password → OUTCOME DONE. (Writes `/setting`.)
3. **Power-cycle** the camera (normal off/on — the actual boot test). Then STILL, USB in.
4. **Check** — `macos/check_sdboot_marker.command`:
   - `DONE: marker present -- ... hook FIRED` → mechanism confirmed.
   - `!! marker absent ...` → hook not used that way / path wrong. Harmless; iterate.
5. **Uninstall** — `macos/uninstall_sdboot_hook.command` → removes hook + payload + marker. Stock.

The ONE irreversible-by-battery-pull action is step 2's write to `/setting`. It is undone by step 5,
by a service-mode delete, or by a firmware update (see Recovery).

## Recovery (if the camera app ever misbehaves after step 3)
- **A: USB service delete.** `sen.elf` is up before the preload → connect and run the UNINSTALL
  level (or a direct `/setting/mode/preload` delete). Removes the hook.
- **B: a bad/missing payload is already ignored** by glibc — camera boots stock on its own.
- **C: firmware update.** The bootloader/UDM updater (BIS bootmode) runs independent of the main
  rootfs and reflashes — the ultimate backstop.

## Next step toward real SD-boot (only after this passes)
Replace the no-op payload with a loader that reads the SD card and re-applies the proven open-gate
libs (og2560/og57). Point `/setting/mode/preload` at a loader on the **SD card** so ejecting the
card becomes a hardware kill-switch.
