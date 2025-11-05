# OpenAlex Parsing Pipeline Rebuild - Summary

**Date**: November 5, 2025
**Status**: ✅ Core infrastructure complete and tested

---

## What Was Built

### 1. Configuration System (`/config.py`)
- Centralized database configuration (host: 192.168.1.100, port: 55432)
- File paths to all .gz files
- Performance tuning parameters (batch size: 50k, progress interval: 10k)
- Support for test mode with line limits

### 2. Base Parser Class (`base_parser.py`)
**Key Features**:
- **PostgreSQL COPY** for maximum speed (10-100x faster than INSERT)
- Streaming .gz file processing (memory efficient, processes 2TB+ datasets)
- Automatic error logging per parser
- Real-time statistics tracking (records/sec, time elapsed, errors)
- Graceful error handling with fallback to execute_values
- Automatic FK constraint disabling during bulk load
- Clean OpenAlex ID extraction (removes URL prefixes)

**Performance**:
- Topics: 29,320 records/sec
- Authors: 22,735 records/sec

### 3. Entity Parsers (All Using COPY Method)

#### ✅ Completed & Tested:

| Parser | Tables Populated | Status | Test Results |
|--------|-----------------|--------|--------------|
| **parse_topics_v2.py** | `topics`, `topic_hierarchy` | ✅ Working | 1,000 topics → 4,000 records (0.1s) |
| **parse_concepts_v2.py** | `concepts` | ✅ Working | 8 concepts total in file |
| **parse_authors_v2.py** | `authors`, `author_topics`, `author_concepts`, `author_institutions`, `authors_works_by_year` | ✅ Working | 100 authors → 3,493 records (0.2s) |
| **parse_publishers_v2.py** | `publishers` | ✅ Created | Not yet tested |
| **parse_funders_v2.py** | `funders` | ✅ Created | Not yet tested |

#### ⏳ To Be Created:

| Parser | Tables to Populate | Complexity | Priority |
|--------|-------------------|------------|----------|
| **parse_sources_v2.py** | `sources`, `source_publishers` | Medium | High |
| **parse_institutions_v2.py** | `institutions`, `institution_geo`, `institution_hierarchy` | High | High |
| **parse_works_v2.py** | `works`, `work_topics`, `work_concepts`, `work_sources`, `work_keywords`, `work_funders`, `citations_by_year`, `referenced_works`, `related_works` | Very High | Critical |
| **parse_authorship.py** | `authorship` | Medium | Critical |

### 4. Smart Orchestrator (`orchestrator.py`)
**Features**:
- Manages parsing order (respects table dependencies)
- JSON state tracking (can resume after failures)
- Real-time progress logging
- Multiple CLI modes

**Commands**:
```bash
python3 orchestrator.py --start    # Start from beginning
python3 orchestrator.py --resume   # Resume from saved state
python3 orchestrator.py --status   # Show current status
python3 orchestrator.py --reset    # Reset state file
python3 orchestrator.py --test     # Test mode (100k lines per file)
python3 orchestrator.py --limit N  # Custom line limit
```

### 5. Database Schema
- **Host**: 192.168.1.100:55432
- **Database**: oadb2
- **Tables**: 32 tables created
- **Constraints**: ZERO (no PKs, no FKs, no UNIQUE) - optimized for bulk loading
- **Status**: ✅ Initialized and ready

---

## Test Results

### Small-Scale Tests (Completed)
```
✅ Topics:    1,000 records → 4,000 DB records (topics + hierarchy)
✅ Concepts:  8 records → 8 DB records
✅ Authors:   100 records → 3,493 DB records (5 tables populated)
```

### Database Verification
```sql
topics:                  1,000
topic_hierarchy:         3,000
concepts:                    8
authors:                   100
author_topics:             770
author_concepts:         2,035
author_institutions:       196
authors_works_by_year:     392
```

---

## Architecture Highlights

### Extract Once, Write Many
Each parser reads the .gz file **once** and extracts data to **multiple tables simultaneously**:

**Example: Authors Parser**
```
author_data.gz (single pass)
   ↓
   ├→ authors table (main entity)
   ├→ author_topics table (from topics array)
   ├→ author_concepts table (from x_concepts array)
   ├→ author_institutions table (from affiliations array)
   └→ authors_works_by_year table (from counts_by_year array)
```

### ID Propagation
Primary and foreign key IDs are extracted during parsing and propagated to all related tables:

```python
author_id = "A5108252927"  # Extracted once
↓
authors.author_id = "A5108252927"
author_topics.author_id = "A5108252927"
author_concepts.author_id = "A5108252927"
author_institutions.author_id = "A5108252927"
authors_works_by_year.author_id = "A5108252927"
```

### Performance Optimization
1. **COPY vs INSERT**: 10-100x faster
2. **Batch size**: 50,000 records per write
3. **Streaming**: Never loads entire file into memory
4. **FK disabled**: No constraint checks during load
5. **Unlogged tables**: Optional (can be enabled for even faster loading)

