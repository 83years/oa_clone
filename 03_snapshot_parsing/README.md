# OpenAlex Snapshot Parsing Pipeline

Complete guide for parsing OpenAlex snapshot data into PostgreSQL database.

---

## Overview

This pipeline parses OpenAlex snapshot `.gz` files into a PostgreSQL database using high-performance COPY operations. The system is designed to handle the full ~2TB OpenAlex dataset efficiently.

**Key Features:**
- PostgreSQL COPY for 10-100x faster bulk loading
- Streaming processing (handles 2TB+ without memory issues)
- Multi-file support (processes all `part_*.gz` files in a directory)
- Single-pass extraction (reads each file once, writes to multiple tables)
- Automatic state tracking and resume capability
- Comprehensive error logging

---

## Prerequisites

### 1. Required Software
- Python 3.8+
- PostgreSQL 12+
- Access to OpenAlex snapshot files (mounted at `/Volumes/OA_snapshot/24OCT2025/data`)

### 2. Required Python Packages
```bash
pip install psycopg2-binary
```

### 3. Database Setup
The PostgreSQL database must be set up **before** running the parsers:

```bash
cd ../02_postgres_setup
export ADMIN_PASSWORD='your_password_here'
python3 oadb2_postgresql_setup.py --wipe
```

This creates a **constraint-free** database optimized for bulk loading:
- 31 tables created
- NO primary keys, NO foreign keys, NO indexes
- Ready for fast COPY operations

---

## File Structure

```
03_snapshot_parsing/
├── README.md                    # This file
├── orchestrator.py              # Main orchestrator script
├── base_parser.py               # Base class for all parsers
├── parse_topics_v2.py           # Topics parser (2 tables)
├── parse_concepts_v2.py         # Concepts parser (1 table)
├── parse_publishers_v2.py       # Publishers parser (1 table)
├── parse_funders_v2.py          # Funders parser (1 table)
├── parse_sources_v2.py          # Sources parser (2 tables)
├── parse_institutions_v2.py     # Institutions parser (3 tables)
├── parse_authors_v2.py          # Authors parser (5 tables)
├── parse_works_v2.py            # Works parser (10 tables)
├── orchestrator_state.json      # State file (auto-generated)
└── logs/                        # Error and progress logs
    ├── orchestrator.log
    ├── parse_authors_errors.log
    ├── parse_works_errors.log
    └── ...
```

---

## Configuration

### Update Snapshot Paths

Edit `../config.py` to point to your snapshot directory:

```python
SNAPSHOT_DIR = '/Volumes/OA_snapshot/24OCT2025/data'

GZ_DIRECTORIES = {
    'topics': f'{SNAPSHOT_DIR}/topics/updated_date=YYYY-MM-DD',
    'concepts': f'{SNAPSHOT_DIR}/concepts/updated_date=YYYY-MM-DD',
    'publishers': f'{SNAPSHOT_DIR}/publishers/updated_date=YYYY-MM-DD',
    'funders': f'{SNAPSHOT_DIR}/funders/updated_date=YYYY-MM-DD',
    'sources': f'{SNAPSHOT_DIR}/sources/updated_date=YYYY-MM-DD',
    'institutions': f'{SNAPSHOT_DIR}/institutions/updated_date=YYYY-MM-DD',
    'authors': f'{SNAPSHOT_DIR}/authors/updated_date=YYYY-MM-DD',
    'works': f'{SNAPSHOT_DIR}/works/updated_date=YYYY-MM-DD',
}
```

**Finding the latest/largest folders:**
```bash
python3 find_largest_folders.py
```

This will output the largest folder for each entity type, which typically contains the most updated data.

### Database Connection

The database configuration is in `../config.py`:

```python
DB_CONFIG = {
    'host': '192.168.1.100',
    'port': 55432,
    'database': 'oadb2',
    'user': 'admin',
    'password': os.getenv('ADMIN_PASSWORD', 'secure_password_123')
}
```

**Important:** Set the `ADMIN_PASSWORD` environment variable:
```bash
export ADMIN_PASSWORD='your_password_here'
```

---

## Running the Pipeline

### Step 1: Reset State (Optional)

If starting fresh or after a failed run:

```bash
python3 orchestrator.py --reset
```

This clears the state file so all parsers will run from scratch.

### Step 2: Test Run (Recommended)

Test with a small sample (1,000 lines per file):

```bash
export ADMIN_PASSWORD='your_password_here'
python3 orchestrator.py --start --limit 1000
```

This will:
- Process 1,000 lines from each `.gz` file
- Test all parsers end-to-end
- Complete in ~1 minute
- Load ~700k-3M test records

### Step 3: Production Run

Run the full pipeline (processes all data):

```bash
export ADMIN_PASSWORD='your_password_here'
python3 orchestrator.py --start
```

**Expected Duration:**
- Phase 1 (Topics, Concepts, Publishers, Funders): ~5-10 minutes
- Phase 2 (Sources, Institutions): ~10-20 minutes
- Phase 3 (Authors): **3-6 hours** (~110M authors)
- Phase 4 (Works): **14-24 hours** (~250M works)
- **Total: 2-3 days for complete 2TB dataset**

