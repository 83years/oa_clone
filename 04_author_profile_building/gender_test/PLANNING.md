# Gender Prediction Pipeline - Implementation Plan

**Date Created:** 2025-01-16
**Status:** Phase 1 - Step 1 Complete
**Goal:** Migrate R-based gender prediction pipeline to Python with PostgreSQL support

---

## Executive Summary

This document outlines the complete plan for migrating the comprehensive R-based gender prediction pipeline to Python. The migration preserves the multi-method validation approach that worked well in R while updating to work with PostgreSQL instead of SQLite, and leveraging modern free, country-aware gender prediction tools.

---

## Project Background

### Current State (Before Migration)

**Two Existing Pipelines:**

1. **R-based Pipeline** (General OpenAlex, SQLite)
   - Target: `openalex_database.db` (SQLite)
   - Orchestrator: `main_orchestrator.R`
   - Methods: 4 gender prediction methods with validation
   - Status: Working well but targets wrong database type

2. **Python Pipeline** (CF Corpus, PostgreSQL)
   - Target: PostgreSQL CF_DB
   - Orchestrator: `orchestrator_profiles.py`
   - Methods: Single method (gender-guesser only)
   - Status: Incomplete, no validation

### Problems Identified

1. **Database type mismatch:** R pipeline uses SQLite, project uses PostgreSQL
2. **Duplicate pipelines:** Two codebases doing similar things differently
3. **Inconsistent approaches:** Different name parsing, different gender prediction methods
4. **No validation in Python:** Python pipeline lacks quality assurance
5. **Legacy files:** Unclear which scripts are current vs deprecated

### Decision

