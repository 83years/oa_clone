# PostgreSQL Performance Optimization for 64GB RAM System

## Overview

This document describes the PostgreSQL memory configuration optimizations applied to the OpenAlex database running on a NAS with 64GB RAM.

## Problem Statement

The database was originally configured with conservative memory settings suitable for smaller systems:
- **shared_buffers**: 4GB (only 6% of available RAM)
- **work_mem**: 256MB
- **maintenance_work_mem**: 2GB
- **effective_cache_size**: 12GB (19% of available RAM)

With 64GB RAM available and only 11% RAM utilization, the system was significantly under-utilizing available hardware resources, leading to slow query performance, especially on large analytical queries against tables like `authors` (115M rows).

## Optimized Configuration

### New Memory Settings

For a 64GB RAM system with a 1.4TB analytical database:

| Setting | Old Value | New Value | Purpose |
|---------|-----------|-----------|---------|
| `shared_buffers` | 4GB | **10GB** | PostgreSQL's main data cache |
| `work_mem` | 256MB | **512MB** | Memory per query operation (sorts, hashes) |
| `maintenance_work_mem` | 2GB | **4GB** | Memory for maintenance operations |
| `effective_cache_size` | 12GB | **40GB** | Planner's estimate of available OS cache |
| `shm_size` (Docker) | 2GB | **12GB** | Shared memory allocation |

### Rationale

**shared_buffers (10GB)**:
- Set to ~16% of total RAM
- Lower than typical 25% recommendation because of very large database size (1.4TB)
- Allows more RAM for OS file system cache, which is crucial for databases larger than RAM

