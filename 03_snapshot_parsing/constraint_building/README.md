# Database Constraint Building Pipeline

Complete guide for adding primary keys, indexes, and foreign keys to the OpenAlex database after data loading is complete.

---

## Current Status

**Last Updated:** November 9, 2025

**Database:** OADB_test (1013 GB test copy of OADB)

**Progress:**
- ✅ Database validation - Database names corrected (OADB_test/OADB)
- ✅ Merged IDs validation - Tested and **SKIPPED** (0.05% match rate, minimal impact)
- ✅ Primary key timing test - Completed on small tables (~159k rows/sec throughput)
- ⚠️ **ISSUE DISCOVERED:** Duplicate records found (2.8M in works, 750K in authors)
- 🔄 **CURRENTLY INVESTIGATING:** Duplicate analysis to determine if data is identical or different
- ⏸️ Duplicate removal - Pending investigation results
- ⏸️ Primary keys - Blocked by duplicates
- ⏸️ Indexes - Not started
- ⏸️ Foreign keys - Not started
- ⏸️ Validation - Not started

---

## Overview

This pipeline builds database constraints on a fully-loaded OpenAlex database. It handles:
- **Duplicate record detection and removal** - **REQUIRED before PKs**
- Merged entity IDs (canonical ID consolidation) - **OPTIONAL**
- Orphaned record detection and manifest generation
- Primary key creation
- Index creation (critical for FK validation performance)
- Foreign key creation (using NOT VALID for speed)
- Constraint validation
- Comprehensive reporting

**Key Features:**
- Test mode support (clone database for testing)
- State tracking and resume capability
- Orphan record flagging for API retrieval
- Deferred FK validation for performance
- Comprehensive logging and reporting
- Validation scripts to test impact before running phases

---

## Prerequisites

### 1. Data Loading Must Be Complete

Before running this pipeline:
- ✅ All entity tables must be fully loaded (authors, works, institutions, etc.)
- ✅ All relationship tables must be populated (authorship, work_topics, etc.)
- ✅ Data loading orchestrator shows all phases "complete"

**Check data loading status:**
```bash
cd ../
python3 orchestrator.py --status
```

### 2. Database Cloning for Testing (Recommended)

Clone the production database for safe testing:
```bash
# Use the Python script to handle connection termination
python3 create_test_database.py
```

Or manually with SQL (requires terminating active connections first):
```sql
-- Connect to PostgreSQL as admin
CREATE DATABASE "OADB_test" WITH TEMPLATE "OADB" OWNER admin;
```

**Note:** Database names are case-sensitive. Use `OADB_test` and `OADB` (not oadb2_test/oadb2).

### 3. Merged IDs Available (OPTIONAL)

**Note:** Based on validation testing, merged IDs have minimal impact (~0.05% match rate) and can be safely skipped to save 1-4 hours.

If you choose to run this phase, verify merged_ids directory exists:
```bash
ls /Volumes/OA_snapshot/24OCT2025/data/merged_ids/
```

Should contain subdirectories: `authors/`, `works/`, `institutions/`, `sources/`, `publishers/`

To test impact before running:
```bash
python3 validate_merged_ids_impact.py
# or
python3 quick_merged_check.py
```

---

## File Structure

