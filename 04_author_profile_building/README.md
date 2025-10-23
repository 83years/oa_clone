# Author Profile Builder - Gender Prediction Pipeline

A production-grade, modular R pipeline for predicting author genders from OpenAlex data using multiple prediction methods with comprehensive validation.

## 📋 Overview

This pipeline extracts author names from an OpenAlex database, predicts genders using a multi-tier approach, and provides detailed validation reports.

### Key Features

- **Multi-method prediction**: Cache → Gender R → gender-guesser → Genderize.io
- **Country-aware predictions**: Leverages country context for improved accuracy
- **Mismatch detection**: Flags disagreements between methods for review
- **Comprehensive validation**: Detailed reports on coverage, confidence, and quality
- **Modular architecture**: Run individual steps or full pipeline
- **Production-ready**: Optimized database operations, batching, error handling

## 🏗️ Architecture

```
04_author_profile_building/
├── config.yaml                      # Configuration file
├── utils.R                          # Utility functions
├── main_orchestrator.R              # Main entry point
├── 01_extract_author_names.R        # Step 1: Name extraction
├── 02_predict_gender_multi.R        # Step 2: Multi-method prediction
├── 03_genderize_api.R               # Step 3: Genderize.io API
├── 04_validate_predictions.R        # Step 4: Validation & reporting
├── cache/                           # Genderize.io cache
├── output/                          # Intermediate JSON files
├── logs/                            # Log files
└── reports/                         # Validation reports
```

## 📦 Requirements

### R Packages

```r
install.packages(c(
  "DBI",
  "RSQLite",
  "dplyr",
  "stringr",
  "tidyr",
  "purrr",
  "jsonlite",
  "yaml",
  "gender",
  "reticulate",
  "httr",
  "ggplot2"
))
```

### Python Packages

```bash
pip install gender-guesser
```

### API Keys

Set your Genderize.io API key as an environment variable:

```bash
export GENDERIZE_API_KEY="your_api_key_here"
```

Or add to your `~/.Renviron` file:

```
GENDERIZE_API_KEY=your_api_key_here
```

## 🚀 Quick Start

### 1. Configure the Pipeline

Edit `config.yaml` to set your database path and preferences:

```yaml
database:
  path: "path/to/your/openalex_database.db"
```

### 2. Run the Default Pipeline

Run extraction, prediction, and validation (skips Genderize.io):

```bash
Rscript main_orchestrator.R
```

### 3. Review Results

Check the validation report:
- HTML report: `reports/validation_report.html`
- Log file: `logs/author_profile_builder.log`
- Predictions: `output/02_predictions_multi.json`

### 4. (Optional) Run Genderize.io

After reviewing mismatches, process remaining names:

```bash
Rscript main_orchestrator.R --steps genderize
```

## 📖 Detailed Usage

### Running Specific Steps

```bash
# Run only extraction
Rscript main_orchestrator.R --steps extract

# Run extraction and prediction
Rscript main_orchestrator.R --steps extract,predict

# Run validation only (on existing results)
Rscript main_orchestrator.R --steps validate

# Run full pipeline including Genderize.io
Rscript main_orchestrator.R --steps all
```

### Testing with Limited Data

Test Genderize.io with 100 names:

```bash
Rscript main_orchestrator.R --steps genderize --max-names 100
```

### Using Custom Config

```bash
Rscript main_orchestrator.R --config my_custom_config.yaml
```

### Command Line Options

```
--config <path>       Path to config file (default: config.yaml)
--steps <steps>       Comma-separated steps: extract, predict, genderize, validate, all
--skip-genderize      Skip Genderize.io API call
--max-names <n>       Limit Genderize.io to N names
--help, -h            Show help message
```

## 🔄 Pipeline Steps

### Step 1: Extract Author Names

**Script**: `01_extract_author_names.R`

