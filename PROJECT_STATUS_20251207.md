# OpenAlex Database Clone - Project Status Summary

**Date:** December 7, 2025
**Project Lead:** Lucas Black (s.lucasblack@gmail.com)
**Database:** oadbv5 @ 192.168.1.162:55432
**Snapshot:** November 25, 2025

---

## Executive Summary

This is a comprehensive data engineering and research project to build and analyze a local copy of the OpenAlex academic database (~2TB), with focus on:
- **Author career trajectory analysis** (102M authors)
- **Gender analysis in academic publishing**
- **Geographic patterns in research output**
- **Network science** (co-authorship and institution networks)
- **Key Opinion Leader (KOL) identification**

### Current Phase: **04 - Author Profile Building** (In Progress)

The project has successfully completed database setup and data parsing, and is now actively building comprehensive author profiles with gender inference and publication pattern analysis.

---

## Project Progress Overview

### ✅ COMPLETED PHASES

#### Phase 01: OpenAlex Snapshot Download
- **Status:** Complete
- **Location:** `/Volumes/Series/25NOV2025/data/`
- **Snapshot Date:** November 25, 2025
- **Data Scale:**
  - 277M works
  - 102M authors
  - 1.1B authorship records
  - 2.3B work-concept relationships
- **Storage:** ~2TB gzipped JSON files

#### Phase 02: PostgreSQL Database Setup
- **Status:** Complete (Rebuilt after NAS hardware replacement)
- **Database:** oadbv5
- **Host:** 192.168.1.162:55432 (UGREEN NAS)
- **PostgreSQL Version:** 16 (Docker container)
- **Tables Created:** 32 tables
- **Infrastructure:**
  - Docker-based deployment
  - Data persistence: `/volume1/postgresql_data`
  - SMB access: `/Volumes/postgresql_data`
  - Performance optimizations implemented

#### Phase 03: Snapshot Parsing & Constraint Building
- **Status:** Complete
- **Achievement:** Successfully parsed entire 2TB dataset into PostgreSQL
- **Key Accomplishments:**
  - All 8 entity parsers created and tested
  - High-performance COPY-based architecture (10-100x faster than INSERT)
  - Single-pass extraction to multiple tables
  - ~2B records successfully loaded

**Parsed Entities:**
1. ✅ Topics (1,000 test → 4,500 production)
2. ✅ Concepts (~65,000)
3. ✅ Publishers (~10,000)
4. ✅ Funders (~32,000)
5. ✅ Sources (~260,000)
6. ✅ Institutions (~117,000)
7. ✅ Authors (~84.4M authors confirmed in author_data.duckdb)
8. ✅ Works (~277M)

**Constraint Building Progress (Nov 29 - Dec 6):**
- ✅ Duplicate investigation and removal
- ✅ Table vacuuming (space reclamation)
- ✅ Primary keys added (all tables except work_keywords)
- 🔄 Indexes (authorship scope completed, full indexing in progress)
- ⏸️ Foreign keys (deferred for performance)
- ⏸️ Orphan record analysis (deferred)

**Schema Corrections (Dec 6):**
- Fixed `authorship.institution_id` reference (moved to `authorship_institutions` table)
- Corrected column names in index scripts
- Added `--scope` flag for selective constraint building

---

### 🔄 IN PROGRESS PHASES

#### Phase 04: Author Profile Building
- **Status:** ACTIVELY IN PROGRESS
- **Database:** `/Users/lucas/Documents/openalex_database/python/OA_clone/04_author_profile_building/datasets/author_data.duckdb` (9.8 GB)
- **Total Authors Processed:** 84,380,180

**Completed Scripts:**
1. ✅ `01_extract_forenames.py` - Extract author forenames from display names
   - Last run: Dec 4, 2025
   - Successfully extracted forenames for gender inference

2. ✅ `02_parse_names.py` - Parse author names into components
   - Last run: Dec 5, 2025
   - Split names into forename/surname

3. ✅ `03_convert_country_codes.py` - Map country codes to country names
   - Last run: Dec 7, 2025
   - Enhanced geographic data for gender inference