```
constraint_building/
├── README.md                           # This file
├── orchestrator_constraints.py         # Main coordinator
│
├── Core Pipeline Scripts:
├── apply_merged_ids.py                 # Phase 1: Update to canonical IDs (OPTIONAL)
├── analyze_orphans.py                  # Phase 2: Detect orphaned records
├── add_primary_keys.py                 # Phase 3: Create primary keys
├── add_indexes.py                      # Phase 4: Create indexes
├── add_foreign_keys.py                 # Phase 5: Create FKs (NOT VALID)
├── validate_constraints.py             # Phase 6: Validate all FKs
├── generate_report.py                  # Phase 7: Generate reports
├── constraint_state.json               # State file (auto-generated)
│
├── Duplicate Handling Scripts (REQUIRED before PKs):
├── investigate_duplicates.py           # Investigate nature of duplicates
├── analyze_duplicates.py               # Get detailed duplicate statistics
├── remove_duplicates.py                # Remove duplicate records
│
├── Validation & Testing Scripts:
├── validate_merged_ids_impact.py       # Test merged IDs impact before running
├── quick_merged_check.py               # Fast merged IDs validation
├── test_pk_single_table.py             # Test PK timing on small tables
├── create_test_database.py             # Create OADB_test database
├── check_databases.py                  # List all databases
├── list_tables.py                      # List tables in OADB_test
│
├── logs/
│   ├── constraints.log                 # Main log (orchestrator only)
│   ├── investigate_duplicates.log      # Duplicate investigation log
│   ├── analyze_duplicates.log          # Duplicate analysis log
│   ├── remove_duplicates.log           # Duplicate removal log
│   ├── add_primary_keys.log            # Primary key creation log
│   ├── add_indexes.log                 # Index creation log
│   ├── add_foreign_keys.log            # Foreign key creation log
│   ├── validate_constraints.log        # Constraint validation log
│   └── validation_failures.log         # FK validation failures
│
├── orphan_manifests/                   # Orphan ID lists (for API retrieval)
│   ├── authorship_author_id_orphans.csv
│   ├── referenced_works_referenced_work_id_orphans.csv
│   └── orphan_summary_report.csv
│
└── reports/                            # Final constraint reports
    ├── primary_keys_YYYYMMDD_HHMMSS.csv
    ├── foreign_keys_YYYYMMDD_HHMMSS.csv
    ├── indexes_YYYYMMDD_HHMMSS.csv
    ├── table_statistics_YYYYMMDD_HHMMSS.csv
    ├── duplicate_analysis.csv          # Duplicate statistics
    └── CONSTRAINT_SUMMARY_YYYYMMDD_HHMMSS.md
```

---

## Quick Start

### Step 0: Check for and Remove Duplicates (REQUIRED FIRST)

```bash
cd constraint_building

# Investigate duplicates
python3 investigate_duplicates.py --test --quick

# Get detailed analysis
python3 analyze_duplicates.py --test

# Remove duplicates (dry-run first!)
python3 remove_duplicates.py --test --dry-run
python3 remove_duplicates.py --test
```

**⚠️ CRITICAL:** Primary keys cannot be created if duplicates exist. This step must be completed first.

### Step 1: Test Run on Cloned Database

After removing duplicates:

```bash
cd constraint_building

# Reset state (if needed)
python3 orchestrator_constraints.py --reset

# Run full pipeline on test database
export ADMIN_PASSWORD='your_password'
python3 orchestrator_constraints.py --start --test
```

**Note:** The orchestrator does NOT handle duplicate removal. You must remove duplicates manually before starting the pipeline.

### Step 2: Review Test Results

```bash
# Check final status
python3 orchestrator_constraints.py --status --test

# Review orphan manifests
ls -lh orphan_manifests/

# Review final summary report
cat reports/CONSTRAINT_SUMMARY_*.md
```

### Step 3: Production Run

If test run successful:
```bash
# Reset state
python3 orchestrator_constraints.py --reset

# Run on production database
export ADMIN_PASSWORD='your_password'
python3 orchestrator_constraints.py --start
```

---

## Handling Duplicate Records (REQUIRED BEFORE PRIMARY KEYS)

### Issue Discovery

During primary key creation, the script checks for duplicate values and will fail if duplicates exist. In our case:
- **works table:** 2,838,995 duplicate groups found
- **authors table:** 750,000 duplicate groups found

Primary keys CANNOT be created until duplicates are resolved.

### Three-Step Workflow

#### Step 1: Investigate Duplicates

Determine if duplicate rows are identical (safe to delete) or have different data (need manual review):

```bash
# Quick check all tables
python3 investigate_duplicates.py --test --quick

# Detailed investigation of specific table
python3 investigate_duplicates.py --test --table works --pk work_id
python3 investigate_duplicates.py --test --table authors --pk author_id
```

**Output:** `logs/investigate_duplicates.log`

This will tell you:
- How many duplicate groups exist
- Whether duplicates are identical or different
- Examples of duplicate records

#### Step 2: Analyze Duplicates

Get comprehensive statistics on all tables:

```bash
python3 analyze_duplicates.py --test
```

**Output:**
- Console output with full statistics
- `logs/analyze_duplicates.log`
- `logs/duplicate_analysis.csv` (detailed report)

This reports:
- Total rows per table
- Number of duplicate groups
- Number of duplicate rows to remove
- Percentage affected

#### Step 3: Remove Duplicates

**IMPORTANT:** Always test with dry-run first!

```bash
# Dry run (shows what would be deleted)
python3 remove_duplicates.py --test --dry-run

# Review the output, then actually remove duplicates
python3 remove_duplicates.py --test
```

