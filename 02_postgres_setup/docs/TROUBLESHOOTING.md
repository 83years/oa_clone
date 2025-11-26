# Troubleshooting Guide

## Quick Diagnostics

Run these commands first to get an overview of the system state:

```bash
# Check container status
docker-compose ps

# Check container logs
docker-compose logs --tail=50

# Check PostgreSQL health
docker-compose exec postgres pg_isready -U admin -d oadbv5

# Check disk space
df -h /volume1/docker/openalex

# Check Docker resources
docker system df
```

## Docker Issues

### Container Won't Start

**Symptoms**: Container repeatedly restarts or fails to start

**Diagnosis**:
```bash
# View detailed logs
docker-compose logs postgres

# Check container inspect
docker inspect openalex_postgres

# Check for port conflicts
netstat -tuln | grep 55432
lsof -i :55432  # macOS
```

**Solutions**:

1. **Port already in use**:
   ```bash
   # Change port in docker-compose.yml or .env
   # Or stop conflicting service
   ```

2. **Volume permission issues**:
   ```bash
   chmod -R 755 /volume1/docker/openalex/pg_data
   chown -R 999:999 /volume1/docker/openalex/pg_data  # PostgreSQL UID
   ```

3. **Configuration errors**:
   ```bash
   # Validate docker-compose.yml
   docker-compose config

   # Check .env file
   cat .env | grep -v ^#
   ```

### Build Failures

**Symptoms**: `docker-compose build` fails

**Diagnosis**:
```bash
# Build with verbose output
docker-compose build --no-cache --progress=plain
```

**Solutions**:

1. **Network issues**:
   ```bash
   # Test connectivity
   ping registry-1.docker.io

   # Use different DNS
   # Edit /etc/docker/daemon.json
   {"dns": ["8.8.8.8", "8.8.4.4"]}
   ```

2. **Disk space**:
   ```bash
   # Clean up Docker
   docker system prune -a
   docker volume prune
   ```

### Out of Disk Space

**Symptoms**: "no space left on device"

**Diagnosis**:
```bash
# Check disk usage
df -h
du -sh /volume1/docker/openalex/*

# Check Docker space
docker system df -v
```

**Solutions**:
```bash
# Clean Docker images
docker image prune -a

# Clean Docker build cache
docker builder prune

# Remove old backups
find /volume1/docker/openalex/backups -name "*.dump" -mtime +30 -delete

# Clean logs
truncate -s 0 /volume1/docker/openalex/logs/*.log
```

## PostgreSQL Issues

### Cannot Connect to Database

**Symptoms**: "connection refused" or "could not connect"

**Diagnosis**:
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Check PostgreSQL logs
docker-compose logs postgres | tail -50

# Test from inside container
docker-compose exec postgres psql -U admin -d oadbv5 -c "SELECT 1;"

# Test from parser container
docker-compose run --rm parser python3 -c "
import psycopg2
import config
conn = psycopg2.connect(**config.DB_CONFIG)
print('Connected!')
conn.close()
"
```

**Solutions**:

1. **PostgreSQL not ready**:
   ```bash
   # Wait for health check
   docker-compose exec postgres pg_isready -U admin

   # Restart PostgreSQL
   docker-compose restart postgres
   ```

2. **Wrong credentials**:
   ```bash
   # Check .env file
   cat .env | grep PASSWORD

   # Verify config.py reads correctly
   docker-compose run --rm parser python3 -c "import config; print(config.DB_CONFIG)"
   ```

3. **Network issues**:
   ```bash
   # Check Docker network
   docker network inspect openalex_network

   # Recreate network
   docker-compose down
   docker-compose up -d
   ```

### Database Corruption

**Symptoms**: "invalid page header" or similar errors

**Diagnosis**:
```bash
# Check database integrity
docker-compose exec postgres psql -U admin -d oadbv5 -c "
  SELECT datname, datallowconn FROM pg_database WHERE datname='oadbv5';
"

# Check for corrupt indexes
docker-compose exec postgres psql -U admin -d oadbv5 -c "
  SELECT tablename, indexname FROM pg_indexes WHERE schemaname='public';
"
```

**Solutions**:

1. **Reindex**:
   ```bash
   docker-compose exec postgres psql -U admin -d oadbv5 -c "REINDEX DATABASE oadbv5;"
   ```

2. **Restore from backup**:
   ```bash
   # See docs/BACKUP_RESTORE.md for full procedure
   docker-compose exec postgres pg_restore -U admin -C -d postgres /backups/latest.dump
   ```

### Slow Query Performance

**Symptoms**: Queries taking too long

**Diagnosis**:
```bash
# Check slow queries
docker-compose exec postgres psql -U admin -d oadbv5 -c "
  SELECT query, calls, total_time, mean_time
  FROM pg_stat_statements
  ORDER BY mean_time DESC
  LIMIT 10;
