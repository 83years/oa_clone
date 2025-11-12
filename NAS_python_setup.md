# Step-by-Step Guide: Setting Up Python Parser on UGREEN NAS

This guide walks you through setting up the OpenAlex snapshot parser to run on your UGREEN NAS using Docker, freeing up your Mac for other work.

---

## Prerequisites Checklist

- [ ] UGREEN NAS with Docker installed
- [ ] SSH access to your NAS
- [ ] PostgreSQL container running on NAS (via docker-compose)
- [ ] OpenAlex snapshot data accessible on NAS
- [ ] Your Mac connected to the same network

---

## Step 1: Find Your NAS IP Address

From your Mac terminal:

```bash
# Find your NAS on the network
ping ugreen.local
# Or check your router's connected devices
```

**Note the IP address** 
`192.168.1.100`

---

## Step 2: Verify PostgreSQL is Running on NAS

SSH into your NAS:

```bash
ssh admin@<nas-ip>
# Enter your NAS password when prompted
```

Check PostgreSQL status:

```bash
# List running containers
docker ps

# You should see something like:
# CONTAINER ID   IMAGE         NAMES
# abc123...      postgres:15   postgres_db
```

**Expected output**: A running container named `postgres_db`

If PostgreSQL is NOT running:

```bash
# Navigate to your postgres directory
cd /path/to/your/postgres/docker-compose

# Start PostgreSQL
docker-compose up -d
```

---

## Step 3: Locate Snapshot Data on NAS

Find where your OpenAlex snapshot is stored:

```bash
# Search for the snapshot directory
find /volume1 -name "24OCT2025" -type d 2>/dev/null
# Or for UGREEN NAS, try:
find /mnt -name "24OCT2025" -type d 2>/dev/null
```

**Write down the full path**. It should look something like:
- `/volume1/OpenAlex/24OCT2025/data`
- `/mnt/user/OA_snapshot/24OCT2025/data`

If you can't find it, list your volumes:

```bash
ls -la /volume1/
# or
ls -la /mnt/
```

---

## Step 4: Create Project Directory on NAS

Create a directory for the parser:

```bash
# Choose a location (adjust path based on your NAS structure)
mkdir -p /volume1/projects/OA_clone
# or
mkdir -p /mnt/user/projects/OA_clone

# Navigate to the directory
cd /volume1/projects/OA_clone
# or
cd /mnt/user/projects/OA_clone
```

**Write down this path** - you'll need it later.

---

## Step 5: Transfer Project Files from Mac to NAS

Open a NEW terminal on your Mac (not the SSH session):

```bash
# Use rsync to copy the project to NAS
rsync -avz --progress \
  --exclude='__pycache__' \
  --exclude='.git' \
  --exclude='03_snapshot_parsing/logs/*.log' \
  --exclude='01_oa_snapshot/' \
  /Users/lucas/Documents/openalex_database/python/OA_clone/ \
  admin@<nas-ip>:/volume1/projects/OA_clone/
```

Replace:
- `<nas-ip>` with your NAS IP from Step 1
- `/volume1/projects/OA_clone/` with the path from Step 4

**Expected**: Files transfer successfully (may take 1-2 minutes)

---

## Step 6: Update docker-compose.yml with Snapshot Path

Back in your NAS SSH session:

```bash
# Navigate to project directory
cd /volume1/projects/OA_clone

# Edit docker-compose.yml
nano docker-compose.yml
```

Find this line:
```yaml
- /path/to/nas/snapshot:/Volumes/OA_snapshot/24OCT2025/data:ro
```

Replace `/path/to/nas/snapshot` with the actual path from Step 3. For example:
```yaml
- /volume1/OpenAlex/24OCT2025/data:/Volumes/OA_snapshot/24OCT2025/data:ro
```

**Save and exit**: Press `Ctrl+X`, then `Y`, then `Enter`

---

## Step 7: Verify Docker Network Exists

Check that the `postgres_network` exists:

```bash
docker network ls | grep postgres
```

**Expected output**:
```
abc123...   postgres_network   bridge   local
```

