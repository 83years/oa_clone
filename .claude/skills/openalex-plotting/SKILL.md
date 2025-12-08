---
name: openalex-plotting
description: Generate publication-quality plots for OpenAlex gender analysis following strict style guide. Use when user asks to create plots, visualizations, or figures for gender analysis, network metrics, temporal trends, or career stage comparisons. Applies mandatory color schemes (Female=#6a00ff purple, Male=#FCA63F orange), proper typography, and accessibility standards.
---

# OpenAlex Gender Analysis Plotting Skill

This skill helps create publication-quality plots that strictly follow the project's visualization style guide for gender analysis in the OpenAlex clinical flow cytometry co-author network.

## When to Use This Skill

Use this skill when the user requests:
- Gender comparison plots (male vs female authors)
- Network centrality visualizations
- Temporal trend analysis
- Career stage comparisons
- Any scientific figure for the gender analysis project

## Critical Requirements

### Mandatory Gender Colors (NEVER DEVIATE)
```python
GENDER_COLORS = {
    "F": "#6a00ff",      # Female - Purple
    "M": "#FCA63F",      # Male - Orange
    "Unknown": "#D3D3D3" # Unknown - Light Gray
}
```

```r
gender_colors <- c(
  "F" = "#6a00ff",      # Female - Purple
  "M" = "#FCA63F",      # Male - Orange
  "Unknown" = "#D3D3D3" # Unknown - Light Gray
)
```

### Terminology Requirements
**ALWAYS USE:**
- "inferred gender" (never just "gender")
- "Male" or "M" (uppercase in labels)
- "Female" or "F" (uppercase in labels)
- "male authors" / "female authors" (lowercase in prose)

**NEVER USE:**
- "man" or "woman"
- "men" or "women"
- "gender identity"
- "sex"

### Standard Figure Dimensions
- **Width:** 13.33 inches
- **Height:** 7.5 inches
- **DPI:** 150 minimum (300 for final publication)
- **Aspect Ratio:** 16:9

### Typography
- **Font:** Arial (Helvetica fallback)
- **Axis titles:** 14pt, bold
- **Axis labels:** 12pt
- **Legend title:** 12pt, bold
- **Legend text:** 10pt
- **Plot title:** 16pt, bold

## Implementation Instructions

### Step 1: Access Style Guide
The complete style guide is located at:
```
/Users/lucas/Documents/openalex_database/python/OA_clone/STYLE_GUIDE.md
```

Read this file for complete specifications.

### Step 2: Use Existing Theme Functions
The project already has theme modules:
- **Python:** `99_visualisations/themes.py`
- **R:** `99_visualisations/themes.R`

Import and use these:

```python
# Python
from themes import set_project_theme, create_figure, save_figure
set_project_theme()
fig, ax = create_figure()
# ... plotting code ...
save_figure(fig, 'figures/my_plot_v1')
```

```r
# R
source("99_visualisations/themes.R")
set_project_theme()
# ... plotting code ...
save_figure(p, "figures/my_plot_v1")
```

### Step 3: Apply Color Palettes
Import color palettes:
```python
# Python
from color_palettes import GENDER_COLORS, CAREER_STAGE_COLORS
```

```r
# R
source("99_visualisations/color_palettes.R")
```

### Step 4: Use Plot Templates
For common plot types, use existing templates:
```python
# Python
from plot_templates import plot_gender_comparison_violin
fig = plot_gender_comparison_violin(data, 'degree_centrality')
```

## Plot Type Reference

### Gender Comparison Plots
- **Type:** Violin plots with boxplots
- **Required elements:**
  - Sample sizes (F: n = X | M: n = Y)
  - Summary statistics (mean ± SD)
  - Significance markers (*, **, ***)
  - Gender colors (F=purple, M=orange)

### Temporal Trends
- **Type:** Line plots with confidence intervals
- **Required elements:**
  - Separate lines per gender
  - 95% CI ribbons (alpha=0.2)
  - Gender colors maintained

### Network Visualizations
- **Type:** Minimalist ego networks
- **Required elements:**
  - Nodes colored by gender
  - White background
  - Edge width by collaboration strength
  - Labels only when essential

### Career Stage Analysis
- **Type:** Faceted plots or grouped bars
- **Colors:** Warm to cool progression
  - Early: #F59E0B (amber)
  - Established: #EAB308 (yellow)
  - Senior: #06B6D4 (cyan)
  - Veteran: #3B82F6 (blue)
  - Emeritus: #6366F1 (indigo)

## Statistical Annotations

### Significance Markers
- `*`: p < 0.05
- `**`: p < 0.01
- `***`: p < 0.001
- `ns`: not significant

Always include legend: `* p < 0.05, ** p < 0.01, *** p < 0.001`

### Effect Sizes
Report Cohen's d in captions or annotations.

### Sample Sizes
Always display: `F: n = 120,000 | M: n = 150,000`
Font: 10pt italic, color: #4B5563

## Accessibility

All plots must be:
- **Colorblind-safe:** Test with deuteranopia simulator
- **High contrast:** Black text on white background
- **Clear labels:** No abbreviations without definition

## Output Files

Save in multiple formats:
```python
# Save both PNG and PDF
save_figure(fig, 'figures/fig1_description_v1')
# Creates: fig1_description_v1.png and fig1_description_v1.pdf
```

## Example Usage Patterns

### Example 1: Create Gender Comparison Plot
```python
from themes import set_project_theme
from plot_templates import plot_gender_comparison_violin
import pandas as pd

set_project_theme()

# Assuming data has columns: gender, degree_centrality
fig = plot_gender_comparison_violin(
    data=df,
    metric='degree_centrality',
    metric_label='Degree Centrality',
    filename='figures/fig2_gender_degree_v1.png'
)
```

### Example 2: Temporal Trend Plot (R)
```r
source("99_visualisations/themes.R")
source("99_visualisations/plot_templates.R")

set_project_theme()

p <- plot_temporal_trends(
  data = df,
  time_var = "year",
  metric_var = "degree_centrality",
  metric_label = "Degree Centrality",
  filename = "figures/fig3_temporal_v1.png"
)
```

## Quality Checklist

Before finalizing any plot, verify:
- [ ] Gender colors correct (F=#6a00ff, M=#FCA63F)
- [ ] Terminology uses "inferred gender"
- [ ] Order: F, M, Unknown (alphabetical)
- [ ] Dimensions: 13.33" × 7.5" at 150 DPI
- [ ] Font: Arial, correct sizes
- [ ] Sample sizes shown
- [ ] Significance markers with legend
- [ ] Colorblind-safe tested
- [ ] Both PNG and PDF saved

## Common Mistakes to Avoid

1. Using "men"/"women" instead of "male authors"/"female authors"
2. Forgetting "inferred" before "gender"
3. Wrong gender color codes
4. Inconsistent gender order
5. Missing sample sizes
6. No effect sizes
7. Non-colorblind-safe colors
8. Wrong figure dimensions

## References

- Full style guide: `STYLE_GUIDE.md`
- Python themes: `99_visualisations/themes.py`
- R themes: `99_visualisations/themes.R`
- Color palettes: `99_visualisations/color_palettes.py` and `.R`
- Plot templates: `99_visualisations/plot_templates.py` and `.R`