**Gender Inference Pipeline (Multiple Methods):**
4. 🔄 `05_infer_genderComputer.py` - Gender inference using genderComputer library
   - **Status:** RUNNING (as of Dec 7, 15:45)
   - Progress: Processing 84.4M authors
   - Rate: ~1,000 records/sec
   - Results: ~40% male, ~36% female, ~24% unknown
   - **Estimated time:** ~24-30 hours total
   - Started: Dec 7, 15:45

5. ✅ `06_infer_genderGuesser.py` - Gender inference using genderGuesser
   - Last run: Dec 4, 2025

6. ✅ `07_infer_genderLocal.py` - Gender inference using local name database
   - Last run: Dec 4, 2025
   - Local database: `local_names.db` (6.0 GB)

7. 🔄 `08_infer_gender_chatgpt.py` - Gender inference using OpenAI API
   - Multiple test runs: Dec 4, 2025
   - API testing and batch size optimization completed

**Publication Pattern Analysis:**
8. ✅ `09_analyze_publications_by_year.py` - Extract publication year patterns
   - **Last successful run:** Dec 7, 12:24
   - Sample size: 100,000 authors (ORCID holders, works_count > 10)
   - Output: DuckDB database with year-by-year publication counts
   - Output file: `author_publications_by_year_20251207_122429.duckdb` (4.3 MB)
   - Purpose: Career trajectory modeling

9. ✅ `10_eda_publications_by_year.R` - Exploratory data analysis in R
   - Last run: Dec 7, 13:19
   - Output: `eda_plots_20251207_131940.pdf` (428 KB)
   - Visualization of publication patterns

10. ✅ `analyze_publication_dates.py` - Publication date validation
    - Last run: Dec 7, 13:46
    - Output: `publication_date_analysis.png` (428 KB)
    - Validates data quality for year-based calculations

**Supporting Scripts:**
- ✅ `country_code_mapping.py` - Country code utilities
- ✅ `create_test_database.py` - Test database creation
- ✅ `validate_results.py` - Results validation
- ✅ `test_batch_sizes.py` - Batch size optimization
- ✅ `test_gpt5nano.py` - GPT API testing
- ✅ `rebuild_authors_works_by_year.py` - Data reconstruction utility

**Gender Inference Library:**
- ✅ `genderComputer/` - Local copy of genderComputer library
  - Built and installed locally
  - Name lists and dictionaries included

**Current Challenges:**
- Some authors have no publication years in `authors_works_by_year` table (warnings in logs)
- Empty forename handling in genderComputer (list index errors)
- Large-scale processing (84M records) requires long run times

**Target Author Profile Features:**
```python
- author_id                    # OpenAlex unique ID
- orcid                        # ORCID identifier
- display_name                 # Full name
- forename                     # ✅ Extracted
- surname                      # ✅ Extracted
- works_count                  # Total publications
- cited_by_count               # Total citations
- current_affiliation_id       # ✅ Available
- current_affiliation_name     # ✅ Available
- current_affiliation_country  # ✅ Mapped to names
- current_affiliation_type     # Institution type
- gender                       # 🔄 Being inferred (4 methods)
- gendercomputer_gender        # 🔄 RUNNING
- genderguesser_gender         # ✅ Complete
- local_gender                 # ✅ Complete
- gpt_gender                   # 🔄 Testing
- most_cited_work              # To be calculated
- max_citations                # To be calculated
- first_publication_year       # 🔄 Being analyzed
- last_publication_year        # 🔄 Being analyzed
- career_length_years          # To be calculated
- career_stage                 # To be modeled
- is_current                   # To be calculated
- corresponding_authorships    # To be counted
- freq_corresponding           # To be calculated
- freq_first_author            # To be calculated
- freq_last_author             # To be calculated
- primary_topic                # To be identified
- primary_concept              # To be identified
```

---

#### Phase 05: Database Query System
- **Status:** COMPLETE & TESTED
- **Location:** `05_db_query/`
- **Purpose:** Query works by title/abstract, topics, keywords

**Completed Components:**
1. ✅ `query_helper.py` - Database connection utilities
2. ✅ `search_queries.py` - Four search methods (title/abstract, topics, keywords, combined)
3. ✅ `count_aggregator.py` - Count works, authors, institutions
4. ✅ `run_search_analysis.py` - CLI orchestrator with CSV export
5. ✅ `test_queries.py` - Comprehensive test suite

