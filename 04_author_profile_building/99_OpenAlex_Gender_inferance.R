# ==============================================================================
# Targeted Display Name Gender Analysis - Database Optimised Version
# ==============================================================================

library(DBI)
library(RSQLite)
library(dplyr)
library(stringr)
library(gender)
library(tidyverse)

# Helper function for NULL handling
`%||%` <- function(x, y) if(is.null(x)) y else x

# Configuration
DB_PATH <- "flow_cytometry_normalized.db"  # Update with your database path
genderize_api_key <- "7dba1eabce863d4d58a81f512862e4d9"
cache_file <- "genderize_cache.rds"

cat("=== TARGETED AUTHOR GENDER ANALYSIS - OPTIMISED VERSION ===\n")
cat("Start time:", as.character(Sys.time()), "\n\n")

# ==============================================================================
# ADVANCED NAME PARSING FUNCTION (unchanged)
# ==============================================================================

parse_display_name_targeted <- function(display_name) {
  if(is.na(display_name) || display_name == "" || nchar(display_name) < 2) {
    return(NA)
  }
  
  # Enhanced cleaning with dash normalisation
  clean_name <- display_name %>%
    str_trim() %>%
    # Normalise all types of dashes to regular hyphens
    # U+2010 (hyphen), U+2011 (non-breaking hyphen), U+2012 (figure dash), 
    # U+2013 (en dash), U+2014 (em dash), U+2015 (horizontal bar)
    str_replace_all("[\u2010-\u2015]", "-")
  
  # Check if it's a single word (no spaces)
  if(!str_detect(clean_name, " ")) {
    # Single word case - could be initials or compound name with periods/hyphens
    if(str_detect(clean_name, "[\\.-]")) {
      # Has periods or hyphens - could be initials or name.surname or compound-name
      
      # Split on periods first, then handle dashes
      if(str_detect(clean_name, "\\.")) {
        period_parts <- str_split(clean_name, "\\.")[[1]]
        
        # If multiple short parts, likely initials (K.W.Pawar) → skip
        if(length(period_parts) >= 2) {
          first_part <- str_trim(period_parts[1])
          second_part <- str_trim(period_parts[2])
          
          # If first part is very short, likely initials → skip
          if(nchar(first_part) <= 2) {
            return(NA)  # Skip K.W.Pawar type names
          }
          
          # If looks like FirstnameLastname → extract first part
          if(nchar(first_part) >= 3 && nchar(second_part) >= 3) {
            return(first_part)  # Extract "James" from "James.Taylor"
          }
        }
      }
      
      # If it has hyphens but no periods, could be compound name like "Jean-François"
      if(str_detect(clean_name, "-") && !str_detect(clean_name, "\\.")) {
        # Single compound name without spaces - treat as potential first name
        # Remove any leading/trailing punctuation but keep internal hyphens
        compound_name <- str_replace_all(clean_name, "^[^A-Za-z\u00C0-\u024F]+|[^A-Za-z\u00C0-\u024F-]+$", "")
        if(nchar(compound_name) >= 3) {
          return(compound_name)  # Keep "Jean-François" as is
        }
      }
    }
    # Single word without periods or hyphens, or unclear pattern → skip
    return(NA)
  }
  
  # Space-separated format (98.5% of cases)
  parts <- str_split(clean_name, "\\s+")[[1]]
  parts <- parts[parts != ""]  # Remove empty parts
  
  if(length(parts) < 2) {
    return(NA)
  }
  
  # Enhanced function to detect initials and abbreviations
  looks_like_initial <- function(part) {
    # Remove periods and hyphens for analysis
    clean_part <- str_replace_all(part, "[\\.-]", "")
    
    # It's likely an initial/abbreviation if:
    # 1. Single character (B, W, etc.)
    # 2. 1-2 chars with periods (W., D.P., etc.)  
    # 3. 2-4 consecutive uppercase letters (GM, AKMZ, etc.)
    # 4. Complex initial patterns (D.-S., K.W., etc.)
    
    return(
      nchar(clean_part) == 1 ||  # Single letter
        (nchar(clean_part) <= 2 && str_detect(part, "\\.")) ||  # Short with periods
        (nchar(clean_part) <= 4 && str_detect(clean_part, "^[A-Z]+$")) ||  # All caps abbreviation
        str_detect(part, "^[A-Z][\\.-][A-Z]")  # Pattern like D.-S. or K.W.
    )
  }
  
  # Check if name starts with any initial-like patterns
  first_part <- parts[1]
  
  # Skip entirely if first part looks like initial/abbreviation
  if(looks_like_initial(first_part)) {
    return(NA)
  }
  
  # Also check for multiple consecutive initial-like parts
  initial_count <- 0
  for(i in 1:min(3, length(parts))) {  # Check first 3 parts max
    if(looks_like_initial(parts[i])) {
      initial_count <- initial_count + 1
    } else {
      break
    }
  }
  
  # Skip if we found any initials at the start
  if(initial_count > 0) {
    return(NA)
  }
  
  # If we get here, first part should be a proper name
  first_name_candidate <- first_part
  
  # Clean the extracted name
  first_name_candidate <- str_replace_all(first_name_candidate, "\\.", "")
  first_name_candidate <- str_trim(first_name_candidate)
  
  # Final validation - must be at least 2 characters
  if(nchar(first_name_candidate) < 2) {
    return(NA)
  }
  
  # Additional validation: skip if it's all uppercase (likely abbreviation)
  if(str_detect(first_name_candidate, "^[A-Z]+$") && nchar(first_name_candidate) <= 4) {
    return(NA)
  }
  
  # Check that it contains only letters, accents, and hyphens (extended European character set)
  # Unicode ranges:
  # - A-Za-z: Basic Latin letters
  # - \u00C0-\u00FF: Latin-1 Supplement (À, Á, Â, Ã, Ä, Å, Æ, Ç, È, É, etc.)
  # - \u0100-\u017F: Latin Extended-A (Ā, Ă, Ą, Ć, Ĉ, Ċ, Č, Ď, etc.)  
  # - \u0180-\u024F: Latin Extended-B (ƃ, Ƃ, Ƅ, Ɔ, Ƈ, etc.)
  # - Plus hyphens (-) for compound names
  if(!str_detect(first_name_candidate, "^[A-Za-z\u00C0-\u00FF\u0100-\u017F\u0180-\u024F-]+$")) {
    return(NA)
  }
  
  # Final check: proper names should have mixed case or be reasonable length
  # Skip very short all-caps that might have slipped through
  if(nchar(first_name_candidate) <= 3 && str_detect(first_name_candidate, "^[A-Z]+$")) {
    return(NA)
  }
  
  return(first_name_candidate)
}

