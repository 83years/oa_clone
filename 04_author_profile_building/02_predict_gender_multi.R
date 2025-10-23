# ==============================================================================
# Step 2: Multi-Method Gender Prediction
# ==============================================================================
# This script:
# 1. Loads extracted names from JSON
# 2. Runs ALL three prediction methods on EVERY forename-country combination:
#    - Cache lookup (genderize.io cache)
#    - Gender R package (SSA/IPUMS)
#    - Gender-guesser (Python package)
# 3. Adds separate columns for each method's prediction
# 4. Flags mismatches where methods disagree
# 5. Outputs enhanced JSON with all predictions
# ==============================================================================

suppressPackageStartupMessages({
  library(dplyr)
  library(stringr)
  library(purrr)
  library(gender)
  library(reticulate)
})

source("utils.R")

# ==============================================================================
# GENDER PREDICTION FUNCTIONS
# ==============================================================================

#' Lookup gender from cache
#'
#' @param names Vector of forenames
#' @param countries Vector of country codes (same length as names)
#' @param cache Cache data frame
#' @return Data frame with name, country_code, gender, probability, source
lookup_cache <- function(names, countries, cache) {
  log_info("Looking up names in cache...")

  # Create lookup key
  lookup_df <- data.frame(
    name = names,
    country_code = ifelse(is.na(countries), "NONE", countries),
    stringsAsFactors = FALSE
  )

  # Join with cache
  results <- lookup_df %>%
    left_join(
      cache %>%
        mutate(country_code = ifelse(is.na(country_code), "NONE", country_code)),
      by = c("name", "country_code")
    ) %>%
    mutate(
      country_code = ifelse(country_code == "NONE", NA_character_, country_code),
      source = "cache"
    ) %>%
    select(name, country_code, gender, probability, source)

  cache_hits <- sum(!is.na(results$gender))
  log_info(paste("Cache hits:", cache_hits, "/", nrow(results),
                 paste0("(", round(cache_hits / nrow(results) * 100, 1), "%)")))

  return(results)
}

#' Predict gender using Gender R package
#'
#' @param names Vector of forenames
#' @param method Method to use ("ssa" or "ipums")
#' @return Data frame with name, gender, probability, source
predict_gender_r <- function(names, method = "ssa") {
  log_info(paste("Predicting genders using Gender R package (", method, ")..."))

  unique_names <- unique(names[!is.na(names)])
  log_info(paste("Unique names to process:", length(unique_names)))

  if (length(unique_names) == 0) {
    return(data.frame(
      name = character(0),
      gender = character(0),
      probability = numeric(0),
      source = character(0)
    ))
  }

  tryCatch({
    gender_results <- gender(unique_names, method = method)

    # Process results
    processed <- gender_results %>%
      mutate(
        probability = case_when(
          gender == "male" ~ proportion_male,
          gender == "female" ~ proportion_female,
          TRUE ~ NA_real_
        ),
        gender = case_when(
          gender == "male" ~ "M",
          gender == "female" ~ "F",
          TRUE ~ NA_character_
        ),
        source = paste0("gender_r_", method)
      ) %>%
      select(name, gender, probability, source)

    predictions <- sum(!is.na(processed$gender))
    log_info(paste("Gender R predictions:", predictions, "/", length(unique_names),
                   paste0("(", round(predictions / length(unique_names) * 100, 1), "%)")))

    return(processed)

  }, error = function(e) {
    log_error(paste("Gender R failed:", e$message))
    return(data.frame(
      name = unique_names,
      gender = NA_character_,
      probability = NA_real_,
      source = paste0("gender_r_", method, "_error")
    ))
  })
}

#' Predict gender using gender-guesser Python package
#'
#' @param names Vector of forenames
#' @param countries Vector of country codes
#' @return Data frame with name, country_code, gender, source
predict_gender_guesser <- function(names, countries = NULL) {
  log_info("Predicting genders using gender-guesser...")

  unique_combos <- data.frame(
    name = names,
    country_code = countries,
    stringsAsFactors = FALSE
  ) %>%
    distinct()

  log_info(paste("Unique name-country combinations:", nrow(unique_combos)))

  tryCatch({
    # Import Python package
    gender_guesser <- import("gender_guesser.detector")
    detector <- gender_guesser$Detector()

    # Process each name
    results <- unique_combos %>%
      mutate(
        raw_result = map2_chr(name, country_code, function(n, c) {
          if (!is.na(c) && c != "") {
            # Try with country context
            detector$get_gender(n, country = c)
          } else {
            detector$get_gender(n)
          }
        }),
        gender = case_when(
          raw_result %in% c("male", "mostly_male") ~ "M",
          raw_result %in% c("female", "mostly_female") ~ "F",
          TRUE ~ NA_character_
        ),
        probability = case_when(
          raw_result %in% c("male", "female") ~ 0.85,
          raw_result %in% c("mostly_male", "mostly_female") ~ 0.65,
          TRUE ~ NA_real_
        ),
        source = "gender_guesser"
      ) %>%
      select(name, country_code, gender, probability, source)

    predictions <- sum(!is.na(results$gender))
    log_info(paste("Gender-guesser predictions:", predictions, "/", nrow(unique_combos),
                   paste0("(", round(predictions / nrow(unique_combos) * 100, 1), "%)")))

    return(results)

  }, error = function(e) {
    log_error(paste("Gender-guesser failed:", e$message))
    log_warn("Make sure gender-guesser is installed: pip install gender-guesser")

    return(data.frame(
      name = unique_combos$name,
      country_code = unique_combos$country_code,
      gender = NA_character_,
      probability = NA_real_,
      source = "gender_guesser_error"
    ))
  })
}

