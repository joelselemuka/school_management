#!/bin/bash

###############################################################################
# Script de Backup Automatique pour School Management System
# 
# Ce script effectue:
# 1. Dump PostgreSQL
# 2. Backup fichiers media
# 3. Backup configuration (.env)
# 4. Compression des backups
# 5. Upload vers stockage cloud (optionnel)
# 6. Nettoyage des anciens backups (>30 jours)
# 7. Notification email en cas d'erreur
#
# Usage: ./backup_database.sh
# Cron: 0 3 * * * /path/to/backup_database.sh
###############################################################################

# Configuration
PROJECT_DIR="/home/schoolapi/school-api"
BACKUP_DIR="/home/schoolapi/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Database
DB_NAME="${DB_NAME:-school_db}"
DB_USER="${DB_USER:-school_user}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

# S3/Cloud (optionnel)
USE_S3=${USE_S3:-false}
S3_BUCKET=${S3_BUCKET:-""}
S3_REGION=${S3_REGION:-"eu-west-1"}

# Notification
NOTIFY_EMAIL=${NOTIFY_EMAIL:-"admin@school.com"}
NOTIFY_ON_SUCCESS=${NOTIFY_ON_SUCCESS:-false}

# Couleurs pour logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# Fonction de notification email
send_notification() {
    local subject="$1"
    local message="$2"
    
    if command -v mail &> /dev/null; then
        echo "$message" | mail -s "$subject" "$NOTIFY_EMAIL"
    fi
}

# Vérifier les dépendances
check_dependencies() {
    log "Vérification des dépendances..."
    
    local missing_deps=()
    
    if ! command -v pg_dump &> /dev/null; then
        missing_deps+=("postgresql-client")
    fi
    
    if ! command -v gzip &> /dev/null; then
        missing_deps+=("gzip")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        error "Dépendances manquantes: ${missing_deps[*]}"
        error "Installez avec: sudo apt install ${missing_deps[*]}"
        exit 1
    fi
    
    log "✓ Toutes les dépendances sont présentes"
}

# Créer les répertoires de backup
create_backup_dirs() {
    log "Création des répertoires de backup..."
    
    mkdir -p "$BACKUP_DIR"/{database,media,config}
    
    if [ $? -ne 0 ]; then
        error "Impossible de créer les répertoires de backup"
        exit 1
    fi
    
    log "✓ Répertoires créés"
}

# Backup PostgreSQL
backup_database() {
    log "Backup de la base de données PostgreSQL..."
    
    local db_backup_file="$BACKUP_DIR/database/db_${DATE}.sql"
    
    # Dump de la base
    PGPASSWORD="$DB_PASSWORD" pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -F c \
        -f "$db_backup_file"
    
    if [ $? -ne 0 ]; then
        error "Échec du backup de la base de données"
        send_notification "⚠️ Backup Failed" "Le backup de la base de données a échoué"
        exit 1
    fi
    
    # Compression
    gzip -f "$db_backup_file"
    
    local db_size=$(du -h "${db_backup_file}.gz" | cut -f1)
    log "✓ Base de données sauvegardée (${db_size})"
}

# Backup des fichiers media
backup_media() {
    log "Backup des fichiers media..."
    
    local media_dir="$PROJECT_DIR/media"
    local media_backup_file="$BACKUP_DIR/media/media_${DATE}.tar.gz"
    
    if [ ! -d "$media_dir" ]; then
        warning "Répertoire media introuvable, ignoré"
        return 0
    fi
    
    # Créer l'archive
    tar -czf "$media_backup_file" -C "$PROJECT_DIR" media/
    
    if [ $? -ne 0 ]; then
        error "Échec du backup des fichiers media"
        return 1
    fi
    
    local media_size=$(du -h "$media_backup_file" | cut -f1)
    log "✓ Fichiers media sauvegardés (${media_size})"
}

# Backup de la configuration
backup_config() {
    log "Backup de la configuration..."
    
    local config_backup_file="$BACKUP_DIR/config/config_${DATE}.tar.gz"
    
    # Sauvegarder .env et fichiers de config
    tar -czf "$config_backup_file" \
        -C "$PROJECT_DIR" \
        .env \
        config/settings/ \
        2>/dev/null
    
    if [ $? -ne 0 ]; then
        warning "Backup de configuration partiel ou échoué"
        return 1
    fi
    
    log "✓ Configuration sauvegardée"
}

