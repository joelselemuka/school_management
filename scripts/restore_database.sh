#!/bin/bash

###############################################################################
# Script de Restauration pour School Management System
# 
# Ce script restaure:
# 1. Base de données PostgreSQL
# 2. Fichiers media
# 3. Configuration
#
# Usage: ./restore_database.sh [backup_date]
# Exemple: ./restore_database.sh 20260311_030000
###############################################################################

# Configuration
PROJECT_DIR="/home/schoolapi/school-api"
BACKUP_DIR="/home/schoolapi/backups"

# Database
DB_NAME="${DB_NAME:-school_db}"
DB_USER="${DB_USER:-school_user}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# Lister les backups disponibles
list_backups() {
    log "Backups disponibles:"
    echo ""
    find "$BACKUP_DIR/database" -name "*.sql.gz" -exec basename {} \; | sort -r | head -10
    echo ""
}

# Confirmer la restauration
confirm_restore() {
    echo -e "${RED}⚠️  ATTENTION: Cette opération va écraser la base de données actuelle!${NC}"
    echo ""
    read -p "Voulez-vous continuer? (oui/non): " confirm
    
    if [ "$confirm" != "oui" ]; then
        log "Restauration annulée"
        exit 0
    fi
}

# Restaurer la base de données
restore_database() {
    local backup_date="$1"
    local db_backup="${BACKUP_DIR}/database/db_${backup_date}.sql.gz"
    
    if [ ! -f "$db_backup" ]; then
        error "Fichier de backup introuvable: $db_backup"
        exit 1
    fi
    
    log "Restauration de la base de données..."
    
    # Arrêter Django (optionnel)
    log "Arrêt de Django..."
    sudo systemctl stop gunicorn 2>/dev/null
    
    # Décompresser et restaurer
    gunzip -c "$db_backup" | PGPASSWORD="$DB_PASSWORD" pg_restore \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --clean \
        --if-exists
    
    if [ $? -ne 0 ]; then
        error "Échec de la restauration de la base de données"
        exit 1
    fi
    
    log "✓ Base de données restaurée"
}

# Restaurer les fichiers media
restore_media() {
    local backup_date="$1"
    local media_backup="${BACKUP_DIR}/media/media_${backup_date}.tar.gz"
    
    if [ ! -f "$media_backup" ]; then
        warning "Backup media introuvable, ignoré"
        return 0
    fi
    
    log "Restauration des fichiers media..."
    
    # Backup du media actuel
    if [ -d "$PROJECT_DIR/media" ]; then
        mv "$PROJECT_DIR/media" "$PROJECT_DIR/media.old.$(date +%s)"
    fi
    
    # Restaurer
    tar -xzf "$media_backup" -C "$PROJECT_DIR"
    
    if [ $? -ne 0 ]; then
        error "Échec de la restauration des fichiers media"
        return 1
    fi
    
    log "✓ Fichiers media restaurés"
}

# Main
main() {
    log "=== Restauration du backup ==="
    
    # Charger .env
    if [ -f "$PROJECT_DIR/.env" ]; then
        set -a
        source "$PROJECT_DIR/.env"
        set +a
    fi
    
    # Vérifier le paramètre
    if [ -z "$1" ]; then
        list_backups
        echo "Usage: $0 <backup_date>"
        echo "Exemple: $0 20260311_030000"
        exit 1
    fi
    
    local backup_date="$1"
    
    confirm_restore
    restore_database "$backup_date"
    restore_media "$backup_date"
    
    # Redémarrer Django
    log "Redémarrage de Django..."
    sudo systemctl start gunicorn
    
    log "=== Restauration terminée ==="
}

main "$@"
