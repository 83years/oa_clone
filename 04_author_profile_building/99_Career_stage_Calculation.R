# Load required libraries
library(DBI)
library(RSQLite)
library(dplyr)

# Connect to the database
db_path <- "/Users/lucas/Documents/R_projects/OpenAlex_aug2025/flow_cytometry_normalized.db"
conn <- dbConnect(SQLite(), db_path)

# Read current author data
authors_query <- "
SELECT 
    author_id,
    first_publication_year,
    last_publication_year
FROM authors 
WHERE first_publication_year IS NOT NULL 
    AND last_publication_year IS NOT NULL
"

authors_data <- dbGetQuery(conn, authors_query)

# Calculate career length and current status
authors_data <- authors_data %>%
  mutate(
    career_length_years = last_publication_year - first_publication_year + 1,
    is_current = case_when(
      last_publication_year >= 2024 ~ 1,  # Current (published in 2024 or later)
      TRUE ~ 0  # Not current
    ),
    career_stage_alt = case_when(
      career_length_years <= 3 ~ "Initial (1-3 yrs)",
      career_length_years <= 7 ~ "Developing (4-7 yrs)", 
      career_length_years <= 15 ~ "Established (8-15 yrs)",
      career_length_years <= 25 ~ "Senior (16-25 yrs)",
      career_length_years > 25 ~ "Veteran (25+ yrs)",
      TRUE ~ NA_character_
    )
  )

# Print summary of calculations
cat("=== Career Length and Current Status Summary ===\n")
cat("Authors processed:", nrow(authors_data), "\n")
cat("Current authors (last pub >= 2024):", sum(authors_data$is_current), "\n")
cat("Career length range:", min(authors_data$career_length_years), "to", max(authors_data$career_length_years), "years\n")

# Print career stage distribution
cat("\n=== Career Stage Distribution ===\n")
stage_counts <- table(authors_data$career_stage_alt)
for(i in 1:length(stage_counts)) {
  cat(names(stage_counts)[i], ":", stage_counts[i], "\n")
}

# Add new columns to authors table if they don't exist
tryCatch({
  dbExecute(conn, "ALTER TABLE authors ADD COLUMN career_length_years INTEGER")
  cat("Added career_length_years column\n")
}, error = function(e) {
  cat("career_length_years column already exists or error:", e$message, "\n")
})

tryCatch({
  dbExecute(conn, "ALTER TABLE authors ADD COLUMN is_current INTEGER")
  cat("Added is_current column\n")
}, error = function(e) {
  cat("is_current column already exists or error:", e$message, "\n")
})

tryCatch({
  dbExecute(conn, "ALTER TABLE authors ADD COLUMN career_stage_alt TEXT")
  cat("Added career_stage_alt column\n")
}, error = function(e) {
  cat("career_stage_alt column already exists or error:", e$message, "\n")
})

# Update the authors table with calculated values
cat("\n=== Updating database ===\n")
update_count <- 0

for(i in 1:nrow(authors_data)) {
  update_query <- sprintf("
    UPDATE authors 
    SET career_length_years = %d,
        is_current = %d,
        career_stage_alt = '%s'
    WHERE author_id = '%s'
  ", 
                          authors_data$career_length_years[i],
                          authors_data$is_current[i], 
                          authors_data$career_stage_alt[i],
                          authors_data$author_id[i]
  )
  
  dbExecute(conn, update_query)
  update_count <- update_count + 1
  
  # Progress indicator
  if(update_count %% 100000 == 0) {
    cat("Updated", update_count, "authors...\n")
  }
}

cat("Successfully updated", update_count, "authors\n")

# Verify the updates
verification_query <- "
SELECT 
    COUNT(*) as total_authors,
    COUNT(career_length_years) as with_career_length,
    COUNT(is_current) as with_current_status,
    COUNT(career_stage_alt) as with_career_stage,
    SUM(is_current) as current_authors
FROM authors
"

verification <- dbGetQuery(conn, verification_query)
cat("\n=== Verification ===\n")
print(verification)

# Show sample of updated data
sample_query <- "
SELECT 
    author_id, 
    display_name,
    first_publication_year, 
    last_publication_year, 
    career_length_years,
    is_current,
    career_stage_alt
FROM authors 
WHERE career_length_years IS NOT NULL
ORDER BY career_length_years DESC
LIMIT 10
"

sample_data <- dbGetQuery(conn, sample_query)
cat("\n=== Sample of Updated Data (Longest Careers) ===\n")
print(sample_data)

# Disconnect from database
dbDisconnect(conn)
cat("\nDatabase connection closed.\n")