# ==============================================================================
# DATABASE SETUP AND OPTIMISED LOADING
# ==============================================================================

cat("--- Setting up optimised database connection ---\n")

con <- dbConnect(RSQLite::SQLite(), DB_PATH)

# Enable WAL mode for better concurrent access and performance
dbExecute(con, "PRAGMA journal_mode=WAL")
dbExecute(con, "PRAGMA synchronous=NORMAL")
dbExecute(con, "PRAGMA cache_size=10000")
dbExecute(con, "PRAGMA temp_store=memory")

# Ensure author_id is properly indexed as primary key
cat("Checking and creating database indexes...\n")

# Check if authors table has proper primary key
table_info <- dbGetQuery(con, "PRAGMA table_info(authors)")
pk_exists <- any(table_info$pk == 1 & table_info$name == "author_id")

if(!pk_exists) {
  cat("Creating primary key index on author_id...\n")
  tryCatch({
    dbExecute(con, "CREATE UNIQUE INDEX IF NOT EXISTS idx_authors_author_id ON authors(author_id)")
  }, error = function(e) {
    cat("Note: Could not create unique index (may already exist):", e$message, "\n")
  })
}

# Add gender column if it doesn't exist
if(!"gender" %in% table_info$name) {
  dbExecute(con, "ALTER TABLE authors ADD COLUMN gender TEXT")
  cat("Added gender column to authors table\n")
}

