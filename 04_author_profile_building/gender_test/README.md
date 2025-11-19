# Gender Prediction Pipeline - Testing Phase

This directory contains the Python-based gender prediction pipeline being developed to replace the R-based approach.

## Status: IN DEVELOPMENT

Currently in Phase 1: Building and testing individual components.

## Pipeline Steps

### Step 1: Extract Author Names ✅ BUILT
**File:** `01_extract_author_names.py`

Extracts forenames and country codes from PostgreSQL database.

**Features:**
- Advanced Unicode-aware name parsing (ported from R)
- Handles compound names (Jean-François)
- Detects and skips initials (K.W.Pawar)
- Supports international characters (Latin, Cyrillic, CJK)
- Extracts country codes from institution affiliations
- Deduplicates (prioritizes display_name over variants)

**Output:** `output/01_extracted_names.json`

**Usage:**
```bash
cd /Users/lucas/Documents/openalex_database/python/OA_clone/04_author_profile_building/gender_test
python 01_extract_author_names.py
```

**Configuration:**
Edit the `Config` class in the script to adjust:
- `USE_NAME_VARIANTS`: Include alternative names (default: True)
- `USE_COUNTRY_CONTEXT`: Extract country codes (default: True)
- `BATCH_SIZE`: Processing batch size (default: 25,000)
- `MIN_FORENAME_LENGTH`: Minimum forename length (default: 2)

### Step 2: Multi-Method Gender Prediction 🚧 TODO
**File:** `02_predict_gender_multi.py` (not yet built)

Multi-method consensus approach:
- global-gender-predictor (WGND 2.0)
- gender-guesser
- names-dataset (fallback)
- Regional tools (naampy, pygenderbr)

**Output:** `output/02_predictions_multi.json`

### Step 3: API Enrichment 🚧 TODO
**File:** `03_genderize_api.py` (not yet built)

API-based enrichment for uncertain cases:
- genderize.io (100-1000/day free)
- NamSor (1000/month free)

**Output:** `output/03_predictions_final.json`

### Step 4: Validation & Reporting 🚧 TODO
**File:** `04_validate_predictions.py` (not yet built)

Quality assurance and HTML report generation.

**Output:** `reports/validation_report.html`

### Step 5: Orchestrator 🚧 TODO
**File:** `orchestrator_gender.py` (not yet built)

Runs all steps sequentially with state management.

## Directory Structure

```
gender_test/
├── README.md                          # This file
├── 01_extract_author_names.py         # Step 1 (built)
├── 02_predict_gender_multi.py         # Step 2 (todo)
├── 03_genderize_api.py                # Step 3 (todo)
├── 04_validate_predictions.py         # Step 4 (todo)
├── orchestrator_gender.py             # Step 5 (todo)
├── config.yaml                        # Configuration (todo)
├── output/                            # JSON outputs
│   ├── 01_extracted_names.json
│   ├── 02_predictions_multi.json
│   └── 03_predictions_final.json
├── logs/                              # Execution logs
└── reports/                           # Validation reports
    └── validation_report.html
```

## Development Approach

1. Build each step individually
2. Test on 1,000 author subset
3. Only proceed to next step when current step passes tests
4. No parallel processing during testing phase
5. Compare results with R pipeline for validation

## Testing

### Test on Small Subset

To test on a limited number of authors, modify the database query in `01_extract_author_names.py`:

```python
# In extract_authors() function, add LIMIT clause:
query = """
    SELECT
        author_id,
        display_name
    FROM authors
    WHERE display_name IS NOT NULL
      AND display_name != ''
    LIMIT 1000  -- Add this line for testing
"""
```

## Dependencies

```bash
# Install required packages
pip install psycopg2-binary  # PostgreSQL adapter

# For Step 2 (not yet built):
pip install global-gender-predictor
pip install gender-guesser
pip install names-dataset
pip install naampy  # For Indian names
pip install pygenderbr  # For Brazilian names

# For Step 3 (not yet built):
pip install genderize
pip install namsor-python-sdk2
```

## Notes

- This pipeline targets PostgreSQL (not SQLite like the R version)
- Uses free, country-aware gender prediction tools
- JSON intermediate storage (not database tables during testing)
- Sequential processing (no parallelization during testing)
- Gender and career trajectory are independent processes
