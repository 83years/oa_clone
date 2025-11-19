# OpenAlex Database Clone Project

A comprehensive data pipeline for building and analyzing a local copy of the OpenAlex academic database, with focus on author career trajectories, gender analysis, and network science.

## Project Status (November 2025)

### Completed Phases
- ✅ **Phase 01:** OpenAlex snapshot download (277M works, 102M authors)
- ✅ **Phase 02:** PostgreSQL database setup on NAS (OADB: 1012 GB)
- ✅ **Phase 03:** Data parsing and loading into PostgreSQL

### Current Work
- 🔄 **Phase 03 (Constraint Building):**
  - Testing database: OADB_test (1013 GB copy)
  - Currently running: Primary key creation (~7 hours)
  - Next: Indexes → Foreign keys → Validation
  - See: `03_snapshot_parsing/constraint_building/README.md`

### Planned Phases
- ⏸️ **Phase 04:** Author profile building (102M authors)
  - Career trajectory clustering (DTW + ML hybrid approach)
  - Scripts ready, awaiting constraint completion
  - See: `04_author_profile_building/test/README.md`
- ⏸️ **Phase 05-09:** Network analysis (co-authorship, institution networks)
- ⏸️ **Phase 10-11:** Hypothesis testing (gender, geography)
- ⏸️ **Phase 12:** Key opinion leader identification

## Database Overview

**Production Database:** `OADB` (1012 GB)
- 277M works
- 102M authors
- 1.1B authorship records
- 2.3B work-concept relationships

**Test Database:** `OADB_test` (1013 GB)
- Full copy for safe testing
- Currently undergoing constraint building

## Key Directories

- `01_oa_snapshot/` - Download scripts for OpenAlex snapshot
- `02_postgres_setup/` - Database schema creation
- `03_snapshot_parsing/` - Data parsing and constraint building
- `04_author_profile_building/` - Career analysis and clustering
- `05_db_query/` - Query tools
- `06-09_network_*/` - Network construction and analysis
- `10-12_*/` - Hypothesis testing and KOL identification

## Quick Links

- [Constraint Building Status](03_snapshot_parsing/constraint_building/README.md)
- [Career Trajectory Analysis](04_author_profile_building/test/README.md)
- [Project Guidelines](CLAUDE.md)

## Contact

Lucas Black (s.lucasblack@gmail.com) 
