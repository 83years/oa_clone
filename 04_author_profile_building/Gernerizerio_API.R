# Load required libraries
library(tidyverse)
library(gender)

# Define helper operator for handling NULL values
`%||%` <- function(x, y) if(is.null(x)) y else x

# API Keys
genderize_api_key <- "7dba1eabce863d4d58a81f512862e4d9"

# Cache file path
cache_file <- "/Users/lucas/Library/CloudStorage/OneDrive-CytoLogicSolutions/Documents/R_Projects/clin_flow_lit/genderize_cache.rds"

# Read the RDS file
file_path <- "/Users/lucas/Library/CloudStorage/OneDrive-CytoLogicSolutions/Documents/R_Projects/clin_flow_lit/CompSci/CompSci_unique_authors_no_gender.rds"
unique_authors <- readRDS(file_path)

# Function to safely apply gender prediction with error handling
safe_gender_predict <- function(names_vector, method = "ssa") {
  
  # Remove NA and empty names
  clean_names <- names_vector[!is.na(names_vector) & names_vector != ""]
  
  if(length(clean_names) == 0) {
    return(data.frame(
      name = character(0),
      gender = character(0),
      proportion_male = numeric(0),
      proportion_female = numeric(0)
    ))
  }
  
  # Try gender prediction with error handling
  tryCatch({
    # Use SSA method (most recent and comprehensive for US names)
    gender_results <- gender(clean_names, method = method)
    return(gender_results)
  }, error = function(e) {
    warning(paste("Gender prediction failed:", e$message))
    # Return empty result with correct structure
    return(data.frame(
      name = clean_names,
      gender = rep(NA, length(clean_names)),
      proportion_male = rep(NA, length(clean_names)),
      proportion_female = rep(NA, length(clean_names))
    ))
  })
}

# Prepare data for gender prediction
cat("Preparing data for gender analysis...\n")
cat("Total authors:", nrow(unique_authors), "\n")

# Load existing genderize.io cache if it exists
if(file.exists(cache_file)) {
  cat("Loading existing genderize.io cache...\n")
  genderize_cache <- readRDS(cache_file)
  cat("Cache contains", nrow(genderize_cache), "names\n")
} else {
  cat("No existing cache found, will create new one\n")
  genderize_cache <- data.frame(
    name = character(0),
    genderize_gender = character(0),
    genderize_probability = numeric(0),
    genderize_count = numeric(0),
    stringsAsFactors = FALSE
  )
}

# Filter for names with 3+ characters and get unique first names
all_valid_names <- unique_authors %>%
  filter(!is.na(fore_name) & 
           fore_name != "" & 
           nchar(fore_name) >= 3) %>%
  distinct(fore_name) %>%
  pull(fore_name)

# Check which names are already in cache
cached_names <- intersect(all_valid_names, genderize_cache$name)
uncached_names <- setdiff(all_valid_names, genderize_cache$name)

cat("Authors with names ≥3 characters:", 
    nrow(unique_authors %>% filter(!is.na(fore_name) & nchar(fore_name) >= 3)), "\n")
cat("Names already in cache:", length(cached_names), "\n")
cat("Names needing prediction:", length(uncached_names), "\n")

# Use uncached names for gender prediction pipeline
unique_names <- uncached_names

cat("Unique first names to analyze:", length(unique_names), "\n")

# Predict genders for unique names
cat("Running gender prediction...\n")
gender_results <- safe_gender_predict(unique_names, method = "ssa")

# If SSA method fails or returns limited results, try IPUMS method
if(nrow(gender_results) < length(unique_names) * 0.5) {
  cat("SSA method had limited coverage, trying IPUMS method...\n")
  gender_results_ipums <- safe_gender_predict(unique_names, method = "ipums")
  
  # Combine results, preferring SSA where available
  if(nrow(gender_results_ipums) > nrow(gender_results)) {
    gender_results <- gender_results_ipums
    cat("Using IPUMS method results\n")
  }
}

# Create lookup table for gender results
gender_lookup <- gender_results %>%
  select(name, gender, proportion_male, proportion_female) %>%
  # Calculate confidence score (higher proportion of predicted gender)
  mutate(
    gender_confidence = case_when(
      gender == "male" ~ proportion_male,
      gender == "female" ~ proportion_female,
      TRUE ~ NA_real_
    )
  )

