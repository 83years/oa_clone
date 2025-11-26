# Backup and Restore Procedures

## Automated Backup System

### Overview

The backup container runs automated PostgreSQL backups daily at 2 AM UTC with the following retention policy:
- **Daily backups**: Keep last 7 days
- **Weekly backups**: Keep last 4 weeks (created on Sundays)

### Backup Location

**On NAS**: `/volume2/postgres_backup/` (slower HDD storage)

**In Container**: `/backups/`

**Access from Mac** (if SMB mounted): `/Volumes/openalex_backups/`

### Backup Format

- Format: PostgreSQL custom format (`.dump`)
- Compressed: Yes
- Includes: All tables, data, and schema
- Excludes: Logs and temporary data

### Checking Backup Status

```bash
# View backup logs
docker-compose exec backup cat /backups/backup.log

# List all backups
docker-compose exec backup ls -lh /backups/*.dump

# Count backups
docker-compose exec backup sh -c "
  echo 'Daily backups:' && find /backups -name 'oadbv5_[0-9]*.dump' | wc -l
  echo 'Weekly backups:' && find /backups -name 'oadbv5_weekly_*.dump' | wc -l
"

# Check latest backup
docker-compose exec backup ls -lt /backups/*.dump | head -1
```

## Manual Backup

### Full Database Backup

```bash
# Execute manual backup
docker-compose exec backup /backup.sh

# Or from PostgreSQL container directly
docker-compose exec postgres pg_dump -U admin -d oadbv5 -F c -f /tmp/manual_backup.dump

# Copy from container to NAS
docker cp openalex_postgres:/tmp/manual_backup.dump /volume1/docker/openalex/backups/
```

### Backup Specific Tables

```bash
# Backup only works table
docker-compose exec postgres pg_dump -U admin -d oadbv5 -F c -t works -f /tmp/works_backup.dump

# Backup multiple tables
docker-compose exec postgres pg_dump -U admin -d oadbv5 -F c -t authors -t works -t authorship -f /tmp/partial_backup.dump
```

### Schema-Only Backup

```bash
# Backup schema without data
docker-compose exec postgres pg_dump -U admin -d oadbv5 -F c -s -f /tmp/schema_only.dump
```

### SQL Format Backup

```bash
# Plain SQL format (for version control or manual review)
docker-compose exec postgres pg_dump -U admin -d oadbv5 -F p -f /tmp/backup.sql
```

## Restore Procedures

### Full Database Restore

#### Method 1: Restore to New Database

```bash
# 1. Create new empty database
docker-compose exec postgres psql -U admin -c "CREATE DATABASE oadbv5_restored;"

# 2. Restore from backup
docker-compose exec postgres pg_restore -U admin -d oadbv5_restored -v /backups/oadbv5_YYYYMMDD_HHMMSS.dump

# 3. Verify restoration
docker-compose exec postgres psql -U admin -d oadbv5_restored -c "\dt"
docker-compose exec postgres psql -U admin -d oadbv5_restored -c "SELECT COUNT(*) FROM works;"

# 4. If successful, switch databases (optional)
# Stop all services first
docker-compose down

# Update .env file: DB_NAME=oadbv5_restored
# Then restart
docker-compose up -d
```

#### Method 2: Restore Over Existing Database

**WARNING**: This deletes all existing data!

```bash
# 1. Stop parser and backup services
docker-compose stop parser backup

# 2. Terminate all connections to database
docker-compose exec postgres psql -U admin -c "
  SELECT pg_terminate_backend(pid)
  FROM pg_stat_activity
  WHERE datname = 'oadbv5' AND pid <> pg_backend_pid();
"

# 3. Drop and recreate database
docker-compose exec postgres psql -U admin -c "DROP DATABASE IF EXISTS oadbv5;"
docker-compose exec postgres psql -U admin -c "CREATE DATABASE oadbv5 OWNER admin;"

# 4. Restore from backup
docker-compose exec postgres pg_restore -U admin -d oadbv5 -v /backups/oadbv5_YYYYMMDD_HHMMSS.dump

# 5. Restart all services
docker-compose restart
```

### Partial Restore (Specific Tables)

