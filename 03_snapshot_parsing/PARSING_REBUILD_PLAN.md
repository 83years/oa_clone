# High-Performance Parsing Pipeline Rebuild Plan

## Core Design Principles
- **Speed First**: Use PostgreSQL COPY (not INSERT) - bypass all checks
- **One Parser Per Entity**: Each .gz file → dedicated parser → its tables
- **Extract Once, Write Many**: Parse JSON once, write to multiple tables in single pass
- **Smart Orchestration**: Track state, log issues, provide real-time diagnostics
- **ID Propagation**: Extract primary/foreign key IDs during parse, distribute to all related tables

---

## Phase 1: Database Schema Optimization (20 min)

### 1. Create `02_postgres_setup/oadb2_schema_fast_load.py`
- Remove ALL constraints (PKs, FKs, UNIQUE, CHECK)
- Keep only: column names, data types, NOT NULL where critical
- No triggers, no defaults (except system timestamps)
- Result: Pure data container optimized for COPY

### 2. Add helper: `reset_database.py`
- Drop all tables
- Recreate schema
- Reset orchestrator state
- One-command clean slate

---

## Phase 2: Parser Architecture (1 hr)

### 3. Create base class: `parsers/base_parser.py`
```python
BaseParser:
  - read_gz_stream(file, line_limit=None) → yields JSON
  - extract_entities() → {main_table: [...], related_table1: [...]}
  - write_with_copy(table, data) → bulk COPY
  - validate_sample(n=100) → API check
  - report_stats() → records parsed, time, speed
```

### 4. Create `parsers/config.py`
- DB connection settings
- File paths to each .gz file
- Table schemas (column order for COPY)
- Progress intervals
- Error logging paths

---

## Phase 3: Individual Parsers (3 hrs)

### 5. `parsers/parse_topics.py`
- **Input**: `topics_data.gz`
- **Outputs**:
  - `topics` table (main)
  - `topic_hierarchy` table (domain→field→subfield→topic)
- **ID extraction**: topic_id, domain_id, field_id, subfield_id
- **Method**: Single pass, build both CSV buffers, COPY both

### 6. `parsers/parse_concepts.py`
- **Input**: `concepts_data.gz`
- **Outputs**: `concepts` table only
- **ID extraction**: concept_id
- **Simple**: Flat structure, no relationships

### 7. `parsers/parse_publishers.py`
- **Input**: `publishers_data.gz`
- **Outputs**: `publishers` table only
- **ID extraction**: publisher_id

### 8. `parsers/parse_funders.py`
- **Input**: `funders_data.gz`
- **Outputs**: `funders` table only
- **ID extraction**: funder_id

### 9. `parsers/parse_sources.py`
- **Input**: `sources_data.gz`
- **Outputs**:
  - `sources` table (main)
  - `source_publishers` table (relationships)
- **ID extraction**: source_id, publisher_id (from nested object)
- **Method**: Parse once, extract publisher relationship, COPY both tables

### 10. `parsers/parse_institutions.py`
- **Input**: `institutions_data.gz`
- **Outputs**:
  - `institutions` table (main)
  - `institution_geo` table (lat/long/city)
  - `institution_hierarchy` table (lineage array → parent/child pairs)
- **ID extraction**: institution_id, parent IDs from lineage array
- **Method**: Parse once, extract geo + hierarchy relationships, COPY three tables

### 11. `parsers/parse_authors.py` (NEW - CRITICAL)
- **Input**: `author_data.gz` (~110M records)
- **Outputs**:
  - `authors` table (main) ← **author_id as future PK**
  - `author_topics` table (from topics array)
  - `author_concepts` table (from x_concepts array)
  - `author_institutions` table (from affiliations array)
  - `authors_works_by_year` table (from counts_by_year array)
- **ID extraction**:
  - author_id (propagate to ALL tables)
  - topic_ids, concept_ids, institution_ids (from nested objects)
  - Extract current_affiliation_id for authors.current_affiliation_id column
- **Method**:
  - Single pass through .gz
  - Build 5 separate CSV buffers in memory (flush every 50k records)
  - COPY all 5 tables in batches
- **Speed target**: ~10k authors/sec = 3 hrs for 110M

