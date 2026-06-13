#!/usr/bin/env bash
# Build CPIS JSON Gate v1.2 distribution ZIP
#
# Usage: bash scripts/build-zip.sh
#
# Creates: openclaw-plugins/cpis-json-gate/dist/cpis-json-gate-v1.2.0.zip

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PLUGIN_DIR="$PROJECT_DIR/openclaw-plugins/cpis-json-gate"
VERSION="1.2.0"
OUTPUT="$PLUGIN_DIR/dist/cpis-json-gate-v${VERSION}.zip"

echo "Building CPIS JSON Gate v${VERSION}..."

cd "$PLUGIN_DIR"

# Run tests first
echo "--- Running tests ---"
npm test 2>&1 || { echo "FAIL: tests failed"; exit 1; }
echo ""

# Create temp build directory
BUILD_DIR="$(mktemp -d)"
trap 'rm -rf "$BUILD_DIR"' EXIT

# Copy plugin files
cp -a dist package.json openclaw.plugin.json "$BUILD_DIR/"

# Create zip
cd "$BUILD_DIR"
rm -f "$OUTPUT"
zip -r "$OUTPUT" . -x "*.map"
cd "$PLUGIN_DIR"

echo "--- Created: $OUTPUT ---"
ls -lh "$OUTPUT"
echo ""
echo "Done."
