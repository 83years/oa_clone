# OpenAlex Database Setup

Fully containerized PostgreSQL database infrastructure for the OpenAlex project with automated backups and remote access.

## Quick Start

### Prerequisites

- Docker and Docker Compose installed on NAS
- SSH access to NAS at 192.168.1.162
- OpenAlex snapshot data at `/Volumes/Series/25NOV2025/data`
- At least 3 TB available storage on NAS

### Initial Setup (One-Time)

#### 1. Prepare NAS Environment

SSH into your NAS:
```bash
ssh -p 86 claude@192.168.1.162
```

Create directory structure:
```bash
mkdir -p /volume1/docker/openalex/{pg_data,logs,state}
mkdir -p /volume2/postgres_backup
chmod -R 755 /volume1/docker/openalex
chmod -R 755 /volume2/postgres_backup
```

#### 2. Transfer Repository to NAS

From your Mac:
```bash
cd /Users/lucas/Documents/openalex_database/python/OA_clone

# Transfer files to NAS
rsync -avz -e "ssh -p 86" --exclude='__pycache__' --exclude='.git' --exclude='*.log' \
  . claude@192.168.1.162:/volume1/docker/openalex/OA_clone/
```

#### 3. Configure Environment Variables

On NAS, create `.env` file:
```bash
cd /volume1/docker/openalex/OA_clone
cp .env.example .env

# Edit .env with your passwords and settings
nano .env
```

Required changes in `.env`:
- Update `ADMIN_PASSWORD` with a strong password
- Update `READONLY_PASSWORD` with a strong password
- Verify `SNAPSHOT_PATH` points to your snapshot data location

#### 4. Build and Start Services

```bash
cd /volume1/docker/openalex/OA_clone

# Build Docker images
docker-compose build

# Start PostgreSQL
docker-compose up -d postgres

# Wait for PostgreSQL to be healthy
docker-compose exec postgres pg_isready -U admin
```

#### 5. Initialize Database Schema

```bash
# Run database setup script
docker-compose run --rm parser python3 02_postgres_setup/oadb2_postgresql_setup.py

# Verify setup
docker-compose exec postgres psql -U admin -d oadbv5 -c "\dt"
```

#### 6. Start Backup Service

```bash
# Start automated backups
docker-compose up -d backup

# Test backup manually
docker-compose exec backup /backup.sh
```

## Common Operations

### Check Service Status

```bash
# View all running containers
docker-compose ps

# Check PostgreSQL health
docker-compose exec postgres pg_isready -U admin -d oadbv5

# View logs
docker-compose logs postgres
docker-compose logs backup
```

### Run Parser (Data Loading)

```bash
# Check parser status
docker-compose run --rm parser python3 03_snapshot_parsing/orchestrator.py --status

# Start parsing (fresh start)
docker-compose run --rm parser python3 03_snapshot_parsing/orchestrator.py --start

# Resume parsing from last state
docker-compose run --rm parser python3 03_snapshot_parsing/orchestrator.py --resume

# Test mode (100k records per file)
docker-compose run --rm parser python3 03_snapshot_parsing/orchestrator.py --start --test
```

### Database Management

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U admin -d oadbv5

# View table sizes
docker-compose exec postgres psql -U admin -d oadbv5 -c "
  SELECT schemaname, tablename,
         pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
  FROM pg_tables
  WHERE schemaname = 'public'
  ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"

# Vacuum and analyze
docker-compose exec postgres psql -U admin -d oadbv5 -c "VACUUM ANALYZE;"
```

### Backup Operations

```bash
# Manual backup
docker-compose exec backup /backup.sh

# List backups
docker-compose exec backup ls -lh /backups/

# Verify backup schedule
docker-compose exec backup crontab -l

# View backup logs
docker-compose exec backup cat /backups/backup.log
```

## Remote Access

### From Mac

#### PostgreSQL Connection
```bash
# Using psql
psql -h 192.168.1.162 -p 55432 -U admin -d oadbv5

# Python connection
python3 -c "
import psycopg2
conn = psycopg2.connect(
    host='192.168.1.162',
    port=55432,
    database='oadbv5',
    user='admin',
    password='your_password'
)
print('Connected successfully!')
conn.close()
"
```

#### Monitor Parser Progress Remotely
```bash
# Check orchestrator status
ssh -p 86 claude@192.168.1.162 "cd /volume1/docker/openalex/OA_clone && docker-compose run --rm parser python3 03_snapshot_parsing/orchestrator.py --status"

# Tail parser logs
ssh -p 86 claude@192.168.1.162 "tail -f /volume1/docker/openalex/logs/orchestrator.log"
```

## Maintenance

### Daily
- Automated backups run at 2 AM UTC
- Monitor disk space usage
- Check logs for errors

### Weekly
- Verify backup success: `docker-compose exec backup cat /backups/backup.log`
- Review parser progress
- Check PostgreSQL performance

### Monthly
- Test backup restoration (see docs/BACKUP_RESTORE.md)
- Update Docker images: `docker-compose pull && docker-compose build`
- Review disk usage and cleanup old logs

## Troubleshooting

### Container Won't Start
```bash
# View detailed logs
docker-compose logs -f postgres

# Check if port 55432 is in use
docker-compose exec postgres netstat -tuln | grep 5432

# Restart services
docker-compose restart postgres
```

### Database Connection Refused
```bash
# Verify PostgreSQL is running
docker-compose ps

# Check PostgreSQL health
docker-compose exec postgres pg_isready -U admin

# View PostgreSQL logs
docker-compose logs postgres | tail -50
```

### Parser Errors
```bash
# View parser logs
docker-compose logs parser

# Check database connection from parser
docker-compose run --rm parser python3 -c "
import config
import psycopg2
conn = psycopg2.connect(**config.DB_CONFIG)
print('Connection successful!')
conn.close()
"
```

For more detailed troubleshooting, see:
- `docs/TROUBLESHOOTING.md` - Common issues and solutions
- `docs/DOCKER_SETUP.md` - Docker architecture details
- `docs/REMOTE_ACCESS.md` - Remote access configuration
- `docs/BACKUP_RESTORE.md` - Backup and recovery procedures

## Architecture

- **PostgreSQL 16**: Database server optimized for bulk loading
- **Parser Container**: Python scripts for parsing OpenAlex snapshots
- **Backup Container**: Automated daily backups with retention policy
- **Network**: Docker bridge network for inter-container communication
- **Volumes**: Persistent storage for data, backups, and logs

## Database Schema

The database consists of 32 tables organized in 4 phases:

- **Phase 0**: Reference tables (topics, concepts, publishers, funders, sources, institutions)
- **Phase 1**: Entity tables (authors, works)
- **Phase 2**: Relationship tables (authorship, work_topics, citations, etc.)
- **Phase 3**: Hierarchy tables (institution_hierarchy, topic_hierarchy)
- **Phase 4**: Supporting tables (alternate_ids, apc, search_metadata)

## Next Steps

1. Run parser to load data: `docker-compose run --rm parser python3 03_snapshot_parsing/orchestrator.py --start`
2. Monitor progress: Check logs at `/volume1/docker/openalex/logs/orchestrator.log`
3. After loading completes: Add constraints using `03_snapshot_parsing/constraint_building/orchestrator_constraints.py`
4. Verify data integrity: Run `verify_setup.py`

## Support

For issues or questions:
1. Check the documentation in `docs/`
2. Review logs: `docker-compose logs`
3. Verify environment configuration in `.env`
4. Ensure all prerequisites are met
