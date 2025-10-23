# ==============================================================================
# Step 3: Genderize.io API Processing (On-Demand)
# ==============================================================================
# This script:
# 1. Loads predictions from step 2
# 2. Identifies names still needing prediction (no consensus)
# 3. Calls Genderize.io API in batches with country context
# 4. Updates cache with new results
# 5. Outputs final predictions with all methods
#
# IMPORTANT: Only run this after reviewing step 2 results!
# The Genderize.io API has usage limits and costs.
# ==============================================================================

suppressPackageStartupMessages({
  library(dplyr)
  library(stringr)
  library(httr)
  library(jsonlite)
})

source("utils.R")

# ==============================================================================
# GENDERIZE.IO API FUNCTIONS
# ==============================================================================

#' Call Genderize.io API in batches
#'
#' @param names Vector of forenames
#' @param countries Vector of country codes (same length as names)
#' @param api_key Genderize.io API key
#' @param config Configuration list
#' @return Data frame with predictions
call_genderize_api_batched <- function(names, countries, api_key, config) {
  if (length(names) == 0) {
    return(data.frame(
      name = character(0),
      country_code = character(0),
      gender = character(0),
      probability = numeric(0),
      count = numeric(0)
    ))
  }

  log_info(paste("Processing", length(names), "names via Genderize.io API"))

  # Get API config
  api_config <- config$apis$genderize
  batch_size <- api_config$batch_size
  rate_limit_delay <- api_config$rate_limit_delay
  max_retries <- api_config$max_retries
  retry_delay <- api_config$retry_delay

  # Initialize results
  all_results <- data.frame(
    name = character(0),
    country_code = character(0),
    gender = character(0),
    probability = numeric(0),
    count = numeric(0)
  )

  # Process in batches
  num_batches <- ceiling(length(names) / batch_size)
  log_info(paste("Batches to process:", num_batches, "(", batch_size, "names per batch)"))

  for (batch_num in 1:num_batches) {
    start_idx <- (batch_num - 1) * batch_size + 1
    end_idx <- min(batch_num * batch_size, length(names))

    batch_names <- names[start_idx:end_idx]
    batch_countries <- countries[start_idx:end_idx]

    # Retry logic
    retry_count <- 0
    success <- FALSE

    while (!success && retry_count <= max_retries) {
      tryCatch({
        # Build query parameters
        query_params <- list()
        query_params$apikey <- api_key

        # Add names with indexed format: name[0], name[1], etc.
        for (i in seq_along(batch_names)) {
          query_params[[paste0("name[", i - 1, "]")]] <- batch_names[i]

          # Add country if available
          if (!is.na(batch_countries[i]) && batch_countries[i] != "") {
            query_params[[paste0("country_id[", i - 1, "]")]] <- batch_countries[i]
          }
        }

        # Make API request
        response <- GET(
          url = "https://api.genderize.io",
          query = query_params,
          timeout(30)
        )

        # Handle response
        if (status_code(response) == 200) {
          content_data <- content(response, "text", encoding = "UTF-8")
          parsed_data <- fromJSON(content_data)

          # Convert to data frame
          if (is.data.frame(parsed_data)) {
            batch_results <- parsed_data
          } else if (is.list(parsed_data) && length(parsed_data) > 0) {
            batch_results <- data.frame(
              name = sapply(parsed_data, function(x) x$name %||% NA),
              gender = sapply(parsed_data, function(x) x$gender %||% NA),
              probability = sapply(parsed_data, function(x) x$probability %||% NA),
              count = sapply(parsed_data, function(x) x$count %||% NA),
              country_id = sapply(parsed_data, function(x) x$country_id %||% NA),
              stringsAsFactors = FALSE
            )
          } else {
            batch_results <- data.frame(
              name = parsed_data$name %||% batch_names[1],
              gender = parsed_data$gender %||% NA,
              probability = parsed_data$probability %||% NA,
              count = parsed_data$count %||% NA,
              country_id = parsed_data$country_id %||% NA,
              stringsAsFactors = FALSE
            )
          }

          # Standardize results
          batch_results <- batch_results %>%
            mutate(
              country_code = country_id,
              gender = case_when(
                gender == "male" ~ "M",
                gender == "female" ~ "F",
                TRUE ~ NA_character_
              )
            ) %>%
            select(name, country_code, gender, probability, count)

          all_results <- bind_rows(all_results, batch_results)
          success <- TRUE

          # Progress reporting
          if (batch_num %% 10 == 0 || batch_num == num_batches) {
            processed <- min(end_idx, length(names))
            log_info(paste("  Progress:", processed, "/", length(names),
                           paste0("(", round(processed / length(names) * 100, 1), "%)")))
          }

        } else if (status_code(response) == 402) {
          log_error("API quota exceeded - payment required")
          log_info(paste("Processed", nrow(all_results), "names before quota limit"))
          return(all_results)

        } else if (status_code(response) == 429) {
          log_warn(paste("Rate limit exceeded, waiting", retry_delay, "seconds..."))
          Sys.sleep(retry_delay)
          retry_count <- retry_count + 1

        } else {
          error_content <- content(response, "text", encoding = "UTF-8")
          log_error(paste("API request failed with status:", status_code(response)))
          log_debug(paste("Response:", substr(error_content, 1, 200)))
          retry_count <- retry_count + 1
        }

      }, error = function(e) {
        log_error(paste("Error in batch", batch_num, ":", e$message))
        retry_count <- retry_count + 1
      })

      if (!success && retry_count <= max_retries) {
        Sys.sleep(rate_limit_delay)
      }
    }

    if (!success) {
      log_warn(paste("Batch", batch_num, "failed after", max_retries, "retries"))
    }

    # Rate limiting between successful batches
    if (success && batch_num < num_batches) {
      Sys.sleep(rate_limit_delay)
    }
  }

  log_info(paste("API processing complete:", nrow(all_results), "results"))

  return(all_results)
}

