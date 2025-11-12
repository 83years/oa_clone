import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from datetime import datetime

# Configuration
DB_HOST = '192.168.1.100'
DB_PORT = '55432'
DB_NAME = 'OADB'
ADMIN_USER = 'admin'
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'secure_password_123')
READONLY_USER = 'user1'
READONLY_PASSWORD = os.getenv('READONLY_PASSWORD', 'OAUserLetmein!234')

def create_database_and_users():
    """Create database and users with proper permissions"""
    print(f"[{datetime.now()}] Connecting to PostgreSQL...")
    
    # Connect to default postgres database
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database='postgres',  # Connect to default postgres database
        user=ADMIN_USER,
        password=ADMIN_PASSWORD
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    try:
        # Check if admin user needs to be a superuser (for creating databases)
        print(f"[{datetime.now()}] Checking user privileges...")
        cursor.execute(f"SELECT usesuper FROM pg_user WHERE usename = '{ADMIN_USER}';")
        is_superuser = cursor.fetchone()[0]

        if not is_superuser:
            print(f"[{datetime.now()}] Granting superuser privileges to {ADMIN_USER}...")
            cursor.execute(f"ALTER USER {ADMIN_USER} WITH SUPERUSER;")
        
        # Check if database exists and clean up user objects before dropping
        cursor.execute(f"""
            SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}');
        """)
        db_exists = cursor.fetchone()[0]

        if db_exists:
            print(f"[{datetime.now()}] Database exists, cleaning up user objects...")
            # Temporarily connect to OADB to clean up user1's objects
            cursor.close()
            conn.close()

            cleanup_conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME,
                user=ADMIN_USER,
                password=ADMIN_PASSWORD
            )
            cleanup_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cleanup_cursor = cleanup_conn.cursor()

            try:
                # Clean up user1's objects in OADB
                cleanup_cursor.execute(f"REASSIGN OWNED BY {READONLY_USER} TO {ADMIN_USER};")
                cleanup_cursor.execute(f"DROP OWNED BY {READONLY_USER} CASCADE;")
                print(f"[{datetime.now()}] ✅ User objects cleaned up in {DB_NAME}")
            except Exception as e:
                print(f"[{datetime.now()}] Note: {e}")
            finally:
                cleanup_cursor.close()
                cleanup_conn.close()

            # Reconnect to postgres database
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                database='postgres',
                user=ADMIN_USER,
                password=ADMIN_PASSWORD
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()

        # Terminate existing connections to the database if it exists
        print(f"[{datetime.now()}] Terminating existing connections...")
        cursor.execute(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{DB_NAME}'
              AND pid <> pg_backend_pid();
        """)

        # Drop database if exists
        print(f"[{datetime.now()}] Dropping existing database if present...")
        cursor.execute(f"DROP DATABASE IF EXISTS {DB_NAME};")

        # Drop read-only user
        print(f"[{datetime.now()}] Dropping and recreating read-only user '{READONLY_USER}'...")
        cursor.execute(f"DROP USER IF EXISTS {READONLY_USER};")
        cursor.execute(f"""
            CREATE USER {READONLY_USER} WITH 
            PASSWORD '{READONLY_PASSWORD}'
            LOGIN
            CONNECTION LIMIT 5;
        """)
        
        # Update admin user password if desired
        print(f"[{datetime.now()}] Updating admin user '{ADMIN_USER}' password...")
        cursor.execute(f"""
            ALTER USER {ADMIN_USER} WITH 
            PASSWORD '{ADMIN_PASSWORD}'
            CONNECTION LIMIT 10;
        """)
        
        # Create database
        print(f"[{datetime.now()}] Creating database '{DB_NAME}'...")
        cursor.execute(f"CREATE DATABASE {DB_NAME} OWNER {ADMIN_USER};")

        print(f"[{datetime.now()}] ✅ Database and users created successfully!")

    except Exception as e:
        print(f"❌ Error creating database: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

def create_tables_and_indexes():
    """Create all tables with indexes and constraints"""
    print(f"\n[{datetime.now()}] Creating tables and indexes...")
    
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=ADMIN_USER,
        password=ADMIN_PASSWORD
    )
    cursor = conn.cursor()
    
    try:
        # 1. WORKS TABLE
        print(f"[{datetime.now()}] Creating works table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS works (
                work_id VARCHAR(255) PRIMARY KEY,
                display_name TEXT,
                title TEXT,
                abstract TEXT,
                doi VARCHAR(255),
                publication_date DATE,
                publication_year INTEGER,
                type VARCHAR(100),
                is_oa_anywhere BOOLEAN,
                oa_status VARCHAR(100),
                oa_url TEXT,
                any_repository_has_fulltext BOOLEAN,
                source_display_name VARCHAR(500),
                host_organization VARCHAR(500),
                host_organization_name VARCHAR(500),
                host_organization_lineage TEXT,
                landing_page_url TEXT,
                license VARCHAR(100),
                version VARCHAR(100),
                referenced_works_count INTEGER,
                is_retracted BOOLEAN,
                language VARCHAR(100),
                language_id VARCHAR(255),
                first_page VARCHAR(255),
                last_page VARCHAR(255),
                volume VARCHAR(100),
                issue VARCHAR(100),
                keywords TEXT,
                sustainable_development_goals TEXT,
                grants TEXT,
                referenced_works_score INTEGER,
                cited_by_count INTEGER,
                created_date TIMESTAMP,
                updated_date TIMESTAMP,
                mesh_id TEXT,
                search_id VARCHAR(255),
                biblio_volume TEXT,
                biblio_issue TEXT,
                biblio_first_page TEXT,
                biblio_last_page TEXT,
                is_paratext BOOLEAN,
                fwci DECIMAL(12,7),
                citation_normalized_percentile_value DECIMAL(12,7),
                citation_normalized_percentile_top_1_percent BOOLEAN,
                citation_normalized_percentile_top_10_percent BOOLEAN,
                cited_by_percentile_year_min DECIMAL(5,2),
                cited_by_percentile_year_max DECIMAL(5,2),
                type_crossref VARCHAR(100),
                indexed_in TEXT,
                locations_count INTEGER,
                authors_count INTEGER,
                concepts_count INTEGER,
                topics_count INTEGER,
                has_fulltext BOOLEAN,
                countries_distinct_count INTEGER,
                institutions_distinct_count INTEGER,
                best_oa_pdf_url TEXT,
                best_oa_landing_page_url TEXT,
                best_oa_is_oa BOOLEAN,
                best_oa_version VARCHAR(100),
                best_oa_license VARCHAR(100),
                primary_location_is_accepted BOOLEAN,
                primary_location_is_published BOOLEAN,
                primary_location_pdf_url TEXT
            );
        """)
        
        # Enable trigram extension for text search
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        
        # 2. AUTHORS TABLE
        print(f"[{datetime.now()}] Creating authors table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS authors (
                author_id VARCHAR(255) PRIMARY KEY,
                display_name VARCHAR(500),
                orcid VARCHAR(100),
                works_count INTEGER,
                cited_by_count INTEGER,
                summary_stats_2yr_mean_citedness DECIMAL(12,7),
                summary_stats_h_index INTEGER,
                summary_stats_i10_index INTEGER,
                created_date TIMESTAMP,
                updated_date TIMESTAMP,
                gender VARCHAR(20),
                current_affiliation_id VARCHAR(255),
                current_affiliation_name VARCHAR(500),
                current_affiliation_country VARCHAR(100),
                current_affiliation_type VARCHAR(100),
                api_response_date DATE,
                api_source VARCHAR(100),
                most_cited_work TEXT,
                first_publication_year INTEGER,
                last_publication_year INTEGER,
                freq_corresponding_author DECIMAL(12,7),
                total_works INTEGER,
                total_citations INTEGER,
                corresponding_authorships INTEGER,
                career_length_years INTEGER,
                current INTEGER,
                career_stage_aff TEXT
            );
        """)
        
        # 3. INSTITUTIONS TABLE
        print(f"[{datetime.now()}] Creating institutions table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS institutions (
                institution_id VARCHAR(255) PRIMARY KEY,
                display_name VARCHAR(500),
                display_name_acronyms TEXT,
                display_name_alternatives TEXT,
                ror VARCHAR(100),
                ror_id VARCHAR(100),
                country_code VARCHAR(10),
                type VARCHAR(100),
                lineage TEXT,
                homepage_url TEXT,
                image_url TEXT,
                image_thumbnail_url TEXT,
                works_count INTEGER,
                cited_by_count INTEGER,
                created_date TIMESTAMP,
                updated_date TIMESTAMP,
                openalex TEXT, 
                grid TEXT, 
                wikipedia TEXT, 
                wikidata TEXT, 
                mag TEXT,
                summary_stats_2yr_mean_citedness DOUBLE PRECISION,
                summary_stats_h_index DOUBLE PRECISION,
                summary_stats_i10_index DOUBLE PRECISION,
                associated_institutions TEXT
            );
        """)
        
        # 4. INSTITUTION GEO TABLE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS institution_geo (
                institution_id TEXT PRIMARY KEY,
                city TEXT,
                geonames_city_id TEXT,
                region TEXT,
                country_code TEXT,
                country TEXT,
                latitude DECIMAL(9,6),
                longitude DECIMAL(9,6),
                FOREIGN KEY (institution_id) REFERENCES institutions(institution_id) ON DELETE CASCADE
            );
        """)
        
        # 5. SOURCES TABLE
        print(f"[{datetime.now()}] Creating sources table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                source_id VARCHAR(255) PRIMARY KEY,
                display_name VARCHAR(500),
                issn_l VARCHAR(100),
                host VARCHAR(255),
                host_organization VARCHAR(500),
                host_organization_lineage TEXT,
                type VARCHAR(100),
                issn TEXT,
                host_organization_name TEXT,
                is_oa TEXT,
                is_in_doaj TEXT,
                works_count INTEGER,
                cited_by_count INTEGER,
                updated_date TIMESTAMP
            );
        """)
        
        # 6. PUBLISHERS TABLE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS publishers (
                publisher_id VARCHAR(255) PRIMARY KEY,
                display_name VARCHAR(500),
                country_code VARCHAR(10),
                hierarchy_level TEXT
            );
        """)
        
        # 7. FUNDERS TABLE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS funders (
                funder_id VARCHAR(255) PRIMARY KEY,
                display_name VARCHAR(500),
                country_code VARCHAR(10),
                description TEXT,
                homepage_url TEXT
            );
        """)
        
        # 8. CONCEPTS TABLE
        print(f"[{datetime.now()}] Creating concepts table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS concepts (
                concept_id VARCHAR(255) PRIMARY KEY,
                display_name VARCHAR(500),
                level INTEGER,
                score DECIMAL(12,7),
                wikidata VARCHAR(100), 
                description TEXT,
                works_count INTEGER,
                cited_by_count INTEGER,
                updated_date TIMESTAMP
            );
        """)
        
        # 9. TOPICS TABLE
        print(f"[{datetime.now()}] Creating topics table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS topics (
                topic_id VARCHAR(255) PRIMARY KEY,
                display_name VARCHAR(500),
                score DECIMAL(12,7),
                subfield_id VARCHAR(255),
                subfield_display_name VARCHAR(500),
                field_id VARCHAR(255),
                field_display_name VARCHAR(500),
                domain_id VARCHAR(255),
                domain_display_name VARCHAR(500), 
                description TEXT, 
                keywords TEXT, 
                works_count INTEGER,
                cited_by_count INTEGER,
                updated_date TIMESTAMP
            );
        """)
        
        # 10. SEARCH_METADATA TABLE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_metadata (
                search_id VARCHAR(255) PRIMARY KEY,
                search_term TEXT,
                publication_year INTEGER,
                search_date TIMESTAMP,
                papers_found INTEGER,
                papers_added INTEGER
            );
        """)
        
        # 11. ALTERNATE_IDS TABLE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alternate_ids (
                alt_id SERIAL PRIMARY KEY,
                work_id VARCHAR(255) REFERENCES works(work_id) ON DELETE CASCADE,
                id_type VARCHAR(100),
                id_value VARCHAR(255)
            );
        """)
        
        # 12. WORK_KEYWORDS TABLE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS work_keywords (
                work_id VARCHAR(255) REFERENCES works(work_id) ON DELETE CASCADE,
                keyword VARCHAR(255),
                PRIMARY KEY (work_id, keyword)
            );
        """)
        
        # 13. AUTHORSHIP TABLE
        print(f"[{datetime.now()}] Creating relationship tables...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS authorship (
                work_id VARCHAR(255) REFERENCES works(work_id) ON DELETE CASCADE,
                author_id VARCHAR(255) REFERENCES authors(author_id) ON DELETE CASCADE,
                author_position TEXT,
                is_corresponding BOOLEAN,
                raw_affiliation_string TEXT,
                institution_id VARCHAR(255),
                PRIMARY KEY (work_id, author_id)
            );
        """)
        
        # 14. CITATIONS TABLE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS citations (
                citing_work_id VARCHAR(255) REFERENCES works(work_id) ON DELETE CASCADE,
                cited_work_id VARCHAR(255) REFERENCES works(work_id) ON DELETE CASCADE,
                PRIMARY KEY (citing_work_id, cited_work_id)
            );
        """)
        
        # 15. WORK_TOPICS TABLE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS work_topics (
                work_id VARCHAR(255) REFERENCES works(work_id) ON DELETE CASCADE,
                topic_id VARCHAR(255) REFERENCES topics(topic_id) ON DELETE CASCADE,
                score DECIMAL(12,7),
                is_primary_topic BOOLEAN DEFAULT FALSE,
                PRIMARY KEY (work_id, topic_id)
            );
        """)
        
        # 16. WORK_CONCEPTS TABLE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS work_concepts (
                work_id VARCHAR(255) REFERENCES works(work_id) ON DELETE CASCADE,
                concept_id VARCHAR(255) REFERENCES concepts(concept_id) ON DELETE CASCADE,
                score DECIMAL(12,7),
                PRIMARY KEY (work_id, concept_id)
            );
        """)
        
        # 17. AUTHOR_TOPICS TABLE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS author_topics (
                author_id VARCHAR(255) REFERENCES authors(author_id) ON DELETE CASCADE,
                topic_id VARCHAR(255) REFERENCES topics(topic_id) ON DELETE CASCADE,
                score DECIMAL(12,7),
                work_count INTEGER,
                recent_work_count INTEGER,
                PRIMARY KEY (author_id, topic_id)
            );
        """)
        
        # 18. AUTHOR_CONCEPTS TABLE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS author_concepts (
                author_id VARCHAR(255) REFERENCES authors(author_id) ON DELETE CASCADE,
                concept_id VARCHAR(255) REFERENCES concepts(concept_id) ON DELETE CASCADE,
                score DECIMAL(20,7),
                work_count INTEGER,
                PRIMARY KEY (author_id, concept_id)
            );
        """)
        
        # 19. AUTHOR_INSTITUTIONS TABLE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS author_institutions (
                author_id VARCHAR(255) REFERENCES authors(author_id) ON DELETE CASCADE,
                institution_id VARCHAR(255) REFERENCES institutions(institution_id) ON DELETE CASCADE,
                start_date DATE,
                end_date DATE,
                affiliation_string TEXT,
                PRIMARY KEY (author_id, institution_id)
            );
        """)
        
        # 20. WORK_FUNDERS TABLE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS work_funders (
                work_id VARCHAR(255) REFERENCES works(work_id) ON DELETE CASCADE,
                funder_id VARCHAR(255) REFERENCES funders(funder_id) ON DELETE CASCADE,
                award_id VARCHAR(1000),
                PRIMARY KEY (work_id, funder_id)
            );
        """)
        
        # 21. WORK_SOURCES TABLE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS work_sources (
                work_id VARCHAR(255) REFERENCES works(work_id) ON DELETE CASCADE,
                source_id VARCHAR(255) REFERENCES sources(source_id) ON DELETE CASCADE,
                PRIMARY KEY (work_id, source_id)
            );
        """)
        
        # 22. SOURCE_PUBLISHERS TABLE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS source_publishers (
                source_id VARCHAR(255) REFERENCES sources(source_id) ON DELETE CASCADE,
                publisher_id VARCHAR(255) REFERENCES publishers(publisher_id) ON DELETE CASCADE,
                PRIMARY KEY (source_id, publisher_id)
            );
        """)
        
        # 23. INSTITUTION_HIERARCHY TABLE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS institution_hierarchy (
                parent_institution_id VARCHAR(255) REFERENCES institutions(institution_id) ON DELETE CASCADE,
                child_institution_id VARCHAR(255) REFERENCES institutions(institution_id) ON DELETE CASCADE,
                hierarchy_level INTEGER,
                relationship_type VARCHAR(100),
                PRIMARY KEY (parent_institution_id, child_institution_id)
            );
        """)
        
        # 24. TOPIC_HIERARCHY TABLE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS topic_hierarchy (
                parent_topic_id VARCHAR(255) REFERENCES topics(topic_id) ON DELETE CASCADE,
                child_topic_id VARCHAR(255) REFERENCES topics(topic_id) ON DELETE CASCADE,
                hierarchy_level INTEGER,
                PRIMARY KEY (parent_topic_id, child_topic_id)
            );
        """)
        
        # 25. REFERENCED_WORKS TABLE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS referenced_works (
                work_id VARCHAR(255) REFERENCES works(work_id) ON DELETE CASCADE,
                referenced_work_id VARCHAR(255),
                PRIMARY KEY (work_id, referenced_work_id)
            );
        """)
        
        # 26. RELATED_WORKS TABLE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS related_works (
                work_id VARCHAR(255) REFERENCES works(work_id) ON DELETE CASCADE,
                related_work_id VARCHAR(255),
                PRIMARY KEY (work_id, related_work_id)
            );
        """)
        
        # 27. CITATIONS_BY_YEAR TABLE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS citations_by_year (
                work_id VARCHAR(255) REFERENCES works(work_id) ON DELETE CASCADE,
                year INTEGER,
                citation_count INTEGER,
                PRIMARY KEY (work_id, year)
            );
        """)
        
        # 28. APC TABLE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS apc (
                work_id VARCHAR(255) PRIMARY KEY REFERENCES works(work_id) ON DELETE CASCADE,
                value DECIMAL(15,2),
                currency VARCHAR(100),
                value_usd DECIMAL(15,2),
                provenance VARCHAR(100)
            );
        """)
        
        # 29. SEARCH_INDEX TABLE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_index (
                search_term_id SERIAL PRIMARY KEY,
                search_term VARCHAR(500),
                entity_type VARCHAR(100),
                entity_id VARCHAR(255),
                entity_name TEXT,
                search_vector TSVECTOR
            );
        """)
        
        # 30. AUTHOR_NAME_VARIANTS TABLE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS author_name_variants (
                variant_id SERIAL PRIMARY KEY,
                author_id VARCHAR(255) REFERENCES authors(author_id) ON DELETE CASCADE,
                name_variant VARCHAR(500),
                variant_type VARCHAR(100),
                confidence_score DECIMAL(12,7)
            );
        """)
        
        # 31. AUTHORS_WORKS_BY_YEAR TABLE
        print(f"[{datetime.now()}] Creating authors_works_by_year table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS authors_works_by_year (
                author_id VARCHAR(255) REFERENCES authors(author_id) ON DELETE CASCADE,
                year INTEGER,
                works_count INTEGER,
                oa_works_count INTEGER,
                cited_by_count INTEGER,
                PRIMARY KEY (author_id, year)
            );
        """)
        
        conn.commit()
        print(f"[{datetime.now()}] ✅ All tables and indexes created successfully!")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error creating tables: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