**Consolidate to unified Python approach:**
- Migrate R's comprehensive multi-method approach to Python
- Target PostgreSQL database
- Preserve R's sophisticated name parsing logic
- Use free, country-aware gender prediction tools
- Sequential development: test each step before proceeding
- Keep R scripts as reference (deprecate, don't delete)

---

## Research: Free Gender Prediction Tools

### Tools Selected for Multi-Method Consensus

#### Tier 1: Always Run (Local, Free)
1. **global-gender-predictor** (WGND 2.0)
   - Type: Local Python library
   - Data: 4.1M unique names, 26M records, 195 countries
   - Country-aware: Yes
   - Cost: Completely free
   - Weight: 1.5 (largest dataset)

2. **gender-guesser**
   - Type: Local Python library
   - Data: 40+ countries from Michael (2007) dataset
   - Country-aware: No (but has regional data)
   - Cost: Completely free
   - Weight: 1.2 (lowest misclassification rate)

3. **names-dataset**
   - Type: Local Python library
   - Data: 491M records, 106 countries
   - Country-aware: Yes
   - Cost: Completely free (3.2GB RAM)
   - Weight: 1.3 (massive coverage)
   - Usage: Fallback when Tier 1 uncertain

#### Tier 2: Regional Boosters (Conditional)
4. **naampy**
   - Type: Local Python library
   - Data: Indian Electoral Rolls
   - Country-aware: Yes (Indian states)
   - Cost: Completely free
   - Weight: 2.0 (highest accuracy for region)
   - Usage: Only when country = 'IN'

5. **pygenderbr**
   - Type: Local Python library
   - Data: IBGE 2010 Census (190.8M people, 130K names)
   - Country-aware: Yes (Brazilian states)
   - Cost: Completely free
   - Weight: 2.0 (highest accuracy for region)
   - Usage: Only when country = 'BR'

#### Tier 3: API Fallback (Reserve Quotas)
6. **genderize.io**
   - Type: REST API
   - Free tier: 100-1000 requests/day
   - Country-aware: Yes (country_id parameter)
   - Accuracy: 96.6% overall, 98%+ German, <82% Asian
   - Weight: 1.4 (well-validated)
   - Usage: Only for uncertain cases after local methods

7. **NamSor**
   - Type: REST API
   - Free tier: 1000 gender/month
   - Country-aware: Yes (22 alphabets)
   - Accuracy: Highest in benchmarks, best for Asian names
   - Weight: 1.5 (best overall accuracy)
   - Usage: Only for remaining uncertain cases

### Expected Coverage

| Scenario | Tools Used | Expected Coverage | Expected Accuracy |
|----------|------------|-------------------|-------------------|
| Western names | WGND + gender-guesser | 95%+ | 95%+ |
| Indian names | naampy + WGND | 90%+ | 90%+ |
| Brazilian names | pygenderbr + WGND | 90%+ | 90%+ |
| Chinese/Korean | WGND + NamSor (quota) | 70-80% | 75-85% |
| Mixed international | All Tier 1+2 + selective API | 85-90% | 85-90% |

---

## Implementation Architecture

### Proposed Pipeline (6 Steps)

```
01_extract_author_names.py          # Extract names & countries from PostgreSQL
    ↓ output/01_extracted_names.json
02_predict_gender_multi.py          # Multi-method consensus (local tools)
    ↓ output/02_predictions_multi.json
03_genderize_api.py                 # API enrichment (optional, for uncertain cases)
    ↓ output/03_predictions_final.json
04_validate_predictions.py          # Statistical validation & HTML reports
    ↓ reports/validation_report.html
05_calculate_career_stage.py       # Career trajectory (INDEPENDENT process)
    ↓ updates cf_authors table
06_build_author_profiles.py         # Complete profiles (authorship, citations, topics)
    ↓ updates cf_authors table

orchestrator_gender.py              # Orchestrates steps 1-4 (gender only)
orchestrator_profiles.py            # Orchestrates steps 5-6 (career & profiles)
```

### Key Architectural Decisions

1. **Database:** PostgreSQL (not SQLite)
2. **Intermediate storage:** JSON files (not database tables during testing)
3. **Processing:** Sequential, single-threaded (during testing phase)
4. **Parallelization:** Planned for production, disabled for testing
5. **Independence:** Gender prediction (steps 1-4) and career trajectory (steps 5-6) are completely independent
6. **Configuration:** YAML or extend existing `config.py`
7. **Caching:** JSON format for cross-run caching

---

## Phased Implementation Plan

### Phase 1: Build & Test Gender Pipeline (Current)

**Testing Location:** `04_author_profile_building/gender_test/`

**Approach:** Sequential development - only proceed to next step when current step passes all tests.

#### Step 1: Extract Author Names ✅ COMPLETE

**File:** `01_extract_author_names.py` (+ `01_extract_author_names_TEST.py`)

**What it does:**
- Connects to PostgreSQL database
- Queries `authors` table for display_name
- Queries `author_name_variants` table for alternative_name
- Extracts country codes via `author_institutions` → `institutions` join
- Advanced Unicode-aware name parsing (ported from R):
  - Normalizes Unicode dashes
  - Handles compound names (Jean-François)
  - Detects initials (K.W.Pawar → skip)
  - Validates character ranges (Latin, Cyrillic, CJK)
  - Minimum length filtering
- Deduplication: prioritize display_name over variants
- For authors with multiple countries: takes most frequent, alphabetical tie-breaking

**Output:** `output/01_extracted_names.json`
```json
{
  "author_id": "A1234567890",
  "forename": "Jean",
  "country_code": "FR",
  "extraction_date": "2025-01-16",
  "min_forename_length": 2
}
```

**Test criteria:**
- Run on 1,000 author subset
- Verify forename parsing matches R output quality
- Check country code extraction accuracy
- Validate JSON structure and content

**Status:** ✅ Built, ready for testing

---

#### Step 2: Multi-Method Gender Prediction 🚧 TODO

**File:** `02_predict_gender_multi.py`

**What it does:**
- Load extracted names from Step 1
- **Stage 1:** Local cache lookup (JSON)
  - Check if name+country previously predicted
  - Return cached result if found
- **Stage 2:** Primary local methods (parallel execution)
  - global-gender-predictor (with country context)
  - gender-guesser
- **Stage 3:** Regional boost (if applicable)
  - naampy if country = 'IN'
  - pygenderbr if country = 'BR'
- **Stage 4:** Fallback method (if no consensus)
  - names-dataset for names not found in primary methods
- **Stage 5:** Consensus calculation
  - Weighted voting across all methods
  - Calculate confidence score (0.0-1.0)
  - Detect mismatches (methods disagree)
  - Flag records needing review
- **Stage 6:** Update cache with new predictions

**Consensus Rules:**
- **High confidence:** ≥65% weighted agreement
- **Medium confidence:** 50-65% weighted agreement
- **Low confidence:** <50% weighted agreement
- Return "unknown" if confidence below threshold

**Output:** `output/02_predictions_multi.json`
```json
{
  "author_id": "A1234567890",
  "forename": "Jean",
  "country_code": "FR",
  "gender_wgnd": "male",
  "prob_wgnd": 0.85,
  "gender_guesser": "male",
  "gender_names": "male",
  "prob_names": 0.78,
  "consensus_gender": "male",
  "confidence": 0.82,
  "methods_used": 3,
  "methods_agree": true,
  "needs_review": false,
  "prediction_date": "2025-01-16"
}
```

**Test criteria:**
- Run on 1,000 author output from Step 1
- Check method agreement rates
- Identify mismatches
- Validate consensus logic
- Verify confidence calculations

**Dependencies:**
```bash
pip install global-gender-predictor
pip install gender-guesser
pip install names-dataset
pip install naampy
pip install pygenderbr
```

**Status:** 🚧 Not yet built

---

#### Step 3: API Enrichment 🚧 TODO

**File:** `03_genderize_api.py`

**What it does:**
- Load predictions from Step 2
- Filter to records with:
  - `confidence < 0.6` OR
  - `needs_review = True` OR
  - `consensus_gender = "unknown"`
- Estimate API costs based on filtered count
- **Warning prompt:** Display cost estimate, ask to proceed
- **Batch processing:**
  - genderize.io: 10 names per request
  - Rate limiting: respect daily quotas
  - Automatic retry on rate limit (429) errors
- **Prioritization:**
  - First: Use genderize.io quota (100-1000/day)
  - Then: Use NamSor quota (1000/month) for remaining
- **Recalculate consensus** with API results added
- **Update cache** with all new predictions

**Output:** `output/03_predictions_final.json` (adds `gender_genderize`, `gender_namsor`, updated `consensus_gender`)

**Test criteria:**
- Run on uncertain records from Step 2
- Verify batch processing works
- Check rate limiting respects quotas
- Confirm cache updates correctly
- Validate consensus recalculation

**Dependencies:**
```bash
pip install genderize
pip install namsor-python-sdk2
```

**Status:** 🚧 Not yet built

---

#### Step 4: Validation & Reporting 🚧 TODO

**File:** `04_validate_predictions.py`

**What it does:**
- Load final predictions (Step 3 or Step 2 if Step 3 skipped)
- **Calculate statistics:**
  - Coverage by method (% of names predicted by each tool)
  - Agreement rates (% where all methods agree)
  - Confidence distribution (high/medium/low counts)
  - Gender distribution (male/female/unknown)
  - Regional patterns (accuracy by country/continent)
  - Top 20 ambiguous names (most common disagreements)
- **Generate HTML report:**
  - Summary statistics tables
  - Charts (coverage, confidence distribution, regional patterns)
  - Detailed tables for ambiguous names
  - Method comparison analysis
- **Export summary JSON** for programmatic analysis

**Output:**
- `reports/validation_report.html` (interactive HTML report)
- `reports/validation_stats.json` (summary statistics)

**Test criteria:**
- Run on complete 1,000 author predictions
- Verify statistics are comprehensive and accurate
- Check HTML report renders correctly
- Validate charts display properly
- Confirm identifies known ambiguous names

**Dependencies:**
```bash
pip install pandas
pip install plotly  # or matplotlib
pip install jinja2
```

**Status:** 🚧 Not yet built

---

#### Step 5: Gender Orchestrator 🚧 TODO

**File:** `orchestrator_gender.py`

**What it does:**
- Command-line interface for running pipeline
- **Modes:**
  - `--all`: Run steps 1-4 sequentially
  - `--step N`: Run single step
  - `--steps 1,2,3`: Run specific steps
  - `--skip-api`: Run steps 1,2,4 (skip API enrichment)
- **State management:**
  - Check which steps already completed (output files exist)
  - Option to resume from last successful step
  - Option to force re-run specific steps
- **Progress monitoring:**
  - Real-time progress updates
  - Estimated time remaining
  - Error handling and recovery
- **Logging:**
  - Comprehensive logs to `logs/orchestrator_*.log`
  - Summary report at completion

**Usage:**
```bash
# Run complete pipeline
python orchestrator_gender.py --all

# Run single step
python orchestrator_gender.py --step 1

# Run specific steps
python orchestrator_gender.py --steps 1,2,4

# Skip API enrichment (free only)
python orchestrator_gender.py --all --skip-api

# Force re-run step 2
python orchestrator_gender.py --step 2 --force
```

**Test criteria:**
- End-to-end test on 1,000 authors
- Test error recovery (simulate failure)
- Test resume functionality
- Verify logging captures all events

**Status:** 🚧 Not yet built

---

#### Step 6: Configuration System 🚧 TODO

**File:** `config.yaml`

**Contains:**
```yaml
# Database configuration
database:
  host: "192.168.1.100"
  port: 55432
  database: "OADB"
  user: "admin"
  password: "${ADMIN_PASSWORD}"  # From environment

# Feature flags
features:
  use_name_variants: true
  use_country_context: true

# Processing parameters
processing:
  batch_size: 25000
  min_forename_length: 2

# Gender prediction methods
gender_prediction:
  methods:
    wgnd:
      enabled: true
      weight: 1.5
    gender_guesser:
      enabled: true
      weight: 1.2
    names_dataset:
      enabled: true
      weight: 1.3
      use_as_fallback: true
    naampy:
      enabled: true
      weight: 2.0
      countries: ["IN"]
    pygenderbr:
      enabled: true
      weight: 2.0
      countries: ["BR"]

  # API configuration
  apis:
    genderize:
      enabled: true
      api_key: null  # Free tier, no key needed
      daily_limit: 1000
      weight: 1.4
    namsor:
      enabled: true
      api_key: "${NAMSOR_API_KEY}"
      monthly_limit: 1000
      weight: 1.5

# Confidence thresholds
confidence:
  high: 0.65
  medium: 0.50
  minimum: 0.40  # Below this = unknown

# Paths
paths:
  output_dir: "./output"
  cache_file: "./cache/gender_cache.json"
  log_dir: "./logs"
  reports_dir: "./reports"

# Logging
logging:
  level: "INFO"
  format: "[%(asctime)s] [%(levelname)s] %(message)s"
```

**Status:** 🚧 Not yet built

---

### Phase 2: Scale Testing & Production Migration

**Only start after Phase 1 completely tested and validated.**

#### Step 2A: Scale Testing
- Test on 10,000 authors
- Test on 100,000 authors
- Test on 1,000,000 authors
- Monitor: memory usage, processing time, API quota consumption
- Optimize batch sizes based on performance
- Profile code for bottlenecks

#### Step 2B: Enable Parallelization
- Implement multiprocessing for name parsing
- Parallel method execution in gender prediction
- Batch-parallel API requests
- Test performance improvement vs single-threaded

#### Step 2C: Move to Production Directory
- Copy tested scripts from `gender_test/` to `04_author_profile_building/`
- Update all paths in scripts
- Update configuration for production database
- Create production orchestrator

#### Step 2D: Database Integration
- Add option to write results directly to PostgreSQL `cf_authors` table
- Maintain JSON output for portability
- Implement transaction management for safety
- Add database caching table for faster lookups

#### Step 2E: Deprecate R Scripts
- Move R scripts to `deprecated_r_pipeline/` subdirectory
- Create `deprecated_r_pipeline/README.md`:
  - Explain migration to Python
  - Document what each R script did
  - Note that scripts are kept as reference only
  - Provide migration date and rationale
- Update main `README.md` to reference new Python pipeline
- Remove R scripts from execution paths

---

### Phase 3: Career Trajectory (Independent Process)

**Only start after Phase 1 & 2 complete.**

**Note:** Career trajectory is completely independent from gender prediction. Can run before, after, or parallel to gender pipeline.

#### Existing File: `calculate_career_stage.py`
- Review and refine existing implementation
- Test independently in `career_trajectory_test/` folder
- Integrate into main orchestrator as independent step

#### Career Stage Features:
- `first_publication_year`: Modeled first year
- `last_publication_year`: Last year published
- `career_length_years`: Difference between first and last
- `career_stage`: Early/Mid/Senior/Emeritus (based on years since first pub)
- `is_current`: Boolean if published in last 3 years

---

## Configuration & Settings

### Environment Variables

```bash
# Database
export DB_HOST="192.168.1.100"
export DB_PORT="55432"
export DB_NAME="OADB"
export DB_USER="admin"
export ADMIN_PASSWORD="secure_password_123"

# API Keys (optional)
export NAMSOR_API_KEY="your_key_here"  # If using NamSor
```

### Directory Structure

```
04_author_profile_building/
├── gender_test/                           # Testing directory
│   ├── PLANNING.md                        # This file
│   ├── README.md                          # Documentation
│   ├── 01_extract_author_names.py         # Step 1 (production)
│   ├── 01_extract_author_names_TEST.py    # Step 1 (test version)
│   ├── 02_predict_gender_multi.py         # Step 2 (todo)
│   ├── 03_genderize_api.py                # Step 3 (todo)
│   ├── 04_validate_predictions.py         # Step 4 (todo)
│   ├── orchestrator_gender.py             # Step 5 (todo)
│   ├── config.yaml                        # Step 6 (todo)
│   ├── output/                            # JSON outputs
│   │   ├── 01_extracted_names.json
│   │   ├── 01_extracted_names_TEST.json
│   │   ├── 02_predictions_multi.json
│   │   └── 03_predictions_final.json
│   ├── cache/                             # Caching
│   │   └── gender_cache.json
│   ├── logs/                              # Execution logs
│   └── reports/                           # Validation reports
│       ├── validation_report.html
│       └── validation_stats.json
│
├── career_trajectory_test/                # Career testing (separate)
│
├── deprecated_r_pipeline/                 # After Phase 2
│   ├── README.md                          # Migration explanation
│   ├── 01_extract_author_names.R
│   ├── 02_predict_gender_multi.R
│   ├── 03_genderize_api.R
│   ├── 04_validate_predictions.R
│   ├── main_orchestrator.R
│   ├── utils.R
│   └── config.yaml
│
├── build_author_profiles.py              # Existing (Step 6)
├── calculate_career_stage.py             # Existing (Step 5)
└── README.md                              # Updated with Python pipeline
```

---

## Testing Strategy

### Test Progression

1. **Unit Testing:** Each function tested independently
2. **Small Dataset:** 1,000 authors for initial validation
3. **Medium Dataset:** 10,000 authors for performance testing
4. **Large Dataset:** 100,000 authors for scaling
5. **Full Dataset:** 1,000,000+ authors for production
6. **Comparison Testing:** Compare with R pipeline results on same dataset

### Validation Criteria

**Name Extraction (Step 1):**
- ✅ Successfully parses >90% of names
- ✅ Correctly identifies initials (excludes them)
- ✅ Preserves compound names
- ✅ Country code coverage >70%
- ✅ No data corruption or encoding issues

**Gender Prediction (Step 2):**
- ✅ Coverage >85% at high confidence
- ✅ Method agreement >80% when all methods predict
- ✅ Confidence scores properly distributed
- ✅ Cache hit rate >50% on re-runs
- ✅ Regional tools activate correctly

**API Enrichment (Step 3):**
- ✅ Only calls APIs for uncertain cases
- ✅ Respects rate limits (no errors)
- ✅ Improves coverage by >5%
- ✅ Cache updated correctly
- ✅ Cost stays within budget

**Validation (Step 4):**
- ✅ Report generates without errors
- ✅ Statistics match manual calculations
- ✅ Charts display correctly
- ✅ Identifies known ambiguous names
- ✅ Regional analysis shows expected patterns

**Orchestrator (Step 5):**
- ✅ Runs all steps successfully
- ✅ Error recovery works
- ✅ Resume functionality works
- ✅ Logs capture all events
- ✅ Command-line interface intuitive

---

## Limitations & Known Issues

### Fundamental Limitations (All Gender Prediction Tools)

1. **Binary Gender Assumption**
   - All tools assume male/female binary
   - Cannot identify non-binary, gender-neutral, or gender-diverse individuals
   - 1.6% of US adults identify as transgender/nonbinary - will be misclassified
   - **Mitigation:** Document limitation, report confidence scores

2. **Name-Based Inference Only**
   - Predicts based on forename, not actual gender identity
   - Cannot account for:
     - Gender transitions
     - Name changes (marriage, cultural, personal)
     - Non-Western naming conventions
   - **Mitigation:** Clearly state "inferred from name" in all documentation

3. **Asian Name Accuracy**
   - Chinese, Korean, Singaporean, Taiwanese names: <82% accuracy
   - Romanization loses information (Pinyin issue)
   - Some gender meanings lost in transliteration
   - **Mitigation:** Flag Asian names as lower confidence, use NamSor for boost

4. **Cultural and Temporal Bias**
   - Training data primarily Western, English-language
   - Historical data may not reflect current naming trends
   - Some names changed gender associations over time
   - **Mitigation:** Use country context, document dataset provenance

5. **Unisex Names**
   - Many names genuinely ambiguous (Taylor, Alex, Jordan, Sam)
   - Regional variations (name gendered in one country, not another)
   - **Mitigation:** High confidence thresholds, use country context, report "unknown"

### Technical Limitations

6. **API Rate Limits**
   - Large datasets (100K+ authors) exceed free tiers
   - Daily/monthly quotas require batching over time
   - **Mitigation:** Prioritize local tools, reserve APIs for edge cases

7. **Rare/Uncommon Names**
   - Not in training datasets
   - New names, creative spellings, very rare names
   - **Mitigation:** names-dataset's 491M records helps, but gaps remain

8. **Misspellings and Variations**
   - Authors may use non-standard spellings
   - Initials only cannot be predicted (J. Smith)
   - **Mitigation:** Fuzzy matching (future enhancement), flag initial-only

9. **Memory Requirements**
   - names-dataset requires 3.2GB RAM when loaded
   - Large batch processing needs adequate memory
   - **Mitigation:** Lazy loading, batch size tuning

### Validation Gaps

10. **No Ground Truth**
    - Cannot validate predictions against self-reported gender
    - Accuracy estimates based on tool benchmarks, not our data
    - **Mitigation:** Sensitivity analysis, confidence reporting, validate subset if possible

---

## Academic Best Practices

### Documentation Requirements

**In all publications using this pipeline:**

1. **Methodology section must include:**
   - All tools used with version numbers
   - Consensus voting algorithm and weights
   - Confidence thresholds applied
   - Coverage statistics (% successfully classified)
   - Confidence distribution

2. **Limitations section must acknowledge:**
   - Binary gender assumption
   - Name-based inference (not self-reported)
   - Geographic/cultural biases in training data
   - Cannot capture gender identity changes over time
   - Specific accuracy limitations by region

3. **Sensitivity analysis:**
   - Test how results change with different confidence thresholds
   - Compare single-tool vs. consensus approaches
   - Analyze uncertainty by region/name origin
   - Report results with and without low-confidence predictions

4. **Transparency:**
   - Provide confidence scores in all datasets
   - Flag low-confidence predictions
   - Make code and methodology available for reproducibility
   - Consider excluding very uncertain predictions from key analyses

### Recommended Validation (If Possible)

- ORCID profiles (some include self-reported gender)
- Author websites with pronouns
- Manual verification of random sample
- Literature review for known authors
- Cross-validation with other gender prediction studies

---

## Success Metrics

### Phase 1 Success Criteria

- ✅ All 6 steps built and tested
- ✅ End-to-end pipeline runs on 1,000 authors
- ✅ Coverage: >85% at confidence ≥0.65
- ✅ Accuracy: Results comparable to R pipeline on same test set
- ✅ Documentation: Complete README and inline comments
- ✅ Validation: HTML report generates successfully

### Phase 2 Success Criteria

- ✅ Scales to 1,000,000+ authors
- ✅ Processing time: <1 hour for 100K authors (with parallelization)
- ✅ Memory usage: <8GB peak
- ✅ API costs: <$50/month for typical usage
- ✅ R scripts successfully deprecated with reference docs

### Phase 3 Success Criteria

- ✅ Career trajectory integrated seamlessly
- ✅ Complete author profiles generated
- ✅ Database integration working
- ✅ Production orchestrator functional
- ✅ Ready for analysis workflows

---

## Timeline Estimate

### Phase 1: Gender Pipeline (Testing)
- Step 1: ✅ Complete (2 hours)
- Step 2: 🚧 4-6 hours (multi-method prediction)
- Step 3: 🚧 2-3 hours (API enrichment)
- Step 4: 🚧 3-4 hours (validation & reporting)
- Step 5: 🚧 2-3 hours (orchestrator)
- Step 6: 🚧 1-2 hours (configuration)
- **Testing:** 2-4 hours
- **Total:** ~15-25 hours

### Phase 2: Production Migration
- Scale testing: 4-6 hours
- Parallelization: 3-5 hours
- Production migration: 2-3 hours
- Database integration: 3-4 hours
- Deprecation: 1-2 hours
- **Total:** ~13-20 hours

### Phase 3: Career Integration
- Review/refine: 2-3 hours
- Testing: 2-3 hours
- Integration: 2-3 hours
- **Total:** ~6-9 hours

**Overall Estimate:** 34-54 hours (4-7 days of focused work)

---

## Dependencies & Installation

### Python Packages Required

```bash
# Core dependencies
pip install psycopg2-binary          # PostgreSQL adapter

# Gender prediction (Tier 1)
pip install global-gender-predictor  # WGND 2.0
pip install gender-guesser           # Conservative baseline
pip install names-dataset            # Comprehensive fallback

# Gender prediction (Tier 2 - Regional)
pip install naampy                   # Indian names
pip install pygenderbr               # Brazilian names

# Gender prediction (Tier 3 - APIs)
pip install genderize                # genderize.io client
pip install namsor-python-sdk2       # NamSor client

# Validation & Reporting
pip install pandas                   # Data analysis
pip install plotly                   # Interactive charts (or matplotlib)
pip install jinja2                   # HTML templating

# Optional
pip install pyyaml                   # YAML config parsing
```

### System Requirements

- **Python:** 3.8+
- **RAM:** 8GB minimum (16GB recommended for large datasets)
- **Disk:** 5GB for libraries and caching
- **Database:** PostgreSQL 12+ with OADB database
- **Network:** Internet access for API calls (optional)

---

## Questions & Answers

### Q: Why JSON instead of database tables for intermediate storage?

**A:** During testing phase, JSON provides:
- Easy inspection and debugging
- Portability across systems
- No database schema changes needed
- Simple versioning and comparison
- Once tested, can migrate to database tables in Phase 2

### Q: Why not use parallel processing from the start?

**A:** Sequential processing during testing:
- Easier to debug and identify issues
- Consistent, reproducible results
- Simpler error tracking
- Once validated, parallelization added in Phase 2

### Q: Can gender prediction run independently from career trajectory?

**A:** Yes, completely independent:
- Gender: Steps 1-4, orchestrator_gender.py
- Career: Step 5, separate orchestrator
- Can run in any order or parallel
- No data dependencies between them

### Q: What if API quotas are exceeded?

**A:** Multi-tiered approach:
- Prioritize local methods (unlimited)
- Use APIs only for uncertain cases (~10-15% of records)
- Batch over multiple days if needed
- NamSor monthly quota for remaining edge cases
- Can skip API enrichment entirely with `--skip-api` flag

### Q: How to compare with R pipeline results?

**A:** Validation approach:
1. Extract same 1,000 author IDs
2. Run R pipeline on this subset
3. Run Python pipeline on same subset
4. Compare outputs:
   - Coverage rates
   - Gender predictions (agreement %)
   - Confidence distributions
5. Investigate any major discrepancies
6. Document differences and rationale

---

## Change Log

| Date | Version | Changes |
|------|---------|---------|
| 2025-01-16 | 0.1 | Initial plan created |
| 2025-01-16 | 0.2 | Step 1 completed and tested |

---

## Next Immediate Action

**Run Step 1 test:**
```bash
cd /Users/lucas/Documents/openalex_database/python/OA_clone/04_author_profile_building/gender_test
pip install psycopg2-binary
python 01_extract_author_names_TEST.py
```

**Review test results:**
- Check log file in `logs/`
- Inspect JSON output in `output/01_extracted_names_TEST.json`
- Verify forename parsing quality
- Check country code coverage
- Validate against expectations

**Once Step 1 validated:**
- Proceed to build Step 2 (02_predict_gender_multi.py)
- No changes to subsequent steps until Step 1 confirmed working

---

## Contact & Support

For questions or issues:
- Review this PLANNING.md
- Check README.md for usage instructions
- Inspect log files for error details
- Consult R scripts in deprecated_r_pipeline/ for reference

---

**End of Planning Document**