# ==============================================================================
# MISMATCH DETECTION
# ==============================================================================

#' Detect mismatches between prediction methods
#'
#' @param data Data frame with gender predictions from multiple methods
#' @return Data frame with mismatch flags
detect_mismatches <- function(data) {
  log_info("Detecting mismatches between methods...")

  data_with_flags <- data %>%
    mutate(
      # Count how many methods made a prediction
      methods_predicted = rowSums(!is.na(select(., starts_with("gender_")))),

      # Count unique gender predictions (excluding NA)
      unique_genders = pmap_int(
        select(., starts_with("gender_")),
        function(...) {
          genders <- c(...)
          genders <- genders[!is.na(genders)]
          if (length(genders) == 0) return(0)
          return(length(unique(genders)))
        }
      ),

      # Flag if there's a mismatch (2+ methods predicted, but disagree)
      has_mismatch = (methods_predicted >= 2) & (unique_genders > 1),

      # Create mismatch description
      mismatch_detail = pmap_chr(
        list(
          has_mismatch,
          gender_cache, gender_r, gender_guesser,
          prob_cache, prob_r, prob_guesser
        ),
        function(mismatch, gc, gr, gg, pc, pr, pg) {
          if (!mismatch) return(NA_character_)

          methods <- c()
          if (!is.na(gc)) methods <- c(methods, paste0("cache:", gc, "(", round(pc, 2), ")"))
          if (!is.na(gr)) methods <- c(methods, paste0("gender_r:", gr, "(", round(pr, 2), ")"))
          if (!is.na(gg)) methods <- c(methods, paste0("guesser:", gg, "(", round(pg, 2), ")"))

          return(paste(methods, collapse = " vs "))
        }
      )
    )

  mismatch_count <- sum(data_with_flags$has_mismatch, na.rm = TRUE)
  log_info(paste("Mismatches detected:", mismatch_count))

  if (mismatch_count > 0) {
    log_warn(paste("Review", mismatch_count, "mismatched predictions before proceeding"))
  }

  return(data_with_flags)
}

# ==============================================================================
# MAIN FUNCTION
# ==============================================================================

