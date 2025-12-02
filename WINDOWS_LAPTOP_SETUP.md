# Windows Laptop Setup Guide
# Career Trajectory Analysis - Standalone Mode

## Overview
This guide sets up your Windows laptop to run career trajectory modeling (scripts 02-08) without requiring a database connection. You'll work with pre-extracted CSV files transferred from your Mac/NAS.

---

## PHASE 1: Install Python

### Step 1: Download Python
1. Open your web browser
2. Go to: https://www.python.org/downloads/
3. Click **"Download Python 3.13.x"** (or latest 3.x version)
4. Wait for download to complete

### Step 2: Install Python
1. Locate the downloaded file (usually in `Downloads` folder): `python-3.13.x-amd64.exe`
2. **RIGHT-CLICK** the installer and select **"Run as administrator"**
3. **IMPORTANT:** Check the box that says **"Add Python to PATH"**
4. Click **"Install Now"**
5. Wait for installation to complete
6. Click **"Close"**

### Step 3: Verify Python Installation
1. Press `Windows Key + R`
2. Type `cmd` and press Enter
3. In the black window (Command Prompt), type:
   ```
   python --version
   ```
4. You should see: `Python 3.13.x`
5. Type:
   ```
   pip --version
   ```
6. You should see: `pip 24.x.x from ...`

**If you see an error:** Python is not in your PATH. Reinstall Python and make sure to check the "Add Python to PATH" box.

---

## PHASE 2: Create Project Directory

### Step 1: Create Working Directory
1. Open File Explorer (`Windows Key + E`)
2. Navigate to your `Documents` folder
3. Create a new folder called `OA_career_analysis`
4. Inside it, create another folder called `data`

Your structure should look like:
```
C:\Users\YourName\Documents\OA_career_analysis\
    └── data\
```

### Step 2: Copy Python Scripts
**You'll do this after transferring files from your Mac** (see PHASE 4)

---

## PHASE 3: Install Required Python Packages

### Step 1: Open Command Prompt
1. Press `Windows Key + R`
2. Type `cmd` and press Enter

### Step 2: Navigate to Project Directory
```
cd Documents\OA_career_analysis
```

### Step 3: Create Requirements File
1. Type `notepad requirements.txt` and press Enter
2. Copy and paste the following into Notepad:
```
numpy>=1.24.0
pandas>=2.0.0
scikit-learn>=1.3.0
tslearn>=0.6.0
scipy>=1.11.0
matplotlib>=3.7.0
seaborn>=0.12.0
joblib>=1.3.0
```
3. Click **File → Save**
4. Close Notepad

### Step 4: Install Packages
In the Command Prompt, type:
```
pip install -r requirements.txt
```

This will take **5-10 minutes**. You'll see lots of text scrolling by - this is normal.

Wait for the message: `Successfully installed ...`

### Step 5: Verify Installation
Type:
```
python -c "import numpy, pandas, sklearn, tslearn; print('All packages installed successfully!')"
```

You should see: `All packages installed successfully!`

**If you see an error:**
- Make sure you're connected to the internet
- Try running: `pip install --upgrade pip`
- Then retry Step 4

---

## PHASE 4: Transfer Files from Mac

### Files You Need from Mac

Your Mac will generate these files using the data extraction script:

