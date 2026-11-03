#!/usr/bin/env bash
# Install the discord-admin skill into a Hermes data dir.
#   bash install-discord-admin.sh [--force]
set -euo pipefail
DATA_DIR="${HERMES_DATA:-/opt/hermes/data}"
SRC="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$DATA_DIR/skills/discord-admin"

mkdir -p "$DEST"
cp "$SRC/SKILL.md" "$DEST/SKILL.md"
mkdir -p "$DEST/scripts"
cp "$SRC/scripts/discord_admin.py" "$DEST/scripts/discord_admin.py"
chmod +x "$DEST/scripts/discord_admin.py"
chown -R 10000:10000 "$DEST" 2>/dev/null || true

echo "installed: $DEST"
echo "try:  docker exec hermes python3 /opt/data/skills/discord-admin/scripts/discord_admin.py diag --guild \$DISCORD_GUILD_ID"
