#!/usr/bin/env Rscript
# Exploratory Data Analysis: Author Publications by Year
#
# This script analyzes the author_publications_by_year DuckDB database
# and generates comprehensive summary statistics and visualizations.
#
# Output:
# - Console output with summary statistics
# - PDF file with multiple plots in the datasets/ folder

# Load required libraries
library(duckdb)
library(dplyr)
library(ggplot2)
library(tidyr)
library(scales)
library(gridExtra)
library(patchwork)

# Suppress warnings for cleaner output
options(warn = -1)

# Configuration
cat("======================================================================\n")
cat("EXPLORATORY DATA ANALYSIS: AUTHOR PUBLICATIONS BY YEAR\n")
cat("======================================================================\n\n")

# Set paths
# Get script directory (works for both Rscript and source())
get_script_dir <- function() {
  cmdArgs <- commandArgs(trailingOnly = FALSE)
  needle <- "--file="
  match <- grep(needle, cmdArgs)
  if (length(match) > 0) {
    # Rscript
    return(dirname(normalizePath(sub(needle, "", cmdArgs[match]))))
  } else {
    # Running interactively or sourced
    return(getwd())
  }
}

script_dir <- get_script_dir()
datasets_dir <- file.path(script_dir, "datasets")
db_file <- file.path(datasets_dir, "author_publications_by_year_20251207_122429.duckdb")
output_pdf <- file.path(datasets_dir, paste0("eda_plots_", format(Sys.time(), "%Y%m%d_%H%M%S"), ".pdf"))

cat(sprintf("Database file: %s\n", db_file))
cat(sprintf("Output PDF: %s\n\n", output_pdf))

# Connect to DuckDB
cat("Connecting to DuckDB...\n")
con <- dbConnect(duckdb::duckdb(), dbdir = db_file, read_only = TRUE)

# Load data
cat("Loading data...\n")
df <- dbGetQuery(con, "SELECT * FROM author_publications_by_year")
cat(sprintf("Loaded %s records\n\n", format(nrow(df), big.mark = ",")))

# Close connection
dbDisconnect(con, shutdown = TRUE)

# ============================================================================
# SECTION 1: BASIC SUMMARY STATISTICS
# ============================================================================
cat("======================================================================\n")
cat("SECTION 1: BASIC SUMMARY STATISTICS\n")
cat("======================================================================\n\n")

cat("Dataset Dimensions:\n")
cat(sprintf("  Total records (author-year pairs): %s\n", format(nrow(df), big.mark = ",")))
cat(sprintf("  Unique authors: %s\n", format(length(unique(df$author_id)), big.mark = ",")))
cat(sprintf("  Year range: %d - %d\n", min(df$publication_year), max(df$publication_year)))
cat(sprintf("  Total works across all authors: %s\n\n", format(sum(df$works_count), big.mark = ",")))

# Calculate author-level statistics
author_stats <- df %>%
  group_by(author_id) %>%
  slice(1) %>%
  ungroup() %>%
  select(author_id, total_career_works, career_length_years, first_pub_year, last_pub_year)

cat("Career Statistics:\n")
cat(sprintf("  Mean career length: %.1f years\n", mean(author_stats$career_length_years)))
cat(sprintf("  Median career length: %.1f years\n", median(author_stats$career_length_years)))
cat(sprintf("  Max career length: %d years\n", max(author_stats$career_length_years)))
cat(sprintf("  Min career length: %d years\n\n", min(author_stats$career_length_years)))

cat("Productivity Statistics:\n")
cat(sprintf("  Mean total works per author: %.1f\n", mean(author_stats$total_career_works)))
cat(sprintf("  Median total works per author: %.1f\n", median(author_stats$total_career_works)))
cat(sprintf("  Max total works per author: %d\n", max(author_stats$total_career_works)))
cat(sprintf("  Min total works per author: %d\n\n", min(author_stats$total_career_works)))

# Quantiles
cat("Total Works Quantiles:\n")
quantiles <- quantile(author_stats$total_career_works, probs = seq(0, 1, 0.1))
for (i in seq_along(quantiles)) {
  cat(sprintf("  %3d%%: %6.1f works\n", (i-1)*10, quantiles[i]))
}
cat("\n")

cat("Career Length Quantiles:\n")
quantiles_career <- quantile(author_stats$career_length_years, probs = seq(0, 1, 0.1))
for (i in seq_along(quantiles_career)) {
  cat(sprintf("  %3d%%: %6.1f years\n", (i-1)*10, quantiles_career[i]))
}
cat("\n")