# Create index on display_name for faster filtering
dbExecute(con, "CREATE INDEX IF NOT EXISTS idx_authors_display_name ON authors(display_name)")

# Create index on gender for faster filtering of NULL values
dbExecute(con, "CREATE INDEX IF NOT EXISTS idx_authors_gender ON authors(gender)")

cat("Database optimisation complete.\n\n")

# ==============================================================================
# OPTIMISED AUTHOR DATA LOADING - EXCLUDE EXISTING GENDERS
# ==============================================================================

cat("--- Loading authors without existing gender assignments ---\n")

# Optimised query to only load authors that need gender prediction
authors_query <- "
  SELECT DISTINCT
    a.author_id,
    a.display_name
  FROM authors AS a
  WHERE a.display_name IS NOT NULL 
    AND a.display_name != ''
    AND (a.gender IS NULL OR a.gender = '')
"

authors_raw <- dbGetQuery(con, authors_query)
cat("Authors needing gender prediction:", nrow(authors_raw), "\n")

if(nrow(authors_raw) == 0) {
  cat("No authors need gender prediction. Analysis complete.\n")
  dbDisconnect(con)
  quit()
}

# ==============================================================================
# BATCHED NAME PARSING (unchanged but optimised batch size)
# ==============================================================================

cat("--- Processing", nrow(authors_raw), "authors in optimised batches ---\n")

# Optimised configuration
batch_size <- 25000  # Larger batches for better performance
total_authors <- nrow(authors_raw)
num_batches <- ceiling(total_authors / batch_size)

cat("Batch size:", batch_size, "\n")
cat("Total batches:", num_batches, "\n\n")

# Initialise empty results dataframe
authors_parsed <- data.frame()

# Process each batch
for(batch_num in 1:num_batches) {
  # Calculate batch indices
  start_idx <- (batch_num - 1) * batch_size + 1
  end_idx <- min(batch_num * batch_size, total_authors)
  
  cat("Processing batch", batch_num, "of", num_batches, 
      "(rows", start_idx, "to", end_idx, ")...\n")
  
  # Extract current batch
  current_batch <- authors_raw[start_idx:end_idx, ]
  
  # Parse current batch
  batch_parsed <- current_batch %>%
    mutate(
      extracted_first_name = map_chr(display_name, parse_display_name_targeted),
      parsing_success = !is.na(extracted_first_name),
      parsing_date = Sys.Date()
    )
  
  # Combine with previous results
  authors_parsed <- bind_rows(authors_parsed, batch_parsed)
  
  # Progress update
  processed_so_far <- nrow(authors_parsed)
  success_so_far <- sum(authors_parsed$parsing_success)
  success_rate <- round(success_so_far / processed_so_far * 100, 2)
  
  cat("  Batch complete. Processed:", processed_so_far, "/", total_authors,
      "(", round(processed_so_far / total_authors * 100, 1), "%)",
      "| Success rate:", success_rate, "%\n")
  
  # Force garbage collection every 5 batches to manage memory
  if(batch_num %% 5 == 0) {
    gc()
    cat("  Memory cleanup completed\n")
  }
  
  cat("\n")
}

cat("=== BATCHED PARSING COMPLETE ===\n")
cat("Final results:", nrow(authors_parsed), "authors processed\n")
cat("Overall success rate:", round(sum(authors_parsed$parsing_success) / nrow(authors_parsed) * 100, 2), "%\n")

# Parsing statistics
parsing_stats <- authors_parsed %>%
  summarise(
    total_authors = n(),
    successful_parsing = sum(parsing_success, na.rm = TRUE),
    parsing_rate = round(successful_parsing / total_authors * 100, 2),
    .groups = "drop"
  )

cat("\nParsing Results:\n")
cat("- Total authors:", parsing_stats$total_authors, "\n")
cat("- Successfully parsed:", parsing_stats$successful_parsing, "\n")
cat("- Success rate:", parsing_stats$parsing_rate, "%\n")

# ==============================================================================
# OPTIMISED GENDER PREDICTION PIPELINE
# ==============================================================================