```bash
# Restore only specific tables
docker-compose exec postgres pg_restore -U admin -d oadbv5 -t authors -t works /backups/oadbv5_YYYYMMDD_HHMMSS.dump

# Restore and clean (drop existing data first)
docker-compose exec postgres pg_restore -U admin -d oadbv5 -t works --clean /backups/oadbv5_YYYYMMDD_HHMMSS.dump
```

### Restore from Remote Location

```bash
# Copy backup from Mac to NAS
scp /path/to/backup.dump admin@192.168.1.162:/volume1/docker/openalex/backups/

# Or copy into running container
docker cp /path/to/backup.dump openalex_postgres:/tmp/backup.dump

# Then restore
docker-compose exec postgres pg_restore -U admin -d oadbv5 /tmp/backup.dump
```

## Disaster Recovery

### Complete System Rebuild

If NAS fails completely:

#### 1. Set Up New NAS
```bash
# Create directories
mkdir -p /volume1/docker/openalex/{pg_data,logs,state}
mkdir -p /volume2/postgres_backup

# Transfer repository
rsync -avz -e "ssh -p 86" OA_clone/ claude@192.168.1.162:/volume1/docker/openalex/OA_clone/
```

#### 2. Restore Backups
```bash
# Copy backups to new NAS (if stored elsewhere)
scp -P 86 -r /backup/location/* claude@192.168.1.162:/volume2/postgres_backup/
```

#### 3. Deploy Containers
```bash
cd /volume1/docker/openalex/OA_clone
docker-compose build
docker-compose up -d postgres
```

#### 4. Restore Database
```bash
# Create database
docker-compose exec postgres psql -U admin -c "CREATE DATABASE oadbv5 OWNER admin;"

# Restore latest backup
LATEST_BACKUP=$(docker-compose exec backup ls -t /backups/oadbv5_*.dump | head -1)
docker-compose exec postgres pg_restore -U admin -d oadbv5 -v $LATEST_BACKUP
```

#### 5. Start All Services
```bash
docker-compose up -d
```

### Point-in-Time Recovery

PostgreSQL custom format backups represent database state at backup time. For point-in-time recovery:

1. **Restore to closest backup before desired time**
2. **Replay transactions** (requires WAL archiving - not currently enabled)

To enable WAL archiving for PITR:
```sql
-- Update postgresql.conf
archive_mode = on
archive_command = 'cp %p /backups/wal/%f'
wal_level = replica
```

## Backup Testing

### Monthly Backup Test

Perform monthly to ensure backups are valid:

```bash
#!/bin/bash
# backup_test.sh

echo "=== Backup Validation Test ==="

# Get latest backup
LATEST=$(docker-compose exec backup ls -t /backups/oadbv5_[0-9]*.dump | head -1)
echo "Testing backup: $LATEST"

# Create test database
docker-compose exec postgres psql -U admin -c "DROP DATABASE IF EXISTS oadbv5_test;"
docker-compose exec postgres psql -U admin -c "CREATE DATABASE oadbv5_test;"

# Restore
docker-compose exec postgres pg_restore -U admin -d oadbv5_test $LATEST

# Verify table count
TABLE_COUNT=$(docker-compose exec postgres psql -U admin -d oadbv5_test -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';")

echo "Tables restored: $TABLE_COUNT"
if [ "$TABLE_COUNT" -eq "32" ]; then
    echo "✅ Backup test passed"
else
    echo "❌ Backup test failed - expected 32 tables, got $TABLE_COUNT"
fi

# Cleanup
docker-compose exec postgres psql -U admin -c "DROP DATABASE oadbv5_test;"
```

## Backup Management

### Cleanup Old Backups

Automated cleanup happens during backup, but manual cleanup if needed:

```bash
# Delete backups older than 30 days
docker-compose exec backup find /backups -name "oadbv5_*.dump" -type f -mtime +30 -delete

# Keep only last 5 backups
docker-compose exec backup sh -c "
  cd /backups
  ls -t oadbv5_[0-9]*.dump | tail -n +6 | xargs rm -f
"
```

### Off-Site Backup

For additional safety, copy backups off-site:

