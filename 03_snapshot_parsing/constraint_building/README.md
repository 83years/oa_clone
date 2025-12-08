# Database Constraint Building Pipeline

Complete guide for adding primary keys, indexes, and foreign keys to the OpenAlex database after data loading is complete.

---

## 🚀 Quick Start for Career Trajectory Analysis

**NEW (December 2025):** Added `--scope` flag to selectively build only the constraints you need right now.

For **immediate career trajectory calculations** (author first/last publication year, current status, authors_works_by_year):

```bash
cd constraint_building

# 1. Add primary keys (REQUIRED FIRST - remove duplicates if needed)
python3 add_primary_keys.py --test

# 2. Add only authorship-related indexes (~20 indexes, <1 hour)
python3 add_indexes.py --scope authorship --test

# 3. (OPTIONAL) Add only authorship-related foreign keys (~10 FKs, <2 minutes)
python3 add_foreign_keys.py --scope authorship --test
```

**What this gives you:**
- ✅ Fast queries on `authorship.author_id` (indexed)
- ✅ Fast queries on `authorship.work_id` (indexed)
- ✅ Fast queries on `works.publication_year` and `works.publication_date` (indexed)
- ✅ Fast queries on `authors_works_by_year` (indexed)
- ✅ Primary keys on all tables for data integrity
- ❌ No keyword search indexes (defer until needed)
- ❌ No work_topics/work_concepts indexes (defer until needed)

**What to skip for now:**
- `--scope keywords` - Only needed when you start searching by title/abstract/keywords
- `--scope all` - Builds ALL indexes (2-4 hours) - only needed for full database queries

**Why scope matters:** Building only authorship indexes saves 60-70% of indexing time and lets you start your career trajectory analysis immediately.

---

## 📋 Recent Updates (December 2025)

### Schema Correction: authorship vs authorship_institutions

**IMPORTANT:** The `authorship` table does NOT have an `institution_id` column. Institution relationships are stored in a separate `authorship_institutions` table.

**Corrected schema:**
- `authorship` table columns: `work_id`, `author_id`, `author_position`, `is_corresponding`, `raw_affiliation_string`
- `authorship_institutions` table columns: `work_id`, `author_id`, `institution_id`

**Scripts updated to fix this:**
- ✅ `add_indexes.py` - Now correctly indexes `authorship_institutions` table
- ✅ `add_foreign_keys.py` - Now correctly creates FKs for `authorship_institutions` table
- ✅ `analyze_orphans.py` - Now correctly analyzes both tables separately

**What changed:**
- Removed incorrect `authorship.institution_id` references
- Added correct `authorship_institutions` table handling
- Added `--scope` flag to both `add_indexes.py` and `add_foreign_keys.py`

---

## Current Status

**Last Updated:** December 6, 2025

**Database:** `oadbv5` (production database on NVMe drives, daily backups to HDD volume)

**Progress:**
- ✅ **Merged IDs** - Skipped (testing showed 0.05% match rate, minimal impact)
- ✅ **Duplicates** - Removed (Nov 29 - Dec 2, 2025)
  - Investigated, analyzed, and removed duplicates from all tables
  - Vacuumed tables to reclaim space
  - Logs in `constraint_building/logs/`
- ✅ **Primary Keys** - Complete except `work_keyword` (Dec 2-6, 2025)
  - All entity tables: works, authors, institutions, sources, etc.
  - All relationship tables: authorship, work_topics, citations_by_year, etc.
  - `work_keyword` table: Deferred (will add later when needed for text search)
  - Throughput: ~159k rows/second
- 🔄 **Indexes** - In progress (started Dec 6, 2025)
  - Currently running: `--scope authorship` (priority for career trajectory analysis)
  - Next: `--scope all` when capacity allows
- ⏸️ **Foreign keys** - Pending (after indexes complete)
- ⏸️ **Orphan analysis** - Deferred (will run after FKs and author trajectory analysis)
- ⏸️ **Validation** - Deferred

