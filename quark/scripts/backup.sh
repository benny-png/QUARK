#!/bin/bash

# Configuration
BACKUP_DIR="/opt/quark/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_CONTAINER="quark_db_1"
DB_NAME="quark"
DB_USER="user"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Backup PostgreSQL database
echo "Backing up PostgreSQL database..."
docker exec $DB_CONTAINER pg_dump -U $DB_USER $DB_NAME > "$BACKUP_DIR/db_backup_$TIMESTAMP.sql"

# Backup Nginx configurations
echo "Backing up Nginx configurations..."
tar -czf "$BACKUP_DIR/nginx_conf_$TIMESTAMP.tar.gz" /etc/nginx/sites-enabled/

# Backup application data
echo "Backing up application data..."
tar -czf "$BACKUP_DIR/app_data_$TIMESTAMP.tar.gz" /opt/quark/data/

# Clean up old backups (keep last 7 days)
find "$BACKUP_DIR" -type f -mtime +7 -delete

echo "Backup completed successfully!" 