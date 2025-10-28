# ggplot2 Themes for Clinical Flow Cytometry Gender Analysis
# ============================================================
#
# This script provides custom ggplot2 themes that enforce the project style guide.
# Apply these themes at the start of plotting scripts to ensure consistency.
#
# Author: Lucas Black
# Date: 2025-10-28
# Version: 1.0

library(ggplot2)

# =============================================================================
# FIGURE DIMENSIONS
# =============================================================================

FIGURE_WIDTH <- 13.33  # inches
FIGURE_HEIGHT <- 7.5   # inches
FIGURE_DPI <- 150

# Multi-panel figure dimensions
FIGURE_2x1_WIDTH <- 13.33
FIGURE_2x1_HEIGHT <- 7.5
FIGURE_1x2_WIDTH <- 13.33
FIGURE_1x2_HEIGHT <- 7.5
FIGURE_2x2_WIDTH <- 13.33
FIGURE_2x2_HEIGHT <- 7.5


# =============================================================================
# FONT SIZES
# =============================================================================

FONT_SIZE_AXIS_TITLE <- 14
FONT_SIZE_AXIS_LABEL <- 12
FONT_SIZE_LEGEND_TITLE <- 12
FONT_SIZE_LEGEND_TEXT <- 10
FONT_SIZE_PLOT_TITLE <- 16
FONT_SIZE_ANNOTATION <- 10
FONT_SIZE_PANEL_LABEL <- 18


# =============================================================================
# PROJECT THEME
# =============================================================================

#' Apply project-wide ggplot2 theme
#'
#' This creates a custom theme that matches the style guide specifications.
#' Call this at the start of any plotting script using theme_set().
#'
#' @param base_size Base font size (default: 12)
#' @param base_family Base font family (default: "Arial")
#' @return A ggplot2 theme object
#'
#' @examples
#' library(ggplot2)
#' theme_set(theme_project())
#' # Now all plots will use project theme
theme_project <- function(base_size = 12, base_family = "Arial") {
  theme_minimal(base_size = base_size, base_family = base_family) +
    theme(
      # Axis titles (bold, size 14)
      axis.title = element_text(
        size = FONT_SIZE_AXIS_TITLE,
        face = "bold",
        color = "black"
      ),

      # Axis text (size 12)
      axis.text = element_text(
        size = FONT_SIZE_AXIS_LABEL,
        color = "black"
      ),

      # Plot title (bold, size 16, centered)
      plot.title = element_text(
        size = FONT_SIZE_PLOT_TITLE,
        face = "bold",
        hjust = 0.5,
        color = "black"
      ),

      # Legend title (bold, size 12)
      legend.title = element_text(
        size = FONT_SIZE_LEGEND_TITLE,
        face = "bold",
        color = "black"
      ),

      # Legend text (size 10)
      legend.text = element_text(
        size = FONT_SIZE_LEGEND_TEXT,
        color = "black"
      ),

      # Legend position (bottom by default, can override)
      legend.position = "bottom",

      # Legend background
      legend.background = element_rect(
        fill = "white",
        color = "#CCCCCC",
        size = 0.5
      ),

      # Panel grid (no minor grid, major grid dashed)
      panel.grid.minor = element_blank(),
      panel.grid.major = element_line(
        color = "gray90",
        linetype = "dashed",
        size = 0.5
      ),

      # Panel background
      panel.background = element_rect(fill = "white", color = NA),

      # Plot background
      plot.background = element_rect(fill = "white", color = NA),

      # Facet strip text (for multi-panel plots)
      strip.text = element_text(
        size = FONT_SIZE_AXIS_LABEL,
        face = "bold",
        color = "black"
      ),

      strip.background = element_rect(
        fill = "#F0F0F0",
        color = "#CCCCCC",
        size = 0.5
      )
    )
}


#' Set project theme globally
#'
#' Convenience function to set project theme for all subsequent plots.
#'
#' @examples
#' set_project_theme()
#' # All plots now use project theme
set_project_theme <- function() {
  theme_set(theme_project())
  message("Project theme applied successfully.")
}


#' Reset to default ggplot2 theme
#'
#' @examples
#' reset_theme()
reset_theme <- function() {
  theme_set(theme_gray())
  message("ggplot2 reset to default theme.")
}


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

#' Save figure in multiple formats following project standards
#'
#' @param plot ggplot object to save
#' @param filename Base filename (without extension)
#' @param width Figure width in inches (default: 13.33)
#' @param height Figure height in inches (default: 7.5)
#' @param dpi Resolution (default: 150)
#' @param formats Vector of formats to save (default: c("png", "pdf"))
#'
#' @examples
#' p <- ggplot(mtcars, aes(mpg, wt)) + geom_point()
#' save_figure(p, "figures/fig1_example_v1")
save_figure <- function(plot,
                        filename,
                        width = FIGURE_WIDTH,
                        height = FIGURE_HEIGHT,
                        dpi = FIGURE_DPI,
                        formats = c("png", "pdf")) {

  for (fmt in formats) {
    output_path <- paste0(filename, ".", fmt)
    ggsave(
      output_path,
      plot = plot,
      width = width,
      height = height,
      dpi = dpi,
      units = "in",
      bg = "white"
    )
    message("Saved: ", output_path)
  }
}


