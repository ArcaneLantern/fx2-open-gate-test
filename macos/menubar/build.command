#!/bin/bash
# Builds "FX2 Open Gate.app" (the menu bar launcher) from main.swift, into the kit's macos/ folder.
# Re-run it after you move the kit, or edit main.swift. Needs the Xcode command line tools (swiftc).
set -e
cd "$(dirname "$0")"
BUILD_DIR="$(pwd)"
KITMACOS="$(dirname "$BUILD_DIR")"                      # the folder with arm_open_gate.command etc.
APP="$KITMACOS/FX2 Open Gate.app"
EXE="FX2OpenGate"
# Signing identity: $FX2_SIGN_ID, else the first "Apple Development" identity in the keychain, else ad-hoc.
ID="${FX2_SIGN_ID:-$(security find-identity -v -p codesigning 2>/dev/null | sed -n 's/.*"\(Apple Development: [^"]*\)".*/\1/p' | head -1)}"

echo "Launchers folder baked in: $KITMACOS"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS"

# Bake the launcher folder path into a copy of the source.
python3 - "$BUILD_DIR/main.swift" "$BUILD_DIR/.main_baked.swift" "$KITMACOS" <<'PY'
import sys
src, dst, kit = sys.argv[1], sys.argv[2], sys.argv[3]
open(dst, "w").write(open(src).read().replace("__KITMACOS__", kit))
PY

swiftc -O -target arm64-apple-macos12.0 "$BUILD_DIR/.main_baked.swift" \
  -o "$APP/Contents/MacOS/$EXE" -framework AppKit
rm -f "$BUILD_DIR/.main_baked.swift"

cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>FX2 Open Gate</string>
  <key>CFBundleDisplayName</key><string>FX2 Open Gate</string>
  <key>CFBundleIdentifier</key><string>com.isaiah.fx2opengate</string>
  <key>CFBundleExecutable</key><string>$EXE</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>CFBundleVersion</key><string>1</string>
  <key>LSUIElement</key><true/>
  <key>LSMinimumSystemVersion</key><string>12.0</string>
  <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
PLIST

if [ -n "$ID" ] && security find-identity -v -p codesigning 2>/dev/null | grep -qF "$ID"; then
  codesign --force --options runtime --sign "$ID" "$APP" && echo "Signed with your Apple Development identity."
else
  codesign --force --sign - "$APP" && echo "Ad-hoc signed (no Apple Development identity found)."
fi

echo "Built: $APP"
