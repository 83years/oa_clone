# Remote Access Guide

## Overview

The OpenAlex database infrastructure supports remote access via SSH, PostgreSQL, and SMB from your Mac and other devices on the local network.

## SSH Access

### Basic Connection

```bash
ssh -p 86 claude@192.168.1.162
```

### SSH Key Authentication (Recommended)

Generate SSH key on Mac (if not already done):
```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

Copy public key to NAS:
```bash
ssh-copy-id -p 86 claude@192.168.1.162
```

Test connection:
```bash
ssh -p 86 claude@192.168.1.162
```

### Common SSH Operations

```bash
# Execute command without entering shell
ssh -p 86 claude@192.168.1.162 "docker-compose -f /volume1/docker/openalex/OA_clone/docker-compose.yml ps"

# Check parser status remotely
ssh -p 86 claude@192.168.1.162 "cd /volume1/docker/openalex/OA_clone && docker-compose run --rm parser python3 03_snapshot_parsing/orchestrator.py --status"

# Tail logs remotely
ssh -p 86 claude@192.168.1.162 "tail -f /volume1/docker/openalex/logs/orchestrator.log"
```

### SSH Config

Add to `~/.ssh/config` on Mac for easier access:

```
Host openalex-nas
    HostName 192.168.1.162
    Port 86
    User claude
    IdentityFile ~/.ssh/id_ed25519
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

Then connect with:
```bash
ssh openalex-nas
```

## PostgreSQL Remote Access

### Connection Details

- **Host**: 192.168.1.162
- **Port**: 55432 (external port, mapped to container port 5432)
- **Database**: oadbv5
- **Username**: admin
- **Password**: (from .env file)

### Using psql (Command Line)

Install PostgreSQL client on Mac:
```bash
brew install postgresql@16
```

Connect:
```bash
psql -h 192.168.1.162 -p 55432 -U admin -d oadbv5
```

Create `.pgpass` file for password-less access:
```bash
echo "192.168.1.162:55432:oadbv5:admin:your_password" >> ~/.pgpass
chmod 600 ~/.pgpass
```

### Using Python

```python
import psycopg2

# Connect to database
conn = psycopg2.connect(
    host='192.168.1.162',
    port=55432,
    database='oadbv5',
    user='admin',
    password='your_password'
)

# Execute query
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM works")
print(f"Total works: {cursor.fetchone()[0]}")

# Close connection
cursor.close()
conn.close()
```

### Using R

```r
library(RPostgreSQL)

# Create connection
drv <- dbDriver("PostgreSQL")
con <- dbConnect(drv,
                 host="192.168.1.162",
                 port=55432,
                 dbname="oadbv5",
                 user="admin",
                 password="your_password")

# Query data
result <- dbGetQuery(con, "SELECT COUNT(*) FROM authors")
print(result)

# Close connection
dbDisconnect(con)
```

### Using GUI Tools

#### pgAdmin 4

1. Download from https://www.pgadmin.org/
2. Add new server:
   - Name: OpenAlex NAS
   - Host: 192.168.1.162
   - Port: 55432
   - Database: oadbv5
   - Username: admin
   - Password: your_password

#### DBeaver

1. Download from https://dbeaver.io/
2. New Connection → PostgreSQL
3. Enter connection details as above

#### TablePlus (Mac)

1. Download from https://tableplus.com/
2. Create new connection → PostgreSQL
3. Enter connection details

## SMB Share Access

### Setting Up SMB Shares on NAS

Via NAS web interface:
1. Control Panel → Shared Folder
2. Create shared folders:
   - `openalex_logs` → `/volume1/docker/openalex/logs` (Read Only)
   - `openalex_backups` → `/volume2/postgres_backup` (Read/Write)
3. Control Panel → File Services → SMB
4. Enable SMB service

### Mounting from Mac

#### Via Finder
1. Finder → Go → Connect to Server (⌘K)
2. Enter: `smb://192.168.1.162/openalex_logs`
3. Authenticate with NAS credentials
4. Repeat for `smb://192.168.1.162/openalex_backups`

#### Via Command Line
```bash
# Create mount points
mkdir -p /Volumes/openalex_logs
mkdir -p /Volumes/openalex_backups

# Mount shares
mount -t smbfs //claude@192.168.1.162/openalex_logs /Volumes/openalex_logs
mount -t smbfs //claude@192.168.1.162/openalex_backups /Volumes/openalex_backups
```

#### Auto-mount on Login

Add to Login Items:
1. System Preferences → Users & Groups → Login Items
2. Add mounted volumes

Or use `/etc/fstab` (requires root):
```
//claude@192.168.1.162/openalex_logs /Volumes/openalex_logs smbfs rw,auto 0 0
```

### Accessing Logs

Once mounted:
```bash
# Tail orchestrator log
tail -f /Volumes/openalex_logs/orchestrator.log

# View backup logs
cat /Volumes/openalex_backups/backup.log

# List all logs
ls -lh /Volumes/openalex_logs/
```

## Remote Monitoring

### Parser Status Script (Mac)

Save as `check_parser.sh`:
```bash
#!/bin/bash
ssh admin@192.168.1.162 "cd /volume1/docker/openalex/OA_clone && docker-compose run --rm parser python3 03_snapshot_parsing/orchestrator.py --status"
```

Make executable:
```bash
chmod +x check_parser.sh
./check_parser.sh
```

### Database Status Script (Mac)

