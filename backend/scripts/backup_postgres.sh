#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL must be set}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP_DIR"

pg_dump --format=custom --no-owner --no-privileges "$DATABASE_URL"   > "$BACKUP_DIR/dermcareai-$TIMESTAMP.dump"

echo "Backup written to $BACKUP_DIR/dermcareai-$TIMESTAMP.dump"