# Combine cache results with new gender R results
all_gender_results <- genderize_cache %>%
  select(name, gender = genderize_gender, 
         proportion_male = genderize_probability, proportion_female = genderize_probability) %>%
  mutate(
    # For cached results, set proportions based on gender
    proportion_male = ifelse(gender == "male", proportion_male, 1 - proportion_male),
    proportion_female = ifelse(gender == "female", proportion_female, 1 - proportion_female),
    gender_confidence = pmax(proportion_male, proportion_female, na.rm = TRUE),
    source = "cache"
  ) %>%
  bind_rows(
    gender_lookup %>% mutate(source = "gender_r")
  )

# Join back to original dataset
authors_with_gender <- unique_authors %>%
  left_join(all_gender_results, by = c("fore_name" = "name")) %>%
  # Clean up column names and add analysis metadata
  rename(
    original_gender = gender.x,           # The original NA column
    predicted_gender = gender.y,         # The new predictions
    gender_confidence_score = gender_confidence
  ) %>%
  # Add analysis timestamp and method info
  mutate(
    gender_analysis_date = Sys.Date(),
    gender_method = case_when(
      source == "cache" ~ "genderize_cache",
      source == "gender_r" ~ "gender_r_package",
      TRUE ~ "unknown"
    ),
    gender_dataset = "ssa_ipums_cache"
  ) %>%
  select(-source)  # Remove temporary source column

# Create summary statistics
summary_stats <- authors_with_gender %>%
  summarise(
    total_authors = n(),
    authors_with_valid_names = sum(!is.na(fore_name) & nchar(fore_name) >= 3),
    names_with_predictions = sum(!is.na(predicted_gender)),
    coverage_rate_all = round(names_with_predictions / total_authors * 100, 2),
    coverage_rate_valid_names = round(names_with_predictions / authors_with_valid_names * 100, 2),
    predicted_male = sum(predicted_gender == "male", na.rm = TRUE),
    predicted_female = sum(predicted_gender == "female", na.rm = TRUE),
    high_confidence_predictions = sum(gender_confidence_score >= 0.8, na.rm = TRUE),
    .groups = "drop"
  )

# Print summary
cat("\n=== GENDER PREDICTION SUMMARY ===\n")
cat("Total authors:", summary_stats$total_authors, "\n")
cat("Authors with valid names (≥3 chars):", summary_stats$authors_with_valid_names, "\n")
cat("Successfully predicted:", summary_stats$names_with_predictions, "\n")
cat("Coverage rate (all authors):", summary_stats$coverage_rate_all, "%\n")
cat("Coverage rate (valid names only):", summary_stats$coverage_rate_valid_names, "%\n")
cat("Predicted male:", summary_stats$predicted_male, "\n")
cat("Predicted female:", summary_stats$predicted_female, "\n")
cat("High confidence (≥80%):", summary_stats$high_confidence_predictions, "\n")

# Show breakdown by country (focusing on Asian vs Western names)
country_breakdown <- authors_with_gender %>%
  filter(!is.na(fore_name) & nchar(fore_name) >= 3) %>%  # Only analyze valid names
  mutate(
    region = case_when(
      country_name %in% c("China", "Japan", "South Korea", "Singapore", 
                          "Taiwan", "Hong Kong", "India", "Thailand", 
                          "Malaysia", "Indonesia", "Philippines") ~ "Asia",
      country_name %in% c("United States", "United Kingdom", "Canada", 
                          "Australia", "Germany", "France", "Netherlands", 
                          "Sweden", "Norway", "Denmark") ~ "Western",
      TRUE ~ "Other"
    )
  ) %>%
  group_by(region) %>%
  summarise(
    total = n(),
    predicted = sum(!is.na(predicted_gender)),
    coverage_rate = round(predicted / total * 100, 2),
    .groups = "drop"
  )

# Identify unmatched names for gender-guesser
unmatched_names <- authors_with_gender %>%
  filter(!is.na(fore_name) & 
           nchar(fore_name) >= 3 & 
           is.na(predicted_gender)) %>%
  distinct(fore_name) %>%
  pull(fore_name)

cat("Names unmatched by gender R package:", length(unmatched_names), "\n")