# Upload vers S3/Cloud (optionnel)
upload_to_cloud() {
    if [ "$USE_S3" != "true" ]; then
        return 0
    fi
    
    log "Upload vers S3..."
    
    if ! command -v aws &> /dev/null; then
        warning "AWS CLI non installé, upload S3 ignoré"
        return 1
    fi
    
    # Upload database backup
    aws s3 cp \
        "$BACKUP_DIR/database/db_${DATE}.sql.gz" \
        "s3://${S3_BUCKET}/backups/database/" \
        --region "$S3_REGION"
    
    # Upload media backup
    aws s3 cp \
        "$BACKUP_DIR/media/media_${DATE}.tar.gz" \
        "s3://${S3_BUCKET}/backups/media/" \
        --region "$S3_REGION"
    
    # Upload config backup
    aws s3 cp \
        "$BACKUP_DIR/config/config_${DATE}.tar.gz" \
        "s3://${S3_BUCKET}/backups/config/" \
        --region "$S3_REGION"
    
    log "✓ Backups uploadés vers S3"
}

# Nettoyage des anciens backups
cleanup_old_backups() {
    log "Nettoyage des backups anciens (>${RETENTION_DAYS} jours)..."
    
    # Supprimer les backups de plus de X jours
    find "$BACKUP_DIR/database" -name "*.sql.gz" -mtime +${RETENTION_DAYS} -delete
    find "$BACKUP_DIR/media" -name "*.tar.gz" -mtime +${RETENTION_DAYS} -delete
    find "$BACKUP_DIR/config" -name "*.tar.gz" -mtime +${RETENTION_DAYS} -delete
    
    log "✓ Anciens backups supprimés"
}

# Vérification de l'intégrité du backup
verify_backup() {
    log "Vérification de l'intégrité..."
    
    local db_backup="${BACKUP_DIR}/database/db_${DATE}.sql.gz"
    
    # Tester la décompression
    gzip -t "$db_backup"
    
    if [ $? -ne 0 ]; then
        error "Le backup de la base de données est corrompu!"
        send_notification "⚠️ Backup Corrupted" "Le backup du $(date) est corrompu"
        exit 1
    fi
    
    log "✓ Intégrité vérifiée"
}

# Statistiques du backup
show_stats() {
    log "Statistiques du backup:"
    
    local db_size=$(du -sh "$BACKUP_DIR/database" | cut -f1)
    local media_size=$(du -sh "$BACKUP_DIR/media" | cut -f1)
    local total_size=$(du -sh "$BACKUP_DIR" | cut -f1)
    local backup_count=$(find "$BACKUP_DIR" -name "*.gz" -o -name "*.tar.gz" | wc -l)
    
    echo "  Database:  $db_size"
    echo "  Media:     $media_size"
    echo "  Total:     $total_size"
    echo "  Fichiers:  $backup_count"
}

# Main execution
main() {
    log "=== Début du backup ==="
    log "Date: $(date)"
    log "Projet: $PROJECT_DIR"
    log "Backup dir: $BACKUP_DIR"
    echo ""
    
    # Charger les variables d'environnement
    if [ -f "$PROJECT_DIR/.env" ]; then
        set -a
        source "$PROJECT_DIR/.env"
        set +a
    fi
    
    # Exécution
    check_dependencies
    create_backup_dirs
    backup_database
    backup_media
    backup_config
    verify_backup
    upload_to_cloud
    cleanup_old_backups
    
    echo ""
    show_stats
    echo ""
    log "=== Backup terminé avec succès ==="
    
    # Notification de succès (optionnel)
    if [ "$NOTIFY_ON_SUCCESS" = "true" ]; then
        send_notification "✅ Backup Success" "Backup du $(date) effectué avec succès"
    fi
    
    exit 0
}

# Trap pour gérer les erreurs
trap 'error "Script interrompu"; exit 1' INT TERM

# Exécuter le main
main "$@"