"

# Check table sizes
docker-compose exec postgres psql -U admin -d oadbv5 -c "
  SELECT schemaname, tablename,
         pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
  FROM pg_tables
  WHERE schemaname='public'
  ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

**Solutions**:

1. **Missing indexes**:
   ```bash
   # Run constraint building
   docker-compose run --rm parser python3 03_snapshot_parsing/constraint_building/orchestrator_constraints.py
   ```

2. **Need vacuum**:
   ```bash
   docker-compose exec postgres psql -U admin -d oadbv5 -c "VACUUM ANALYZE;"
   ```

3. **Tune configuration**:
   ```bash
   # Edit docker/postgres/postgresql.conf
   # Increase shared_buffers, work_mem, etc.
   # Then rebuild and restart
   docker-compose build postgres
   docker-compose restart postgres
   ```

## Parser Issues

### Parser Crashes or Hangs

**Symptoms**: Parser stops responding or exits with errors

**Diagnosis**:
```bash
# Check parser logs
docker-compose logs parser

# Check orchestrator log
tail -100 /volume1/docker/openalex/logs/orchestrator.log

# Check memory usage
docker stats openalex_parser --no-stream
```

**Solutions**:

1. **Out of memory**:
   ```bash
   # Reduce batch size in .env
   BATCH_SIZE=25000  # Instead of 50000

   # Restart parser
   docker-compose restart parser
   ```

2. **Database connection lost**:
   ```bash
   # Check PostgreSQL is running
   docker-compose exec postgres pg_isready

   # Resume from last state
   docker-compose run --rm parser python3 03_snapshot_parsing/orchestrator.py --resume
   ```

3. **Corrupt snapshot data**:
   ```bash
   # Verify snapshot files
   gzip -t /Volumes/Series/25NOV2025/data/works/updated_date=*/part_*.gz

   # Re-download if corrupt
   python3 01_oa_snapshot/openalex_downloader.py
   ```

### Cannot Find Snapshot Data

**Symptoms**: "No such file or directory" for snapshot files

**Diagnosis**:
```bash
# Check if data is mounted
docker-compose exec parser ls -la /data

# Check snapshot path in .env
cat .env | grep SNAPSHOT

# Check actual location
ls -la /Volumes/Series/25NOV2025/data
```

**Solutions**:

1. **Update snapshot path**:
   ```bash
   # Edit .env
   SNAPSHOT_PATH=/actual/path/to/snapshot/data

   # Restart
   docker-compose down
   docker-compose up -d
   ```

2. **Mount permissions**:
   ```bash
   chmod -R 755 /Volumes/Series/25NOV2025/data
   ```

### Orchestrator State Issues

**Symptoms**: Orchestrator won't resume or shows wrong state

**Diagnosis**:
```bash
# Check orchestrator state
cat /volume1/docker/openalex/state/orchestrator_state.json

# Check orchestrator status
docker-compose run --rm parser python3 03_snapshot_parsing/orchestrator.py --status
```

**Solutions**:

1. **Reset orchestrator**:
   ```bash
   docker-compose run --rm parser python3 03_snapshot_parsing/orchestrator.py --reset
   ```

2. **Manual state fix**:
   ```bash
   # Edit state file
   nano /volume1/docker/openalex/state/orchestrator_state.json
   ```

## Backup Issues

### Backups Not Running

**Symptoms**: No new backups appearing

**Diagnosis**:
```bash
# Check backup container
docker-compose ps backup

# Check cron status
docker-compose exec backup crontab -l

# Check backup logs
docker-compose exec backup cat /backups/backup.log

# Check cron logs
docker-compose exec backup cat /var/log/cron.log
```

**Solutions**:

1. **Container not running**:
   ```bash
   docker-compose up -d backup
   ```

2. **Cron not running**:
   ```bash
   docker-compose restart backup
   docker-compose logs backup
   ```

3. **Manual backup test**:
   ```bash
   docker-compose exec backup /backup.sh
   ```

### Backup Fails

**Symptoms**: Backup script errors

**Diagnosis**:
```bash
# Run backup with verbose output
docker-compose exec backup sh -x /backup.sh

# Check PostgreSQL connection
docker-compose exec backup pg_isready -h postgres -p 5432 -U admin
```

**Solutions**:

1. **Database connection**:
   ```bash
   # Check credentials in .env
   cat .env | grep -E '(DB_HOST|DB_PORT|ADMIN_PASSWORD)'
   ```

2. **Disk space**:
   ```bash
   # Check backup directory space
   docker-compose exec backup df -h /backups
   ```

## Network Issues

### Cannot Access from Mac

**Symptoms**: Cannot connect remotely via PostgreSQL or SSH