cat("\n--- Preparing for gender prediction ---\n")

# Get unique names for prediction
unique_names_data <- authors_parsed %>%
  filter(parsing_success) %>%
  distinct(extracted_first_name, .keep_all = TRUE) %>%
  select(extracted_first_name)

cat("Unique first names for analysis:", nrow(unique_names_data), "\n")

# Load existing cache
if(file.exists(cache_file)) {
  cat("Loading existing cache...\n")
  genderize_cache <- readRDS(cache_file)
  cat("Cache contains:", nrow(genderize_cache), "names\n")
} else {
  genderize_cache <- data.frame(
    name = character(0),
    genderize_gender = character(0),
    genderize_probability = numeric(0),
    genderize_count = numeric(0),
    stringsAsFactors = FALSE
  )
}

# Identify names needing prediction
all_names <- unique(unique_names_data$extracted_first_name)
cached_names <- intersect(all_names, genderize_cache$name)
uncached_names <- setdiff(all_names, genderize_cache$name)

cat("Names in cache:", length(cached_names), "\n")
cat("Names needing prediction:", length(uncached_names), "\n")

# ==============================================================================
# IMPROVED GENDERIZE.IO API WITH BATCHING
# ==============================================================================

# Optimised Genderize.io API with batch requests (FIXED)
use_genderize_api_batched <- function(names_vector, api_key) {
  if(length(names_vector) == 0) {
    return(data.frame(
      name = character(0),
      genderize_gender = character(0),
      genderize_probability = numeric(0),
      genderize_count = numeric(0)
    ))
  }
  
  if(!require(httr, quietly = TRUE)) {
    install.packages("httr")
    library(httr)
  }
  if(!require(jsonlite, quietly = TRUE)) {
    install.packages("jsonlite")
    library(jsonlite)
  }
  
  results <- data.frame(
    name = character(0),
    genderize_gender = character(0),
    genderize_probability = numeric(0),
    genderize_count = numeric(0)
  )
  
  # Process in batches of 10 (max allowed by Genderize.io)
  batch_size <- 10
  total_names <- length(names_vector)
  num_batches <- ceiling(total_names / batch_size)
  
  cat("Processing", total_names, "names in", num_batches, "batches of", batch_size, "\n")
  
  for(i in 1:num_batches) {
    start_idx <- (i - 1) * batch_size + 1
    end_idx <- min(i * batch_size, total_names)
    batch_names <- names_vector[start_idx:end_idx]
    
    tryCatch({
      # Build query parameters for batch request
      query_params <- list()
      
      # Add API key
      query_params$apikey <- api_key
      
      # Add batch names using indexed format: name[0], name[1], etc.
      for(j in seq_along(batch_names)) {
        query_params[[paste0("name[", j-1, "]")]] <- batch_names[j]
      }
      
      # Make GET request with query parameters
      response <- GET(
        url = "https://api.genderize.io",
        query = query_params,
        timeout(30)
      )
      
      if(status_code(response) == 200) {
        content_data <- content(response, "text", encoding = "UTF-8")
        parsed_data <- fromJSON(content_data)
        
        # Handle both single result and array results
        if(is.data.frame(parsed_data)) {
          batch_results <- parsed_data
        } else if(is.list(parsed_data) && length(parsed_data) > 0) {
          # Convert list to dataframe
          batch_results <- data.frame(
            name = sapply(parsed_data, function(x) x$name %||% NA),
            gender = sapply(parsed_data, function(x) x$gender %||% NA),
            probability = sapply(parsed_data, function(x) x$probability %||% NA),
            count = sapply(parsed_data, function(x) x$count %||% NA),
            stringsAsFactors = FALSE
          )
        } else {
          # Single result - convert to dataframe
          batch_results <- data.frame(
            name = parsed_data$name %||% batch_names[1],
            gender = parsed_data$gender %||% NA,
            probability = parsed_data$probability %||% NA,
            count = parsed_data$count %||% NA,
            stringsAsFactors = FALSE
          )
        }
        
        # Standardise column names and add to results
        if(nrow(batch_results) > 0) {
          standardised_batch <- data.frame(
            name = batch_results$name,
            genderize_gender = batch_results$gender,
            genderize_probability = batch_results$probability,
            genderize_count = batch_results$count,
            stringsAsFactors = FALSE
          )
          
          results <- bind_rows(results, standardised_batch)
        }
        
      } else if(status_code(response) == 402) {
        cat("API quota exceeded at batch", i, "\n")
        break
      } else if(status_code(response) == 429) {
        cat("Rate limit exceeded at batch", i, ", waiting 60 seconds...\n")
        Sys.sleep(60)
        next  # Retry this batch
      } else {
        cat("API request failed with status:", status_code(response), "for batch", i, "\n")
        # Print response content for debugging
        error_content <- content(response, "text", encoding = "UTF-8")
        cat("Response:", substr(error_content, 1, 200), "\n")
      }
      
      # Progress update
      if(i %% 100 == 0 || i == num_batches) {
        cat("Processed", min(end_idx, total_names), "/", total_names, 
            "names (", round(min(end_idx, total_names) / total_names * 100, 1), "%)\n")
      }
      
      # Respectful delay between requests
      if(i < num_batches) Sys.sleep(0.1)
      
    }, error = function(e) {
      cat("Error processing batch", i, ":", e$message, "\n")
      # Continue with next batch on error
    })
  }
  
  # Cache all results immediately
  if(nrow(results) > 0) {
    cat("Caching", nrow(results), "new API results...\n")
    
    # Update cache with new results
    updated_cache <- genderize_cache %>%
      bind_rows(results) %>%
      distinct(name, .keep_all = TRUE)
    
    saveRDS(updated_cache, cache_file)
    cat("Cache updated successfully\n")
  }
  
  return(results)
}

