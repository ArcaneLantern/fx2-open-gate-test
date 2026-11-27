@echo off
rem FX2 (firmware 1.01): THE 3840x2560 OPEN GATE WITH XAVC S-I 4K: open_gate_3840x2560_test plus one encoder step for XAVC S-I 4K (AVC intra 4:2:2 10-bit) at 3840x2560 (I19). 23.98p (PAL: 25p). Start from a cold boot on STILL. The S-I step is NOT YET RUN ON AN FX2.
rem WRITES into the camera's memory (not firmware, not settings). A cold boot (battery out for 10 seconds) returns it to stock. The power switch alone does NOT: it keeps the encoder step (a mixed state not to record in).
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python environment missing: run setup.cmd first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -I -B "tools\camera_tests\CT6_memory_read_check\fx2_apply.py" og2560si %*
echo.
pause