### Step 4: Resume After Interruption

If the process is interrupted, resume from where it left off:

```bash
export ADMIN_PASSWORD='your_password_here'
python3 orchestrator.py --resume
```

The orchestrator saves state after each entity completes, so you won't lose progress.

---

## Monitoring Progress

### Check Orchestrator Status

```bash
python3 orchestrator.py --status
```

Output shows current state of all parsers:
```
✅ topics          complete   | Records: 4,500 | Errors: 0
✅ concepts        complete   | Records: 65,000 | Errors: 0
⏳ authors         running    | Records: 0 | Errors: 0
⏸️  works          pending    | Records: 0 | Errors: 0
```

### Monitor Logs in Real-Time

```bash
# Watch orchestrator log
tail -f logs/orchestrator.log

# Watch specific parser errors
tail -f logs/parse_authors_errors.log
tail -f logs/parse_works_errors.log
```

### Check Database Record Counts

```bash
python3 check_db_counts.py
```

This shows record counts for all 31 tables.

---

## Understanding the Parsing Phases

The orchestrator runs parsers in dependency order:

### Phase 1: Reference Tables
Small lookup tables that other entities depend on:
- **Topics** → `topics`, `topic_hierarchy` (2 tables)
- **Concepts** → `concepts` (1 table)
- **Publishers** → `publishers` (1 table)
- **Funders** → `funders` (1 table)

### Phase 2: Sources and Institutions
Medium-sized tables:
- **Sources** → `sources`, `source_publishers` (2 tables)
- **Institutions** → `institutions`, `institution_geo`, `institution_hierarchy` (3 tables)

### Phase 3: Authors
Large dataset (~110M authors):
- **Authors** → `authors`, `author_topics`, `author_concepts`, `author_institutions`, `authors_works_by_year` (5 tables)

### Phase 4: Works
Massive dataset (~250M works):
- **Works** → `works`, `authorship`, `work_topics`, `work_concepts`, `work_sources`, `work_keywords`, `work_funders`, `citations_by_year`, `referenced_works`, `related_works` (10 tables)

---

## Data Tables Populated

### Reference Tables (9 tables)
1. `topics` - Research topics
2. `topic_hierarchy` - Topic relationships (domain→field→subfield→topic)
3. `concepts` - Legacy concepts
4. `publishers` - Academic publishers
5. `funders` - Research funders
6. `sources` - Academic sources (journals, conferences)
7. `source_publishers` - Source-publisher relationships
8. `institutions` - Academic institutions
9. `institution_geo` - Institution geographic data
10. `institution_hierarchy` - Institution relationships

### Author Tables (5 tables)
11. `authors` - Author profiles
12. `author_topics` - Author research topics
13. `author_concepts` - Author research concepts
14. `author_institutions` - Author-institution affiliations
15. `authors_works_by_year` - Author publication counts by year

### Work Tables (10 tables)
16. `works` - Publications (articles, books, etc.)
17. `authorship` - Work-author-institution relationships ⭐
18. `work_topics` - Work topics
19. `work_concepts` - Work concepts
20. `work_sources` - Work sources
21. `work_keywords` - Work keywords
22. `work_funders` - Work funding
23. `citations_by_year` - Citation counts by year
24. `referenced_works` - Citation graph (work A cites work B)
25. `related_works` - Related works

### Other Tables (6 tables)
26. `apc` - Article processing charges
27. `search_metadata` - Search metadata
28. `search_index` - Search index
29. `author_name_variants` - Author name variations
30. `work_identifiers` - Work alternative IDs
31. `funders_identifiers` - Funder alternative IDs

---

## Expected Results

### Test Run (--limit 1000)
```
Topics:                    1,000
Topic hierarchy:           3,000
Concepts:                  1,000
Publishers:                1,000
Funders:                   1,000
Sources:                   1,000
Institutions:              1,000
Authors:                  15,000 (15 files × 1,000)
Author relationships:    556,368
Works:                    34,000 (34 files × 1,000)
Work relationships:    2,249,742
─────────────────────────────────
TOTAL:                ~2.8M records
Time:                      ~1 min
```

### Production Run (Full Dataset)
```
Topics:                    ~4,500
Concepts:                 ~65,000
Publishers:               ~10,000
Funders:                  ~32,000
Sources:                 ~260,000
Institutions:            ~117,000
Authors:              ~110,000,000
Author relationships: ~300,000,000
Works:                ~250,000,000
Work relationships: ~1,500,000,000
─────────────────────────────────
TOTAL:              ~2,000,000,000 records
Time:                    2-3 days
```

---

## Troubleshooting

### Common Issues

#### 1. Out of Memory
**Symptom:** Python process killed or memory errors

**Solution:** The parsers use streaming and should handle large files. If issues persist:
- Reduce batch size in `../config.py`: `BATCH_SIZE = 25000`
- Ensure sufficient swap space on system

#### 2. Database Connection Timeout
**Symptom:** `connection to server ... lost`

**Solution:**
- Check PostgreSQL is running: `pg_isready -h 192.168.1.100 -p 55432`
- Increase PostgreSQL connection timeout
- Check network connectivity

