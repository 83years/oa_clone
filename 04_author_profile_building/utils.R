# ==============================================================================
# Utility Functions for Author Profile Builder
# ==============================================================================

# Required libraries
suppressPackageStartupMessages({
  library(DBI)
  library(RSQLite)
  library(dplyr)
  library(stringr)
  library(jsonlite)
  library(yaml)
})

# ==============================================================================
# CONFIGURATION LOADING
# ==============================================================================

#' Load configuration from YAML file
#'
#' @param config_path Path to config.yaml file
#' @return List containing configuration
load_config <- function(config_path = "config.yaml") {
  if (!file.exists(config_path)) {
    stop("Configuration file not found: ", config_path)
  }

  config <- yaml::read_yaml(config_path)
  log_info(paste("Configuration loaded from:", config_path))

  return(config)
}

#' Get API key from config or environment
#'
#' @param config Configuration list
#' @param api_name Name of the API (e.g., "genderize")
#' @return API key string
get_api_key <- function(config, api_name = "genderize") {
  api_config <- config$apis[[api_name]]

  if (is.null(api_config)) {
    stop("API configuration not found for: ", api_name)
  }

  # Try environment variable first
  if (api_config$use_env_var) {
    env_var <- api_config$env_var_name
    api_key <- Sys.getenv(env_var)

    if (api_key != "") {
      log_info(paste("API key loaded from environment variable:", env_var))
      return(api_key)
    }
  }

  # Fall back to config file
  if (!is.null(api_config$key)) {
    log_warn("Using API key from config file (not recommended for production)")
    return(api_config$key)
  }

  stop("API key not found in environment or config for: ", api_name)
}

# ==============================================================================
# LOGGING FUNCTIONS
# ==============================================================================

# Global log file path (set by init_logging)
.log_file <- NULL

#' Initialize logging system
#'
#' @param config Configuration list
init_logging <- function(config) {
  # Create logs directory if it doesn't exist
  log_dir <- dirname(config$paths$log_file)
  if (!dir.exists(log_dir)) {
    dir.create(log_dir, recursive = TRUE)
  }

  # Set global log file path
  .log_file <<- config$paths$log_file

  # Write header to log file
  timestamp <- format(Sys.time(), config$logging$timestamp_format)
  header <- paste0(
    "\n", paste(rep("=", 80), collapse = ""), "\n",
    "Author Profile Builder - Log Started: ", timestamp, "\n",
    paste(rep("=", 80), collapse = ""), "\n"
  )

  cat(header, file = .log_file, append = TRUE)
  log_info("Logging initialized")
}

#' Write log message
#'
#' @param level Log level (DEBUG, INFO, WARN, ERROR)
#' @param message Message to log
log_message <- function(level, message) {
  timestamp <- format(Sys.time(), "%Y-%m-%d %H:%M:%S")
  log_entry <- paste0("[", timestamp, "] [", level, "] ", message, "\n")

  # Console output
  cat(log_entry)

  # File output
  if (!is.null(.log_file)) {
    cat(log_entry, file = .log_file, append = TRUE)
  }
}

#' Log info message
log_info <- function(message) {
  log_message("INFO", message)
}

#' Log warning message
log_warn <- function(message) {
  log_message("WARN", message)
}

#' Log error message
log_error <- function(message) {
  log_message("ERROR", message)
}

#' Log debug message
log_debug <- function(message) {
  log_message("DEBUG", message)
}

# ==============================================================================
# DATABASE FUNCTIONS
# ==============================================================================

#' Create optimized database connection
#'
#' @param config Configuration list
#' @return DBI connection object
create_db_connection <- function(config) {
  db_path <- config$database$path

  if (!file.exists(db_path)) {
    stop("Database file not found: ", db_path)
  }

  log_info(paste("Connecting to database:", db_path))

  con <- dbConnect(RSQLite::SQLite(), db_path)

  # Apply optimizations
  opt <- config$database$optimization
  dbExecute(con, paste0("PRAGMA journal_mode=", opt$journal_mode))
  dbExecute(con, paste0("PRAGMA synchronous=", opt$synchronous))
  dbExecute(con, paste0("PRAGMA cache_size=", opt$cache_size))
  dbExecute(con, paste0("PRAGMA temp_store=", opt$temp_store))

  log_info("Database connection established and optimized")

  return(con)
}

#' Close database connection safely
#'
#' @param con DBI connection object
close_db_connection <- function(con) {
  if (!is.null(con) && dbIsValid(con)) {
    dbDisconnect(con)
    log_info("Database connection closed")
  }
}