**Diagnosis**:
```bash
# Test network connectivity
ping 192.168.1.162

# Test PostgreSQL port
nc -zv 192.168.1.162 55432

# Test SSH
ssh -p 86 claude@192.168.1.162 echo "Connected"
```

**Solutions**:

1. **Firewall blocking**:
   ```bash
   # On NAS, check firewall rules
   iptables -L -n

   # Or check NAS firewall UI
   ```

2. **Docker not exposing port**:
   ```bash
   # Verify port mapping
   docker-compose ps
   docker port openalex_postgres
   ```

3. **Network configuration**:
   ```bash
   # Check IP address
   ifconfig  # or ip addr

   # Verify docker-compose.yml has correct port mapping
   grep -A 2 "ports:" docker-compose.yml
   ```

### Containers Cannot Communicate

**Symptoms**: Parser cannot reach PostgreSQL

**Diagnosis**:
```bash
# Check Docker network
docker network inspect openalex_network

# Test connectivity from parser
docker-compose run --rm parser ping postgres

# Test PostgreSQL port
docker-compose run --rm parser nc -zv postgres 5432
```

**Solutions**:
```bash
# Recreate network
docker-compose down
docker network rm openalex_network
docker-compose up -d
```

## Performance Issues

### System Running Slow

**Diagnosis**:
```bash
# Check system resources
top

# Check Docker stats
docker stats

# Check disk I/O
iostat -x 1 5  # Linux
```

**Solutions**:

1. **Reduce resource usage**:
   ```bash
   # Lower batch size
   BATCH_SIZE=25000

   # Reduce parallel parsers
   PARALLEL_PARSERS=2
   ```

2. **Optimize PostgreSQL**:
   ```bash
   # Run VACUUM
   docker-compose exec postgres psql -U admin -d oadbv5 -c "VACUUM FULL ANALYZE;"
   ```

3. **Check NAS load**:
   ```bash
   # Monitor NAS performance via web UI
   # Consider upgrading NAS RAM or moving to SSD
   ```

## Data Issues

### Missing or Incorrect Data

**Diagnosis**:
```bash
# Check table row counts
docker-compose exec postgres psql -U admin -d oadbv5 -c "
  SELECT tablename, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC;
"

# Check for foreign key violations
docker-compose exec postgres psql -U admin -d oadbv5 -c "
  SELECT conname, conrelid::regclass, confrelid::regclass
  FROM pg_constraint
  WHERE contype = 'f';
"
```

**Solutions**:

1. **Re-run parser**:
   ```bash
   # Clear and restart
   docker-compose run --rm parser python3 02_postgres_setup/wipe_database.py
   docker-compose run --rm parser python3 02_postgres_setup/oadb2_postgresql_setup.py
   docker-compose run --rm parser python3 03_snapshot_parsing/orchestrator.py --start
   ```

2. **Check snapshot data**:
   ```bash
   # Verify files exist and are readable
   find /Volumes/Series/25NOV2025/data -name "*.gz" | head -20
   ```

## Getting Help

If issues persist:

1. **Collect diagnostic information**:
   ```bash
   # Create diagnostic bundle
   mkdir ~/openalex_diagnostics
   docker-compose logs > ~/openalex_diagnostics/docker_logs.txt
   cp .env.example ~/openalex_diagnostics/  # Don't include actual .env with passwords!
   docker-compose config > ~/openalex_diagnostics/composed_config.yml
   df -h > ~/openalex_diagnostics/disk_usage.txt
   ```

2. **Check documentation**:
   - README.md - Quick start guide
   - docs/DOCKER_SETUP.md - Docker architecture
   - docs/REMOTE_ACCESS.md - Remote access setup
   - docs/BACKUP_RESTORE.md - Backup procedures

3. **Review logs systematically**:
   - Docker logs: `docker-compose logs`
   - PostgreSQL logs: `docker-compose exec postgres tail -100 /var/lib/postgresql/data/log/*`
   - Parser logs: `/volume1/docker/openalex/logs/orchestrator.log`
   - Backup logs: `/volume1/docker/openalex/backups/backup.log`

## Common Error Messages

| Error Message | Likely Cause | Solution |
|--------------|--------------|----------|
| "connection refused" | PostgreSQL not running | `docker-compose up -d postgres` |
| "no space left on device" | Disk full | Clean up old backups/logs |
| "permission denied" | File permissions | `chmod -R 755 /volume1/docker/openalex` |
| "could not find snapshot" | Wrong path in .env | Update SNAPSHOT_PATH |
| "invalid page header" | Database corruption | Restore from backup |
| "out of memory" | Insufficient RAM | Reduce BATCH_SIZE |
| "cannot resolve hostname" | Network issue | Check docker network |
| "authentication failed" | Wrong password | Check .env file |
