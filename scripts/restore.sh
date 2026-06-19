#!/bin/bash

# Fleet OBD Restore Script
# Usage: ./scripts/restore.sh <backup_file>

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file>"
    echo "Available backups:"
    ls -1 ./backups/database_*.dump* 2>/dev/null || echo "  No backups found"
    exit 1
fi

BACKUP_FILE="$1"
DB_NAME="${DB_NAME:-fleet_obd}"
DB_USER="${DB_USER:-fleet_user}"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "Restoring from: $BACKUP_FILE"
echo "Database: $DB_NAME"

# Drop existing database
echo "Dropping existing database..."
psql -U "$DB_USER" -h localhost -c "DROP DATABASE IF EXISTS $DB_NAME;"
psql -U "$DB_USER" -h localhost -c "CREATE DATABASE $DB_NAME;"

# Restore
echo "Restoring database..."
if [[ "$BACKUP_FILE" == *.gz ]]; then
    gunzip -c "$BACKUP_FILE" | pg_restore -U "$DB_USER" -h localhost -d "$DB_NAME"
else
    pg_restore -U "$DB_USER" -h localhost -d "$DB_NAME" "$BACKUP_FILE"
fi

echo "Restore complete!"