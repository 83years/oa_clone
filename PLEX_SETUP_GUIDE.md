# Plex Media Server Setup on UGREEN NAS (Docker)

## Overview
This guide will help you set up Plex Media Server in a Docker container on your UGREEN NASSync DXP4800 Plus, allowing it to run independently of your Mac.

---

## Prerequisites
- UGREEN NAS with Docker installed ✓
- SSH access to your NAS
- Media files stored at `/volume2/Media/Films` (HDD storage)
- Docker installed on `/volume1` (NVMe storage)
- Network access to NAS from devices you'll use to watch content

**Storage Configuration:**
- `/volume1` (NVMe) - Fast drives for Docker, Plex config, and transcode operations
- `/volume2` (HDD) - Large capacity drives for media file storage
- This is an optimal setup: fast operations on NVMe, bulk storage on HDD

---

## Step 1: Access Your NAS via SSH

From your Mac terminal:

```bash
ssh claude@192.168.1.162 -p 86
# Password: xf4WM6PV
```

---

## Step 2: Create Directory Structure for Plex

Once connected to the NAS, create directories for Plex configuration and verify your media location:

```bash
# Create Plex config directory
mkdir -p /volume1/docker/plex/config
mkdir -p /volume1/docker/plex/transcode

# Verify your media directory exists
ls -la /volume2/Media/Films

# If the path is different, adjust accordingly
# Common UGREEN paths: /volume2/Media/ or /mnt/Media/
```

**Note:** Find your actual media path by exploring:
```bash
find /volume2 -type d -name "Films" 2>/dev/null
# or
find /mnt -type d -name "Films" 2>/dev/null
```

---

## Step 3: Get Your Plex Claim Token (Optional but Recommended)

This allows Plex to automatically link to your account during setup.

1. On your Mac, visit: https://www.plex.tv/claim/
2. Log in with your Plex account (create one if needed)
3. Copy the claim token (starts with `claim-`)
4. **Important:** This token expires in 4 minutes, so have it ready before running the container

---

## Step 4: Create Docker Compose File

On the NAS, create a docker-compose file:

```bash
# Create directory for compose file
mkdir -p /volume1/docker/plex
cd /volume1/docker/plex

# Create the compose file
nano docker-compose.yml
```

Paste this configuration (adjust paths and token as needed):

```yaml
version: '3.8'

services:
  plex:
    image: lscr.io/linuxserver/plex:latest
    container_name: plex
    network_mode: host
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Europe/London  # Change to your timezone
      - VERSION=docker
      - PLEX_CLAIM=claim-XXXXXXXXXXXXXXXXXXXX  # Replace with your claim token or remove this line
    volumes:
      - /volume1/docker/plex/config:/config          # NVMe - Fast database/metadata
      - /volume1/docker/plex/transcode:/transcode    # NVMe - Fast transcoding operations
      - /volume2/Media/Films:/media/films            # HDD - Large media storage
    restart: unless-stopped
```

**Save and exit:** Press `Ctrl+X`, then `Y`, then `Enter`

---

## Step 5: Important Configuration Adjustments

### A. Find Your User ID (PUID) and Group ID (PGID)

```bash
id claude
# Output example: uid=1026(claude) gid=100(users)
# Use these numbers for PUID and PGID in the compose file
```

Edit the compose file and update PUID and PGID:
```bash
nano docker-compose.yml
# Change PUID=1000 to your uid
# Change PGID=1000 to your gid
```

### B. Set Your Timezone

Common options:
- `America/New_York`
- `America/Los_Angeles`
- `Europe/London`
- `Asia/Tokyo`
- `Australia/Sydney`

Find yours: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones

### C. Verify Media Path

Make absolutely sure the path on the left side of the volume mapping matches where your media actually is:
```bash
ls -la /volume2/Media/Films
# If this doesn't work, find the correct path and update the compose file
```

---

## Step 6: Launch Plex Container

```bash
# Make sure you're in the directory with docker-compose.yml
cd /volume1/docker/plex

# Pull the image and start the container
sudo docker-compose up -d

# Check if it's running
sudo docker ps | grep plex

# View logs to ensure it started correctly
docker logs plex
```

---

## Step 7: Initial Plex Setup

### Access Plex Web Interface

1. **From your Mac browser**, go to:
   ```
   http://192.168.1.162:32400/web
   ```

2. **If you used a claim token:** You should automatically be logged in

3. **If you didn't use a claim token or it expired:**
   - You may need to create an SSH tunnel:
   ```bash
   # On your Mac, run:
   ssh -L 32400:localhost:32400 claude@192.168.1.162 -p 86
   # Then access: http://localhost:32400/web
   ```

4. **Complete the setup wizard:**
   - Sign in to your Plex account
   - Name your server (e.g., "UGREEN Plex Server")
   - Add media libraries:
     - Click "Add Library"
     - Choose type (Movies)
     - Click "Browse for Media Folder"
     - Navigate to `/media/films` (this is how it appears inside the container)
     - Add additional folders if needed

5. **Important Settings to Configure:**
   - Go to Settings → Network
   - Check "Enable server on local network"
   - Verify "Secure connections" is set to "Preferred"
   - In "Custom server access URLs" you can add: `http://192.168.1.162:32400`

---

## Step 8: Verify Everything Works

### Test from Mac (while it's on)
1. Open browser to `http://192.168.1.162:32400/web`
2. Browse your library
3. Try playing a video

