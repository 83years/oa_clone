# ==============================================================================
# Author Profile Builder - Main Orchestrator
# ==============================================================================
# This is the main entry point for the gender prediction pipeline.
#
# Usage:
#   Rscript main_orchestrator.R [options]
#
# Options:
#   --config <path>       Path to config file (default: config.yaml)
#   --steps <steps>       Comma-separated steps to run (default: all)
#                         Options: extract, predict, genderize, validate, all
#   --skip-genderize      Skip Genderize.io API call (step 3)
#   --max-names <n>       Limit Genderize.io to N names
#   --help                Show this help message
#
# Examples:
#   # Run all steps except Genderize.io
#   Rscript main_orchestrator.R --skip-genderize
#
#   # Run only extraction and prediction
#   Rscript main_orchestrator.R --steps extract,predict
#
#   # Run Genderize.io with limit
#   Rscript main_orchestrator.R --steps genderize --max-names 1000
#
#   # Validate existing results
#   Rscript main_orchestrator.R --steps validate
# ==============================================================================

suppressPackageStartupMessages({
  library(dplyr)
})

# Source utility functions
source("utils.R")

# Source step scripts
source("01_extract_author_names.R")
source("02_predict_gender_multi.R")
source("03_genderize_api.R")
source("04_validate_predictions.R")

# ==============================================================================
# COMMAND LINE ARGUMENT PARSING
# ==============================================================================

parse_args <- function() {
  args <- commandArgs(trailingOnly = TRUE)

  options <- list(
    config_path = "config.yaml",
    steps = c("extract", "predict", "validate"),  # Default: skip genderize
    skip_genderize = FALSE,
    max_names = NULL,
    show_help = FALSE
  )

  i <- 1
  while (i <= length(args)) {
    arg <- args[i]

    if (arg == "--help" || arg == "-h") {
      options$show_help <- TRUE
      break

    } else if (arg == "--config") {
      if (i < length(args)) {
        options$config_path <- args[i + 1]
        i <- i + 1
      }

    } else if (arg == "--steps") {
      if (i < length(args)) {
        step_string <- args[i + 1]
        options$steps <- trimws(unlist(strsplit(step_string, ",")))
        i <- i + 1
      }

    } else if (arg == "--skip-genderize") {
      options$skip_genderize <- TRUE
      options$steps <- setdiff(options$steps, "genderize")

    } else if (arg == "--max-names") {
      if (i < length(args)) {
        options$max_names <- as.numeric(args[i + 1])
        i <- i + 1
      }

    } else if (arg == "all") {
      options$steps <- c("extract", "predict", "genderize", "validate")
    }

    i <- i + 1
  }

  # Handle "all" shortcut
  if ("all" %in% options$steps) {
    options$steps <- c("extract", "predict", "genderize", "validate")
  }

  return(options)
}