**Parallel Work:**
- 🔄 **Author gender inference** - Running in `04_author_profile_building/`

---

## Production Timeline

Actual work completed on `oadbv5`:

| Phase | Dates | Duration | Status | Notes |
|-------|-------|----------|--------|-------|
| Duplicate Investigation | Nov 29, 2025 | 1 day | ✅ Complete | `investigate_duplicates.py`, `analyze_duplicates.py` |
| Duplicate Removal | Nov 29 - Dec 2, 2025 | 4 days | ✅ Complete | Multiple runs with error corrections |
| Table Vacuuming | Dec 2-5, 2025 | 3 days | ✅ Complete | Reclaimed space from deleted duplicates |
| Primary Keys (all except work_keyword) | Dec 2-6, 2025 | 4 days | ✅ Complete | ~159k rows/sec throughput |
| Indexes (authorship scope) | Dec 6, 2025 - TBD | In progress | 🔄 Running | Priority for career trajectories |
| Indexes (all scope) | TBD | Pending | ⏸️ Queued | When capacity allows |
| Foreign Keys | TBD | Pending | ⏸️ Queued | After indexes complete |
| work_keyword Primary Key | TBD | Deferred | ⏸️ Queued | Needed later for text search |
| Orphan Analysis | TBD | Deferred | ⏸️ Queued | After FKs and author analysis |

**Logs location:**
- Database build: `03_snapshot_parsing/logs/`
- Constraint building: `03_snapshot_parsing/constraint_building/logs/`

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

### 2. Database Backup Strategy (IMPORTANT)

**Current setup for `oadbv5`:**
- Production database on NVMe drives for performance
- Daily automated backups to separate HDD volume on NAS
- Working directly on production database
- Can restore from backup if needed

**For testing (optional):**
Clone the production database for safe testing:
```bash
# Use the Python script to handle connection termination
python3 create_test_database.py
```

Or manually with SQL (requires terminating active connections first):
```sql
-- Connect to PostgreSQL as admin
CREATE DATABASE "oadbv5_test" WITH TEMPLATE "oadbv5" OWNER admin;
```

**Note:** All scripts support `--test` flag for working on a test database clone.

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

**Note:** These instructions reflect the workflow used on `oadbv5` production database. For safety, consider testing on a clone first using `--test` flag.

### Step 0: Check for and Remove Duplicates (✅ COMPLETE on oadbv5)

```bash
cd constraint_building

# Investigate duplicates
python3 investigate_duplicates.py --quick

# Get detailed analysis
python3 analyze_duplicates.py

# Remove duplicates (dry-run first!)
python3 remove_duplicates.py --dry-run
python3 remove_duplicates.py
```

**⚠️ CRITICAL:** Primary keys cannot be created if duplicates exist. This step must be completed first.

**Status on oadbv5:** ✅ Complete (Nov 29 - Dec 2, 2025)

### Step 1: Add Primary Keys (✅ COMPLETE on oadbv5)

After removing duplicates:

```bash
cd constraint_building

# Add primary keys to all tables (except work_keywords - deferred)
python3 add_primary_keys.py
```

**Status on oadbv5:** ✅ Complete (Dec 2-6, 2025)

### Step 2: Add Indexes (🔄 IN PROGRESS on oadbv5)

```bash
# Add authorship-related indexes (for career trajectory analysis)
python3 add_indexes.py --scope authorship

# Later: Add all remaining indexes
python3 add_indexes.py --scope all
```

**Status on oadbv5:** 🔄 In progress (started Dec 6, 2025)

### Step 3: Next Steps (Pending)

After indexes complete:

```bash
# Add foreign keys
python3 add_foreign_keys.py --scope authorship  # Or --scope all

# (Optional) Run orphan analysis after author trajectory work
python3 analyze_orphans.py

# (Optional) Validate constraints
python3 validate_constraints.py

# Generate final reports
python3 generate_report.py
```

