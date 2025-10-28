# Clinical Flow Cytometry Gender Analysis
## Visualization & Communication Style Guide

**Project**: Analysis of Gender Roles Within a Clinical Flow Cytometry Co-Author Network
**Version**: 1.0
**Last Updated**: 2025-10-28
**Status**: AUTHORITATIVE - All visualizations must follow this guide

---

## Table of Contents
1. [Critical Gender Communication Guidelines](#1-critical-gender-communication-guidelines)
2. [Color Palettes](#2-color-palettes)
3. [Typography & Text](#3-typography--text)
4. [Figure Dimensions & Export](#4-figure-dimensions--export)
5. [Plot Types by Analysis](#5-plot-types-by-analysis)
6. [Statistical Annotations](#6-statistical-annotations)
7. [Network Visualizations](#7-network-visualizations)
8. [Accessibility Requirements](#8-accessibility-requirements)
9. [Workflow & Implementation](#9-workflow--implementation)
10. [Code Templates](#10-code-templates)

---

## 1. Critical Gender Communication Guidelines

### 1.1 Language Requirements

**CRITICAL**: Gender is a sensitive topic. Precision in language is mandatory.

#### Approved Terminology

**ALWAYS USE**:
- "inferred gender" (never just "gender")
- "Male" or "M" (uppercase in labels, legends)
- "Female" or "F" (uppercase in labels, legends)
- "male authors" / "female authors" (lowercase in prose)
- "uninferred gender" or "unknown gender" (for authors without gender assignment)

**NEVER USE**:
- "man" or "woman"
- "men" or "women"
- "gender identity"
- "sex"
- "boys" or "girls"
- Any pronouns (he/she/they) when referring to aggregate data
- "other" (use "Unknown" or "Uninferred")

#### Example Correct Usage

✅ **Correct**: "Female authors show lower degree centrality (mean = 12.4, SD = 8.2) compared to male authors (mean = 15.1, SD = 9.7)."

✅ **Correct**: "Authors with uninferred gender (n = 234,521) were excluded from gender-specific analyses."

✅ **Correct**: "We inferred gender using a multi-method approach (genderizeR, gender-guesser, Genderize.io API) based on author forenames and country of affiliation."

❌ **Incorrect**: "Women have fewer connections than men."

❌ **Incorrect**: "Authors' gender was determined from their names."

❌ **Incorrect**: "Male/female/other authors were compared."

### 1.2 Methodological Transparency

**ALWAYS**:
- Use "inferred" when describing gender (never state as fact)
- Report inference accuracy (e.g., "83% validation accuracy on 1,000-author sample")
- Report coverage (e.g., "Gender inferred for 78% of authors [M: 42%, F: 36%]")
- Note limitations (e.g., "Gender inference limited to binary classification")
- Specify inference methods in methods section and figure captions

### 1.3 Visual Representation

**Gender must ALWAYS be visually consistent across all figures**:
- Use ONLY the specified colors (see Section 2.1)
- Present in consistent order: F, M, Unknown (left to right, top to bottom)
- Use same color scheme across all plots (never vary)

---

## 2. Color Palettes

### 2.1 Gender Colors (MANDATORY - NEVER DEVIATE)

**These colors are FIXED and MUST be used in all gender-related visualizations.**

```python
# Python
GENDER_COLORS = {
    "F": "#6a00ff",      # Female - Purple
    "M": "#FCA63F",      # Male - Orange
    "Unknown": "#D3D3D3" # Unknown - Light Gray
}
```

```r
# R
gender_colors <- c(
  "F" = "#6a00ff",      # Female - Purple
  "M" = "#FCA63F",      # Male - Orange
  "Unknown" = "#D3D3D3" # Unknown - Light Gray
)
```

**Rationale**:
- Purple (#6a00ff): Distinct, not traditionally gender-coded
- Orange (#FCA63F): Warm, high contrast with purple
- Gray (#D3D3D3): Neutral, indicates missing data
- High contrast between M and F for clarity
- Distinguishable for deuteranopia (most common colorblindness)

**Usage Rules**:
- Use uppercase keys ("M", "F", "Unknown") consistently
- Order: F, M, Unknown (alphabetical for F/M, Unknown last)
- Never reverse order (keeps visual consistency across figures)

### 2.2 Career Stage Colors (Warm to Cool Progression)

Career stage progresses from warm (early career) to cool (veteran), representing maturation and experience.

```python
# Python
CAREER_STAGE_COLORS = {
    "Early": "#F59E0B",        # Amber/Orange - warmth, energy, beginning
    "Established": "#EAB308",  # Yellow - growth, development
    "Senior": "#06B6D4",       # Cyan - maturity, stability
    "Veteran": "#3B82F6",      # Blue - depth, experience
    "Emeritus": "#6366F1"      # Indigo - wisdom, legacy
}
```

```r
# R
career_stage_colors <- c(
  "Early" = "#F59E0B",        # Amber/Orange
  "Established" = "#EAB308",  # Yellow
  "Senior" = "#06B6D4",       # Cyan
  "Veteran" = "#3B82F6",      # Blue
  "Emeritus" = "#6366F1"      # Indigo
)
```

**Notes**:
- If your final career stage taxonomy differs, adjust labels but keep warm→cool progression
- This palette is colorblind-safe (tested for deuteranopia)
- Order represents career progression (always plot in this order)

### 2.3 Centrality Measure Colors

For plotting multiple centrality measures (degree, PageRank, eigenvector, etc.) on same plot or in facets.

```python
# Python
CENTRALITY_COLORS = {
    "Degree": "#06B6D4",         # Cyan
    "PageRank": "#22C55E",       # Green
    "Eigenvector": "#EAB308",    # Yellow
    "Clustering": "#8B5CF6",     # Purple
    "Betweenness": "#EF4444",    # Red
    "Closeness": "#F97316",      # Orange
    "Katz": "#3B82F6",           # Blue
    "Bridging": "#EC4899",       # Pink
    "Constraint": "#0EA5E9",     # Sky Blue
    "Hub": "#84CC16"             # Lime
}
```

```r
# R (matching your previous palette, adapted)
centrality_colors <- c(
  "Degree" = "#06B6D4",         # Cyan
  "PageRank" = "#22C55E",       # Green
  "Eigenvector" = "#EAB308",    # Yellow
  "Clustering" = "#8B5CF6",     # Purple
  "Betweenness" = "#EF4444",    # Red
  "Closeness" = "#F97316",      # Orange
  "Katz" = "#3B82F6",           # Blue
  "Bridging" = "#EC4899",       # Pink
  "Constraint" = "#0EA5E9",     # Sky Blue
  "Hub" = "#84CC16"             # Lime
)
```

**Usage**:
- Use when comparing multiple centrality measures
- Palette is colorblind-safe
- Order by importance in your analysis (e.g., Degree, PageRank, Eigenvector first)

### 2.4 Author Typology Colors (To Be Defined After Clustering)

Placeholder palette for 5-6 author archetypes (H3 analysis). **Define after clustering** to match cluster characteristics.

**Suggested Approach**:
- Use distinct, saturated colors (high contrast)
- Each cluster gets unique color (avoid gradients here - clusters are categorical)
- Colorblind-safe combinations

**Example** (adapt based on cluster interpretation):
```python
# Placeholder - adjust after clustering
AUTHOR_TYPE_COLORS = {
    "Emerging Researchers": "#06AED5",    # Bright Cyan - growth potential
    "Productive Specialists": "#0C2D48",  # Deep Navy - focus
    "Network Connectors": "#EE6C4D",      # Coral Red - collaboration
    "Senior Leaders": "#BF1A2F",          # Deep Red - influence
    "Established Experts": "#386641",     # Forest Green - excellence
    "Peripheral Contributors": "#AA6C39"  # Bronze - niche
}
```

**Decision Point**: Finalize this palette in Phase 10 (H3 analysis) after cluster interpretation.

### 2.5 Sequential Palettes (For Heatmaps, Gradients)

Use colorblind-safe sequential palettes for continuous variables.

**Recommended**:
- **Purple**: `#f7fcfd` → `#4d004b` (light to dark purple, matches Female color)
- **Orange**: `#fff5eb` → `#7f2704` (light to dark orange, matches Male color)
- **Viridis**: Python `plt.cm.viridis`, R `scale_fill_viridis_c()` (universal safe choice)

**Usage**:
- Heatmaps (e.g., correlation matrices)
- Continuous centrality scores on network nodes
- Temporal trends (single variable over time)

### 2.6 Diverging Palettes (For Showing Differences)

Use for showing deviations from a midpoint (e.g., gender gap: negative to positive).

**Recommended**:
- **Purple-Orange**: `#6a00ff` (F) ← `#FFFFFF` (neutral) → `#FCA63F` (M)
  - Use when showing M vs F differences
  - Negative = more Female, Positive = more Male, Zero = neutral
- **Blue-Red**: `#2563eb` ← `#FFFFFF` → `#dc2626` (alternative)

**Usage**:
- Gender gap visualizations (e.g., centrality difference M - F)
- Effect size plots
- Regression coefficient plots (negative vs. positive effects)

---

## 3. Typography & Text

### 3.1 Fonts

**Primary Font**: Arial (or Helvetica if Arial unavailable)

**Rationale**:
- Clean, sans-serif
- Universally available
- Accepted by all major journals
- Excellent readability at small sizes

**Font Specification**:
```python
# Python (matplotlib)
import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'Arial'
plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'sans-serif']
```

```r
# R (ggplot2)
library(ggplot2)
theme_set(theme_minimal(base_family = "Arial"))
```

**Fallback**: If Arial unavailable, use Helvetica or system default sans-serif. Document which font was used.

### 3.2 Font Sizes

**Standard sizes** (for 13.33" × 7.5" figure at 150 DPI):

| Element | Size (pt) | Usage |
|---------|-----------|-------|
| Axis titles | 14 | "Degree Centrality", "Publication Year" |
| Axis labels | 12 | Tick labels (numbers, categories) |
| Legend title | 12 | "Inferred Gender" |
| Legend text | 10 | "M", "F", "Unknown" |
| Plot title | 16 | Main plot title (if used) |
| Annotations | 10 | Significance stars, N values |
| Figure caption | N/A | Set by journal (not part of plot) |

**Adjustments**:
- For smaller plots (if created): scale proportionally
- For presentations: increase all by 2-4 pt
- For posters: increase all by 8-12 pt

### 3.3 Text Formatting

**Axis Titles**:
- Title case: "Degree Centrality", "Publication Year"
- Bold: **Yes** (weight 600-700)
- Italics: No (unless variable names, e.g., *p*-value)

**Axis Labels**:
- Sentence case for categories: "Male", "Female", "Unknown"
- Numbers as is: "0", "1000", "2000"
- No bold, no italics

**Legend**:
- Title bold: **"Inferred Gender"**
- Items not bold: "M", "F", "Unknown"

**Annotations**:
- Minimal text
- Use symbols where possible: `*`, `**`, `***` (not "p < 0.05")
- Sample sizes: `n = 150,000` (italicize n)

---

## 4. Figure Dimensions & Export

### 4.1 Standard Dimensions

**All plots use consistent dimensions** (unless physically impossible):

- **Width**: 13.33 inches
- **Height**: 7.5 inches
- **Aspect Ratio**: 16:9 (widescreen, good for presentations and papers)

**Rationale**:
- Wide format accommodates side-by-side comparisons
- Consistent sizing simplifies manuscript formatting
- 16:9 works well for both print and digital

### 4.2 Export Settings

**Resolution**: 150 DPI (minimum), 300 DPI for final publication

**Format**:
- **Primary**: PNG (lossless, widely compatible)
- **Vector**: PDF or SVG (for journals requiring vector graphics)

**File Naming Convention**:
```
fig[number]_[descriptor]_[version].[ext]

Examples:
- fig1_corpus_overview_v1.png
- fig2_gender_centrality_comparison_v2.png
- fig3_temporal_trends_v1.pdf
- figS1_degree_distribution_v1.png (supplementary)
```

**Export Code**:

```python
# Python (matplotlib)
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(13.33, 7.5), dpi=150)
# ... plotting code ...
plt.tight_layout()
plt.savefig('figures/fig1_corpus_overview_v1.png', dpi=150, bbox_inches='tight')
plt.savefig('figures/fig1_corpus_overview_v1.pdf', bbox_inches='tight')  # Vector version
plt.close()
```

```r
# R (ggplot2)
library(ggplot2)

p <- ggplot(...) + ...

ggsave(
  "figures/fig1_corpus_overview_v1.png",
  plot = p,
  width = 13.33,
  height = 7.5,
  dpi = 150,
  units = "in"
)

ggsave(
  "figures/fig1_corpus_overview_v1.pdf",
  plot = p,
  width = 13.33,
  height = 7.5,
  units = "in"
)
```

### 4.3 Multi-Panel Figures

For figures with multiple subplots (e.g., A, B, C, D):

**Layout Options**:
- **2×1**: Two plots side-by-side (each 6.5" wide)
- **1×2**: Two plots stacked (each 7.5" tall)
- **2×2**: Four plots in grid (each 6.5" × 3.5")

**Panel Labels**:
- Top-left corner of each panel
- Bold, uppercase: **A**, **B**, **C**, **D**
- Font size: 18 pt
- Position: inside plot area, 0.5" from edges

**Example**:
```python
fig, axes = plt.subplots(1, 2, figsize=(13.33, 7.5))
axes[0].text(0.02, 0.98, 'A', transform=axes[0].transAxes,
             fontsize=18, fontweight='bold', va='top')
axes[1].text(0.02, 0.98, 'B', transform=axes[1].transAxes,
             fontsize=18, fontweight='bold', va='top')
```

---

## 5. Plot Types by Analysis

### 5.1 Gender Comparison Plots (H1, H2, H3, H6)

**Primary Plot Type**: Violin plots with embedded boxplots

**Purpose**: Show distribution differences between male and female authors

**Structure**:
- X-axis: Inferred Gender (categories: F, M)
- Y-axis: Centrality measure (continuous)
- Colors: Gender colors (F = purple, M = orange)
- Show: Full distribution (violin) + quartiles (boxplot inside)

**Required Elements**:
- Sample sizes: `F: n = 120,000 | M: n = 150,000` (top or bottom of plot)
- Summary statistics: Mean ± SD in legend or annotation
- Significance: `***` if p < 0.001, `**` if p < 0.01, `*` if p < 0.05 (bracket above)
- Y-axis: Natural scale (not log unless extremely skewed)

**Example Python Code** (see Section 10.1 for full template)

**When to Use**:
- Comparing M vs F on single metric
- H1 (centrality differences)
- H6 (ego network metrics by gender)

**Variations**:
- **Faceted by career stage**: Separate panel for Early, Established, Senior, etc.
- **Multiple centrality measures**: Facet by measure (Degree, PageRank, etc.)

### 5.2 Temporal Trend Plots (H4)

**Primary Plot Types**:
1. Line plots with confidence intervals (continuous time)
2. Connected points with error bars (binned time)

**Purpose**: Show how gender gaps change over time

**Structure**:

**Option 1: Line plots with ribbons**
- X-axis: Year (continuous)
- Y-axis: Centrality measure (continuous)
- Lines: One per gender (F = purple, M = orange)
- Ribbons: 95% CI (same color, alpha = 0.2)

**Option 2: Connected points with error bars**
- X-axis: Time period (categorical: "2000-2004", "2005-2009", etc.)
- Y-axis: Centrality measure
- Points: Mean value per gender per period
- Error bars: 95% CI or SD
- Connected by lines

**Required Elements**:
- Clear distinction between F and M trends
- Show where confidence intervals overlap (no difference) vs. separate (significant difference)
- Annotate key time points (e.g., "Gender gap closes after 2015")
- Sample sizes per period (in caption or supplementary)

**When to Use**:
- H4 (temporal trends in gender equity)
- Showing convergence or divergence over time

### 5.3 Regression Coefficient Plots (H1-H6)

**Primary Plot Types**:
1. Forest plots (coefficients with CI bars)
2. Effect plots (predicted values)

**Purpose**: Visualize regression model results

**Forest Plots**:
- X-axis: Coefficient estimate (effect size)
- Y-axis: Predictor variables (categorical: Gender, Career Stage, etc.)
- Points: Coefficient estimate
- Lines: 95% CI
- Vertical line at x = 0 (null effect)
- Color-code: Significant (p < 0.05) vs. non-significant

**Effect Plots**:
- X-axis: Predictor of interest (e.g., Career Stage)
- Y-axis: Predicted outcome (e.g., Degree Centrality)
- Lines/ribbons: Predicted values ± 95% CI
- Separate lines by gender (F = purple, M = orange)

**When to Use**:
- Showing regression results
- H1 (gender effect on centrality, controlling for career stage)
- H5 (career trajectory models)

### 5.4 Institutional Stratification Plots (H2)

**Primary Plot Type**: Scatter plot with trend line OR grouped bar chart

**Purpose**: Show relationship between institution centrality and gender composition

**Scatter Plot**:
- X-axis: Institution centrality (e.g., degree centrality)
- Y-axis: % Female authors at institution
- Points: Each institution (color by centrality quartile)
- Trend line: LOESS or linear regression
- Horizontal reference line: Overall % female (e.g., 40%)

**Grouped Bar Chart**:
- X-axis: Institution centrality quartile (Q1 = low, Q4 = high)
- Y-axis: Count or % authors
- Bars: Grouped by gender (F, M)
- Show: Gender distribution shifts across quartiles

**When to Use**:
- H2 (are women underrepresented at high-centrality institutions?)

### 5.5 Author Typology Plots (H3)

**Multiple complementary visualizations** (as specified):

**Plot 1: PCA/UMAP Scatter (Cluster Separation)**
- X-axis: PC1 or UMAP1
- Y-axis: PC2 or UMAP2
- Points: Authors (colored by cluster)
- Purpose: Show cluster separation in reduced dimensions

**Plot 2: Heatmap (Cluster Profiles)**
- Rows: Clusters (5-6 types)
- Columns: Features (centrality measures, productivity, etc.)
- Cells: Standardized mean values (z-scores)
- Color: Sequential (e.g., blue-white-red for low-avg-high)
- Purpose: Show what characterizes each cluster

**Plot 3: Cluster Composition by Gender**
- X-axis: Cluster type
- Y-axis: Count or %
- Bars: Stacked by gender (F, M)
- Purpose: Show gender distribution across clusters

**When to Use**:
- H3 (author typology and gender disparities)
- Showing archetypes (e.g., "Emerging", "Connectors", "Leaders")

### 5.6 Network Visualizations (Phase 06-09)

**Style**: Minimalist (as specified)

**Ego Network Plots**:
- Central node: Highlighted (larger, different shape)
- Direct connections: Colored by gender (F = purple, M = orange, Unknown = gray)
- Edge width: Proportional to collaboration strength (paper count)
- Labels: Central node only (or top 5 most connected)
- Layout: Force-directed (Fruchterman-Reingold or similar)
- Background: White
- No border

**Full Network (if shown)**:
- **Not recommended** for 306k nodes (unreadable)
- If necessary: Show largest connected component, heavily filtered (e.g., >20 papers)
- Nodes: Small, colored by attribute (gender, cluster, etc.)
- Edges: Thin, gray, alpha = 0.1 (mostly invisible)
- Purpose: Show overall structure, not individual nodes

**When to Use**:
- Illustrative ego networks (Phase 09)
- Community structure overview (Phase 07)
- **Sparingly** - most analysis uses metrics, not visualizations

### 5.7 Descriptive Statistics Plots (Corpus Overview)

**Plot Types**:

**Temporal Growth (Works per Year)**:
- X-axis: Year
- Y-axis: Count of works
- Geom: Area or line plot
- Color: Single color (e.g., #3B82F6 blue) or gradient

**Journal Distribution (Top 20 Journals)**:
- X-axis: Count of works
- Y-axis: Journal name (sorted by count)
- Geom: Horizontal bar chart
- Color: Single color

**Geographic Distribution**:
- Map: World map with countries colored by work count (choropleth)
- OR Bar chart: Top 20 countries
- Color: Sequential palette

**Author Productivity Distribution**:
- X-axis: Works count (binned: 1, 2-5, 6-10, 11-20, >20)
- Y-axis: Count of authors (log scale if skewed)
- Geom: Bar chart or histogram
- Color: Single color

---

## 6. Statistical Annotations

### 6.1 Significance Markers

**System**: Star notation with legend

**Markers**:
- `*` : p < 0.05
- `**` : p < 0.01
- `***` : p < 0.001
- `ns` : not significant (p ≥ 0.05)

**Placement**:
- Above comparison (bracket connecting groups)
- Centered horizontally
- Font size: 10 pt
- Color: Black (always, regardless of bar/violin colors)

**Legend** (include in every figure with significance markers):
```
* p < 0.05, ** p < 0.01, *** p < 0.001
```

**Example**:
```python
# Bracket from x=0 (M) to x=1 (F), at y=max+5%
ax.plot([0, 1], [ymax*1.05, ymax*1.05], 'k-', linewidth=1)
ax.text(0.5, ymax*1.06, '***', ha='center', fontsize=10)
```

### 6.2 Effect Sizes

**Report effect sizes** (not just p-values) in:
- Figure captions: "Cohen's d = 0.42"
- Supplementary tables: Full regression results
- Text annotations (optional): On forest plots

**Interpretation**:
- Small: d ≈ 0.2
- Medium: d ≈ 0.5
- Large: d ≈ 0.8

**When to Show**:
- Always calculate (even if not on plot)
- Show on plot if space permits
- Always in caption or supplementary materials

### 6.3 Sample Sizes

**ALWAYS show sample sizes** (as specified)

**Format**:
```
F: n = 120,000 | M: n = 150,000
```

**Placement**:
- Top of plot (below title if present)
- OR bottom of plot (above x-axis label)
- OR in legend
- Font size: 10 pt
- Color: Dark gray (#4B5563)

**Italicize n**: `n = 150,000`

**Example**:
```python
ax.text(0.5, 0.95, 'F: n = 120,000 | M: n = 150,000',
        transform=ax.transAxes, ha='center', fontsize=10, style='italic')
```

### 6.4 Summary Statistics

**Show mean ± SD** (as specified)

**Format**:
```
F: 12.4 ± 8.2 | M: 15.1 ± 9.7
```

**Placement**:
- In legend (if space)
- OR annotation in plot
- OR in caption

**Alternative**: Show in table if too cluttered for plot

---

## 7. Network Visualizations

### 7.1 Ego Network Plots

**Style**: Minimalist, clean, essential elements only

**Layout**:
- Algorithm: Fruchterman-Reingold or Kamada-Kawai (force-directed)
- Central node: Fixed at origin
- Neighbors: Arranged in circle or organically

**Nodes**:
- Central node:
  - Size: Large (e.g., 500)
  - Shape: Star or square
  - Color: Red
  - Border: Thick (2-3 pt)
  - Label: Yes (author name or ID)
- Neighbor nodes:
  - Size: Medium (e.g., 200)
  - Shape: Circle
  - Color: By gender (M = #FCA63F, F = #6a00ff, Unknown = #D3D3D3)
  - Border: Thin (0.5 pt), black
  - Label: Only if <20 nodes total, otherwise no labels

**Edges**:
- Width: Proportional to weight (collaboration count)
  - Min width: 0.5
  - Max width: 3
- Color: Light gray (#9CA3AF)
- Style: Solid
- Curved: Yes

**Background**: White (#FFFFFF)

**No Legend** unless node colors represent something other than gender (then include)

**Example Use Cases**:
- Illustrate typical ego networks for male vs. female authors
- Show high-centrality author ego network
- Supplementary: Ego networks for all major clusters

**Code Template**: See Section 10.3

### 7.2 Community/Cluster Visualizations

**For large networks** (e.g., largest connected component):

**Nodes**:
- Size: Tiny (e.g., 10-20)
- Color: By community (use distinct palette)
- No labels (too many)
- No borders (clean look)

**Edges**:
- Very thin (0.1-0.2)
- Gray with high transparency (alpha = 0.05)
- Purpose: Show structure, not individual connections

**Layout**:
- Force-directed (networkx spring_layout or igraph FR)
- May take hours for large networks (run overnight)

**Purpose**:
- Show overall network structure
- Illustrate field fragmentation or cohesion
- **Not for detailed analysis** (use metrics for that)

**Use sparingly**: One overview figure, maybe in supplementary materials

### 7.3 Network Color Schemes

**When coloring nodes by attribute**:

- **Gender**: Use gender colors (F, M, Unknown)
- **Career Stage**: Use career stage colors (warm to cool)
- **Centrality**: Use sequential palette (light to dark)
- **Cluster**: Use distinct categorical palette (from Section 2.4)

**Never mix** multiple attributes on same plot (unless using node size + color for different attributes)

---

## 8. Accessibility Requirements

### 8.1 Colorblind Safety

**CRITICAL**: All palettes must be distinguishable for deuteranopia (red-green colorblindness, ~8% of males)

**Testing**:
- Use online tools: [Coblis](https://www.color-blindness.com/coblis-color-blindness-simulator/) or [Viz Palette](https://projects.susielu.com/viz-palette)
- Upload generated plots, simulate deuteranopia
- Ensure key comparisons (M vs F, different clusters) remain distinguishable

**Gender Colors** (already tested):
- F (#6a00ff) vs M (#FCA63F): ✅ Distinguishable in deuteranopia
- Purple becomes blue-ish, orange remains orange-ish (still distinct)

**Career Stage Colors** (warm to cool):
- ✅ Distinguishable (relies on lightness gradient as well as hue)

**Centrality Colors**:
- ✅ Selected for colorblind safety

**If creating NEW palettes**:
- Use ColorBrewer (all palettes marked "colorblind safe")
- OR test manually with simulators

### 8.2 Additional Accessibility

**Patterns/Textures** (optional, for extreme accessibility):
- Use hatching or textures in addition to colors
- Example: F = purple + dots, M = orange + diagonal lines
- Useful for: Bar charts, area plots
- Not needed if colors are already colorblind-safe

**High Contrast**:
- Ensure text contrasts with background (WCAG AA: ratio ≥ 4.5:1)
- Black text on white background: ✅
- Dark gray (#374151) on white: ✅
- Avoid light text on light backgrounds

**Alternative Formats**:
- Provide underlying data tables in supplementary materials
- Screen readers can't parse images, but can read tables

---

## 9. Workflow & Implementation

### 9.1 Two-Phase Approach

**Phase 1: Exploratory (During Analysis)**

**Purpose**: Understand data, test hypotheses, iterate quickly

**Style**:
- Quick plots using default settings
- No need to follow style guide strictly
- Focus: Insight, not aesthetics
- Save as: `exploratory/` folder, don't version control

**Tools**:
- Python: matplotlib with defaults, seaborn
- R: ggplot2 with defaults

**Example**:
```python
# Quick exploratory plot
import matplotlib.pyplot as plt
plt.scatter(x, y)
plt.xlabel('Degree')
plt.ylabel('PageRank')
plt.show()  # Don't save
```

**Phase 2: Publication-Quality (For Final Figures)**

**Purpose**: Create figures for manuscript

**Style**:
- **Strictly follow style guide**
- Every element specified (colors, fonts, sizes)
- Reproducible (code saved, version controlled)
- Save as: `figures/` folder, include in repo

**Tools**:
- Use templates (Section 10)
- Apply custom themes (Python: rcParams, R: theme_set())

**Example**:
```python
# Publication-quality plot using template
from plot_templates import plot_gender_comparison_violin
fig = plot_gender_comparison_violin(data, metric='degree_centrality')
fig.savefig('figures/fig2_gender_degree_v1.png', dpi=150, bbox_inches='tight')
```

**When to Transition**:
- After analysis complete (results finalized)
- When preparing manuscript
- For presentations (if high-stakes)

### 9.2 Code Organization

**Directory Structure**:
```
99_visualisations/
├── plot_templates.py        # Python plotting functions
├── plot_templates.R          # R plotting functions
├── themes.py                 # Custom matplotlib themes
├── themes.R                  # Custom ggplot2 themes
├── color_palettes.py         # Color definitions (Python)
├── color_palettes.R          # Color definitions (R)
├── test_plots.py             # Test all templates
├── test_colorblind.py        # Colorblind simulation tests
├── exploratory/              # Scratch plots (not version controlled)
│   └── .gitignore            # Ignore this folder
├── figures/                  # Final publication figures
│   ├── fig1_corpus_overview_v1.png
│   ├── fig2_gender_centrality_v1.png
│   └── ...
└── README.md                 # Usage instructions
```

**Best Practices**:
- One function per plot type (e.g., `plot_gender_comparison_violin()`)
- Functions accept data + parameters, return fig object
- All style settings in function (no external state)
- Document parameters clearly

### 9.3 Reproducibility

**Requirements**:
1. **Save plot code**: Every final figure has associated script
2. **Version control**: Figures in git, code in git
3. **Document**: README lists which script creates which figure
4. **Automate**: Makefile or script to regenerate all figures

**Example Makefile**:
```makefile
all: fig1 fig2 fig3

fig1:
	python 99_visualisations/create_fig1.py

fig2:
	python 99_visualisations/create_fig2.py

fig3:
	Rscript 99_visualisations/create_fig3.R

clean:
	rm figures/*.png
```

**Documentation** (`99_visualisations/README.md`):
```markdown
# Figure Generation

| Figure | Script | Description |
|--------|--------|-------------|
| fig1_corpus_overview_v1.png | create_fig1.py | Temporal growth + journal distribution |
| fig2_gender_centrality_v1.png | create_fig2.py | Violin plot: degree centrality by gender |
| fig3_temporal_trends_v1.png | create_fig3.py | Line plot: gender gap over time |

## To regenerate all figures:
```bash
make all
```
```

---

## 10. Code Templates

### 10.1 Python: Gender Comparison Violin Plot

```python
"""
Template: Gender comparison violin plot
Usage: H1 (gender differences in centrality)
"""

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from scipy import stats

# Color palette
GENDER_COLORS = {
    "M": "#FCA63F",
    "F": "#6a00ff",
    "Unknown": "#D3D3D3"
}

def plot_gender_comparison_violin(
    data: pd.DataFrame,
    metric: str,
    metric_label: str = None,
    title: str = None,
    filename: str = None
):
    """
    Create violin plot comparing male and female authors on a metric.

    Parameters:
    -----------
    data : pd.DataFrame
        Must contain columns: 'gender', metric
        'gender' must be 'M', 'F', or 'Unknown'
    metric : str
        Column name of metric to compare (e.g., 'degree_centrality')
    metric_label : str, optional
        Y-axis label (defaults to metric name, title case)
    title : str, optional
        Plot title (default: no title)
    filename : str, optional
        If provided, save to this path

    Returns:
    --------
    fig : matplotlib.figure.Figure
    """

    # Filter to M and F only (exclude Unknown for comparison)
    plot_data = data[data['gender'].isin(['M', 'F'])].copy()

    # Calculate statistics
    stats_dict = {}
    for gender in ['M', 'F']:
        gender_data = plot_data[plot_data['gender'] == gender][metric]
        stats_dict[gender] = {
            'n': len(gender_data),
            'mean': gender_data.mean(),
            'std': gender_data.std()
        }

    # T-test
    m_vals = plot_data[plot_data['gender'] == 'M'][metric]
    f_vals = plot_data[plot_data['gender'] == 'F'][metric]
    t_stat, p_val = stats.ttest_ind(m_vals, f_vals)

    # Cohen's d
    cohens_d = (stats_dict['M']['mean'] - stats_dict['F']['mean']) / \
               np.sqrt((stats_dict['M']['std']**2 + stats_dict['F']['std']**2) / 2)

    # Significance marker
    if p_val < 0.001:
        sig_marker = '***'
    elif p_val < 0.01:
        sig_marker = '**'
    elif p_val < 0.05:
        sig_marker = '*'
    else:
        sig_marker = 'ns'

    # Create figure
    fig, ax = plt.subplots(figsize=(13.33, 7.5), dpi=150)

    # Set font
    plt.rcParams['font.family'] = 'Arial'
    plt.rcParams['font.size'] = 12

    # Violin plot
    parts = ax.violinplot(
        [f_vals, m_vals],
        positions=[0, 1],
        widths=0.7,
        showmeans=False,
        showmedians=False,
        showextrema=False
    )

    # Color violins
    for i, gender in enumerate(['F', 'M']):
        parts['bodies'][i].set_facecolor(GENDER_COLORS[gender])
        parts['bodies'][i].set_alpha(0.7)
        parts['bodies'][i].set_edgecolor('black')
        parts['bodies'][i].set_linewidth(1)

    # Overlay boxplots
    bp = ax.boxplot(
        [f_vals, m_vals],
        positions=[0, 1],
        widths=0.3,
        showfliers=False,
        patch_artist=True,
        boxprops=dict(facecolor='white', alpha=0.8),
        medianprops=dict(color='black', linewidth=2),
        whiskerprops=dict(color='black', linewidth=1),
        capprops=dict(color='black', linewidth=1)
    )

    # X-axis
    ax.set_xticks([0, 1])
    ax.set_xticklabels(['Female', 'Male'], fontsize=12)
    ax.set_xlabel('Inferred Gender', fontsize=14, fontweight='bold')

    # Y-axis
    if metric_label is None:
        metric_label = metric.replace('_', ' ').title()
    ax.set_ylabel(metric_label, fontsize=14, fontweight='bold')
    ax.tick_params(axis='y', labelsize=12)

    # Sample sizes and stats
    sample_text = f"F: n = {stats_dict['F']['n']:,} | M: n = {stats_dict['M']['n']:,}"
    stats_text = f"F: {stats_dict['F']['mean']:.2f} ± {stats_dict['F']['std']:.2f} | " + \
                 f"M: {stats_dict['M']['mean']:.2f} ± {stats_dict['M']['std']:.2f}"

    ax.text(0.5, 0.98, sample_text, transform=ax.transAxes,
            ha='center', va='top', fontsize=10, style='italic', color='#4B5563')
    ax.text(0.5, 0.94, stats_text, transform=ax.transAxes,
            ha='center', va='top', fontsize=10, color='#4B5563')

    # Significance bracket
    ymax = plot_data[metric].max()
    bracket_y = ymax * 1.05
    ax.plot([0, 1], [bracket_y, bracket_y], 'k-', linewidth=1)
    ax.text(0.5, bracket_y * 1.02, sig_marker, ha='center', fontsize=10)

    # Legend
    legend_text = f"* p < 0.05, ** p < 0.01, *** p < 0.001\nCohen's d = {cohens_d:.3f}"
    ax.text(0.98, 0.02, legend_text, transform=ax.transAxes,
            ha='right', va='bottom', fontsize=9, color='#4B5563',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    # Title (if provided)
    if title:
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)

    # Clean up
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='y', alpha=0.3, linestyle='--')

    plt.tight_layout()

    # Save if filename provided
    if filename:
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.savefig(filename.replace('.png', '.pdf'), bbox_inches='tight')

    return fig

# Example usage:
# data = pd.DataFrame({
#     'gender': ['M', 'F', 'M', 'F', ...],
#     'degree_centrality': [12.5, 8.3, 15.2, 11.1, ...]
# })
# fig = plot_gender_comparison_violin(
#     data,
#     metric='degree_centrality',
#     metric_label='Degree Centrality',
#     filename='figures/fig2_gender_degree_v1.png'
# )
```

### 10.2 R: Temporal Trend Line Plot

```r
# Template: Temporal trend line plot with confidence intervals
# Usage: H4 (temporal trends in gender gaps)

library(ggplot2)
library(dplyr)

# Color palette
gender_colors <- c(
  "M" = "#FCA63F",
  "F" = "#6a00ff"
)

plot_temporal_trends <- function(
  data,
  time_var = "year",
  metric_var = "degree_centrality",
  metric_label = NULL,
  title = NULL,
  filename = NULL
) {
  #' Create line plot showing temporal trends by gender
  #'
  #' @param data Data frame with columns: time_var, gender, metric_var
  #' @param time_var Name of time variable (e.g., "year")
  #' @param metric_var Name of metric to plot (e.g., "degree_centrality")
  #' @param metric_label Y-axis label (defaults to metric_var)
  #' @param title Plot title (optional)
  #' @param filename Save path (optional)
  #' @return ggplot object

  # Aggregate by time and gender
  plot_data <- data %>%
    filter(gender %in% c("M", "F")) %>%
    group_by(!!sym(time_var), gender) %>%
    summarise(
      mean = mean(!!sym(metric_var), na.rm = TRUE),
      sd = sd(!!sym(metric_var), na.rm = TRUE),
      n = n(),
      se = sd / sqrt(n),
      ci_lower = mean - 1.96 * se,
      ci_upper = mean + 1.96 * se,
      .groups = 'drop'
    )

  # Default label
  if (is.null(metric_label)) {
    metric_label <- tools::toTitleCase(gsub("_", " ", metric_var))
  }

  # Create plot
  p <- ggplot(plot_data, aes(x = !!sym(time_var), y = mean, color = gender, fill = gender)) +
    # Confidence ribbons
    geom_ribbon(aes(ymin = ci_lower, ymax = ci_upper), alpha = 0.2, color = NA) +
    # Lines
    geom_line(linewidth = 1.5) +
    # Points
    geom_point(size = 2.5, shape = 21, fill = "white", stroke = 1.5) +
    # Colors
    scale_color_manual(values = gender_colors, labels = c("Female", "Male")) +
    scale_fill_manual(values = gender_colors, labels = c("Female", "Male")) +
    # Labels
    labs(
      x = tools::toTitleCase(gsub("_", " ", time_var)),
      y = metric_label,
      color = "Inferred Gender",
      fill = "Inferred Gender",
      title = title
    ) +
    # Theme
    theme_minimal(base_family = "Arial", base_size = 12) +
    theme(
      axis.title = element_text(size = 14, face = "bold"),
      axis.text = element_text(size = 12),
      legend.title = element_text(size = 12, face = "bold"),
      legend.text = element_text(size = 10),
      legend.position = "bottom",
      panel.grid.minor = element_blank(),
      panel.grid.major = element_line(color = "gray90", linetype = "dashed"),
      plot.title = element_text(size = 16, face = "bold", hjust = 0.5)
    )

  # Save if filename provided
  if (!is.null(filename)) {
    ggsave(
      filename,
      plot = p,
      width = 13.33,
      height = 7.5,
      dpi = 150,
      units = "in"
    )
    # Also save PDF
    ggsave(
      sub("\\.png$", ".pdf", filename),
      plot = p,
      width = 13.33,
      height = 7.5,
      units = "in"
    )
  }

  return(p)
}

# Example usage:
# data <- read.csv("centrality_over_time.csv")
# p <- plot_temporal_trends(
#   data,
#   time_var = "publication_year",
#   metric_var = "degree_centrality",
#   metric_label = "Degree Centrality",
#   filename = "figures/fig4_temporal_trends_v1.png"
# )
# print(p)
```

### 10.3 Python: Ego Network Visualization

```python
"""
Template: Ego network visualization (minimalist)
Usage: Phase 09 (ego network analysis)
"""

import networkx as nx
import matplotlib.pyplot as plt
import numpy as np

GENDER_COLORS = {
    "M": "#FCA63F",
    "F": "#6a00ff",
    "Unknown": "#D3D3D3"
}

def plot_ego_network(
    G: nx.Graph,
    ego_node: str,
    max_neighbors: int = 50,
    filename: str = None
):
    """
    Plot ego network (1-hop neighborhood) for a single author.

    Parameters:
    -----------
    G : nx.Graph
        Full network with node attributes (gender, etc.)
    ego_node : str
        Author ID of ego node
    max_neighbors : int
        Maximum neighbors to show (for readability)
    filename : str, optional
        Save path

    Returns:
    --------
    fig : matplotlib.figure.Figure
    """

    # Extract ego network (1-hop)
    ego_graph = nx.ego_graph(G, ego_node, radius=1)

    # Limit neighbors if too many
    neighbors = list(ego_graph.neighbors(ego_node))
    if len(neighbors) > max_neighbors:
        # Keep top neighbors by edge weight
        neighbor_weights = [
            (n, ego_graph[ego_node][n].get('weight', 1))
            for n in neighbors
        ]
        neighbor_weights.sort(key=lambda x: x[1], reverse=True)
        keep_neighbors = [n for n, w in neighbor_weights[:max_neighbors]]
        keep_nodes = [ego_node] + keep_neighbors
        ego_graph = ego_graph.subgraph(keep_nodes)

    # Layout
    pos = nx.spring_layout(ego_graph, k=0.5, iterations=50, seed=428)
    # Fix ego at center
    pos[ego_node] = np.array([0.5, 0.5])

    # Node colors by gender
    node_colors = [
        GENDER_COLORS.get(ego_graph.nodes[n].get('gender', 'Unknown'), '#D3D3D3')
        for n in ego_graph.nodes()
    ]

    # Node sizes
    node_sizes = [
        500 if n == ego_node else 200
        for n in ego_graph.nodes()
    ]

    # Edge widths by weight
    edge_weights = [ego_graph[u][v].get('weight', 1) for u, v in ego_graph.edges()]
    max_weight = max(edge_weights) if edge_weights else 1
    edge_widths = [0.5 + 2.5 * (w / max_weight) for w in edge_weights]

    # Create figure
    fig, ax = plt.subplots(figsize=(13.33, 7.5), dpi=150, facecolor='white')
    ax.set_facecolor('white')

    # Draw network
    # Edges
    nx.draw_networkx_edges(
        ego_graph, pos, ax=ax,
        width=edge_widths,
        edge_color='#9CA3AF',
        alpha=0.6
    )

    # Nodes
    nx.draw_networkx_nodes(
        ego_graph, pos, ax=ax,
        node_size=node_sizes,
        node_color=node_colors,
        edgecolors='black',
        linewidths=[2 if n == ego_node else 0.5 for n in ego_graph.nodes()]
    )

    # Labels (ego node only, or all if <20 nodes)
    if len(ego_graph.nodes()) < 20:
        labels = {n: ego_graph.nodes[n].get('display_name', n)[:20] for n in ego_graph.nodes()}
    else:
        labels = {ego_node: ego_graph.nodes[ego_node].get('display_name', ego_node)[:20]}

    nx.draw_networkx_labels(
        ego_graph, pos, labels, ax=ax,
        font_size=10,
        font_family='Arial',
        font_weight='bold' if len(labels) == 1 else 'normal'
    )

    # Remove axes
    ax.axis('off')

    # Title
    degree = ego_graph.degree(ego_node)
    gender = ego_graph.nodes[ego_node].get('gender', 'Unknown')
    ax.set_title(
        f"Ego Network: {ego_node[:20]} (Gender: {gender}, Degree: {degree})",
        fontsize=14, fontweight='bold', pad=20, family='Arial'
    )

    plt.tight_layout()

    # Save if filename provided
    if filename:
        plt.savefig(filename, dpi=150, bbox_inches='tight', facecolor='white')
        plt.savefig(filename.replace('.png', '.pdf'), bbox_inches='tight', facecolor='white')

    return fig

# Example usage:
# G = nx.read_gpickle('coauthor_network_gt1.pkl.gz')
# fig = plot_ego_network(
#     G,
#     ego_node='A1234567890',
#     max_neighbors=30,
#     filename='figures/figS1_ego_network_example_v1.png'
# )
```

---

## 11. Quick Reference

### Color Codes (Copy-Paste Ready)

```python
# Python
GENDER_COLORS = {"F": "#6a00ff", "M": "#FCA63F", "Unknown": "#D3D3D3"}
CAREER_STAGE_COLORS = {"Early": "#F59E0B", "Established": "#EAB308", "Senior": "#06B6D4", "Veteran": "#3B82F6", "Emeritus": "#6366F1"}
```

```r
# R
gender_colors <- c("F" = "#6a00ff", "M" = "#FCA63F", "Unknown" = "#D3D3D3")
career_stage_colors <- c("Early" = "#F59E0B", "Established" = "#EAB308", "Senior" = "#06B6D4", "Veteran" = "#3B82F6", "Emeritus" = "#6366F1")
```

### Figure Dimensions

```python
fig, ax = plt.subplots(figsize=(13.33, 7.5), dpi=150)
plt.savefig('figure.png', dpi=150, bbox_inches='tight')
```

```r
ggsave("figure.png", width = 13.33, height = 7.5, dpi = 150, units = "in")
```

### Font Setup

```python
plt.rcParams['font.family'] = 'Arial'
plt.rcParams['font.size'] = 12
```

```r
theme_set(theme_minimal(base_family = "Arial", base_size = 12))
```

---

## 12. Checklist for Each Figure

Before submitting any figure, verify:

- [ ] **Colors**: Gender colors correct (F = #6a00ff, M = #FCA63F)?
- [ ] **Language**: "Inferred gender", "male"/"female" (not "man"/"woman")?
- [ ] **Order**: Gender order F, M, Unknown (alphabetical)?
- [ ] **Dimensions**: 13.33" × 7.5" at 150+ DPI?
- [ ] **Font**: Arial, correct sizes (14pt axis titles, 12pt labels)?
- [ ] **Sample sizes**: n values shown?
- [ ] **Statistics**: Significance markers (* ** ***) with legend?
- [ ] **Colorblind-safe**: Tested with simulator?
- [ ] **Clean**: No chart junk, unnecessary elements removed?
- [ ] **Reproducible**: Code saved, version controlled?
- [ ] **Caption**: Includes "Gender inferred from forename using [method]"?
- [ ] **Files**: Both PNG (raster) and PDF (vector) saved?

---

## 13. Common Mistakes to Avoid

1. **Using "men" or "women"** → Use "male authors" or "female authors"
2. **Forgetting "inferred"** → Always "inferred gender"
3. **Wrong gender colors** → Check hex codes exactly (F = #6a00ff, M = #FCA63F)
4. **Inconsistent order** → Always F, M, Unknown (alphabetical, left to right)
5. **No sample sizes** → Always show n values
6. **p-values without effect sizes** → Report Cohen's d or similar
7. **Cluttered network plots** → Keep minimalist (labels only when essential)
8. **Tiny fonts** → Check font sizes (12pt minimum for axis labels)
9. **Non-colorblind-safe palettes** → Test with simulator
10. **Different figure dimensions** → Stick to 13.33 × 7.5 inches

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-28 | Lucas + Claude | Initial comprehensive style guide created |

---

**END OF STYLE GUIDE**

*This document is AUTHORITATIVE. All project visualizations must follow these specifications. Update this document if standards change, and version control all updates.*
