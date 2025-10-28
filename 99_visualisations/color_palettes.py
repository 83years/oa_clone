"""
Color Palettes for Clinical Flow Cytometry Gender Analysis
===========================================================

This module defines all color palettes used in the project visualizations.
All colors follow the project style guide and are colorblind-safe.

Author: Lucas Black
Date: 2025-10-28
Version: 1.0
"""

# =============================================================================
# GENDER COLORS (MANDATORY - NEVER DEVIATE)
# =============================================================================

GENDER_COLORS = {
    "F": "#6a00ff",      # Female - Purple
    "M": "#FCA63F",      # Male - Orange
    "Unknown": "#D3D3D3" # Unknown - Light Gray
}

# Order for plotting (alphabetical F, M, Unknown)
GENDER_ORDER = ["F", "M", "Unknown"]

# Labels for plots
GENDER_LABELS = {
    "F": "Female",
    "M": "Male",
    "Unknown": "Unknown"
}


# =============================================================================
# CAREER STAGE COLORS (Warm to Cool Progression)
# =============================================================================

CAREER_STAGE_COLORS = {
    "Early": "#F59E0B",        # Amber/Orange - warmth, energy, beginning
    "Established": "#EAB308",  # Yellow - growth, development
    "Senior": "#06B6D4",       # Cyan - maturity, stability
    "Veteran": "#3B82F6",      # Blue - depth, experience
    "Emeritus": "#6366F1"      # Indigo - wisdom, legacy
}

# Order for plotting (career progression)
CAREER_STAGE_ORDER = ["Early", "Established", "Senior", "Veteran", "Emeritus"]


# =============================================================================
# CENTRALITY MEASURE COLORS
# =============================================================================

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

# Lowercase versions for flexibility
CENTRALITY_COLORS_LOWER = {k.lower(): v for k, v in CENTRALITY_COLORS.items()}


# =============================================================================
# AUTHOR TYPOLOGY COLORS (To be finalized after clustering in Phase 10)
# =============================================================================

# Placeholder - adjust after H3 analysis based on cluster interpretation
AUTHOR_TYPE_COLORS = {
    "Emerging Researchers": "#06AED5",    # Bright Cyan - growth potential
    "Productive Specialists": "#0C2D48",  # Deep Navy - focus
    "Network Connectors": "#EE6C4D",      # Coral Red - collaboration
    "Senior Leaders": "#BF1A2F",          # Deep Red - influence
    "Established Experts": "#386641",     # Forest Green - excellence
    "Peripheral Contributors": "#AA6C39"  # Bronze - niche
}


# =============================================================================
# SEQUENTIAL PALETTES (For heatmaps, gradients)
# =============================================================================

# Purple sequential (matches Female color)
PURPLE_SEQUENTIAL = ["#f7fcfd", "#e0ecf4", "#bfd3e6", "#9ebcda", "#8c96c6",
                     "#8c6bb1", "#88419d", "#810f7c", "#4d004b"]

# Orange sequential (matches Male color)
ORANGE_SEQUENTIAL = ["#fff5eb", "#fee6ce", "#fdd0a2", "#fdae6b", "#fd8d3c",
                     "#f16913", "#d94801", "#a63603", "#7f2704"]


# =============================================================================
# DIVERGING PALETTES (For showing differences)
# =============================================================================

# Purple-Orange diverging (for gender gaps: F negative, M positive)
PURPLE_ORANGE_DIVERGING_11 = [
    "#6a00ff",  # Strong Female (most negative)
    "#8c4aff",
    "#ae94ff",
    "#c9b8ff",
    "#e4ddff",
    "#FFFFFF",  # Neutral
    "#ffe4d4",
    "#ffc9a9",
    "#ffae7e",
    "#ff9353",
    "#FCA63F"   # Strong Male (most positive)
]


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_gender_color(gender: str) -> str:
    """
    Get color for a gender value.

    Parameters
    ----------
    gender : str
        Gender value ('F', 'M', or 'Unknown')

    Returns
    -------
    str
        Hex color code
    """
    return GENDER_COLORS.get(gender, GENDER_COLORS["Unknown"])


def get_career_stage_color(stage: str) -> str:
    """
    Get color for a career stage.

    Parameters
    ----------
    stage : str
        Career stage name

    Returns
    -------
    str
        Hex color code
    """
    return CAREER_STAGE_COLORS.get(stage, "#CCCCCC")


def get_centrality_color(measure: str) -> str:
    """
    Get color for a centrality measure (case-insensitive).

    Parameters
    ----------
    measure : str
        Centrality measure name

    Returns
    -------
    str
        Hex color code
    """
    # Try exact match first
    if measure in CENTRALITY_COLORS:
        return CENTRALITY_COLORS[measure]
    # Try lowercase
    return CENTRALITY_COLORS_LOWER.get(measure.lower(), "#CCCCCC")


# =============================================================================
# COLOR PALETTE VALIDATION
# =============================================================================

def validate_colorblind_safe():
    """
    Placeholder for colorblind safety validation.

    Use external tools like Coblis or Viz Palette to test:
    - https://www.color-blindness.com/coblis-color-blindness-simulator/
    - https://projects.susielu.com/viz-palette

    All palettes in this module have been tested for deuteranopia.
    """
    pass


if __name__ == "__main__":
    # Print all palettes for verification
    print("Gender Colors:")
    for gender, color in GENDER_COLORS.items():
        print(f"  {gender}: {color}")

    print("\nCareer Stage Colors:")
    for stage, color in CAREER_STAGE_COLORS.items():
        print(f"  {stage}: {color}")

    print("\nCentrality Measure Colors:")
    for measure, color in CENTRALITY_COLORS.items():
        print(f"  {measure}: {color}")

    print("\nAuthor Type Colors:")
    for type_, color in AUTHOR_TYPE_COLORS.items():
        print(f"  {type_}: {color}")
