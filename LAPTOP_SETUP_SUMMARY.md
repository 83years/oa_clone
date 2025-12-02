# Windows Laptop Setup - Complete Summary
# Career Trajectory Analysis Parallelization

## Overview

This document provides a complete overview of how to set up your Windows laptop to run career trajectory analysis while your Mac continues parsing the database.

**Goal:** Speed up your project by parallelizing CPU-intensive ML/clustering work on the laptop while keeping I/O-intensive database operations on the Mac/NAS.

---

## What You'll Accomplish

### Mac (Continues Running)
- ✅ Parsing works into database (~56% complete, keep running)
- ✅ Extract sample data for laptop (one-time, 15-30 min)

### Windows Laptop (New Work)
- ✅ DTW clustering analysis (CPU-intensive)
- ✅ ML model training (CPU-intensive)
- ✅ Career stage classification (CPU-intensive)
- ✅ **No database I/O** - works offline with CSV files

### NAS (After Laptop Work Completes)
- ⏱️ Apply trained models to full 117M authors (future)
- ⏱️ Full forename extraction (future)
- ⏱️ DuckDB name dictionary building (can move from Mac now)

**Time Saved:** ~1-2 days of processing can happen in parallel instead of sequentially

---

## File Locations

### On Your Mac

**Created by this setup:**
```
/Users/lucas/Documents/openalex_database/python/OA_clone/
├── WINDOWS_LAPTOP_SETUP.md           ← Windows setup instructions
├── LAPTOP_SETUP_SUMMARY.md           ← This file
└── 04_author_profile_building/
    └── career_trajectory_test/
        ├── MAC_EXTRACTION_GUIDE.md   ← Mac extraction instructions
        ├── LAPTOP_QUICKSTART.md      ← Quick reference for laptop
        ├── laptop_requirements.txt   ← Python packages for laptop
        ├── 00_prepare_laptop_data.py ← Script to extract data
        └── laptop_transfer/          ← Created when you run extraction
            ├── README.txt
            ├── WINDOWS_LAPTOP_SETUP.md
            ├── LAPTOP_QUICKSTART.md
            ├── laptop_requirements.txt
            ├── 02_dtw_clustering.py
            ├── 03_select_optimal_clusters.py
            ├── 05_extract_trajectory_features.py
            ├── 06_train_ml_classifier.py
            ├── 07_derive_classification_rules.py
            ├── 08_validate_hybrid_system.py
            └── data/
                ├── test_sample_authors.csv
                ├── test_trajectories.npz
                └── test_metadata.csv
```

### On Windows Laptop (After Transfer)

```
C:\Users\YourName\Documents\OA_career_analysis\
├── README.txt
├── WINDOWS_LAPTOP_SETUP.md
├── LAPTOP_QUICKSTART.md
├── laptop_requirements.txt
├── 02_dtw_clustering.py
├── 03_select_optimal_clusters.py
├── 05_extract_trajectory_features.py
├── 06_train_ml_classifier.py
├── 07_derive_classification_rules.py
├── 08_validate_hybrid_system.py
└── data\
    ├── test_sample_authors.csv
    ├── test_trajectories.npz
    └── test_metadata.csv
```

---

## Complete Workflow

### Phase 1: Mac Data Extraction (15-30 minutes)

**Guide:** `MAC_EXTRACTION_GUIDE.md`

```bash
# On your Mac
cd /Users/lucas/Documents/openalex_database/python/OA_clone/04_author_profile_building/career_trajectory_test

# Run extraction script
python3 00_prepare_laptop_data.py
```

**Creates:** `laptop_transfer/` folder (~30-60 MB)

### Phase 2: File Transfer (10-30 minutes)

**Methods:**
- **USB Drive:** Copy `laptop_transfer/` to USB → Insert in Windows → Copy to `Documents\OA_career_analysis\`
- **Cloud:** Upload to Dropbox/Google Drive/OneDrive → Download on Windows
- **Network:** Use simple HTTP server (see MAC_EXTRACTION_GUIDE.md)

### Phase 3: Windows Setup (20-40 minutes)

**Guide:** `WINDOWS_LAPTOP_SETUP.md` or `LAPTOP_QUICKSTART.md`

**Steps:**
1. Install Python 3.13+ (with "Add to PATH")
2. Install packages: `pip install -r laptop_requirements.txt`
3. Verify installation

### Phase 4: Run Analysis on Windows (1-2 hours)

**Guide:** `LAPTOP_QUICKSTART.md`

```cmd
# On Windows Command Prompt
cd Documents\OA_career_analysis

