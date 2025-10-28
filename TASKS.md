# OpenAlex Clinical Flow Cytometry Gender Analysis
## Detailed Task Breakdown

**Last Updated**: 2025-10-28
**Project Status**: Phase 03 (Data Pipeline) in progress

---

## How to Use This Document

### Task Structure
Each task includes:
- **Task ID**: Unique identifier (e.g., P03-T01)
- **Description**: What needs to be done
- **Inputs**: What data/files are needed
- **Outputs**: What will be created
- **Acceptance Criteria**: How to know task is complete
- **Testing Requirements**: What validation is needed
- **Dependencies**: What must be complete first
- **Complexity**: Trivial / Simple / Moderate / Complex / Very Complex
- **Status**: Not Started / In Progress / Complete / Blocked

### Complexity Ratings
- **Trivial** (1): <1 hour, no uncertainty
- **Simple** (2): 1-4 hours, clear path
- **Moderate** (3): 4-16 hours, some problem-solving needed
- **Complex** (4): 2-5 days, significant design decisions
- **Very Complex** (5): >1 week, major technical challenges

---

## PHASE 03: Complete Data Pipeline

**Phase Status**: In Progress (70% complete)
**Priority**: CRITICAL PATH
**Dependencies**: None (foundational)

### Data Loading Tasks

#### P03-T01: Monitor and Complete Works Table Loading
**Status**: In Progress (background process)
**Complexity**: Simple (2)
**Priority**: High

**Description**: Monitor ongoing works table loading process until completion

**Current State**:
- Processing at ~3,000-4,000 works/second
- Recent batch: 339,617 works in 17.6 minutes
- Orchestrator tracking progress

**Tasks**:
1. Check orchestrator logs daily for progress and errors
2. Monitor disk space on NAS (works table growing)
3. Verify batch commit times (should be 5-6 minutes per 100k records)
4. Note completion timestamp when finished

**Inputs**:
- Orchestrator state: `03_snapshot_parsing/big_tables/works/orchestrator_state.json`
- Logs: `03_snapshot_parsing/big_tables/works/logs/`

**Outputs**:
- Completed works table in OADB
- Final processing log with total record count
- Completion summary (total works, time taken, errors)

**Acceptance Criteria**:
- All manifest files processed
- 0 critical errors in logs
- Record count matches expected (~250M for full OpenAlex, or subset)
- Database accessible and queryable

**Testing**:
```sql
-- Verify record count
SELECT COUNT(*) FROM works;

-- Check for nulls in critical fields
SELECT
    COUNT(*) - COUNT(work_id) as missing_work_id,
    COUNT(*) - COUNT(title) as missing_title,
    COUNT(*) - COUNT(publication_year) as missing_year
FROM works;

-- Sample records
SELECT * FROM works ORDER BY RANDOM() LIMIT 10;
```

**Dependencies**: None (already in progress)

---

#### P03-T02: Execute Works Relationships Parsing
**Status**: Not Started (CRITICAL - BLOCKING)
**Complexity**: Moderate (3)
**Priority**: CRITICAL

**Description**: Parse works relationship JSON data into authorship, work_concepts, and work_topics tables

**Current State**:
- Script exists: `03_snapshot_parsing/big_tables/works/parse_works_relationships.py`
- NOT YET EXECUTED
- Authorship table currently EMPTY

**Tasks**:
1. Review `parse_works_relationships.py` code
2. Verify database schema for relationship tables (authorship, work_concepts, work_topics)
3. Configure script (batch size, data paths, database connection)
4. Run script on sample (100 works) to test
5. Execute full relationship parsing
6. Monitor progress and troubleshoot errors

**Inputs**:
- Works JSON files (same as works table loading)
- Database with works table populated
- Authors, concepts, topics tables populated

**Outputs**:
- Populated authorship table (~2M rows for 292k works × ~7 authors/paper)
- Populated work_concepts table
- Populated work_topics table
- Processing log with statistics

**Acceptance Criteria**:
- Authorship table has expected row count (~1.5-2.5M for 292k works)
- Foreign keys valid (all work_id, author_id, institution_id exist)
- No duplicate authorship records (work_id + author_id unique within position)
- Sample validation: check 10 papers manually, verify author list matches

**Testing**:
```sql
-- Count authorships
SELECT COUNT(*) FROM authorship;

-- Check author per paper distribution
SELECT
    author_count,
    COUNT(*) as num_papers
FROM (
    SELECT work_id, COUNT(*) as author_count
    FROM authorship
    GROUP BY work_id
) AS counts
GROUP BY author_count
ORDER BY author_count;

-- Validate foreign keys
SELECT COUNT(*)
FROM authorship a
LEFT JOIN works w ON a.work_id = w.work_id
WHERE w.work_id IS NULL; -- Should be 0

-- Sample validation
SELECT w.title, a.author_position, au.display_name
FROM authorship a
JOIN works w ON a.work_id = w.work_id
JOIN authors au ON a.author_id = au.author_id
WHERE w.work_id = '[pick a known work ID]'
ORDER BY a.author_position;
```

**Dependencies**:
- P03-T01 (works table complete)
- Authors table complete (in progress)

**Estimated Duration**: 4-8 hours (3-4 hours execution + troubleshooting)

---

#### P03-T03: Complete Authors Table Loading
**Status**: In Progress (288 files as of Oct 28)
**Complexity**: Simple (2)
**Priority**: High

**Description**: Monitor and complete authors table loading

**Current State**:
- Orchestrator tracking: 288 files completed (Oct 28, 09:40)
- Processing: authors, author_topics, author_concepts, author_name_variants

**Tasks**:
1. Monitor orchestrator logs for progress
2. Check for errors in recent logs
3. Verify completion when orchestrator finishes
4. Generate summary report

**Inputs**:
- Authors JSON files from snapshot
- Orchestrator state: `03_snapshot_parsing/big_tables/authors/orchestrator_state.json`

**Outputs**:
- Completed authors table (~110M authors expected for full OpenAlex)
- Populated author_topics, author_concepts, author_name_variants tables
- Completion log

**Acceptance Criteria**:
- All manifest files processed
- Record count reasonable (~100M+ for full OpenAlex)
- Sample validation: check known authors appear correctly

**Testing**:
```sql
-- Count authors
SELECT COUNT(*) FROM authors;

-- Check fields
SELECT
    COUNT(*) - COUNT(author_id) as missing_id,
    COUNT(*) - COUNT(display_name) as missing_name,
    COUNT(*) - COUNT(works_count) as missing_works_count
FROM authors;

-- Check distribution of works counts
SELECT
    CASE
        WHEN works_count = 1 THEN '1 paper'
        WHEN works_count BETWEEN 2 AND 5 THEN '2-5 papers'
        WHEN works_count BETWEEN 6 AND 20 THEN '6-20 papers'
        WHEN works_count > 20 THEN '>20 papers'
    END as productivity_bracket,
    COUNT(*) as num_authors
FROM authors
GROUP BY productivity_bracket;
```

**Dependencies**: None (already in progress)

---

#### P03-T04: Investigate and Fix Column Size Issues
**Status**: Not Started
**Complexity**: Moderate (3)
**Priority**: Medium

**Description**: Investigate `fix_column_sizes.py` script and resolve any data type issues

**Current State**:
- Script exists: `03_snapshot_parsing/big_tables/works/fix_column_sizes.py`
- Suggests some columns may have size/type mismatches

**Tasks**:
1. Review `fix_column_sizes.py` to understand what issues it addresses
2. Check database logs for any VARCHAR overflow errors during loading
3. Identify affected columns and records
4. Run fix script if needed (on backup first!)
5. Validate data integrity after fix

**Inputs**:
- Works table (potentially with column size issues)
- `fix_column_sizes.py` script

**Outputs**:
- Fixed column definitions (if needed)
- Migration log
- Validation report

**Acceptance Criteria**:
- No data truncation errors in logs
- All data preserved (row count unchanged)
- Queries run without column size warnings

**Testing**:
```sql
-- Check for suspiciously truncated data (all same length)
SELECT title, LENGTH(title) as len
FROM works
WHERE LENGTH(title) = 255  -- Common VARCHAR limit
LIMIT 20;

-- Check abstract lengths (common overflow field)
SELECT MAX(LENGTH(abstract)) as max_abstract_len FROM works;
```

**Dependencies**: P03-T01 (works table loading complete)

**Estimated Duration**: 2-4 hours

---

### Validation Tasks

#### P03-T05: Design Database Validation Framework
**Status**: Not Started
**Complexity**: Moderate (3)
**Priority**: High

**Description**: Design systematic validation approach for testing database accuracy vs. OpenAlex API

**Tasks**:
1. Design validation sampling strategy:
   - Stratified random sample (by entity type, year, geographic distribution)
   - Edge case sampling (very productive authors, highly cited works)
   - Total: 1,000 queries (200 works, 200 authors, 200 institutions, 200 authorships, 200 concepts/topics/etc.)
2. Write validation script framework:
   - API query function (with rate limiting)
   - Database query function
   - Comparison function (field-by-field comparison)
   - Reporting function (accuracy metrics, mismatch log)
3. Define acceptable mismatch types:
   - Data freshness (API updated since snapshot)
   - Precision differences (rounding)
   - Missing data (NULL in DB, value in API)
4. Set threshold: >95% match rate required

**Inputs**:
- OpenAlex API access (email: s.lucasblack@gmail.com)
- Populated database tables