Save as `check_db.sh`:
```bash
#!/bin/bash
psql -h 192.168.1.162 -p 55432 -U admin -d oadbv5 << EOF
SELECT
    schemaname,
    tablename,
    n_live_tup as row_count,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY n_live_tup DESC
LIMIT 10;
EOF
```

### Backup Status Script (Mac)

Save as `check_backups.sh`:
```bash
#!/bin/bash
ssh admin@192.168.1.162 "ls -lh /volume1/docker/openalex/backups/ | tail -20"
```

## Security Best Practices

### Network Security

1. **Firewall Configuration**
   ```bash
   # On NAS, allow only local network
   # Example using iptables (if available):
   iptables -A INPUT -s 192.168.1.0/24 -p tcp --dport 55432 -j ACCEPT
   iptables -A INPUT -p tcp --dport 55432 -j DROP
   ```

2. **VPN for Remote Access**
   - Use NAS VPN server for access outside local network
   - Never expose PostgreSQL directly to internet

### Password Security

1. **Use Strong Passwords**
   - Minimum 16 characters
   - Mix of uppercase, lowercase, numbers, symbols
   - Use password manager

2. **Rotate Passwords Regularly**
   - Change PostgreSQL passwords quarterly
   - Update .env file on NAS
   - Update .pgpass on Mac
   - Restart containers: `docker-compose restart`

3. **Separate Read-Only User**
   ```sql
   -- Create read-only user
   CREATE USER analyst WITH PASSWORD 'strong_password';
   GRANT CONNECT ON DATABASE oadbv5 TO analyst;
   GRANT USAGE ON SCHEMA public TO analyst;
   GRANT SELECT ON ALL TABLES IN SCHEMA public TO analyst;
   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO analyst;
   ```

### SSH Security

1. **Disable Password Authentication** (key-only):
   ```bash
   # On NAS, edit /etc/ssh/sshd_config
   PasswordAuthentication no
   PubkeyAuthentication yes
   ```

2. **Use SSH Multiplexing** (faster connections):
   Add to `~/.ssh/config`:
   ```
   Host openalex-nas
       ControlMaster auto
       ControlPath ~/.ssh/sockets/%r@%h-%p
       ControlPersist 600
   ```

## Monitoring from Mac

### Real-Time Dashboard (Terminal)

Use `watch` command:
```bash
# Monitor container stats
watch -n 5 'ssh admin@192.168.1.162 "docker stats --no-stream openalex_postgres openalex_backup"'

# Monitor disk usage
watch -n 60 'ssh admin@192.168.1.162 "df -h /volume1/docker/openalex"'
```

### Log Monitoring

Use `multitail` for multiple logs:
```bash
brew install multitail

multitail \
  -l 'ssh admin@192.168.1.162 "tail -f /volume1/docker/openalex/logs/orchestrator.log"' \
  -l 'ssh admin@192.168.1.162 "tail -f /volume1/docker/openalex/backups/backup.log"'
```

## Troubleshooting Remote Access

### Cannot Connect via SSH

```bash
# Test network connectivity
ping 192.168.1.162

# Test SSH port
nc -zv 192.168.1.162 22

# Check SSH service on NAS
ssh admin@192.168.1.162 "systemctl status sshd"  # or service sshd status
```

### Cannot Connect to PostgreSQL

```bash
# Test port connectivity
nc -zv 192.168.1.162 55432

# Check if PostgreSQL is listening
ssh admin@192.168.1.162 "docker-compose -f /volume1/docker/openalex/OA_clone/docker-compose.yml exec postgres netstat -tuln | grep 5432"

# Check PostgreSQL health
ssh admin@192.168.1.162 "docker-compose -f /volume1/docker/openalex/OA_clone/docker-compose.yml exec postgres pg_isready -U admin"
```

### Cannot Mount SMB Shares

```bash
# Test SMB port
nc -zv 192.168.1.162 445

# Check SMB service on NAS
ssh admin@192.168.1.162 "systemctl status smbd"  # or check via NAS UI

# Try manual mount with verbose output
mount_smbfs -v //admin@192.168.1.162/openalex_logs /Volumes/openalex_logs
```

### Slow Connections

```bash
# Check network latency
ping -c 10 192.168.1.162

# Check bandwidth
iperf3 -c 192.168.1.162  # Requires iperf3 on both sides

# Use SSH compression for slow networks
ssh -C admin@192.168.1.162
```

## Quick Reference

### Connection Strings

**SSH**:
```
ssh -p 86 claude@192.168.1.162
```

**PostgreSQL**:
```
postgresql://admin:password@192.168.1.162:55432/oadbv5
```

**SMB Logs**:
```
smb://claude@192.168.1.162/openalex_logs
```

**SMB Backups**:
```
smb://claude@192.168.1.162/openalex_backups
```

### Common Remote Commands

```bash
# Check parser status
ssh -p 86 claude@192.168.1.162 "cd /volume1/docker/openalex/OA_clone && docker-compose run --rm parser python3 03_snapshot_parsing/orchestrator.py --status"

# View database size
psql -h 192.168.1.162 -p 55432 -U admin -d oadbv5 -c "SELECT pg_size_pretty(pg_database_size('oadbv5'));"

# List recent backups
ssh -p 86 claude@192.168.1.162 "ls -lht /volume2/postgres_backup/*.dump | head -10"

# Check container status
ssh -p 86 claude@192.168.1.162 "docker-compose -f /volume1/docker/openalex/OA_clone/docker-compose.yml ps"
```