#' Execute query with error handling
#'
#' @param con Database connection
#' @param query SQL query string
#' @param params Optional query parameters
#' @return Query results
safe_query <- function(con, query, params = NULL) {
  tryCatch({
    if (is.null(params)) {
      result <- dbGetQuery(con, query)
    } else {
      result <- dbGetQuery(con, query, params = params)
    }
    return(result)
  }, error = function(e) {
    log_error(paste("Query failed:", e$message))
    log_debug(paste("Query:", query))
    stop(e)
  })
}

#' Batch update database records
#'
#' @param con Database connection
#' @param table_name Target table name
#' @param update_data Data frame with updates
#' @param key_column Column to match on (e.g., "author_id")
#' @param batch_size Number of records per batch
batch_update <- function(con, table_name, update_data, key_column, batch_size = 10000) {
  total_rows <- nrow(update_data)
  num_batches <- ceiling(total_rows / batch_size)

  log_info(paste("Updating", total_rows, "records in", num_batches, "batches"))

  dbExecute(con, "BEGIN TRANSACTION")
  updated_count <- 0

  tryCatch({
    for (batch_num in 1:num_batches) {
      start_idx <- (batch_num - 1) * batch_size + 1
      end_idx <- min(batch_num * batch_size, total_rows)

      batch_data <- update_data[start_idx:end_idx, ]

      # Create temporary table for this batch
      temp_table <- paste0("temp_update_", batch_num)
      dbWriteTable(con, temp_table, batch_data, temporary = TRUE)

      # Build UPDATE query dynamically
      update_cols <- setdiff(names(batch_data), key_column)
      set_clause <- paste(
        sapply(update_cols, function(col) {
          paste0(table_name, ".", col, " = ", temp_table, ".", col)
        }),
        collapse = ", "
      )

      update_query <- sprintf(
        "UPDATE %s SET %s FROM %s WHERE %s.%s = %s.%s",
        table_name, set_clause, temp_table,
        table_name, key_column, temp_table, key_column
      )

      batch_updated <- dbExecute(con, update_query)
      updated_count <- updated_count + batch_updated

      # Clean up temporary table
      dbExecute(con, sprintf("DROP TABLE %s", temp_table))

      if (batch_num %% 5 == 0) {
        log_info(paste("  Progress:", updated_count, "/", total_rows,
                       paste0("(", round(updated_count / total_rows * 100, 1), "%)")))
      }
    }

    dbExecute(con, "COMMIT")
    log_info(paste("Successfully updated", updated_count, "records"))

  }, error = function(e) {
    dbExecute(con, "ROLLBACK")
    log_error(paste("Batch update failed, rolled back:", e$message))
    stop(e)
  })

  return(updated_count)
}

# ==============================================================================
# FILE I/O FUNCTIONS
# ==============================================================================

#' Ensure directory exists
#'
#' @param path Directory path
ensure_dir <- function(path) {
  if (!dir.exists(path)) {
    dir.create(path, recursive = TRUE)
    log_info(paste("Created directory:", path))
  }
}

#' Save data to JSON with pretty formatting
#'
#' @param data Data frame or list
#' @param file_path Output file path
save_json <- function(data, file_path) {
  ensure_dir(dirname(file_path))

  write_json(
    data,
    file_path,
    pretty = TRUE,
    auto_unbox = TRUE,
    na = "null"
  )

  file_size <- file.info(file_path)$size
  log_info(paste("Saved JSON:", file_path,
                 paste0("(", round(file_size / 1024, 2), " KB)")))
}

#' Load data from JSON
#'
#' @param file_path Input file path
#' @return Data frame or list
load_json <- function(file_path) {
  if (!file.exists(file_path)) {
    stop("JSON file not found: ", file_path)
  }

  data <- read_json(file_path, simplifyVector = TRUE)
  log_info(paste("Loaded JSON:", file_path))

  return(data)
}

#' Load or create cache
#'
#' @param cache_path Path to RDS cache file
#' @return Data frame with cached data
load_or_create_cache <- function(cache_path) {
  if (file.exists(cache_path)) {
    cache <- readRDS(cache_path)
    log_info(paste("Loaded cache:", cache_path,
                   paste0("(", nrow(cache), " entries)")))
    return(cache)
  } else {
    log_info("No existing cache found, creating new cache")
    return(data.frame(
      name = character(0),
      country_code = character(0),
      gender = character(0),
      probability = numeric(0),
      count = numeric(0),
      stringsAsFactors = FALSE
    ))
  }
}