#### 3. Date Format Errors
**Symptom:** `date/time field value out of range`

**Solution:** Already fixed in `parse_authors_v2.py` (ensures 4-digit years)

#### 4. Disk Space Issues
**Symptom:** `No space left on device`

**Solution:**
- Check available space: `df -h`
- The database will grow to ~500GB-1TB for full dataset
- Ensure PostgreSQL data directory has sufficient space

#### 5. Parser Fails Mid-Run
**Symptom:** Parser exits with error code

**Solution:**
- Check logs in `logs/parse_<entity>_errors.log`
- Fix the issue
- Resume: `python3 orchestrator.py --resume`

### Performance Optimization

If parsing is slower than expected:

1. **Check disk I/O:**
   ```bash
   iostat -x 5
   ```

2. **Monitor database performance:**
   ```sql
   SELECT * FROM pg_stat_database WHERE datname='oadb2';
   ```

3. **Adjust PostgreSQL settings** (postgresql.conf):
   ```
   shared_buffers = 8GB
   work_mem = 256MB
   maintenance_work_mem = 2GB
   effective_cache_size = 24GB
   ```

4. **Use unlogged tables** (faster but no crash recovery):
   In `../config.py`: `USE_UNLOGGED_TABLES = True`

---

## Running Individual Parsers

You can run parsers individually for testing or specific updates:

```bash
# Topics
python3 parse_topics_v2.py --input-file /path/to/topics_folder/part_000.gz --limit 1000

# Authors (processes all files in directory)
python3 parse_authors_v2.py --input-file /path/to/authors_folder/part_000.gz

# Works
python3 parse_works_v2.py --input-file /path/to/works_folder/part_000.gz --limit 100
```

**Note:** Individual parsers only process a single file. Use the orchestrator to process all files in a directory.

---

## After Parsing Completes

### 1. Add Constraints (Optional)

After loading all data, you can add primary keys and foreign keys for data integrity:

```bash
cd ../02_postgres_setup
python3 oadb2_add_constraints.py
```

**Warning:** This will take several hours on the full dataset.

### 2. Create Indexes

For better query performance:

```bash
python3 oadb2_create_indexes.py
```

### 3. Validate Data

Check data integrity:

```bash
python3 oadb2_validation.py
```

### 4. Analyze Database

Generate statistics for query optimizer:

```sql
ANALYZE;
```

---

## Performance Metrics

Based on testing with largest snapshot folders:

| Entity | Files | Records | Time | Throughput |
|--------|-------|---------|------|------------|
| Topics | 1 | 4,000 | 0.3s | 20,000/sec |
| Concepts | 1 | 1,000 | 0.4s | 3,600/sec |
| Publishers | 1 | 1,000 | 0.2s | 9,800/sec |
| Funders | 1 | 1,000 | 0.2s | 7,800/sec |
| Sources | 1 | 1,503 | 0.4s | 4,700/sec |
| Institutions | 1 | 2,592 | 0.6s | 5,800/sec |
| **Authors** | **15** | **556,368** | **7.7s** | **100,000/sec** |
| **Works** | **34** | **2,249,742** | **34s** | **120,000/sec** |

**Overall:** ~70,000-120,000 records/second

---

## Technical Details

### COPY vs INSERT Performance

The parsers use PostgreSQL COPY instead of INSERT for bulk loading:

```
INSERT:            ~1,000 records/sec
execute_values:   ~10,000 records/sec
COPY:            ~100,000 records/sec  ✅ (100x faster)
```

### Batch Size

Default batch size is 50,000 records. Adjust in `../config.py`:

```python
BATCH_SIZE = 50000  # Increase for more memory, decrease for slower systems
```

### Multi-File Processing

The orchestrator automatically processes all `part_*.gz` files in each directory:
- Discovers files using glob pattern: `part_*.gz`
- Processes in sorted order: `part_000.gz`, `part_001.gz`, etc.
- Logs progress for each file

### State Management

The orchestrator saves state in `orchestrator_state.json`:

```json
{
  "topics": {"status": "complete", "records": 4500, "errors": 0},
  "authors": {"status": "running", "records": 5000000, "errors": 0},
  "works": {"status": "pending", "records": 0, "errors": 0}
}
```

Statuses: `pending`, `running`, `complete`, `failed`

---

## Support and Issues

For issues or questions:

1. Check logs in `logs/` directory
2. Review this README
3. Check database connection and available disk space
4. Verify snapshot files are accessible

---

## Quick Reference Commands

```bash
# Setup
export ADMIN_PASSWORD='your_password'

# Test run (small sample)
python3 orchestrator.py --start --limit 1000

# Production run (full dataset)
python3 orchestrator.py --start

# Resume after interruption
python3 orchestrator.py --resume

# Check status
python3 orchestrator.py --status

# Reset state
python3 orchestrator.py --reset

# Monitor logs
tail -f logs/orchestrator.log

# Check database
python3 check_db_counts.py
```

---

**Last Updated:** November 2025
**Version:** 2.0 (COPY-based high-performance parsers)
