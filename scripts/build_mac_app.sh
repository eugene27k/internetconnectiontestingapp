#!/usr/bin/env bash
set -euo pipefail

APP_NAME="InternetConnectionTester"
DMG_NAME="${APP_NAME}.dmg"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$ROOT_DIR/dist"
STAGING_DIR="$DIST_DIR/${APP_NAME}-dmg"

if [[ "$(uname)" != "Darwin" ]]; then
  echo "This packaging script must be run on macOS." >&2
  exit 1
fi

if ! command -v pyinstaller >/dev/null 2>&1; then
  echo "pyinstaller is required. Install with: python3 -m pip install pyinstaller" >&2
  exit 1
fi

cd "$ROOT_DIR"

# Build the .app bundle using PyInstaller.
pyinstaller mac_app_main.py \
  --name "$APP_NAME" \
  --windowed \
  --noconfirm \
  --clean \
  --add-data "README.md:."

rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR"
cp -R "$DIST_DIR/${APP_NAME}.app" "$STAGING_DIR/"

cat > "$STAGING_DIR/README.txt" <<'NOTE'
Internet Connection Tester (macOS)
----------------------------------
Double-click the app to start monitoring. Session logs are saved under:
  ~/Library/Application Support/internetconnectiontestingapp/sessions

If macOS warns that the app is from an unidentified developer, you can right-click
and choose "Open" to bypass Gatekeeper for this build.
NOTE

hdiutil create -volname "$APP_NAME" -srcfolder "$STAGING_DIR" -ov -format UDZO "$DIST_DIR/$DMG_NAME"

echo "DMG created at: $DIST_DIR/$DMG_NAME"