# Function to use gender-guesser package via reticulate
use_gender_guesser <- function(names_vector) {
  
  if(length(names_vector) == 0) {
    return(data.frame(
      name = character(0),
      gender_guesser_result = character(0),
      gender_guesser_clean = character(0)
    ))
  }
  
  # Load reticulate for Python integration
  if (!require(reticulate, quietly = TRUE)) {
    cat("Installing reticulate package...\n")
    install.packages("reticulate")
    library(reticulate)
  }
  
  tryCatch({
    # Try to import gender_guesser
    gender_guesser <- import("gender_guesser.detector")
    detector <- gender_guesser$Detector()
    
    # Apply gender_guesser to each name
    results <- sapply(names_vector, function(name) {
      detector$get_gender(name)
    })
    
    # Clean results (convert to standard male/female/unknown)
    clean_results <- case_when(
      results %in% c("male", "mostly_male") ~ "male",
      results %in% c("female", "mostly_female") ~ "female",
      TRUE ~ "unknown"
    )
    
    return(data.frame(
      name = names_vector,
      gender_guesser_result = results,
      gender_guesser_clean = clean_results,
      stringsAsFactors = FALSE
    ))
    
  }, error = function(e) {
    cat("Gender-guesser not available. Error:", e$message, "\n")
    cat("To install: pip install gender-guesser\n")
    
    # Return empty results
    return(data.frame(
      name = names_vector,
      gender_guesser_result = rep(NA, length(names_vector)),
      gender_guesser_clean = rep(NA, length(names_vector)),
      stringsAsFactors = FALSE
    ))
  })
}

# Run gender-guesser on unmatched names
if(length(unmatched_names) > 0) {
  cat("Running gender-guesser on unmatched names...\n")
  guesser_results <- use_gender_guesser(unmatched_names)
  
  # Merge with main dataset
  authors_step2 <- authors_with_gender %>%
    left_join(guesser_results, by = c("fore_name" = "name"))
  
} else {
  cat("All names were matched by gender R package - skipping gender-guesser\n")
  authors_step2 <- authors_with_gender %>%
    mutate(
      gender_guesser_result = NA_character_,
      gender_guesser_clean = NA_character_
    )
}

# Function to use genderize.io API
use_genderize_api <- function(names_vector, api_key, max_names = 1000) {
  
  if(length(names_vector) == 0) {
    return(data.frame(
      name = character(0),
      genderize_gender = character(0),
      genderize_probability = numeric(0),
      genderize_count = numeric(0)
    ))
  }
  
  # Load required packages
  if (!require(httr, quietly = TRUE)) {
    cat("Installing httr package...\n")
    install.packages("httr")
    library(httr)
  }
  
  if (!require(jsonlite, quietly = TRUE)) {
    cat("Installing jsonlite package...\n")
    install.packages("jsonlite")
    library(jsonlite)
  }
  
  # Limit the number of names to avoid excessive API costs
  if(length(names_vector) > max_names) {
    cat("WARNING: Limiting to first", max_names, "names to avoid excessive API costs\n")
    cat("Total unmatched names:", length(names_vector), "\n")
    names_vector <- names_vector[1:max_names]
  }
  
  # Clean names: remove special characters and ensure they're valid
  clean_names <- names_vector[!is.na(names_vector) & 
                                names_vector != "" & 
                                nchar(names_vector) >= 2]
  
  # Remove names with numbers or special characters that might cause URL issues
  clean_names <- clean_names[grepl("^[A-Za-z\\.' -]+$", clean_names)]
  
  if(length(clean_names) == 0) {
    return(data.frame(
      name = character(0),
      genderize_gender = character(0),
      genderize_probability = numeric(0),
      genderize_count = numeric(0)
    ))
  }
  
  # Initialize results dataframe
  all_results <- data.frame(
    name = character(0),
    genderize_gender = character(0),
    genderize_probability = numeric(0),
    genderize_count = numeric(0)
  )
  
  # Process one name at a time to avoid URL encoding issues
  cat("Processing", length(clean_names), "clean names via genderize.io...\n")
  
  for(i in seq_along(clean_names)) {
    name <- clean_names[i]
    
    tryCatch({
      # URL encode the name properly
      encoded_name <- URLencode(name, reserved = TRUE)
      
      # Build query URL for single name
      url <- paste0("https://api.genderize.io/?name=", encoded_name, "&apikey=", api_key)
      
      # Make API call
      response <- GET(url)
      
      if(status_code(response) == 200) {
        content_data <- content(response, "text", encoding = "UTF-8")
        parsed_data <- fromJSON(content_data)
        
        # Create result row
        result_row <- data.frame(
          name = name,
          genderize_gender = parsed_data$gender %||% NA,
          genderize_probability = parsed_data$probability %||% NA,
          genderize_count = parsed_data$count %||% NA,
          stringsAsFactors = FALSE
        )
        
        all_results <- rbind(all_results, result_row)
        
      } else if(status_code(response) == 402) {
        cat("API quota exceeded or payment required. Stopping at name", i, "\n")
        break
      } else {
        cat("API call failed for name", i, "(", name, ") - Status:", status_code(response), "\n")
        # Add empty result for this name
        result_row <- data.frame(
          name = name,
          genderize_gender = NA,
          genderize_probability = NA,
          genderize_count = NA,
          stringsAsFactors = FALSE
        )
        all_results <- rbind(all_results, result_row)
      }
      
      # Progress indicator
      if(i %% 100 == 0) {
        cat("Processed", i, "of", length(clean_names), "names\n")
      }
      
      # Small delay to be respectful to API
      Sys.sleep(0.05)
      
    }, error = function(e) {
      cat("Error processing name", i, "(", name, "):", e$message, "\n")
      # Add empty result for this name
      result_row <- data.frame(
        name = name,
        genderize_gender = NA,
        genderize_probability = NA,
        genderize_count = NA,
        stringsAsFactors = FALSE
      )
      all_results <<- rbind(all_results, result_row)
    })
  }
  
  cat("Genderize.io completed:", nrow(all_results), "results\n")
  return(all_results)
}