**What it does**:
- Reads `author_id` and `display_name` from `authors` table
- Reads `author_id` and `alternative_name` from `AUTHOR_NAME_VARIANTS` table
- Extracts country codes from `institutions` via `author_institutions`
- Parses forenames using advanced Unicode-aware name parsing
- Outputs: `output/01_extracted_names.json`

**Key features**:
- Handles compound names (e.g., Jean-François)
- Detects and skips initials (e.g., K.W.Pawar)
- Supports international characters (Latin, Cyrillic, CJK)
- Deduplicates: prioritizes display_name over variants

### Step 2: Multi-Method Gender Prediction

**Script**: `02_predict_gender_multi.R`

**What it does**:
- Runs **all three methods** on **every forename-country combination**:
  1. **Cache lookup** (instant, free)
  2. **Gender R package** (SSA/IPUMS, free)
  3. **gender-guesser** (Python, free)
- Adds separate columns for each method's prediction
- Detects and flags mismatches where methods disagree
- Outputs: `output/02_predictions_multi.json`

**Key features**:
- All methods run in parallel (not cascading)
- Country-aware predictions (gender-guesser)
- Confidence scores for each method
- Mismatch detection and reporting

### Step 3: Genderize.io API (On-Demand)

**Script**: `03_genderize_api.R`

**What it does**:
- Processes names without consensus from Step 2
- Calls Genderize.io API with country context
- Updates cache with new results
- Outputs: `output/03_predictions_final.json`

**Important**:
- Only run after reviewing Step 2 results
- May incur costs beyond free tier (1000 names/day)
- Batches requests for efficiency
- Automatic retry on rate limits

**Cost estimation**:
- Free: 1,000 names/day
- Paid: ~$0.01 per name beyond free tier

### Step 4: Validate Predictions

**Script**: `04_validate_predictions.R`

**What it does**:
- Calculates comprehensive statistics
- Analyzes coverage, confidence, regional patterns
- Identifies ambiguous names and quality issues
- Generates HTML report (optional)
- Outputs: `reports/validation_report.html`

**Validation metrics**:
- Coverage rate by method
- Consensus predictions
- Method agreement rate
- Confidence distribution
- Regional analysis
- Top ambiguous names

## 📊 Output Files

### JSON Format

Each step outputs JSON files with cumulative results:

**Step 1** (`01_extracted_names.json`):
```json
{
  "author_id": "A1234567890",
  "forename": "Jean",
  "country_code": "FR",
  "extraction_date": "2025-01-15"
}
```

**Step 2** (`02_predictions_multi.json`):
```json
{
  "author_id": "A1234567890",
  "forename": "Jean",
  "country_code": "FR",
  "gender_cache": "M",
  "prob_cache": 0.85,
  "gender_r": "M",
  "prob_r": 0.72,
  "gender_guesser": "M",
  "prob_guesser": 0.85,
  "methods_predicted": 3,
  "unique_genders": 1,
  "has_mismatch": false,
  "consensus_gender": "M",
  "needs_review": false
}
```

**Step 3** (`03_predictions_final.json`):
- Same as Step 2, plus:
  - `gender_genderize`: Genderize.io prediction
  - `prob_genderize`: Genderize.io probability

## ⚙️ Configuration

### Database Tables

The pipeline expects these tables:

```sql
-- Authors table
CREATE TABLE authors (
  author_id TEXT PRIMARY KEY,
  display_name TEXT
);

-- Name variants (optional)
CREATE TABLE AUTHOR_NAME_VARIANTS (
  author_id TEXT,
  alternative_name TEXT
);

-- Institutions
CREATE TABLE institutions (
  institution_id TEXT PRIMARY KEY,
  country_code TEXT
);

-- Author-institution relationships
CREATE TABLE author_institutions (
  author_id TEXT,
  institution_id TEXT
);
```

### Customizing Regions

Edit `config.yaml` to define regions for analysis:

