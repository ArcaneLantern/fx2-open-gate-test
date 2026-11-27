@echo off
rem FX2 (firmware 1.01): THE 3840x2560 OPEN GATE FOR A PAL-SET FX2 (fifth kit; WORKS on an FX2 set to PAL, GitHub issue 5): raw write buffer, the PAL sensor step P5 (mode 0x880, 25p), output size, encoder side with the MP4 headers, rear screen; then one read-only dump on MOVIE. XAVC S 4K, 25p (a PAL FX2's XAVC HS 4K is 50p only). Start from a cold boot on STILL.
rem WRITES into the camera's memory (not firmware, not settings). A cold boot (battery out for 10 seconds) returns it to stock. The power switch alone does NOT: it keeps the encoder step (a mixed state not to record in).
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python environment missing: run setup.cmd first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -I -B "tools\camera_tests\CT6_memory_read_check\fx2_apply.py" og2560 --pal %*
echo.
pause