#' Save cache to RDS
#'
#' @param cache Data frame with cache data
#' @param cache_path Path to RDS cache file
save_cache <- function(cache, cache_path) {
  ensure_dir(dirname(cache_path))
  saveRDS(cache, cache_path)
  log_info(paste("Saved cache:", cache_path,
                 paste0("(", nrow(cache), " entries)")))
}

# ==============================================================================
# NAME PARSING FUNCTIONS
# ==============================================================================

#' Advanced name parsing function
#'
#' @param display_name Full display name
#' @return Extracted first name or NA
parse_forename <- function(display_name) {
  if (is.na(display_name) || display_name == "" || nchar(display_name) < 2) {
    return(NA)
  }

  # Normalize Unicode dashes
  clean_name <- display_name %>%
    str_trim() %>%
    str_replace_all("[\u2010-\u2015]", "-")

  # Single word case
  if (!str_detect(clean_name, " ")) {
    if (str_detect(clean_name, "[\\.-]")) {
      # Handle periods
      if (str_detect(clean_name, "\\.")) {
        period_parts <- str_split(clean_name, "\\.")[[1]]

        if (length(period_parts) >= 2) {
          first_part <- str_trim(period_parts[1])

          if (nchar(first_part) <= 2) {
            return(NA)  # Likely initials
          }

          if (nchar(first_part) >= 3) {
            return(first_part)
          }
        }
      }

      # Handle hyphens (compound names)
      if (str_detect(clean_name, "-") && !str_detect(clean_name, "\\.")) {
        compound_name <- str_replace_all(clean_name, "^[^A-Za-z\u00C0-\u024F]+|[^A-Za-z\u00C0-\u024F-]+$", "")
        if (nchar(compound_name) >= 3) {
          return(compound_name)
        }
      }
    }
    return(NA)
  }

  # Space-separated format
  parts <- str_split(clean_name, "\\s+")[[1]]
  parts <- parts[parts != ""]

  if (length(parts) < 2) {
    return(NA)
  }

  # Check if looks like initial
  looks_like_initial <- function(part) {
    clean_part <- str_replace_all(part, "[\\.-]", "")

    return(
      nchar(clean_part) == 1 ||
        (nchar(clean_part) <= 2 && str_detect(part, "\\.")) ||
        (nchar(clean_part) <= 4 && str_detect(clean_part, "^[A-Z]+$")) ||
        str_detect(part, "^[A-Z][\\.-][A-Z]")
    )
  }

  first_part <- parts[1]

  if (looks_like_initial(first_part)) {
    return(NA)
  }

  # Clean extracted name
  first_name <- first_part %>%
    str_replace_all("\\.", "") %>%
    str_trim()

  # Validation
  if (nchar(first_name) < 2) {
    return(NA)
  }

  if (str_detect(first_name, "^[A-Z]+$") && nchar(first_name) <= 4) {
    return(NA)
  }

  if (!str_detect(first_name, "^[A-Za-z\u00C0-\u00FF\u0100-\u017F\u0180-\u024F-]+$")) {
    return(NA)
  }

  return(first_name)
}

# ==============================================================================
# HELPER OPERATORS
# ==============================================================================

#' NULL coalescing operator
`%||%` <- function(x, y) {
  if (is.null(x)) y else x
}

# ==============================================================================
# PROGRESS REPORTING
# ==============================================================================

#' Report progress during batch processing
#'
#' @param current Current iteration number
#' @param total Total iterations
#' @param interval Report every N iterations
#' @param prefix Message prefix
report_progress <- function(current, total, interval = 1000, prefix = "Progress") {
  if (current %% interval == 0 || current == total) {
    pct <- round(current / total * 100, 1)
    log_info(paste0(prefix, ": ", current, "/", total, " (", pct, "%)"))
  }
}

# ==============================================================================
# VALIDATION HELPERS
# ==============================================================================

#' Calculate coverage statistics
#'
#' @param data Data frame with predictions
#' @param config Configuration list
#' @return List with statistics
calculate_coverage_stats <- function(data, config) {
  stats <- list(
    total_records = nrow(data),
    valid_forenames = sum(!is.na(data$forename)),
    with_country = sum(!is.na(data$country_code)),
    cache_predictions = sum(!is.na(data$gender_cache), na.rm = TRUE),
    gender_r_predictions = sum(!is.na(data$gender_r), na.rm = TRUE),
    guesser_predictions = sum(!is.na(data$gender_guesser), na.rm = TRUE),
    genderize_predictions = sum(!is.na(data$gender_genderize), na.rm = TRUE)
  )

  return(stats)
}

# ==============================================================================
# INITIALIZATION
# ==============================================================================

log_info("Utility functions loaded successfully")