show_help <- function() {
  cat("
==============================================================================
Author Profile Builder - Gender Prediction Pipeline
==============================================================================

USAGE:
  Rscript main_orchestrator.R [options]

OPTIONS:
  --config <path>       Path to config file (default: config.yaml)
  --steps <steps>       Comma-separated steps to run (default: extract,predict,validate)
                        Options: extract, predict, genderize, validate, all
  --skip-genderize      Skip Genderize.io API call (step 3)
  --max-names <n>       Limit Genderize.io to N names (useful for testing)
  --help, -h            Show this help message

STEPS:
  extract               Step 1: Extract author names and country codes from database
  predict               Step 2: Run multi-method gender prediction (cache, Gender R, gender-guesser)
  genderize             Step 3: Call Genderize.io API for remaining names (costs may apply)
  validate              Step 4: Validate predictions and generate reports
  all                   Run all steps in sequence

EXAMPLES:
  # Run default pipeline (no Genderize.io)
  Rscript main_orchestrator.R

  # Run full pipeline including Genderize.io
  Rscript main_orchestrator.R --steps all

  # Run only extraction and prediction
  Rscript main_orchestrator.R --steps extract,predict

  # Test Genderize.io with 100 names
  Rscript main_orchestrator.R --steps genderize --max-names 100

  # Validate existing results
  Rscript main_orchestrator.R --steps validate

  # Use custom config file
  Rscript main_orchestrator.R --config my_config.yaml

NOTES:
  - The Genderize.io API (step 3) has usage limits and may incur costs.
  - By default, step 3 is skipped. Use --steps all to include it.
  - Make sure to set your GENDERIZE_API_KEY environment variable.
  - Check config.yaml for database paths and other settings.

==============================================================================
")
}

# ==============================================================================
# MAIN ORCHESTRATOR FUNCTION
# ==============================================================================

run_pipeline <- function(options) {
  cat("\n")
  log_info("==============================================================================")
  log_info("         AUTHOR PROFILE BUILDER - GENDER PREDICTION PIPELINE")
  log_info("==============================================================================")
  log_info(paste("Start time:", Sys.time()))
  log_info(paste("Configuration:", options$config_path))
  log_info(paste("Steps to run:", paste(options$steps, collapse = ", ")))
  log_info("==============================================================================\n")

  # Load configuration
  config <- load_config(options$config_path)

  # Initialize logging
  init_logging(config)

  # Track overall timing
  start_time <- Sys.time()

  # Track results
  results <- list()

  # ============================================================================
  # STEP 1: EXTRACT AUTHOR NAMES
  # ============================================================================

  if ("extract" %in% options$steps) {
    log_info("\n╔════════════════════════════════════════════════════════════════════╗")
    log_info("║                    STEP 1: EXTRACT AUTHOR NAMES                    ║")
    log_info("╚════════════════════════════════════════════════════════════════════╝\n")

    step_start <- Sys.time()

    tryCatch({
      results$extract <- extract_author_names(config)

      step_duration <- as.numeric(difftime(Sys.time(), step_start, units = "mins"))
      log_info(paste("✓ Step 1 completed in", round(step_duration, 2), "minutes\n"))

    }, error = function(e) {
      log_error(paste("✗ Step 1 failed:", e$message))
      stop("Pipeline halted due to error in step 1")
    })
  } else {
    log_info("Skipping Step 1: Extract Author Names\n")
  }

  # ============================================================================
  # STEP 2: MULTI-METHOD GENDER PREDICTION
  # ============================================================================

  if ("predict" %in% options$steps) {
    log_info("\n╔════════════════════════════════════════════════════════════════════╗")
    log_info("║              STEP 2: MULTI-METHOD GENDER PREDICTION                ║")
    log_info("╚════════════════════════════════════════════════════════════════════╝\n")

    step_start <- Sys.time()

    tryCatch({
      results$predict <- predict_gender_multi(config)

      step_duration <- as.numeric(difftime(Sys.time(), step_start, units = "mins"))
      log_info(paste("✓ Step 2 completed in", round(step_duration, 2), "minutes\n"))

      # Check for mismatches
      mismatch_count <- sum(results$predict$has_mismatch, na.rm = TRUE)
      if (mismatch_count > 0) {
        log_warn(paste("⚠️  ATTENTION:", mismatch_count, "records have mismatched predictions"))
        log_warn("   Review the output JSON before proceeding to Step 3 (Genderize.io)")
      }

    }, error = function(e) {
      log_error(paste("✗ Step 2 failed:", e$message))
      stop("Pipeline halted due to error in step 2")
    })
  } else {
    log_info("Skipping Step 2: Multi-Method Gender Prediction\n")
  }

  # ============================================================================
  # STEP 3: GENDERIZE.IO API (Optional)
  # ============================================================================

  if ("genderize" %in% options$steps && !options$skip_genderize) {
    log_info("\n╔════════════════════════════════════════════════════════════════════╗")
    log_info("║              STEP 3: GENDERIZE.IO API PROCESSING                   ║")
    log_info("╚════════════════════════════════════════════════════════════════════╝\n")

    log_warn("⚠️  This step will call the Genderize.io API which may incur costs")
    log_info("   Make sure you have reviewed the results from Step 2 first")
    log_info("   Press Ctrl+C to cancel, or wait 5 seconds to continue...\n")
    Sys.sleep(5)

    step_start <- Sys.time()

    tryCatch({
      results$genderize <- process_genderize_api(
        config,
        only_missing = TRUE,
        max_names = options$max_names
      )

      step_duration <- as.numeric(difftime(Sys.time(), step_start, units = "mins"))
      log_info(paste("✓ Step 3 completed in", round(step_duration, 2), "minutes\n"))

    }, error = function(e) {
      log_error(paste("✗ Step 3 failed:", e$message))
      log_warn("Pipeline will continue with existing predictions")
    })

  } else if (options$skip_genderize) {
    log_info("\n╔════════════════════════════════════════════════════════════════════╗")
    log_info("║                 STEP 3: GENDERIZE.IO (SKIPPED)                     ║")
    log_info("╚════════════════════════════════════════════════════════════════════╝")
    log_info("\nGenderize.io API step skipped (use --steps all to include)\n")
  }

  # ============================================================================
  # STEP 4: VALIDATE PREDICTIONS
  # ============================================================================

  if ("validate" %in% options$steps) {
    log_info("\n╔════════════════════════════════════════════════════════════════════╗")
    log_info("║                 STEP 4: VALIDATE PREDICTIONS                       ║")
    log_info("╚════════════════════════════════════════════════════════════════════╝\n")

    step_start <- Sys.time()

    tryCatch({
      results$validate <- validate_predictions(config)

      step_duration <- as.numeric(difftime(Sys.time(), step_start, units = "mins"))
      log_info(paste("✓ Step 4 completed in", round(step_duration, 2), "minutes\n"))

    }, error = function(e) {
      log_error(paste("✗ Step 4 failed:", e$message))
      log_warn("Validation failed but predictions are still available")
    })
  } else {
    log_info("Skipping Step 4: Validate Predictions\n")
  }

  # ============================================================================
  # PIPELINE COMPLETE
  # ============================================================================

  total_duration <- as.numeric(difftime(Sys.time(), start_time, units = "mins"))

  log_info("\n╔════════════════════════════════════════════════════════════════════╗")
  log_info("║                   PIPELINE COMPLETED SUCCESSFULLY                  ║")
  log_info("╚════════════════════════════════════════════════════════════════════╝\n")

  log_info(paste("Total runtime:", round(total_duration, 2), "minutes"))
  log_info(paste("End time:", Sys.time()))

  # Print output file locations
  log_info("\n=== OUTPUT FILES ===")

  if ("extract" %in% options$steps) {
    log_info(paste("  Step 1:", config$paths$extracted_names))
  }

  if ("predict" %in% options$steps) {
    log_info(paste("  Step 2:", config$paths$predictions_multi))
  }

  if ("genderize" %in% options$steps && !options$skip_genderize) {
    log_info(paste("  Step 3:", config$paths$predictions_final))
  }

  if ("validate" %in% options$steps && config$validation$generate_html_report) {
    log_info(paste("  Validation Report:", config$paths$validation_report))
  }

  log_info(paste("  Log File:", config$paths$log_file))

  # Print next steps
  log_info("\n=== NEXT STEPS ===")

  if ("genderize" %in% options$steps) {
    log_info("  1. Review the validation report")
    log_info("  2. Check the final predictions JSON file")
    log_info("  3. Update the database with gender predictions")
  } else if ("predict" %in% options$steps) {
    log_info("  1. Review the validation report and mismatches")
    log_info("  2. If satisfied, run: Rscript main_orchestrator.R --steps genderize")
    log_info("  3. Or skip Genderize.io and use existing predictions")
  } else if ("validate" %in% options$steps) {
    log_info("  1. Review the validation report")
    log_info("  2. Address any quality issues identified")
  }

  log_info("\n==============================================================================\n")

  return(invisible(results))
}

# ==============================================================================
# SCRIPT EXECUTION
# ==============================================================================

if (!interactive()) {
  # Parse command line arguments
  options <- parse_args()

  # Show help if requested
  if (options$show_help) {
    show_help()
    quit(status = 0)
  }

  # Run pipeline
  tryCatch({
    results <- run_pipeline(options)
    quit(status = 0)

  }, error = function(e) {
    cat("\n")
    log_error("==============================================================================")
    log_error("                         PIPELINE FAILED")
    log_error("==============================================================================")
    log_error(paste("Error:", e$message))
    log_error("==============================================================================\n")
    quit(status = 1)
  })

} else {
  # Interactive mode
  cat("
Running in interactive mode.

To run the pipeline, use:
  options <- list(
    config_path = 'config.yaml',
    steps = c('extract', 'predict', 'validate'),
    skip_genderize = TRUE,
    max_names = NULL
  )
  results <- run_pipeline(options)

Or run from command line:
  Rscript main_orchestrator.R

For help:
  Rscript main_orchestrator.R --help
")
}
