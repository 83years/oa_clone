# Visualization Module
## Clinical Flow Cytometry Gender Analysis

This directory contains all visualization code, themes, color palettes, and generated figures for the project.

**Last Updated**: 2025-10-28
**Status**: Infrastructure ready, awaiting data

---

## Directory Structure

```
99_visualisations/
├── color_palettes.py          # Python color definitions (MANDATORY)
├── color_palettes.R            # R color definitions (MANDATORY)
├── themes.py                   # Python/matplotlib themes
├── themes.R                    # R/ggplot2 themes
├── plot_templates.py           # Python plotting functions
├── plot_templates.R            # R plotting functions (TODO)
├── test_plots.py               # Test all templates (TODO)
├── test_colorblind.py          # Colorblind simulation tests (TODO)
├── exploratory/                # Scratch plots (NOT version controlled)
│   └── .gitignore
├── figures/                    # Final publication figures
└── README.md                   # This file
```

---

## Quick Start

### Python

```python
# At the start of any plotting script
from themes import set_project_theme
from color_palettes import GENDER_COLORS, CAREER_STAGE_COLORS
from plot_templates import plot_gender_comparison_violin

# Apply theme
set_project_theme()

# Use templates
fig = plot_gender_comparison_violin(
    data,
    metric='degree_centrality',
    metric_label='Degree Centrality',
    filename='figures/fig2_gender_degree_v1'
)
```

### R

```r
# At the start of any plotting script
source("99_visualisations/themes.R")
source("99_visualisations/color_palettes.R")

# Apply theme
set_project_theme()

# Use colors
library(ggplot2)
ggplot(data, aes(gender, centrality, fill = gender)) +
  geom_violin() +
  scale_fill_manual(values = gender_colors)
```

---

## Color Palettes

### Gender Colors (MANDATORY - NEVER DEVIATE)

```python
# Python
GENDER_COLORS = {
    "F": "#6a00ff",      # Female - Purple
    "M": "#FCA63F",      # Male - Orange
    "Unknown": "#D3D3D3" # Unknown - Gray
}
```

```r
# R
gender_colors <- c(
  "F" = "#6a00ff",
  "M" = "#FCA63F",
  "Unknown" = "#D3D3D3"
)
```

**Order**: Always F, M, Unknown (alphabetical)

### Career Stage Colors

Warm (early career) → Cool (veteran):
- Early: `#F59E0B` (Amber/Orange)
- Established: `#EAB308` (Yellow)
- Senior: `#06B6D4` (Cyan)
- Veteran: `#3B82F6` (Blue)
- Emeritus: `#6366F1` (Indigo)

### Centrality Colors

See `color_palettes.py` or `color_palettes.R` for full palette.

---

## Figure Standards

### Dimensions
- **Width**: 13.33 inches
- **Height**: 7.5 inches
- **DPI**: 150 (minimum), 300 for publication

### Fonts
- **Family**: Arial
- **Axis titles**: 14pt, bold
- **Axis labels**: 12pt
- **Legend**: Title 12pt bold, text 10pt
- **Plot title**: 16pt, bold

### Export
- Save both PNG (raster) and PDF (vector)
- Naming: `fig[number]_[descriptor]_[version].[ext]`
- Example: `fig2_gender_centrality_v1.png`

---

## Available Plot Templates

### Python (`plot_templates.py`)

1. **`plot_gender_comparison_violin()`** - Violin plots for gender comparisons (H1, H2, H3, H6)
2. **`plot_temporal_trends_lines()`** - Line plots with confidence intervals (H4)

**TODO**:
- Forest plots (regression coefficients)
- Effect plots (predicted values)
- Scatter plots (institutional stratification)
- Heatmaps (cluster profiles)
- Network visualizations (ego networks)

### R (`plot_templates.R`)

**TODO**: Create R versions of plot templates

---

## Workflow

### Phase 1: Exploratory (During Analysis)

**Purpose**: Quick exploration, iteration

**Location**: `exploratory/` (not version controlled)

**Style**: Use defaults, focus on insights not aesthetics

```python
# Quick exploratory plot
import matplotlib.pyplot as plt
plt.scatter(x, y)
plt.xlabel('Degree')
plt.ylabel('PageRank')
plt.show()  # Don't save
```

### Phase 2: Publication-Quality (For Manuscript)

**Purpose**: Final figures for publication

**Location**: `figures/` (version controlled)

**Style**: Strictly follow style guide, use templates

