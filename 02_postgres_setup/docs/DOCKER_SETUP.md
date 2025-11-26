# Docker Setup - Detailed Architecture

## Overview

The OpenAlex database infrastructure uses Docker Compose to orchestrate three containerized services running on your NAS at 192.168.1.162.

## Services

### 1. PostgreSQL Container (`postgres`)

**Purpose**: PostgreSQL 16 database server optimized for bulk loading

**Image**: Custom build from `docker/postgres/Dockerfile`
- Base: `postgres:16`
- Extensions: `pg_trgm`, `pg_stat_statements`
- Custom configuration: `postgresql.conf`

**Ports**:
- Container: 5432
- Host: 55432 (exposed for remote access)

**Volumes**:
- `/var/lib/postgresql/data` → `/volume1/docker/openalex/pg_data` (database storage - faster NVMe)
- `/docker-entrypoint-initdb.d` → `./docker/postgres/init-scripts` (initialization scripts)

**Environment Variables**:
- `POSTGRES_DB`: Database name (default: oadbv5)
- `POSTGRES_USER`: Admin username (default: admin)
- `POSTGRES_PASSWORD`: Admin password (from .env)

**Resource Limits**:
- Shared memory: 2GB
- Configuration tuned for bulk loading (see postgresql.conf)

**Health Check**:
```bash
pg_isready -U admin -d oadbv5
```

### 2. Parser Container (`parser`)

**Purpose**: Python 3.11 container for running OpenAlex snapshot parsers

**Image**: Custom build from `docker/parser/Dockerfile`
- Base: `python:3.11-slim`
- Dependencies: psycopg2-binary, boto3
- Application code: Mounted from host

**Volumes**:
- `/data` → `/Volumes/Series/25NOV2025/data` (snapshot data, read-only)
- `/logs` → `/volume1/docker/openalex/logs` (parser logs)
- `/app/03_snapshot_parsing` → `/volume1/docker/openalex/state` (orchestrator state)
- `/app` → `./` (application code, mounted)

**Environment Variables**:
- `DB_HOST=postgres`: Use container name for internal network
- `DB_PORT=5432`: Internal PostgreSQL port
- `SNAPSHOT_DIR=/data`: Snapshot data path in container
- `LOG_DIR=/logs`: Log directory path in container
- `BATCH_SIZE`: Records per COPY operation
- `PARALLEL_PARSERS`: Concurrent parsers

**Entrypoint**: `/entrypoint.sh`
- Waits for PostgreSQL to be ready
- Tests database connection
- Executes command

**Profile**: `manual`
- Does not start automatically with `docker-compose up -d`
- Run manually when needed: `docker-compose run --rm parser [command]`

**Dependencies**:
- Requires `postgres` service to be healthy before starting

### 3. Backup Container (`backup`)

**Purpose**: Automated PostgreSQL backups with retention policy

**Image**: Custom build from `docker/backup/Dockerfile`
- Base: `alpine:3.18`
- Tools: `postgresql16-client`, `bash`, `cron`

**Volumes**:
- `/backups` → `/volume2/postgres_backup` (backup storage - slower HDD)

**Environment Variables**:
- `DB_HOST=postgres`: PostgreSQL container name
- `DB_PORT=5432`: Internal port
- `PGPASSWORD`: Password for pg_dump (from .env)
- `BACKUP_RETENTION_DAYS`: Daily backup retention (default: 7)
- `BACKUP_RETENTION_WEEKS`: Weekly backup retention (default: 4)

**Schedule**: Daily at 2:00 AM UTC via cron

**Backup Format**: PostgreSQL custom format (`.dump`)
- Compressed
- Includes all data and schema
- Can be restored with `pg_restore`

**Restart Policy**: `unless-stopped`
- Automatically restarts on failure
- Persists across NAS reboots

## Network Architecture

**Network**: `openalex_network` (bridge driver)

Internal communication:
```
postgres:5432 ← parser (DB_HOST=postgres)
postgres:5432 ← backup (DB_HOST=postgres)
```

External access:
```
192.168.1.162:55432 → postgres:5432
```

## Volume Management

### Bind Mounts vs Named Volumes

All volumes use bind mounts to specific NAS directories for easy access and backup:

```yaml
postgres_data:
  device: /volume1/docker/openalex/pg_data  # Faster NVMe storage

backups:
  device: /volume2/postgres_backup  # Slower HDD storage

parser_logs:
  device: /volume1/docker/openalex/logs

parser_state:
  device: /volume1/docker/openalex/state
```

### Snapshot Data

Snapshot data is mounted read-only from its current location:
```yaml
${SNAPSHOT_PATH:-/Volumes/Series/25NOV2025/data}:/data:ro
```

**Note**: Update `SNAPSHOT_PATH` in `.env` if snapshot location changes.

## Configuration Management

### Environment File (.env)

The `.env` file contains all configuration:
- Database credentials
- File paths
- Performance settings
- Backup retention

**Security**:
- `.env` is git-ignored
- Never commit passwords to repository
- Use `.env.example` as template

### Centralized Config (config.py)

Python scripts import configuration from `config.py`:
```python
import config
conn = psycopg2.connect(**config.DB_CONFIG)
```