# Identify names still unmatched after first two methods
still_unmatched <- authors_step2 %>%
  filter(!is.na(fore_name) & 
           nchar(fore_name) >= 3 & 
           is.na(predicted_gender) & 
           (is.na(gender_guesser_clean) | gender_guesser_clean == "unknown")) %>%
  distinct(fore_name) %>%
  pull(fore_name)

cat("Names still unmatched after gender R + gender-guesser:", length(still_unmatched), "\n")

# Run genderize.io on remaining unmatched names
if(length(still_unmatched) > 0) {
  cat("Running genderize.io API on remaining unmatched names...\n")
  # Limit to 1000 names to control API costs - adjust max_names as needed
  genderize_results <- use_genderize_api(still_unmatched, genderize_api_key, max_names = 500000)
  
  # Update cache with new results
  if(nrow(genderize_results) > 0) {
    cat("Updating cache with", nrow(genderize_results), "new results...\n")
    
    # Combine new results with existing cache
    updated_cache <- genderize_cache %>%
      bind_rows(genderize_results) %>%
      distinct(name, .keep_all = TRUE)  # Remove duplicates, keeping first occurrence
    
    # Save updated cache
    saveRDS(updated_cache, cache_file)
    cat("Cache updated and saved\n")
    
    # Update the global cache variable for this session
    genderize_cache <- updated_cache
  }
  
  # Merge with main dataset
  authors_final <- authors_step2 %>%
    left_join(genderize_results, by = c("fore_name" = "name"))
  
} else {
  cat("No names remaining for genderize.io\n")
  authors_final <- authors_step2 %>%
    mutate(
      genderize_gender = NA_character_,
      genderize_probability = NA_real_,
      genderize_count = NA_real_
    )
}

# Create final combined gender prediction
authors_final <- authors_final %>%
  mutate(
    # Create combined gender prediction with priority order
    final_gender = case_when(
      gender_method == "genderize_cache" ~ predicted_gender,             # 1st: Cache (highest priority)
      !is.na(predicted_gender) & gender_method != "genderize_cache" ~ predicted_gender,  # 2nd: gender R
      gender_guesser_clean == "male" ~ "male",                          # 3rd: gender-guesser
      gender_guesser_clean == "female" ~ "female",
      genderize_gender == "male" ~ "male",                              # 4th: new genderize.io
      genderize_gender == "female" ~ "female",
      TRUE ~ NA_character_
    ),
    # Track which method was used (update to include cache)
    prediction_method = case_when(
      gender_method == "genderize_cache" ~ "genderize_cache",
      !is.na(predicted_gender) & gender_method != "genderize_cache" ~ "gender_r",
      !is.na(gender_guesser_clean) & gender_guesser_clean != "unknown" ~ "gender_guesser",
      !is.na(genderize_gender) ~ "genderize_io",
      TRUE ~ "none"
    ),
    # Add confidence score (use genderize probability when available)
    final_confidence = case_when(
      !is.na(gender_confidence_score) ~ gender_confidence_score,
      !is.na(genderize_probability) ~ genderize_probability,
      prediction_method == "gender_guesser" ~ 0.75,  # Estimated confidence
      TRUE ~ NA_real_
    )
  )

# Final comprehensive summary statistics
final_summary <- authors_final %>%
  filter(!is.na(fore_name) & nchar(fore_name) >= 3) %>%
  summarise(
    valid_names = n(),
    total_predictions = sum(!is.na(final_gender)),
    from_cache = sum(prediction_method == "genderize_cache"),
    from_gender_r = sum(prediction_method == "gender_r"),
    from_gender_guesser = sum(prediction_method == "gender_guesser"),
    from_genderize = sum(prediction_method == "genderize_io"),
    final_coverage = round(total_predictions / valid_names * 100, 2),
    final_male = sum(final_gender == "male", na.rm = TRUE),
    final_female = sum(final_gender == "female", na.rm = TRUE),
    high_confidence = sum(final_confidence >= 0.8, na.rm = TRUE)
  )

