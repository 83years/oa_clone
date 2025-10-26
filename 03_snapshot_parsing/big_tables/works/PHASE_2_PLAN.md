# Phase 2: Building Joining Tables - Comprehensive Plan

## Overview

**Phase 1 (Complete):** Works table fully populated with all metadata
**Phase 2 (This Plan):** Build all joining tables that link works to authors, topics, concepts, citations, etc.

## Strategy: Fast Bulk Loading

### Traditional Approach (SLOW - ❌ Don't use)
```
1. CREATE TABLE with FK constraints
2. INSERT row by row (each insert validates FKs)
3. Very slow for 100M+ records
```

### Bulk Approach (FAST - ✅ Use this)
```
1. CREATE TABLE WITHOUT FK constraints
2. COPY bulk data (no validation, very fast)
3. Analyze and report FK violations
4. DELETE invalid records (orphaned relationships)
5. ADD FK constraints (one-time validation)
6. CREATE indexes
```

**Why this works:**
- COPY is 100-1000x faster than INSERT
- Validation happens once at the end, not per-row
- Can identify and fix data quality issues in batch
- Can parallelize the loading

---

## Pre-Phase 2 Verification

### 1. Verify Works Table Complete

```bash
# Run verification script
python3 verify_works_complete.py
```

**Checks:**
- [ ] All works files processed (check orchestrator state)
- [ ] No duplicate work_ids
- [ ] Expected row count (~250M records)
- [ ] No NULL work_ids
- [ ] Date ranges look correct
- [ ] Sample random works for data quality

**SQL checks:**
```sql
-- Total works count
SELECT COUNT(*) FROM works;

-- Check for duplicates
SELECT work_id, COUNT(*) FROM works GROUP BY work_id HAVING COUNT(*) > 1;

-- Check for NULLs
SELECT COUNT(*) FROM works WHERE work_id IS NULL;

-- Date range
SELECT MIN(publication_year), MAX(publication_year) FROM works;

-- Sample data
SELECT * FROM works LIMIT 100;
```

### 2. Verify Entity Tables Complete

**Required entities:**
- [ ] Authors table complete (~100M records)
- [ ] Topics table complete (~4.5K records)
- [ ] Concepts table complete (~65K records)
- [ ] Sources table complete (~250K records)
- [ ] Funders table complete (~30K records)
- [ ] Institutions table complete (~110K records)

**SQL checks:**
```sql
SELECT
    'authors' as table_name, COUNT(*) as count FROM authors
UNION ALL
SELECT 'topics', COUNT(*) FROM topics
UNION ALL
SELECT 'concepts', COUNT(*) FROM concepts
UNION ALL
SELECT 'sources', COUNT(*) FROM sources
UNION ALL
SELECT 'funders', COUNT(*) FROM funders
UNION ALL
SELECT 'institutions', COUNT(*) FROM institutions;
```

### 3. Disk Space Check

**Estimate joining table sizes:**
- `authorship`: ~1B records × ~100 bytes = ~100GB
- `work_topics`: ~750M records × ~50 bytes = ~38GB
- `work_concepts`: ~2B records × ~50 bytes = ~100GB
- `citations_by_year`: ~500M records × ~40 bytes = ~20GB
- `referenced_works`: ~2.5B records × ~60 bytes = ~150GB
- **Total estimate: ~500GB+**

```bash
# Check available disk space
df -h /path/to/postgres/data
```

---

## Joining Tables - Prioritization

### Tier 1: Self-Referential (No External FK Dependencies)

These only reference `works(work_id)` - can be built immediately after works table is complete.

| Table | Estimated Rows | Source Field | Priority |
|-------|---------------|--------------|----------|
| `citations_by_year` | ~500M | `work.counts_by_year[]` | HIGH |
| `alternate_ids` | ~400M | `work.ids{}` | MEDIUM |
| `work_keywords` | ~300M | `work.keywords[]` | MEDIUM |
| `related_works` | ~2.5B | `work.related_works[]` | LOW |
| `referenced_works` | ~2.5B | `work.referenced_works[]` | HIGH |

**Notes:**
- `referenced_works.referenced_work_id` may not exist in works table (external references)
- Will need to handle orphaned references gracefully

### Tier 2: Cross-Entity Dependencies

These require BOTH `works` and another entity table to be complete.

| Table | Estimated Rows | Dependencies | Priority |
|-------|---------------|--------------|----------|
| `authorship` | ~1B | works + authors | **CRITICAL** |
| `work_topics` | ~750M | works + topics | **CRITICAL** |
| `work_concepts` | ~2B | works + concepts | HIGH |
| `work_sources` | ~250M | works + sources | HIGH |
| `work_funders` | ~50M | works + funders | MEDIUM |
| `apc` | ~10M | works only | MEDIUM |

