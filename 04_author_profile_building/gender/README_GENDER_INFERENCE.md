# Gender Inference Pipeline

A comprehensive pipeline for inferring author gender using multiple population-specific and general-purpose tools, combined with weighted consensus logic.

## Overview

This pipeline uses 8 different gender inference tools to maximize accuracy across diverse populations:

### General Purpose Tools
1. **genderComputer** - General purpose with country context
2. **gender-guesser** - Database lookup with ambiguity handling
3. **ChatGPT (gpt-5-nano)** - High-quality AI-based inference

### Population-Specific Tools
4. **genderpred-in** - Optimized for Indian names (~96% accuracy, LSTM-based)
5. **persian-gender-detection** - Optimized for Persian/Iranian names (19K+ name database)
6. **genderizer3** - Optimized for Turkish names (Naive Bayesian classifier)

### ML-Based General Tools
7. **chicksexer** - Character-level LSTM with cultural context awareness
8. **namesex** - Random Forest with word2vec features, Chinese names

## Installation

```bash
# Install all required packages
pip install -r requirements_gender_inference.txt

# Note: genderComputer is a local package in ../genderComputer/
# Make sure it's accessible in your Python path
```

### Package Compatibility Notes

- **namesex**: May have compatibility issues with newer scikit-learn versions. If you encounter errors, try:
  ```bash
  pip install scikit-learn==0.24.2
  ```

- **chicksexer**: Requires TensorFlow, which can be large. GPU version available separately.

## Usage

### Option 1: Run All Tools with Orchestrator (Recommended)

```bash
# Run all tools and calculate consensus
python gender_orchestrator.py

# Run with custom database
python gender_orchestrator.py --db datasets/my_authors.duckdb

# Skip expensive tools (e.g., ChatGPT, chicksexer)
python gender_orchestrator.py --skip gpt --skip chicksexer

# Only run specific tools
python gender_orchestrator.py --only gendercomputer genderguesser genderpred_in
```

### Option 2: Run Tools Individually

Each tool can be run independently:

```bash
# General purpose tools
python 05_infer_genderComputer.py
python 06_infer_genderGuesser.py
python 08_infer_gender_chatgpt.py --limit 1000  # Test with 1000 records first

# Population-specific tools
python 11_infer_genderpred_in.py --country India  # Filter by country
python 13_infer_persian_gender.py --country Iran
python 15_infer_genderizer3.py

# ML-based tools
python 12_infer_namesex.py
python 14_infer_chicksexer.py --batch-size 50
```

## Database Schema

The pipeline adds the following columns to the `authors` table:

### Tool-Specific Columns

| Tool | Gender Column | Probability Columns |
|------|--------------|-------------------|
| genderComputer | `gendercomputer_gender` | - |
| gender-guesser | `genderguesser_gender` | - |
| ChatGPT | `gpt_gender` | `gpt_probability` |
| genderpred-in | `genderpred_in_gender` | `genderpred_in_male_prob`, `genderpred_in_female_prob` |
| namesex | `namesex_gender` | `namesex_prob` |
| persian-gender | `persian_gender` | - |
| chicksexer | `chicksexer_gender` | `chicksexer_male_prob`, `chicksexer_female_prob` |
| genderizer3 | `genderizer3_gender` | - |

### Consensus Columns

- `consensus_gender` (TEXT): Final consensus gender ('male', 'female', or NULL)
- `consensus_confidence` (DOUBLE): Confidence score (0.0 to 1.0)
- `consensus_votes` (TEXT): JSON string with vote breakdown

## Consensus Logic

The consensus algorithm uses population-weighted voting:

### Weight Factors

1. **Base Weights** (applied to all):
   - genderComputer: 1.2
   - gender-guesser: 1.0
   - ChatGPT: 1.5 (highest quality)
   - chicksexer: 1.3 (cultural context)
   - genderpred-in: 0.8 (population-specific)
   - namesex: 1.0
   - persian-gender: 0.5 (very specific)
   - genderizer3: 0.9

2. **Population Bonuses** (multipliers for target populations):
   - genderpred-in: **2.0x** weight for Indian authors
   - persian-gender: **2.0x** weight for Iranian authors
   - genderizer3: **1.5x** weight for Turkish authors

3. **Probability Multipliers**:
   - When tools provide probability scores, these multiply the weight
   - Example: genderpred-in with 0.95 female probability gets 0.8 × 2.0 × 0.95 = 1.52 votes

### Decision Threshold