# ============================================================================
# SECTION 2: TEMPORAL ANALYSIS
# ============================================================================
cat("======================================================================\n")
cat("SECTION 2: TEMPORAL ANALYSIS\n")
cat("======================================================================\n\n")

# Publications by year
pubs_by_year <- df %>%
  group_by(publication_year) %>%
  summarise(
    total_works = sum(works_count),
    num_authors = n(),
    .groups = "drop"
  ) %>%
  arrange(publication_year)

cat("Publication Trends:\n")
cat(sprintf("  Peak year (most works): %d (%s works)\n",
            pubs_by_year$publication_year[which.max(pubs_by_year$total_works)],
            format(max(pubs_by_year$total_works), big.mark = ",")))
cat(sprintf("  Peak year (most authors): %d (%s authors)\n\n",
            pubs_by_year$publication_year[which.max(pubs_by_year$num_authors)],
            format(max(pubs_by_year$num_authors), big.mark = ",")))

# Recent trends (last 10 years)
recent_years <- pubs_by_year %>%
  filter(publication_year >= max(publication_year) - 10)

cat("Recent Trends (Last 10 Years):\n")
for (i in 1:nrow(recent_years)) {
  cat(sprintf("  %d: %7s works from %6s authors\n",
              recent_years$publication_year[i],
              format(recent_years$total_works[i], big.mark = ","),
              format(recent_years$num_authors[i], big.mark = ",")))
}
cat("\n")

# ============================================================================
# SECTION 3: PRODUCTIVITY PATTERNS
# ============================================================================
cat("======================================================================\n")
cat("SECTION 3: PRODUCTIVITY PATTERNS\n")
cat("======================================================================\n\n")

# Calculate publications per year across career
author_productivity <- df %>%
  group_by(author_id) %>%
  summarise(
    mean_pubs_per_year = mean(works_count),
    max_pubs_in_year = max(works_count),
    total_active_years = n(),
    career_length = first(career_length_years),
    total_works = first(total_career_works),
    .groups = "drop"
  )

cat("Productivity Metrics:\n")
cat(sprintf("  Mean publications per active year: %.2f\n", mean(author_productivity$mean_pubs_per_year)))
cat(sprintf("  Median publications per active year: %.2f\n", median(author_productivity$mean_pubs_per_year)))
cat(sprintf("  Mean max publications in single year: %.2f\n", mean(author_productivity$max_pubs_in_year)))
cat(sprintf("  Overall max publications in single year: %d\n\n", max(author_productivity$max_pubs_in_year)))

# Activity vs Career Length
cat("Activity Analysis:\n")
cat(sprintf("  Mean active years: %.1f\n", mean(author_productivity$total_active_years)))
cat(sprintf("  Mean career length: %.1f\n", mean(author_productivity$career_length)))
cat(sprintf("  Mean activity rate: %.1f%%\n\n",
            mean(author_productivity$total_active_years / (author_productivity$career_length + 1)) * 100))

# ============================================================================
# SECTION 4: CREATE VISUALIZATIONS
# ============================================================================
cat("======================================================================\n")
cat("SECTION 4: GENERATING VISUALIZATIONS\n")
cat("======================================================================\n\n")

cat("Creating plots...\n")

# Start PDF
pdf(output_pdf, width = 11, height = 8.5)

# Define theme
theme_custom <- theme_minimal() +
  theme(
    plot.title = element_text(size = 14, face = "bold"),
    plot.subtitle = element_text(size = 10, color = "gray40"),
    axis.title = element_text(size = 11),
    axis.text = element_text(size = 9),
    legend.position = "bottom"
  )

# PLOT 1: Distribution of Total Career Works
p1 <- ggplot(author_stats, aes(x = total_career_works)) +
  geom_histogram(bins = 50, fill = "steelblue", color = "white", alpha = 0.7) +
  scale_x_continuous(breaks = seq(0, max(author_stats$total_career_works), by = 20)) +
  labs(
    title = "Distribution of Total Career Works per Author",
    subtitle = sprintf("Based on %s authors", format(nrow(author_stats), big.mark = ",")),
    x = "Total Career Works",
    y = "Number of Authors"
  ) +
  theme_custom

# PLOT 2: Distribution of Career Length
p2 <- ggplot(author_stats, aes(x = career_length_years)) +
  geom_histogram(bins = 40, fill = "coral", color = "white", alpha = 0.7) +
  labs(
    title = "Distribution of Career Length",
    subtitle = sprintf("Mean: %.1f years, Median: %.1f years",
                       mean(author_stats$career_length_years),
                       median(author_stats$career_length_years)),
    x = "Career Length (years)",
    y = "Number of Authors"
  ) +
  theme_custom

