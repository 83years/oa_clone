# Why We Don't Parse the Authors Snapshot

## Executive Summary

**Decision**: Build the authors table from works data instead of parsing the separate OpenAlex authors snapshot.

**Rationale**: The authors snapshot and works snapshot come from different time periods, causing an ~80% mismatch. By deriving author data from works, we achieve 100% consistency and capture all necessary fields for our research goals.

---

## The Problem: Temporal Snapshot Mismatch

### Initial Discovery
When parsing both authors and works snapshots, we found:
- **115 million authors** in authors table (from authors snapshot)
- **75 million unique authors** in authorship table (from works snapshot)
- **Only ~20% match** between the two tables

### Root Cause
OpenAlex snapshots are taken at different dates:
- Works snapshot: `updated_date=2022-02-01` (example)
- Authors snapshot: Different date, different coverage

This means:
- Authors in works might not exist in authors snapshot
- Authors in authors snapshot might have no works in our works data
- Author metadata (names, affiliations) may be out of sync

### Impact on Research
This mismatch blocked:
- **Phase 4**: Author profile building (missing 80% of authors)
- **Phase 10**: Gender hypothesis testing (can't infer gender without names)
- **Phase 11**: Geography hypothesis testing (can't track mobility)

---

## The Solution: Derive Authors from Works

### Why This Works

1. **100% Match Guarantee**
   - Every author_id in authorship table will have an entry in authors table
   - No orphaned authorships
   - No missing author metadata

2. **Complete Data Capture**
   - Works data contains author display names (`author.display_name`)
   - Works data contains raw author names (`authorship.raw_author_name`)
   - Works data contains geographic data (`authorship.countries[]`)
   - Works data contains institution affiliations with country codes

3. **Normalized Database Design**
   - New tables created for proper data organization:
     - `author_names`: Track name variations across publications
     - `authorship_countries`: Track geographic mobility
     - Enhanced `authorship`: Now includes author names directly
     - Enhanced `authorship_institutions`: Now includes country codes

---

## What We Capture from Works Data

### Table 1: Author Identity & Names
| Data Field | Source in Works | Captured In | Purpose |
|------------|-----------------|-------------|---------|
| Author ID | `authorship.author.id` | `authorship.author_id` | Unique identifier |
| Display Name | `authorship.author.display_name` | `authorship.author_display_name` | Normalized canonical name |
| Raw Author Name | `authorship.raw_author_name` | `authorship.raw_author_name` | Name as published in paper |
| Forename | Parsed from display_name | `author_names.forename` | Gender inference |
| Lastname | Parsed from display_name | `author_names.lastname` | Name analysis |

### Table 2: Author Geography
| Data Field | Source in Works | Captured In | Purpose |
|------------|-----------------|-------------|---------|
| Countries | `authorship.countries[]` | `authorship_countries` | Track author mobility |
| Institution Country | `authorship.institutions[].country_code` | `authorship_institutions.country_code` | Quick country lookup |
| Current Affiliation | Derived from latest work | `authors.current_affiliation_*` | Current location |

### Table 3: Author Productivity & Impact
| Data Field | Derived From | Captured In | Purpose |
|------------|--------------|-------------|---------|
| Works Count | `COUNT(authorship)` | `authors.works_count` | Productivity metric |
| Total Citations | `SUM(works.cited_by_count)` | `authors.cited_by_count` | Impact metric |
| Corresponding Count | `COUNT WHERE is_corresponding` | `authors.corresponding_authorships` | Seniority indicator |
| First Author Count | `COUNT WHERE author_position='first'` | Derived metric | Career stage |
| Last Author Count | `COUNT WHERE author_position='last'` | Derived metric | Seniority indicator |

### Table 4: Author Career Timeline
| Data Field | Derived From | Captured In | Purpose |
|------------|--------------|-------------|---------|
| First Publication Year | `MIN(publication_year)` | `authors.first_publication_year` | Career start |
| Last Publication Year | `MAX(publication_year)` | `authors.last_publication_year` | Current activity |
| Career Length | `MAX - MIN years` | `authors.career_length_years` | Experience |
| Is Current | `MAX year >= NOW() - 3` | `authors.current` | Active researcher |

---

## Database Changes Implemented

### 1. New Tables Created

#### `author_names`
**Purpose**: Track how author names appear across publications
```sql
CREATE TABLE author_names (
    author_id VARCHAR(255),
    work_id VARCHAR(255),
    raw_author_name TEXT,          -- Name as published
    display_name TEXT,              -- Canonical name from OpenAlex
    publication_year INTEGER,       -- When this name was used
    forename TEXT,                  -- Parsed first name
    lastname TEXT                   -- Parsed last name
);
```

**Why**:
- Gender inference needs forenames
- Track name changes over career (marriage, transliteration)
- Disambiguation support

#### `authorship_countries`
**Purpose**: Track which countries authors worked from on each publication
```sql
CREATE TABLE authorship_countries (
    work_id VARCHAR(255),
    author_id VARCHAR(255),
    country_code VARCHAR(10)       -- ISO 2-letter code
);
```

**Why**:
- Geography hypothesis testing (Phase 11)
- Track author mobility patterns
- International collaboration analysis

#### `work_locations`
**Purpose**: Detailed open access location data per work
```sql
CREATE TABLE work_locations (
    work_id VARCHAR(255),
    is_oa BOOLEAN,
    landing_page_url TEXT,
    source_id VARCHAR(255),
    provenance VARCHAR(100),
    is_primary BOOLEAN
);
```

**Why**:
- Detailed OA analysis by source
- Track different versions/locations of same work

### 2. Enhanced Existing Tables

#### `authorship` (2 new columns)
```sql
-- ADDED:
raw_author_name TEXT              -- Name as it appears in paper
author_display_name TEXT          -- Normalized name from OpenAlex
```

**Why**: Enable gender inference directly from authorship table

#### `authorship_institutions` (1 new column)
```sql
-- ADDED:
country_code VARCHAR(10)          -- Denormalized for performance
```

**Why**: Fast country lookups without joining to institutions table

#### `works` (3 new columns)
```sql
-- ADDED:
has_content_pdf BOOLEAN           -- Full-text availability
has_content_grobid_xml BOOLEAN    -- Structured full-text
topics_key BIGINT                 -- Link to topics
```

**Why**: Track full-text availability for later analysis

---

## Parser Changes: V2 → V3

### New File: `parse_works_v3.py`

**Key Enhancements**:

1. **Name Parsing**
   - Uses `nameparser` library to split display_name into forename/lastname
   - Handles various name formats (Western, Eastern, hyphenated)
   - Graceful fallback if parsing fails

2. **Author Names Capture**
   ```python
   # NEW in V3
   author_display_name = author.get('display_name')
   raw_author_name = authorship.get('raw_author_name')
   forename, lastname = self.parse_name(author_display_name)
   ```

3. **Geographic Data Capture**
   ```python
   # NEW in V3
   countries = authorship.get('countries', [])
   for country_code in countries:
       authorship_countries_batch.append({
           'work_id': work_id,
           'author_id': author_id,
           'country_code': country_code
       })
   ```

4. **Institution Country Denormalization**
   ```python
   # ENHANCED in V3
   inst_country_code = inst.get('country_code')
   authorship_institutions_batch.append({
       'work_id': work_id,
       'author_id': author_id,
       'institution_id': inst_id,
       'country_code': inst_country_code  # NEW
   })
   ```

5. **New Batching Logic**
   - Added batches for 3 new tables
   - Optimized batch sizes (50k for joining tables)
   - COPY method for all tables (fast bulk load)

---

## Building the Authors Table from Works

After parsing works with V3, build authors table using:
`04_author_profile_building/00_build_authors_from_works.py`

**SQL Strategy**:
```sql
WITH author_stats AS (
    SELECT
        author_id,
        COUNT(DISTINCT work_id) as works_count,
        SUM(cited_by_count) as total_citations,
        MIN(publication_year) as first_pub_year,
        MAX(publication_year) as last_pub_year,
        COUNT(CASE WHEN is_corresponding THEN 1 END) as corresponding_count
    FROM authorship
    JOIN works ON authorship.work_id = works.work_id
    GROUP BY author_id
)
-- Then join with latest institution, name, etc.
```

**Features Derived**:
- Identity (most common name)
- Productivity (works count, citations)
- Career timeline (first/last year, career length)
- Position patterns (first/last/corresponding frequencies)
- Geographic mobility (countries count, latest institution)
- Impact (most cited work, max citations)

---

## Benefits of This Approach

### 1. Data Consistency
✅ **100% match** between authorship and authors tables
✅ **No orphaned records** or missing data
✅ **Single source of truth** (works data)

### 2. Research Enablement
✅ **Gender analysis** now possible (have names)
✅ **Geography hypothesis** now testable (have countries)
✅ **Career modeling** fully supported (have timeline)

### 3. Database Efficiency
✅ **Normalized design** for complex queries
✅ **Denormalized country_code** for performance
✅ **No duplicate data** from mismatched snapshots

### 4. Future-Proof
✅ **Name variation tracking** for disambiguation
✅ **Geographic mobility** for collaboration patterns
✅ **OA location tracking** for policy analysis

---

## Trade-offs and Limitations

### What We Lost (Acceptably)
- ❌ **ORCID IDs**: Not in works data (can enrich via API later)
- ❌ **H-index**: Not in works data (can calculate if needed)
- ❌ **2yr mean citedness**: Not in works data (can calculate)

### What We Gained
- ✅ **Perfect consistency** with our works data
- ✅ **Name variations** across publications
- ✅ **Geographic tracking** at authorship level
- ✅ **No temporal mismatch** issues

### Mitigation Strategies
1. **ORCID enrichment**: Query API for high-priority authors only
2. **H-index calculation**: SQL query across authorship + citations
3. **Citation metrics**: Derive from works table as needed

---

## Performance Implications

### Storage Requirements
| Table | Estimated Rows | Storage Impact |
|-------|----------------|----------------|
| `author_names` | ~600M (1 per authorship) | ~15GB |
| `authorship_countries` | ~600M (avg 1 country/author) | ~10GB |
| `work_locations` | ~600M (multiple per work) | ~20GB |
| **Total New Storage** | | **~45GB** |

### Query Performance
✅ **Faster country queries**: Denormalized country_code in authorship_institutions
✅ **Efficient name lookups**: author_names indexed on author_id
⚠️ **More joins needed**: For ORCID (if added later via API)

---

## Migration Path

### Step 1: Update Database Schema
```bash
python 02_postgres_setup/orchestrator.py
```
Creates 35 tables (32 original + 3 new)

### Step 2: Parse Works with V3
```bash
python 03_snapshot_parsing/parse_works_v3.py --input-file <works.gz>
```
Populates all tables including new author data

### Step 3: Build Authors Table
```bash
python 04_author_profile_building/00_build_authors_from_works.py
```
Aggregates author data from works/authorship tables

### Step 4: Gender Inference
Use forenames from `author_names` table:
```sql
SELECT DISTINCT author_id, forename, country_code
FROM author_names
JOIN authorship_countries USING (author_id, work_id)
```

---

## Validation & Quality Checks

### After Parsing
1. **Count Check**: `SELECT COUNT(DISTINCT author_id) FROM authorship`
2. **Name Coverage**: `SELECT COUNT(*) FROM author_names WHERE forename IS NOT NULL`
3. **Country Coverage**: `SELECT COUNT(DISTINCT author_id) FROM authorship_countries`

### After Building Authors
1. **Match Rate**: Should be 100% between authorship and authors
2. **Name Quality**: Check forename/lastname parsing success rate
3. **Geographic Coverage**: Verify country_code distribution

---

## Conclusion

By deriving authors from works data instead of parsing the separate authors snapshot, we:

1. **Solved the 80% mismatch problem** - 100% consistency guaranteed
2. **Enabled critical research phases** - Gender (Phase 4, 10) and Geography (Phase 11)
3. **Created a normalized, efficient database** - Proper separation of concerns
4. **Future-proofed the design** - Easy to add API enrichment later
5. **Maintained COPY performance** - Fast bulk loading preserved

**This approach ensures we capture everything needed for research goals while avoiding unnecessary complexity and data inconsistency issues.**

---

## References

- Analysis Document: `MISSING_WORKS_DATA_ANALYSIS.md`
- Parse Changes Summary: `PARSE_WORKS_CHANGES_SUMMARY.md`
- New Parser: `03_snapshot_parsing/parse_works_v3.py`
- Schema: `02_postgres_setup/orchestrator.py`
- Author Builder: `04_author_profile_building/00_build_authors_from_works.py`
