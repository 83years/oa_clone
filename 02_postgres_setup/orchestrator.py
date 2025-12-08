import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
import sys
import time
from datetime import datetime

# Import centralized configuration
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Database configuration from centralized config
DB_HOST = config.DB_CONFIG['host']
DB_PORT = config.DB_CONFIG['port']
DB_NAME = config.DB_CONFIG['database']
ADMIN_USER = config.DB_CONFIG['user']
ADMIN_PASSWORD = config.DB_CONFIG['password']
READONLY_USER = os.getenv('READONLY_USER', 'user1')
READONLY_PASSWORD = os.getenv('READONLY_PASSWORD', 'OAUserLetmein!234')

def create_database():
    """Create OADB2 database"""
    print(f"[{datetime.now()}] Connecting to PostgreSQL...")

    # Connect to default postgres database
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database='postgres',
        user=ADMIN_USER,
        password=ADMIN_PASSWORD
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    try:
        # Check if database exists
        cursor.execute(f"""
            SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}');
        """)
        db_exists = cursor.fetchone()[0]

        if db_exists:
            print(f"[{datetime.now()}] Database {DB_NAME} already exists. Terminating connections...")
            # Terminate existing connections
            cursor.execute(f"""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = '{DB_NAME}'
                  AND pid <> pg_backend_pid();
            """)

            # Drop database
            print(f"[{datetime.now()}] Dropping existing database...")
            cursor.execute(f"DROP DATABASE IF EXISTS {DB_NAME};")

        # Create database
        print(f"[{datetime.now()}] Creating database '{DB_NAME}'...")
        cursor.execute(f"CREATE DATABASE {DB_NAME} OWNER {ADMIN_USER};")

        print(f"[{datetime.now()}] ✅ Database created successfully!")
        print(f"[{datetime.now()}] Waiting for database to be ready...")
        time.sleep(2)  # Give PostgreSQL time to fully initialize the database

    except Exception as e:
        print(f"❌ Error creating database: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

def create_tables_no_constraints():
    """Create all tables WITHOUT any constraints (no PKs, no FKs, minimal indexes)"""
    print(f"\n[{datetime.now()}] Creating tables without constraints...")

    # Try to connect with retries
    conn = None
    for attempt in range(3):
        try:
            print(f"[{datetime.now()}] Connecting to {DB_NAME} database (attempt {attempt + 1}/3)...")
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME,
                user=ADMIN_USER,
                password=ADMIN_PASSWORD
            )
            print(f"[{datetime.now()}] ✅ Connected successfully!")
            break
        except Exception as e:
            if attempt < 2:
                print(f"[{datetime.now()}] Connection failed, retrying in 2 seconds...")
                time.sleep(2)
            else:
                print(f"❌ Could not connect after 3 attempts: {e}")
                raise

    cursor = conn.cursor()

    try:
        # Enable trigram extension for text search (needed for potential queries)
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

        # PHASE 0: SMALL/REFERENCE TABLES (Parent entities - load first)

        # 1. TOPICS TABLE
        print(f"[{datetime.now()}] Creating topics table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS topics (
                topic_id VARCHAR(255),
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

        # 2. CONCEPTS TABLE
        print(f"[{datetime.now()}] Creating concepts table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS concepts (
                concept_id VARCHAR(255),
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

        # 3. PUBLISHERS TABLE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS publishers (
                publisher_id VARCHAR(255),
                display_name VARCHAR(500),
                country_code VARCHAR(10),
                hierarchy_level TEXT
            );
        """)

        # 4. FUNDERS TABLE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS funders (
                funder_id VARCHAR(255),
                display_name VARCHAR(500),
                country_code VARCHAR(10),
                description TEXT,
                homepage_url TEXT
            );
        """)

        # 5. SOURCES TABLE
        print(f"[{datetime.now()}] Creating sources table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                source_id VARCHAR(255),
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

        # 6. INSTITUTIONS TABLE
        print(f"[{datetime.now()}] Creating institutions table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS institutions (
                institution_id VARCHAR(255),
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

        # 7. INSTITUTION GEO TABLE - COMMENTED OUT (not populated from snapshot)
        # Will be created when needed for geographic analysis
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS institution_geo (
                institution_id TEXT,
                city TEXT,
                geonames_city_id TEXT,
                region TEXT,
                country_code TEXT,
                country TEXT,
                latitude DECIMAL(9,6),
                longitude DECIMAL(9,6)
            );
        """)

        # PHASE 1: LARGE ENTITY TABLES

        # 8. AUTHORS TABLE - COMMENTED OUT (not populated from snapshot)
        # Authors data is captured in author_names table from works parsing
        # This table will be built later from aggregated authorship data
        # print(f"[{datetime.now()}] Creating authors table...")
        # cursor.execute("""
        #     CREATE TABLE IF NOT EXISTS authors (
        #         author_id VARCHAR(255),
        #         display_name VARCHAR(500),
        #         orcid VARCHAR(100),
        #         forenames_extracted TEXT,
        #         forename_confidence NUMERIC(5,4),
        #         works_count INTEGER,
        #         cited_by_count INTEGER,
        #         summary_stats_2yr_mean_citedness DECIMAL(15,7),
        #         summary_stats_h_index INTEGER,
        #         summary_stats_i10_index INTEGER,
        #         created_date TIMESTAMP,
        #         updated_date TIMESTAMP,
        #         gender VARCHAR(20),
        #         current_affiliation_id VARCHAR(255),
        #         current_affiliation_name VARCHAR(500),
        #         current_affiliation_country VARCHAR(100),
        #         current_affiliation_type VARCHAR(100),
        #         api_response_date DATE,
        #         api_source VARCHAR(100),
        #         most_cited_work TEXT,
        #         first_publication_year INTEGER,
        #         last_publication_year INTEGER,
        #         freq_corresponding_author DECIMAL(12,7),
        #         total_works INTEGER,
        #         total_citations INTEGER,
        #         corresponding_authorships INTEGER,
        #         career_length_years INTEGER,
        #         current INTEGER,
        #         career_stage_aff TEXT
        #     );
        # """)

        # 9. WORKS TABLE
        print(f"[{datetime.now()}] Creating works table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS works (
                work_id VARCHAR(255),
                display_name TEXT,
                title TEXT,
                abstract TEXT,
                doi VARCHAR(1000),
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
                first_page VARCHAR(500),
                last_page VARCHAR(500),
                volume VARCHAR(1000),
                issue TEXT,
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
                primary_location_pdf_url TEXT,
                has_content_pdf BOOLEAN,
                has_content_grobid_xml BOOLEAN,
                topics_key BIGINT
            );
        """)

        # PHASE 2: RELATIONSHIP/JOINING TABLES

        # 10. AUTHORSHIP TABLE
        print(f"[{datetime.now()}] Creating relationship tables...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS authorship (
                work_id VARCHAR(255),
                author_id VARCHAR(255),
                author_position TEXT,
                is_corresponding BOOLEAN,
                raw_affiliation_string TEXT,
                raw_author_name TEXT,
                author_display_name TEXT
            );
        """)

        # 10b. AUTHORSHIP_INSTITUTIONS TABLE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS authorship_institutions (
                work_id VARCHAR(255),
                author_id VARCHAR(255),
                institution_id VARCHAR(255),
                country_code VARCHAR(10)
            );
        """)

        # 10c. AUTHOR_NAMES TABLE (ENHANCED - includes country and initial detection)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS author_names (
                author_id VARCHAR(255),
                work_id VARCHAR(255),
                raw_author_name TEXT,
                display_name TEXT,
                publication_year INTEGER,
                forename TEXT,
                lastname TEXT,
                country_code VARCHAR(10),
                forename_is_initial BOOLEAN
            );
        """)

        # 10e. WORK_LOCATIONS TABLE (NEW - MEDIUM PRIORITY)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS work_locations (
                work_id VARCHAR(255),
                is_oa BOOLEAN,
                landing_page_url TEXT,
                source_id VARCHAR(255),
                provenance VARCHAR(100),
                is_primary BOOLEAN
            );
        """)

        # 11. WORK_TOPICS TABLE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS work_topics (
                work_id VARCHAR(255),
                topic_id VARCHAR(255),
                score DECIMAL(12,7),
                is_primary_topic BOOLEAN DEFAULT FALSE
            );
        """)

        # 12. WORK_CONCEPTS TABLE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS work_concepts (
                work_id VARCHAR(255),
                concept_id VARCHAR(255),
                score DECIMAL(12,7)
            );
        """)

        # 13. WORK_SOURCES TABLE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS work_sources (
                work_id VARCHAR(255),
                source_id VARCHAR(255)
            );
        """)

        # 14. CITATIONS_BY_YEAR TABLE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS citations_by_year (
                work_id VARCHAR(255),
                year INTEGER,
                citation_count INTEGER
            );
        """)

        # 15. REFERENCED_WORKS TABLE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS referenced_works (
                work_id VARCHAR(255),
                referenced_work_id VARCHAR(255)
            );
        """)

        # 16. RELATED_WORKS TABLE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS related_works (
                work_id VARCHAR(255),
                related_work_id VARCHAR(255)
            );
        """)

        # 17. WORK_FUNDERS TABLE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS work_funders (
                work_id VARCHAR(255),
                funder_id VARCHAR(255),
                award_id VARCHAR(1000)
            );
        """)

        # 18. WORK_KEYWORDS TABLE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS work_keywords (
                work_id VARCHAR(255),
                keyword VARCHAR(255)
            );
        """)

        # 19. AUTHOR_TOPICS TABLE - COMMENTED OUT (derived data, not from snapshot)
        # Will be created when building author profiles from authorship data
        # cursor.execute("""
        #     CREATE TABLE IF NOT EXISTS author_topics (
        #         author_id VARCHAR(255),
        #         topic_id VARCHAR(255),
        #         score DECIMAL(12,7),
        #         work_count INTEGER,
        #         recent_work_count INTEGER
        #     );
        # """)

        # 20. AUTHOR_CONCEPTS TABLE - COMMENTED OUT (derived data, not from snapshot)
        # Will be created when building author profiles from authorship data
        # cursor.execute("""
        #     CREATE TABLE IF NOT EXISTS author_concepts (
        #         author_id VARCHAR(255),
        #         concept_id VARCHAR(255),
        #         score DECIMAL(20,7),
        #         work_count INTEGER
        #     );
        # """)

        # 21. AUTHOR_INSTITUTIONS TABLE - COMMENTED OUT (derived data, not from snapshot)
        # This tracks historical/current affiliations, not per-work affiliations
        # Will be created when needed, derived from authorship_institutions
        # cursor.execute("""
        #     CREATE TABLE IF NOT EXISTS author_institutions (
        #         author_id VARCHAR(255),
        #         institution_id VARCHAR(255),
        #         start_date DATE,
        #         end_date DATE,
        #         affiliation_string TEXT
        #     );
        # """)

        # 22. SOURCE_PUBLISHERS TABLE - COMMENTED OUT (not populated from snapshot)
        # Will be created if needed for publisher analysis
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS source_publishers (
                source_id VARCHAR(255),
                publisher_id VARCHAR(255)
            );
        """)

        # PHASE 3: HIERARCHY TABLES

        # 23. INSTITUTION_HIERARCHY TABLE - COMMENTED OUT (not populated from snapshot)
        # Will be created when needed for hierarchical institution analysis
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS institution_hierarchy (
                parent_institution_id VARCHAR(255),
                child_institution_id VARCHAR(255),
                hierarchy_level INTEGER,
                relationship_type VARCHAR(100)
            );
        """)

        # 24. TOPIC_HIERARCHY TABLE - COMMENTED OUT (not populated from snapshot)
        # Will be created when needed for hierarchical topic analysis
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS topic_hierarchy (
                parent_topic_id VARCHAR(255),
                child_topic_id VARCHAR(255),
                hierarchy_level INTEGER
            );
        """)

        # PHASE 4: SUPPORTING/METADATA TABLES

        # 25. ALTERNATE_IDS TABLE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alternate_ids (
                alt_id SERIAL,
                work_id VARCHAR(255),
                id_type VARCHAR(100),
                id_value VARCHAR(255)
            );
        """)

        # 26. APC TABLE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS apc (
                work_id VARCHAR(255),
                value DECIMAL(15,2),
                currency VARCHAR(100),
                value_usd DECIMAL(15,2),
                provenance VARCHAR(100)
            );
        """)

        # 28. SEARCH_METADATA TABLE - COMMENTED OUT (user-generated data, not from snapshot)
        # Will be created when implementing search functionality
        # cursor.execute("""
        #     CREATE TABLE IF NOT EXISTS search_metadata (
        #         search_id VARCHAR(255),
        #         search_term TEXT,
        #         publication_year INTEGER,
        #         search_date TIMESTAMP,
        #         papers_found INTEGER,
        #         papers_added INTEGER
        #     );
        # """)

        # 29. SEARCH_INDEX TABLE - COMMENTED OUT (user-generated data, not from snapshot)
        # Will be created when implementing search functionality
        # cursor.execute("""
        #     CREATE TABLE IF NOT EXISTS search_index (
        #         search_term_id SERIAL,
        #         search_term VARCHAR(500),
        #         entity_type VARCHAR(100),
        #         entity_id VARCHAR(255),
        #         entity_name TEXT,
        #         search_vector TSVECTOR
        #     );
        # """)

        # 30. AUTHOR_NAME_VARIANTS TABLE - COMMENTED OUT (derived data, not from snapshot)
        # Will be created when building author disambiguation/matching systems
        # cursor.execute("""
        #     CREATE TABLE IF NOT EXISTS author_name_variants (
        #         variant_id SERIAL,
        #         author_id VARCHAR(255),
        #         name_variant TEXT,
        #         variant_type VARCHAR(100),
        #         confidence_score DECIMAL(12,7)
        #     );
        # """)

        # 31. AUTHORS_WORKS_BY_YEAR TABLE - COMMENTED OUT (derived data, not from snapshot)
        # Will be created when building author profiles from authorship data
        # print(f"[{datetime.now()}] Creating authors_works_by_year table...")
        # cursor.execute("""
        #     CREATE TABLE IF NOT EXISTS authors_works_by_year (
        #         author_id VARCHAR(255),
        #         year INTEGER,
        #         works_count INTEGER,
        #         oa_works_count INTEGER,
        #         cited_by_count INTEGER
        #     );
        # """)

        # 32. DATA_MODIFICATION_LOG TABLE - COMMENTED OUT (audit log, not from snapshot)
        # Will be created when implementing audit logging
        # cursor.execute("""
        #     CREATE TABLE IF NOT EXISTS data_modification_log (
        #         log_id SERIAL,
        #         username TEXT NOT NULL,
        #         table_name TEXT,
        #         action TEXT,
        #         ip_address INET,
        #         modified_at TIMESTAMP DEFAULT NOW(),
        #         row_count INTEGER
        #     );
        # """)

        conn.commit()
        print(f"[{datetime.now()}] ✅ All tables created without constraints!")
        print(f"[{datetime.now()}] ℹ️  Note: NO primary keys, NO foreign keys, NO indexes (except extension)")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error creating tables: {e}")
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

        # Verify NO primary keys exist
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.table_constraints
            WHERE constraint_schema = 'public' AND constraint_type = 'PRIMARY KEY';
        """)
        pk_count = cursor.fetchone()[0]
        print(f"  ✅ Primary keys: {pk_count} (should be 0)")

        # Verify NO foreign keys exist
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.table_constraints
            WHERE constraint_schema = 'public' AND constraint_type = 'FOREIGN KEY';
        """)
        fk_count = cursor.fetchone()[0]
        print(f"  ✅ Foreign keys: {fk_count} (should be 0)")

        # Count indexes (will have a few from SERIAL columns and extensions)
        cursor.execute("""
            SELECT COUNT(*) FROM pg_indexes
            WHERE schemaname = 'public';
        """)
        index_count = cursor.fetchone()[0]
        print(f"  ✅ Total indexes: {index_count} (minimal - only auto-created)")

        print(f"\n[{datetime.now()}] ✅ Setup verification complete!")
        print(f"  📊 Database is ready for constraint-free bulk loading!")

    except Exception as e:
        print(f"❌ Error during verification: {e}")
    finally:
        cursor.close()
        conn.close()