cat("\n=== FINAL COMBINED RESULTS SUMMARY ===\n")
cat("Valid names (≥3 chars):", final_summary$valid_names, "\n")
cat("Total predictions:", final_summary$total_predictions, "\n")
cat("From cache:", final_summary$from_cache, "\n")
cat("From gender R:", final_summary$from_gender_r, "\n")
cat("From gender-guesser:", final_summary$from_gender_guesser, "\n")
cat("From genderize.io (new):", final_summary$from_genderize, "\n")
cat("Final coverage rate:", final_summary$final_coverage, "%\n")
cat("Predicted male:", final_summary$final_male, "\n")
cat("Predicted female:", final_summary$final_female, "\n")
cat("High confidence (≥80%):", final_summary$high_confidence, "\n")

# Save final results
output_path <- "/Users/lucas/Library/CloudStorage/OneDrive-CytoLogicSolutions/Documents/R_Projects/clin_flow_lit/unique_authors_with_gender_combined.rds"
saveRDS(authors_final, output_path)
cat("\nFinal results saved to:", output_path, "\n")

library(DBI)
library(RSQLite)
library(dplyr)

# Step 1: Change male/female to M/F in the final_gender column
authors_final <- authors_final %>%
  mutate(final_gender = case_when(
    final_gender == "male" ~ "M",
    final_gender == "female" ~ "F",
    TRUE ~ final_gender  # Keep NA or other values as-is
  ))

# Step 2: Connect to database and update the authors table
DB_PATH <- "CompSci_1990_2024.sqlite"

# Connect to the database
con <- dbConnect(RSQLite::SQLite(), DB_PATH)

# Step 3: Check if gender column exists and create it if it doesn't
# Get the current table structure
table_info <- dbGetQuery(con, "PRAGMA table_info(authors)")
existing_columns <- table_info$name

cat("Current columns in authors table:", paste(existing_columns, collapse = ", "), "\n")

# Check if gender column exists
if (!"gender" %in% existing_columns) {
  cat("Gender column not found. Adding gender column to authors table...\n")
  
  # Add the gender column as TEXT type (can store M, F, or NULL)
  dbExecute(con, "ALTER TABLE authors ADD COLUMN gender TEXT")
  
  cat("Gender column successfully added to authors table.\n")
} else {
  cat("Gender column already exists in authors table.\n")
}

# Step 4: Filter to only rows where we have a gender prediction (not NA)
gender_updates <- authors_final %>%
  filter(!is.na(final_gender)) %>%
  select(unique_author_id, final_gender)

# Step 5: Update the database in batches for better performance
batch_size <- 1000
total_rows <- nrow(gender_updates)

cat("Updating", total_rows, "authors with gender information...\n")

for (i in seq(1, total_rows, batch_size)) {
  end_idx <- min(i + batch_size - 1, total_rows)
  batch_data <- gender_updates[i:end_idx, ]
  
  # Create temporary table for this batch
  dbWriteTable(con, "temp_gender_updates", batch_data, overwrite = TRUE)
  
  # Update authors table using JOIN
  dbExecute(con, "
    UPDATE authors 
    SET gender = temp_gender_updates.final_gender
    FROM temp_gender_updates 
    WHERE authors.unique_author_id = temp_gender_updates.unique_author_id
  ")
  
  cat("Updated batch", ceiling(i/batch_size), "of", ceiling(total_rows/batch_size), "\n")
}

# Step 6: Clean up temporary table
dbExecute(con, "DROP TABLE IF EXISTS temp_gender_updates")

# Step 7: Verify the updates
updated_count <- dbGetQuery(con, "
  SELECT COUNT(*) as count 
  FROM authors 
  WHERE gender IN ('M', 'F')
")

# Also get a breakdown of the gender distribution
gender_distribution <- dbGetQuery(con, "
  SELECT 
    gender,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM authors), 2) as percentage
  FROM authors 
  GROUP BY gender
  ORDER BY count DESC
")

cat("\n=== UPDATE RESULTS ===\n")
cat("Total authors with gender assigned:", updated_count$count, "\n")
cat("\nGender distribution:\n")
print(gender_distribution)

# Step 8: Close the database connection
dbDisconnect(con)

cat("\nGender update complete!\n")