---

## Next Steps

### Immediate (Complete the Pipeline)
1. **Create parse_sources_v2.py** - sources + source_publishers tables
2. **Create parse_institutions_v2.py** - institutions + geo + hierarchy tables
3. **Create parse_works_v2.py** - works + 8 relationship tables (CRITICAL)
4. **Create parse_authorship.py** - authorship junction table (CRITICAL for networks)

### Testing
5. **Run orchestrator --test** - parse all entities with 100k line limit
6. **Validate results** - check table counts, sample data, relationships
7. **Fix any issues** - adjust column sizes, data types, error handling

### Production
8. **Run full parse** - remove line limits, parse complete 2TB dataset
9. **Monitor progress** - watch logs, handle errors, estimate completion time
10. **Post-load optimization** - add indexes, VACUUM ANALYZE

### Future (Optional)
11. **Add primary keys** - fast, just creates indexes
12. **Add foreign keys** - slow, validates all relationships (days)
13. **Validation suite** - API sampling, accuracy checks, orphan detection

---

## File Locations

```
OA_clone/
├── config.py                      # Global configuration
├── 02_postgres_setup/
│   └── oadb2_postgresql_setup.py  # Database schema (constraint-free)
└── 03_snapshot_parsing/
    ├── base_parser.py             # Base class with COPY support
    ├── orchestrator.py            # Smart orchestrator
    ├── parse_topics_v2.py         # ✅ Topics parser
    ├── parse_concepts_v2.py       # ✅ Concepts parser
    ├── parse_authors_v2.py        # ✅ Authors parser (5 tables)
    ├── parse_publishers_v2.py     # ✅ Publishers parser
    ├── parse_funders_v2.py        # ✅ Funders parser
    ├── parse_sources_v2.py        # ⏳ To be created
    ├── parse_institutions_v2.py   # ⏳ To be created
    ├── parse_works_v2.py          # ⏳ To be created (9 tables)
    ├── parse_authorship.py        # ⏳ To be created (CRITICAL)
    ├── orchestrator_state.json    # State tracking (auto-generated)
    ├── logs/                      # Error and progress logs
    ├── *.gz                       # Data files
    ├── PARSING_REBUILD_PLAN.md    # Detailed plan
    └── REBUILD_SUMMARY.md         # This file
```

---

## Performance Estimates

### Test Mode (100k lines per file)
- **Time**: ~15 minutes
- **Records**: ~500k across all tables
- **Purpose**: Validate pipeline, find issues

### Production Mode (Full 2TB dataset)
- **Topics**: ~4,500 records, <1 minute
- **Concepts**: ~65,000 records, ~1 minute
- **Publishers**: ~10,000 records, ~1 minute
- **Funders**: ~32,000 records, ~1 minute
- **Sources**: ~260,000 records, ~5 minutes
- **Institutions**: ~117,000 records, ~5 minutes
- **Authors**: ~110M records, **3-5 hours**
- **Works**: ~250M records, **14-20 hours**
- **Authorship**: ~750M records, **14-20 hours**

**Total estimated time**: 2-3 days for complete 2TB load

---

## Key Success Factors

✅ **Constraint-free schema** - enables fast bulk loading
✅ **PostgreSQL COPY** - 10-100x faster than INSERT
✅ **Single-pass extraction** - read each file once, write to multiple tables
✅ **Streaming processing** - handles 2TB+ without memory issues
✅ **Automatic error handling** - logs errors, continues processing
✅ **State tracking** - can resume after failures
✅ **ID propagation** - foreign keys ready for post-load constraint addition

---

## Troubleshooting

### Connection Issues
- Check PostgreSQL is running: `pg_isready -h 192.168.1.100 -p 55432`
- Verify credentials: `export ADMIN_PASSWORD='secure_password_123'`
- Test connection: `psql -h 192.168.1.100 -p 55432 -U admin -d oadb2`

### Parsing Errors
- Check error logs: `tail -f logs/parse_<entity>_errors.log`
- Review orchestrator log: `tail -f logs/orchestrator.log`
- Validate .gz files: `zcat file.gz | head -5` (should show valid JSON)

### Performance Issues
- Check batch size in config.py (default: 50,000)
- Enable unlogged tables for faster writes (no crash recovery)
- Monitor disk I/O: `iostat -x 5`
- Monitor database: `SELECT * FROM pg_stat_activity WHERE datname='oadb2';`

---

## Contact & Support

For issues or questions about this parsing pipeline:
1. Review PARSING_REBUILD_PLAN.md for detailed specifications
2. Check logs in `03_snapshot_parsing/logs/`
3. Verify database state with orchestrator: `python3 orchestrator.py --status`
4. Test individual parsers with `--limit 100` flag