#' Add panel label to plot
#'
#' @param label Panel label (e.g., "A", "B", "C")
#' @param x X position in npc coordinates (default: 0.02)
#' @param y Y position in npc coordinates (default: 0.98)
#' @param size Font size (default: 18)
#' @param fontface Font face (default: "bold")
#' @return A geom_text layer
#'
#' @examples
#' library(ggplot2)
#' ggplot(mtcars, aes(mpg, wt)) +
#'   geom_point() +
#'   add_panel_label("A")
add_panel_label <- function(label,
                             x = 0.02,
                             y = 0.98,
                             size = FONT_SIZE_PANEL_LABEL,
                             fontface = "bold") {
  annotate(
    "text",
    x = x,
    y = y,
    label = label,
    size = size / .pt,  # Convert to mm
    fontface = fontface,
    hjust = 0,
    vjust = 1
  )
}


#' Add sample size text to plot
#'
#' @param text Sample size text (e.g., "F: n = 120,000 | M: n = 150,000")
#' @param x X position in npc coordinates (default: 0.5, centered)
#' @param y Y position in npc coordinates (default: 0.95)
#' @param size Font size (default: 10)
#' @param color Text color (default: "#4B5563")
#' @return An annotation layer
#'
#' @examples
#' library(ggplot2)
#' ggplot(mtcars, aes(mpg, wt)) +
#'   geom_point() +
#'   add_sample_size_text("n = 32")
add_sample_size_text <- function(text,
                                  x = 0.5,
                                  y = 0.95,
                                  size = FONT_SIZE_ANNOTATION,
                                  color = "#4B5563") {
  annotate(
    "text",
    x = x,
    y = y,
    label = text,
    size = size / .pt,
    fontface = "italic",
    color = color,
    hjust = 0.5,
    vjust = 1
  )
}


#' Add significance bracket with star notation
#'
#' @param x1 X position of left end (data coordinates)
#' @param x2 X position of right end (data coordinates)
#' @param y Y position of bracket (data coordinates)
#' @param text Significance text (e.g., "***", "**", "*", "ns")
#' @param size Font size (default: 10)
#' @return A list of annotation layers
#'
#' @examples
#' library(ggplot2)
#' ggplot(mtcars, aes(factor(cyl), mpg)) +
#'   geom_boxplot() +
#'   add_significance_bracket(1, 2, 35, "***")
add_significance_bracket <- function(x1,
                                      x2,
                                      y,
                                      text,
                                      size = FONT_SIZE_ANNOTATION) {
  list(
    # Bracket line
    annotate(
      "segment",
      x = x1,
      xend = x2,
      y = y,
      yend = y,
      color = "black",
      size = 0.5
    ),
    # Text
    annotate(
      "text",
      x = (x1 + x2) / 2,
      y = y,
      label = text,
      size = size / .pt,
      vjust = -0.5,
      hjust = 0.5
    )
  )
}


#' Enable/disable grid on specific axis
#'
#' @param axis Which axis: "y", "x", or "both" (default: "y")
#' @return A theme modification
#'
#' @examples
#' library(ggplot2)
#' ggplot(mtcars, aes(mpg, wt)) +
#'   geom_point() +
#'   enable_grid("y")
enable_grid <- function(axis = "y") {
  if (axis == "y") {
    theme(
      panel.grid.major.y = element_line(
        color = "gray90",
        linetype = "dashed",
        size = 0.5
      ),
      panel.grid.major.x = element_blank()
    )
  } else if (axis == "x") {
    theme(
      panel.grid.major.x = element_line(
        color = "gray90",
        linestyle = "dashed",
        size = 0.5
      ),
      panel.grid.major.y = element_blank()
    )
  } else if (axis == "both") {
    theme(
      panel.grid.major = element_line(
        color = "gray90",
        linetype = "dashed",
        size = 0.5
      )
    )
  }
}


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if (interactive()) {
  library(ggplot2)

  # Apply project theme
  set_project_theme()

  # Source color palettes
  source("color_palettes.R")

  # Create example plot
  example_data <- data.frame(
    gender = c("F", "M"),
    centrality = c(12.4, 15.1),
    n = c(120000, 150000)
  )

  p <- ggplot(example_data, aes(x = gender, y = centrality, fill = gender)) +
    geom_bar(stat = "identity") +
    scale_fill_manual(
      values = gender_colors,
      labels = gender_labels
    ) +
    scale_x_discrete(labels = c("F" = "Female", "M" = "Male")) +
    labs(
      x = "Inferred Gender",
      y = "Mean Degree Centrality",
      title = "Example Plot with Project Theme",
      fill = "Inferred Gender"
    ) +
    add_sample_size_text("F: n = 120,000 | M: n = 150,000") +
    add_significance_bracket(1, 2, max(example_data$centrality) * 1.1, "***") +
    enable_grid("y")

  print(p)

  # Save figure
  save_figure(p, "example_plot_with_theme_R")

  cat("\nExample plot created successfully!\n")
  cat("Check example_plot_with_theme_R.png and example_plot_with_theme_R.pdf\n")
}