### Test Container Persistence
```bash
# SSH into NAS
ssh claude@192.168.1.162 -p 86

# Check container status
docker ps -a | grep plex

# Restart the container
docker restart plex

# Verify it comes back up
docker ps | grep plex
```

### Test with Mac Turned Off
1. Completely shut down your Mac
2. From another device (phone, tablet, smart TV):
   - Install the Plex app
   - Sign in to your account
   - Your server should appear
   - Try streaming content

---

## Step 9: Install Plex Apps on Other Devices

Download Plex apps:
- **iOS/iPad:** App Store → "Plex"
- **Android:** Play Store → "Plex"
- **Smart TV:** Search for "Plex" in your TV's app store
- **Roku/Fire TV/Apple TV:** Available in respective app stores

All devices should automatically discover your server when on the same network.

---

## Troubleshooting

### Container Won't Start
```bash
# Check logs
docker logs plex

# Common issues:
# 1. Port 32400 already in use
# 2. Permission issues with mounted volumes
# 3. Incorrect paths

# Fix permissions if needed
chown -R claude:users /volume1/docker/plex
```

### Can't Access from Web Browser
```bash
# Verify container is running
docker ps | grep plex

# Check if port is listening
netstat -tuln | grep 32400

# If not using network_mode: host, try this compose version instead:
# Change network_mode: host to:
    ports:
      - "32400:32400/tcp"
      - "1900:1900/udp"
      - "3005:3005/tcp"
      - "5353:5353/udp"
      - "8324:8324/tcp"
      - "32410:32410/udp"
      - "32412:32412/udp"
      - "32413:32413/udp"
      - "32414:32414/udp"
      - "32469:32469/tcp"
```

### Media Not Showing Up
```bash
# Verify path inside container
docker exec plex ls -la /media/films

# If empty, check your volume mapping in docker-compose.yml
# Make sure the path before the colon exists on the NAS

# Trigger a library scan from Plex web interface
# Settings → Library → Scan Library Files
```

### Container Doesn't Restart After NAS Reboot
```bash
# Check Docker service is enabled
systemctl status docker

# Verify restart policy
docker inspect plex | grep -A 5 RestartPolicy

# Should show: "Name": "unless-stopped"
```

---

## Maintenance Commands

```bash
# View logs
docker logs plex
docker logs -f plex  # Follow logs in real-time

# Restart container
docker restart plex

# Stop container
docker stop plex

# Start container
docker start plex

# Update Plex to latest version
cd /volume1/docker/plex
docker-compose pull
docker-compose up -d

# View resource usage
docker stats plex
```

---

## Adding More Media Libraries

1. Copy/move media to your NAS (e.g., TV Shows to `/volume2/Media/TV`)
2. Update `docker-compose.yml` to add the new volume:
   ```yaml
   volumes:
     - /volume1/docker/plex/config:/config          # NVMe
     - /volume1/docker/plex/transcode:/transcode    # NVMe
     - /volume2/Media/Films:/media/films            # HDD
     - /volume2/Media/TV:/media/tv                  # HDD - Add this line
   ```
3. Recreate container: `docker-compose up -d`
4. In Plex web interface, add new library pointing to `/media/tv`

---

## Security Recommendations

1. **Change default SSH password** if you haven't already
2. **Enable Plex authentication:** Settings → Network → "Require authentication"
3. **Use HTTPS:** Consider setting up a reverse proxy with SSL
4. **Limit remote access:** Settings → Remote Access → Configure as needed
5. **Regular updates:** Update the Plex container monthly
6. **Firewall:** Only expose necessary ports to the internet

---

## Remote Access (Optional)

If you want to access Plex from outside your home network:

1. **Enable in Plex:**
   - Settings → Remote Access
   - Click "Enable Remote Access"
   - Plex will try to configure automatically

2. **Manual Port Forwarding** (if automatic fails):
   - Log into your router
   - Forward port 32400 (TCP) to 192.168.1.162:32400
   - Return to Plex Settings → Remote Access
   - Click "Retry"

**Security Note:** Remote access exposes your server to the internet. Use a strong Plex account password.

---

## Performance Tips

1. **Optimal Storage Configuration:** Your setup is ideal:
   - Config/metadata on `/volume1` (NVMe) = Fast database operations
   - Transcode on `/volume1` (NVMe) = Fast video conversion
   - Media files on `/volume2` (HDD) = Large, affordable storage
2. **Direct Play:** Encourage direct play by using compatible formats (H264/AAC for broad compatibility) to minimize transcoding
3. **Hardware Transcoding:** Plex Pass required for hardware-accelerated transcoding
4. **Network:** Use wired Ethernet connection for NAS when possible for best streaming performance

---

## Summary

Your Plex server is now running in a Docker container on your NAS and will:
- ✓ Start automatically when the NAS boots
- ✓ Run independently of your Mac
- ✓ Be accessible from any device on your network
- ✓ Persist all settings and watch history

Your Mac can now be turned off completely, and Plex will continue serving media!

---

## Quick Reference

**NAS SSH:** `ssh claude@192.168.1.162 -p 86`

**Plex Web:** `http://192.168.1.162:32400/web`

**Docker Compose Location:** `/volume1/docker/plex/docker-compose.yml`

**Config Location (NVMe):** `/volume1/docker/plex/config`

**Media Location (HDD):** `/volume2/Media/Films`

**Logs:** `docker logs plex`

**Restart:** `docker restart plex`

**Update:** `cd /volume1/docker/plex && docker-compose pull && docker-compose up -d`
