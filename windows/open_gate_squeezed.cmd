@echo off
rem FX2 (firmware 1.01): the squeezed open gate (ran on an FX2, 2026-11-26): the raw write buffer, the full-height sensor step and the rear-screen step, then one read-only dump on MOVIE. Records the whole 3:2 sensor area squeezed into a 3840x2160 file (stretch the height by 32/27 in the editor: 3840x2560). No output-size or encoder step. Start from a cold boot on STILL.
rem WRITES into the camera's memory (not firmware, not settings). A cold boot (battery out for 10 seconds) returns it to stock. The power switch alone does NOT: it keeps the encoder step (a mixed state not to record in).
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python environment missing: run setup.cmd first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -I -B "tools\camera_tests\CT6_memory_read_check\fx2_apply.py" squeeze %*
echo.
pause
