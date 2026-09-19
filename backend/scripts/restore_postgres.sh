#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL must be set}"
: "${BACKUP_FILE:?BACKUP_FILE must be set}"

pg_restore --clean --if-exists --no-owner --no-privileges   --dbname="$DATABASE_URL" "$BACKUP_FILE"

echo "Restore completed from $BACKUP_FILE"