**Processing Order:**
1. `authorship` - Essential for author-work links
2. `work_topics` - Essential for subject classification
3. `work_concepts` - Important for concept analysis
4. `work_sources` - Important for journal/venue links
5. `citations_by_year` - Important for temporal analysis
6. `referenced_works` - Important for citation networks
7. Others - Lower priority

---

## Architecture Design

### Option 1: Monolithic Parser (Single Pass) ⭐ RECOMMENDED

**Pros:**
- Read works files ONCE
- Extract ALL relationships simultaneously
- Most efficient use of I/O
- Fastest overall

**Cons:**
- More complex code
- All-or-nothing processing
- Harder to debug individual tables

### Option 2: Modular Parsers (Per Table)

**Pros:**
- Simple, focused code
- Can retry individual tables
- Easy to debug
- Incremental progress

**Cons:**
- Read works files MULTIPLE times (slow)
- Redundant I/O
- Much slower overall

### Option 3: Hybrid (Two-Phase) ⭐⭐ BEST CHOICE

**Phase 2a: Extract to CSV**
- Single parser reads works files ONCE
- Extracts ALL relationships
- Writes to CSV files (one per joining table)
- Fast, streaming, memory-efficient

**Phase 2b: Load from CSV**
- Bulk COPY CSVs into tables
- Validate and clean data
- Add FK constraints
- Create indexes

**Advantages:**
- Single I/O pass (fast)
- Modular loading (flexible)
- Can retry individual table loads
- CSVs can be verified/inspected before loading
- Easy to parallelize loading phase

---

## Implementation Plan

### Step 1: Create Extraction Parser

**File:** `parse_works_relationships.py`

**Function:**
- Reads works .gz files (same as parse_works.py)
- Extracts relationship data from each work
- Streams to CSV files using PostgreSQL COPY format
- Handles large files with buffering

**Output CSV files:**
- `authorship.csv`
- `work_topics.csv`
- `work_concepts.csv`
- `work_sources.csv`
- `citations_by_year.csv`
- `referenced_works.csv`
- `related_works.csv`
- `alternate_ids.csv`
- `work_keywords.csv`
- `work_funders.csv`
- `apc.csv`

