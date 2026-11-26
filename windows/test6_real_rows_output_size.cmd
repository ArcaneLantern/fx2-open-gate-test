@echo off
rem FX2 (firmware 1.01): TEST 6 (fourth kit): test 5 plus the output size (3840x2560), then one read-only dump on MOVIE. Expected: a steady picture; a recording may stop after a second (no encoder step yet). SteadyShot Off. Start from a cold boot on STILL. NOT YET RUN ON AN FX2.
rem WRITES into the camera's memory (not firmware, not settings). A cold boot (battery out for 10 seconds) returns it to stock; whether the power switch alone does on the FX2 is not known.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python environment missing: run setup.cmd first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -I -B "tools\camera_tests\CT6_memory_read_check\fx2_apply.py" test6 %*
echo.
pause
