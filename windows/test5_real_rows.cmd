@echo off
rem FX2 (firmware 1.01): TEST 5 (fourth kit): the raw write buffer and the sensor step H5, whose first scaler gives 4336x2560 (the A7 IV's ogh2560_v1), then one read-only dump on MOVIE. Expected: squeezed 3840x2160 clips, as test 2. SteadyShot Off. Start from a cold boot on STILL. NOT YET RUN ON AN FX2.
rem WRITES into the camera's memory (not firmware, not settings). A cold boot (battery out for 10 seconds) returns it to stock; whether the power switch alone does on the FX2 is not known.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python environment missing: run setup.cmd first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -I -B "tools\camera_tests\CT6_memory_read_check\fx2_apply.py" test5 %*
echo.
pause