# Helper operator for handling NULL values
`%||%` <- function(x, y) {
  if (is.null(x)) y else x
}

# ==============================================================================
# GENDER PREDICTION FUNCTIONS (other methods unchanged)
# ==============================================================================

# Safe gender prediction using gender R package
safe_gender_predict <- function(names_vector, method = "ssa") {
  if(length(names_vector) == 0) {
    return(data.frame(
      name = character(0),
      gender = character(0),
      proportion_male = numeric(0),
      proportion_female = numeric(0)
    ))
  }
  
  tryCatch({
    gender_results <- gender(names_vector, method = method)
    return(gender_results)
  }, error = function(e) {
    cat("Gender R package failed:", e$message, "\n")
    return(data.frame(
      name = names_vector,
      gender = rep(NA, length(names_vector)),
      proportion_male = rep(NA, length(names_vector)),
      proportion_female = rep(NA, length(names_vector))
    ))
  })
}

# Gender-guesser function
use_gender_guesser <- function(names_vector) {
  if(length(names_vector) == 0) {
    return(data.frame(
      name = character(0),
      gender_guesser_clean = character(0)
    ))
  }
  
  if(!require(reticulate, quietly = TRUE)) {
    cat("Installing reticulate...\n")
    install.packages("reticulate")
    library(reticulate)
  }
  
  tryCatch({
    gender_guesser <- import("gender_guesser.detector")
    detector <- gender_guesser$Detector()
    
    results <- sapply(names_vector, function(name) {
      detector$get_gender(name)
    })
    
    clean_results <- case_when(
      results %in% c("male", "mostly_male") ~ "male",
      results %in% c("female", "mostly_female") ~ "female",
      TRUE ~ "unknown"
    )
    
    return(data.frame(
      name = names_vector,
      gender_guesser_clean = clean_results,
      stringsAsFactors = FALSE
    ))
    
  }, error = function(e) {
    cat("Gender-guesser not available:", e$message, "\n")
    return(data.frame(
      name = names_vector,
      gender_guesser_clean = rep("unknown", length(names_vector)),
      stringsAsFactors = FALSE
    ))
  })
}

# ==============================================================================
# RUN OPTIMISED PREDICTION PIPELINE
# ==============================================================================

cat("\n--- Running gender prediction pipeline ---\n")

