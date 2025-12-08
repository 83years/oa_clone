# Database Rebuild Readiness Checklist
**Target Database**: `oadbv5`
**Date**: 2025-12-08
**Rebuild Type**: Complete wipe and rebuild with parse_works_v3.py

---

## Current Configuration Status

### Database Configuration:
```python
# From config.py:
Database: oadbv5
Host: 192.168.1.162
Port: 55432
User: admin
```

**✅ Configuration is CORRECT** - Will target `oadbv5` database

---

## Pre-Flight Checklist

### 1. ✅ Critical New Files Present

| File | Status | Size | Purpose |
|------|--------|------|---------|
| `02_postgres_setup/orchestrator.py` | ✅ READY | 24KB | Creates 35 tables (32+3 new) |
| `03_snapshot_parsing/parse_works_v3.py` | ✅ READY | 30KB | Enhanced parser with names |
| `03_snapshot_parsing/base_parser.py` | ✅ READY | 8.2KB | Base parsing logic |
| `04_author_profile_building/00_build_authors_from_works.py` | ✅ READY | 10KB | Builds authors table |

### 2. ✅ Reference Parser Files Present

| Parser | Status | Purpose |
|--------|--------|---------|
| `parse_topics_v2.py` | ✅ READY | Parse topics |
| `parse_concepts_v2.py` | ✅ READY | Parse concepts |
| `parse_institutions_v2.py` | ✅ READY | Parse institutions |
| `parse_sources_v2.py` | ✅ READY | Parse sources |
| `parse_publishers_v2.py` | ✅ READY | Parse publishers |
| `parse_funders_v2.py` | ✅ READY | Parse funders |

### 3. ⚠️ Dependencies Check

**CRITICAL**: Need to install `nameparser` for parse_works_v3.py

```bash
# Check if installed:
pip list | grep nameparser

# If not installed:
pip install nameparser
```

**Status**: ⚠️ **VERIFY BEFORE PROCEEDING**

### 4. ✅ Data Source Paths

From config.py:
```
SNAPSHOT_DIR: /Volumes/Series/25NOV2025/data
```

Check data availability:
```bash
# Verify paths exist:
ls -lh /Volumes/Series/25NOV2025/data/topics/
ls -lh /Volumes/Series/25NOV2025/data/concepts/
ls -lh /Volumes/Series/25NOV2025/data/institutions/
ls -lh /Volumes/Series/25NOV2025/data/sources/
ls -lh /Volumes/Series/25NOV2025/data/works/

# Check works data specifically:
ls -lh /Volumes/Series/25NOV2025/data/works/updated_date=2022-02-01/ | head
```

**Status**: ⚠️ **VERIFY DATA PATHS EXIST**

### 5. ✅ Database Connection

Test database connectivity:
```bash
# Test connection:
psql -h 192.168.1.162 -p 55432 -U admin -d postgres -c "SELECT version();"

# Check if oadbv5 exists:
psql -h 192.168.1.162 -p 55432 -U admin -d postgres -c "\l" | grep oadbv5
```

**Status**: ⚠️ **VERIFY CONNECTION BEFORE PROCEEDING**

### 6. ⚠️ Backup Current Database (Optional but Recommended)

If you want to keep a backup of current `oadbv5` before wiping:

```bash
# Backup current database:
pg_dump -h 192.168.1.162 -p 55432 -U admin oadbv5 > /backup/oadbv5_backup_20251208.sql

# Or just backup schema (much faster):
pg_dump -h 192.168.1.162 -p 55432 -U admin --schema-only oadbv5 > /backup/oadbv5_schema_20251208.sql
```

**Status**: ⚠️ **DECIDE IF YOU WANT BACKUP**

### 7. ⚠️ Disk Space Check

Estimate required space:
- Works data: ~200GB (compressed) → ~2TB (database)
- Reference tables: ~50GB
- Indexes (added later): ~500GB
- **Total estimated**: ~2.5TB

