# Ethnicity Inference Pipeline

This pipeline infers author ethnicity/nationality using five complementary tools and combines their predictions using a weighted consensus algorithm.

## Overview

The pipeline consists of five ethnicity inference tools:

1. **ethnicseer** - Predicts 12 ethnic categories with 84% accuracy
2. **pyethnicity** - US-centric race prediction using advanced ML models
3. **ethnidata** - Nationality/country prediction with regional context (238 countries)
4. **name2nat** - Global nationality prediction (254 nationalities from Wikipedia)
5. **raceBERT** - State-of-the-art transformer-based prediction (86% f1-score)

Results are combined using a consensus algorithm that maps predictions to unified ethnicity categories.

**Note**: name2nat and raceBERT have special dependencies (see Installation section). The pipeline works with any combination of available tools.

## Tools

### 1. ethnicseer (01_infer_ethnicseer.py)

**Predicts**: 12 ethnic categories based on name analysis

**Categories**:
- Chinese (chi)
- English (eng)
- French (frn)
- German (ger)
- Indian (ind)
- Italian (ita)
- Japanese (jap)
- Korean (kor)
- Middle-Eastern (mea)
- Russian (rus)
- Spanish (spa)
- Vietnamese (vie)

**Accuracy**: ~84% on test data

**Output Columns**:
- `ethnicseer_ethnicity` (TEXT): Predicted ethnic category code
- `ethnicseer_confidence` (DOUBLE): Confidence score (0-1)

**Usage**:
```bash
python 01_infer_ethnicseer.py --db path/to/database.duckdb --batch-size 1000
```

### 2. pyethnicity (02_infer_pyethnicity.py)

**Predicts**: 4 US-centric race categories with probabilities

**Categories**:
- Asian
- Black
- Hispanic
- White

**Model**: Advanced ML trained on Florida voter registration data

**Output Columns**:
- `pyethnicity_asian` (DOUBLE): Probability of Asian (0-1)
- `pyethnicity_black` (DOUBLE): Probability of Black (0-1)
- `pyethnicity_hispanic` (DOUBLE): Probability of Hispanic (0-1)
- `pyethnicity_white` (DOUBLE): Probability of White (0-1)

**Usage**:
```bash
python 02_infer_pyethnicity.py --db path/to/database.duckdb --batch-size 100
```

**Note**: Slower than other tools due to ML model overhead. Default batch size is 100.

### 3. ethnidata (03_infer_ethnidata.py)

**Predicts**: Nationality with regional and linguistic context

**Coverage**:
- 238 countries
- 6 major regions (Africa, Americas, Asia, Europe, Middle East, Oceania)
- 72 languages
- 169,197 first names
- 246,537 last names

**Output Columns**:
- `ethnidata_country_code` (TEXT): ISO country code
- `ethnidata_country_name` (TEXT): Full country name
- `ethnidata_region` (TEXT): Geographic region
- `ethnidata_language` (TEXT): Primary language
- `ethnidata_confidence` (DOUBLE): Confidence score (0-1)

**Usage**:
```bash
python 03_infer_ethnidata.py --db path/to/database.duckdb --batch-size 1000
```

### 4. name2nat (04_infer_name2nat.py)

**Predicts**: 254 nationalities from Wikipedia data

**Model**: Bidirectional GRU neural network (Flair NLP library)

**Training Data**: 1.1 million names from Wikipedia (June 2020 dump)

**Accuracy**:
- Top-1: 55.1%
- Top-3: 77.9%
- Top-5: 86.8%

**Output Columns**:
- `name2nat_nationality1` (TEXT): Top nationality prediction
- `name2nat_probability1` (DOUBLE): Probability for top prediction
- `name2nat_nationality2` (TEXT): Second nationality prediction
- `name2nat_probability2` (DOUBLE): Probability for second prediction
- `name2nat_nationality3` (TEXT): Third nationality prediction
- `name2nat_probability3` (DOUBLE): Probability for third prediction

**Usage**:
```bash
python 04_infer_name2nat.py --db path/to/database.duckdb --batch-size 100
```

**Note**: May have dependency conflicts in some environments. If installation fails with dependency errors, you can skip this tool and use the other tools in the pipeline.

### 5. raceBERT (05_infer_racebert.py)