predict_gender_multi <- function(config) {
  log_info("=== STEP 2: MULTI-METHOD GENDER PREDICTION ===")

  # Load extracted names
  input_path <- config$paths$extracted_names
  if (!file.exists(input_path)) {
    stop("Input file not found. Run step 1 first: ", input_path)
  }

  names_data <- load_json(input_path)
  log_info(paste("Loaded", nrow(names_data), "author records"))

  # Load cache
  cache_path <- config$paths$genderize_cache
  cache <- load_or_create_cache(cache_path)

  # ============================================================================
  # Get unique forename-country combinations
  # ============================================================================
  unique_combos <- names_data %>%
    distinct(forename, country_code, .keep_all = FALSE)

  log_info(paste("Unique forename-country combinations:", nrow(unique_combos)))

  # ============================================================================
  # Method 1: Cache Lookup
  # ============================================================================
  log_info("\n--- METHOD 1: Cache Lookup ---")

  cache_results <- lookup_cache(
    unique_combos$forename,
    unique_combos$country_code,
    cache
  )

  # ============================================================================
  # Method 2: Gender R Package
  # ============================================================================
  log_info("\n--- METHOD 2: Gender R Package ---")

  # Try SSA method first
  gender_r_ssa <- predict_gender_r(unique_combos$forename, method = "ssa")

  # Check coverage
  ssa_coverage <- sum(!is.na(gender_r_ssa$gender)) / nrow(gender_r_ssa)

  if (ssa_coverage < 0.5) {
    log_info("SSA coverage low, trying IPUMS method...")
    gender_r_ipums <- predict_gender_r(unique_combos$forename, method = "ipums")

    ipums_coverage <- sum(!is.na(gender_r_ipums$gender)) / nrow(gender_r_ipums)

    if (ipums_coverage > ssa_coverage) {
      log_info("Using IPUMS results (better coverage)")
      gender_r_results <- gender_r_ipums
    } else {
      log_info("Using SSA results")
      gender_r_results <- gender_r_ssa
    }
  } else {
    gender_r_results <- gender_r_ssa
  }

  # ============================================================================
  # Method 3: Gender-Guesser
  # ============================================================================
  log_info("\n--- METHOD 3: Gender-Guesser ---")

  guesser_results <- predict_gender_guesser(
    unique_combos$forename,
    unique_combos$country_code
  )

  # ============================================================================
  # Combine All Results
  # ============================================================================
  log_info("\n--- Combining Results ---")

  # Start with unique combinations
  combined_results <- unique_combos

  # Join cache results
  combined_results <- combined_results %>%
    left_join(
      cache_results %>%
        select(name, country_code, gender_cache = gender, prob_cache = probability),
      by = c("forename" = "name", "country_code")
    )

  # Join Gender R results (no country context)
  combined_results <- combined_results %>%
    left_join(
      gender_r_results %>%
        select(name, gender_r = gender, prob_r = probability),
      by = c("forename" = "name")
    )

  # Join gender-guesser results
  combined_results <- combined_results %>%
    left_join(
      guesser_results %>%
        select(name, country_code, gender_guesser = gender, prob_guesser = probability),
      by = c("forename" = "name", "country_code")
    )

  # ============================================================================
  # Detect Mismatches
  # ============================================================================
  combined_results <- detect_mismatches(combined_results)

  # ============================================================================
  # Join Back to Full Dataset
  # ============================================================================
  log_info("Joining predictions back to full dataset...")

  final_data <- names_data %>%
    left_join(
      combined_results,
      by = c("forename", "country_code")
    )

  # ============================================================================
  # Add Summary Columns
  # ============================================================================
  final_data <- final_data %>%
    mutate(
      # Consensus gender (if all methods agree)
      consensus_gender = case_when(
        unique_genders == 1 ~ coalesce(gender_cache, gender_r, gender_guesser),
        TRUE ~ NA_character_
      ),

      # Needs review flag
      needs_review = has_mismatch | (methods_predicted == 0),

      # Processing metadata
      processing_date = as.character(Sys.Date())
    )

  # ============================================================================
  # Save Results
  # ============================================================================
  output_path <- config$paths$predictions_multi

  save_json(final_data, output_path)

  # ============================================================================
  # Generate Summary Statistics
  # ============================================================================
  log_info("\n=== PREDICTION SUMMARY ===")

  summary_stats <- final_data %>%
    summarise(
      total_records = n(),
      unique_combos = n_distinct(forename, country_code),

      # Coverage by method
      cache_predictions = sum(!is.na(gender_cache)),
      gender_r_predictions = sum(!is.na(gender_r)),
      guesser_predictions = sum(!is.na(gender_guesser)),

      # Agreement
      consensus_predictions = sum(!is.na(consensus_gender)),
      mismatches = sum(has_mismatch, na.rm = TRUE),
      needs_review_count = sum(needs_review, na.rm = TRUE),

      # At least one prediction
      any_prediction = sum(methods_predicted > 0)
    )

  log_info(paste("Total records:", summary_stats$total_records))
  log_info(paste("Unique forename-country combinations:", summary_stats$unique_combos))
  log_info("\nPredictions by method:")
  log_info(paste("  Cache:", summary_stats$cache_predictions,
                 paste0("(", round(summary_stats$cache_predictions / summary_stats$total_records * 100, 1), "%)")))
  log_info(paste("  Gender R:", summary_stats$gender_r_predictions,
                 paste0("(", round(summary_stats$gender_r_predictions / summary_stats$total_records * 100, 1), "%)")))
  log_info(paste("  Gender-guesser:", summary_stats$guesser_predictions,
                 paste0("(", round(summary_stats$guesser_predictions / summary_stats$total_records * 100, 1), "%)")))
  log_info(paste("\nConsensus predictions:", summary_stats$consensus_predictions,
                 paste0("(", round(summary_stats$consensus_predictions / summary_stats$total_records * 100, 1), "%)")))
  log_info(paste("Mismatches detected:", summary_stats$mismatches))
  log_info(paste("Records needing review:", summary_stats$needs_review_count))

  # Show top mismatches
  if (summary_stats$mismatches > 0) {
    log_info("\nTop 10 mismatched names:")

    top_mismatches <- final_data %>%
      filter(has_mismatch) %>%
      group_by(forename, country_code, mismatch_detail) %>%
      summarise(count = n(), .groups = "drop") %>%
      arrange(desc(count)) %>%
      head(10)

    for (i in 1:nrow(top_mismatches)) {
      log_info(paste("  ", top_mismatches$forename[i],
                     paste0("(", top_mismatches$country_code[i], "):"),
                     top_mismatches$mismatch_detail[i],
                     "-", top_mismatches$count[i], "authors"))
    }
  }

  log_info(paste("\nOutput saved to:", output_path))
  log_info("=== STEP 2 COMPLETE ===\n")

  return(final_data)
}

# ==============================================================================
# SCRIPT EXECUTION (if run directly)
# ==============================================================================

if (!interactive()) {
  config <- load_config("config.yaml")
  init_logging(config)

  result <- predict_gender_multi(config)

  log_info("Multi-method gender prediction completed successfully")
}
