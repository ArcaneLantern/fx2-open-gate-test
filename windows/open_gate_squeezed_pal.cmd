@echo off
rem FX2 (firmware 1.01): the squeezed open gate for a PAL-set FX2 (fifth kit): raw write buffer, the PAL sensor step Q5 (mode 0x880, 25p), rear screen; then one read-only dump on MOVIE. A 3840x2160 file holding the whole 3:2 sensor area squeezed (stretch by 32/27). Start from a cold boot on STILL. NOT YET RUN ON A CAMERA.
rem WRITES into the camera's memory (not firmware, not settings). A cold boot (battery out for 10 seconds) returns it to stock. The power switch alone does NOT: it keeps the encoder step (a mixed state not to record in).
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python environment missing: run setup.cmd first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -I -B "tools\camera_tests\CT6_memory_read_check\fx2_apply.py" squeeze --pal %*
echo.
pause
