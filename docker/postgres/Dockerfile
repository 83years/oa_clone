FROM postgres:16


# Copy custom PostgreSQL configuration
COPY postgresql.conf /etc/postgresql/postgresql.conf

# Set custom config file location
CMD ["postgres", "-c", "config_file=/etc/postgresql/postgresql.conf"]