**Data Files (go in `data\` folder):**
1. `test_sample_authors.csv` - Sample of 50,000 authors
2. `test_trajectories.npz` - Career trajectory data (NumPy compressed)
3. `test_metadata.csv` - Author metadata

**Python Scripts (go in main `OA_career_analysis\` folder):**
1. `02_dtw_clustering.py`
2. `03_select_optimal_clusters.py`
3. `05_extract_trajectory_features.py`
4. `06_train_ml_classifier.py`
5. `07_derive_classification_rules.py`
6. `08_validate_hybrid_system.py`

### Transfer Methods

**Option A: USB Drive**
1. Copy files from Mac to USB drive
2. Insert USB drive into Windows laptop
3. Copy files to appropriate folders

**Option B: Email (for smaller files)**
1. Email CSV files to yourself
2. Download on Windows laptop
3. Save to appropriate folders

**Option C: Cloud Storage (Dropbox, Google Drive, OneDrive)**
1. Upload files from Mac
2. Download on Windows laptop

### Final Directory Structure
After transfer, you should have:
```
C:\Users\YourName\Documents\OA_career_analysis\
    ├── requirements.txt
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

## PHASE 5: Run Career Trajectory Analysis

### Step 1: Open Command Prompt in Project Directory
1. Open File Explorer
2. Navigate to `Documents\OA_career_analysis`
3. In the address bar at the top, click and type `cmd`
4. Press Enter

You should see Command Prompt open with path: `C:\Users\YourName\Documents\OA_career_analysis>`

### Step 2: Run Scripts in Order

**Script 02: DTW Clustering** (30-60 minutes)
```
python 02_dtw_clustering.py
```

This will:
- Load trajectory data
- Perform clustering with different k values (5, 7, 10, 12, 15, 20)
- Save cluster assignments to `data\dtw_clusters_k*.csv`
- Save metrics to `data\clustering_metrics.csv`

**Script 03: Select Optimal Clusters** (1-2 minutes)
```
python 03_select_optimal_clusters.py
```

This will analyze clustering results and recommend the best k value.

**Script 05: Extract Trajectory Features** (5-10 minutes)
```
python 05_extract_trajectory_features.py
```

This will extract statistical features from trajectories for ML training.

**Script 06: Train ML Classifier** (10-20 minutes)
```
python 06_train_ml_classifier.py
```

This will train machine learning models to classify career stages.

**Script 07: Derive Classification Rules** (2-5 minutes)
```
python 07_derive_classification_rules.py
```

This will extract human-readable rules from the ML models.

**Script 08: Validate Hybrid System** (5-10 minutes)
```
python 08_validate_hybrid_system.py
```

This will validate the complete classification system.

### Step 3: Monitor Progress
- Each script will print progress messages
- Watch for `✓ Complete` or `Error` messages
- If a script fails, copy the error message and troubleshoot

### Step 4: Review Results
Results will be saved in the `data\` folder as CSV files. You can open them with Excel or any spreadsheet program.

---

## PHASE 6: Transfer Results Back to Mac

Once analysis is complete, copy result files back to your Mac:

**Files to Transfer Back:**
- `data\dtw_clusters_k*.csv` - All cluster assignment files
- `data\clustering_metrics.csv` - Clustering quality metrics
- `data\trajectory_features.csv` - Extracted features
- `data\ml_classifier_results.csv` - ML classification results
- `data\classification_rules.txt` - Human-readable rules
- `data\validation_report.csv` - Validation results

Use the same transfer method (USB, email, cloud) as before.

---

## Troubleshooting

### "Python is not recognized as an internal or external command"
**Solution:** Python is not in your PATH
1. Uninstall Python (Settings → Apps → Python)
2. Reinstall and CHECK the "Add Python to PATH" box

### "No module named 'numpy'" (or other package)
**Solution:** Package not installed
```
pip install numpy pandas scikit-learn tslearn
```

### "FileNotFoundError: test_trajectories.npz"
**Solution:** Data files not in correct location
- Make sure all data files are in `data\` subfolder
- Check file names match exactly (case-sensitive)

### Script runs but produces no output
**Solution:** Check for error messages
- Look for red text in Command Prompt
- Check that input files exist and are not empty

### Computer runs very slow
**Solution:** Close other programs
- Close web browser, email, etc.
- These scripts use a lot of CPU - that's normal
- Let them run overnight if needed

### "MemoryError" during clustering
**Solution:** Reduce sample size
- Edit the data extraction script on Mac to use fewer authors (e.g., 25,000 instead of 50,000)

---

## Performance Expectations

**Hardware recommendations:**
- 8GB+ RAM (16GB preferred)
- 4+ CPU cores
- 10GB free disk space

**Runtime estimates (50,000 authors):**
- Script 02 (DTW Clustering): 30-60 minutes
- Script 03 (Select Clusters): 1-2 minutes
- Script 05 (Extract Features): 5-10 minutes
- Script 06 (Train ML): 10-20 minutes
- Script 07 (Derive Rules): 2-5 minutes
- Script 08 (Validate): 5-10 minutes

**Total time: 1-2 hours**

You can leave scripts running and check back periodically.

---

## Next Steps

After completing all scripts:
1. Transfer result files back to Mac
2. Review clustering results in Excel
3. Examine classification rules
4. Ready to apply models to full author database (will be done on NAS)

---

## Questions?

If you encounter issues:
1. Check the Troubleshooting section above
2. Copy the exact error message
3. Note which script failed and at what step
4. Contact for support with these details