---

## Handling Duplicate Records (✅ COMPLETE on oadbv5)

### Issue Discovery

During primary key creation, the script checks for duplicate values and will fail if duplicates exist. In the initial oadbv5 build:
- **works table:** 2,838,995 duplicate groups found
- **authors table:** 750,000 duplicate groups found
- Other tables also had duplicates

Primary keys CANNOT be created until duplicates are resolved.

**Status on oadbv5:** ✅ Duplicates removed (Nov 29 - Dec 2, 2025)

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
1. **Vacuum tables** to reclaim disk space from deleted rows:
   ```bash
   # Vacuum individual tables
   python3 vacuum_table.py --table works
   python3 vacuum_table.py --table authors
   # etc.
   ```
2. Re-run primary key creation: `python3 add_primary_keys.py`
3. Verify no duplicates remain
4. Continue with rest of pipeline (indexes → foreign keys → validation)

**On oadbv5:**
- ✅ Duplicates removed (Nov 29 - Dec 2, 2025)
- ✅ Tables vacuumed (Dec 2-5, 2025)
- ✅ Primary keys added (Dec 2-6, 2025)

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

### Phase 3: Add Primary Keys (~4 days actual, ✅ COMPLETE on oadbv5)

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
- **Deferred:** `work_keywords` - keyword column can be very long, PK deferred until needed for text search

**Status on oadbv5:**
- ✅ Complete (Dec 2-6, 2025)
- Actual throughput: ~159k rows/second
- All tables have PKs except `work_keywords` (intentionally deferred)

**Run independently:**
```bash
python3 add_primary_keys.py --test
python3 add_primary_keys.py
```

**Note:** Logging configured to both console and `logs/add_primary_keys.log`

---

### Phase 4: Add Indexes (🔄 IN PROGRESS on oadbv5)

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

**Status on oadbv5:**
- 🔄 In progress (started Dec 6, 2025)
- Currently running: `--scope authorship` (priority for career trajectory calculations)
- Next phase: `--scope all` when capacity allows

**NEW: Scope flag for selective indexing:**
```bash
# Only indexes for career trajectory calculations (RECOMMENDED for immediate needs)
python3 add_indexes.py --scope authorship --test
python3 add_indexes.py --scope authorship

# Only keyword/search indexes (defer until needed)
python3 add_indexes.py --scope keywords --test
python3 add_indexes.py --scope keywords

# All indexes (full database)
python3 add_indexes.py --scope all --test
python3 add_indexes.py --scope all

# Default (same as --scope all)
python3 add_indexes.py --test
python3 add_indexes.py
```

**Scope options:**
- `authorship`: Only authorship, authors, works, authors_works_by_year tables (~20 indexes) - for career trajectory analysis
- `keywords`: Only work_keywords table indexes - for text search capabilities
- `all`: All tables and all indexes (default)

---

### Phase 5: Add Foreign Keys (5-10 minutes for all, <2 minutes for authorship scope)

**Script:** `add_foreign_keys.py`

**Purpose:** Create all foreign key constraints (NOT VALID)

**What it does:**
- Creates ~40 foreign key constraints
- Uses `NOT VALID` flag for fast creation (no immediate validation)
- Uses `ON DELETE CASCADE` for referential integrity

**Why NOT VALID:** Creating FKs without validation is instant. Validation happens separately.

**Foreign keys created:**
- Authorship: author_id, work_id (NOTE: authorship table has NO institution_id column!)
- Authorship institutions: work_id, author_id, institution_id (separate table!)
- Work relationships: work_topics, work_concepts, work_sources, etc.
- Author relationships: author_topics, author_concepts, author_institutions
- Citations: citations_by_year, referenced_works, related_works
- Hierarchies: institution_hierarchy, topic_hierarchy

