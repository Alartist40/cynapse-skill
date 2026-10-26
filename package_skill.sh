#!/usr/bin/env bash
# Package Cynapse Synaptic Memory for Agensi.io distribution
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo " Packaging Cynapse Synaptic Memory Skill  "
echo "=========================================="

# 1. Build optimized Rust binary
echo "[1/4] Compiling native Rust binary in release mode..."
cargo build --release
mkdir -p bin
cp target/release/cynapse-synaptic-memory bin/cynapse-synaptic-memory

# 2. Run automated test suite
echo "[2/4] Verifying binary execution..."
bin/cynapse-synaptic-memory stats

# 3. Create distribution zip
echo "[3/4] Creating distribution archive..."
rm -rf dist
mkdir -p dist
zip -r dist/cynapse-synaptic-memory.zip \
  SKILL.md \
  README.md \
  LICENSE \
  Cargo.toml \
  src/ \
  bin/cynapse-synaptic-memory \
  references/ \
  -x "*.git*" "*.DS_Store*" "target/*"

# 4. Report status
ZIP_SIZE=$(du -h dist/cynapse-synaptic-memory.zip | cut -f1)
echo "[4/4] Package ready: dist/cynapse-synaptic-memory.zip ($ZIP_SIZE)"
echo ""
echo "=========================================="
echo " Ready for Upload to Agensi.io            "
echo "=========================================="
echo "1. Go to: https://www.agensi.io/sell"
echo "2. Title: Cynapse Synaptic Memory"
echo "3. Description: 4-Tier Biological Memory for Claude Code, Cursor, Copilot"
echo "4. Upload File: dist/cynapse-synaptic-memory.zip"
echo "5. Pricing: Free (\$0) - 100% Free & Open-Source (Community Growth)"
echo "=========================================="