**Outputs**:
- Validation script: `03_snapshot_parsing/validate_db.py`
- Sampling plan documentation
- Validation report template

**Acceptance Criteria**:
- Script runs without errors on test sample (10 records)
- Handles API rate limits gracefully
- Produces interpretable comparison report
- Code documented and tested

**Testing**:
- Test on 10 known entities
- Verify correct handling of API errors (404, rate limit)
- Check report format is clear

**Dependencies**: P03-T01, P03-T02, P03-T03 (tables populated)

**Estimated Duration**: 4-6 hours

---

#### P03-T06: Execute Database Validation Against API
**Status**: Not Started
**Complexity**: Simple (2)
**Priority**: High

**Description**: Run validation suite and generate accuracy report

**Tasks**:
1. Generate stratified random sample (1,000 entity IDs)
2. Run validation script (may take 1-2 hours with API rate limits)
3. Generate validation report
4. Investigate any systematic mismatches
5. Document validation results

**Inputs**:
- Validation script (from P03-T05)
- Sample entity IDs

**Outputs**:
- Validation report: `03_snapshot_parsing/validation_report_20251115.md`
- Mismatch log (if any)
- Accuracy metrics by entity type

**Acceptance Criteria**:
- Report shows >95% accuracy for all entity types
- Mismatches documented and explained (data freshness, known issues)
- Pass/fail determination clear

**Testing**:
```python
# Expected report structure
{
    "works": {"accuracy": 0.97, "mismatches": 6},
    "authors": {"accuracy": 0.96, "mismatches": 8},
    "institutions": {"accuracy": 0.98, "mismatches": 4},
    "authorship": {"accuracy": 0.95, "mismatches": 10},
    "overall": {"accuracy": 0.965, "pass": True}
}
```

**Dependencies**: P03-T05 (validation framework ready)

**Estimated Duration**: 2-3 hours (plus 1-2 hours script runtime)

---

#### P03-T07: Generate Data Completeness Report
**Status**: Not Started
**Complexity**: Simple (2)
**Priority**: Medium

**Description**: Generate comprehensive data quality report for all tables

**Tasks**:
1. Write SQL queries for each table:
   - Record counts
   - Null percentages by column
   - Duplicate detection
   - Outlier detection (e.g., authors with 10,000+ papers)
   - Temporal distribution (records per year)
2. Run queries and compile results
3. Generate formatted report

**Inputs**:
- All populated database tables

**Outputs**:
- Data completeness report: `03_snapshot_parsing/data_quality_report.md`
- Includes:
  - Table-by-table statistics
  - Identified issues (if any)
  - Recommendations

**Acceptance Criteria**:
- All tables covered
- Null rates documented
- No unexpected duplicates (besides legitimate cases)
- Report formatted for readability

**Example Output**:
```markdown
## Works Table
- Total records: 251,342,556
- Null rates:
  - work_id: 0%
  - title: 0.3%
  - abstract: 42% (expected - many works lack abstracts)
  - publication_year: 0.1%
- Duplicates: 0 (work_id unique)
- Year range: 1800-2024
- Outliers: 15 works with >50,000 citations (validated as legitimate)
```

**Testing**:
- Verify report matches manual queries
- Check that identified issues are real (not script bugs)

**Dependencies**: P03-T01, P03-T02, P03-T03 (all tables populated)

**Estimated Duration**: 3-4 hours

---

#### P03-T08: Write Phase 03 Summary Documentation
**Status**: Not Started
**Complexity**: Simple (2)
**Priority**: Medium

**Description**: Document Phase 03 completion with summary statistics and lessons learned

**Tasks**:
1. Update `03_snapshot_parsing/README.md` with final statistics
2. Create `03_snapshot_parsing/RESULTS_SUMMARY.md`:
   - Record counts by table
   - Processing times and performance
   - Validation results
   - Issues encountered and resolutions
   - Key decisions made
3. Update project-level `DECISION_LOG.md` with any Phase 03 decisions

**Inputs**:
- All Phase 03 outputs (logs, reports, validation results)

**Outputs**:
- Updated README.md
- RESULTS_SUMMARY.md
- Updated DECISION_LOG.md

**Acceptance Criteria**:
- Documentation complete and accurate
- Future users can understand what was done and why
- Key statistics easily findable

**Dependencies**: P03-T01 through P03-T07 complete

**Estimated Duration**: 2-3 hours

---

## PHASE 04: Author Profile Enrichment

**Phase Status**: Not Started (code exists, not run)
**Priority**: CRITICAL PATH
**Dependencies**: Phase 03 complete

### Gender Inference Tasks

#### P04-T01: Review and Test Gender Inference Pipeline (R)
**Status**: Not Started
**Complexity**: Simple (2)
**Priority**: High

**Description**: Review existing R gender inference code and test on small sample

**Current State**:
- Code exists: `04_author_profile_building/` (22 files)
- Not yet executed
- Multi-method pipeline ready: genderizeR, gender-guesser, Genderize.io API

**Tasks**:
1. Review code:
   - `01_extract_author_names.R` - Name parsing
   - `02_predict_gender_multi.R` - Multi-method prediction
   - `03_genderize_api.R` - API integration
   - `04_validate_predictions.R` - Validation
   - `main_orchestrator.R` - Main runner
2. Check R package dependencies (install if needed)
3. Review `config.yaml` - update paths and parameters
4. Test on small sample (100 authors)

**Inputs**:
- Authors table (display_name, current_affiliation_country)
- `config.yaml` (updated)

**Outputs**:
- Confirmed working pipeline
- Test results on 100 authors
- Any necessary code fixes

**Acceptance Criteria**:
- Pipeline runs without errors on test sample
- Output format understood (gender, confidence, method)
- Processing time estimated (to project full run time)

**Testing**:
```r
# Test run
source("04_author_profile_building/main_orchestrator.R")
# Test mode: 100 authors
# Check output format, accuracy on known authors
```

**Dependencies**: P03-T03 (authors table complete)

**Estimated Duration**: 2-3 hours

---

#### P04-T02: Sample 1000 Authors for Validation
**Status**: Not Started
**Complexity**: Simple (2)
**Priority**: High

**Description**: Generate stratified sample of 1,000 authors for manual validation

**Tasks**:
1. Design sampling strategy:
   - Stratify by country (ensure diversity: US, Europe, Asia, other)
   - Stratify by name characteristics (different scripts, lengths)
   - Stratify by works count (1 paper, 2-10, 10+)
   - Random seed: 42 (reproducibility)
2. Execute sampling query
3. Export sample author IDs and display names
4. Document sample composition

**Inputs**:
- Authors table

**Outputs**:
- Sample file: `04_author_profile_building/validation_sample_1000.csv`
- Sample composition report: `04_author_profile_building/validation_sample_composition.md`

**Acceptance Criteria**:
- Exactly 1,000 authors
- Diverse across stratification variables
- Reproducible (same seed → same sample)
- Sample IDs logged

**Testing**:
```sql
-- Sampling query
WITH author_strata AS (
    SELECT
        author_id,
        display_name,
        current_affiliation_country,
        works_count,
        CASE
            WHEN current_affiliation_country IN ('US', 'United States') THEN 'US'
            WHEN current_affiliation_country IN (SELECT country FROM european_countries) THEN 'Europe'
            WHEN current_affiliation_country IN (SELECT country FROM asian_countries) THEN 'Asia'
            ELSE 'Other'
        END as region,
        CASE
            WHEN works_count = 1 THEN 'single'
            WHEN works_count BETWEEN 2 AND 10 THEN 'low'
            ELSE 'high'
        END as productivity
    FROM authors
    WHERE display_name IS NOT NULL
)
SELECT author_id, display_name, current_affiliation_country, works_count
FROM author_strata
WHERE [stratified sampling logic with random seed 42]
ORDER BY RANDOM() -- with seed
LIMIT 1000;
```

**Dependencies**: P03-T03 (authors table)

**Estimated Duration**: 1-2 hours

---

#### P04-T03: Run Gender Inference on Validation Sample
**Status**: Not Started
**Complexity**: Simple (2)
**Priority**: High

**Description**: Run gender inference pipeline on 1,000 author validation sample

**Tasks**:
1. Configure R pipeline for sample IDs
2. Run gender inference (all methods: genderizeR, gender-guesser, API)
3. Generate HTML validation report
4. Export results for manual review

**Inputs**:
- Validation sample (P04-T02)
- Gender inference pipeline (P04-T01)

**Outputs**:
- Gender predictions for 1,000 authors: `04_author_profile_building/validation_predictions.csv`
- HTML validation report: `04_author_profile_building/validation_report.html`
- Includes:
  - Method agreement/disagreement
  - Confidence distributions
  - Low-confidence flagging

**Acceptance Criteria**:
- All 1,000 authors processed
- HTML report generated and viewable
- Results include gender (M/F/Unknown), confidence, method used

**Testing**:
- Spot-check 10 obvious names (e.g., "Michael Smith" → M, "Jennifer Lee" → F)
- Check method agreement rate (expect 85-95% agreement across methods)

**Dependencies**: P04-T01, P04-T02

**Estimated Duration**: 1-2 hours (including runtime)

---

#### P04-T04: Manual Validation of Gender Predictions
**Status**: Not Started
**Complexity**: Moderate (3)
**Priority**: High

**Description**: Manually review validation sample to assess accuracy

**Tasks**:
1. Review HTML validation report
2. For subsample (100-200 authors with diverse predictions):
   - Google author name + affiliation
   - Check personal website, publications, pronouns
   - Record actual gender (M/F/Unknown if ambiguous)
