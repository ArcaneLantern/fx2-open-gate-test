# FX2 boot-time open-gate loader — design (2026-11-27, LOCAL)

## Proven foundation (hardware, 2026-11-27)
`/etc/ld.so.preload` on the FX2 (nflasha10, rw) loads an arbitrary library into processes at boot and
runs its constructor. Verified end-to-end: wrote the hook via the guarded Jiritsu path, power-cycled,
and a no-op marker library ran and left `/etc/fx2_preload_ran` (`marker_ran=YES`). The write survives a
battery pull; the camera booted normally; USB service came up (recovery reachable). This is a
persistent, runs-at-every-boot, battery-pull-proof code hook. The debug-gated `/setting/mode/preload`
path (in `bootin.elf`, behind `gdb --args` / "clearing env") does NOT fire in normal boot — dead end.

## The goal
At boot, with no laptop, bring the camera up already recording open gate (3840×2560 or 5.7K), with a
simple on/off (ideally: SD card present = on, card out = stock).

## The gap between "a library runs at boot" and "open gate is applied"
Today the open gate is applied over USB **service mode** (Senser): the kit uploads `libJit` libraries
that run in the camera and write coprocessor RAM via `/dev/mem` (the pinned site lists of L13/H5/K5,
L16/K16, L19/K19, S16), then the user flips STILL→MOVIE so the imaging pipeline re-reads the patched
values. A boot-time preload has **no service-mode context and the wrong timing**: its constructor runs
when the process *starts*, before imaging init. So the loader must do three new things:

1. **Target the right process.** `/etc/ld.so.preload` is global. The loader's constructor must check
   its own identity (`/proc/self/comm` or `argv[0]`) and act only inside the imaging app (`im.elf`);
   in every other process it returns immediately (stays a pure no-op).
2. **Act at the right time, not at constructor time.** The site writes must land after imaging init
   and be picked up by the pipeline. Options, cheapest first:
   - a) **Watcher thread**: the constructor spawns a thread that waits for a readiness signal (a file/
        sysfs node, or the drive-mode register reaching the movie state) then applies the sites — same
        trigger the STILL→MOVIE switch gives today.
   - b) **Function hook**: interpose a libc/imaging symbol called once imaging is up, apply there.
   - c) Re-use the firmware's own `/setting/mode/*` or a Senser-style path to request a re-init.
3. **Replicate the kit's `/dev/mem` site writes.** Embed the pinned open-gate designs and write the
   same physical sites (coprocessor RAM 0x4xxxxxxxx + the memory-manager words). This is porting the
   L/H/K/L16/L19/S16 bodies out of the Jiritsu-delivered `libJit` into a self-triggering boot library.

## Hard problems / unknowns (to settle in emulation first)
- **Trigger point**: which readable signal means "imaging is up and about to enter movie"? (A watcher
  polling the drive-mode shadow, as the dumps read it, is the most self-contained.)
- **Re-apply vs one-shot**: the pipeline may re-init on mode/format changes (it does on 60p). The
  loader likely must re-apply on each movie-entry, like a resident agent, not once.
- **Which state to apply**: read it from the SD card (a small text file) so one build serves
  og2560 / og57 / squeezed, and **card-out = nothing to apply = stock** (hardware kill-switch).
- **Safety of a resident `/dev/mem` writer** running every boot inside im.elf: must fail closed (if any
  precheck — firmware hash, drive mode, site stock-check — is off, do nothing), exactly like the kit's
  guards, since there is no USB operator watching.

## Incremental, safe milestones (each proven in Unicorn/QEMU before hardware)
1. **Process-targeted no-op**: the preload acts only in `im.elf` (writes the marker only there). Proves
   targeting. (Low risk, builds on today's result.)
2. **One benign site at the right time**: watcher thread applies a single, reversible, harmless
   coprocessor write after movie-entry, and a dump confirms it took. Proves timing + `/dev/mem` from a
   boot library.
3. **One real open-gate step** (e.g. the screen step S16 only) at boot, dump-verified.
4. **Full og2560/og57** at boot, with the SD-card state file + card-out kill-switch.
Each step keeps the kill-switch (remove the SD card, or `/etc/fx2_preload_disable`) and the three
recovery layers (uninstall, service-mode delete, firmware update).

## MILESTONE 1 RESULT (2026-11-27, hardware): the camera app is ISOLATED from /etc/ld.so.preload
A process-aware marker (writes `/etc/fx2in_<comm>` per process) was installed, the camera power-cycled,
and the full process list read back (getdents). `/etc/ld.so.preload` loaded into these **boot-time
system processes**: `pam_tally2 cp startBTCore.sh pidof btproperty.elf get_finger_prin cat grep
ssh-keygen wcnssfilter.elf` — the Bluetooth/wireless/auth init phase. **`im.elf` (the camera app) was
NOT among them.** So the camera app runs in a separate mount namespace / chroot where our root-namespace
`/etc/ld.so.preload` is invisible. `im.elf` itself IS glibc-dynamic (interp `/lib/ld-linux-aarch64.so.1`
= ld-2.25.so, which honors ld.so.preload) — so the block is the namespace boundary, not the linker.

**Consequence:** `/etc/ld.so.preload` cannot directly inject into `im.elf`. The hosts it DOES reach are
mostly short-lived helpers (cp/grep/cat/pidof/ssh-keygen) — poor for a resident watcher; `btproperty.elf`
/ `wcnssfilter.elf` may be daemons worth checking.

**Forward options (all deeper RE):**
- **A. Find im.elf's root.** RE how `bootin.elf`/init launches `im.elf` (chroot / pivot_root / unshare)
  and write `ld.so.preload` in the `/etc` that im.elf actually sees.
- **B. /dev/mem watcher in a root-namespace daemon.** Applying the open gate needs `/dev/mem` + the right
  timing, not necessarily im.elf's address space. A preload in a long-lived root process (e.g.
  `wcnssfilter.elf` if it is a daemon) could host a thread that waits for movie-entry and writes the
  sites. Needs a reliable long-lived host and is fragile.
- **C. Writable boot script.** `startBTCore.sh` is a shell script in the boot path; if it (or anything it
  sources) lives on a writable partition, a line could be added — but the rootfs is ro, so unlikely.

## Honest assessment
The persistence problem is solved. The remaining work — a resident, self-triggering, fail-closed
`/dev/mem` applier inside im.elf — is a real RE/engineering project (author-level), best done in the
emulator first. The **Pi dongle remains the zero-brick-risk "no laptop" answer today**; this loader is
the elegant end-state, now that boot-time execution is proven.