def create_audit_logging():
    """Create audit logging tables and triggers for data modifications"""
    print(f"\n[{datetime.now()}] Setting up audit logging...")
    
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=ADMIN_USER,
        password=ADMIN_PASSWORD
    )
    cursor = conn.cursor()
    
    try:
        # Create audit log table for data modifications
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_modification_log (
                log_id SERIAL PRIMARY KEY,
                username TEXT NOT NULL,
                table_name TEXT,
                action TEXT,
                ip_address INET,
                modified_at TIMESTAMP DEFAULT NOW(),
                row_count INTEGER
            );
        """)
        
        # Create audit function for INSERT/UPDATE/DELETE operations
        cursor.execute("""
            CREATE OR REPLACE FUNCTION log_data_modifications()
            RETURNS TRIGGER AS $$
            BEGIN
                INSERT INTO data_modification_log (username, table_name, action, ip_address)
                VALUES (
                    current_user,
                    TG_TABLE_NAME,
                    TG_OP,
                    inet_client_addr()
                );
                
                IF TG_OP = 'DELETE' THEN
                    RETURN OLD;
                ELSE
                    RETURN NEW;
                END IF;
            END;
            $$ LANGUAGE plpgsql;
        """)
        
        # Create triggers for important tables
        important_tables = ['works', 'authors', 'institutions', 'authorship', 'citations']
        
        for table in important_tables:
            cursor.execute(f"""
                DROP TRIGGER IF EXISTS {table}_modification_trigger ON {table};
                CREATE TRIGGER {table}_modification_trigger
                    AFTER INSERT OR UPDATE OR DELETE ON {table}
                    FOR EACH STATEMENT
                    EXECUTE FUNCTION log_data_modifications();
            """)
            print(f"  ✅ Created modification trigger for {table}")
        
        conn.commit()
        print(f"\n[{datetime.now()}] ✅ Audit logging configured successfully!")
        print(f"\n  📝 Note: Data modifications (INSERT/UPDATE/DELETE) are logged in 'data_modification_log' table")
        print(f"  📝 Note: SELECT operations require PostgreSQL logging to be enabled")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error setting up audit logging: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

def enable_postgresql_logging():
    """Display instructions for enabling PostgreSQL query logging"""
    print(f"\n[{datetime.now()}] PostgreSQL Logging Configuration Required")
    print("="*70)
    print("\nTo audit SELECT queries, add these settings to postgresql.conf:")
    print("\n# Logging Configuration")
    print("logging_collector = on")
    print("log_directory = 'pg_log'")
    print("log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'")
    print("log_statement = 'all'  # Options: none, ddl, mod, all")
    print("log_line_prefix = '%t [%p] %u@%d [%h] '")
    print("log_connections = on")
    print("log_disconnections = on")
    print("log_duration = on")
    print("log_min_duration_statement = 0  # Log all queries (0ms+)")
    print("\n# For production, consider:")
    print("# log_statement = 'mod'  # Only log data-modifying statements")
    print("# log_min_duration_statement = 1000  # Only log slow queries (1s+)")
    
    print("\n" + "="*70)
    print("Alternative: Enable logging for specific users only")
    print("="*70)
    print(f"\nTo log only '{READONLY_USER}' queries, run these SQL commands:")
    print(f"ALTER USER {READONLY_USER} SET log_statement = 'all';")
    print(f"ALTER USER {READONLY_USER} SET log_min_duration_statement = 0;")
    
    print("\n" + "="*70)
    print("Viewing Logs")
    print("="*70)
    print("\n# Find log directory:")
    print("SHOW log_directory;")
    print("\n# View recent logs:")
    print("tail -f /var/lib/postgresql/data/pg_log/postgresql-*.log")
    print("\n# Or use pgBadger for log analysis:")
    print("pgbadger /var/lib/postgresql/data/pg_log/postgresql-*.log")
    
    print("\n⚠️  After editing postgresql.conf, restart PostgreSQL:")
    print("sudo systemctl restart postgresql")
    print("="*70 + "\n")

def setup_user_permissions():
    """Configure read-only permissions for user account"""
    print(f"\n[{datetime.now()}] Configuring user permissions...")
    
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=ADMIN_USER,
        password=ADMIN_PASSWORD
    )
    cursor = conn.cursor()
    
    try:
        # Grant connect permission
        cursor.execute(f"GRANT CONNECT ON DATABASE {DB_NAME} TO {READONLY_USER};")
        
        # Grant schema usage
        cursor.execute(f"GRANT USAGE ON SCHEMA public TO {READONLY_USER};")
        
        # Revoke all existing permissions
        cursor.execute(f"REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM {READONLY_USER};")
        
        # Grant SELECT on works table only
        cursor.execute(f"GRANT SELECT ON works TO {READONLY_USER};")
        
        # Grant SELECT on modification log so user can see modifications (if relevant)
        cursor.execute(f"GRANT SELECT ON data_modification_log TO {READONLY_USER};")
        
        # Enable Row Level Security on modification log
        cursor.execute("""
            ALTER TABLE data_modification_log ENABLE ROW LEVEL SECURITY;
        """)
        
        # Drop existing policy if it exists
        cursor.execute("""
            DROP POLICY IF EXISTS user_can_see_own_modifications ON data_modification_log;
        """)
        
        # Create policy for read-only user
        cursor.execute(f"""
            CREATE POLICY user_can_see_own_modifications ON data_modification_log
                FOR SELECT
                TO {READONLY_USER}
                USING (username = current_user);
        """)
        
        conn.commit()
        print(f"[{datetime.now()}] ✅ User permissions configured!")
        print(f"  ✅ User '{READONLY_USER}' can SELECT from 'works' table only")
        print(f"  ✅ User '{READONLY_USER}' can view their own modification logs")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error configuring permissions: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

def verify_setup():
    """Verify the database setup"""
    print(f"\n[{datetime.now()}] Verifying setup...")
    
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=ADMIN_USER,
        password=ADMIN_PASSWORD
    )
    cursor = conn.cursor()
    
    try:
        # Count tables
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
        """)
        table_count = cursor.fetchone()[0]
        print(f"  ✅ Total tables created: {table_count}")

        # Count indexes
        cursor.execute("""
            SELECT COUNT(*) FROM pg_indexes
            WHERE schemaname = 'public';
        """)
        index_count = cursor.fetchone()[0]
        print(f"  ✅ Total indexes created: {index_count}")

        # Count triggers
        cursor.execute("""
            SELECT COUNT(*) FROM pg_trigger
            WHERE tgname NOT LIKE 'pg_%';
        """)
        trigger_count = cursor.fetchone()[0]
        print(f"  ✅ Total triggers created: {trigger_count}")
        
        # Verify user permissions
        cursor.execute(f"""
            SELECT table_name, privilege_type
            FROM information_schema.role_table_grants
            WHERE grantee = '{READONLY_USER}'
            ORDER BY table_name;
        """)
        permissions = cursor.fetchall()
        print(f"  ✅ Read-only user permissions:")
        for table, privilege in permissions:
            print(f"    - {privilege} on {table}")

        # Check if logging tables exist
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'data_modification_log'
            );
        """)
        log_table_exists = cursor.fetchone()[0]
        if log_table_exists:
            print(f"  ✅ Audit logging table 'data_modification_log' created")

        print(f"\n[{datetime.now()}] ✅ Setup verification complete!")
        
    except Exception as e:
        print(f"❌ Error during verification: {e}")
    finally:
        cursor.close()
        conn.close()

def print_connection_info():
    """Print connection information and security notes"""
    print("\n" + "="*70)
    print("✅ DATABASE SETUP COMPLETE!")
    print("="*70)
    print(f"\nDatabase: {DB_NAME}")
    print(f"Host: {DB_HOST}")
    print(f"Port: {DB_PORT}")
    print(f"\nAdmin User: {ADMIN_USER}")
    print(f"Admin Password: {ADMIN_PASSWORD}")
    print(f"\nRead-Only User: {READONLY_USER}")
    print(f"Read-Only Password: {READONLY_PASSWORD}")
    
    print("\n" + "="*70)
    print("🔒 SECURITY CONFIGURATION REQUIRED")
    print("="*70)
    print("\n1. Edit postgresql.conf:")
    print("   listen_addresses = '*'")
    print("\n2. Edit pg_hba.conf (add these lines):")
    print(f"   # Admin access from local network only")
    print(f"   host    {DB_NAME}    {ADMIN_USER}    192.168.1.0/24    scram-sha-256")
    print(f"   host    {DB_NAME}    {ADMIN_USER}    0.0.0.0/0          reject")
    print(f"   ")
    print(f"   # Read-only user from internet (restrict to specific IPs if possible)")
    print(f"   host    {DB_NAME}    {READONLY_USER}    0.0.0.0/0          scram-sha-256")
    print(f"   # OR restrict to specific IPs:")
    print(f"   # host    {DB_NAME}    {READONLY_USER}    203.0.113.45/32    scram-sha-256")
    
    print("\n3. Enable SSL in postgresql.conf:")
    print("   ssl = on")
    print("   ssl_cert_file = '/path/to/server.crt'")
    print("   ssl_key_file = '/path/to/server.key'")
    
    print("\n4. Restart PostgreSQL:")
    print("   sudo systemctl restart postgresql")
    
    print("\n5. Configure router port forwarding:")
    print(f"   Forward port {DB_PORT} to {DB_HOST}:{DB_PORT}")
    
    print("\n" + "="*70)
    print("PYTHON CONNECTION EXAMPLES")
    print("="*70)
    
    print("\n# Admin connection (local network only):")
    print(f"""
