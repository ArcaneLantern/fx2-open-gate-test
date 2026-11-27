#!/bin/bash
# FX2 5.7K (5760x3840, 300 Mbps) in ONE connection (LOCAL, 2026-11-27): open_gate_fast.command with plan og57 (check + L13 K5 K16 K19 S16).
# The same pinned steps as open_gate_5760x3840_test.command, which ran on this FX2 2026-11-27 (clips 0455/0456).
# Before: XAVC HS 4K or XAVC S 4K 23.98p, 100M+ bit rate, SteadyShot Off, V90 SD or CFexpress A. After: no in-camera playback of 5.7K clips.
FX2_PLAN=og57 exec "$(dirname "$0")/open_gate_fast.command"