**Test Results (Dec 7, 2025):**
- ✅ Database connection: Successful
- ✅ Title/Abstract search: 323,426 works for "flow cytometry"
- ✅ Topic search: 0 works (topics not matching exact phrase)
- ✅ Keyword search: 265,524 works for "flow cytometry"
- ✅ Combined (UNION): 432,651 works total
- Query execution time: 5-30 minutes for large result sets

**Features:**
- Multiple search methods (title, abstract, topics, keywords)
- Author and institution counting via authorship tables
- CSV export with timestamps
- Comprehensive logging
- Ready for production use

---

### ⏸️ PLANNED PHASES (Not Started)

#### Phase 06-09: Network Analysis
- **Status:** Not started
- **Folders:** Empty placeholders created
- **Planned Work:**
  - Co-authorship network construction
  - Author-institution network mapping
  - Co-institution networks
  - Network metrics (degree, PageRank, eigenvector, clustering, Katz, closeness, betweenness)

#### Phase 10-11: Hypothesis Testing
- **Status:** Not started
- **Focus Areas:**
  - Gender impact on career trajectories
  - Geographic patterns in academic success
  - Statistical analysis of disparities

#### Phase 12: Key Opinion Leader Analysis
- **Status:** Not started
- **Planned Work:**
  - Current and historical KOL identification
  - Career trajectory modeling
  - Predictive modeling for emerging KOLs

---

## Recent Work Timeline (Nov 25 - Dec 7, 2025)

### Week 1: Database Rebuild (Nov 25 - Dec 2)
- **Nov 25-27:** New OpenAlex snapshot downloaded (Nov 25, 2025)
- **Nov 29:** Started duplicate investigation on oadbv5
- **Nov 29 - Dec 2:** Duplicate removal across all tables
- **Dec 2:** Table vacuuming to reclaim disk space

### Week 2: Constraints & Author Profiling (Dec 2 - Dec 7)
- **Dec 2-6:** Primary key creation (all tables except work_keywords)
- **Dec 4:** Author name extraction and parsing completed
- **Dec 4:** Multiple gender inference test runs
- **Dec 5:** Table vacuuming operations (multiple tables)
- **Dec 5:** Authorship index creation started
- **Dec 6:** Schema errors fixed in constraint scripts
- **Dec 7 (morning):** Publication pattern analysis (100k author sample)
- **Dec 7 (midday):** R-based exploratory data analysis
- **Dec 7 (afternoon):** genderComputer inference started on full 84M dataset

### Key Accomplishments This Week
1. ✅ Fixed critical schema bugs in constraint building scripts
2. ✅ Completed name parsing for all 84.4M authors
3. ✅ Successfully analyzed publication patterns for sample data
4. ✅ Started large-scale gender inference (currently running)
5. ✅ Validated database query system with real queries

---

## Technical Infrastructure

### Hardware
- **Database Server:** UGREEN NAS (new - replaced after RAID failure)
- **Storage:** NVMe drives for database, HDD volumes for backups
- **Network:** Local network (192.168.1.x)
- **Development:** MacBook (local machine)

### Software Stack
- **Database:** PostgreSQL 16 (Docker)
- **Languages:** Python 3.13, R
- **Key Libraries:**
  - `psycopg2` (PostgreSQL adapter)
  - `duckdb` (local analytics database)
  - `genderComputer`, `genderGuesser` (gender inference)
  - OpenAI API (GPT-based gender inference)
  - `ggplot2`, `tidyverse` (R visualization)

### Data Flow
1. **Source:** OpenAlex snapshot (gzipped JSON) → `/Volumes/Series/25NOV2025/data/`
2. **Parsing:** Python parsers → PostgreSQL `oadbv5` @ 192.168.1.162:55432
3. **Analysis:** PostgreSQL → DuckDB → Analysis scripts → Results/Visualizations

### File Organization
```
OA_clone/
├── 01_oa_snapshot/          ✅ Download scripts & logs
├── 02_postgres_setup/       ✅ Database schema & setup
├── 03_snapshot_parsing/     ✅ Parsers & constraint building
├── 04_author_profile_building/  🔄 ACTIVE - Gender & career analysis
├── 05_db_query/             ✅ Query system (tested)
├── 06-09_network_*/         ⏸️ Empty placeholders
├── 10-12_*/                 ⏸️ Empty placeholders
├── 99_visualisations/       ✅ Themes & color palettes
├── genderComputer/          ✅ Local gender inference library
├── config.py                ✅ Global configuration
└── Various README/docs      ✅ Documentation
```