# Method 1: Gender R package
cat("Step 1: Gender R package (SSA method)...\n")
gender_r_results <- safe_gender_predict(uncached_names, method = "ssa")

if(nrow(gender_r_results) < length(uncached_names) * 0.5) {
  cat("SSA coverage low, trying IPUMS method...\n")
  gender_r_ipums <- safe_gender_predict(uncached_names, method = "ipums")
  if(nrow(gender_r_ipums) > nrow(gender_r_results)) {
    gender_r_results <- gender_r_ipums
  }
}

cat("Gender R results:", sum(!is.na(gender_r_results$gender)), "predictions\n")

# Method 2: Gender-guesser for unmatched
unmatched_after_r <- setdiff(uncached_names, 
                             gender_r_results$name[!is.na(gender_r_results$gender)])

cat("Step 2: Gender-guesser for", length(unmatched_after_r), "unmatched names...\n")
guesser_results <- use_gender_guesser(unmatched_after_r)
guesser_matched <- sum(guesser_results$gender_guesser_clean %in% c("male", "female"))
cat("Gender-guesser results:", guesser_matched, "predictions\n")

# Method 3: Optimised Genderize.io for remaining
still_unmatched <- setdiff(unmatched_after_r, 
                           guesser_results$name[guesser_results$gender_guesser_clean != "unknown"])

if(length(still_unmatched) > 0) {
  cat("Step 3: Genderize.io batched API for", length(still_unmatched), "remaining names...\n")
  
  genderize_new <- use_genderize_api_batched(still_unmatched, genderize_api_key)
  cat("Genderize.io results:", nrow(genderize_new), "predictions\n")
  
  # Update global cache
  if(nrow(genderize_new) > 0) {
    genderize_cache <- readRDS(cache_file)  # Re-read updated cache
  }
} else {
  genderize_new <- data.frame()
}

# ==============================================================================
# COMBINE RESULTS (unchanged)
# ==============================================================================

cat("\n--- Combining prediction results ---\n")

# Create comprehensive gender lookup
all_gender_results <- genderize_cache %>%
  select(name, gender = genderize_gender, confidence = genderize_probability) %>%
  mutate(method = "cache") %>%
  bind_rows(
    gender_r_results %>%
      select(name, gender, confidence = proportion_male) %>%
      mutate(
        confidence = case_when(
          gender == "male" ~ confidence,
          gender == "female" ~ 1 - confidence,
          TRUE ~ NA_real_
        ),
        method = "gender_r"
      )
  ) %>%
  bind_rows(
    guesser_results %>%
      filter(gender_guesser_clean != "unknown") %>%
      select(name, gender = gender_guesser_clean) %>%
      mutate(confidence = 0.75, method = "guesser")
  ) %>%
  # Keep first result per name (priority order)
  group_by(name) %>%
  slice_head(n = 1) %>%
  ungroup() %>%
  # Standardise to M/F
  mutate(
    final_gender = case_when(
      gender == "male" ~ "M",
      gender == "female" ~ "F",
      TRUE ~ NA_character_
    )
  ) %>%
  filter(!is.na(final_gender))

# Join back to authors
authors_with_gender <- authors_parsed %>%
  left_join(all_gender_results %>% select(name, final_gender, confidence, method), 
            by = c("extracted_first_name" = "name"))

# ==============================================================================
# OPTIMISED DATABASE UPDATES WITH CHUNKING
# ==============================================================================

cat("\n--- Performing optimised database updates ---\n")

# Get records that need updating
gender_updates <- authors_with_gender %>%
  filter(!is.na(final_gender)) %>%
  select(author_id, final_gender)