# PLOT 3: Log-scale total works
p3 <- ggplot(author_stats, aes(x = total_career_works)) +
  geom_histogram(bins = 50, fill = "forestgreen", color = "white", alpha = 0.7) +
  scale_x_log10(labels = comma) +
  labs(
    title = "Distribution of Total Career Works (Log Scale)",
    subtitle = "Shows spread across orders of magnitude",
    x = "Total Career Works (log scale)",
    y = "Number of Authors"
  ) +
  theme_custom

# PLOT 4: Career length vs Total works
p4 <- ggplot(author_stats, aes(x = career_length_years, y = total_career_works)) +
  geom_bin2d(bins = 50) +
  scale_fill_viridis_c(trans = "log10", name = "Count") +
  labs(
    title = "Career Length vs Total Works",
    subtitle = "Hexbin density plot",
    x = "Career Length (years)",
    y = "Total Career Works"
  ) +
  theme_custom

# Print page 1
print((p1 | p2) / (p3 | p4))

# PLOT 5: Publications over time (aggregate)
p5 <- ggplot(pubs_by_year, aes(x = publication_year, y = total_works)) +
  geom_line(color = "steelblue", size = 1) +
  geom_point(color = "steelblue", size = 2, alpha = 0.6) +
  scale_y_continuous(labels = comma) +
  labs(
    title = "Total Publications by Year",
    subtitle = "Aggregate publication output across all authors",
    x = "Publication Year",
    y = "Total Works"
  ) +
  theme_custom

# PLOT 6: Number of authors publishing by year
p6 <- ggplot(pubs_by_year, aes(x = publication_year, y = num_authors)) +
  geom_line(color = "coral", size = 1) +
  geom_point(color = "coral", size = 2, alpha = 0.6) +
  scale_y_continuous(labels = comma) +
  labs(
    title = "Authors Publishing by Year",
    subtitle = "Number of authors with at least one publication per year",
    x = "Publication Year",
    y = "Number of Authors"
  ) +
  theme_custom

# PLOT 7: Recent trends (last 30 years)
recent_30 <- pubs_by_year %>%
  filter(publication_year >= max(publication_year) - 30)

p7 <- ggplot(recent_30, aes(x = publication_year, y = total_works)) +
  geom_area(fill = "steelblue", alpha = 0.5) +
  geom_line(color = "steelblue", size = 1) +
  scale_y_continuous(labels = comma) +
  labs(
    title = "Publication Trends: Last 30 Years",
    subtitle = "Total works published per year",
    x = "Publication Year",
    y = "Total Works"
  ) +
  theme_custom

# PLOT 8: First publication year distribution
p8 <- ggplot(author_stats, aes(x = first_pub_year)) +
  geom_histogram(bins = 50, fill = "forestgreen", color = "white", alpha = 0.7) +
  labs(
    title = "Distribution of First Publication Year",
    subtitle = "When did authors start publishing?",
    x = "First Publication Year",
    y = "Number of Authors"
  ) +
  theme_custom

# Print page 2
print((p5 | p6) / (p7 | p8))

# PLOT 9: Productivity metrics
p9 <- ggplot(author_productivity, aes(x = mean_pubs_per_year)) +
  geom_histogram(bins = 40, fill = "purple", color = "white", alpha = 0.7) +
  scale_x_continuous(limits = c(0, quantile(author_productivity$mean_pubs_per_year, 0.99))) +
  labs(
    title = "Mean Publications per Active Year",
    subtitle = "Average productivity across career (99th percentile cutoff)",
    x = "Mean Publications per Year",
    y = "Number of Authors"
  ) +
  theme_custom

# PLOT 10: Max publications in a single year
p10 <- ggplot(author_productivity, aes(x = max_pubs_in_year)) +
  geom_histogram(bins = 40, fill = "orange", color = "white", alpha = 0.7) +
  scale_x_continuous(limits = c(0, quantile(author_productivity$max_pubs_in_year, 0.99))) +
  labs(
    title = "Maximum Publications in a Single Year",
    subtitle = "Peak productivity (99th percentile cutoff)",
    x = "Max Publications in One Year",
    y = "Number of Authors"
  ) +
  theme_custom

# PLOT 11: Active years vs career length
p11 <- ggplot(author_productivity, aes(x = career_length, y = total_active_years)) +
  geom_bin2d(bins = 40) +
  geom_abline(slope = 1, intercept = 1, color = "red", linetype = "dashed", size = 1) +
  scale_fill_viridis_c(trans = "log10", name = "Count") +
  labs(
    title = "Active Years vs Career Length",
    subtitle = "Red line = 100% activity rate (publishing every year)",
    x = "Career Length (years)",
    y = "Total Active Years"
  ) +
  theme_custom

