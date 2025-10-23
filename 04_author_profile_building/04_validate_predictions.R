# ==============================================================================
# Step 4: Validate Gender Predictions
# ==============================================================================
# This script:
# 1. Loads final predictions
# 2. Calculates comprehensive validation statistics
# 3. Analyzes coverage, confidence, and regional patterns
# 4. Identifies ambiguous names and quality issues
# 5. Generates detailed HTML report (optional)
# ==============================================================================

suppressPackageStartupMessages({
  library(dplyr)
  library(stringr)
  library(tidyr)
  library(ggplot2)
})

source("utils.R")

# ==============================================================================
# VALIDATION FUNCTIONS
# ==============================================================================

#' Calculate overall coverage statistics
#'
#' @param data Predictions data frame
#' @return List with coverage stats
calculate_coverage_stats <- function(data) {
  stats <- list(
    total_records = nrow(data),
    unique_authors = n_distinct(data$author_id),
    unique_forenames = n_distinct(data$forename),

    # Coverage by method
    cache_coverage = sum(!is.na(data$gender_cache)),
    gender_r_coverage = sum(!is.na(data$gender_r)),
    guesser_coverage = sum(!is.na(data$gender_guesser)),
    genderize_coverage = sum(!is.na(data$gender_genderize), na.rm = TRUE),

    # Overall coverage
    consensus_coverage = sum(!is.na(data$consensus_gender)),
    any_prediction = sum(data$methods_predicted > 0, na.rm = TRUE),

    # Quality metrics
    high_confidence = sum(
      pmax(data$prob_cache, data$prob_r, data$prob_guesser, data$prob_genderize, na.rm = TRUE) >= 0.8,
      na.rm = TRUE
    ),
    has_mismatch = sum(data$has_mismatch, na.rm = TRUE)
  )

  # Calculate percentages
  stats$cache_pct <- round(stats$cache_coverage / stats$total_records * 100, 2)
  stats$gender_r_pct <- round(stats$gender_r_coverage / stats$total_records * 100, 2)
  stats$guesser_pct <- round(stats$guesser_coverage / stats$total_records * 100, 2)
  stats$genderize_pct <- round(stats$genderize_coverage / stats$total_records * 100, 2)
  stats$consensus_pct <- round(stats$consensus_coverage / stats$total_records * 100, 2)
  stats$any_prediction_pct <- round(stats$any_prediction / stats$total_records * 100, 2)

  return(stats)
}

#' Analyze method agreement
#'
#' @param data Predictions data frame
#' @return Data frame with agreement analysis
analyze_method_agreement <- function(data) {
  # Calculate agreement for records with 2+ predictions
  agreement_data <- data %>%
    filter(methods_predicted >= 2) %>%
    mutate(
      all_agree = unique_genders == 1,
      partial_agree = unique_genders > 1
    )

  agreement_stats <- data.frame(
    total_with_multiple = nrow(agreement_data),
    all_agree = sum(agreement_data$all_agree),
    partial_disagree = sum(agreement_data$partial_agree),
    agreement_rate = round(sum(agreement_data$all_agree) / nrow(agreement_data) * 100, 2)
  )

  return(agreement_stats)
}

#' Analyze confidence distribution
#'
#' @param data Predictions data frame
#' @return Data frame with confidence analysis
analyze_confidence_distribution <- function(data) {
  # Get maximum confidence across all methods for each record
  confidence_data <- data %>%
    mutate(
      max_confidence = pmax(prob_cache, prob_r, prob_guesser, prob_genderize, na.rm = TRUE)
    ) %>%
    filter(!is.na(max_confidence)) %>%
    mutate(
      confidence_category = cut(
        max_confidence,
        breaks = c(0, 0.4, 0.6, 0.8, 1.0),
        labels = c("Low (<40%)", "Medium (40-60%)", "High (60-80%)", "Very High (80%+)"),
        include.lowest = TRUE
      )
    )

  confidence_summary <- confidence_data %>%
    count(confidence_category) %>%
    mutate(percentage = round(n / sum(n) * 100, 2))

  return(confidence_summary)
}

