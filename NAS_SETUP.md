# Setting Up OpenAlex Parser on UGREEN NAS

## Prerequisites
- UGREEN NAS with Docker installed
- SSH access to your NAS
- OpenAlex snapshot data accessible on NAS
- PostgreSQL database at 192.168.1.100:55432

## Step-by-Step Setup

### 1. Transfer Project to NAS

```bash
# From your Mac, copy the project to NAS
# Replace <nas-ip> and <nas-path> with your NAS details
rsync -avz --exclude='__pycache__' --exclude='.git' \
  /Users/lucas/Documents/openalex_database/python/OA_clone/ \
  <nas-user>@<nas-ip>:<nas-path>/OA_clone/
```

### 2. Locate Snapshot Data on NAS

SSH into your NAS and find where the snapshot data is stored:

```bash
ssh <nas-user>@<nas-ip>
find / -name "24OCT2025" -type d 2>/dev/null
```

Note the path - you'll need this for the docker-compose.yml volume mount.

### 3. Update docker-compose.yml

Edit `docker-compose.yml` and update the snapshot data path:

```yaml
volumes:
  # Change this line to match your NAS path
  - /actual/path/to/snapshot:/Volumes/OA_snapshot/24OCT2025/data:ro
```

### 4. Connect to PostgreSQL Network

The docker-compose.yml is pre-configured to connect to your existing PostgreSQL container via the `postgres_network`.

**Important**: The parser will connect to PostgreSQL using:
- **Host**: `postgres` (container name, not IP address)
- **Port**: `5432` (internal Docker port, not the mapped 55432)
- **Database**: `OADB`
- **User**: `admin`
- **Password**: `secure_password_123`

This configuration is already set in docker-compose.yml. No `.env` file needed unless you want to override these values.

### 5. Ensure PostgreSQL is Running

Make sure your PostgreSQL container is running first:

```bash
# Navigate to your postgres docker-compose directory
cd /path/to/postgres/compose

# Start PostgreSQL if not running
docker-compose up -d

# Verify it's healthy
docker ps | grep postgres
```

### 6. Build Docker Image

```bash
cd <nas-path>/OA_clone
docker-compose build
```

### 7. Test Database Connectivity

```bash
# Test that the parser can reach PostgreSQL
docker-compose run --rm openalex-parser python3 -c "
import psycopg2
conn = psycopg2.connect(
    host='postgres',
    port=5432,
    database='OADB',
    user='admin',
    password='secure_password_123'
)
print('✅ Successfully connected to PostgreSQL!')
conn.close()
"

# Show orchestrator status
docker-compose run --rm openalex-parser python3 03_snapshot_parsing/orchestrator.py --status
```

### 8. Run the Parser

#### Option A: Start Fresh
```bash
docker-compose run --rm openalex-parser python3 03_snapshot_parsing/orchestrator.py --start
```

#### Option B: Resume from Saved State
```bash
docker-compose run --rm openalex-parser python3 03_snapshot_parsing/orchestrator.py --resume
```

#### Option C: Run in Background (Long-Running)
```bash
docker-compose up -d
# Check logs
docker-compose logs -f
```

### 9. Monitor Progress

```bash
# Check orchestrator status
docker-compose run --rm openalex-parser python3 03_snapshot_parsing/orchestrator.py --status

# View logs
tail -f 03_snapshot_parsing/logs/orchestrator.log
```

### 10. Stop/Manage Container

```bash
# Stop container
docker-compose down

# Restart container
docker-compose restart

# View running containers
docker ps
```

## Test Mode

To run in test mode (processes only 100k lines per file):

```bash
docker-compose run --rm openalex-parser python3 03_snapshot_parsing/orchestrator.py --start --test
```

## Troubleshooting

### Database Connection Issues
```bash
# Test PostgreSQL connectivity from container
docker-compose run --rm openalex-parser \
  psql -h 192.168.1.100 -p 55432 -U admin -d OADB -c "SELECT version();"
```

### Data Path Issues
```bash
# Verify snapshot data is accessible
docker-compose run --rm openalex-parser ls -la /Volumes/OA_snapshot/24OCT2025/data
```

### Check Logs
```bash
# View all logs
docker-compose logs

# Follow logs in real-time
docker-compose logs -f
```

### Reset State
```bash
docker-compose run --rm openalex-parser python3 03_snapshot_parsing/orchestrator.py --reset
```

## Performance Optimization

For better performance on NAS:

1. **Adjust batch size** in `config.py`:
   ```python
   BATCH_SIZE = 100000  # Increase for faster bulk inserts
   ```

2. **Use unlogged tables** (faster but no crash recovery):
   ```python
   USE_UNLOGGED_TABLES = True
   ```

3. **Allocate more resources** in docker-compose.yml:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '4'
         memory: 8G
   ```

## Alternative: Direct Python Installation on NAS

If you prefer not to use Docker:

```bash
# SSH into NAS
ssh <nas-user>@<nas-ip>

# Install Python (method depends on your NAS OS)
# For Ubuntu/Debian-based:
apt-get update && apt-get install python3 python3-pip

# Install dependencies
pip3 install psycopg2-binary

# Run directly
cd <nas-path>/OA_clone
python3 03_snapshot_parsing/orchestrator.py --resume
```

## Monitoring from Your Mac

While the NAS runs the parser, monitor from your Mac:

```bash
# SSH in and check status
ssh <nas-user>@<nas-ip> "docker-compose -f <nas-path>/OA_clone/docker-compose.yml \
  run --rm openalex-parser python3 03_snapshot_parsing/orchestrator.py --status"

# Or tail logs remotely
ssh <nas-user>@<nas-ip> "tail -f <nas-path>/OA_clone/03_snapshot_parsing/logs/orchestrator.log"
```
