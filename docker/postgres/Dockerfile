FROM postgres:16

# Install additional extensions if needed
RUN apt-get update && apt-get install -y \
    postgresql-16-pg-trgm \
    && rm -rf /var/lib/apt/lists/*

# Copy custom PostgreSQL configuration
COPY postgresql.conf /etc/postgresql/postgresql.conf

# Set custom config file location
CMD ["postgres", "-c", "config_file=/etc/postgresql/postgresql.conf"]
