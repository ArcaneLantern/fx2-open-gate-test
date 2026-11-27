@echo off
rem FX2 (firmware 1.01): THE 5760x3840 (5.7K) TEST FOR A PAL-SET FX2: as open_gate_5760x3840_test with the PAL sensor step J5 (mode 0x880). XAVC S 4K, 25p. SteadyShot Off. A V90 SD card or CFexpress Type A. Start from a cold boot on STILL. NOT YET RUN ON AN FX2.
rem WRITES into the camera's memory (not firmware, not settings). A cold boot (battery out for 10 seconds) returns it to stock. The power switch alone does NOT: it keeps the encoder step (a mixed state not to record in).
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python environment missing: run setup.cmd first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -I -B "tools\camera_tests\CT6_memory_read_check\fx2_apply.py" og57 --pal %*
echo.
pause
