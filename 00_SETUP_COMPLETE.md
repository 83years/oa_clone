# ✅ Windows Laptop Setup - READY TO USE

## What I've Created

I've set up a complete system to parallelize your work across Mac and Windows laptop. Here's what's ready:

### 📚 Documentation (5 Guides)

1. **LAPTOP_SETUP_SUMMARY.md** - Master overview of entire process
2. **WINDOWS_LAPTOP_SETUP.md** - Detailed Windows setup instructions
3. **LAPTOP_QUICKSTART.md** - Quick reference for running analysis
4. **MAC_EXTRACTION_GUIDE.md** - How to extract data on Mac
5. **00_SETUP_COMPLETE.md** - This file

### 🔧 Scripts Created

**Mac Data Extraction:**
- `04_author_profile_building/career_trajectory_test/00_prepare_laptop_data.py`
  - Extracts 50,000 author sample from your database
  - Creates complete transfer package
  - Runtime: 15-30 minutes

**Windows Analysis (6 scripts):**
- `02_dtw_clustering.py` - DTW clustering
- `03_select_optimal_clusters.py` - Cluster selection
- `05_extract_trajectory_features.py` - Feature extraction
- `06_train_ml_classifier.py` - ML training
- `07_derive_classification_rules.py` - Rule derivation
- `08_validate_hybrid_system.py` - Validation
- `run_all_analysis.bat` - Run all scripts automatically (Windows)

**Support Files:**
- `laptop_requirements.txt` - Python packages for Windows
- All scripts are database-free (work offline)

---

## 🚀 Next Steps (Quick Version)

### Step 1: Extract Data on Mac (NOW)

```bash
cd /Users/lucas/Documents/openalex_database/python/OA_clone/04_author_profile_building/career_trajectory_test
python3 00_prepare_laptop_data.py
```

**Creates:** `laptop_transfer/` folder (~30-60 MB)
**Time:** 15-30 minutes

### Step 2: Transfer to Windows

Copy the entire `laptop_transfer/` folder to your Windows laptop:
- Via USB drive, OR
- Via cloud (Dropbox/Google Drive/OneDrive), OR
- Via network

Place it in: `C:\Users\YourName\Documents\OA_career_analysis\`

### Step 3: Windows Setup (One Time)

1. Install Python 3.13 from python.org
   - ⚠️ CHECK "Add Python to PATH"
2. Open Command Prompt:
   ```cmd
   cd Documents\OA_career_analysis
   pip install -r laptop_requirements.txt
   ```

### Step 4: Run Analysis on Windows

**Option A: Automatic (Easy)**
```cmd
run_all_analysis.bat
```
Just double-click the file or run from Command Prompt.

**Option B: Manual (More control)**
```cmd
python 02_dtw_clustering.py
python 03_select_optimal_clusters.py
python 05_extract_trajectory_features.py
python 06_train_ml_classifier.py
python 07_derive_classification_rules.py
python 08_validate_hybrid_system.py
```

**Total time:** 1-2 hours (can run overnight)

### Step 5: Transfer Results Back

Copy `data\` folder from Windows back to Mac.

---

## 📖 Detailed Instructions

For complete step-by-step instructions, see:

- **First time?** → Read `LAPTOP_SETUP_SUMMARY.md`
- **Extracting on Mac?** → Follow `MAC_EXTRACTION_GUIDE.md`
- **Setting up Windows?** → Follow `WINDOWS_LAPTOP_SETUP.md`
- **Running analysis?** → Use `LAPTOP_QUICKSTART.md`

---

## 🎯 What This Accomplishes

### Without Laptop Parallelization
```
Mac: Parse DB → Wait → Extract names → Wait → Train models → Apply models
     ^^^^^^^^   (Days of sequential work)
```

### With Laptop Parallelization
```
Mac:     Parse DB (continues) ─────────────────────→
                  ↓ (extract sample once)
Laptop:           Train models (1-2 hrs) ─────→
                                          ↓ (transfer back)
