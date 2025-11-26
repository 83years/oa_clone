FROM alpine:3.18

# Install PostgreSQL client and cron
RUN apk add --no-cache \
    postgresql16-client \
    bash \
    tzdata \
    && rm -rf /var/cache/apk/*

# Set timezone to UTC
ENV TZ=UTC

# Create backup directory
RUN mkdir -p /backups

# Copy backup script
COPY backup.sh /backup.sh
RUN chmod +x /backup.sh

# Copy crontab file
COPY crontab /etc/crontabs/root

# Create log file for cron
RUN touch /var/log/cron.log

# Start cron in foreground
CMD crond -f -l 2