Check available space on database server:
```bash
# Check disk space on NAS:
ssh admin@192.168.1.162 -p 86 "df -h | grep postgres"

# Or if PostgreSQL data is on specific volume:
ssh admin@192.168.1.162 -p 86 "df -h"
```

**Status**: ⚠️ **VERIFY DISK SPACE AVAILABLE**

---

## What Will Be Created

### Database Schema (35 Tables):

**Phase 0: Reference Tables (6 tables)**
1. topics
2. concepts
3. publishers
4. funders
5. sources
6. institutions
7. institution_geo

**Phase 1: Main Entity Tables (2 tables)**
8. authors (built AFTER works parsing using 00_build_authors_from_works.py)
9. works

**Phase 2: Relationship Tables (13 tables - 3 NEW)**
10. authorship (ENHANCED: +2 columns: raw_author_name, author_display_name)
11. authorship_institutions (ENHANCED: +1 column: country_code)
12. ✨ **authorship_countries** (NEW)
13. ✨ **author_names** (NEW - with forename/lastname parsing)
14. ✨ **work_locations** (NEW)
15. work_topics
16. work_concepts
17. work_sources
18. citations_by_year
19. referenced_works
20. related_works
21. work_funders
22. work_keywords
23. author_topics (from authors snapshot - may skip)
24. author_concepts (from authors snapshot - may skip)
25. author_institutions (from authors snapshot - may skip)
26. source_publishers

**Phase 3: Hierarchy Tables (2 tables)**
27. institution_hierarchy
28. topic_hierarchy

**Phase 4: Supporting Tables (7 tables)**
29. alternate_ids
30. apc
31. search_metadata
32. search_index
33. author_name_variants
34. authors_works_by_year
35. data_modification_log

---

## Parsing Sequence

### Step 1: Database Setup (5 minutes)
```bash
cd /Users/lucas/Documents/openalex_database/python/OA_clone/02_postgres_setup
python orchestrator.py
```

**Expected Output**:
```
✅ 35 tables created (32 original + 3 new)
✅ NO primary keys
✅ NO foreign keys
✅ NO unique constraints
✅ Minimal indexes (only auto-created)
```

### Step 2: Parse Reference Tables First (Optional but Recommended)
```bash
cd /Users/lucas/Documents/openalex_database/python/OA_clone/03_snapshot_parsing

# Parse in order (smallest to largest):
python parse_topics_v2.py --input-file /Volumes/Series/25NOV2025/data/topics/updated_date=*/part_*.gz
python parse_concepts_v2.py --input-file /Volumes/Series/25NOV2025/data/concepts/updated_date=*/part_*.gz
python parse_publishers_v2.py --input-file /Volumes/Series/25NOV2025/data/publishers/updated_date=*/part_*.gz
python parse_funders_v2.py --input-file /Volumes/Series/25NOV2025/data/funders/updated_date=*/part_*.gz
python parse_sources_v2.py --input-file /Volumes/Series/25NOV2025/data/sources/updated_date=*/part_*.gz
python parse_institutions_v2.py --input-file /Volumes/Series/25NOV2025/data/institutions/updated_date=*/part_*.gz
```

**Why**: Having reference tables populated makes works parsing cleaner (validates foreign keys conceptually)

**Time Estimate**: 1-3 hours total

### Step 3: Parse Works with V3 (THE BIG ONE)
```bash
cd /Users/lucas/Documents/openalex_database/python/OA_clone/03_snapshot_parsing

# Test with single file first (RECOMMENDED):
python parse_works_v3.py --input-file /Volumes/Series/25NOV2025/data/works/updated_date=2022-02-01/part_000.gz --limit 10000

# If successful, parse all works files:
python parse_works_v3.py --input-file /Volumes/Series/25NOV2025/data/works/updated_date=2022-02-01/part_*.gz
```

**Time Estimate**: 48-72 hours for all works (depends on data size)

