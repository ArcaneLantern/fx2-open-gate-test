@echo off
rem FX2 (firmware 1.01): THE 5760x3840 (5.7K) TEST: raw write buffer, the sensor step K5 (first scaler 5760x3840), four scaler units with a 30.8 MB output buffer and the output size 5760x3840 (K16), the encoder side at 300 Mbps on the 100M+ settings with I and P pictures only and the MP4 headers at 5760x3840 (K19), rear screen; then one read-only dump on MOVIE. XAVC HS 4K or XAVC S 4K, 23.98p; on a PAL-set camera the PAL step J5 and XAVC S 4K 25p. SteadyShot Off. A V90 SD card or CFexpress Type A. Start from a cold boot on STILL. NOT YET RUN ON AN FX2 (the A7 IV records 5760x3840 with these steps).
rem WRITES into the camera's memory (not firmware, not settings). A cold boot (battery out for 10 seconds) returns it to stock. The power switch alone does NOT: it keeps the encoder step (a mixed state not to record in).
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python environment missing: run setup.cmd first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -I -B "tools\camera_tests\CT6_memory_read_check\fx2_apply.py" og57 %*
echo.
pause
