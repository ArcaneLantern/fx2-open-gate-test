@echo off
rem FX2 (firmware 1.01): THE 5760x3840 STATE WITH XAVC S-I 4K: open_gate_5760x3840_test plus one encoder step for XAVC S-I 4K at 5760x3840 (G19; works on an A7 IV at 24p). Start from a cold boot on STILL. NOT YET RUN ON AN FX2.
rem WRITES into the camera's memory (not firmware, not settings). A cold boot (battery out for 10 seconds) returns it to stock. The power switch alone does NOT: it keeps the encoder step (a mixed state not to record in).
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python environment missing: run setup.cmd first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -I -B "tools\camera_tests\CT6_memory_read_check\fx2_apply.py" og57si %*
echo.
pause
