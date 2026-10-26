#!/usr/bin/env bash
# Package Cynapse Synaptic Memory for Agensi.io distribution
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo " Packaging Cynapse Synaptic Memory Skill  "
echo "=========================================="

# 1. Run automated tests
echo "[1/4] Running unit tests..."
python3 tests/test_synapse_memory.py

# 2. Clean cache files
echo "[2/4] Cleaning pycache and temporary files..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
rm -rf dist
mkdir -p dist

# 3. Create distribution zip
echo "[3/4] Creating distribution archive..."
zip -r dist/cynapse-synaptic-memory.zip \
  SKILL.md \
  README.md \
  LICENSE \
  scripts/ \
  references/ \
  tests/ \
  -x "*.git*" "*.DS_Store*" "*__pycache__*"

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
echo "5. Pricing Recommendation: Free (Lead Magnet) or \$19 (Pro)"
echo "=========================================="