If you don't see it:

```bash
# The network is created by your postgres docker-compose
# Navigate to your postgres directory and ensure it's running
cd /path/to/postgres/compose
docker-compose up -d
```

---

## Step 8: Build the Parser Docker Image

Navigate to the project directory:

```bash
cd /volume1/projects/OA_clone
```

Build the Docker image:

```bash
docker-compose build
```

**Expected**: Build completes successfully after 1-3 minutes
```
Successfully built abc123...
Successfully tagged oa_clone_openalex-parser:latest
```

---

## Step 9: Test Database Connectivity

Test that the parser can connect to PostgreSQL:

```bash
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
```

**Expected output**: `✅ Successfully connected to PostgreSQL!`

**If it fails**:
- Check PostgreSQL is running: `docker ps | grep postgres`
- Verify the password matches in both docker-compose files
- Ensure both containers are on the same network

---

## Step 10: Test Snapshot Data Access

Verify the parser can see the snapshot files:

```bash
docker-compose run --rm openalex-parser \
  ls -la /Volumes/OA_snapshot/24OCT2025/data/
```

**Expected**: You should see directories like `topics/`, `authors/`, `works/`, etc.

**If it fails**:
- Verify the path in docker-compose.yml (Step 6)
- Check the snapshot data exists on NAS: `ls -la /volume1/OpenAlex/24OCT2025/data/`

---

## Step 11: Check Orchestrator Status

See what's been parsed so far:

```bash
docker-compose run --rm openalex-parser \
  python3 03_snapshot_parsing/orchestrator.py --status
```

**Expected output**: Status table showing all entities (topics, concepts, etc.)

---

## Step 12: Run a Test Parse

Run in test mode (processes only 100k lines per file):

```bash
docker-compose run --rm openalex-parser \
  python3 03_snapshot_parsing/orchestrator.py --start --test
```

**Expected**: Parsing begins, you see progress output

**To stop**: Press `Ctrl+C`

---

## Step 13: Run Full Production Parse

Once the test works, run the full parse:

### Option A: Interactive Mode (You can see output)

```bash
docker-compose run --rm openalex-parser \
  python3 03_snapshot_parsing/orchestrator.py --resume
```

### Option B: Background Mode (Runs independently)

```bash
# Start in background
docker-compose up -d

# View logs in real-time
docker-compose logs -f
```

**To detach from logs**: Press `Ctrl+C` (container keeps running)

---

## Step 14: Monitor Progress

### From NAS (SSH session):

```bash
# Check orchestrator status
docker-compose run --rm openalex-parser \
  python3 03_snapshot_parsing/orchestrator.py --status

# View logs
tail -f /volume1/projects/OA_clone/03_snapshot_parsing/logs/orchestrator.log
```

### From Your Mac (Remote monitoring):

```bash
# SSH in and check status in one command
ssh admin@<nas-ip> "cd /volume1/projects/OA_clone && \
  docker-compose run --rm openalex-parser \
  python3 03_snapshot_parsing/orchestrator.py --status"

# Tail logs remotely
ssh admin@<nas-ip> "tail -f /volume1/projects/OA_clone/03_snapshot_parsing/logs/orchestrator.log"
```

---

## Step 15: Managing the Parser

### Stop the parser:

```bash
# If running in background
docker-compose down

# If running in foreground
# Press Ctrl+C
```

### Resume parsing:

```bash
# The orchestrator remembers where it left off
docker-compose run --rm openalex-parser \
  python3 03_snapshot_parsing/orchestrator.py --resume
```

### Reset and start over:

```bash
docker-compose run --rm openalex-parser \
  python3 03_snapshot_parsing/orchestrator.py --reset

docker-compose run --rm openalex-parser \
  python3 03_snapshot_parsing/orchestrator.py --start
```

---

## Troubleshooting

### Problem: "network postgres_network not found"

**Solution**:
```bash
# Find your postgres directory
cd /path/to/postgres/compose

# Start postgres (this creates the network)
docker-compose up -d

# Verify network exists
docker network ls | grep postgres
```

---