**work_mem (512MB)**:
- Doubled from 256MB to handle complex analytical queries
- With 200 max_connections: 512MB × 200 = 100GB theoretical max (won't happen in practice)
- Actual concurrent analytical queries likely much lower
- Each sort/hash operation per query gets this much memory

**maintenance_work_mem (4GB)**:
- Critical for index creation and VACUUM operations on 115M+ row tables
- Larger values significantly speed up maintenance operations

**effective_cache_size (40GB)**:
- ~63% of total RAM
- Represents shared_buffers (10GB) + OS page cache (~30GB)
- Helps query planner make better decisions about using indexes vs sequential scans

**shm_size (12GB)**:
- Must be at least as large as shared_buffers
- Set slightly higher (12GB) to accommodate additional shared memory needs

## Files Modified

### 1. PostgreSQL Configuration
**File**: `docker/postgres/postgresql.conf`

```ini
# Memory Settings (optimized for 64GB RAM system)
shared_buffers = 10GB
work_mem = 512MB
maintenance_work_mem = 4GB
effective_cache_size = 40GB
```

### 2. Docker Compose Configuration
**File**: `docker-compose.yml`

```yaml
services:
  postgres:
    shm_size: '12gb'  # Must be >= shared_buffers
```

### 3. Documentation Updates
- `02_postgres_setup/docs/DOCKER_SETUP.md` - Updated resource limits section
- `02_postgres_setup/PERFORMANCE_OPTIMIZATION.md` - This file

## Applying the Changes

### On NAS (Required for changes to take effect)

1. **Transfer updated files to NAS**:
   ```bash
   cd /Users/lucas/Documents/openalex_database/python/OA_clone

   rsync -avz -e "ssh -p 86" --exclude='__pycache__' --exclude='.git' --exclude='*.log' \
     docker/ claude@192.168.1.162:/volume1/docker/openalex/OA_clone/docker/

   rsync -avz -e "ssh -p 86" --exclude='__pycache__' --exclude='.git' --exclude='*.log' \
     docker-compose.yml claude@192.168.1.162:/volume1/docker/openalex/OA_clone/
   ```

2. **SSH into NAS**:
   ```bash
   ssh -p 86 claude@192.168.1.162
   cd /volume1/docker/openalex/OA_clone
   ```

3. **Rebuild and restart PostgreSQL container**:
   ```bash
   # Stop PostgreSQL
   docker-compose stop postgres

   # Rebuild the container with new configuration
   docker-compose build postgres

   # Start PostgreSQL with new settings
   docker-compose up -d postgres

   # Verify it started successfully
   docker-compose logs postgres
   ```

4. **Verify new settings are applied**:
   ```bash
   docker-compose exec postgres psql -U admin -d oadbv5 -c "
   SELECT name, setting, unit
   FROM pg_settings
   WHERE name IN (
       'shared_buffers',
       'work_mem',
       'maintenance_work_mem',
       'effective_cache_size'
   )
   ORDER BY name;
   "
   ```

   Expected output:
   ```
              name          | setting  | unit
   -------------------------+----------+------
    effective_cache_size    | 5242880  | 8kB  (40GB)
    maintenance_work_mem    | 4194304  | kB   (4GB)
    shared_buffers          | 1310720  | 8kB  (10GB)
    work_mem                | 524288   | kB   (512MB)
   ```

## Expected Impact

### RAM Utilization
- **Before**: ~11% RAM usage (7GB of 64GB)
- **Target**: 60-80% RAM usage (38-51GB of 64GB)
- **Breakdown**:
  - PostgreSQL shared_buffers: 10GB
  - OS file system cache: 30-40GB
  - Other processes: 5-7GB
  - Available: 7-17GB

### Query Performance
- **Simple queries** (LIMIT 100): Minimal change, already fast
- **Analytical queries**: Significant improvement expected
  - Better use of memory for sorts and hashes
  - More data cached in shared_buffers
  - Planner makes better decisions with accurate effective_cache_size

### Maintenance Operations
- **Index creation**: 2x faster with 4GB maintenance_work_mem
- **VACUUM operations**: Significantly faster on large tables
- **ANALYZE**: Faster statistics collection

## Monitoring

### Check Memory Usage
```bash
# On NAS
free -h

# PostgreSQL memory usage
docker stats openalex_postgres

# PostgreSQL buffer cache hit ratio (should be >95%)
docker-compose exec postgres psql -U admin -d oadbv5 -c "
SELECT
  sum(heap_blks_read) as heap_read,
  sum(heap_blks_hit) as heap_hit,
  sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) * 100 AS cache_hit_ratio
FROM pg_statio_user_tables;
"
```

### Check CPU Usage
```bash
# On NAS
top -bn1 | grep postgres

# Or using docker stats
docker stats openalex_postgres --no-stream
```

### Query Performance
```bash
# View slow queries
docker-compose exec postgres psql -U admin -d oadbv5 -c "
SELECT
  query,
  calls,
  total_exec_time / 1000 as total_time_seconds,
  mean_exec_time / 1000 as mean_time_seconds,
  max_exec_time / 1000 as max_time_seconds
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
"
```

## Further Optimization Possibilities

### If RAM usage is still low (<50%)
Consider increasing:
- `shared_buffers` to 12-14GB
- `effective_cache_size` to 45-48GB

### If seeing slow queries with temp file usage
Check for temp file usage:
```sql
SELECT * FROM pg_stat_statements WHERE temp_blks_written > 0;
```
If frequent temp file usage, consider increasing `work_mem` further (e.g., to 1GB).

### If maintenance operations are still slow
Increase `maintenance_work_mem` to 6-8GB for very large index builds.

### For pure analytical workload (no concurrent writes)
Consider even higher `work_mem` (1-2GB) since analytical queries typically have few concurrent connections.

## Rollback Instructions

If these changes cause issues, revert to previous settings:

**postgresql.conf**:
```ini
shared_buffers = 4GB
work_mem = 256MB
maintenance_work_mem = 2GB
effective_cache_size = 12GB
```

**docker-compose.yml**:
```yaml
shm_size: '2gb'
```

Then rebuild and restart:
```bash
docker-compose build postgres
docker-compose restart postgres
```

## Notes

- These settings assume the NAS is dedicated primarily to the database
- With 200 max_connections, theoretical max memory usage is high, but actual usage depends on concurrent query patterns
- For development/testing with few connections, these settings are very safe
- Monitor actual RAM usage over time and adjust as needed
- These settings are optimized for read-heavy analytical workloads on large tables

## References

- [PostgreSQL Memory Configuration](https://www.postgresql.org/docs/current/runtime-config-resource.html)
- [Tuning PostgreSQL for Large Analytical Queries](https://www.postgresql.org/docs/current/populate.html)
- [PostgreSQL Performance Tuning](https://wiki.postgresql.org/wiki/Performance_Optimization)