```bash
# Rsync backups to external drive
rsync -avz -e "ssh -p 86" claude@192.168.1.162:/volume2/postgres_backup/ /Volumes/ExternalDrive/openalex_backups/

# Or to cloud storage (requires AWS CLI)
aws s3 sync /volume2/postgres_backup/ s3://my-bucket/openalex-backups/
```

### Backup Monitoring

Create monitoring script:

```bash
#!/bin/bash
# check_backup_health.sh

# Check if backup ran today
TODAY=$(date +"%Y%m%d")
TODAY_BACKUP=$(docker-compose exec backup ls /backups/oadbv5_${TODAY}_*.dump 2>/dev/null | wc -l)

if [ "$TODAY_BACKUP" -gt "0" ]; then
    echo "✅ Today's backup exists"
else
    echo "❌ No backup found for today"
    # Send alert
fi

# Check backup size (should be > 1GB for full database)
LATEST=$(docker-compose exec backup ls -t /backups/oadbv5_*.dump | head -1)
SIZE=$(docker-compose exec backup stat -f%z $LATEST)

if [ "$SIZE" -gt "1000000000" ]; then
    echo "✅ Backup size looks good: $(($SIZE / 1024 / 1024)) MB"
else
    echo "⚠️  Backup size seems small: $(($SIZE / 1024 / 1024)) MB"
fi
```

## Export for Analysis

### Export to CSV

```bash
# Export works table to CSV
docker-compose exec postgres psql -U admin -d oadbv5 -c "
  COPY (SELECT * FROM works LIMIT 10000) TO STDOUT WITH CSV HEADER
" > works_sample.csv

# Export query results
docker-compose exec postgres psql -U admin -d oadbv5 -c "
  COPY (
    SELECT a.display_name, COUNT(w.work_id) as paper_count
    FROM authors a
    JOIN authorship auth ON a.author_id = auth.author_id
    JOIN works w ON auth.work_id = w.work_id
    GROUP BY a.author_id, a.display_name
    ORDER BY paper_count DESC
    LIMIT 100
  ) TO STDOUT WITH CSV HEADER
" > top_authors.csv
```

### Export for Transfer

```bash
# Create compressed backup for transfer
docker-compose exec postgres pg_dump -U admin -d oadbv5 | gzip > oadbv5_export.sql.gz

# Split large backup for transfer
split -b 1G oadbv5_export.sql.gz oadbv5_part_
```

## Troubleshooting Backups

### Backup Fails

```bash
# Check backup logs
docker-compose logs backup

# Test PostgreSQL connectivity from backup container
docker-compose exec backup psql -h postgres -p 5432 -U admin -d oadbv5 -c "SELECT version();"

# Check disk space
docker-compose exec backup df -h /backups
```

### Restore Fails

```bash
# Check backup file integrity
docker-compose exec postgres pg_restore --list /backups/oadbv5_YYYYMMDD.dump

# Restore with verbose output and errors
docker-compose exec postgres pg_restore -U admin -d oadbv5 -v --exit-on-error /backups/oadbv5_YYYYMMDD.dump
```

### Backup Size Issues

```bash
# Analyze database size by table
docker-compose exec postgres psql -U admin -d oadbv5 -c "
  SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    pg_total_relation_size(schemaname||'.'||tablename) AS bytes
  FROM pg_tables
  WHERE schemaname = 'public'
  ORDER BY bytes DESC;
"
```

## Quick Reference

### Common Commands

```bash
# Manual backup
docker-compose exec backup /backup.sh

# List backups
docker-compose exec backup ls -lht /backups/*.dump

# Restore to new database
docker-compose exec postgres pg_restore -U admin -C -d postgres /backups/oadbv5_YYYYMMDD.dump

# Test backup
docker-compose exec postgres pg_restore --list /backups/oadbv5_YYYYMMDD.dump | head

# Copy backup to Mac
scp -P 86 claude@192.168.1.162:/volume2/postgres_backup/oadbv5_YYYYMMDD.dump ~/Desktop/
```

### Backup Schedule

- **Daily**: 2:00 AM UTC
- **Retention**: 7 days for daily, 28 days for weekly
- **Location**: `/volume2/postgres_backup/` (slower HDD storage)
- **Format**: PostgreSQL custom (compressed)