# PLOT 12: Activity rate distribution
author_productivity <- author_productivity %>%
  mutate(activity_rate = total_active_years / (career_length + 1))

p12 <- ggplot(author_productivity, aes(x = activity_rate * 100)) +
  geom_histogram(bins = 40, fill = "darkgreen", color = "white", alpha = 0.7) +
  labs(
    title = "Publication Activity Rate",
    subtitle = "Percentage of years with at least one publication",
    x = "Activity Rate (%)",
    y = "Number of Authors"
  ) +
  theme_custom

# Print page 3
print((p9 | p10) / (p11 | p12))

# PLOT 13: Last publication year distribution
p13 <- ggplot(author_stats, aes(x = last_pub_year)) +
  geom_histogram(bins = 50, fill = "royalblue", color = "white", alpha = 0.7) +
  labs(
    title = "Distribution of Last Publication Year",
    subtitle = "When did authors last publish?",
    x = "Last Publication Year",
    y = "Number of Authors"
  ) +
  theme_custom

# PLOT 14: Box plot of works by decade of first publication
author_stats <- author_stats %>%
  mutate(first_pub_decade = floor(first_pub_year / 10) * 10)

p14 <- author_stats %>%
  filter(first_pub_decade >= 1960) %>%
  ggplot(aes(x = factor(first_pub_decade), y = total_career_works)) +
  geom_boxplot(fill = "coral", alpha = 0.7, outlier.alpha = 0.3) +
  scale_y_log10() +
  labs(
    title = "Career Works by First Publication Decade",
    subtitle = "Log scale, showing variation by cohort",
    x = "First Publication Decade",
    y = "Total Career Works (log scale)"
  ) +
  theme_custom +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))

# PLOT 15: Violin plot of career length by decade
p15 <- author_stats %>%
  filter(first_pub_decade >= 1960) %>%
  ggplot(aes(x = factor(first_pub_decade), y = career_length_years)) +
  geom_violin(fill = "steelblue", alpha = 0.7) +
  geom_boxplot(width = 0.1, fill = "white", alpha = 0.8, outlier.alpha = 0.3) +
  labs(
    title = "Career Length by First Publication Decade",
    subtitle = "Violin plot with embedded boxplot",
    x = "First Publication Decade",
    y = "Career Length (years)"
  ) +
  theme_custom +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))

# PLOT 16: Publications per year over time (mean)
yearly_productivity <- df %>%
  group_by(publication_year) %>%
  summarise(
    mean_works_per_author = mean(works_count),
    median_works_per_author = median(works_count),
    .groups = "drop"
  )

p16 <- ggplot(yearly_productivity, aes(x = publication_year)) +
  geom_line(aes(y = mean_works_per_author, color = "Mean"), size = 1) +
  geom_line(aes(y = median_works_per_author, color = "Median"), size = 1) +
  scale_color_manual(values = c("Mean" = "coral", "Median" = "steelblue"), name = "") +
  labs(
    title = "Average Publications per Author-Year",
    subtitle = "Mean vs Median productivity per year",
    x = "Publication Year",
    y = "Publications per Author"
  ) +
  theme_custom

# Print page 4
print((p13 | p14) / (p15 | p16))

# Close PDF
dev.off()

# ============================================================================
# SECTION 5: SUMMARY REPORT
# ============================================================================
cat("\n======================================================================\n")
cat("ANALYSIS COMPLETE\n")
cat("======================================================================\n\n")

cat("Key Findings:\n")
cat(sprintf("  1. Analyzed %s authors with %s total publications\n",
            format(nrow(author_stats), big.mark = ","),
            format(sum(author_stats$total_career_works), big.mark = ",")))
cat(sprintf("  2. Average career length: %.1f years (median: %.1f)\n",
            mean(author_stats$career_length_years),
            median(author_stats$career_length_years)))
cat(sprintf("  3. Average total works: %.1f (median: %.1f)\n",
            mean(author_stats$total_career_works),
            median(author_stats$total_career_works)))
cat(sprintf("  4. Average productivity: %.2f publications per active year\n",
            mean(author_productivity$mean_pubs_per_year)))
cat(sprintf("  5. Average activity rate: %.1f%% of career years\n",
            mean(author_productivity$activity_rate) * 100))
cat(sprintf("  6. Publication years span: %d to %d\n",
            min(df$publication_year), max(df$publication_year)))
cat("\n")

cat(sprintf("Output saved to: %s\n", output_pdf))
cat("\nScript completed successfully!\n")