DB_CONFIG_ADMIN = {{
    'host': '{DB_HOST}',
    'port': '{DB_PORT}',
    'database': '{DB_NAME}',
    'user': '{ADMIN_USER}',
    'password': os.getenv('ADMIN_PASSWORD'),
    'sslmode': 'require'
}}
""")
    
    print("\n# Read-only connection (internet access):")
    print(f"""
DB_CONFIG_READONLY = {{
    'host': 'your-public-ip-or-domain.com',  # Update with your public IP
    'port': '{DB_PORT}',
    'database': '{DB_NAME}',
    'user': '{READONLY_USER}',
    'password': os.getenv('READONLY_PASSWORD'),
    'sslmode': 'require',
    'connect_timeout': 10
}}
""")
    
    print("\n" + "="*70)
    print("📊 AUDIT LOGGING")
    print("="*70)
    print("\n📊 Data Modification Logging:")
    print("  ✅ INSERT/UPDATE/DELETE operations are logged in 'data_modification_log'")
    print("\nTo view modification logs:")
    print("  SELECT * FROM data_modification_log ORDER BY modified_at DESC LIMIT 20;")
    print("\nTo view logs for a specific user:")
    print(f"  SELECT * FROM data_modification_log WHERE username = '{READONLY_USER}';")
    print("\nTo view logs for a specific table:")
    print("  SELECT * FROM data_modification_log WHERE table_name = 'works';")
    
    print("\n📊 SELECT Query Logging:")
    print("  ⚠️  Requires PostgreSQL logging to be enabled (see instructions above)")
    print("  ✅ Run enable_postgresql_logging() for detailed instructions")
    
    print("\n" + "="*70)
    print("QUERY LOGGING QUICK START")
    print("="*70)
    print("\nOption 1: Enable logging for read-only user only (recommended):")
    print(f"  ALTER USER {READONLY_USER} SET log_statement = 'all';")
    print(f"  ALTER USER {READONLY_USER} SET log_min_duration_statement = 0;")
    
    print("\nOption 2: Enable logging for all users:")
    print("  Edit postgresql.conf and add:")
    print("    log_statement = 'all'")
    print("    log_connections = on")
    
    print("\nAfter changes, restart PostgreSQL:")
    print("  sudo systemctl restart postgresql")
    
    print("\n" + "="*70)
    print("⚠️  IMPORTANT SECURITY REMINDERS")
    print("="*70)
    print("1. ✅ Change default passwords immediately")
    print("2. ✅ Use environment variables for passwords, never hardcode")
    print("3. ✅ Enable SSL/TLS for all connections")
    print("4. ✅ Restrict admin user to local network only")
    print("5. ✅ Use strong, unique passwords (20+ characters)")
    print("6. ✅ Whitelist specific IP addresses when possible")
    print("7. ✅ Regularly review audit logs")
    print("8. ✅ Keep PostgreSQL updated")
    print("9. ✅ Consider using a VPN instead of direct internet access")
    print("10. ✅ Implement database backups")
    print("11. ✅ Enable PostgreSQL logging for SELECT queries")
    print("12. ✅ Monitor log files regularly for suspicious activity")
    print("="*70 + "\n")

def create_log_analysis_views():
    """Create helpful views for analyzing audit logs"""
    print(f"\n[{datetime.now()}] Creating log analysis views...")
    
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=ADMIN_USER,
        password=ADMIN_PASSWORD
    )
    cursor = conn.cursor()
    
    try:
        # View for daily modification summary
        cursor.execute("""
            CREATE OR REPLACE VIEW daily_modification_summary AS
            SELECT 
                DATE(modified_at) as date,
                username,
                table_name,
                action,
                COUNT(*) as operation_count
            FROM data_modification_log
            GROUP BY DATE(modified_at), username, table_name, action
            ORDER BY date DESC, operation_count DESC;
        """)
        
        # View for user activity summary
        cursor.execute("""
            CREATE OR REPLACE VIEW user_activity_summary AS
            SELECT 
                username,
                COUNT(*) as total_operations,
                COUNT(DISTINCT table_name) as tables_accessed,
                MIN(modified_at) as first_access,
                MAX(modified_at) as last_access,
                COUNT(DISTINCT DATE(modified_at)) as days_active
            FROM data_modification_log
            GROUP BY username
            ORDER BY total_operations DESC;
        """)
        
        # View for recent suspicious activity
        cursor.execute("""
            CREATE OR REPLACE VIEW recent_modifications AS
            SELECT 
                log_id,
                username,
                table_name,
                action,
                ip_address,
                modified_at,
                EXTRACT(EPOCH FROM (NOW() - modified_at))/60 as minutes_ago
            FROM data_modification_log
            WHERE modified_at > NOW() - INTERVAL '24 hours'
            ORDER BY modified_at DESC;
        """)
        
        # Grant read-only user access to their own activity views
        cursor.execute(f"GRANT SELECT ON daily_modification_summary TO {READONLY_USER};")
        cursor.execute(f"GRANT SELECT ON user_activity_summary TO {READONLY_USER};")
        cursor.execute(f"GRANT SELECT ON recent_modifications TO {READONLY_USER};")
        
        conn.commit()
        print(f"[{datetime.now()}] ✅ Log analysis views created!")
        print(f"  ✅ daily_modification_summary")
        print(f"  ✅ user_activity_summary")
        print(f"  ✅ recent_modifications")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error creating log analysis views: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

def main():
    """Main execution function"""
    try:
        print("="*70)
        print("OpenAlex Database Setup Script")
        print("="*70)
        
        # Step 1: Create database and users
        create_database_and_users()
        
        # Step 2: Create all tables and indexes
        create_tables_and_indexes()
        
        # Step 3: Setup audit logging for data modifications
        create_audit_logging()
        
        # Step 4: Create helpful log analysis views
        create_log_analysis_views()
        
        # Step 5: Configure user permissions
        setup_user_permissions()
        
        # Step 6: Verify setup
        verify_setup()
        
        # Step 7: Display PostgreSQL logging instructions
        enable_postgresql_logging()
        
        # Step 8: Print connection info
        print_connection_info()
        
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        print("Please check the error messages above and try again.")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("✅ Database setup completed successfully!")
        print("\n📝 Next Steps:")
        print("  1. Configure PostgreSQL logging (see instructions above)")
        print("  2. Update pg_hba.conf for network access")
        print("  3. Enable SSL certificates")
        print("  4. Restart PostgreSQL")
        print("  5. Test connections from both local and remote machines")
    else:
        print("❌ Database setup failed. Please review errors above.")