**Key features:**
- Streaming writes (don't load all in memory)
- Progress tracking
- State management (resume capability)
- Error handling

### Step 2: Create CSV Loader

**File:** `load_relationships.py`

**Function for each table:**
1. **Create table without FK constraints**
   ```sql
   CREATE TABLE authorship (
       work_id VARCHAR(255),
       author_id VARCHAR(255),
       ...
       -- NO FK CONSTRAINTS YET
   );
   ```

2. **Bulk COPY from CSV**
   ```sql
   COPY authorship FROM '/path/to/authorship.csv' WITH CSV;
   ```

3. **Analyze FK violations**
   ```sql
   -- Find orphaned work_ids
   SELECT COUNT(*) FROM authorship a
   WHERE NOT EXISTS (SELECT 1 FROM works w WHERE w.work_id = a.work_id);

   -- Find orphaned author_ids
   SELECT COUNT(*) FROM authorship a
   WHERE NOT EXISTS (SELECT 1 FROM authors au WHERE au.author_id = a.author_id);
   ```

4. **Clean invalid records**
   ```sql
   DELETE FROM authorship a
   WHERE NOT EXISTS (SELECT 1 FROM works w WHERE w.work_id = a.work_id)
      OR NOT EXISTS (SELECT 1 FROM authors au WHERE au.author_id = a.author_id);
   ```

5. **Add FK constraints**
   ```sql
   ALTER TABLE authorship
   ADD CONSTRAINT fk_authorship_work
   FOREIGN KEY (work_id) REFERENCES works(work_id) ON DELETE CASCADE;

   ALTER TABLE authorship
   ADD CONSTRAINT fk_authorship_author
   FOREIGN KEY (author_id) REFERENCES authors(author_id) ON DELETE CASCADE;
   ```

6. **Create indexes**
   ```sql
   CREATE INDEX idx_authorship_work_id ON authorship(work_id);
   CREATE INDEX idx_authorship_author_id ON authorship(author_id);
   ```

7. **Report statistics**
   - Total records loaded
   - Invalid records removed
   - FK violations by type
   - Final row count

### Step 3: Create Orchestrator

**File:** `orchestrator_relationships.py`

**Function:**
- Coordinates entire Phase 2
- Runs extraction parser
- Runs CSV loaders in order
- Tracks state
- Handles resume
- Generates final report

---

## Execution Plan

### Part A: Pre-Verification (1 hour)
```bash
# Verify works table
python3 verify_works_complete.py

# Verify entity tables
python3 verify_entities_complete.py

# Check disk space
df -h
```

### Part B: Extract Relationships (12-24 hours)
```bash
# Run extraction parser
python3 parse_works_relationships.py

# This will:
# - Read all works files once
# - Extract all relationships
# - Write to CSV files
# - Track progress
```

**Output:** 11 CSV files ready for loading

### Part C: Load Relationships (6-12 hours)
```bash
# Run loader for each table in priority order
python3 load_relationships.py --table authorship
python3 load_relationships.py --table work_topics
python3 load_relationships.py --table work_concepts
python3 load_relationships.py --table work_sources
python3 load_relationships.py --table citations_by_year
python3 load_relationships.py --table referenced_works
# ... etc
```

**Or use orchestrator:**
```bash
python3 orchestrator_relationships.py
```

### Part D: Verification (1 hour)
```bash
# Verify all joining tables
python3 verify_relationships_complete.py
```

---

## Error Handling Strategy

### FK Violations

**Expected scenarios:**
1. **Orphaned work_ids** - Should NOT happen (works table is complete)
2. **Orphaned author_ids** - WILL happen (some authors not in snapshot)
3. **Orphaned topic_ids** - Unlikely but possible
4. **Orphaned concept_ids** - Unlikely but possible
5. **Orphaned source_ids** - WILL happen (some sources not in snapshot)
6. **Orphaned funder_ids** - WILL happen (some funders not in snapshot)

**Handling strategy:**
- **Log all violations** - Save to separate CSV for analysis
- **Report statistics** - How many of each type
- **Delete orphaned records** - Clean before adding FKs
- **Optional: Flag for API retrieval** - Missing entities can be fetched later

### Data Quality Issues

**Potential issues:**
- Malformed IDs
- NULL values where not expected
- Duplicate relationships
- Invalid dates/scores

**Handling:**
- Validate during extraction
- Clean during loading
- Log all issues
- Generate data quality report

---

## Performance Optimization

### During Extraction:
- Batch writes to CSV (every 10K records)
- Use buffered I/O
- Compress CSVs if disk space limited

### During Loading:
- Disable triggers during COPY
- Set `session_replication_role = replica`
- Increase `maintenance_work_mem`
- Disable autovacuum temporarily
- Build indexes AFTER bulk load

### Database Settings (temporary):
```sql
-- Increase work memory for bulk operations
SET maintenance_work_mem = '4GB';

-- Disable replication role (skips triggers)
SET session_replication_role = replica;

-- Disable autovacuum during bulk load
ALTER TABLE authorship SET (autovacuum_enabled = false);
```

---

## Monitoring & Progress Tracking

### State File Format:
```json
{
  "phase": "extraction",
  "extraction": {
    "files_processed": 2450,
    "files_total": 3500,
    "works_processed": 180000000,
    "last_file": "part_2449.gz",
    "relationships_extracted": {
      "authorship": 650000000,
      "work_topics": 540000000,
      "work_concepts": 1200000000
    }
  },
  "loading": {
    "authorship": "complete",
    "work_topics": "in_progress",
    "work_concepts": "pending"
  }
}
```

### Progress Logging:
```
[2025-10-25 10:00:00] Starting relationship extraction
[2025-10-25 10:05:00] Processed 1000 files, 50M works, extracted 150M relationships
[2025-10-25 10:10:00] Processed 2000 files, 100M works, extracted 300M relationships
...
```

---

## Success Criteria

### Phase 2 Complete When:
- [ ] All CSV files generated successfully
- [ ] All CSVs loaded into tables
- [ ] FK constraints added to all tables
- [ ] Indexes created on all tables
- [ ] Data quality report reviewed
- [ ] FK violation statistics acceptable (<5% orphaned records)
- [ ] Verification queries pass
- [ ] Final row counts match expectations

### Key Metrics:
- Total authorship records: ~1B
- Total work_topics records: ~750M
- Total work_concepts records: ~2B
- FK violation rate: <5%
- Processing time: <48 hours total

---

## Rollback Plan

**If Phase 2 fails:**
1. CSVs are preserved - can retry loading
2. Can drop joining tables and recreate
3. Works table is untouched
4. Entity tables are untouched

**No data loss risk** - all source data remains intact.

---

## Next Steps

**Ready to proceed?**
1. Review this plan
2. Run pre-verification scripts
3. I'll create the extraction parser (`parse_works_relationships.py`)
4. I'll create the loader script (`load_relationships.py`)
5. I'll create the orchestrator
6. Begin Phase 2 execution