# Run scripts in order
python 02_dtw_clustering.py         # 30-60 min
python 03_select_optimal_clusters.py # 1-2 min
python 05_extract_trajectory_features.py # 5-10 min
python 06_train_ml_classifier.py    # 10-20 min
python 07_derive_classification_rules.py # 2-5 min
python 08_validate_hybrid_system.py # 5-10 min
```

**Creates:** Multiple CSV result files in `data\` folder

### Phase 5: Transfer Results Back (10-30 minutes)

**Files to transfer back to Mac:**
- `data\dtw_clusters_k*.csv`
- `data\clustering_metrics.csv`
- `data\trajectory_features.csv`
- `data\ml_classifier_results.csv`
- `data\classification_rules.txt`
- `data\validation_report.csv`
- `trained_models\` (entire folder)

**Use same transfer method as Phase 2**

---

## What Each Component Does

### Scripts You Run on Mac

| Script | Purpose | Runtime |
|--------|---------|---------|
| `00_prepare_laptop_data.py` | Extract sample data from database | 15-30 min |

### Scripts Laptop Runs Automatically

| Script | Purpose | Runtime | CPU Usage |
|--------|---------|---------|-----------|
| `02_dtw_clustering.py` | Cluster careers using DTW | 30-60 min | 80-100% |
| `03_select_optimal_clusters.py` | Find best k value | 1-2 min | 30-60% |
| `05_extract_trajectory_features.py` | Extract statistical features | 5-10 min | 50-80% |
| `06_train_ml_classifier.py` | Train ML models | 10-20 min | 60-90% |
| `07_derive_classification_rules.py` | Create interpretable rules | 2-5 min | 30-50% |
| `08_validate_hybrid_system.py` | Validate complete system | 5-10 min | 40-70% |

### Why This Parallelization Works

**Database operations (Mac/NAS):**
- Heavy disk I/O
- Sequential writes to PostgreSQL
- Limited by database write speed
- Benefits from fast NVMe drives

**ML/Clustering operations (Laptop):**
- Heavy CPU computation
- Works with in-memory data
- No database access needed
- Benefits from multiple CPU cores

**No conflict:** Laptop doesn't touch database, Mac doesn't do CPU-heavy ML work

---

## Document Guide

### Start Here
1. **LAPTOP_SETUP_SUMMARY.md** (this file) - Overview of entire process

### On Mac
2. **MAC_EXTRACTION_GUIDE.md** - How to extract data and create transfer package

### On Windows
3. **WINDOWS_LAPTOP_SETUP.md** - Complete detailed setup guide (for first-time setup)
4. **LAPTOP_QUICKSTART.md** - Quick reference (after setup is complete)

### In Transfer Package
5. **README.txt** - Basic transfer instructions and file list

---

## Quick Start (Impatient Mode)

### On Mac (now):
```bash
cd /Users/lucas/Documents/openalex_database/python/OA_clone/04_author_profile_building/career_trajectory_test
python3 00_prepare_laptop_data.py
# Copy laptop_transfer/ to USB drive
```

### On Windows (after transfer):
1. Install Python 3.13 from python.org (CHECK "Add to PATH")
2. Copy USB contents to `Documents\OA_career_analysis\`
3. Open Command Prompt:
```cmd
cd Documents\OA_career_analysis
pip install -r laptop_requirements.txt
python 02_dtw_clustering.py
python 03_select_optimal_clusters.py
python 05_extract_trajectory_features.py
python 06_train_ml_classifier.py
python 07_derive_classification_rules.py
python 08_validate_hybrid_system.py
```
4. Copy `data\` folder back to Mac via USB

---

## Requirements

### Mac/NAS
- ✅ Python 3.13 (already installed)
- ✅ PostgreSQL database access (already configured)
- ✅ psycopg2, pandas, numpy (already installed)
- ✅ 1GB free disk space for transfer package

### Windows Laptop
- ❓ Python 3.13+ (needs installation)
- ❓ 8GB+ RAM (check your specs)
- ❓ 4+ CPU cores (check your specs)
- ❓ 10GB free disk space
- ❓ Internet access (for package installation only)

### Transfer Medium
- USB drive (2GB+), OR
- Cloud storage account, OR
- Same network connection

---

## Troubleshooting Quick Reference

### Mac Issues

**"Connection refused" when running extraction:**
→ Check NAS database is running: `ping 192.168.1.162`

**"No module named psycopg2":**
→ `pip3 install psycopg2-binary`

**Script takes >1 hour:**
→ Check database performance, consider reducing sample size

### Windows Issues

**"Python is not recognized":**
→ Reinstall Python, CHECK "Add Python to PATH" box

**"No module named tslearn":**
→ `pip install tslearn`

**"FileNotFoundError":**
→ Check files are in `data\` subfolder, verify file names

**Script runs but no output:**
→ Check `data\` folder in File Explorer for CSV files

### Transfer Issues

**Files corrupted after transfer:**
→ Re-transfer, try different method (USB vs cloud)

**Missing files:**
→ Check `laptop_transfer/` has all files before transferring

---

## Performance Expectations

### Mac Extraction
- **Time:** 15-30 minutes
- **Data size:** 30-60 MB
- **Database queries:** ~5-10 queries with temp tables

### Windows Analysis
- **Total time:** 1-2 hours for all scripts
- **CPU usage:** High (50-100%) - this is normal
- **RAM usage:** 2-4 GB
- **Disk usage:** ~500 MB (including results)

### Comparison vs Sequential
- **Without laptop:** All work happens sequentially on Mac after parsing completes
- **With laptop:** Trajectory analysis happens NOW while parsing continues
- **Time saved:** 1-2 days of sequential processing

---

## What Happens After

Once you have results back on Mac:

### Immediate Next Steps
1. Review clustering quality metrics
2. Examine classification rules for interpretability
3. Validate model performance

### Future Work (on NAS)
4. Apply trained models to full 117M authors (scripts 09-12)
5. Build complete author profiles with career stages
6. Continue to hypothesis testing (phases 10-11)

### The Big Picture
- Laptop work creates the **methodology** and **trained models**
- NAS work will apply this to the **full dataset**
- Mac continues its current work **uninterrupted**

---

## Support

If you get stuck:

1. **Check the specific guide for your current step:**
   - Extracting on Mac? → `MAC_EXTRACTION_GUIDE.md`
   - Setting up Windows? → `WINDOWS_LAPTOP_SETUP.md`
   - Running analysis? → `LAPTOP_QUICKSTART.md`

2. **Look for the exact error message**
   - Copy the full error text
   - Check the Troubleshooting section
   - Note which script and what step

3. **Verify basics**
   - Python installed and in PATH?
   - Files in correct locations?
   - Packages installed?

4. **Document for help**
   - Screenshot of error
   - Which guide you were following
   - Which step failed
   - What you've already tried

---

## Summary Checklist

### Mac (Do Once)
- [ ] Navigate to career_trajectory_test directory
- [ ] Run `python3 00_prepare_laptop_data.py`
- [ ] Verify `laptop_transfer/` folder created
- [ ] Transfer folder to Windows laptop

### Windows (Do Once)
- [ ] Install Python 3.13+ with "Add to PATH"
- [ ] Copy transferred files to `Documents\OA_career_analysis\`
- [ ] Install packages: `pip install -r laptop_requirements.txt`
- [ ] Verify installation successful

### Windows (Analysis)
- [ ] Run script 02 (DTW clustering)
- [ ] Run script 03 (select clusters)
- [ ] Run script 05 (extract features)
- [ ] Run script 06 (train ML)
- [ ] Run script 07 (derive rules)
- [ ] Run script 08 (validate)

### Transfer Back
- [ ] Copy result files from Windows to USB/cloud
- [ ] Transfer to Mac
- [ ] Verify all result files received

### Continue Project
- [ ] Review clustering metrics
- [ ] Examine classification rules
- [ ] Validate model accuracy
- [ ] Ready to apply to full database (on NAS)

---

## Files Created by This Setup

All the guides and scripts needed:

✅ WINDOWS_LAPTOP_SETUP.md - Complete Windows setup guide
✅ LAPTOP_QUICKSTART.md - Quick reference for Windows
✅ MAC_EXTRACTION_GUIDE.md - Mac extraction instructions
✅ LAPTOP_SETUP_SUMMARY.md - This overview document
✅ 00_prepare_laptop_data.py - Data extraction script
✅ laptop_requirements.txt - Python packages for Windows

**Everything is ready to go!**

---

## Next Step

**Start here:**

```bash
cd /Users/lucas/Documents/openalex_database/python/OA_clone/04_author_profile_building/career_trajectory_test
python3 00_prepare_laptop_data.py
```

Then follow `MAC_EXTRACTION_GUIDE.md` for detailed instructions.

---

**Questions? Each guide has detailed troubleshooting sections.**

Good luck! 🚀