#' Analyze regional patterns
#'
#' @param data Predictions data frame
#' @param config Configuration list
#' @return Data frame with regional analysis
analyze_regional_patterns <- function(data, config) {
  # Map countries to regions
  regions_config <- config$validation$regions

  region_mapping <- data.frame()
  for (region_name in names(regions_config)) {
    region_codes <- regions_config[[region_name]]
    region_mapping <- bind_rows(
      region_mapping,
      data.frame(
        country_code = region_codes,
        region = region_name,
        stringsAsFactors = FALSE
      )
    )
  }

  # Join with data
  regional_data <- data %>%
    filter(!is.na(country_code)) %>%
    left_join(region_mapping, by = "country_code") %>%
    mutate(region = ifelse(is.na(region), "Other", region))

  # Calculate regional statistics
  regional_stats <- regional_data %>%
    group_by(region) %>%
    summarise(
      total_authors = n(),
      with_prediction = sum(!is.na(consensus_gender)),
      coverage_rate = round(with_prediction / total_authors * 100, 2),
      male_count = sum(consensus_gender == "M", na.rm = TRUE),
      female_count = sum(consensus_gender == "F", na.rm = TRUE),
      male_pct = round(male_count / with_prediction * 100, 2),
      female_pct = round(female_count / with_prediction * 100, 2),
      .groups = "drop"
    ) %>%
    arrange(desc(total_authors))

  return(regional_stats)
}

#' Identify top ambiguous names
#'
#' @param data Predictions data frame
#' @param top_n Number of names to return
#' @return Data frame with ambiguous names
identify_ambiguous_names <- function(data, top_n = 20) {
  ambiguous <- data %>%
    filter(has_mismatch) %>%
    group_by(forename, mismatch_detail) %>%
    summarise(
      count = n(),
      countries = paste(unique(country_code[!is.na(country_code)]), collapse = ", "),
      .groups = "drop"
    ) %>%
    arrange(desc(count)) %>%
    head(top_n)

  return(ambiguous)
}

#' Analyze gender distribution
#'
#' @param data Predictions data frame
#' @return Data frame with gender distribution
analyze_gender_distribution <- function(data) {
  gender_dist <- data %>%
    filter(!is.na(consensus_gender)) %>%
    count(consensus_gender) %>%
    mutate(
      percentage = round(n / sum(n) * 100, 2)
    )

  return(gender_dist)
}

# ==============================================================================
# REPORT GENERATION
# ==============================================================================

