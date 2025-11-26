#!/bin/bash
#
# PostgreSQL Backup Script for OpenAlex Database
# Performs compressed database dumps with retention policy
#

set -e

# Configuration from environment variables
DB_HOST="${DB_HOST:-postgres}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-oadbv5}"
DB_USER="${DB_USER:-admin}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
RETENTION_WEEKS="${BACKUP_RETENTION_WEEKS:-4}"

# Generate timestamp for backup file
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.dump"
LOG_FILE="${BACKUP_DIR}/backup.log"

# Ensure backup directory exists
mkdir -p "${BACKUP_DIR}"

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

log "=========================================="
log "Starting PostgreSQL backup"
log "Database: ${DB_NAME}"
log "Host: ${DB_HOST}:${DB_PORT}"
log "=========================================="

# Check if PostgreSQL is accessible
if ! pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" > /dev/null 2>&1; then
    log "ERROR: PostgreSQL is not accessible at ${DB_HOST}:${DB_PORT}"
    exit 1
fi

log "PostgreSQL is accessible"

# Perform the backup
log "Creating backup: ${BACKUP_FILE}"
START_TIME=$(date +%s)

pg_dump -h "${DB_HOST}" \
        -p "${DB_PORT}" \
        -U "${DB_USER}" \
        -d "${DB_NAME}" \
        -F c \
        -b \
        -v \
        -f "${BACKUP_FILE}" 2>&1 | tee -a "${LOG_FILE}"

if [ ${PIPESTATUS[0]} -eq 0 ]; then
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)

    log "Backup completed successfully"
    log "Duration: ${DURATION} seconds"
    log "Size: ${BACKUP_SIZE}"
else
    log "ERROR: Backup failed"
    exit 1
fi

# Retention policy - Keep daily backups
log "Applying retention policy..."
log "Keeping last ${RETENTION_DAYS} daily backups"

# Find and delete backups older than retention period (daily backups)
find "${BACKUP_DIR}" -name "${DB_NAME}_*.dump" -type f -mtime +${RETENTION_DAYS} -delete 2>&1 | tee -a "${LOG_FILE}"

# Weekly backups - keep one backup per week
# On Sundays, create a copy for weekly retention
DAY_OF_WEEK=$(date +%u)  # 1=Monday, 7=Sunday
if [ "${DAY_OF_WEEK}" -eq 7 ]; then
    WEEKLY_BACKUP="${BACKUP_DIR}/${DB_NAME}_weekly_${TIMESTAMP}.dump"
    cp "${BACKUP_FILE}" "${WEEKLY_BACKUP}"
    log "Created weekly backup: ${WEEKLY_BACKUP}"

    # Delete weekly backups older than retention period
    RETENTION_WEEKS_DAYS=$((RETENTION_WEEKS * 7))
    find "${BACKUP_DIR}" -name "${DB_NAME}_weekly_*.dump" -type f -mtime +${RETENTION_WEEKS_DAYS} -delete 2>&1 | tee -a "${LOG_FILE}"
fi

# List current backups
log "Current backups:"
ls -lh "${BACKUP_DIR}"/*.dump 2>/dev/null | tee -a "${LOG_FILE}" || log "No backups found"

# Count backups
DAILY_COUNT=$(find "${BACKUP_DIR}" -name "${DB_NAME}_[0-9]*.dump" -type f | wc -l)
WEEKLY_COUNT=$(find "${BACKUP_DIR}" -name "${DB_NAME}_weekly_*.dump" -type f | wc -l)
log "Total daily backups: ${DAILY_COUNT}"
log "Total weekly backups: ${WEEKLY_COUNT}"

log "=========================================="
log "Backup process completed"
log "=========================================="

exit 0