3. Calculate accuracy metrics:
   - Overall accuracy (% correct)
   - Precision/recall by gender
   - Accuracy by confidence level
   - Accuracy by country
4. Document findings and recommend threshold

**Inputs**:
- Validation predictions (P04-T03)
- HTML report

**Outputs**:
- Manual validation results: `04_author_profile_building/manual_validation_results.csv`
- Validation summary report: `04_author_profile_building/validation_summary.md`
- Recommended confidence threshold (e.g., "use predictions with confidence >0.75")

**Acceptance Criteria**:
- ≥100 authors manually validated
- Accuracy >80% (target for proceeding to full run)
- Clear recommendation on confidence threshold
- Documentation of any systematic errors (e.g., specific countries/names)

**Example Output**:
```markdown
## Validation Summary
- Sample size: 150 manually validated
- Overall accuracy: 83%
- M accuracy: 87% (precision: 92%, recall: 87%)
- F accuracy: 79% (precision: 85%, recall: 79%)
- Confidence >0.8 accuracy: 91%
- Confidence 0.6-0.8 accuracy: 75%
- Confidence <0.6 accuracy: 62%

**Recommendation**: Use confidence threshold 0.7. Expect ~85% accuracy on full dataset.
```

**Dependencies**: P04-T03

**Estimated Duration**: 4-6 hours (manual work intensive)

---

#### P04-T05: Adjust Pipeline Based on Validation (if needed)
**Status**: Not Started
**Complexity**: Simple to Moderate (2-3)
**Priority**: Medium

**Description**: Adjust gender inference pipeline if validation reveals issues

**Conditional Task**: Only needed if P04-T04 reveals accuracy <80% or systematic issues

**Possible Adjustments**:
1. Change confidence threshold
2. Prioritize certain methods (e.g., API over heuristics for specific countries)
3. Add country-specific adjustments
4. Flag certain name patterns as unreliable

**Inputs**:
- Validation results (P04-T04)
- Gender inference code

**Outputs**:
- Updated pipeline code (if needed)
- Updated config (thresholds, method weights)
- Justification documented

**Acceptance Criteria**:
- Changes improve accuracy on validation set
- Changes documented in code comments
- Re-run validation sample to confirm improvement

**Dependencies**: P04-T04

**Estimated Duration**: 2-4 hours (if needed)

---

#### P04-T06: Run Full Gender Inference (2M Authors)
**Status**: Not Started
**Complexity**: Simple (2) - but long runtime
**Priority**: High

**Description**: Run gender inference pipeline on full author database

**Tasks**:
1. Configure pipeline for full run (all authors with display_name)
2. Set up batch processing (e.g., 100k authors per batch)
3. Execute pipeline (may take hours/overnight)
4. Monitor progress and logs
5. Handle errors gracefully

**Inputs**:
- Full authors table (~2M authors)
- Validated gender inference pipeline

**Outputs**:
- Gender predictions for all authors: `04_author_profile_building/all_authors_gender.csv`
- Processing log
- Coverage report (% M, % F, % Unknown by country)

**Acceptance Criteria**:
- All authors processed (100% of those with display_name)
- Results include gender, confidence, method
- Coverage ≥70% (M or F assigned)
- No critical errors in log

**Testing**:
```r
# Check coverage
table(gender_results$gender)
# M      F      Unknown
# 800k   600k   600k

# Check confidence distribution
summary(gender_results$confidence)

# Check by country
table(gender_results$country, gender_results$gender)
```

**Dependencies**: P04-T03, P04-T04, P04-T05 (pipeline validated)

**Estimated Duration**: 4-8 hours runtime (overnight run recommended)

---

#### P04-T07: Write Gender Predictions to Database
**Status**: Not Started
**Complexity**: Simple (2)
**Priority**: High

**Description**: Update authors.gender column with inference results

**Tasks**:
1. Load gender predictions CSV
2. Match to authors table by author_id
3. Update authors.gender column
4. Optionally: add authors.gender_confidence, authors.gender_method columns
5. Verify updates

**Inputs**:
- Gender predictions CSV (P04-T06)
- Authors table

**Outputs**:
- Updated authors table with gender column populated
- Update log

**Acceptance Criteria**:
- All author records updated (gender may be Unknown for some)
- No mismatches (author_id exists)
- Sample validation: check known authors have correct gender

**Testing**:
```sql
-- Check update coverage
SELECT gender, COUNT(*) FROM authors GROUP BY gender;

-- Spot check
SELECT author_id, display_name, gender
FROM authors
WHERE display_name ILIKE '%Jennifer%' OR display_name ILIKE '%Michael%'
LIMIT 20;
```

**Dependencies**: P04-T06

**Estimated Duration**: 1-2 hours

---

#### P04-T08: Generate Gender Inference Report
**Status**: Not Started
**Complexity**: Simple (2)
**Priority**: Medium

**Description**: Create comprehensive report on gender inference results

**Tasks**:
1. Compile statistics:
   - Overall coverage (% M, % F, % Unknown)
   - Coverage by country
   - Confidence distributions
   - Method usage (which method assigned most genders?)
2. Generate visualizations:
   - Bar chart: gender distribution
   - Map: coverage by country
   - Histogram: confidence distribution
3. Write interpretation:
   - Comparison to validation accuracy
   - Known limitations
   - Recommendations for analysis (e.g., sensitivity analyses excluding low-confidence)

**Inputs**:
- Gender predictions (P04-T06, P04-T07)
- Validation results (P04-T04)

**Outputs**:
- Report: `04_author_profile_building/gender_inference_report.md`
- Figures: embedded or in `04_author_profile_building/figures/`

**Acceptance Criteria**:
- Report clearly communicates coverage and accuracy
- Suitable for methods section of publication
- Limitations honestly discussed

**Dependencies**: P04-T07

**Estimated Duration**: 2-3 hours

---

### Career Stage Modeling Tasks

#### P04-T09: Define Career Stage Model (Collaborative)
**Status**: Not Started
**Complexity**: Moderate (3)
**Priority**: High

**Description**: Collaborate with Lucas to define career stage taxonomy and calculation rules

**Approach**: Hybrid (domain knowledge + data-driven validation)

**Tasks**:
1. **Propose Initial Model** (Lucas + Claude):
   - Taxonomy (e.g., 5 stages: Early, Established, Senior, Emeritus, Rising)
   - Decision rules:
     - **Early**: 0-5 years since first publication, primarily first author
     - **Established**: 6-15 years, mix of first/last, ≥1 corresponding authorship
     - **Senior**: 16+ years, primarily last/corresponding author, ≥20 papers
     - **Emeritus**: >20 years but inactive (no papers in last 5 years)
     - **Rising**: <10 years but high productivity/citations (potential fast-track)
2. **Data Exploration**:
   - Plot distributions: years active, authorship patterns, productivity
   - Identify natural breakpoints
   - Check proportion of authors in each proposed stage (reasonable?)
3. **Validation**:
   - Test on known authors (if Lucas has examples)
   - Check face validity (do assigned stages make sense?)
4. **Refinement**:
   - Adjust thresholds based on data
   - Consider field-specific norms (clinical flow cytometry career timelines)
5. **Documentation**:
   - Write formal model definition
   - Justify thresholds with data

**Inputs**:
- Authors table with computed career metrics (years active, authorship patterns)
- Lucas's domain knowledge of clinical flow cytometry career norms

**Outputs**:
- Career stage model document: `04_author_profile_building/career_stage_model.md`
- Includes:
  - Stage definitions
  - Decision rules (precise thresholds)
  - Justification
  - Validation results

**Acceptance Criteria**:
- Model clearly defined (no ambiguity)
- Thresholds justified (not arbitrary)
- Distributes authors reasonably (no stage with 90% of authors)
- Lucas approves model

**Dependencies**: P04-T07 (need author data), authorship table (P03-T02)

**Estimated Duration**: 4-6 hours (collaborative session + analysis)

---

#### P04-T10: Compute Career Metrics for All Authors
**Status**: Not Started
**Complexity**: Moderate (3)
**Priority**: High

**Description**: Compute career-related metrics needed for stage model and analyses

**Metrics to Compute**:
1. **Temporal**:
   - `first_publication_year` (earliest year in authorship)
   - `last_publication_year` (latest year in authorship)
   - `career_length_years` (last - first)
   - `is_current` (published 2022-2024?)
2. **Authorship Patterns**:
   - `first_author_count` (times in position 1)
   - `last_author_count` (times in last position)
   - `middle_author_count` (times in middle)
   - `freq_first_author` (first_count / total_papers)
   - `freq_last_author` (last_count / total_papers)
3. **Productivity**:
   - `works_count` (already in authors table)
   - `cited_by_count` (already in authors table)
4. **Affiliation**:
   - `current_affiliation_id` (institution from most recent paper)
   - `current_affiliation_name`
   - `current_affiliation_country`

**Tasks**:
1. Write SQL queries to compute metrics
2. Create table: `author_career_metrics` OR add columns to `authors` table
3. Execute queries (may take time for 2M authors)
4. Validate results (spot-check, distributions)

**Inputs**:
- Authorship table (work_id, author_id, author_position)
- Works table (publication_year)
- Authors table (works_count, cited_by_count)

**Outputs**:
- Table with career metrics for all authors
- Summary statistics report

**Acceptance Criteria**:
- All 2M authors have computed metrics
- Distributions reasonable (no negative years, etc.)
- Null handling documented (e.g., authors with no affiliation)