### Problem: "No such file or directory" for snapshot data

**Solution**:
```bash
# On NAS, verify the snapshot path exists
ls -la /volume1/OpenAlex/24OCT2025/data/

# Update docker-compose.yml with correct path
nano docker-compose.yml
# Update the volumes section
```

---

### Problem: Database connection refused

**Solution**:
```bash
# Check postgres is running
docker ps | grep postgres

# Check postgres health
docker logs postgres_db | tail -20

# Verify they're on the same network
docker inspect postgres_db | grep Network
docker inspect openalex-parser | grep Network
```

---

### Problem: Parser is slow or hanging

**Solution**:
```bash
# Check available disk space
df -h

# Check container resource usage
docker stats

# View parser logs for errors
docker-compose logs -f
```

---

### Problem: Permission denied errors

**Solution**:
```bash
# On NAS, ensure log directory is writable
chmod -R 755 /volume1/projects/OA_clone/03_snapshot_parsing/logs/

# Restart the container
docker-compose restart
```

---

## Performance Tips

### 1. Increase Batch Size for Faster Parsing

Edit `config.py` on the NAS:

```bash
nano /volume1/projects/OA_clone/config.py
```

Change:
```python
BATCH_SIZE = 50000  # Increase to 100000 or 200000
```

Rebuild after changes:
```bash
docker-compose build
```

---

### 2. Monitor Database Size Growth

```bash
# Check database size periodically
docker exec postgres_db psql -U admin -d OADB -c "
SELECT pg_size_pretty(pg_database_size('OADB')) as db_size;
"
```

---

### 3. Run in Background with Auto-Restart

Edit `docker-compose.yml`:
```yaml
restart: unless-stopped  # Already configured
```

Then start:
```bash
docker-compose up -d
```

The parser will automatically restart if:
- It crashes
- NAS reboots
- Docker daemon restarts

---

## Cleaning Up

### Remove stopped containers:

```bash
docker-compose down
```

### Remove the parser image (to rebuild fresh):

```bash
docker-compose down --rmi local
```

### Clear logs:

```bash
rm -f /volume1/projects/OA_clone/03_snapshot_parsing/logs/*.log
```

---

## Next Steps After Parsing Completes

1. **Verify data in PostgreSQL**:
   ```bash
   docker exec postgres_db psql -U admin -d OADB -c "
   SELECT
     (SELECT COUNT(*) FROM authors) as author_count,
     (SELECT COUNT(*) FROM works) as works_count;
   "
   ```

2. **Stop the parser** (it's done):
   ```bash
   docker-compose down
   ```

3. **Continue on your Mac** with the next phase (author profile building)

---

## Quick Reference Commands

```bash
# Check status
docker-compose run --rm openalex-parser python3 03_snapshot_parsing/orchestrator.py --status

# Resume parsing
docker-compose run --rm openalex-parser python3 03_snapshot_parsing/orchestrator.py --resume

# View logs
docker-compose logs -f

# Stop everything
docker-compose down

# SSH into NAS
ssh admin@<nas-ip>

# Monitor from Mac
ssh admin@<nas-ip> "docker-compose -f /volume1/projects/OA_clone/docker-compose.yml logs -f"
```

---

## Estimated Timeline

- **Setup (Steps 1-12)**: 30-60 minutes
- **Test parse**: 5-10 minutes
- **Full parse**: Several hours to days depending on data size

The orchestrator will show estimated time remaining during parsing.

---

## Success Checklist

After completing all steps, you should have:

- [ ] Parser running on NAS in Docker
- [ ] Connected to PostgreSQL via Docker network (not external network)
- [ ] Access to snapshot data
- [ ] Logs being written to `logs/` directory
- [ ] Ability to monitor progress remotely from Mac
- [ ] Mac freed up for other work

---

## Need Help?

If you get stuck:

1. Check the Troubleshooting section above
2. Review logs: `docker-compose logs -f`
3. Check orchestrator status: `--status` command
4. Verify each prerequisite is met

Remember: The orchestrator saves state, so you can safely stop and resume at any time!