---

## Database Status (oadbv5)

### Connection Details
- **Host:** 192.168.1.162
- **Port:** 55432
- **Database:** oadbv5
- **User:** admin
- **Status:** Active and accessible

### Data Scale (Estimated from Logs)
| Table | Estimated Rows | Status |
|-------|---------------|--------|
| authors | 84,380,180 | ✅ Loaded |
| works | ~277M | ✅ Loaded |
| authorship | ~1.1B | ✅ Loaded |
| authorship_institutions | ~500M | ✅ Loaded |
| institutions | ~117,000 | ✅ Loaded |
| topics | ~4,500 | ✅ Loaded |
| work_topics | ~500M | ✅ Loaded |
| work_concepts | ~2.3B | ✅ Loaded |
| work_keywords | Large | ✅ Loaded |
| citations_by_year | Large | ✅ Loaded |
| referenced_works | Large | ✅ Loaded |

### Constraints Status
- ✅ Primary Keys: All tables except `work_keywords`
- 🔄 Indexes: Authorship scope complete, full indexing in progress
- ⏸️ Foreign Keys: Deferred for performance
- ⏸️ Unique Constraints: Deferred

### Known Issues
- `work_keywords` primary key deferred (not needed for current work)
- Some orphan records exist (analysis deferred)
- Merged IDs not processed (affects <0.05% of records)

---

## Key Insights from Logs

### Data Quality Issues Identified

1. **Missing Publication Years:**
   - Many authors in `authors_works_by_year` have NULL years
   - Affects career trajectory calculations
   - Script handles gracefully with warnings

2. **Empty Forenames:**
   - ~24% of authors have empty/missing forenames
   - Causes "list index out of range" errors in genderComputer
   - Script continues processing with "unknown" gender assignment

3. **Query Performance:**
   - Large result sets (>300k works) take 5-30 minutes
   - Indexes improve performance significantly
   - Combined UNION queries more efficient than separate queries

### Processing Rates
- **Name Parsing:** Fast (completed 84M in < 1 day)
- **Gender Inference (genderComputer):** ~1,000 records/sec = ~24-30 hours for full dataset
- **Publication Analysis:** ~100k authors analyzed in <10 seconds
- **Database Queries:** 5-30 minutes for complex searches

---

## Risk Assessment

### Current Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Long-running gender inference could fail | Medium | Proper logging, batch commits, error handling |
| Hardware failure (new NAS) | Low | Daily backups to HDD volume |
| Disk space exhaustion | Low | 10GB+ available, monitoring in place |
| Data quality issues in author records | Medium | Multiple gender inference methods, validation scripts |

### Mitigations in Place
- ✅ Comprehensive error logging
- ✅ Graceful error handling (continues on failure)
- ✅ Progress tracking every 10k records
- ✅ Batch commits to prevent data loss
- ✅ Test databases for validation
- ✅ Multiple inference methods for cross-validation

---

## Next Steps (Priority Order)

### Immediate (Next 1-3 Days)
1. 🔄 **Monitor genderComputer inference** - Currently running on 84M authors
   - Check progress in logs: `04_author_profile_building/logs/`
   - Estimated completion: Dec 8-9, 2025

2. **Resume indexing if needed** - Check status of full database indexing
   - Location: `03_snapshot_parsing/constraint_building/`
   - Command: Check logs or re-run with `--scope all`

3. **Validate gender inference results** - Once genderComputer completes
   - Compare results from 4 methods
   - Identify consensus and conflicts
   - Calculate confidence scores

### Short Term (Next 1-2 Weeks)
4. **Complete remaining author profile features:**
   - Most cited work calculation
   - Career stage modeling
   - Authorship position frequencies
   - Primary topic/concept identification

5. **Build career trajectory clustering:**
   - DTW (Dynamic Time Warping) analysis
   - ML-based trajectory classification
   - Early/mid/late career identification

6. **Start Phase 06: Network Building**
   - Co-authorship network extraction
   - Author-institution mapping
   - Network export formats

### Medium Term (Next 1-2 Months)
7. **Network Analysis (Phase 07)**
   - Calculate centrality measures
   - Community detection
   - Network visualization