**What Gets Populated**:
- works table (main work records)
- authorship table (with author names!)
- authorship_institutions table (with country codes!)
- authorship_countries table (NEW)
- author_names table (NEW - with forename/lastname)
- work_locations table (NEW)
- work_topics
- work_concepts
- work_sources
- work_keywords
- work_funders
- citations_by_year
- referenced_works
- related_works
- apc
- alternate_ids

### Step 4: Build Authors Table from Works
```bash
cd /Users/lucas/Documents/openalex_database/python/OA_clone/04_author_profile_building

python 00_build_authors_from_works.py
```

**Time Estimate**: 15-30 minutes (large aggregation query)

**What Gets Created**:
- authors table (derived from authorship + works aggregation)
- 100% match guarantee with authorship table

### Step 5: Validation
```bash
# Check record counts:
psql -h 192.168.1.162 -p 55432 -U admin oadbv5 -c "
SELECT
    'works' as table_name, COUNT(*) FROM works
UNION ALL
SELECT 'authorship', COUNT(*) FROM authorship
UNION ALL
SELECT 'author_names', COUNT(*) FROM author_names
UNION ALL
SELECT 'authorship_countries', COUNT(*) FROM authorship_countries
UNION ALL
SELECT 'authors', COUNT(*) FROM authors;
"

# Verify author names have forenames:
psql -h 192.168.1.162 -p 55432 -U admin oadbv5 -c "
SELECT
    COUNT(*) as total_names,
    COUNT(forename) as with_forename,
    ROUND(100.0 * COUNT(forename) / COUNT(*), 2) as forename_pct
FROM author_names;
"

# Check authorship/authors match:
psql -h 192.168.1.162 -p 55432 -U admin oadbv5 -c "
SELECT
    COUNT(DISTINCT a.author_id) as authorship_authors,
    (SELECT COUNT(*) FROM authors) as authors_table,
    COUNT(DISTINCT a.author_id) = (SELECT COUNT(*) FROM authors) as perfect_match
FROM authorship a;
"
```

---

## Known Issues and Gotchas

### 1. ⚠️ Parse Authors Snapshot?
**Decision Needed**: Skip parsing authors snapshot (parse_authors_v2.py)?

**Recommendation**: **SKIP IT**
- We're building authors from works now
- Parsing authors snapshot will create mismatch issues again
- Only parse if you need author_topics, author_concepts for backward compatibility

### 2. ⚠️ Name Parser Failures
If nameparser isn't installed or fails:
- parse_works_v3.py will still work
- forename/lastname columns in author_names will be NULL
- Gender inference will need alternative approach

### 3. ⚠️ Disk Space During Parsing
- PostgreSQL WAL logs can grow large during bulk COPY
- Monitor disk space during works parsing
- Consider: `CHECKPOINT;` commands periodically

### 4. ⚠️ Long Parse Times
Works parsing with v3 takes longer than v2 because:
- More data extraction (names, countries)
- Name parsing overhead (nameparser)
- 3 additional tables being populated

**Mitigation**: Run in tmux/screen session, leave running overnight

---

## Pre-Flight Verification Commands

Run these BEFORE starting:

```bash
# 1. Check Python packages:
python3 -c "import psycopg2; import nameparser; print('✅ All packages installed')"

# 2. Check database connection:
psql -h 192.168.1.162 -p 55432 -U admin -d postgres -c "SELECT 1;" && echo "✅ Database reachable"

# 3. Check data paths exist:
ls /Volumes/Series/25NOV2025/data/works/updated_date=2022-02-01/ && echo "✅ Works data accessible"

# 4. Check disk space:
df -h /Volumes/Series/25NOV2025 && echo "✅ Check if >2.5TB available"

# 5. Check config is correct:
python3 -c "import sys; sys.path.insert(0, '/Users/lucas/Documents/openalex_database/python/OA_clone'); import config; print(f'Database: {config.DB_CONFIG[\"database\"]}'); print(f'Host: {config.DB_CONFIG[\"host\"]}')"
```

