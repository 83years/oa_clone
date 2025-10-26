# Phase 2 Quick Reference Guide

## Overview

Phase 2 builds the joining tables that connect works to authors, topics, concepts, sources, citations, and funders.

**Strategy:** Extract relationships to CSV → Bulk COPY → Clean orphans → Add FK constraints → Create indexes

---

## File Structure

```
03_snapshot_parsing/
├── parse_works_relationships.py    # Extract relationships to CSV
├── load_relationships.py           # Load CSV into database
├── orchestrator_relationships.py   # Coordinate everything
├── verify_works_complete.py        # Pre-Phase 2 verification
├── verify_entities_complete.py     # Pre-Phase 2 verification
└── PHASE_2_PLAN.md                # Full detailed plan
```

**CSV Output Directory:** `/Volumes/OA_snapshot/works_tables/`

---

## Pre-Flight Checks

Before starting Phase 2, verify Phase 1 is complete:

```bash
cd /Users/lucas/Documents/openalex_database/python/OA_clone/03_snapshot_parsing

# Verify works table
python3 verify_works_complete.py

# Verify entity tables (authors, topics, concepts, etc.)
python3 verify_entities_complete.py
```

Both should return **✅ READY FOR PHASE 2**

---

## Quick Start (Recommended)

Use the orchestrator to run everything automatically:

```bash
# Start Phase 2 (or resume if interrupted)
python3 orchestrator_relationships.py

# Start fresh (clear previous state)
python3 orchestrator_relationships.py --no-resume
```

The orchestrator will:
1. Extract all relationships from works files to CSV
2. Load each table sequentially
3. Handle FK violations
4. Generate reports

**Estimated time:** 20-38 hours

---

## Manual Mode (Advanced)

For more control, run each phase separately:

### Phase 2a: Extract Relationships

Extract from a single works file:
```bash
python3 parse_works_relationships.py \
  --input-file /Volumes/OA_snapshot/03OCT2025/openalex-snapshot/data/works/updated_date=2024-10-13/part_000.gz \
  --output-dir /Volumes/OA_snapshot/works_tables
```

Or process all files with a loop:
```bash
for file in /Volumes/OA_snapshot/03OCT2025/openalex-snapshot/data/works/updated_date=*/part_*.gz; do
  python3 parse_works_relationships.py --input-file "$file"
done
```

**Output:** CSV files in `/Volumes/OA_snapshot/works_tables/`
- `authorship_part_000.csv`
- `work_topics_part_000.csv`
- etc.

### Phase 2b: Load Tables

Load a single table:
```bash
python3 load_relationships.py --table authorship
```

Load all tables (sequential):
```bash
for table in authorship work_topics work_concepts work_sources \
             citations_by_year referenced_works work_funders \
             alternate_ids work_keywords related_works apc; do
  python3 load_relationships.py --table $table
done
```

**Each load process:**
1. Creates table (no FK constraints)
2. COPY CSV files (bulk load)
3. Analyzes FK violations
4. Deletes orphaned records
5. Adds FK constraints
6. Creates indexes
7. Generates report

---

## Tables & Loading Order

Tables are loaded sequentially in this order:

| # | Table | Priority | Dependencies | Est. Rows |
|---|-------|----------|--------------|-----------|
| 1 | `authorship` | CRITICAL | works + authors | ~1B |
| 2 | `work_topics` | CRITICAL | works + topics | ~750M |
| 3 | `work_concepts` | HIGH | works + concepts | ~2B |
| 4 | `work_sources` | HIGH | works + sources | ~250M |
| 5 | `citations_by_year` | HIGH | works | ~500M |
| 6 | `referenced_works` | HIGH | works | ~2.5B |
| 7 | `work_funders` | MEDIUM | works + funders | ~50M |
| 8 | `alternate_ids` | MEDIUM | works | ~400M |
| 9 | `work_keywords` | MEDIUM | works | ~300M |
| 10 | `related_works` | LOW | works | ~2.5B |
| 11 | `apc` | LOW | works | ~10M |

---

## FK Violation Handling

**Default Threshold:** <1% of records

**What happens:**
1. Load all CSV data (no validation)
2. Count FK violations (orphaned references)
3. If violations < 1%: Auto-clean
4. If violations > 1%: Ask user confirmation
5. Delete orphaned records
6. Add FK constraints (will succeed because orphans are gone)

**Common orphans:**
- Authors not in authors table (~expected)
- Sources not in sources table (~expected)
- Funders not in funders table (~expected)
- Referenced works not in works table (~expected - external refs)