```python
# Publication plot using template
from plot_templates import plot_gender_comparison_violin

fig = plot_gender_comparison_violin(
    data,
    metric='degree_centrality',
    metric_label='Degree Centrality',
    filename='figures/fig2_gender_degree_v1'
)
```

---

## Testing

### Test Plot Templates

```bash
# Test Python templates
python 99_visualisations/plot_templates.py

# Test R templates (when created)
Rscript 99_visualisations/plot_templates.R
```

This will create example plots in `figures/` with prefix `example_`.

### Test Colorblind Safety

**TODO**: Create `test_colorblind.py`

Use online tools:
- [Coblis](https://www.color-blindness.com/coblis-color-blindness-simulator/)
- [Viz Palette](https://projects.susielu.com/viz-palette)

All palettes have been pre-tested for deuteranopia.

---

## Figure Generation

| Figure | Script | Description | Status |
|--------|--------|-------------|--------|
| fig1_corpus_overview_v1.png | TBD | Temporal growth + journal distribution | TODO |
| fig2_gender_centrality_v1.png | TBD | Violin plot: degree centrality by gender | TODO |
| fig3_temporal_trends_v1.png | TBD | Line plot: gender gap over time | TODO |

**To regenerate all figures** (once scripts created):

```bash
# Using Makefile (TODO: create)
make all

# Or manually
python 99_visualisations/create_fig1.py
python 99_visualisations/create_fig2.py
# etc.
```

---

## Style Guide Reference

For complete visualization specifications, see:
- **Main Reference**: `/STYLE_GUIDE.md` (project root)
- **Section 9.2**: This directory structure
- **Section 10**: Code templates

---

## Critical Requirements

### Gender Communication

**ALWAYS**:
- Use "inferred gender" (never just "gender")
- Use "Female"/"F" and "Male"/"M" (never "woman"/"man")
- Order: F, M, Unknown (alphabetical)
- Colors: F = `#6a00ff`, M = `#FCA63F`, Unknown = `#D3D3D3`

**NEVER**:
- Use "men" or "women"
- Use "gender identity"
- Deviate from specified colors
- Change gender order

### Every Figure Must Include

- [ ] Correct gender colors (F = purple, M = orange)
- [ ] Alphabetical order (F, M, Unknown)
- [ ] Sample sizes (n values)
- [ ] Appropriate statistics (p-values, effect sizes)
- [ ] Inferred gender note in caption
- [ ] Both PNG and PDF versions saved
- [ ] Colorblind-safe palette

---

## Common Issues & Solutions

### Issue: "Arial font not found"

**Solution** (Python):
```python
# Check available fonts
import matplotlib.font_manager as fm
fonts = [f.name for f in fm.fontManager.ttflist]
print([f for f in fonts if 'Arial' in f or 'Helvetica' in f])

# If Arial unavailable, themes.py will fall back to Helvetica
```

**Solution** (R):
```r
# Check available fonts
library(extrafont)
font_import()  # One-time import
loadfonts()
fonts()[grep("Arial|Helvetica", fonts())]
```

### Issue: Plots don't match style guide

**Solution**: Ensure theme is applied at script start:

```python
from themes import set_project_theme
set_project_theme()  # Always call this first!
```

### Issue: Gender colors wrong

**Solution**: Use color palette constants, never hardcode:

```python
# WRONG
colors = ['purple', 'orange']

# CORRECT
from color_palettes import GENDER_COLORS
colors = [GENDER_COLORS['F'], GENDER_COLORS['M']]
```

---

## Dependencies

### Python

```bash
pip install matplotlib seaborn pandas numpy scipy
```

### R

```r
install.packages(c("ggplot2", "dplyr", "extrafont"))
```

---

## TODO

- [ ] Create `plot_templates.R` (R versions of templates)
- [ ] Create `test_plots.py` (automated testing)
- [ ] Create `test_colorblind.py` (colorblind simulation)
- [ ] Add forest plot template (regression coefficients)
- [ ] Add effect plot template (predicted values)
- [ ] Add scatter plot template (institutional stratification)
- [ ] Add heatmap template (cluster profiles)
- [ ] Add network visualization template (ego networks)
- [ ] Create individual figure generation scripts (create_fig1.py, etc.)
- [ ] Create Makefile for automated figure generation

---

## Questions?

Refer to:
1. **STYLE_GUIDE.md** (project root) - Complete specifications
2. **color_palettes.py / .R** - All color definitions with comments
3. **themes.py / .R** - Theme implementation details
4. **plot_templates.py / .R** - Example usage in docstrings

---

**Remember**: Consistency is key. Follow the style guide strictly for all publication figures.
