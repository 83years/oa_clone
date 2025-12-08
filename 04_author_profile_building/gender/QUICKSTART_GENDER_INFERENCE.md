# Gender Inference Pipeline - Quick Start Guide

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd 04_author_profile_building
pip install -r requirements_gender_inference.txt
```

### 2. Run the Complete Pipeline

```bash
# Run all tools and calculate consensus
python gender_orchestrator.py
```

That's it! The orchestrator will:
- Run all 8 gender inference tools sequentially
- Log progress to console and `logs/` directory
- Calculate weighted consensus based on population
- Store results in your DuckDB database

## 📊 Expected Output

```
======================================================================
GENDER INFERENCE ORCHESTRATOR
======================================================================
Database: /path/to/author_data.duckdb
======================================================================

======================================================================
Running: 05_infer_genderComputer.py
======================================================================
[2025-12-08 10:00:00] [INFO] Starting 05_infer_genderComputer.py
[2025-12-08 10:00:05] [INFO] Progress: 10,000/100,000 (10.0%) | Rate: 2000 records/sec
...
✓ 05_infer_genderComputer.py completed successfully

======================================================================
Running: 11_infer_genderpred_in.py
======================================================================
...

======================================================================
CALCULATING CONSENSUS GENDER
======================================================================
[2025-12-08 10:15:00] [INFO] Processing 100,000 authors
[2025-12-08 10:15:10] [INFO] Progress: 10,000/100,000 (10.0%)
...

======================================================================
CONSENSUS CALCULATION COMPLETE
======================================================================
Total records processed: 100,000
Male: 65,432 (65.43%)
Female: 28,765 (28.77%)
Uncertain: 5,803 (5.80%)
Success rate: 94.20%
======================================================================
```

## 🎯 Run Specific Tools Only

### Skip Expensive Tools (ChatGPT, chicksexer)
```bash
python gender_orchestrator.py --skip gpt --skip chicksexer
```

### Only Run Fast General Tools
```bash
python gender_orchestrator.py --only gendercomputer genderguesser
```

### Only Run Population-Specific Tools
```bash
python gender_orchestrator.py --only genderpred_in persian genderizer3
```

## 🧪 Testing First

### Test with ChatGPT Limit
```bash
# Test ChatGPT with just 100 names first to check cost
python 08_infer_gender_chatgpt.py --limit 100
```

### Test Individual Tools
```bash
# Test genderpred-in on Indian authors only
python 11_infer_genderpred_in.py --country India

# Test Persian tool on Iranian authors only
python 13_infer_persian_gender.py --country Iran
```

## 📁 Files Created

### Scripts (in 04_author_profile_building/)
- `gender_orchestrator.py` - Main orchestrator
- `gender_consensus.py` - Consensus logic module
- `11_infer_genderpred_in.py` - Indian names (genderpred-in)
- `12_infer_namesex.py` - Chinese names, ML-based (namesex)
- `13_infer_persian_gender.py` - Persian names (persian-gender-detection)
- `14_infer_chicksexer.py` - Cultural context (chicksexer)
- `15_infer_genderizer3.py` - Turkish/multilingual (genderizer3)

### Existing Scripts (already in place)
- `05_infer_genderComputer.py` - General (genderComputer)
- `06_infer_genderGuesser.py` - General (gender-guesser)
- `08_infer_gender_chatgpt.py` - AI-based (ChatGPT gpt-5-nano)

### Documentation
- `README_GENDER_INFERENCE.md` - Complete documentation
- `QUICKSTART_GENDER_INFERENCE.md` - This file
- `requirements_gender_inference.txt` - Python dependencies

### Logs
- `logs/` directory - All execution logs with timestamps

## 🔍 Checking Results

```sql
-- View consensus results
SELECT
    author_id,
    display_name,
    country_name,
    consensus_gender,
    consensus_confidence,
    gendercomputer_gender,
    genderpred_in_gender,
    persian_gender
FROM authors
WHERE consensus_gender IS NOT NULL
LIMIT 10;

-- Check confidence distribution
SELECT
    CASE
        WHEN consensus_confidence >= 0.8 THEN 'High (>=0.8)'
        WHEN consensus_confidence >= 0.6 THEN 'Medium (0.6-0.8)'
        ELSE 'Low (<0.6)'
    END as confidence_level,
    COUNT(*) as count
FROM authors
WHERE consensus_gender IS NOT NULL
GROUP BY confidence_level;

-- Check by country
SELECT
    country_name,
    consensus_gender,
    COUNT(*) as count,
    AVG(consensus_confidence) as avg_confidence
FROM authors
WHERE consensus_gender IS NOT NULL
    AND country_name IN ('India', 'Iran', 'Turkey', 'China', 'United States')
GROUP BY country_name, consensus_gender
ORDER BY country_name, consensus_gender;
```

## ⚠️ Common Issues

### namesex compatibility error
```bash
# Install compatible scikit-learn version
pip install scikit-learn==0.24.2
```

### ChatGPT API error
```python
# Set API key in config.py or use command line
python 08_infer_gender_chatgpt.py --api-key YOUR_KEY
```

### chicksexer slow performance
```bash
# Use smaller batch size
python 14_infer_chicksexer.py --batch-size 50
```

## 💡 Tips

1. **Run overnight**: The full pipeline can take several hours for large databases
2. **Monitor logs**: Check `logs/` directory for progress if running in background
3. **Start small**: Test with `--limit` arguments before full runs
4. **Skip expensive tools**: Use `--skip gpt chicksexer` for faster runs
5. **Population targeting**: Use `--country` filters for population-specific tools

## 📈 Performance Expectations

| Records | Fast Tools Only | All Tools | With ChatGPT |
|---------|----------------|-----------|--------------|
| 10K | ~5 minutes | ~15 minutes | ~30 minutes |
| 100K | ~30 minutes | ~2 hours | ~4 hours |
| 1M | ~4 hours | ~15 hours | ~30 hours |

*Times are approximate and depend on hardware*

## 🎓 Understanding Consensus

The pipeline uses **weighted voting** where:
- Population-specific tools get 2x weight for their populations
- High-quality tools (ChatGPT) get higher base weights
- Probability scores multiply the weights
- Need >50% weighted votes for a decision

Example for Indian author:
```
genderComputer: male (weight: 1.2)
genderpred-in: female, prob=0.95 (weight: 0.8 × 2.0 × 0.95 = 1.52)
Result: female (confidence: 0.56)
```

## 📚 Next Steps

1. Review `README_GENDER_INFERENCE.md` for detailed documentation
2. Check consensus quality in your database
3. Adjust tool selection based on your population
4. Consider running expensive tools (GPT) on uncertain cases only

## 🆘 Need Help?

- Check log files in `logs/` directory
- Review tool-specific columns in database
- See `README_GENDER_INFERENCE.md` for troubleshooting
- Test consensus logic: `python gender_consensus.py`