### 12. `parsers/parse_works.py` (REBUILD)
- **Input**: `works_data.gz` (~250M records)
- **Outputs**:
  - `works` table (main) ← **work_id as future PK**
  - `work_topics` table (from topics array)
  - `work_concepts` table (from concepts array)
  - `work_sources` table (from locations/primary_location)
  - `work_keywords` table (from keywords array)
  - `work_funders` table (from grants array)
  - `citations_by_year` table (from counts_by_year array)
  - `referenced_works` table (from referenced_works array)
  - `related_works` table (from related_works array)
- **ID extraction**:
  - work_id (propagate to ALL relationship tables)
  - topic_ids, concept_ids, source_ids, funder_ids from nested arrays
  - referenced_work_ids, related_work_ids from arrays
- **Special handling**:
  - Extract **author_ids** from authorships array but DON'T write authorship table yet
  - Store authorship data separately for Phase 4
- **Method**:
  - Single pass, build 9 CSV buffers
  - Flush and COPY every 50k works
- **Speed target**: ~5k works/sec = 14 hrs for 250M

### 13. `parsers/parse_authorship.py` (NEW - POST-PROCESSING)
- **Input**: Re-read `works_data.gz` OR read from works table
- **Output**: `authorship` table ONLY
- **ID extraction**:
  - work_id (from work)
  - author_id (from authorships array) ← **Requires author_id as FK**
  - institution_id (from authorships.institutions array)
- **Method**:
  - Lightweight parse: only extract id + authorships array
  - One author = one row in authorship table
  - Estimated ~750M authorship records (avg 3 authors per work)
- **Why separate**: Can run AFTER authors table complete to ensure author_ids exist
- **Speed target**: ~15k authorships/sec = 14 hrs for 750M

---

## Phase 4: Smart Orchestrator (2 hrs)

### 14. `parsers/orchestrator.py`

#### Core Features:

**State tracking**: JSON file stores progress for each parser
```json
{
  "topics": {
    "status": "complete",
    "records": 4516,
    "started": "2025-01-15T10:23:11",
    "completed": "2025-01-15T10:23:45",
    "errors": 0
  },
  "authors": {
    "status": "running",
    "records": 45000000,
    "started": "2025-01-15T11:00:00",
    "progress_pct": 41,
    "errors": 12
  },
  "works": {
    "status": "pending",
    "records": 0
  }
}
```

**Dependency management**:
- Phase 1 (parallel): topics, concepts, publishers, funders
- Phase 2 (parallel): sources, institutions (depend on Phase 1)
- Phase 3 (sequential): authors (large, depends on institutions)
- Phase 4 (sequential): works (huge, depends on authors)
- Phase 5 (sequential): authorship (huge, depends on authors + works)

**Real-time monitoring**:
- Live progress: "Authors: 45.2M / ~110M (41%) | 9,823 records/sec | ETA: 1h 52m"
- Error tracking: Log every malformed JSON, missing field, data overflow
- Performance metrics: Records/sec, MB/sec, DB write speed

**Error handling**:
- Malformed JSON → log line number, skip record
- Missing required field → log record ID, skip or use NULL
- Data overflow (column too small) → log field + value, truncate with warning
- Connection loss → save state, resume from last batch

**Logging**:
- `logs/orchestrator.log` - high-level progress
- `logs/parse_authors_errors.log` - detailed errors per parser
- `logs/parse_works_errors.log` - etc.
- `logs/performance.csv` - timestamp, parser, records/sec, memory_mb

**CLI Interface**:
- `python orchestrator.py --start` - begin from scratch
- `python orchestrator.py --resume` - continue from saved state
- `python orchestrator.py --status` - show current progress
- `python orchestrator.py --validate` - run API validation on sample
- `python orchestrator.py --reset` - clear state, drop tables

**Validation**:
- After each parser: sample 100 random IDs → API query → compare fields
- Report accuracy: "Authors: 97.2% field match (3 API errors, 2 mismatches)"
- Flag suspicious patterns: "82% of works missing abstracts"

---

## Phase 5: Testing Framework (1 hr)

### 15. Add line limits for testing
- Each parser accepts `--limit 100000` flag
- Orchestrator test mode: `python orchestrator.py --test --limit 100000`
- Quick validation: ~800k records total in 10-15 minutes
- Verify table relationships, ID propagation, no crashes

### 16. Create `validate_schema.py`
- Check all tables exist
- Check column counts match schema
- Check for NULL values in critical ID columns
- Generate summary: "32 tables, 847,291 records, 0 critical errors"

