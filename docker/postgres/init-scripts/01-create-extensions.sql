-- Initialize PostgreSQL extensions for OpenAlex database
-- This script runs automatically when the container is first created

-- Enable pg_trgm extension for trigram text search and fuzzy matching
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Enable pg_stat_statements for query performance monitoring
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'OpenAlex database extensions initialized successfully';
    RAISE NOTICE '  - pg_trgm: enabled (trigram text search)';
    RAISE NOTICE '  - pg_stat_statements: enabled (query monitoring)';
END $$;