**Testing**:
```sql
-- Check distributions
SELECT
    MIN(first_publication_year) as earliest,
    MAX(last_publication_year) as latest,
    AVG(career_length_years) as avg_career_length
FROM author_career_metrics;

-- Check authorship patterns
SELECT
    AVG(freq_first_author) as avg_first_freq,
    AVG(freq_last_author) as avg_last_freq
FROM author_career_metrics
WHERE works_count >= 5; -- Authors with ≥5 papers

-- Sample
SELECT * FROM author_career_metrics
ORDER BY RANDOM() LIMIT 20;
```

**Dependencies**: P03-T02 (authorship table), P03-T03 (authors table)

**Estimated Duration**: 4-6 hours

---

#### P04-T11: Implement Career Stage Model
**Status**: Not Started
**Complexity**: Moderate (3)
**Priority**: High

**Description**: Implement career stage model in R or Python

**Tasks**:
1. Write classification function:
   - Input: author career metrics
   - Output: career_stage (Early/Established/Senior/Emeritus/Rising)
   - Follow decision rules from P04-T09
2. Test on sample (100 authors, manually verify)
3. Apply to all authors
4. Generate distribution report

**Inputs**:
- Career metrics (P04-T10)
- Career stage model definition (P04-T09)

**Outputs**:
- Career stage assignments for all authors
- Distribution report (% in each stage)
- Code: `04_author_profile_building/99_Career_stage_Calculation.R` (or .py)

**Acceptance Criteria**:
- All authors assigned a stage
- Distribution reasonable (e.g., Early: 40%, Established: 30%, Senior: 20%, Emeritus: 5%, Rising: 5%)
- Spot-check: known authors have sensible stages

**Testing**:
```r
# Distribution
table(author_stages$career_stage)

# Cross-tab with years active
table(author_stages$career_stage, cut(author_stages$career_length_years, breaks=c(0,5,15,100)))

# Sample
sample_n(author_stages, 20)
```

**Dependencies**: P04-T09, P04-T10

**Estimated Duration**: 3-4 hours

---

#### P04-T12: Write Career Stages to Database
**Status**: Not Started
**Complexity**: Simple (2)
**Priority**: High

**Description**: Update authors table with career stage assignments

**Tasks**:
1. Load career stage assignments
2. Update authors.career_stage column
3. Verify updates

**Inputs**:
- Career stage assignments (P04-T11)

**Outputs**:
- Updated authors table with career_stage column

**Acceptance Criteria**:
- All authors have career_stage assigned
- Distribution matches P04-T11 report

**Testing**:
```sql
SELECT career_stage, COUNT(*)
FROM authors
GROUP BY career_stage;
```

**Dependencies**: P04-T11

**Estimated Duration**: 1 hour

---

#### P04-T13: Write Phase 04 Summary Documentation
**Status**: Not Started
**Complexity**: Simple (2)
**Priority**: Medium

**Description**: Document Phase 04 completion

**Tasks**:
1. Update `04_author_profile_building/README.md`
2. Create `04_author_profile_building/RESULTS_SUMMARY.md`:
   - Gender inference results (coverage, accuracy)
   - Career stage model definition and distribution
   - Key decisions and justifications
3. Update `DECISION_LOG.md`

**Inputs**:
- All Phase 04 outputs

**Outputs**:
- Updated documentation

**Acceptance Criteria**:
- Clear summary of Phase 04 work
- Suitable for methods section reference

**Dependencies**: All Phase 04 tasks complete

**Estimated Duration**: 2-3 hours

---

## PHASE 05: Corpus Definition & Query System

**Phase Status**: Not Started
**Priority**: CRITICAL PATH
**Dependencies**: Phase 03, Phase 04

### Query System Design

#### P05-T01: Design Reusable Query Framework
**Status**: Not Started
**Complexity**: Complex (4)
**Priority**: High

**Description**: Design and implement query system with versioning and logging

**Requirements**:
- Multiple query methods (text search, MeSH, topics, journals)
- Query logging (track what, when, who)
- Version control (corpus_v1, corpus_v2, etc.)
- Comparison framework (Venn diagrams of overlaps)
- Reproducible (same query → same results)

**Tasks**:
1. **Design Schema**:
   - `search_metadata` table (already exists?)
     - query_id, query_name, query_type, query_string, date_run, work_count, version
   - `corpus_definitions` table
     - corpus_id, corpus_name, version, creation_date, description, final_work_count
   - `corpus_works` table
     - corpus_id, work_id (mapping)

2. **Implement Query Classes** (Python):
   ```python
   class QueryBuilder:
       def __init__(self, db_connection):
           pass

       def text_search(self, terms, fields=['title', 'abstract']):
           """Search for terms in specified fields"""
           pass

       def topic_search(self, topic_ids):
           """Search by OpenAlex topic IDs"""
           pass

       def journal_search(self, source_ids):
           """Search by journal/source IDs"""
           pass

       def mesh_search(self, mesh_terms):
           """Search by MeSH terms (if available)"""
           pass

       def combine(self, query1, query2, operator='AND'):
           """Combine queries with AND/OR/NOT"""
           pass

       def execute(self, query_name, save_version=None):
           """Execute query, log to search_metadata, optionally save as corpus"""
           pass

       def compare(self, query_list):
           """Generate Venn diagram of overlaps"""
           pass
   ```

3. **Implement Logging**:
   - Log every query execution
   - Save query parameters (for reproducibility)
   - Link queries to corpus versions

4. **Test Framework**:
   - Test queries on small dataset
   - Verify logging works
   - Test combine and compare functions

**Inputs**:
- Database with works, work_topics, work_concepts tables

**Outputs**:
- Query framework code: `05_db_query/query_builder.py`
- Schema updates (tables created)
- Unit tests: `05_db_query/test_query_builder.py`
- Documentation: `05_db_query/README.md`

**Acceptance Criteria**:
- All query types implemented
- Logging functional
- Unit tests pass
- Documentation clear (usage examples)

**Dependencies**: P03-T01, P03-T02 (works and relationships)

**Estimated Duration**: 6-8 hours

---

#### P05-T02: Identify Relevant OpenAlex Topics/Concepts
**Status**: Not Started
**Complexity**: Moderate (3)
**Priority**: High

**Description**: Identify which OpenAlex topics/concepts correspond to clinical flow cytometry

**Tasks**:
1. Explore topics table:
   ```sql
   SELECT * FROM topics WHERE display_name ILIKE '%flow cytometry%';
   SELECT * FROM topics WHERE display_name ILIKE '%cytometry%';
   ```
2. Explore concepts table similarly
3. Manually review candidate topics/concepts (read descriptions, check example works)
4. Compile final list of relevant topic/concept IDs
5. Estimate corpus size for each

**Inputs**:
- Topics table
- Concepts table
- Work_topics, work_concepts relationships

**Outputs**:
- List of relevant topic IDs: `05_db_query/relevant_topics.csv`
- List of relevant concept IDs: `05_db_query/relevant_concepts.csv`
- Exploration report: `05_db_query/topic_concept_exploration.md`

**Acceptance Criteria**:
- ≥3 topics identified
- ≥5 concepts identified
- Justification for each (why relevant to clinical flow cytometry)
- Estimated work counts documented

**Testing**:
```sql
-- Check work counts
SELECT t.display_name, COUNT(wt.work_id) as num_works
FROM topics t
JOIN work_topics wt ON t.topic_id = wt.topic_id
WHERE t.topic_id IN ([identified topic IDs])
GROUP BY t.display_name;
```

**Dependencies**: P03-T02 (relationships table)

**Estimated Duration**: 3-4 hours

---

### Multi-Method Query Execution

#### P05-T03: Execute Method 1 - Text Search
**Status**: Not Started
**Complexity**: Simple (2)
**Priority**: High

**Description**: Query works with "clinical flow cytometry" or related terms in title/abstract

**Tasks**:
1. Define search terms:
   - Primary: "clinical flow cytometry"
   - Secondary: "flow cytometry" + "clinical", "diagnostic flow cytometry", etc.
   - Decide: exact phrase vs. fuzzy match
2. Execute query using QueryBuilder
3. Log query to search_metadata
4. Generate summary report (work count, year distribution)

**Inputs**:
- Works table (title, abstract)
- Query framework (P05-T01)

**Outputs**:
- Work IDs from text search: `05_db_query/results/text_search_work_ids.csv`
- Summary report: `05_db_query/results/text_search_summary.md`
- Query logged to database

**Acceptance Criteria**:
- Query executed successfully
- Result count: 200k-400k works (expected range)
- Summary report shows reasonable year distribution
- Query logged and reproducible

**Testing**:
```sql
-- Verify query
SELECT COUNT(*) FROM works
WHERE (title ILIKE '%clinical flow cytometry%' OR abstract ILIKE '%clinical flow cytometry%')
   OR (title ILIKE '%flow cytometry%' AND (title ILIKE '%clinical%' OR abstract ILIKE '%clinical%'));

-- Year distribution
SELECT publication_year, COUNT(*)
FROM works
WHERE work_id IN ([text search results])
GROUP BY publication_year
ORDER BY publication_year;
```

**Dependencies**: P05-T01 (query framework)

**Estimated Duration**: 2-3 hours

---

#### P05-T04: Execute Method 2 - Topic/Concept Search
**Status**: Not Started
**Complexity**: Simple (2)
**Priority**: High

**Description**: Query works by OpenAlex topics/concepts