---

## Phase 6: Execution Plan

### Test Run (15 min):
1. Reset database
2. Run orchestrator with 100k line limit
3. Validate: all tables populated, IDs present, no crashes
4. Fix any issues

### Production Run (estimated 2-3 days for 2TB):
1. Reset database
2. Run orchestrator unlimited
3. Monitor logs in real-time
4. Handle errors as they occur
5. Validate samples periodically

### Post-Load (optional, later):
1. Add primary keys (fast, just creates indexes)
2. Add foreign keys (slow, validates ~1B relationships)
3. Add indexes on common query columns
4. VACUUM ANALYZE

---

## Key Performance Optimizations

1. **COPY vs INSERT**: 10-100x faster
2. **Batch size**: 50,000 records per COPY (balance memory vs speed)
3. **Unlogged tables**: Optional flag to disable WAL during load
4. **Parallel parsing**: Phase 1 parsers run simultaneously (4 processes)
5. **Streaming**: Never load entire file in memory, process line-by-line
6. **Minimal validation**: Parse JSON, extract fields, write - no business logic

---

## Deliverables

1. **Schema**: `oadb2_schema_fast_load.py` (constraint-free)
2. **Base**: `parsers/base_parser.py`, `parsers/config.py`
3. **8 Parsers**: topics, concepts, publishers, funders, sources, institutions, authors, works
4. **Post-processor**: `parsers/parse_authorship.py`
5. **Orchestrator**: `parsers/orchestrator.py` (state tracking, logging, validation)
6. **Utilities**: `reset_database.py`, `validate_schema.py`
7. **Documentation**: README with usage examples

---

## Expected Test Results (100k line limit)

- topics: ~4,500 records
- concepts: ~65,000 records
- publishers: ~10,000 records
- funders: ~32,000 records
- sources: ~100,000 records (capped)
- institutions: ~100,000 records (capped)
- authors: ~100,000 records (capped)
- works: ~100,000 records (capped)
- **Populated relationship tables**: author_topics, author_concepts, work_topics, work_concepts, etc.
- **Empty junction table**: authorship (built in separate pass)

Total: ~500k records across 32 tables in ~15 minutes

---

## .GZ File to Tables Mapping

### Available .gz Files and Their Target Tables:

| .gz File | Main Table | Related Tables | Parser |
|----------|------------|----------------|--------|
| concepts_data.gz | concepts | - | parse_concepts.py |
| funders_data.gz | funders | - | parse_funders.py |
| publishers_data.gz | publishers | - | parse_publishers.py |
| topics_data.gz | topics | topic_hierarchy | parse_topics.py |
| sources_data.gz | sources | source_publishers | parse_sources.py |
| institutions_data.gz | institutions | institution_geo, institution_hierarchy | parse_institutions.py |
| author_data.gz | authors | author_topics, author_concepts, author_institutions, authors_works_by_year | parse_authors.py (NEW) |
| works_data.gz | works | work_topics, work_concepts, work_sources, work_keywords, work_funders, citations_by_year, referenced_works, related_works | parse_works.py (REBUILD) |
| works_data.gz | authorship | - | parse_authorship.py (NEW, separate pass) |

---

## Primary Key and Foreign Key Strategy

### Primary Keys (added POST-load):
- author_id (authors table)
- work_id (works table)
- topic_id (topics table)
- concept_id (concepts table)
- institution_id (institutions table)
- source_id (sources table)
- publisher_id (publishers table)
- funder_id (funders table)

### Foreign Keys (extracted during parse, enforced POST-load):
- authors.current_affiliation_id → institutions.institution_id
- authorship.author_id → authors.author_id
- authorship.work_id → works.work_id
- authorship.institution_id → institutions.institution_id
- author_topics.author_id → authors.author_id
- author_topics.topic_id → topics.topic_id
- author_concepts.author_id → authors.author_id
- author_concepts.concept_id → concepts.concept_id
- work_topics.work_id → works.work_id
- work_topics.topic_id → topics.topic_id
- work_concepts.work_id → works.work_id
- work_concepts.concept_id → concepts.concept_id
- (and many more...)

### ID Extraction Strategy:
All parsers extract IDs during the JSON parse and propagate them to related tables in the same pass. IDs are stored as VARCHAR(255) with the OpenAlex URL prefix removed (e.g., "A2208157607" instead of "https://openalex.org/A2208157607").