**Predicts**: Race and ethnicity using transformer models

**Model**: RoBERTa transformer (state-of-the-art)

**Performance**: 86% f1-score (4.1% improvement over previous SOTA)

**Race Categories**:
- nh_white: Non-Hispanic White
- nh_black: Non-Hispanic Black
- nh_api: Non-Hispanic Asian/Pacific Islander
- nh_aian: Non-Hispanic American Indian/Alaska Native
- nh_2prace: Non-Hispanic Two or More Races
- hispanic: Hispanic

**Ethnicity Model**: Also provides detailed ethnic group predictions

**Output Columns**:
- `racebert_race` (TEXT): Predicted race category
- `racebert_race_score` (DOUBLE): Confidence score for race
- `racebert_ethnicity` (TEXT): Predicted ethnicity category
- `racebert_ethnicity_score` (DOUBLE): Confidence score for ethnicity

**Usage**:
```bash
# CPU (default)
python 05_infer_racebert.py --db path/to/database.duckdb --batch-size 100

# GPU (if available)
python 05_infer_racebert.py --db path/to/database.duckdb --batch-size 100 --gpu
```

**Requirements**:
- **PyTorch** (visit https://pytorch.org/get-started/locally/ for installation)
- **NOT available for Intel Macs** (works on Apple Silicon, Linux, Windows)
- GPU acceleration recommended for large datasets

**Note**: If PyTorch is not installed, this tool will gracefully skip.

## Consensus Algorithm

The consensus module (`ethnicity_consensus.py`) combines predictions using:

1. **Mapping to Unified Categories**: All tool predictions are mapped to consistent categories
2. **Quality Weights**: Each tool has a base quality weight based on performance
3. **Confidence Multipliers**: Confidence scores multiply the base weights
4. **Context Bonuses**: Tools get bonuses for their areas of expertise

### Unified Ethnicity Categories

The consensus algorithm outputs these categories:

- **East Asian**: Chinese, Japanese, Korean, Mongolian
- **South Asian**: Indian, Pakistani, Bangladeshi, Nepalese, Sri Lankan, Afghan
- **Southeast Asian**: Vietnamese, Thai, Filipino, Indonesian, Malaysian
- **Middle Eastern/North African**: Arab, Iranian, Turkish, North African
- **Hispanic/Latino**: Spanish-speaking Americas and Spain
- **European**: English, French, German, Italian, Russian, and other European
- **Sub-Saharan African**: Sub-Saharan African countries
- **African/African American**: US Black population (from pyethnicity)
- **Oceanian**: Pacific Islander, Australian, New Zealand
- **Other/Mixed**: When predictions are uncertain or mixed

### Tool Weights

Base weights:
- **ethnicseer**: 1.2 (high quality, 84% accuracy)
- **pyethnicity**: 1.0 (good for US names)
- **ethnidata**: 0.8 (granular but requires mapping)
- **name2nat**: 1.0 (global coverage, 254 nationalities)
- **raceBERT**: 1.3 (state-of-the-art, 86% f1-score)

Context bonuses:
- **pyethnicity** gets +30% for African American predictions
- **ethnidata** gets +20% for Middle Eastern/North African and Sub-Saharan African

### Example Consensus Calculation

For **Wei Wang** (Chinese name):

**ethnicseer**: `chi` (Chinese) with 0.999 confidence
- Maps to: East Asian
- Weight: 1.2 × 0.999 = 1.199

**pyethnicity**: Asian=0.9999, Black=0.00002, Hispanic=0.00005, White=0.00003
- Maps to: Asian (generic)
- Weight: 1.0 × 0.9999 = 1.000

**ethnidata**: China, Asia region, 0.95 confidence
- Maps to: East Asian
- Weight: 0.8 × 0.95 = 0.76

**Consensus**: East Asian (66.2% confidence)

## Orchestrator

The orchestrator (`ethnicity_orchestrator.py`) manages the entire pipeline:

```bash
# Run all tools
python ethnicity_orchestrator.py

# Run with custom database
python ethnicity_orchestrator.py --db datasets/my_authors.duckdb

# Skip specific tools (e.g., tools requiring PyTorch)
python ethnicity_orchestrator.py --skip racebert --skip name2nat

# Only run specific tools
python ethnicity_orchestrator.py --only ethnicseer ethnidata pyethnicity
```

### Orchestrator Process

1. Runs each tool script in sequence
2. Logs progress and results for each tool
3. Calculates consensus ethnicity for all authors
4. Stores results in database

### Output Columns

The orchestrator adds these consensus columns:

- `consensus_ethnicity` (TEXT): Final ethnicity category
- `consensus_ethnicity_confidence` (DOUBLE): Confidence score (0-1)
- `consensus_ethnicity_votes` (TEXT): JSON with vote breakdown by category

## Installation

Install all required packages:

```bash
pip install -r requirements_ethnicity_inference.txt
```

### Requirements

**Core Tools** (always work):
- Python >= 3.7
- duckdb >= 0.9.0
- ethnicseer >= 0.1.2
- pyethnicity >= 0.0.27
- ethnidata >= 3.0.3
- onnxruntime >= 1.15.0
- polars >= 0.19.0
- scikit-learn >= 1.0.0
- numpy >= 1.21.0

**Optional Tools** (may have compatibility issues):
- name2nat >= 0.5.1 (may have dependency conflicts)
- racebert >= 1.1.0 (requires PyTorch, see below)

**For raceBERT** (when you get your Mac Studio):
- torch >= 2.0.0 (install from https://pytorch.org/get-started/locally/)
- transformers >= 4.0.0

**Note**: raceBERT requires PyTorch which is NOT available for Intel Macs. It will work on your new Mac Studio (Apple Silicon).

## Database Schema

### Input Requirements

The pipeline requires these columns in the `authors` table:

- `author_id`: Unique identifier
- `display_name`: Full name (for ethnicseer)
- `forename`: First name (for pyethnicity and ethnidata)
- `surname`: Last name (for pyethnicity and ethnidata)

### Output Columns

After running the pipeline, these columns are added:

**ethnicseer**:
- `ethnicseer_ethnicity` (TEXT)
- `ethnicseer_confidence` (DOUBLE)

**pyethnicity**:
- `pyethnicity_asian` (DOUBLE)
- `pyethnicity_black` (DOUBLE)
- `pyethnicity_hispanic` (DOUBLE)
- `pyethnicity_white` (DOUBLE)

**ethnidata**:
- `ethnidata_country_code` (TEXT)
- `ethnidata_country_name` (TEXT)
- `ethnidata_region` (TEXT)
- `ethnidata_language` (TEXT)
- `ethnidata_confidence` (DOUBLE)

**name2nat**:
- `name2nat_nationality1` (TEXT)
- `name2nat_probability1` (DOUBLE)
- `name2nat_nationality2` (TEXT)
- `name2nat_probability2` (DOUBLE)
- `name2nat_nationality3` (TEXT)
- `name2nat_probability3` (DOUBLE)

**raceBERT**:
- `racebert_race` (TEXT)
- `racebert_race_score` (DOUBLE)
- `racebert_ethnicity` (TEXT)
- `racebert_ethnicity_score` (DOUBLE)

**Consensus**:
- `consensus_ethnicity` (TEXT)
- `consensus_ethnicity_confidence` (DOUBLE)
- `consensus_ethnicity_votes` (TEXT)

## Performance

### Processing Speed

Approximate speeds on modern hardware:

- **ethnicseer**: 500-1000 records/sec
- **pyethnicity**: 10-40 records/sec (slower due to ML model)
- **ethnidata**: 500-1000 records/sec
- **name2nat**: 50-150 records/sec (neural network overhead)
- **raceBERT**: 10-50 records/sec CPU, 100-500 records/sec GPU (transformer model)
- **consensus**: 5000-10000 records/sec

### Total Pipeline Time

For 1 million authors (all 5 tools):
- ethnicseer: ~15-30 minutes
- pyethnicity: ~7-28 hours (slowest component)
- ethnidata: ~15-30 minutes
- name2nat: ~2-6 hours
- raceBERT: ~6-28 hours CPU, ~30-180 minutes GPU
- consensus: ~2-3 minutes

**Total** (all tools, CPU): ~16-63 hours
**Total** (core 3 tools only): ~8-29 hours

**Optimization tips**:
- Skip pyethnicity if you don't need US-centric race categories
- Skip name2nat and raceBERT if dependencies are problematic
- Use GPU for raceBERT if available for 10x+ speedup
- Core tools (ethnicseer, ethnidata) complete in ~30-60 minutes

## Example Queries

### Get consensus ethnicity distribution

```sql
SELECT
    consensus_ethnicity,
    COUNT(*) as count,
    ROUND(AVG(consensus_ethnicity_confidence), 3) as avg_confidence
FROM authors
WHERE consensus_ethnicity IS NOT NULL
GROUP BY consensus_ethnicity
ORDER BY count DESC;
```

### Get authors by specific ethnicity

```sql
SELECT
    author_id,
    display_name,
    consensus_ethnicity,
    consensus_ethnicity_confidence,
    ethnidata_country_name
FROM authors
WHERE consensus_ethnicity = 'South Asian'
    AND consensus_ethnicity_confidence > 0.7
ORDER BY consensus_ethnicity_confidence DESC
LIMIT 100;
```

### Compare tool predictions

```sql
SELECT
    author_id,
    display_name,
    ethnicseer_ethnicity,
    pyethnicity_asian,
    ethnidata_country_name,
    consensus_ethnicity
FROM authors
WHERE ethnicseer_ethnicity IS NOT NULL
    OR pyethnicity_asian IS NOT NULL
    OR ethnidata_country_name IS NOT NULL
LIMIT 100;
```

### Get high-confidence predictions

```sql
SELECT
    consensus_ethnicity,
    COUNT(*) as count
FROM authors
WHERE consensus_ethnicity_confidence >= 0.8
GROUP BY consensus_ethnicity
ORDER BY count DESC;
```

## Troubleshooting

### pyethnicity is very slow

**Cause**: pyethnicity uses ONNX Runtime for ML model inference, which has overhead per prediction.

**Solutions**:
- Reduce batch size (try 50 or 25)
- Skip pyethnicity if you don't need US-centric race categories
- Run pyethnicity separately on a subset of data

### scikit-learn version warnings

**Cause**: ethnicseer's pre-trained model was pickled with an older scikit-learn version.

**Solution**: These warnings are usually safe to ignore. The model will still work correctly. If you encounter errors, try:
```bash
pip install 'scikit-learn>=1.0.0,<1.6.0'
```

### ethnidata returns null results

**Cause**: Name not found in ethnidata's database, or name format issue.

**Solution**: This is normal for uncommon names. The consensus algorithm will use predictions from the other tools.

### Memory issues with large datasets

**Cause**: Processing too many records at once.

**Solutions**:
- Reduce batch size in individual scripts: `--batch-size 500`
- Process data in chunks using LIMIT/OFFSET in SQL
- Increase available system memory

### Tool script not found

**Cause**: Running from wrong directory or incorrect path.

**Solution**: Always run scripts from the `ethnicity/` directory or use absolute paths.

## Architecture

### File Structure

```
ethnicity/
├── 01_infer_ethnicseer.py          # ethnicseer wrapper
├── 02_infer_pyethnicity.py         # pyethnicity wrapper
├── 03_infer_ethnidata.py           # ethnidata wrapper
├── ethnicity_consensus.py           # Consensus logic module
├── ethnicity_orchestrator.py        # Main orchestrator script
├── requirements_ethnicity_inference.txt
├── README_ETHNICITY_INFERENCE.md    # This file
└── logs/                            # Timestamped log files

```

### Design Principles

1. **Modular**: Each tool is a standalone script
2. **Logged**: All operations logged to console and file
3. **Resumable**: Can skip already-processed tools
4. **Flexible**: Can run individual tools or full pipeline
5. **Consensus-based**: Multiple perspectives for better accuracy

## Citation

If you use this pipeline in research, please cite the underlying tools:

**ethnicseer**:
- Treeratpituk, Pucktada, and C. Lee Giles. "Name-ethnicity classification and ethnicity-sensitive name matching." AAAI Conference on Artificial Intelligence. 2012.

**pyethnicity**:
- https://github.com/CangyuanLi/pyethnicity

**ethnidata**:
- https://pypi.org/project/ethnidata/

## License

Individual tools have their own licenses:
- ethnicseer: Apache Software License 2.0
- pyethnicity: Check repository
- ethnidata: Check package documentation

This pipeline wrapper code follows your project's license.