8. **Hypothesis Testing (Phase 10-11)**
   - Gender disparity analysis
   - Geographic pattern analysis
   - Statistical modeling

9. **Documentation & Publication Prep**
   - Methods documentation
   - Data dictionary
   - Preliminary findings

---

## Resource Utilization

### Storage
- **Database (oadbv5):** ~2TB (PostgreSQL data directory)
- **Author Profile Data:** 9.8 GB (DuckDB)
- **Local Name Database:** 6.0 GB
- **OpenAlex Snapshot:** ~2TB (original gzipped files)
- **Logs:** ~500 MB
- **Total Project:** ~6-7TB

### Compute
- **Current Active Process:** genderComputer (1 process, ~1k records/sec)
- **Database Load:** Light (mainly serving queries from active scripts)
- **Network:** Local network only, no external dependencies (except OpenAI API)

### Time Investment
- **Phase 01-03:** ~2 weeks (including rebuild after hardware failure)
- **Phase 04 (current):** ~2 weeks and ongoing
- **Total elapsed:** ~1.5 months since Oct 21, 2025

---

## Documentation Status

### ✅ Comprehensive Documentation Exists For:
- Database setup and Docker configuration (`02_postgres_setup/docs/`)
- Parsing architecture and final status (`03_snapshot_parsing/FINAL_STATUS.md`)
- Constraint building updates (`03_snapshot_parsing/constraint_building/UPDATES_SUMMARY.md`)
- Query system usage (`05_db_query/README.md`)
- Coding standards (`CLAUDE.md`, `STYLE_GUIDE.md`)
- Setup guides (NAS, laptop, Windows laptop, Plex)

### 📝 Documentation Needed:
- Complete Phase 04 methodology (gender inference, career trajectories)
- Network building procedures (Phase 06)
- Analysis pipeline (Phases 07-12)
- Data dictionary for all tables
- API documentation for query system

---

## Lessons Learned

### What Worked Well
1. **COPY-based parsing:** 10-100x faster than INSERT statements
2. **Single-pass extraction:** Reading each file once, writing to multiple tables
3. **Modular architecture:** Independent parsers, easy to test and debug
4. **Multiple gender inference methods:** Cross-validation and higher coverage
5. **DuckDB for analysis:** Fast, embedded database perfect for intermediate results
6. **Comprehensive logging:** Essential for debugging and monitoring long-running processes

### Challenges Overcome
1. **NAS hardware failure:** Successfully rebuilt on new hardware
2. **Database IP address changes:** Updated config, all scripts adapted
3. **Schema errors in constraints:** Fixed column name mismatches
4. **Duplicate records:** Comprehensive identification and removal
5. **Missing data handling:** Graceful error handling prevents crashes

### Ongoing Challenges
1. **Processing time:** 84M records takes days even at 1k/sec
2. **Data quality:** Missing years, empty names, orphan records
3. **Disk space management:** Large intermediate files, regular cleanup needed
4. **API costs:** OpenAI API usage for gender inference (limited by budget)

---

## Project Health: 🟢 GREEN

**Overall Assessment:** The project is in excellent health and making steady progress.

### Strengths
- ✅ All foundational infrastructure complete
- ✅ Database successfully populated with 2B+ records
- ✅ Robust error handling and logging
- ✅ Multiple validation methods in place
- ✅ Clear roadmap and phase structure

### Areas for Attention
- ⚠️ Long processing times require patience and monitoring
- ⚠️ Data quality issues need ongoing validation
- ⚠️ Future phases (06-12) not yet started

### Confidence Level
- **High confidence** in completing Phase 04 (author profiling)
- **Medium confidence** in timeline for Phases 06-09 (depends on compute resources)
- **High confidence** in technical approach and methodology

---

## Contact & References

**Project Lead:** Lucas Black
**Email:** s.lucasblack@gmail.com
**Repository:** Local Git repository (not yet public)
**Documentation:** See `CLAUDE.md` for project guidelines and coding standards

**Key References:**
- OpenAlex Documentation: https://docs.openalex.org/
- genderComputer Library: Local installation in `genderComputer/`
- PostgreSQL 16 Documentation: https://www.postgresql.org/docs/16/

---

**Document Version:** 1.0
**Last Updated:** December 7, 2025
**Next Update:** Recommend weekly updates during active development phases
