# ==============================================================================
# Step 1: Extract Author Names and Country Codes
# ==============================================================================
# This script:
# 1. Reads author_id and display_name from authors table
# 2. Reads author_id and alternative_name from AUTHOR_NAME_VARIANTS table
# 3. Extracts country codes from institutions via author_institutions
# 4. Parses forenames from all names
# 5. Outputs JSON file with author_id, forename, country_code
# ==============================================================================

suppressPackageStartupMessages({
  library(dplyr)
  library(stringr)
  library(purrr)
})

source("utils.R")

# ==============================================================================
# MAIN FUNCTION
# ==============================================================================

extract_author_names <- function(config) {
  log_info("=== STEP 1: EXTRACT AUTHOR NAMES ===")

  # Connect to database
  con <- create_db_connection(config)

  tryCatch({
    # Get table names from config
    authors_table <- config$database$tables$authors
    variants_table <- config$database$tables$author_name_variants
    institutions_table <- config$database$tables$institutions
    author_institutions_table <- config$database$tables$author_institutions

    # =========================================================================
    # Extract authors and display names
    # =========================================================================
    log_info("Extracting authors and display names...")

    authors_query <- sprintf("
      SELECT
        author_id,
        display_name
      FROM %s
      WHERE display_name IS NOT NULL
        AND display_name != ''
    ", authors_table)

    authors_df <- safe_query(con, authors_query)
    log_info(paste("Loaded", nrow(authors_df), "authors with display names"))

    # =========================================================================
    # Extract name variants (if enabled)
    # =========================================================================
    variants_df <- NULL

    if (config$features$use_name_variants) {
      log_info("Extracting author name variants...")

      # Check if table exists
      table_exists <- dbExistsTable(con, variants_table)

      if (table_exists) {
        variants_query <- sprintf("
          SELECT
            author_id,
            alternative_name
          FROM %s
          WHERE alternative_name IS NOT NULL
            AND alternative_name != ''
        ", variants_table)

        variants_df <- safe_query(con, variants_query)
        log_info(paste("Loaded", nrow(variants_df), "name variants"))
      } else {
        log_warn(paste("Table", variants_table, "not found, skipping variants"))
      }
    } else {
      log_info("Name variants disabled in config")
    }

    # =========================================================================
    # Extract country codes (if enabled)
    # =========================================================================
    country_codes <- NULL

    if (config$features$use_country_context) {
      log_info("Extracting country codes from institutions...")

      # Check if tables exist
      if (dbExistsTable(con, institutions_table) &&
          dbExistsTable(con, author_institutions_table)) {

        country_query <- sprintf("
          SELECT DISTINCT
            ai.author_id,
            i.country_code
          FROM %s AS ai
          INNER JOIN %s AS i
            ON ai.institution_id = i.institution_id
          WHERE i.country_code IS NOT NULL
            AND i.country_code != ''
        ", author_institutions_table, institutions_table)

        country_df <- safe_query(con, country_query)
        log_info(paste("Loaded", nrow(country_df), "author-country associations"))

        # Handle authors with multiple countries - take most common
        country_codes <- country_df %>%
          group_by(author_id) %>%
          # Count occurrences of each country per author
          add_count(country_code, name = "country_freq") %>%
          # Take the most frequent country
          slice_max(country_freq, n = 1, with_ties = FALSE) %>%
          # If tie, take first alphabetically
          arrange(author_id, country_code) %>%
          slice_head(n = 1) %>%
          ungroup() %>%
          select(author_id, country_code)

        log_info(paste("Resolved to", nrow(country_codes), "unique author-country pairs"))

      } else {
        log_warn("Institution tables not found, skipping country extraction")
      }
    } else {
      log_info("Country context disabled in config")
    }

    # =========================================================================
    # Combine all names (display_name + variants)
    # =========================================================================
    log_info("Combining display names and variants...")

    # Start with display names
    all_names <- authors_df %>%
      rename(name = display_name) %>%
      mutate(source = "display_name")

    # Add variants if available
    if (!is.null(variants_df) && nrow(variants_df) > 0) {
      variants_processed <- variants_df %>%
        rename(name = alternative_name) %>%
        mutate(source = "variant")

      all_names <- bind_rows(all_names, variants_processed)
    }

    log_info(paste("Total names to process:", nrow(all_names)))

    # =========================================================================
    # Parse forenames in batches
    # =========================================================================
    log_info("Parsing forenames from names...")

    batch_size <- config$processing$batch_size
    total_names <- nrow(all_names)
    num_batches <- ceiling(total_names / batch_size)

    log_info(paste("Processing in", num_batches, "batches of", batch_size))

    # Initialize results
    parsed_names <- data.frame()

    for (batch_num in 1:num_batches) {
      start_idx <- (batch_num - 1) * batch_size + 1
      end_idx <- min(batch_num * batch_size, total_names)

      current_batch <- all_names[start_idx:end_idx, ]

      # Parse forenames
      batch_parsed <- current_batch %>%
        mutate(
          forename = map_chr(name, parse_forename),
          parsing_success = !is.na(forename)
        )

      parsed_names <- bind_rows(parsed_names, batch_parsed)

      # Progress reporting
      if (batch_num %% 10 == 0 || batch_num == num_batches) {
        success_rate <- round(sum(parsed_names$parsing_success) / nrow(parsed_names) * 100, 2)
        log_info(paste("Batch", batch_num, "/", num_batches,
                       "- Success rate:", success_rate, "%"))
      }

      # Garbage collection
      if (batch_num %% config$processing$gc_frequency == 0) {
        gc(verbose = FALSE)
      }
    }

    # =========================================================================
    # Filter to successfully parsed names
    # =========================================================================
    parsed_names <- parsed_names %>%
      filter(parsing_success) %>%
      select(author_id, forename, source)

    log_info(paste("Successfully parsed", nrow(parsed_names), "forenames"))

    # =========================================================================
    # Deduplicate: prioritize display_name over variants
    # =========================================================================
    log_info("Deduplicating names...")

    unique_names <- parsed_names %>%
      # Order by source priority (display_name before variant)
      arrange(author_id, source) %>%
      # Keep first occurrence (display_name if exists, else variant)
      distinct(author_id, forename, .keep_all = TRUE) %>%
      select(author_id, forename)

    log_info(paste("Unique author-forename combinations:", nrow(unique_names)))

    # =========================================================================
    # Join with country codes
    # =========================================================================
    if (!is.null(country_codes)) {
      log_info("Joining with country codes...")

      final_data <- unique_names %>%
        left_join(country_codes, by = "author_id")

      with_country <- sum(!is.na(final_data$country_code))
      without_country <- sum(is.na(final_data$country_code))

      log_info(paste("Authors with country code:", with_country))
      log_info(paste("Authors without country code:", without_country))

    } else {
      final_data <- unique_names %>%
        mutate(country_code = NA_character_)

      log_info("No country codes available")
    }

    # =========================================================================
    # Add metadata
    # =========================================================================
    final_data <- final_data %>%
      mutate(
        extraction_date = as.character(Sys.Date()),
        min_forename_length = config$name_parsing$min_forename_length
      ) %>%
      # Filter by minimum length
      filter(nchar(forename) >= min_forename_length)

    log_info(paste("Final dataset size:", nrow(final_data), "records"))

    # =========================================================================
    # Save to JSON
    # =========================================================================
    output_path <- config$paths$extracted_names

    # Ensure output directory exists
    ensure_dir(dirname(output_path))

    save_json(final_data, output_path)

    # =========================================================================
    # Generate summary statistics
    # =========================================================================
    log_info("\n=== EXTRACTION SUMMARY ===")
    log_info(paste("Total authors processed:", nrow(authors_df)))

    if (!is.null(variants_df)) {
      log_info(paste("Name variants processed:", nrow(variants_df)))
    }

    log_info(paste("Total names parsed:", nrow(parsed_names)))
    log_info(paste("Unique author-forename pairs:", nrow(unique_names)))
    log_info(paste("Final records (after filtering):", nrow(final_data)))

    if (!is.null(country_codes)) {
      coverage <- round(with_country / nrow(final_data) * 100, 2)
      log_info(paste("Country code coverage:", coverage, "%"))
    }

    # Forename length distribution
    length_dist <- final_data %>%
      mutate(length_category = cut(
        nchar(forename),
        breaks = c(0, 3, 5, 8, 15, Inf),
        labels = c("2-3", "4-5", "6-8", "9-15", "15+")
      )) %>%
      count(length_category)

    log_info("\nForename length distribution:")
    for (i in 1:nrow(length_dist)) {
      log_info(paste("  ", length_dist$length_category[i], "chars:",
                     length_dist$n[i], "names"))
    }

    # Top countries if available
    if (!is.null(country_codes) && with_country > 0) {
      top_countries <- final_data %>%
        filter(!is.na(country_code)) %>%
        count(country_code, sort = TRUE) %>%
        head(10)

      log_info("\nTop 10 countries:")
      for (i in 1:nrow(top_countries)) {
        log_info(paste("  ", top_countries$country_code[i], ":",
                       top_countries$n[i], "authors"))
      }
    }

    log_info(paste("\nOutput saved to:", output_path))
    log_info("=== STEP 1 COMPLETE ===\n")

    return(final_data)

  }, finally = {
    close_db_connection(con)
  })
}

# ==============================================================================
# SCRIPT EXECUTION (if run directly)
# ==============================================================================

if (!interactive()) {
  config <- load_config("config.yaml")
  init_logging(config)

  result <- extract_author_names(config)

  log_info("Name extraction completed successfully")
}
