# Quick Start Guide

Get your gender prediction pipeline running in 5 minutes!

## Prerequisites

### 1. Install R Packages

```r
install.packages(c(
  "DBI", "RSQLite", "dplyr", "stringr", "tidyr",
  "purrr", "jsonlite", "yaml", "gender", "reticulate",
  "httr", "ggplot2"
))
```

### 2. Install Python Package

```bash
pip install gender-guesser
```

### 3. Set API Key (Optional for Step 3)

```bash
# Add to ~/.Renviron
echo 'GENDERIZE_API_KEY=your_key_here' >> ~/.Renviron
```

Or copy `.env.example` to `.env` and add your key.

## Configuration

### 1. Update Database Path

Edit `config.yaml`:

```yaml
database:
  path: "your_database.db"  # ← Change this to your database path
```

### 2. Verify Table Names

Make sure your database has these tables:
- `authors` (with `author_id`, `display_name`)
- `AUTHOR_NAME_VARIANTS` (optional, with `author_id`, `alternative_name`)
- `institutions` (optional, with `institution_id`, `country_code`)
- `author_institutions` (optional, joining table)

If your table names differ, update them in `config.yaml`:

```yaml
database:
  tables:
    authors: "your_authors_table_name"
    author_name_variants: "your_variants_table_name"
    institutions: "your_institutions_table_name"
    author_institutions: "your_joining_table_name"
```

## Run the Pipeline

### Default Run (Recommended First Time)

Runs Steps 1-2 only (no API costs):

```bash
Rscript main_orchestrator.R
```

This will:
1. ✅ Extract author names from database
2. ✅ Predict genders using 3 free methods
3. ✅ Generate validation report
4. ⏭️ Skip Genderize.io (no API costs)

### Check Results

1. **Validation Report**: `reports/validation_report.html`
   - Open in browser to see coverage, confidence, regional analysis

2. **Predictions**: `output/02_predictions_multi.json`
   - Contains all predictions from 3 methods
   - Shows where methods disagree

3. **Logs**: `logs/author_profile_builder.log`
   - Detailed execution log

### Review Mismatches

Look for records where methods disagree:

```r
library(jsonlite)
library(dplyr)

data <- read_json("output/02_predictions_multi.json", simplifyVector = TRUE)

# Show mismatches
mismatches <- data %>%
  filter(has_mismatch) %>%
  count(forename, country_code, mismatch_detail, sort = TRUE)

head(mismatches, 20)
```

### (Optional) Run Genderize.io

After reviewing results, process remaining names:

```bash
# Test with 100 names first
Rscript main_orchestrator.R --steps genderize --max-names 100

# Then run full
Rscript main_orchestrator.R --steps genderize
```

⚠️ **Warning**: This may incur costs beyond 1,000 names/day

## Expected Output

After default run, you should see:

```
✓ Step 1 completed: 150,000 authors extracted
✓ Step 2 completed: 75% coverage from free methods
✓ Step 4 completed: Validation report generated

Output files:
  - output/01_extracted_names.json
  - output/02_predictions_multi.json
  - reports/validation_report.html
  - logs/author_profile_builder.log
```

## Typical Coverage

| Method | Coverage |
|--------|----------|
| Cache | 60-70% |
| Gender R | +10-15% |
| Gender-guesser | +5-10% |
| **Total (free)** | **~75-85%** |
| Genderize.io | +5-10% |
| **Total (with API)** | **~85-95%** |

## Troubleshooting

### "Database file not found"

Update the `database.path` in `config.yaml`

### "gender-guesser not available"

```bash
pip install gender-guesser
```

### "Table not found"

Update table names in `config.yaml` or disable features:

```yaml
features:
  use_name_variants: false    # Skip variants table
  use_country_context: false  # Skip institutions table
```

### "API quota exceeded"

You've hit the free tier limit. Wait 24 hours or upgrade your plan.

## Next Steps

1. ✅ Review validation report
2. ✅ Check mismatch details
3. ✅ Decide if you need Genderize.io
4. ✅ Update database with predictions (see README)

## Getting Help

- Full documentation: `README.md`
- Configuration reference: `config.yaml` (comments)
- Check logs: `logs/author_profile_builder.log`

---

**Ready?** Run this command to start:

```bash
Rscript main_orchestrator.R
```
