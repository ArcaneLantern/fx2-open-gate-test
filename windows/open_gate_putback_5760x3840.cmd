@echo off
rem FX2 (firmware 1.01): put back the 5760x3840 (5.7K) state without a cold boot: screen, encoder side, output side, sensor step, raw write buffer (NTSC or PAL as the newest check reads it).
rem WRITES into the camera's memory (not firmware, not settings). A cold boot (battery out for 10 seconds) returns it to stock. The power switch alone does NOT: it keeps the encoder step (a mixed state not to record in).
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python environment missing: run setup.cmd first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -I -B "tools\camera_tests\CT6_memory_read_check\fx2_apply.py" putback-57 %*
echo.
pause