NAS:                                      Apply to 117M authors
```

**Time Saved:** 1-2 days of sequential processing

---

## 📊 What Gets Processed

**Sample Size:** 50,000 authors
- Stratified by career length, decade, and activity status
- Representative of full 117M author database

**Analysis:**
1. DTW clustering (finds career trajectory patterns)
2. ML classification (learns to classify without DTW)
3. Rule derivation (creates interpretable rules)
4. Validation (ensures accuracy)

**Results:**
- Cluster assignments for different k values
- Trained ML models (can classify 117M authors)
- Human-readable classification rules
- Quality metrics and validation reports

---

## 💻 System Requirements

### Mac (Current)
- ✅ Python 3.13 - Already installed
- ✅ PostgreSQL access - Already configured
- ✅ 1GB free space - You have plenty

### Windows Laptop (Needed)
- ❓ Python 3.13+ - Needs installation
- ❓ 8GB+ RAM - Check laptop specs
- ❓ 4+ CPU cores - Check laptop specs
- ❓ 10GB free disk - Check available space
- ❓ Internet - Only for initial package install

### Transfer
- USB drive (2GB+), OR
- Cloud storage account, OR
- Same network connection

---

## ⚡ Performance Expectations

| Task | Machine | Time | CPU | I/O |
|------|---------|------|-----|-----|
| Works parsing | Mac | Ongoing | 30% | High |
| Data extraction | Mac | 15-30 min | 40% | Medium |
| DTW clustering | Laptop | 30-60 min | 90% | Low |
| ML training | Laptop | 10-20 min | 70% | Low |
| Other scripts | Laptop | 15 min | 50% | Low |

**No Conflicts:** Laptop uses CPU, Mac uses disk I/O. They don't interfere.

---

## 🔍 File Locations

### On Mac (Now)
```
/Users/lucas/Documents/openalex_database/python/OA_clone/
├── LAPTOP_SETUP_SUMMARY.md
├── WINDOWS_LAPTOP_SETUP.md
├── 00_SETUP_COMPLETE.md (this file)
└── 04_author_profile_building/
    └── career_trajectory_test/
        ├── MAC_EXTRACTION_GUIDE.md
        ├── LAPTOP_QUICKSTART.md
        ├── laptop_requirements.txt
        ├── 00_prepare_laptop_data.py
        ├── run_all_analysis.bat
        ├── 02-08_*.py (analysis scripts)
        └── laptop_transfer/ (created when you run extraction)
```

### On Windows (After Transfer)
```
C:\Users\YourName\Documents\OA_career_analysis\
├── README.txt
├── WINDOWS_LAPTOP_SETUP.md
├── LAPTOP_QUICKSTART.md
├── laptop_requirements.txt
├── run_all_analysis.bat
├── 02-08_*.py
└── data\
    ├── test_sample_authors.csv
    ├── test_trajectories.npz
    └── test_metadata.csv
```

---

## 🆘 Common Issues

### Mac Extraction

**"Connection refused to database"**
→ Check NAS is running: `ping 192.168.1.162`

**"No module named 'psycopg2'"**
→ `pip3 install psycopg2-binary`

### Windows Setup

**"Python is not recognized"**
→ Reinstall Python, CHECK "Add to PATH"

**"No module named 'tslearn'"**
→ `pip install tslearn`

**"FileNotFoundError"**
→ Check files are in `data\` folder

---

## ✅ Success Checklist

### On Mac
- [ ] Run `00_prepare_laptop_data.py`
- [ ] Verify `laptop_transfer/` created
- [ ] Check folder size (~30-60 MB)
- [ ] Transfer to Windows laptop

### On Windows
- [ ] Python installed with PATH
- [ ] Files in `Documents\OA_career_analysis\`
- [ ] Packages installed
- [ ] All 6 scripts run successfully
- [ ] Results in `data\` folder

### Transfer Back
- [ ] Copy results to Mac
- [ ] Verify all CSV files received
- [ ] Review clustering metrics
- [ ] Check classification rules

---

## 🎬 Ready to Start?

### Command to Run on Mac:

```bash
cd /Users/lucas/Documents/openalex_database/python/OA_clone/04_author_profile_building/career_trajectory_test
python3 00_prepare_laptop_data.py
```

Then follow the on-screen instructions and `MAC_EXTRACTION_GUIDE.md`.

---

## 📞 Need Help?

Each guide has detailed troubleshooting:
- `LAPTOP_SETUP_SUMMARY.md` - Overview troubleshooting
- `MAC_EXTRACTION_GUIDE.md` - Mac-specific issues
- `WINDOWS_LAPTOP_SETUP.md` - Windows-specific issues
- `LAPTOP_QUICKSTART.md` - Runtime issues

---

## 🎯 After This Is Done

Once laptop analysis completes and you transfer results back:

1. **Review Results**
   - Examine clustering quality metrics
   - Read classification rules
   - Validate model performance

2. **Apply to Full Database** (on NAS)
   - Run scripts 09-12 to classify all 117M authors
   - Uses trained models from laptop work
   - No need to re-cluster everything

3. **Continue Project**
   - Author profile building complete
   - Ready for hypothesis testing (phases 10-11)
   - Gender and geography analysis

---

**Everything is ready. Start with `MAC_EXTRACTION_GUIDE.md`**

Good luck! 🚀