`config.py` reads from environment variables with fallback defaults:
```python
DB_CONFIG = {
    'host': os.getenv('DB_HOST', '192.168.1.162'),
    'port': int(os.getenv('DB_PORT', '55432')),
    ...
}
```

This allows running parsers both:
- In Docker (with container-specific env vars)
- Locally on Mac (with NAS IP defaults)

## Building and Updating

### Initial Build

```bash
cd /volume1/docker/openalex/OA_clone
docker-compose build
```

Builds all three images:
1. `openalex_postgres:latest`
2. `openalex_parser:latest`
3. `openalex_backup:latest`

### Rebuild After Changes

```bash
# Rebuild specific service
docker-compose build postgres
docker-compose build parser
docker-compose build backup

# Rebuild all
docker-compose build

# Force rebuild (no cache)
docker-compose build --no-cache
```

### Update Base Images

```bash
# Pull latest base images
docker-compose pull

# Rebuild with new bases
docker-compose build
```

## Starting and Stopping

### Start All Services

```bash
# Start PostgreSQL and backup (parser is manual profile)
docker-compose up -d

# Or start specific services
docker-compose up -d postgres
docker-compose up -d backup
```

### Stop Services

```bash
# Stop all
docker-compose down

# Stop specific service
docker-compose stop postgres
docker-compose stop backup
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific
docker-compose restart postgres
```

## Logs and Monitoring

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f postgres
docker-compose logs -f backup

# Last N lines
docker-compose logs --tail=100 postgres
```

### Container Stats

```bash
# Real-time resource usage
docker stats openalex_postgres openalex_backup

# Service status
docker-compose ps
```

### PostgreSQL Logs

PostgreSQL logs are inside the container:
```bash
docker-compose exec postgres tail -f /var/lib/postgresql/data/log/postgresql-*.log
```

## Resource Limits

### Current Limits

```yaml
postgres:
  shm_size: '2gb'
  # Configured in postgresql.conf:
  # - shared_buffers: 4GB
  # - work_mem: 256MB
  # - maintenance_work_mem: 2GB
```

### Adding Resource Constraints

To limit CPU and memory, add to docker-compose.yml:

```yaml
services:
  postgres:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 16G
        reservations:
          cpus: '2'
          memory: 8G
```

## Security Considerations

### Network Exposure

- PostgreSQL port 55432 exposed on host
- Accessible from local network (192.168.1.x)
- Not exposed to internet (firewall recommended)

### Credentials

- Stored in `.env` file (git-ignored)
- Passed as environment variables to containers
- Never hardcoded in scripts

### Container Security

- Containers run as non-root where possible
- Read-only mounts for snapshot data
- Limited network access (bridge network only)

## Troubleshooting

### Container Won't Start

```bash
# View build logs
docker-compose build postgres 2>&1 | less

# Check for port conflicts
netstat -tuln | grep 55432

# Inspect container
docker inspect openalex_postgres
```

### Volume Permission Issues

```bash
# Check ownership
ls -ld /volume1/docker/openalex/*

# Fix permissions
chmod -R 755 /volume1/docker/openalex
```

### Network Issues

```bash
# Inspect network
docker network inspect openalex_network

# Test connectivity
docker-compose exec parser ping postgres
docker-compose exec backup nc -zv postgres 5432
```

## Advanced Operations

### Access Container Shell

```bash
# PostgreSQL container
docker-compose exec postgres bash

# Parser container (must be running)
docker-compose run --rm parser bash

# Backup container
docker-compose exec backup sh
```

### Manual Database Operations

```bash
# psql into database
docker-compose exec postgres psql -U admin -d oadbv5

# Run SQL file
docker-compose exec -T postgres psql -U admin -d oadbv5 < script.sql

# Dump database manually
docker-compose exec postgres pg_dump -U admin -d oadbv5 -F c -f /tmp/manual_backup.dump
```

### Clean Up

```bash
# Remove stopped containers
docker-compose rm -f

# Remove unused images
docker image prune -a

# Remove all (WARNING: deletes data)
docker-compose down -v  # Removes volumes too!
```

## Performance Tuning

### PostgreSQL Settings

Edit `docker/postgres/postgresql.conf` and rebuild:
- `shared_buffers`: Increase for more caching
- `work_mem`: Increase for complex queries
- `max_wal_size`: Increase for fewer checkpoints

### Parser Performance

Adjust in `.env`:
- `BATCH_SIZE`: Larger = faster but more memory
- `PARALLEL_PARSERS`: More = faster but higher CPU

### Backup Optimization

- Run backups during low-activity periods
- Compress backups (already enabled in custom format)
- Store backups on separate volume/drive if possible

## Migration and Portability

### Moving to Different NAS

1. Stop services: `docker-compose down`
2. Copy directories:
   - `/volume1/docker/openalex/` → new NAS
3. Update `.env` with new paths if needed
4. Rebuild images on new NAS: `docker-compose build`
5. Start services: `docker-compose up -d`

### Backup Before Major Changes

```bash
# Backup volumes (database and state)
tar -czf openalex_volumes.tar.gz /volume1/docker/openalex/

# Backup database backups directory
tar -czf openalex_backups.tar.gz /volume2/postgres_backup/

# Export database
docker-compose exec postgres pg_dumpall -U admin > full_backup.sql
```
