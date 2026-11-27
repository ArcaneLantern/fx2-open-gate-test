@echo off
rem FX2 (firmware 1.01): DIAGNOSTIC TEST 4 (third kit): test 3 plus the encoder side (the open gate without the screen step), then one read-only dump on MOVIE. Start from a cold boot on STILL.
rem WRITES into the camera's memory (not firmware, not settings). A cold boot (battery out for 10 seconds) returns it to stock. The power switch alone does NOT: it keeps the encoder step (a mixed state not to record in).
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python environment missing: run setup.cmd first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -I -B "tools\camera_tests\CT6_memory_read_check\fx2_apply.py" test4 %*
echo.
pause