**Output:**
- `logs/remove_duplicates_dryrun.log` (for dry-run)
- `logs/remove_duplicates.log` (for actual removal)

**Strategy:** Keeps the first inserted row (lowest ctid) for each duplicate group.

### Understanding Duplicates

**Why do duplicates exist?**
1. Data was loaded multiple times (parsing script ran twice)
2. Source data contained duplicates
3. Parsing logic didn't enforce uniqueness

**What if duplicates have different data?**
- The removal script keeps the first inserted row
- If rows have different data, this means some data will be lost
- Review investigation output carefully
- Consider manual merge if data differences are significant

### After Duplicate Removal

Once duplicates are removed:
1. Re-run primary key creation: `python3 add_primary_keys.py --test`
2. Verify no duplicates remain
3. Continue with rest of pipeline (indexes → foreign keys → validation)

---

## Pipeline Phases

### Phase 0: Remove Duplicates - **REQUIRED BEFORE PRIMARY KEYS**

**Scripts:** `investigate_duplicates.py`, `analyze_duplicates.py`, `remove_duplicates.py`

**Purpose:** Remove duplicate records that prevent primary key creation

**See:** [Handling Duplicate Records](#handling-duplicate-records-required-before-primary-keys) section above for detailed workflow.

**Estimated time:**
- Investigation: 30-60 minutes
- Removal: 2-4 hours (depends on number of duplicates)

---

### Phase 1: Apply Merged IDs (1-2 hours) - **OPTIONAL, RECOMMENDED TO SKIP**

**Script:** `apply_merged_ids.py`

**Purpose:** Update old/deprecated entity IDs to canonical IDs

**⚠️ SKIP RECOMMENDATION:** Based on validation testing:
- Only 0.05% of records have merged IDs (1.1M merged IDs exist but only ~138k database records affected)
- Minimal impact on orphan reduction
- Saves 1-4 hours of processing time
- Can always run later if needed

**What it does:**
- Loads all merged_ids CSV.gz files for: authors, works, institutions, sources
- Builds lookup tables (old_id → canonical_id)
- Updates critical tables: `authorship`, `citations_by_year`, `referenced_works`, `related_works`

**Validate before running:**
```bash
python3 validate_merged_ids_impact.py  # Detailed validation
python3 quick_merged_check.py          # Fast check
```

**Run independently (if needed):**
```bash
python3 apply_merged_ids.py --test  # Test database
python3 apply_merged_ids.py         # Production database
```

---

### Phase 2: Orphan Analysis (30-45 minutes)

**Script:** `analyze_orphans.py`

**Purpose:** Identify records with foreign keys pointing to non-existent entities

**What it does:**
- Checks all FK relationships (authorship, work_topics, citations, etc.)
- Identifies orphaned records using LEFT JOIN queries
- Exports orphan ID manifests to `orphan_manifests/` directory
- Generates summary report

**Output files:**
- `orphan_manifests/authorship_author_id_orphans.csv` - Missing author IDs
- `orphan_manifests/referenced_works_referenced_work_id_orphans.csv` - Missing work IDs
- `orphan_manifests/orphan_summary_report.csv` - Summary statistics

**Why critical:** These manifests are used for retrieving missing entities via OpenAlex API

**Run independently:**
```bash
python3 analyze_orphans.py --test
python3 analyze_orphans.py
```

---

### Phase 3: Add Primary Keys (~7 hours)

**Script:** `add_primary_keys.py`

**Purpose:** Create primary key constraints on all tables

**⚠️ PREREQUISITE:** All duplicates MUST be removed first (see Phase 0). Primary key creation will fail if duplicates exist.

**What it does:**
- Checks for duplicates before creating PKs (will fail if found)
- Creates single-column PKs: `works(work_id)`, `authors(author_id)`, etc.
- Creates composite PKs: `authorship(work_id, author_id, author_position)`, etc.

**Tables with PKs:**
- **Single-column:** works, authors, institutions, sources, publishers, funders, concepts, topics
- **Composite:** authorship, work_topics, work_concepts, citations_by_year, referenced_works, etc.

**Timing (based on test runs):**
- Small tables (<1M rows): Seconds
- Medium tables (100M rows): ~10-30 minutes
- Large tables (1-2B rows): ~2-4 hours
- **Total estimated:** ~7.1 hours (throughput: ~159k rows/second)

**Test timing first:**
```bash
python3 test_pk_single_table.py
```

**Run independently:**
```bash
python3 add_primary_keys.py --test
python3 add_primary_keys.py
```

**Note:** No log file is created by default. Output is to stdout only. Redirect to capture:
```bash
python3 add_primary_keys.py --test > logs/add_primary_keys.log 2>&1
```

---

### Phase 4: Add Indexes (2-4 hours)

**Script:** `add_indexes.py`

**Purpose:** Create indexes on FK columns and common query fields

**What it does:**
- Creates indexes on ALL foreign key columns (critical for FK validation)
- Creates indexes on common query columns (names, dates, counts)
- Creates composite indexes for common queries

**Why BEFORE FKs:** FK validation is 10-100x faster with indexes in place

**Index types:**
- FK column indexes (btree): ~50 indexes
- Query column indexes (btree): ~15 indexes
- Composite indexes: ~5 indexes

**Run independently:**
```bash
python3 add_indexes.py --test
python3 add_indexes.py
```

---

### Phase 5: Add Foreign Keys (5-10 minutes)

**Script:** `add_foreign_keys.py`

**Purpose:** Create all foreign key constraints (NOT VALID)

**What it does:**
- Creates ~40 foreign key constraints
- Uses `NOT VALID` flag for fast creation (no immediate validation)
- Uses `ON DELETE CASCADE` for referential integrity

**Why NOT VALID:** Creating FKs without validation is instant. Validation happens separately.

**Foreign keys created:**
- Authorship: author_id, work_id, institution_id
- Work relationships: work_topics, work_concepts, work_sources, etc.
- Author relationships: author_topics, author_concepts, author_institutions
- Citations: citations_by_year, referenced_works, related_works
- Hierarchies: institution_hierarchy, topic_hierarchy

**Run independently:**
```bash
python3 add_foreign_keys.py --test
python3 add_foreign_keys.py
```

---

### Phase 6: Validate Constraints (4-8 hours)

**Script:** `validate_constraints.py`

**Purpose:** Validate all NOT VALID foreign keys

**What it does:**
- Finds all constraints marked NOT VALID
- Runs `ALTER TABLE ... VALIDATE CONSTRAINT` on each
- Logs validation failures to `logs/validation_failures.log`

**Expected behavior:**
- Some FKs WILL fail validation (orphaned records exist)
- This is EXPECTED - orphans are flagged for API retrieval
- Script logs failures but doesn't exit with error

**Run independently:**
```bash
python3 validate_constraints.py --test
python3 validate_constraints.py
```

---

### Phase 7: Generate Reports (1-2 minutes)

**Script:** `generate_report.py`

**Purpose:** Document all constraints, indexes, and statistics

**What it does:**
- Exports list of all primary keys
- Exports list of all foreign keys (with validation status)
- Exports list of all indexes
- Exports table row counts
- Generates markdown summary report

**Output files:**
- `reports/primary_keys_YYYYMMDD_HHMMSS.csv`
- `reports/foreign_keys_YYYYMMDD_HHMMSS.csv`
- `reports/indexes_YYYYMMDD_HHMMSS.csv`
- `reports/table_statistics_YYYYMMDD_HHMMSS.csv`
- `reports/CONSTRAINT_SUMMARY_YYYYMMDD_HHMMSS.md` ← **Main summary**

**Run independently:**
```bash
python3 generate_report.py --test
python3 generate_report.py
```

---

## Monitoring Progress

### Check Overall Status

```bash
python3 orchestrator_constraints.py --status
```

Output:
```
======================================================================
CONSTRAINT BUILDING STATUS
Database: oadb2_test
======================================================================
  ✅ Merged Ids          complete
  ✅ Orphan Analysis     complete
  ✅ Primary Keys        complete
  ⏳ Indexes             running
  ⏸️  Foreign Keys       pending
  ⏸️  Validation         pending
  ⏸️  Reporting          pending
======================================================================
```

### Monitor Logs in Real-Time

```bash
# Main orchestrator log
tail -f logs/constraints.log

# Validation failures
tail -f logs/validation_failures.log
```

### Resume After Interruption

```bash
python3 orchestrator_constraints.py --resume --test
```

The orchestrator saves state after each phase, so progress is never lost.

---

## Expected Results

### Test Database (oadb2_test)

Assuming test database is a clone of production:

| Phase | Expected Result |
|-------|-----------------|
| Merged IDs | ~500k-2M ID updates across critical tables |
| Orphan Analysis | 10-30% orphan rate in referenced_works, 1-5% in authorship |
| Primary Keys | ~25 PKs created |
| Indexes | ~70 indexes created |
| Foreign Keys | ~40 FKs created (NOT VALID) |
| Validation | 5-15 FKs fail validation (orphans exist) |
| Reports | 5 report files generated |

### Production Database (oadb2)

Same as test, but larger scale.

**Estimated Time:**
- Merged IDs: 1-2 hours
- Orphan Analysis: 30-45 minutes
- Primary Keys: 20-30 minutes
- Indexes: 2-4 hours
- Foreign Keys: 5-10 minutes
- Validation: 4-8 hours
- Reporting: 1-2 minutes

**Total: 8-15 hours**

---

## Handling Orphaned Records

### What Are Orphaned Records?

Records with foreign keys pointing to entities that don't exist in the database.

**Common examples:**
- `authorship.author_id = 'A12345'` but `A12345` doesn't exist in `authors` table
- `referenced_works.referenced_work_id = 'W67890'` but `W67890` doesn't exist in `works` table

### Why Do They Exist?

1. **Incomplete data loading** - Not all entities from snapshot were loaded yet
2. **External entities** - References to works/authors outside the snapshot
3. **Deprecated IDs** - Some IDs were merged but not all mappings were in merged_ids

### How to Retrieve Missing Entities

**Step 1: Review orphan manifests**
```bash
cd orphan_manifests
cat orphan_summary_report.csv
```

**Step 2: Use OpenAlex API to retrieve missing entities**

The manifest files contain missing entity IDs. Create a script to:
1. Read orphan manifest CSVs
2. For each orphaned ID, call OpenAlex API:
   ```
   https://api.openalex.org/works/W12345
   https://api.openalex.org/authors/A67890
   ```
3. Parse response and insert into database
4. Re-run validation

**Example:**
```python
import requests
import pandas as pd

# Read orphan manifest
orphans = pd.read_csv('authorship_author_id_orphans.csv')

for author_id in orphans['orphaned_id']:
    url = f"https://api.openalex.org/authors/{author_id}"
    response = requests.get(url, params={'mailto': 's.lucasblack@gmail.com'})

    if response.status_code == 200:
        author_data = response.json()
        # Insert author_data into database
        ...
```

**Step 3: Re-run validation**
```bash
python3 validate_constraints.py --test
```

---

## Troubleshooting

### Issue 1: "Found X duplicate groups - CANNOT CREATE PK"

**Symptom:** Primary key creation fails with message about duplicates

**Solution:**
1. Run investigation to understand the duplicates:
   ```bash
   python3 investigate_duplicates.py --test --quick
   ```
2. Analyze impact:
   ```bash
   python3 analyze_duplicates.py --test
   ```
3. Remove duplicates (after dry-run test):
   ```bash
   python3 remove_duplicates.py --test --dry-run
   python3 remove_duplicates.py --test
   ```
4. Re-run primary key creation:
   ```bash
   python3 add_primary_keys.py --test
   ```

**Root causes:**
- Data loaded multiple times
- Parsing scripts didn't enforce uniqueness
- Source data contained duplicates

### Issue 2: "Merged IDs directory not found"

**Symptom:** `apply_merged_ids.py` reports missing merged_ids directory

**Solution:**
- Verify path: `/Volumes/OA_snapshot/24OCT2025/data/merged_ids/`
- Check if external drive is mounted
- Update `MERGED_IDS_DIR` in `apply_merged_ids.py` if path changed
- Consider skipping this phase (minimal impact, 0.05% match rate)

### Issue 3: "Foreign key validation fails"

**Symptom:** Many FKs fail validation with orphaned records

**Solution:**
- This is EXPECTED - orphaned records will exist
- Review `orphan_manifests/` to see which entities are missing
- Retrieve missing entities via OpenAlex API
- Re-run validation after retrieval

### Issue 4: "Index creation takes too long"

**Symptom:** `add_indexes.py` runs for 6+ hours

**Solution:**
- This is normal on large tables (works: 250M rows, authorship: 500M+ rows)
- Ensure database has sufficient `work_mem` and `maintenance_work_mem`
- Monitor with: `SELECT * FROM pg_stat_progress_create_index;`

### Issue 5: "Database disk space full"

**Symptom:** Constraint creation fails with "no space left on device"

**Solution:**
- Indexes and constraints require significant disk space
- Ensure 200-300GB free space on database volume
- Check disk usage: `df -h /path/to/postgresql/data`

---

## Performance Optimization

### PostgreSQL Configuration

For optimal performance, adjust `postgresql.conf`:

```ini
# Memory settings
shared_buffers = 8GB
work_mem = 256MB
maintenance_work_mem = 2GB
effective_cache_size = 24GB

# Checkpoint settings (for large writes)
checkpoint_timeout = 30min
max_wal_size = 10GB

# Parallel workers
max_parallel_workers_per_gather = 4
max_parallel_workers = 8
```

### Monitor Progress

```sql
-- Check index creation progress
SELECT * FROM pg_stat_progress_create_index;

-- Check table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## After Constraint Building

### 1. Review Final Reports

```bash
cat reports/CONSTRAINT_SUMMARY_*.md
```

### 2. Retrieve Missing Entities (If Needed)

If orphaned records exist:
1. Use orphan manifests to retrieve entities via API
2. Insert missing entities into database
3. Re-run: `python3 validate_constraints.py`

### 3. Analyze Database

Update PostgreSQL statistics:
```sql
ANALYZE;
```

### 4. Test Queries

Verify constraints are working:
```sql
-- Test FK constraint
DELETE FROM authors WHERE author_id = 'A12345';
-- Should cascade delete from authorship

-- Test PK constraint
INSERT INTO authors (author_id, display_name) VALUES ('A12345', 'Test');
INSERT INTO authors (author_id, display_name) VALUES ('A12345', 'Duplicate');
-- Should fail with duplicate key error
```

### 5. Move to Next Phase

Proceed to Phase 04: Author Profile Building

---

## Command Reference

```bash
# STEP 0: Handle Duplicates (REQUIRED FIRST)
python3 investigate_duplicates.py --test --quick          # Quick check all tables
python3 investigate_duplicates.py --test --table works --pk work_id  # Detailed investigation
python3 analyze_duplicates.py --test                       # Comprehensive analysis
python3 remove_duplicates.py --test --dry-run             # Test removal
python3 remove_duplicates.py --test                       # Actually remove

# Full pipeline (test database) - AFTER removing duplicates
python3 orchestrator_constraints.py --start --test

# Full pipeline (production) - AFTER removing duplicates
python3 orchestrator_constraints.py --start

# Resume after interruption
python3 orchestrator_constraints.py --resume

# Check status
python3 orchestrator_constraints.py --status

# Reset state (start fresh)
python3 orchestrator_constraints.py --reset

# Run individual phases
python3 apply_merged_ids.py --test
python3 analyze_orphans.py --test
python3 add_primary_keys.py --test
python3 add_indexes.py --test
python3 add_foreign_keys.py --test
python3 validate_constraints.py --test
python3 generate_report.py --test

# Validation & testing
python3 validate_merged_ids_impact.py  # Check merged IDs impact
python3 quick_merged_check.py          # Fast merged IDs check
python3 test_pk_single_table.py        # Test PK timing
python3 create_test_database.py        # Create test DB
python3 check_databases.py             # List databases
python3 list_tables.py                 # List tables
```

---

## Design Decisions

### Why NOT VALID for Foreign Keys?

Creating FKs with `NOT VALID` is 100-1000x faster on large tables because:
- No immediate table scan required
- FK metadata created instantly
- Validation happens in separate step (can be parallelized in future)

### Why Indexes Before FKs?

FK validation scans child table for every parent row. With indexes:
- Validation is 10-100x faster
- Future queries using FKs are fast

### Why Flag Orphans Instead of Deleting?

Per user requirement: "Flag orphans for API retrieval"
- Preserves all data
- Allows retrieval of missing entities
- Enables complete database (no data loss)

### Why Apply Merged IDs to Critical Tables Only?

Per user requirement: "Apply only to critical tables (authorship, citations)"
- Saves 50-60% time vs full application
- Focuses on tables critical for network analysis
- Still reduces most orphans

---

## Support and Issues

For issues or questions:
1. Check logs in `logs/` directory
2. Review `orphan_manifests/` for orphaned records
3. Review `reports/CONSTRAINT_SUMMARY_*.md` for status
4. Check database connection and disk space

---

**Last Updated:** November 2025
**Version:** 1.0 (Constraint Building Pipeline)