def print_summary():
    """Print summary information"""
    print("\n" + "="*70)
    print("✅ OADB2 DATABASE SETUP COMPLETE!")
    print("="*70)
    print(f"\nDatabase: {DB_NAME}")
    print(f"Host: {DB_HOST}")
    print(f"Port: {DB_PORT}")
    print(f"\n🚀 READY FOR CONSTRAINT-FREE BULK LOADING")
    print("\n📊 Database Characteristics:")
    print("  ✅ 35 tables created (32 original + 3 new)")
    print("  ✅ NO primary keys")
    print("  ✅ NO foreign keys")
    print("  ✅ NO unique constraints")
    print("  ✅ Minimal indexes (only auto-created)")
    print("\n📝 Next Steps:")
    print("  1. Run oadb2_master_orchestrator.py to load all data")
    print("  2. Run oadb2_add_constraints.py to add constraints after loading")
    print("  3. Run oadb2_performance_report.py for performance analysis")
    print("  4. Run oadb2_validation.py to verify data integrity")
    print("="*70 + "\n")

def main():
    """Main execution function"""
    try:
        print("="*70)
        print("OADB2 Database Setup Script - Constraint-Free Loading Test")
        print("="*70)

        # Step 1: Create database
        create_database()

        # Step 2: Create all tables WITHOUT constraints
        create_tables_no_constraints()

        # Step 3: Verify setup
        verify_setup()

        # Step 4: Print summary
        print_summary()

    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        print("Please check the error messages above and try again.")
        return False

    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("✅ OADB2 database setup completed successfully!")
    else:
        print("❌ OADB2 database setup failed. Please review errors above.")