# ==============================================================================
# MAIN FUNCTION
# ==============================================================================

process_genderize_api <- function(config, only_missing = TRUE, max_names = NULL) {
  log_info("=== STEP 3: GENDERIZE.IO API PROCESSING ===")

  # Get API key
  api_key <- get_api_key(config, "genderize")

  # Load predictions from step 2
  input_path <- config$paths$predictions_multi
  if (!file.exists(input_path)) {
    stop("Input file not found. Run step 2 first: ", input_path)
  }

  predictions_data <- load_json(input_path)
  log_info(paste("Loaded", nrow(predictions_data), "records from step 2"))

  # Load cache
  cache_path <- config$paths$genderize_cache
  cache <- load_or_create_cache(cache_path)
  initial_cache_size <- nrow(cache)

  # ============================================================================
  # Identify names needing API call
  # ============================================================================

  if (only_missing) {
    log_info("Filtering to records without consensus prediction...")

    names_to_process <- predictions_data %>%
      filter(is.na(consensus_gender) | needs_review) %>%
      distinct(forename, country_code)

  } else {
    log_info("Processing all unique forename-country combinations...")

    names_to_process <- predictions_data %>%
      distinct(forename, country_code)
  }

  log_info(paste("Names needing API call:", nrow(names_to_process)))

  # Apply max_names limit if specified
  if (!is.null(max_names) && nrow(names_to_process) > max_names) {
    log_warn(paste("Limiting to first", max_names, "names (set max_names=NULL to process all)"))
    names_to_process <- names_to_process %>% head(max_names)
  }

  # Check if any names need processing
  if (nrow(names_to_process) == 0) {
    log_info("No names need API processing")
    log_info("=== STEP 3 COMPLETE ===\n")
    return(predictions_data)
  }

  # Estimate cost
  api_config <- config$apis$genderize
  free_quota <- api_config$max_daily_quota
  cost_per_name <- 0.01  # Approximate cost after free tier

  if (nrow(names_to_process) > free_quota) {
    estimated_cost <- (nrow(names_to_process) - free_quota) * cost_per_name
    log_warn(paste("Estimated API cost: $", round(estimated_cost, 2),
                   "(", nrow(names_to_process) - free_quota, "names beyond free tier)"))
    log_warn("Press Ctrl+C to cancel, or wait 10 seconds to continue...")
    Sys.sleep(10)
  }

  # ============================================================================
  # Call Genderize.io API
  # ============================================================================
  log_info("\n--- Calling Genderize.io API ---")

  api_results <- call_genderize_api_batched(
    names_to_process$forename,
    names_to_process$country_code,
    api_key,
    config
  )

  # ============================================================================
  # Update Cache
  # ============================================================================
  if (nrow(api_results) > 0) {
    log_info("Updating cache with new results...")

    updated_cache <- cache %>%
      bind_rows(api_results) %>%
      # Remove duplicates, keeping most recent (last occurrence)
      group_by(name, country_code) %>%
      slice_tail(n = 1) %>%
      ungroup()

    save_cache(updated_cache, cache_path)

    new_entries <- nrow(updated_cache) - initial_cache_size
    log_info(paste("Added", new_entries, "new entries to cache"))
  }

  # ============================================================================
  # Join API Results to Predictions
  # ============================================================================
  log_info("Joining API results to predictions...")

  final_data <- predictions_data %>%
    left_join(
      api_results %>%
        select(forename = name, country_code, gender_genderize = gender,
               prob_genderize = probability),
      by = c("forename", "country_code")
    ) %>%
    mutate(
      # Update consensus if we now have agreement
      consensus_gender = case_when(
        !is.na(consensus_gender) ~ consensus_gender,  # Keep existing consensus
        # Check for new consensus with Genderize.io
        !is.na(gender_genderize) ~ gender_genderize,
        TRUE ~ NA_character_
      ),

      # Update needs_review flag
      needs_review = case_when(
        !is.na(consensus_gender) ~ FALSE,
        TRUE ~ needs_review
      ),

      # Update processing metadata
      processing_date = as.character(Sys.Date()),
      genderize_processed = TRUE
    )

  # ============================================================================
  # Save Final Results
  # ============================================================================
  output_path <- config$paths$predictions_final

  save_json(final_data, output_path)

  # ============================================================================
  # Summary Statistics
  # ============================================================================
  log_info("\n=== FINAL SUMMARY ===")

  final_summary <- final_data %>%
    summarise(
      total_records = n(),

      # Coverage by method
      cache_predictions = sum(!is.na(gender_cache)),
      gender_r_predictions = sum(!is.na(gender_r)),
      guesser_predictions = sum(!is.na(gender_guesser)),
      genderize_predictions = sum(!is.na(gender_genderize)),

      # Overall coverage
      consensus_predictions = sum(!is.na(consensus_gender)),
      any_prediction = sum(
        !is.na(gender_cache) | !is.na(gender_r) |
          !is.na(gender_guesser) | !is.na(gender_genderize)
      ),

      # Quality metrics
      still_needs_review = sum(needs_review, na.rm = TRUE)
    )

  log_info(paste("Total records:", final_summary$total_records))
  log_info("\nFinal predictions by method:")
  log_info(paste("  Cache:", final_summary$cache_predictions))
  log_info(paste("  Gender R:", final_summary$gender_r_predictions))
  log_info(paste("  Gender-guesser:", final_summary$guesser_predictions))
  log_info(paste("  Genderize.io:", final_summary$genderize_predictions))
  log_info(paste("\nConsensus predictions:", final_summary$consensus_predictions,
                 paste0("(", round(final_summary$consensus_predictions /
                                     final_summary$total_records * 100, 1), "%)")))
  log_info(paste("Any prediction:", final_summary$any_prediction,
                 paste0("(", round(final_summary$any_prediction /
                                     final_summary$total_records * 100, 1), "%)")))
  log_info(paste("Still needs review:", final_summary$still_needs_review))

  log_info(paste("\nOutput saved to:", output_path))
  log_info("=== STEP 3 COMPLETE ===\n")

  return(final_data)
}

# ==============================================================================
# SCRIPT EXECUTION (if run directly)
# ==============================================================================

if (!interactive()) {
  config <- load_config("config.yaml")
  init_logging(config)

  # Parse command line arguments
  args <- commandArgs(trailingOnly = TRUE)

  only_missing <- TRUE
  max_names <- NULL

  if (length(args) > 0) {
    if ("--all" %in% args) {
      only_missing <- FALSE
    }

    max_idx <- which(args == "--max-names")
    if (length(max_idx) > 0 && length(args) > max_idx) {
      max_names <- as.numeric(args[max_idx + 1])
      log_info(paste("Limiting to", max_names, "names"))
    }
  }

  result <- process_genderize_api(config, only_missing, max_names)

  log_info("Genderize.io API processing completed successfully")
}