**Tasks**:
1. Use topic/concept IDs from P05-T02
2. Execute query using QueryBuilder
3. Log query
4. Generate summary report

**Inputs**:
- Relevant topic/concept IDs (P05-T02)
- Query framework

**Outputs**:
- Work IDs from topic search: `05_db_query/results/topic_search_work_ids.csv`
- Summary report: `05_db_query/results/topic_search_summary.md`

**Acceptance Criteria**:
- Query executed successfully
- Result count documented
- Logged and reproducible

**Testing**:
```sql
SELECT COUNT(DISTINCT wt.work_id)
FROM work_topics wt
WHERE wt.topic_id IN ([topic IDs from P05-T02]);
```

**Dependencies**: P05-T01, P05-T02

**Estimated Duration**: 2 hours

---

#### P05-T05: Execute Method 3 - Journal Filtering (Optional)
**Status**: Not Started
**Complexity**: Simple (2)
**Priority**: Low

**Description**: Query works from specific clinical flow cytometry journals

**Note**: Use for validation/comparison, not primary corpus definition

**Tasks**:
1. Identify journal source IDs (from hypothesis doc list: Cytometry Part B, Blood, etc.)
2. Execute query
3. Compare to text/topic searches

**Inputs**:
- Journal list (from hypothesis doc)
- Sources table

**Outputs**:
- Work IDs from journal filter: `05_db_query/results/journal_filter_work_ids.csv`

**Acceptance Criteria**:
- Journals identified and queried
- Used for validation (overlap with other methods)

**Dependencies**: P05-T01

**Estimated Duration**: 2 hours

---

#### P05-T06: Compare Query Methods (Venn Analysis)
**Status**: Not Started
**Complexity**: Moderate (3)
**Priority**: High

**Description**: Compare overlaps between query methods to understand corpus definition

**Tasks**:
1. Load work IDs from all methods (P05-T03, P05-T04, P05-T05)
2. Compute overlaps:
   - Text ∩ Topic
   - Text ∩ Journal
   - Topic ∩ Journal
   - Text ∩ Topic ∩ Journal
   - Unique to each method
3. Generate Venn diagram (2-way and 3-way)
4. Investigate discrepancies:
   - Sample works unique to text search (why not in topics?)
   - Sample works unique to topic search (why not in text?)
5. Generate comparison report

**Inputs**:
- Work ID lists from P05-T03, P05-T04, P05-T05

**Outputs**:
- Venn diagram: `05_db_query/results/query_method_overlap.png`
- Comparison report: `05_db_query/results/query_comparison.md`
- Includes:
  - Overlap counts
  - Example works from each region
  - Interpretation

**Acceptance Criteria**:
- Overlaps computed correctly
- Venn diagram clear and interpretable
- Report explains differences between methods

**Testing**:
```python
import matplotlib_venn

text_ids = set(load_ids('text_search_work_ids.csv'))
topic_ids = set(load_ids('topic_search_work_ids.csv'))

overlap = len(text_ids & topic_ids)
text_only = len(text_ids - topic_ids)
topic_only = len(topic_ids - text_ids)

matplotlib_venn.venn2([text_ids, topic_ids], set_labels=('Text Search', 'Topic Search'))
```

**Dependencies**: P05-T03, P05-T04, P05-T05

**Estimated Duration**: 3-4 hours

---

### Corpus Validation & Finalization

#### P05-T07: Sample and Manually Validate Corpus Relevance
**Status**: Not Started
**Complexity**: Moderate (3)
**Priority**: High

**Description**: Manually review sample of works to assess relevance

**Tasks**:
1. **Sample 100 works from corpus** (stratified by year, query method)
   - Random seed: 42
2. **Manual review**:
   - Read title and abstract
   - Classify: Relevant / Borderline / Irrelevant
   - Note why irrelevant (if applicable)
3. **Sample 100 works from EXCLUDED set** (nearby works not in corpus)
   - Check for false negatives
4. Calculate precision and recall estimates
5. Decide if refinement needed

**Inputs**:
- Corpus work IDs (union or intersection from P05-T06)
- Excluded work IDs (works in DB but not in corpus)

**Outputs**:
- Validation sample results: `05_db_query/validation/manual_validation_results.csv`
- Validation report: `05_db_query/validation/validation_report.md`
- Includes:
  - Precision (% of corpus actually relevant)
  - Recall estimate (missed relevant works)
  - Examples of errors
  - Recommendation (refine query or accept)

**Acceptance Criteria**:
- 100 corpus works reviewed
- 100 excluded works reviewed
- Precision ≥90% (target)
- Report clear on whether refinement needed

**Dependencies**: P05-T06 (preliminary corpus)

**Estimated Duration**: 4-6 hours (manual work)

---

#### P05-T08: Refine Corpus Query (if needed)
**Status**: Not Started
**Complexity**: Moderate (3)
**Priority**: High (conditional)

**Description**: Adjust query based on validation findings

**Conditional**: Only if P05-T07 shows precision <90% or significant false negatives

**Possible Adjustments**:
- Add/remove search terms
- Adjust topic/concept IDs
- Combine methods differently (e.g., require overlap)
- Add manual inclusions/exclusions

**Tasks**:
1. Analyze validation errors (P05-T07)
2. Design refined query
3. Execute refined query
4. Re-validate on sample
5. Iterate until precision ≥90%

**Inputs**:
- Validation results (P05-T07)
- Original queries

**Outputs**:
- Refined corpus (work IDs)
- Documentation of refinements

**Acceptance Criteria**:
- Precision ≥90% on re-validation
- Refinements justified and documented

**Dependencies**: P05-T07

**Estimated Duration**: 3-5 hours (if needed)

---

#### P05-T09: Create Final Corpus Table
**Status**: Not Started
**Complexity**: Simple (2)
**Priority**: High

**Description**: Create final corpus definition in database

**Tasks**:
1. Finalize work ID list (after validation/refinement)
2. Create corpus in database:
   ```sql
   -- Create corpus definition
   INSERT INTO corpus_definitions (corpus_name, version, description, creation_date, final_work_count)
   VALUES ('clinical_flow_cytometry', 'v1', 'Clinical flow cytometry corpus defined by [methods]', CURRENT_DATE, [count]);

   -- Populate corpus_works
   INSERT INTO corpus_works (corpus_id, work_id)
   SELECT [corpus_id], work_id FROM [final work ID list];
   ```
3. Verify corpus table
4. Create convenience view:
   ```sql
   CREATE VIEW clinical_flow_cytometry_works AS
   SELECT w.*
   FROM works w
   JOIN corpus_works cw ON w.work_id = cw.work_id
   WHERE cw.corpus_id = [clinical_flow_cytometry_corpus_id];
   ```

**Inputs**:
- Final work ID list (P05-T07 or P05-T08)

**Outputs**:
- Populated corpus_definitions table
- Populated corpus_works table
- View: clinical_flow_cytometry_works
- Export: `05_db_query/final_corpus_v1_work_ids.csv`

