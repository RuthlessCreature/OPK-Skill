#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-}"
if [[ -z "$TARGET" ]]; then
  cat <<'EOF'
Usage:
  ./install.sh <skill-directory>

Examples:
  ./install.sh ~/.codex/skills/opk
  ./install.sh .claude/skills/opk
  ./install.sh .agents/skills/opk
EOF
  exit 2
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$TARGET/scripts"
cp "$ROOT/SKILL.md" "$TARGET/SKILL.md"
cp "$ROOT/scripts/opk.py" "$TARGET/scripts/opk.py"
chmod +x "$TARGET/scripts/opk.py"

echo "Installed OPK Skill to: $TARGET"
echo "Next: export OPK_API_KEY='<your-key>'"