- Gender assigned if weighted votes > 50% and clear majority
- Otherwise marked as uncertain (NULL)

## Performance Characteristics

| Tool | Speed | Best For | Notes |
|------|-------|---------|-------|
| genderComputer | Fast | General | Local lookup |
| gender-guesser | Very Fast | General | Local lookup |
| ChatGPT | Slow | High accuracy | API calls, costs money |
| genderpred-in | Fast | Indian names | LSTM model |
| namesex | Medium | Chinese names | RF model, compatibility issues |
| persian-gender | Very Fast | Persian names | Database lookup |
| chicksexer | Slow | Cultural context | TensorFlow model |
| genderizer3 | Fast | Turkish/multilingual | Naive Bayesian |

## Example Consensus Scenarios

### Scenario 1: Indian Author
```
Tools:
- genderComputer: male
- genderguesser: unknown
- genderpred-in: female (prob: 0.95)

Weights:
- genderComputer: 1.2 votes male
- genderpred-in: 0.8 × 2.0 × 0.95 = 1.52 votes female

Result: female (confidence: 0.56)
```

### Scenario 2: Iranian Author
```
Tools:
- genderComputer: male
- persian-gender: female

Weights:
- genderComputer: 1.2 votes male
- persian-gender: 0.5 × 2.0 = 1.0 votes female

Result: male (confidence: 0.55)
```

### Scenario 3: All Agree
```
Tools:
- genderComputer: male
- genderguesser: male
- chicksexer: male (prob: 0.92)

Weights:
- Total: ~3.7 votes male

Result: male (confidence: 0.95+)
```

## Logging

All scripts log to both console and file:
- Log directory: `04_author_profile_building/logs/`
- Log format: `{script_name}_{YYYYMMDD_HHMMSS}.log`
- Includes progress updates every batch

## Cost Considerations

### ChatGPT (gpt-5-nano)
- **Pricing**: $0.05 per 1M input tokens, $0.40 per 1M output tokens
- **Estimated cost**: ~$0.007 per 1,000 names (with batch_size=250)
- **Recommendation**: Test with `--limit` first

### chicksexer
- Free but requires TensorFlow
- Slower than other tools
- Consider using `--batch-size 50-100` for balance

## Troubleshooting

### namesex Import Error
```
ModuleNotFoundError: No module named 'sklearn.ensemble.forest'
```
**Solution**: Install compatible scikit-learn version:
```bash
pip install scikit-learn==0.24.2
```

### chicksexer TensorFlow Error
**Solution**: Ensure TensorFlow is installed:
```bash
pip install tensorflow>=2.0.0
```

### ChatGPT API Error
**Solution**: Set API key in config.py or use `--api-key` argument

## Testing the Pipeline

### Test Consensus Logic
```bash
# Run the gender_consensus module directly
python gender_consensus.py
```

### Test Individual Tools
```bash
# Test genderpred-in with a small sample
python 11_infer_genderpred_in.py --country India

# Test ChatGPT with limited records
python 08_infer_gender_chatgpt.py --limit 100
```

### Validate Results
```sql
-- Check consensus distribution
SELECT
    consensus_gender,
    COUNT(*) as count,
    AVG(consensus_confidence) as avg_confidence
FROM authors
WHERE consensus_gender IS NOT NULL
GROUP BY consensus_gender;

-- Check tool agreement for high confidence cases
SELECT
    gendercomputer_gender,
    genderguesser_gender,
    consensus_gender,
    consensus_confidence
FROM authors
WHERE consensus_confidence > 0.8
LIMIT 10;
```

## Contributing

When adding new gender inference tools:

1. Create wrapper script following naming convention: `{number}_infer_{toolname}.py`
2. Add columns to database with prefix `{toolname}_`
3. Update `gender_consensus.py` with tool weight and normalization
4. Add tool to `gender_orchestrator.py` tool_scripts dict
5. Update this README

## References

- [genderpred-in](https://pypi.org/project/genderpred-in/) - Indian names
- [persian-gender-detection](https://pypi.org/project/persian-gender-detection/) - Persian names
- [chicksexer](https://github.com/kensk8er/chicksexer) - Cultural context
- [genderizer3](https://pypi.org/project/genderizer3/) - Turkish/multilingual
- [namesex](https://pypi.org/project/namesex/) - ML-based, Chinese names
- [gender-guesser](https://pypi.org/project/gender-guesser/) - General purpose
- [genderComputer](https://github.com/tue-mdse/genderComputer) - General purpose
