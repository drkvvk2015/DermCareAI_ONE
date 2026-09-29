#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL must be set}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP_DIR"

BACKUP_FILE="$BACKUP_DIR/dermcareai-$TIMESTAMP.dump"
pg_dump --format=custom --no-owner --no-privileges "$DATABASE_URL" > "$BACKUP_FILE"
test -s "$BACKUP_FILE"
pg_restore --list "$BACKUP_FILE" >/dev/null

echo "Backup written and verified: $BACKUP_FILE"
