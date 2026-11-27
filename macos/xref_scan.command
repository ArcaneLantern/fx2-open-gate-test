#!/bin/bash
# FX2 1.01 (LOCAL, 2026-11-28): READ-ONLY. The xref scan of the coprocessor code (who calls the display functions) in eleven parts, in one
# service connection (fx2_batch.py plan xrefscan: check + xref01..xref11). Nothing in the camera's memory or settings is changed.
# Camera on STILL or MOVIE, USB in (Mass Storage). The results go to windows/camera_private (newest folder).
cd "$(dirname "$0")" || exit 1
PY="$PWD/.venv/bin/python"
TOOLS="$PWD/../windows/tools/camera_tests/CT6_memory_read_check"
PRIVATE="$PWD/../windows/camera_private"
done_() { echo; read -r -p "Press Return to close. "; exit "$1"; }
[ -x "$PY" ] || { echo "Python environment missing: run setup.command first."; done_ 1; }
"$PY" -I -B "$TOOLS/fx2_batch.py" xrefscan --dry-run >/dev/null || { echo "!! The offline checks failed. Nothing was sent."; done_ 1; }
echo "Read-only xref scan in one connection. Your Mac password, once:"
sudo /bin/bash -c '
  trap : INT
  PY=$1; TOOLS=$2; PRIVATE=$3
  "$PY" -I -B "$TOOLS/fx2_batch.py" xrefscan --go --firmware-shown 1.01
  status=$?
  [ -d "$PRIVATE" ] && chown -R "$SUDO_UID:$SUDO_GID" "$PRIVATE"
  exit $status' go "$PY" "$TOOLS" "$PRIVATE"
done_ $?
