#!/bin/bash
# ==============================================================================
# Arcwright - Qdrant Vector DB Backup Script
#
# Run this script to package the Qdrant storage folder so it can be 
# uploaded to Google Drive and shared across devices without re-embedding.
# 
# Usage: 
#   sudo ./backup_db.sh
# ==============================================================================

set -e

BACKUP_FILE="qdrant_storage_backup.tar.gz"

echo "🛑 Stopping Qdrant container..."
docker stop arcwright_qdrant || true

echo "📦 Compressing qdrant_storage/ to $BACKUP_FILE..."
# We use sudo here in case docker files are owned by root
tar -czvf "$BACKUP_FILE" qdrant_storage/

echo "▶️ Restarting Qdrant container..."
docker start arcwright_qdrant

echo "✅ Backup complete! You can now upload $BACKUP_FILE to Google Drive."
echo "   To restore on a new machine:"
echo "   1. Download $BACKUP_FILE"
echo "   2. Run: tar -xzvf $BACKUP_FILE"
echo "   3. Run: docker compose up -d"