**NEW: Scope flag for selective FK creation:**
```bash
# Only FKs for career trajectory calculations (RECOMMENDED for immediate needs)
python3 add_foreign_keys.py --scope authorship --test
python3 add_foreign_keys.py --scope authorship

# Only keyword/search FKs (defer until needed)
python3 add_foreign_keys.py --scope keywords --test
python3 add_foreign_keys.py --scope keywords

# All foreign keys (full database)
python3 add_foreign_keys.py --scope all --test
python3 add_foreign_keys.py --scope all

# Default (same as --scope all)
python3 add_foreign_keys.py --test
python3 add_foreign_keys.py
```

**Scope options:**
- `authorship`: Only authorship, authorship_institutions, authors, works tables (~10 FKs) - for career trajectory analysis
- `keywords`: Only work_keywords table FKs - for text search capabilities
- `all`: All tables and all foreign keys (default)

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

## Actual Results on oadbv5

### Completed Phases

| Phase | Actual Result | Duration | Status |
|-------|---------------|----------|--------|
| Merged IDs | Skipped (0.05% impact) | - | ✅ Skipped |
| Duplicate Removal | All duplicates removed from all tables | 4 days | ✅ Complete |
| Table Vacuuming | Space reclaimed from deleted rows | 3 days | ✅ Complete |
| Primary Keys | ~24 PKs created (all except work_keywords) | 4 days | ✅ Complete |
| Indexes (authorship) | ~20 indexes for career trajectories | In progress | 🔄 Running |

### Pending Phases

| Phase | Expected Result | Estimated Time |
|-------|-----------------|----------------|
| Indexes (all) | ~70 total indexes | 2-4 hours |
| Foreign Keys (authorship) | ~10 FKs (NOT VALID) | <2 minutes |
| Foreign Keys (all) | ~40 FKs (NOT VALID) | 5-10 minutes |
| Orphan Analysis | Deferred until after author analysis | 30-45 minutes |
| Validation | Deferred until needed | 4-8 hours |
| Reports | 5 report files | 1-2 minutes |

### Actual Timing vs Estimates

- **Duplicates:** 4 days actual (included investigation, removal, vacuum)
- **Primary Keys:** 4 days actual (vs. ~7 hours estimated) - likely due to large table sizes
- **Throughput:** ~159k rows/second (as estimated)

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

# Run indexes with scope
python3 add_indexes.py --scope authorship --test  # Only authorship indexes (RECOMMENDED)
python3 add_indexes.py --scope keywords --test    # Only keyword indexes
python3 add_indexes.py --scope all --test         # All indexes
python3 add_indexes.py --test                     # All indexes (default)

# Run foreign keys with scope
python3 add_foreign_keys.py --scope authorship --test  # Only authorship FKs (RECOMMENDED)
python3 add_foreign_keys.py --scope keywords --test    # Only keyword FKs
python3 add_foreign_keys.py --scope all --test         # All FKs
python3 add_foreign_keys.py --test                     # All FKs (default)

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

## Summary

This README documents the constraint building pipeline for the OpenAlex database clone project. The pipeline has been successfully applied to the `oadbv5` production database with the following key outcomes:

- ✅ All duplicates removed (Nov 29 - Dec 2, 2025)
- ✅ All tables vacuumed (Dec 2-5, 2025)
- ✅ Primary keys added to all tables except `work_keywords` (Dec 2-6, 2025)
- 🔄 Authorship indexes in progress (started Dec 6, 2025)
- ⏸️ Full indexing, foreign keys, and validation deferred until after author trajectory analysis

**Next Steps:**
1. Complete authorship indexes
2. Begin author career trajectory calculations
3. Add remaining indexes when capacity allows
4. Add foreign keys for data integrity
5. Run orphan analysis for missing entity retrieval

---

**Last Updated:** December 6, 2025
**Database:** oadbv5 (production)
**Version:** 2.0 (Updated with actual production results)
