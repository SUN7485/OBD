#!/bin/bash

# Fleet OBD Backup Script
# Usage: ./scripts/backup.sh

set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_DIR:-./backups}"
DB_NAME="${DB_NAME:-fleet_obd}"
DB_USER="${DB_USER:-fleet_user}"

mkdir -p "$BACKUP_DIR"

echo "Starting backup at $TIMESTAMP..."

# Backup PostgreSQL
echo "Backing up database: $DB_NAME"
pg_dump -U "$DB_USER" -h localhost -Fc "$DB_NAME" > "$BACKUP_DIR/database_${TIMESTAMP}.dump"

# Optionally compress
if command -v gzip &> /dev/null; then
    gzip "$BACKUP_DIR/database_${TIMESTAMP}.dump"
    echo "Compressed backup to: database_${TIMESTAMP}.dump.gz"
else
    echo "Backup saved to: database_${TIMESTAMP}.dump"
fi

# Keep only last 7 backups
ls -t "$BACKUP_DIR"/database_*.dump* | tail -n +8 | xargs -r rm -f

echo "Backup complete!"