#' Generate validation report
#'
#' @param data Predictions data frame
#' @param config Configuration list
#' @param output_file Output file path
generate_validation_report <- function(data, config, output_file) {
  log_info("Generating validation report...")

  # Calculate all statistics
  coverage_stats <- calculate_coverage_stats(data)
  agreement_stats <- analyze_method_agreement(data)
  confidence_dist <- analyze_confidence_distribution(data)
  regional_stats <- analyze_regional_patterns(data, config)
  ambiguous_names <- identify_ambiguous_names(data, top_n = 20)
  gender_dist <- analyze_gender_distribution(data)

  # Create HTML report
  html_content <- paste0("
<!DOCTYPE html>
<html>
<head>
  <title>Gender Prediction Validation Report</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; }
    h1 { color: #2c3e50; }
    h2 { color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 5px; }
    table { border-collapse: collapse; width: 100%; margin: 20px 0; }
    th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
    th { background-color: #3498db; color: white; }
    tr:nth-child(even) { background-color: #f2f2f2; }
    .metric { background-color: #ecf0f1; padding: 15px; margin: 10px 0; border-radius: 5px; }
    .metric-value { font-size: 24px; font-weight: bold; color: #2c3e50; }
    .metric-label { font-size: 14px; color: #7f8c8d; }
    .warning { background-color: #fff3cd; padding: 10px; border-left: 4px solid #ffc107; margin: 10px 0; }
    .success { background-color: #d4edda; padding: 10px; border-left: 4px solid #28a745; margin: 10px 0; }
  </style>
</head>
<body>
  <h1>Gender Prediction Validation Report</h1>
  <p><strong>Generated:</strong> ", Sys.time(), "</p>
  <p><strong>Total Records:</strong> ", format(coverage_stats$total_records, big.mark = ","), "</p>
  <p><strong>Unique Authors:</strong> ", format(coverage_stats$unique_authors, big.mark = ","), "</p>

  <h2>Overall Coverage</h2>
  <div class='metric'>
    <div class='metric-label'>Consensus Predictions</div>
    <div class='metric-value'>", coverage_stats$consensus_coverage, " (", coverage_stats$consensus_pct, "%)</div>
  </div>

  <table>
    <tr>
      <th>Method</th>
      <th>Predictions</th>
      <th>Coverage</th>
    </tr>
    <tr>
      <td>Cache</td>
      <td>", format(coverage_stats$cache_coverage, big.mark = ","), "</td>
      <td>", coverage_stats$cache_pct, "%</td>
    </tr>
    <tr>
      <td>Gender R</td>
      <td>", format(coverage_stats$gender_r_coverage, big.mark = ","), "</td>
      <td>", coverage_stats$gender_r_pct, "%</td>
    </tr>
    <tr>
      <td>Gender-guesser</td>
      <td>", format(coverage_stats$guesser_coverage, big.mark = ","), "</td>
      <td>", coverage_stats$guesser_pct, "%</td>
    </tr>
    <tr>
      <td>Genderize.io</td>
      <td>", format(coverage_stats$genderize_coverage, big.mark = ","), "</td>
      <td>", coverage_stats$genderize_pct, "%</td>
    </tr>
  </table>

  <h2>Method Agreement</h2>
  <p>Records with multiple predictions: ", format(agreement_stats$total_with_multiple, big.mark = ","), "</p>
  <p>All methods agree: ", format(agreement_stats$all_agree, big.mark = ","), " (", agreement_stats$agreement_rate, "%)</p>
  <p>Methods disagree: ", format(agreement_stats$partial_disagree, big.mark = ","), "</p>

  ", if(coverage_stats$has_mismatch > 0) {
    paste0("<div class='warning'><strong>⚠️ Warning:</strong> ",
           format(coverage_stats$has_mismatch, big.mark = ","),
           " records have mismatched predictions between methods. Review recommended.</div>")
  } else {
    "<div class='success'><strong>✓</strong> No mismatches detected between prediction methods.</div>"
  }, "

  <h2>Confidence Distribution</h2>
  <table>
    <tr>
      <th>Confidence Level</th>
      <th>Count</th>
      <th>Percentage</th>
    </tr>
  ")

  for(i in 1:nrow(confidence_dist)) {
    html_content <- paste0(html_content, "
    <tr>
      <td>", confidence_dist$confidence_category[i], "</td>
      <td>", format(confidence_dist$n[i], big.mark = ","), "</td>
      <td>", confidence_dist$percentage[i], "%</td>
    </tr>")
  }

  html_content <- paste0(html_content, "
  </table>

  <h2>Gender Distribution</h2>
  <table>
    <tr>
      <th>Gender</th>
      <th>Count</th>
      <th>Percentage</th>
    </tr>
  ")

  for(i in 1:nrow(gender_dist)) {
    html_content <- paste0(html_content, "
    <tr>
      <td>", ifelse(gender_dist$consensus_gender[i] == "M", "Male", "Female"), "</td>
      <td>", format(gender_dist$n[i], big.mark = ","), "</td>
      <td>", gender_dist$percentage[i], "%</td>
    </tr>")
  }

  html_content <- paste0(html_content, "
  </table>

  <h2>Regional Analysis</h2>
  <table>
    <tr>
      <th>Region</th>
      <th>Total Authors</th>
      <th>With Prediction</th>
      <th>Coverage</th>
      <th>Male %</th>
      <th>Female %</th>
    </tr>
  ")

  for(i in 1:nrow(regional_stats)) {
    html_content <- paste0(html_content, "
    <tr>
      <td>", regional_stats$region[i], "</td>
      <td>", format(regional_stats$total_authors[i], big.mark = ","), "</td>
      <td>", format(regional_stats$with_prediction[i], big.mark = ","), "</td>
      <td>", regional_stats$coverage_rate[i], "%</td>
      <td>", regional_stats$male_pct[i], "%</td>
      <td>", regional_stats$female_pct[i], "</td>
    </tr>")
  }

  html_content <- paste0(html_content, "
  </table>

  <h2>Top 20 Ambiguous Names</h2>
  <table>
    <tr>
      <th>Forename</th>
      <th>Mismatch Detail</th>
      <th>Count</th>
      <th>Countries</th>
    </tr>
  ")

  if(nrow(ambiguous_names) > 0) {
    for(i in 1:nrow(ambiguous_names)) {
      html_content <- paste0(html_content, "
      <tr>
        <td>", ambiguous_names$forename[i], "</td>
        <td><small>", ambiguous_names$mismatch_detail[i], "</small></td>
        <td>", ambiguous_names$count[i], "</td>
        <td><small>", ambiguous_names$countries[i], "</small></td>
      </tr>")
    }
  } else {
    html_content <- paste0(html_content, "
      <tr><td colspan='4'><em>No ambiguous names found</em></td></tr>")
  }

  html_content <- paste0(html_content, "
  </table>

</body>
</html>
  ")

  # Write HTML file
  ensure_dir(dirname(output_file))
  writeLines(html_content, output_file)

  log_info(paste("Validation report saved to:", output_file))
}

# ==============================================================================
# MAIN FUNCTION
# ==============================================================================

validate_predictions <- function(config, input_file = NULL) {
  log_info("=== STEP 4: VALIDATE PREDICTIONS ===")

  # Determine input file
  if (is.null(input_file)) {
    # Try final predictions first, fall back to multi-method predictions
    if (file.exists(config$paths$predictions_final)) {
      input_file <- config$paths$predictions_final
    } else if (file.exists(config$paths$predictions_multi)) {
      input_file <- config$paths$predictions_multi
      log_warn("Using multi-method predictions (step 3 not run yet)")
    } else {
      stop("No prediction files found. Run steps 1-2 first.")
    }
  }

  # Load predictions
  predictions_data <- load_json(input_file)
  log_info(paste("Loaded", nrow(predictions_data), "records from:", input_file))

  # ============================================================================
  # Calculate Statistics
  # ============================================================================

  log_info("\n--- Calculating Coverage Statistics ---")
  coverage_stats <- calculate_coverage_stats(predictions_data)

  log_info(paste("Total records:", format(coverage_stats$total_records, big.mark = ",")))
  log_info(paste("Unique authors:", format(coverage_stats$unique_authors, big.mark = ",")))
  log_info(paste("Unique forenames:", format(coverage_stats$unique_forenames, big.mark = ",")))
  log_info("\nCoverage by method:")
  log_info(paste("  Cache:", coverage_stats$cache_coverage,
                 paste0("(", coverage_stats$cache_pct, "%)")))
  log_info(paste("  Gender R:", coverage_stats$gender_r_coverage,
                 paste0("(", coverage_stats$gender_r_pct, "%)")))
  log_info(paste("  Gender-guesser:", coverage_stats$guesser_coverage,
                 paste0("(", coverage_stats$guesser_pct, "%)")))
  log_info(paste("  Genderize.io:", coverage_stats$genderize_coverage,
                 paste0("(", coverage_stats$genderize_pct, "%)")))
  log_info(paste("\nConsensus predictions:", coverage_stats$consensus_coverage,
                 paste0("(", coverage_stats$consensus_pct, "%)")))

  log_info("\n--- Analyzing Method Agreement ---")
  agreement_stats <- analyze_method_agreement(predictions_data)
  log_info(paste("Records with multiple predictions:", agreement_stats$total_with_multiple))
  log_info(paste("All methods agree:", agreement_stats$all_agree,
                 paste0("(", agreement_stats$agreement_rate, "%)")))

  log_info("\n--- Analyzing Confidence Distribution ---")
  confidence_dist <- analyze_confidence_distribution(predictions_data)
  print(confidence_dist)

  log_info("\n--- Analyzing Regional Patterns ---")
  regional_stats <- analyze_regional_patterns(predictions_data, config)
  print(regional_stats)

  log_info("\n--- Identifying Ambiguous Names ---")
  ambiguous_names <- identify_ambiguous_names(predictions_data, top_n = 10)
  if(nrow(ambiguous_names) > 0) {
    log_info("Top 10 ambiguous names:")
    print(ambiguous_names)
  } else {
    log_info("No ambiguous names found")
  }

  # ============================================================================
  # Generate HTML Report (if enabled)
  # ============================================================================

  if (config$validation$generate_html_report) {
    log_info("\n--- Generating HTML Report ---")
    report_path <- config$paths$validation_report

    generate_validation_report(predictions_data, config, report_path)
  }

  log_info("\n=== STEP 4 COMPLETE ===\n")

  # Return statistics for use by orchestrator
  return(list(
    coverage_stats = coverage_stats,
    agreement_stats = agreement_stats,
    confidence_dist = confidence_dist,
    regional_stats = regional_stats,
    ambiguous_names = ambiguous_names
  ))
}

# ==============================================================================
# SCRIPT EXECUTION (if run directly)
# ==============================================================================

if (!interactive()) {
  config <- load_config("config.yaml")
  init_logging(config)

  result <- validate_predictions(config)

  log_info("Validation completed successfully")
}