**Acceptance Criteria**:
- Corpus count: 250k-350k works (target ~292k based on Lucas's estimate)
- All works exist in works table (no orphans)
- View queries successfully

**Testing**:
```sql
-- Verify count
SELECT COUNT(*) FROM corpus_works WHERE corpus_id = [clinical_flow_cytometry];

-- Verify all works exist
SELECT COUNT(*) FROM corpus_works cw
LEFT JOIN works w ON cw.work_id = w.work_id
WHERE w.work_id IS NULL; -- Should be 0

-- Test view
SELECT * FROM clinical_flow_cytometry_works LIMIT 10;
```

**Dependencies**: P05-T07 or P05-T08

**Estimated Duration**: 2 hours

---

#### P05-T10: Generate Corpus Statistics Report
**Status**: Not Started
**Complexity**: Moderate (3)
**Priority**: High

**Description**: Generate comprehensive statistics for final corpus

**Tasks**:
1. Compute statistics:
   - Total works count
   - Year range and distribution (histogram)
   - Journal distribution (top 20 journals)
   - Total unique authors (from authorship table)
   - Total unique institutions
   - Geographic distribution (by institution country)
   - Citation distribution (total citations, top-cited works)
   - Topics/concepts distribution
2. Generate visualizations:
   - Works per year (line plot)
   - Top journals (bar chart)
   - Geographic distribution (map or bar chart)
   - Author productivity distribution (histogram)
3. Write narrative summary

**Inputs**:
- Final corpus (P05-T09)
- Authorship table
- Authors table
- Institutions table

**Outputs**:
- Corpus statistics report: `05_db_query/corpus_statistics_v1.md`
- Figures: `05_db_query/figures/corpus_*.png`

**Acceptance Criteria**:
- All statistics computed and accurate
- Visualizations clear and publication-quality
- Report suitable for publication (descriptive stats section)

**Example Output**:
```markdown
## Clinical Flow Cytometry Corpus Statistics (v1)

### Overview
- Total works: 292,156
- Year range: 1983-2024 (41 years)
- Authors: 1,987,453 total, 306,142 with >1 paper
- Institutions: 15,234 unique institutions
- Countries: 156 countries represented

### Temporal Distribution
[Line plot: works per year, showing growth]
- Peak year: 2019 (18,432 works)
- Growth rate (2000-2024): 7.2% per year

### Top Journals
1. Cytometry Part B: 34,521 works (11.8%)
2. Blood: 28,103 works (9.6%)
...

### Geographic Distribution
- US: 35.2% of works
- Europe: 32.1%
- Asia: 24.3%
...
```

**Dependencies**: P05-T09

**Estimated Duration**: 4-5 hours

---

#### P05-T11: Historical Data Quality Assessment
**Status**: Not Started
**Complexity**: Moderate (3)
**Priority**: Medium

**Description**: Assess data completeness by decade to determine historical cutoff

**Tasks**:
1. Stratify corpus by decade (1980s, 1990s, 2000s, 2010s, 2020s)
2. For each decade, compute:
   - Works count
   - % with abstracts
   - % with author affiliations (from authorship)
   - % with complete author names (not just initials)
   - % with topics/concepts assigned
3. Identify quality threshold (e.g., "use decades with ≥70% complete author affiliations")
4. Set historical cutoff for analyses

**Inputs**:
- Corpus works
- Authorship table
- Authors table

**Outputs**:
- Data quality by decade report: `05_db_query/historical_data_quality.md`
- Recommendation: final time range (e.g., "1990-2024")

**Acceptance Criteria**:
- Quality metrics computed for all decades
- Clear recommendation on cutoff
- Rationale documented

**Example**:
```markdown
## Data Quality by Decade

| Decade | Works | Abstract % | Affiliation % | Full Name % |
|--------|-------|------------|---------------|-------------|
| 1980s  | 1,234 | 23%        | 15%           | 45%         |
| 1990s  | 8,521 | 68%        | 54%           | 78%         |
| 2000s  | 45,102| 87%        | 82%           | 93%         |
| 2010s  | 112,345| 94%       | 91%           | 97%         |
| 2020s  | 124,954| 96%       | 94%           | 98%         |

**Recommendation**: Use 1990-2024 (exclude 1980s due to <50% affiliation data)
```

**Dependencies**: P05-T09

**Estimated Duration**: 3-4 hours

---

#### P05-T12: Write Phase 05 Summary Documentation
**Status**: Not Started
**Complexity**: Simple (2)
**Priority**: Medium

**Description**: Document Phase 05 completion

**Tasks**:
1. Update `05_db_query/README.md`
2. Create `05_db_query/RESULTS_SUMMARY.md`
3. Update `DECISION_LOG.md` with corpus definition decisions

**Inputs**:
- All Phase 05 outputs

**Outputs**:
- Updated documentation

**Acceptance Criteria**:
- Clear documentation of corpus definition
- Suitable for publication methods section

**Dependencies**: All Phase 05 tasks complete

**Estimated Duration**: 2-3 hours

---

## PHASE 06: Network Construction

**Phase Status**: Not Started
**Priority**: CRITICAL PATH
**Dependencies**: Phase 05 (corpus defined)

### Network Data Extraction

#### P06-T01: Extract Co-Author Edge List
**Status**: Not Started
**Complexity**: Moderate (3)
**Priority**: High

**Description**: Extract co-authorship relationships from database

**Tasks**:
1. Write SQL query to extract co-author pairs:
   ```sql
   -- All author pairs on same paper in corpus
   SELECT
       a1.author_id AS author1_id,
       a2.author_id AS author2_id,
       COUNT(DISTINCT a1.work_id) AS paper_count,
       MIN(w.publication_year) AS first_collab_year,
       MAX(w.publication_year) AS last_collab_year
   FROM authorship a1
   JOIN authorship a2 ON a1.work_id = a2.work_id AND a1.author_id < a2.author_id
   JOIN corpus_works cw ON a1.work_id = cw.work_id
   JOIN works w ON a1.work_id = w.work_id
   WHERE cw.corpus_id = [clinical_flow_cytometry_corpus_id]
   GROUP BY a1.author_id, a2.author_id;
   ```
2. Test query on sample (10 works)
3. Execute full query (may take 30min-2hours)
4. Export to CSV/Parquet

**Inputs**:
- Authorship table
- Corpus_works table

**Outputs**:
- Co-author edge list: `06_network_building/data/coauthor_edgelist.parquet`
- Includes columns: author1_id, author2_id, paper_count, first_year, last_year
- Query log with execution time

**Acceptance Criteria**:
- Edge count: estimated 1-10M edges (depends on network density)
- No self-loops (author1_id ≠ author2_id)
- All author IDs exist in authors table
- Sample validation: check known collaborations present

**Testing**:
```python
import pandas as pd

edges = pd.read_parquet('coauthor_edgelist.parquet')

# Check structure
print(edges.shape)
print(edges.head())

# Check for self-loops
assert (edges['author1_id'] != edges['author2_id']).all()

# Check paper counts
print(edges['paper_count'].describe())
```

**Dependencies**: P05-T09 (corpus defined)

**Estimated Duration**: 3-4 hours

---

#### P06-T02: Extract Author-Institution Relationships
**Status**: Not Started
**Complexity**: Moderate (3)
**Priority**: High

**Description**: Extract author-institution affiliations from corpus

**Tasks**:
1. Write SQL query:
   ```sql
   SELECT
       a.author_id,
       a.affiliation_institution_id AS institution_id,
       COUNT(DISTINCT a.work_id) AS paper_count,
       MIN(w.publication_year) AS first_year,
       MAX(w.publication_year) AS last_year
   FROM authorship a
   JOIN corpus_works cw ON a.work_id = cw.work_id
   JOIN works w ON a.work_id = w.work_id
   WHERE a.affiliation_institution_id IS NOT NULL
   GROUP BY a.author_id, a.affiliation_institution_id;
   ```
2. Execute and export

**Inputs**:
- Authorship table (with affiliation_institution_id)
- Corpus_works table

**Outputs**:
- Author-institution edge list: `06_network_building/data/author_institution_edgelist.parquet`

**Acceptance Criteria**:
- All institution IDs exist in institutions table
- Each author-institution pair has ≥1 paper

**Dependencies**: P05-T09

**Estimated Duration**: 2-3 hours

---

#### P06-T03: Extract Co-Institution Relationships (Optional)
**Status**: Not Started
**Complexity**: Moderate (3)
**Priority**: Low

**Description**: Extract institution-institution collaborations

**Note**: Optional - only if needed for institutional analysis

**Tasks**:
1. Define collaboration metric (shared authors or shared papers)
2. Write query
3. Execute and export

**Dependencies**: P06-T02

**Estimated Duration**: 2-3 hours (if needed)

---

### Network Object Construction

#### P06-T04: Load Co-Author Network into NetworkX
**Status**: Not Started
**Complexity**: Moderate (3)
**Priority**: High

**Description**: Load co-author edge list into NetworkX graph object

**Tasks**:
1. Write network loading script:
   ```python
   import networkx as nx
   import pandas as pd

   # Load edges
   edges = pd.read_parquet('coauthor_edgelist.parquet')

   # Create graph
   G = nx.Graph()

   # Add edges with weights
   for _, row in edges.iterrows():
       G.add_edge(
           row['author1_id'],
           row['author2_id'],
           weight=row['paper_count'],
           first_year=row['first_year'],
           last_year=row['last_year']
       )
   ```
2. Add node attributes (gender, career_stage, etc. from authors table)
3. Test on sample (10k nodes)
4. Load full network
5. Compute basic stats (node count, edge count, density)
6. Save network (pickle format for reuse)

**Inputs**:
- Co-author edge list (P06-T01)
- Author attributes (authors table: gender, career_stage, works_count, etc.)

**Outputs**:
- NetworkX graph object: `06_network_building/networks/coauthor_network_full.pkl.gz`
- Includes: all nodes with attributes, all edges with weights
- Loading script: `06_network_building/load_network.py`
- Basic stats report: `06_network_building/network_basic_stats.md`

**Acceptance Criteria**:
- Network loads successfully
- Node count matches expected (~2M or ~306k for filtered)
- Edge count matches edge list
- Node attributes correctly attached (spot-check)
- Can query graph (G.degree(), G.neighbors(), etc.)

**Testing**:
```python
# Basic checks
print(f"Nodes: {G.number_of_nodes()}")
print(f"Edges: {G.number_of_edges()}")
print(f"Density: {nx.density(G)}")

# Check attributes
sample_node = list(G.nodes())[0]
print(G.nodes[sample_node])  # Should show gender, career_stage, etc.

# Check connectivity
components = list(nx.connected_components(G))
print(f"Connected components: {len(components)}")
print(f"Largest component size: {len(max(components, key=len))}")
```

**Dependencies**: P06-T01, P04-T07 (gender), P04-T12 (career_stage)

**Estimated Duration**: 4-6 hours (includes troubleshooting memory issues)

---

#### P06-T05: Build Tiered Networks (Filtered by Productivity)
**Status**: Not Started
**Complexity**: Moderate (3)
**Priority**: High

**Description**: Build multiple network versions filtered by author productivity

**Tasks**:
1. Define tiers:
   - Tier 0: All authors (2M nodes)
   - Tier 1: Authors with >1 paper (306k nodes)
   - Tier 2: Authors with >5 papers
   - Tier 3: Authors with >10 papers
   - Tier 4: Authors with >20 papers
2. For each tier:
   - Filter nodes based on works_count
   - Create subgraph
   - Compute basic stats
   - Save network
3. Generate tier comparison table

**Inputs**:
- Full network (P06-T04)
- Author works_count attribute

**Outputs**:
- 5 network files:
  - `coauthor_network_all.pkl.gz` (Tier 0)
  - `coauthor_network_gt1.pkl.gz` (Tier 1 - PRIMARY)
  - `coauthor_network_gt5.pkl.gz` (Tier 2)
  - `coauthor_network_gt10.pkl.gz` (Tier 3)
  - `coauthor_network_gt20.pkl.gz` (Tier 4)
- Tier comparison table: `06_network_building/tier_comparison.md`

**Example Comparison Table**:
| Tier | Filter | Nodes | Edges | Density | Largest Component |
|------|--------|-------|-------|---------|-------------------|
| 0    | All    | 2.0M  | 8.5M  | 0.00001 | 1.8M (90%)        |
| 1    | >1 paper | 306k | 4.2M | 0.0001 | 295k (96%)       |
| 2    | >5 papers | 98k | 2.1M | 0.0004 | 96k (98%)        |
| 3    | >10 papers | 52k | 1.3M | 0.0009 | 51k (98%)       |
| 4    | >20 papers | 28k | 0.8M | 0.002  | 27k (99%)        |

**Acceptance Criteria**:
- All 5 networks built and saved
- Tier 1 (>1 paper) designated as PRIMARY network for main analyses
- Comparison table shows expected trends (smaller, denser networks with filtering)

**Testing**:
```python
# Load and compare
tiers = [
    ('all', nx.read_gpickle('coauthor_network_all.pkl.gz')),
    ('gt1', nx.read_gpickle('coauthor_network_gt1.pkl.gz')),
    # etc.
]

for name, G in tiers:
    print(f"{name}: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
```

**Dependencies**: P06-T04

**Estimated Duration**: 3-4 hours

---

#### P06-T06: Load Author-Institution Network
**Status**: Not Started
**Complexity**: Moderate (3)
**Priority**: Medium

**Description**: Load author-institution bipartite network

**Tasks**:
1. Load edge list (P06-T02)
2. Create bipartite graph (NetworkX supports this)
3. Add node attributes (distinguish author vs. institution nodes)
4. Save network

**Inputs**:
- Author-institution edge list (P06-T02)

**Outputs**:
- Bipartite network: `06_network_building/networks/author_institution_network.pkl.gz`

**Acceptance Criteria**:
- Network bipartite (edges only between authors and institutions, not within)
- Node attributes indicate type (author vs. institution)

**Testing**:
```python
# Check bipartite structure
from networkx.algorithms import bipartite
print(f"Is bipartite: {bipartite.is_bipartite(G)}")
```

**Dependencies**: P06-T02

**Estimated Duration**: 2-3 hours

---

#### P06-T07: Write Phase 06 Summary Documentation
**Status**: Not Started
**Complexity**: Simple (2)
**Priority**: Medium

**Description**: Document Phase 06 completion

**Tasks**:
1. Update `06_network_building/README.md`
2. Create `06_network_building/RESULTS_SUMMARY.md`
3. Update `DECISION_LOG.md`

**Dependencies**: All Phase 06 tasks complete

**Estimated Duration**: 2 hours

---

## PHASE 07: Network Analysis

**Phase Status**: Not Started
**Priority**: CRITICAL PATH
**Dependencies**: Phase 06

### Descriptive Statistics

#### P07-T01: Compute Basic Network Properties
**Status**: Not Started
**Complexity**: Simple (2)
**Priority**: High

**Description**: Compute and report basic network statistics for all tiers

**Metrics**:
- Node count, edge count
- Density
- Connected components (number, size distribution)
- Average degree
- Degree distribution (mean, median, max, quantiles)
- Average clustering coefficient

**Tasks**:
1. Write analysis script
2. Run on all tier networks
3. Generate summary table and plots

**Inputs**:
- All tier networks (P06-T05)

**Outputs**:
- Summary statistics table: `07_network_analysis/basic_stats_all_tiers.md`
- Figures: degree distributions, component size distributions

**Acceptance Criteria**:
- All metrics computed
- Results interpretable (match expectations for social networks)
- Comparison across tiers informative

**Dependencies**: P06-T05

**Estimated Duration**: 2-3 hours

---

#### P07-T02: Analyze Degree Distributions
**Status**: Not Started
**Complexity**: Moderate (3)
**Priority**: High

**Description**: Detailed analysis of degree distributions (power-law? scale-free?)

**Tasks**:
1. Plot degree distributions (log-log scale)
2. Test for power-law fit (using powerlaw package)
3. Compare to other network models (exponential, log-normal)
4. Interpret: is this a scale-free network?

**Inputs**:
- Primary network (Tier 1: >1 paper)

**Outputs**:
- Degree distribution analysis: `07_network_analysis/degree_distribution_analysis.md`
- Figures: log-log plot, fitted distributions

**Acceptance Criteria**:
- Distribution characterized (power-law exponent if applicable)
- Comparison to reference networks
- Interpretation for publication

**Dependencies**: P07-T01

**Estimated Duration**: 3-4 hours

---

### Centrality Measures

#### P07-T03: Compute Degree Centrality
**Status**: Not Started
**Complexity**: Simple (2)
**Priority**: High

**Description**: Compute degree centrality for all nodes

**Tasks**:
1. Compute degree centrality:
   ```python
   degree_centrality = nx.degree_centrality(G)
   ```
2. Save to CSV (author_id, degree_centrality)
3. Compute summary stats by gender

**Inputs**:
- Primary network (Tier 1)

**Outputs**:
- Centrality scores: `07_network_analysis/centrality/degree_centrality.csv`
- Summary by gender: `07_network_analysis/centrality/degree_centrality_by_gender.md`

**Acceptance Criteria**:
- All nodes have centrality score
- Gender comparison shows preliminary H1 result

**Dependencies**: P06-T05

**Estimated Duration**: 1-2 hours

---

#### P07-T04: Compute PageRank
**Status**: Not Started
**Complexity**: Simple (2)
**Priority**: High

**Description**: Compute PageRank centrality

**Tasks**:
1. Compute PageRank:
   ```python
   pagerank = nx.pagerank(G, weight='weight')
   ```
2. Save and summarize by gender

**Outputs**:
- `07_network_analysis/centrality/pagerank.csv`
- Summary by gender

**Dependencies**: P06-T05

**Estimated Duration**: 1-2 hours

---

#### P07-T05: Compute Eigenvector Centrality
**Status**: Not Started
**Complexity**: Simple (2)
**Priority**: High

**Description**: Compute eigenvector centrality

**Tasks**:
1. Compute eigenvector centrality (may fail if network disconnected - use largest component)
2. Save and summarize by gender

**Outputs**:
- `07_network_analysis/centrality/eigenvector_centrality.csv`

**Dependencies**: P06-T05

**Estimated Duration**: 1-2 hours

---

#### P07-T06: Compute Clustering Coefficient
**Status**: Not Started
**Complexity**: Simple (2)
**Priority**: High

**Description**: Compute local clustering coefficient for all nodes

**Tasks**:
1. Compute clustering:
   ```python
   clustering = nx.clustering(G, weight='weight')
   ```
2. Save and summarize by gender

**Outputs**:
- `07_network_analysis/centrality/clustering_coefficient.csv`

**Dependencies**: P06-T05

**Estimated Duration**: 1-2 hours

---

#### P07-T07: Compute Katz Centrality
**Status**: Not Started
**Complexity**: Moderate (3)
**Priority**: Medium

**Description**: Compute Katz centrality (if feasible for network size)

**Tasks**:
1. Attempt Katz centrality computation
2. If fails due to size, compute on largest component or Tier 2 network

**Outputs**:
- `07_network_analysis/centrality/katz_centrality.csv` (if feasible)

**Dependencies**: P06-T05

**Estimated Duration**: 2-3 hours

---

#### P07-T08: Assess Feasibility of Closeness/Betweenness
**Status**: Not Started
**Complexity**: Simple (2)
**Priority**: Medium

**Description**: Determine if closeness and betweenness centrality are computationally feasible

**Tasks**:
1. Check network size (Tier 1: ~306k nodes)
2. Test closeness on sample (1000 nodes) - estimate time for full network
3. Test betweenness on sample - estimate time
4. Decide:
   - Closeness: compute if estimated time <1 day
   - Betweenness: likely skip (too slow for 300k+ nodes)
5. Document decision

**Outputs**:
- Feasibility report: `07_network_analysis/centrality/closeness_betweenness_feasibility.md`

**Acceptance Criteria**:
- Clear go/no-go decision
- Rationale documented

**Dependencies**: P06-T05

**Estimated Duration**: 1-2 hours

---

#### P07-T09: Compute Closeness Centrality (if feasible)
**Status**: Not Started
**Complexity**: Moderate (3)
**Priority**: Low

**Description**: Compute closeness centrality if P07-T08 deems feasible

**Conditional**: Only if P07-T08 says yes

**Tasks**:
1. Compute closeness on largest connected component
2. May take hours - run overnight

**Outputs**:
- `07_network_analysis/centrality/closeness_centrality.csv` (if computed)

**Dependencies**: P07-T08

**Estimated Duration**: Variable (hours to day)

---

#### P07-T10: Combine All Centrality Measures
**Status**: Not Started
**Complexity**: Simple (2)
**Priority**: High

**Description**: Combine all centrality measures into single dataframe

**Tasks**:
1. Merge all centrality CSVs (author_id as key)
2. Add author attributes (gender, career_stage, works_count, etc.)
3. Create master centrality dataframe
4. Save for hypothesis testing

**Inputs**:
- All centrality CSVs (P07-T03 through P07-T09)
- Author attributes (authors table)

**Outputs**:
- Master centrality file: `07_network_analysis/centrality/all_centrality_measures.parquet`
- Includes columns: author_id, degree_centrality, pagerank, eigenvector_centrality, clustering, gender, career_stage, works_count, cited_by_count, etc.

**Acceptance Criteria**:
- All authors in network have centrality scores
- Attributes correctly joined
- No missing data (except legitimate NULLs like Unknown gender)

**Dependencies**: P07-T03 through P07-T09

**Estimated Duration**: 1-2 hours

---

#### P07-T11: Preliminary Gender Comparison (Preview of H1)
**Status**: Not Started
**Complexity**: Moderate (3)
**Priority**: High

**Description**: Preliminary analysis of gender differences in centrality

**Tasks**:
1. For each centrality measure:
   - Compare M vs F (t-test)
   - Plot distributions (violin plot)
   - Compute effect size (Cohen's d)
2. Generate preliminary report (NOT final hypothesis test, just exploratory)

**Inputs**:
- Master centrality file (P07-T10)

**Outputs**:
- Preliminary gender analysis: `07_network_analysis/preliminary_gender_analysis.md`
- Figures: centrality distributions by gender

**Acceptance Criteria**:
- All centrality measures compared by gender
- Statistical tests run (but interpret cautiously - no controls yet)
- First glimpse of H1 result (are there gender gaps?)

**Dependencies**: P07-T10

**Estimated Duration**: 3-4 hours

---

### Community Detection

#### P07-T12: Run Leiden Algorithm for Community Detection
**Status**: Not Started
**Complexity**: Moderate (3)
**Priority**: Medium

**Description**: Identify communities in the network

**Tasks**:
1. Run Leiden algorithm (using igraph or leidenalg package)
2. Assign community IDs to all nodes
3. Compute community sizes
4. Characterize communities (gender composition, topics, productivity)

**Inputs**:
- Primary network (Tier 1)

**Outputs**:
- Community assignments: `07_network_analysis/communities/community_assignments.csv`
- Community characterization report: `07_network_analysis/communities/community_analysis.md`

**Acceptance Criteria**:
- All nodes assigned to community
- Community sizes reasonable (not one giant community or all singletons)
- Communities interpretable (distinct characteristics)

**Testing**:
```python
# Check community size distribution
community_sizes = pd.Series(communities).value_counts()
print(community_sizes.describe())
```

**Dependencies**: P06-T05

**Estimated Duration**: 3-4 hours

---

#### P07-T13: Write Phase 07 Summary Documentation
**Status**: Not Started
**Complexity**: Simple (2)
**Priority**: Medium

**Description**: Document Phase 07 completion

**Dependencies**: All Phase 07 tasks complete

**Estimated Duration**: 2 hours

---

## PHASE 08-12: Remaining Phases

[Due to length constraints, I'll summarize remaining phases at high level. Each would be broken down into 10-15 detailed tasks similar to above]

### Phase 08: ERGM Analysis (3-4 weeks)
- Configuration model baseline
- Subnetwork sampling (10-20 networks)
- ERGM fitting and testing
- Aggregation and interpretation

### Phase 09: Subnetwork Analysis (3-4 weeks)
- Ego network extraction (key authors + sample)
- Ego network metrics
- Temporal network construction
- Longitudinal tracking
- (Stretch) Interactive ego network tool

### Phase 10: Gender Hypothesis Testing (4-6 weeks) ⭐ PRIMARY
- H1: Centrality gaps (t-tests, regression, effect sizes)
- H2: Institutional stratification (chi-square, logistic regression)
- H3: Author typology (clustering, gender × type tests)
- H4: Temporal trends (time series, change points)
- H5: Career trajectories (longitudinal models)
- H6: Collaboration patterns (homophily, ego network comparisons)
- Publication-ready tables and figures

### Phase 11: Geography Analysis (2-3 weeks)
- Geographic extension of H1-H6
- Cross-country comparisons

### Phase 12: KOL Identification (2-3 weeks)
- Define KOL criteria
- Identify current/historical KOLs
- Model trajectories
- Predict emerging KOLs

### Phase 99: Visualization (Ongoing + 2 weeks)
- Theme development
- Publication figures
- (Stretch) Interactive dashboard

---

## TASK DEPENDENCY GRAPH

```
Phase 03: Data Pipeline
├── P03-T01 (Monitor works loading) [IN PROGRESS]
├── P03-T02 (Parse relationships) [BLOCKED by T01] 🔴 CRITICAL
├── P03-T03 (Complete authors) [IN PROGRESS]
├── P03-T04 (Fix column sizes) [BLOCKED by T01]
├── P03-T05 (Design validation) [BLOCKED by T01, T02, T03]
├── P03-T06 (Run validation) [BLOCKED by T05]
├── P03-T07 (Data quality report) [BLOCKED by T01-T03]
└── P03-T08 (Documentation) [BLOCKED by T01-T07]

Phase 04: Author Profiles [BLOCKED by Phase 03]
├── P04-T01 (Test R pipeline) [BLOCKED by P03-T03]
├── P04-T02 (Sample 1000) [BLOCKED by P03-T03]
├── P04-T03 (Run sample inference) [BLOCKED by T01, T02]
├── P04-T04 (Manual validation) [BLOCKED by T03]
├── P04-T05 (Adjust pipeline) [CONDITIONAL, blocked by T04]
├── P04-T06 (Full inference) [BLOCKED by T03/T05]
├── P04-T07 (Write to DB) [BLOCKED by T06]
├── P04-T08 (Report) [BLOCKED by T07]
├── P04-T09 (Define career model) [BLOCKED by P03-T02]
├── P04-T10 (Compute career metrics) [BLOCKED by P03-T02, P03-T03]
├── P04-T11 (Implement career model) [BLOCKED by T09, T10]
├── P04-T12 (Write to DB) [BLOCKED by T11]
└── P04-T13 (Documentation) [BLOCKED by all P04 tasks]

Phase 05: Corpus [BLOCKED by Phase 03, 04]
├── P05-T01 (Query framework) [BLOCKED by P03-T01, T02]
├── P05-T02 (Identify topics) [BLOCKED by P03-T02]
├── P05-T03 (Text search) [BLOCKED by T01]
├── P05-T04 (Topic search) [BLOCKED by T01, T02]
├── P05-T05 (Journal filter) [BLOCKED by T01]
├── P05-T06 (Compare methods) [BLOCKED by T03, T04, T05]
├── P05-T07 (Manual validation) [BLOCKED by T06]
├── P05-T08 (Refine query) [CONDITIONAL, blocked by T07]
├── P05-T09 (Create corpus table) [BLOCKED by T07/T08]
├── P05-T10 (Corpus statistics) [BLOCKED by T09]
├── P05-T11 (Historical quality) [BLOCKED by T09]
└── P05-T12 (Documentation) [BLOCKED by all P05 tasks]

Phase 06: Networks [BLOCKED by Phase 05]
Phase 07: Analysis [BLOCKED by Phase 06]
Phase 08: ERGM [BLOCKED by Phase 07]
Phase 09: Subnetworks [BLOCKED by Phase 07]
Phase 10: Hypothesis Testing [BLOCKED by Phase 09] ⭐
```

---

## CURRENT IMMEDIATE NEXT STEPS (Priority Order)

### Critical Path Tasks (Must Do Now)
1. **P03-T02: Execute Works Relationships Parsing** 🔴 BLOCKING EVERYTHING
   - This populates authorship table
   - Required for ALL downstream work
   - Estimate: 4-8 hours

2. **P03-T01: Monitor works table loading** (background)
   - Check daily
   - Note completion

3. **P03-T03: Monitor authors table loading** (background)
   - Check daily

### Next Priority (After Critical Path)
4. **P03-T05 + P03-T06: Database Validation**
   - Design and run validation suite
   - Confirm >95% accuracy
   - Estimate: 6-9 hours

5. **P04-T01 through P04-T08: Gender Inference**
   - Test, validate, run full pipeline
   - Estimate: 15-20 hours total

6. **P04-T09 through P04-T12: Career Stage Model**
   - Define, compute, implement
   - Estimate: 12-15 hours

### Then Proceed Sequentially
- Phase 05 (Corpus): ~25-30 hours
- Phase 06 (Networks): ~20-25 hours
- Phase 07 (Analysis): ~25-30 hours
- Phases 08-10 (ERGM, Subnetworks, Hypotheses): ~60-80 hours

---

## EFFORT ESTIMATES BY PHASE

| Phase | Tasks | Estimated Hours | Estimated Weeks (Full-Time) |
|-------|-------|-----------------|------------------------------|
| Phase 03 (remaining) | 8 | 30-40 | 1-2 |
| Phase 04 | 13 | 35-45 | 1.5-2 |
| Phase 05 | 12 | 25-35 | 1-1.5 |
| Phase 06 | 7 | 20-30 | 1-1.5 |
| Phase 07 | 13 | 25-35 | 1-1.5 |
| Phase 08 | ~12 | 30-40 | 1.5-2 |
| Phase 09 | ~12 | 25-35 | 1-1.5 |
| Phase 10 | ~15 | 40-50 | 2-2.5 |
| Phase 11 | ~10 | 20-30 | 1-1.5 |
| Phase 12 | ~8 | 15-25 | 1 |
| **TOTAL** | **~110 tasks** | **265-365 hours** | **13-18 weeks full-time** |

**For part-time work (20 hours/week)**: 13-18 months

---

**END OF TASKS DOCUMENT**

*This is a living document. Mark tasks complete as you finish them. Add new tasks as needed. Update estimates based on actual experience.*