if(nrow(gender_updates) > 0) {
  cat("Updating", nrow(gender_updates), "author records with gender information\n")
  
  # Chunk updates for better performance and memory management
  update_batch_size <- 10000
  total_updates <- nrow(gender_updates)
  num_update_batches <- ceiling(total_updates / update_batch_size)
  
  cat("Processing updates in", num_update_batches, "batches of", update_batch_size, "\n")
  
  # Begin transaction for all updates
  dbExecute(con, "BEGIN TRANSACTION")
  
  updated_count <- 0
  
  tryCatch({
    for(batch_num in 1:num_update_batches) {
      start_idx <- (batch_num - 1) * update_batch_size + 1
      end_idx <- min(batch_num * update_batch_size, total_updates)
      
      batch_updates <- gender_updates[start_idx:end_idx, ]
      
      cat("Processing update batch", batch_num, "of", num_update_batches, 
          "(", nrow(batch_updates), "records)...\n")
      
      # Create temporary table for this batch
      temp_table_name <- paste0("temp_gender_updates_", batch_num)
      dbWriteTable(con, temp_table_name, batch_updates, temporary = TRUE)
      
      # Optimised UPDATE using JOIN syntax for SQLite
      batch_updated <- dbExecute(con, sprintf("
        UPDATE authors 
        SET gender = %s.final_gender
        FROM %s 
        WHERE authors.author_id = %s.author_id
      ", temp_table_name, temp_table_name, temp_table_name))
      
      updated_count <- updated_count + batch_updated
      
      cat("  Updated", batch_updated, "records in this batch\n")
      
      # Clean up temporary table
      dbExecute(con, sprintf("DROP TABLE %s", temp_table_name))
      
      # Optional progress update
      if(batch_num %% 5 == 0) {
        cat("  Total updated so far:", updated_count, "/", total_updates, 
            "(", round(updated_count / total_updates * 100, 1), "%)\n")
      }
    }
    
    # Commit all updates
    dbExecute(con, "COMMIT")
    cat("All updates committed successfully\n")
    
  }, error = function(e) {
    # Rollback on error
    dbExecute(con, "ROLLBACK")
    cat("Error during updates, rolled back:", e$message, "\n")
    updated_count <- 0
  })
  
  cat("Final update count:", updated_count, "records\n")
  
} else {
  cat("No records to update\n")
}

# ==============================================================================
# GENERATE RESULTS AND CLEANUP
# ==============================================================================

# Generate summary statistics
final_summary <- authors_with_gender %>%
  summarise(
    total_authors = n(),
    successful_parsing = sum(parsing_success),
    gender_predictions = sum(!is.na(final_gender)),
    coverage_all = round(gender_predictions / total_authors * 100, 2),
    coverage_parsed = round(gender_predictions / successful_parsing * 100, 2),
    male_count = sum(final_gender == "M", na.rm = TRUE),
    female_count = sum(final_gender == "F", na.rm = TRUE),
    high_confidence = sum(confidence >= 0.8, na.rm = TRUE)
  )

cat("\n=== FINAL RESULTS ===\n")
cat("Total authors processed:", final_summary$total_authors, "\n")
cat("Successfully parsed names:", final_summary$successful_parsing, "\n")
cat("Gender predictions made:", final_summary$gender_predictions, "\n")
cat("Overall coverage:", final_summary$coverage_all, "%\n")
cat("Coverage of parsed names:", final_summary$coverage_parsed, "%\n")
cat("Male predictions:", final_summary$male_count, "\n")
cat("Female predictions:", final_summary$female_count, "\n")
cat("High confidence (≥80%):", final_summary$high_confidence, "\n")

# Method breakdown
method_breakdown <- authors_with_gender %>%
  filter(!is.na(final_gender)) %>%
  count(method, sort = TRUE)

cat("\nMethod breakdown:\n")
print(method_breakdown)

# Verify final database state
verification <- dbGetQuery(con, "
  SELECT 
    gender,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM authors WHERE gender IS NOT NULL), 2) as percentage
  FROM authors
  WHERE gender IS NOT NULL
  GROUP BY gender
  ORDER BY count DESC
")

cat("\nFinal database gender distribution:\n")
print(verification)

# Cleanup and save
dbDisconnect(con)
saveRDS(authors_with_gender, "author_profiles_gender_results_optimised.rds")

cat("\n=== OPTIMISED ANALYSIS COMPLETE ===\n")
cat("End time:", as.character(Sys.time()), "\n")