---

## Final Readiness Assessment

### ✅ Ready to Proceed If:
- [ ] All critical files present (orchestrator.py, parse_works_v3.py, etc.)
- [ ] `nameparser` package installed (`pip install nameparser`)
- [ ] Database connection verified (can connect to 192.168.1.162:55432)
- [ ] Data paths exist (/Volumes/Series/25NOV2025/data/)
- [ ] Sufficient disk space available (>2.5TB recommended)
- [ ] (Optional) Current database backed up
- [ ] You understand this will WIPE oadbv5 database completely

### ⚠️ Not Ready If:
- [ ] nameparser not installed
- [ ] Cannot connect to database
- [ ] Data paths don't exist
- [ ] Insufficient disk space
- [ ] Need to backup current database first

---

## Rollback Plan

If something goes wrong:

### Option 1: Restore from Backup
```bash
# If you made a backup:
dropdb -h 192.168.1.162 -p 55432 -U admin oadbv5
createdb -h 192.168.1.162 -p 55432 -U admin oadbv5
psql -h 192.168.1.162 -p 55432 -U admin oadbv5 < /backup/oadbv5_backup_20251208.sql
```

### Option 2: Revert to Old Schema
```bash
cd /Users/lucas/Documents/openalex_database/python/OA_clone
git checkout <previous-commit-hash>  # Before v3 changes
python 02_postgres_setup/orchestrator.py
# Parse with old parsers
```

---

## Post-Rebuild Tasks

After successful rebuild:

### 1. Add Constraints (When Ready)
```bash
# Run constraint building scripts (when ready - can take days):
cd 03_snapshot_parsing/constraint_building
python add_primary_keys.py
python add_indexes.py
python add_foreign_keys.py
```

### 2. Gender Inference
```bash
# Use forenames from author_names table:
cd 04_author_profile_building
# Create new gender inference scripts that query author_names table
```

### 3. Geography Analysis
```bash
# Use authorship_countries table:
SELECT author_id, COUNT(DISTINCT country_code) as countries_count
FROM authorship_countries
GROUP BY author_id
HAVING COUNT(DISTINCT country_code) > 1;  -- Authors who worked in multiple countries
```

---

## Quick Start Command

If all checks pass, run these commands in sequence:

```bash
# Terminal 1: Start database rebuild
cd /Users/lucas/Documents/openalex_database/python/OA_clone
pip install nameparser
cd 02_postgres_setup
python orchestrator.py

# Terminal 2: Monitor PostgreSQL logs (optional)
ssh admin@192.168.1.162 -p 86
tail -f /var/lib/postgresql/data/log/postgresql-*.log

# Terminal 1 (continued): Parse works
cd ../03_snapshot_parsing
python parse_works_v3.py --input-file /Volumes/Series/25NOV2025/data/works/updated_date=2022-02-01/part_000.gz --limit 10000  # TEST FIRST
# If successful:
python parse_works_v3.py --input-file /Volumes/Series/25NOV2025/data/works/updated_date=2022-02-01/part_*.gz

# Terminal 1: Build authors
cd ../04_author_profile_building
python 00_build_authors_from_works.py
```

---

## Are You Ready?

**Answer these questions**:

1. ✅ Do you have `nameparser` installed? → Run: `pip install nameparser`
2. ✅ Can you connect to the database? → Run: `psql -h 192.168.1.162 -p 55432 -U admin -d postgres -c "SELECT 1;"`
3. ✅ Does the works data exist? → Run: `ls /Volumes/Series/25NOV2025/data/works/`
4. ✅ Do you have >2.5TB disk space? → Run: `df -h`
5. ✅ Do you want to backup current oadbv5? → **Your choice**
6. ✅ Are you prepared for 48-72 hours of parsing time? → **Your choice**

**If all answers are YES → You're ready to rebuild oadbv5!**

**If any answer is NO → Address the issue first!**
