# Project: OA_clone

## Overview
[Brief description]

## Coding standards
- Language: Python (primary), R (secondary)
- Style: 
# Code Style

## General Principles
- Keep code simple and efficient
- Modular approach: build small, testable components that work independently and together
- Write for iterative development with frequent testing

## Naming Conventions
- Follow standard Python conventions:
  - Functions and variables: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_CASE`
- Python files: numbered prefix format `01_process_data.py`, `02_analysis.py`

## Project Structure
- Organise work into phase folders: `01_data_prep/`, `02_analysis/`, `03_visualisation/`
- Each phase contains modular scripts orchestrated by a main script
- Keep related functionality in separate, importable modules

## Imports
- Standard library imports first
- Custom/local scripts second
- One blank line between groups

## Documentation & Comments
- **During development**: Use extensive inline comments to explain logic
- **For publication**: Remove inline comments, add comprehensive docstrings to all functions/classes
- Code should be self-documenting through clear naming

## Error Handling
- Implement graceful error handling - catch exceptions and provide informative messages
- Don't let the programme crash silently; always indicate what went wrong
- For data processing: validate inputs and handle missing/malformed data appropriately

## Logging
**CRITICAL**: All scripts MUST implement proper logging. Never allow days to pass without knowing what a script is doing.

### Required Logging Standards:
- **Always log to both console AND file** - dual output ensures visibility
- **Use Python's logging module** with proper configuration
- **Include timestamps** in all log messages (format: `[YYYY-MM-DD HH:MM:SS]`)
- **Store log files** in a dedicated `logs/` directory within each phase folder
- **Name log files** with timestamps: `{script_name}_{YYYYMMDD_HHMMSS}.log`

### Progress Logging for Long-Running Operations:
- Log progress at regular intervals (e.g., every 100k records, every 5 minutes)
- Include completion percentage when total is known
- Log current state, records processed, and estimated time remaining
- For batch operations, log: batch number, records in batch, total processed, time elapsed
- Always log when starting and completing major phases

### Log Levels:
- **INFO**: Normal progress updates, milestones, summaries
- **WARNING**: Non-fatal issues, degraded performance, missing optional data
- **ERROR**: Failures that don't stop execution, recoverable errors
- **CRITICAL**: Fatal errors that stop execution

### Example Logging Setup:
```python
import logging
from datetime import datetime
from pathlib import Path

# Create logs directory
log_dir = Path(__file__).parent / 'logs'
log_dir.mkdir(exist_ok=True)

# Setup logging to both file and console
log_file = log_dir / f'{Path(__file__).stem}_{datetime.now():%Y%m%d_%H%M%S}.log'

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()  # Console output
    ]
)

logger = logging.getLogger(__name__)
logger.info(f"Starting {Path(__file__).name}")
logger.info(f"Log file: {log_file}")
```

## File structure
01_oa_snapshot:
- Code that deals with the downloading of the OpenAlex snapshot files and how they are stored locally

02_postgres_setup: 
- Code that builds an empty PostgeSQL database on a local NAS server
- This code will need to replicate the OpenAlex database schema closely 

03_snapshot_parsing:
- Code that parses the different types of OA json files into the PostgreSQL database
- Each data type will need to be read into its own table and connecting tables 
- For all but the works table foreign keys need to be respected
- For the works table and joining tables the foreign keys should be temporally turned off and COPY used to bulk add data. Once the data is in the table foreign keys can be built. 
- Missing data will need to be collected using the OA API using the email: s.lucasblack@gmail.com

04_author_profile_building: 
- Code to build as complete an author profile as possible for each author in the authors table
- Author profile features derived from the OA will include:
*author_id - a unique author identification given by the OA data
*orcid - a unique author identifier given grom the ORCID database 
*display_name - the name of the author. Used to infer the author gender 
*works_count - the total number of works for an author
*cited_by_count - the total number of citations for an author
*last_known_institution - the last known institution that he author published from
*updated_date - the date that the data was updated 
*current_affiliation_id - the unique institution identifier from the OA database of the institution the author last published from 
*current_affiliation_name - the name of the institution the author last published from 
*current_affiliation_country - the country of the institution. Sometimes used to help refine gender inference 
*current_affiliation_type - The type of institution the author is at 
*gender - the inferred gender of the author based on their forename and country 
*most_cited_work - the unique work ID of the authors most cited work 
*max_citations - the maximum cited any single work an author has 
*first_publication_year - the modeled first year an author published. Multiple models will be applied and tested to determine the career stage of authors. 
*last_publication_year - the last year an author published 
*career_length_years - the difference between fir modeled first year and last year 
*career_stage - the modeled career stage of an author
*is_current - booleon if the author published within the last 3 years 
*corrisponding_authorships - the number of times an author has a corrisponding authorship 
*freq_corresponding - the number of times an author is corrsponding divided by their total number of papers 
*freq_first_author - the frequency an uthor is first 
*freq_last_author - the frequency the author is last
*primary_topic - the topic on which the author published most 
*primary_concept - the concept on which the author publishes most 

05_db_query:
- code to handle database queries based on work titles, abstracts, keywords and MeSH terms 
- filtering and refining works lists 

06_network_building:
- code to build a co-author, author-institution and/or co-institution network 

07_network_analysis:
- analysis of the network measuring: 
degree centrality 
pagerank
eigenvector centrality 
cluster coefficient 
katz centrality 
closeness centrality - if the network is <300k nodes
betweenness centrality - if the network is <500k nodes 

08_ERGM_analysis:
- code to test how far the network is from a random network of the same size and number of nodes/edges 
- code to test how far away the network is from a random network with multiple features that match 
- robust statistical analysis comparing real and random networks 

09_subnetwork_analysis:
- code to build and measure the network properties for:
*author ego networks
*time constrained networks 
*location constrained networks 

10_gender_hypothesis_testing:
- code testing hypotheses on how gender impacts author career stages measures of success 
- this is the main focus of the project

11_geography_hypothesis_testing:
- code testing hypotheses on how authors in different countries can experience different measures of success 
- this is a secondary focus of the project 

12_key_opinion_leaders:
- code to identify current and previous KOLs
- code to model the careers of previous KOLs
- code to identify potential new KOLs based on similarity to known KOLs at a similar career stage 

99_visualisations:
- code for themes, colours and general visualizations 