**Reports saved to:**
- `{table_name}_load_report.json` - Per-table details
- `phase2_final_report.json` - Overall summary

---

## Monitoring Progress

### Orchestrator State

State is saved in `phase2_state.json`:
```json
{
  "phase": "extraction_in_progress",
  "extraction": {
    "completed_files": ["..."],
    "failed_files": []
  },
  "loading": {
    "completed_tables": ["authorship", "work_topics"],
    "failed_tables": []
  }
}
```

### Logs

Logs are saved in `logs/`:
- `phase2_orchestrator_YYYYMMDD_HHMMSS.log` - Main orchestrator log
- `relationships_extractor_YYYYMMDD_HHMMSS.log` - Per-file extraction logs

### Real-time Progress

Watch the orchestrator log in real-time:
```bash
tail -f logs/phase2_orchestrator_*.log | grep -E "SUCCESS|FAILED|Loading"
```

---

## Resume After Interruption

Phase 2 is fully resumable. If interrupted (Ctrl+C, power loss, etc.):

```bash
# Resume where you left off
python3 orchestrator_relationships.py
```

State is saved after each:
- Works file extracted
- Table loaded

**No data loss** - all source files remain intact.

---

## Troubleshooting

### Problem: FK violations exceed 1%

**Cause:** Entity tables (authors, topics, etc.) may be incomplete

**Solution:**
```bash
# Verify entity tables
python3 verify_entities_complete.py

# If missing entities, complete them first
# Then retry table load
python3 load_relationships.py --table authorship
```

### Problem: Out of disk space

**Cause:** CSV files are large (~200-500GB total)

**Solution:**
```bash
# Check space
df -h /Volumes/OA_snapshot

# Delete CSV files after each table loads
rm /Volumes/OA_snapshot/works_tables/authorship_*.csv

# Or extract and load one table at a time (slower but less space)
```

### Problem: Table load times out

**Cause:** Very large tables (work_concepts, referenced_works)

**Solution:**
```bash
# Increase timeout in load_relationships.py (line ~XXX)
# Or split CSV files into smaller chunks
```

### Problem: Extraction fails on specific file

**Cause:** Corrupted .gz file or malformed JSON

**Solution:**
```bash
# Check the specific file
gunzip -t /path/to/file.gz

# If corrupted, download again or skip
# Orchestrator tracks failed files for retry
```

---

## Cleanup

After Phase 2 completes successfully:

```bash
# Optional: Delete CSV files to save space
rm -rf /Volumes/OA_snapshot/works_tables/*.csv

# Keep reports
ls *_report.json
```

---

## Success Criteria

Phase 2 is complete when:

- [ ] All works files extracted to CSV
- [ ] All 11 tables loaded
- [ ] FK constraints added to all tables
- [ ] Indexes created
- [ ] FK violation rate < 1% for all tables
- [ ] `phase2_final_report.json` shows `"phase": "loading_complete"`

---

## Next Steps After Phase 2

Once Phase 2 completes:

1. **Verify joining tables:**
   ```bash
   # Count records
   psql -h 192.168.1.100 -p 55432 -U admin -d OADB -c "
   SELECT 'authorship' as table, COUNT(*) FROM authorship
   UNION ALL SELECT 'work_topics', COUNT(*) FROM work_topics;
   "
   ```

2. **Test queries:**
   ```sql
   -- Find an author's works
   SELECT w.title, w.publication_year
   FROM works w
   JOIN authorship a ON w.work_id = a.work_id
   WHERE a.author_id = 'A1234567890';
   ```

3. **Proceed to Phase 3:** Author profile building (step 04)

---

## Quick Commands Cheat Sheet

```bash
# Pre-check
python3 verify_works_complete.py && python3 verify_entities_complete.py

# Run Phase 2 (full automation)
python3 orchestrator_relationships.py

# Run Phase 2 fresh
python3 orchestrator_relationships.py --no-resume

# Extract single file (manual)
python3 parse_works_relationships.py --input-file FILE.gz

# Load single table (manual)
python3 load_relationships.py --table authorship

# Check progress
tail -f logs/phase2_orchestrator_*.log

# View state
cat phase2_state.json | python3 -m json.tool

# View final report
cat phase2_final_report.json | python3 -m json.tool
```

---

## Support Files

- `PHASE_2_PLAN.md` - Comprehensive 400+ line plan
- `WORKS_TABLE_UPDATES.md` - Phase 1 completion summary
- `phase2_state.json` - Runtime state (auto-generated)
- `phase2_final_report.json` - Final report (auto-generated)
- `*_load_report.json` - Per-table reports (auto-generated)