```yaml
validation:
  regions:
    Asia:
      - "CN"  # China
      - "JP"  # Japan
      - "KR"  # South Korea
    Western:
      - "US"  # United States
      - "GB"  # United Kingdom
      - "CA"  # Canada
```

### Performance Tuning

```yaml
processing:
  batch_size: 25000              # Records per batch
  update_batch_size: 10000       # Database update batch size
  gc_frequency: 5                # Garbage collection frequency
```

## 🔍 Reviewing Mismatches

After Step 2, review mismatches before proceeding to Genderize.io:

```r
# Load predictions
library(jsonlite)
data <- read_json("output/02_predictions_multi.json", simplifyVector = TRUE)

# Filter mismatches
mismatches <- data %>%
  filter(has_mismatch) %>%
  select(forename, country_code, gender_cache, gender_r, gender_guesser, mismatch_detail)

# View top ambiguous names
mismatches %>%
  count(forename, mismatch_detail, sort = TRUE) %>%
  head(20)
```

## 📈 Expected Performance

### Coverage Rates

| Method | Expected Coverage |
|--------|------------------|
| Cache | 60-70% |
| Gender R | 15-20% additional |
| Gender-guesser | 5-10% additional |
| Genderize.io | 5-10% additional |
| **Total** | **85-95%** |

### Processing Speed

For 1 million authors:

| Step | Estimated Time |
|------|----------------|
| Step 1: Extract | 5-10 minutes |
| Step 2: Predict | 10-15 minutes |
| Step 3: Genderize | 2-3 hours* |
| Step 4: Validate | 5 minutes |

*Depends on number of uncached names and API rate limits

## 🐛 Troubleshooting

### gender-guesser not found

```bash
pip install gender-guesser
```

If using conda:
```bash
conda install -c conda-forge gender-guesser
```

### Database connection fails

Check your database path in `config.yaml`:
```yaml
database:
  path: "correct/path/to/database.db"
```

### Genderize.io API errors

**402 Payment Required**: You've exceeded your free quota

**429 Too Many Requests**: Rate limited, script will retry automatically

**401 Unauthorized**: Check your API key is set correctly

### Memory issues

Reduce batch size in `config.yaml`:
```yaml
processing:
  batch_size: 10000  # Reduce from 25000
```

## 📝 Best Practices

### 1. Start Without Genderize.io

Run Steps 1-2 first to see coverage from free methods:
```bash
Rscript main_orchestrator.R --skip-genderize
```

### 2. Review Mismatches

Check the validation report before proceeding to Genderize.io

### 3. Test API Calls

Test with limited names first:
```bash
Rscript main_orchestrator.R --steps genderize --max-names 100
```

### 4. Cache Everything

The cache file (`cache/genderize_cache.rds`) saves API calls. Keep it backed up!

### 5. Monitor Logs

Check `logs/author_profile_builder.log` for detailed progress and errors

## 🔐 Security

### API Keys

**Never commit API keys to version control!**

Use environment variables:
```bash
export GENDERIZE_API_KEY="your_key_here"
```

Or add to `~/.Renviron`:
```
GENDERIZE_API_KEY=your_key_here
```

### .gitignore

The following are ignored by git:
- `config.yaml` (if it contains sensitive data)
- `cache/`
- `output/`
- `logs/`
- `reports/`

## 📚 Additional Resources

- **Gender R Package**: https://github.com/ropensci/gender
- **gender-guesser**: https://pypi.org/project/gender-guesser/
- **Genderize.io API**: https://genderize.io/
- **OpenAlex**: https://openalex.org/

## 🤝 Contributing

This is part of the OA_clone project. Follow the coding standards in `CLAUDE.md`.

## 📄 License

[Your license here]

## 🙋 Support

For issues and questions:
1. Check the troubleshooting section
2. Review log files in `logs/`
3. Check the validation report
4. Open an issue in the repository

---

**Last Updated**: January 2025
**Version**: 1.0.0
