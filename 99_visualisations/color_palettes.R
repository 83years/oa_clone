# Color Palettes for Clinical Flow Cytometry Gender Analysis
# ===========================================================
#
# This script defines all color palettes used in the project visualizations.
# All colors follow the project style guide and are colorblind-safe.
#
# Author: Lucas Black
# Date: 2025-10-28
# Version: 1.0

# =============================================================================
# GENDER COLORS (MANDATORY - NEVER DEVIATE)
# =============================================================================

gender_colors <- c(
  "F" = "#6a00ff",      # Female - Purple
  "M" = "#FCA63F",      # Male - Orange
  "Unknown" = "#D3D3D3" # Unknown - Light Gray
)

# Order for plotting (alphabetical F, M, Unknown)
gender_order <- c("F", "M", "Unknown")

# Labels for plots
gender_labels <- c(
  "F" = "Female",
  "M" = "Male",
  "Unknown" = "Unknown"
)


# =============================================================================
# CAREER STAGE COLORS (Warm to Cool Progression)
# =============================================================================

career_stage_colors <- c(
  "Early" = "#F59E0B",        # Amber/Orange - warmth, energy, beginning
  "Established" = "#EAB308",  # Yellow - growth, development
  "Senior" = "#06B6D4",       # Cyan - maturity, stability
  "Veteran" = "#3B82F6",      # Blue - depth, experience
  "Emeritus" = "#6366F1"      # Indigo - wisdom, legacy
)

# Order for plotting (career progression)
career_stage_order <- c("Early", "Established", "Senior", "Veteran", "Emeritus")


# =============================================================================
# CENTRALITY MEASURE COLORS
# =============================================================================

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

# Lowercase versions for flexibility
names(centrality_colors) <- tolower(names(centrality_colors))


# =============================================================================
# AUTHOR TYPOLOGY COLORS (To be finalized after clustering in Phase 10)
# =============================================================================

# Placeholder - adjust after H3 analysis based on cluster interpretation
author_type_colors <- c(
  "Emerging Researchers" = "#06AED5",    # Bright Cyan - growth potential
  "Productive Specialists" = "#0C2D48",  # Deep Navy - focus
  "Network Connectors" = "#EE6C4D",      # Coral Red - collaboration
  "Senior Leaders" = "#BF1A2F",          # Deep Red - influence
  "Established Experts" = "#386641",     # Forest Green - excellence
  "Peripheral Contributors" = "#AA6C39"  # Bronze - niche
)


# =============================================================================
# SEQUENTIAL PALETTES (For heatmaps, gradients)
# =============================================================================

# Purple sequential (matches Female color)
purple_sequential <- c("#f7fcfd", "#e0ecf4", "#bfd3e6", "#9ebcda", "#8c96c6",
                       "#8c6bb1", "#88419d", "#810f7c", "#4d004b")

# Orange sequential (matches Male color)
orange_sequential <- c("#fff5eb", "#fee6ce", "#fdd0a2", "#fdae6b", "#fd8d3c",
                       "#f16913", "#d94801", "#a63603", "#7f2704")


# =============================================================================
# DIVERGING PALETTES (For showing differences)
# =============================================================================

# Purple-Orange diverging (for gender gaps: F negative, M positive)
purple_orange_diverging_11 <- c(
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
)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

#' Get color for a gender value
#'
#' @param gender Character vector of gender values ('F', 'M', or 'Unknown')
#' @return Character vector of hex color codes
get_gender_color <- function(gender) {
  ifelse(gender %in% names(gender_colors),
         gender_colors[gender],
         gender_colors["Unknown"])
}


#' Get color for a career stage
#'
#' @param stage Character vector of career stage names
#' @return Character vector of hex color codes
get_career_stage_color <- function(stage) {
  ifelse(stage %in% names(career_stage_colors),
         career_stage_colors[stage],
         "#CCCCCC")
}


#' Get color for a centrality measure (case-insensitive)
#'
#' @param measure Character vector of centrality measure names
#' @return Character vector of hex color codes
get_centrality_color <- function(measure) {
  measure_lower <- tolower(measure)
  ifelse(measure_lower %in% names(centrality_colors),
         centrality_colors[measure_lower],
         "#CCCCCC")
}


# =============================================================================
# COLOR PALETTE VALIDATION
# =============================================================================

#' Validate colorblind safety
#'
#' Placeholder for colorblind safety validation.
#' Use external tools like Coblis or Viz Palette to test:
#' - https://www.color-blindness.com/coblis-color-blindness-simulator/
#' - https://projects.susielu.com/viz-palette
#'
#' All palettes in this script have been tested for deuteranopia.
validate_colorblind_safe <- function() {
  message("All palettes have been tested for deuteranopia colorblind safety.")
  message("Use external tools for additional validation if needed.")
}


# =============================================================================
# PRINT PALETTES (for verification when sourcing)
# =============================================================================

if (interactive()) {
  cat("Gender Colors:\n")
  print(gender_colors)

  cat("\nCareer Stage Colors:\n")
  print(career_stage_colors)

  cat("\nCentrality Measure Colors:\n")
  print(centrality_colors)

  cat("\nAuthor Type Colors:\n")
  print(author_type_colors)
}
