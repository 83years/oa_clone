# OpenAlex Database Clone Project

A comprehensive data pipeline for building and analyzing a local copy of the OpenAlex academic database, with focus on author career trajectories, gender analysis, and network science.

## Project Status (November 2025)

### Completed Phases
- ✅ **Phase 01:** OpenAlex snapshot download (277M works, 102M authors)
- ✅ **Phase 02:** PostgreSQL database setup on NAS (Rebuilt after RAID failure)
- 🔄 **Phase 03:** Data parsing and loading into PostgreSQL

### Current Work
- 🔄 **Phase 02-03 Rebuild:**
  - New database: OADBv5 (rebuilt November 2025 after hardware failure)
  - Docker-based PostgreSQL 16 on UGREEN NAS
  - Database schema created (32 tables, constraint-free for bulk loading)
  - Ready for data parsing from OpenAlex snapshot
  - See: `02_postgres_setup/oadb2_postgresql_setup.py`

### Planned Phases
- ⏸️ **Phase 04:** Author profile building (102M authors)
  - Career trajectory clustering (DTW + ML hybrid approach)
  - Scripts ready, awaiting constraint completion
  - See: `04_author_profile_building/test/README.md`
- ⏸️ **Phase 05-09:** Network analysis (co-authorship, institution networks)
- ⏸️ **Phase 10-11:** Hypothesis testing (gender, geography)
- ⏸️ **Phase 12:** Key opinion leader identification

## Database Overview

**Current Database:** `OADBv5`
- Host: 192.168.1.100:55432
- PostgreSQL 16 (Docker container on UGREEN NAS)
- Admin user: admin
- Database: oadbv5
- Status: Empty schema created, ready for data loading
- 32 tables created (constraint-free for bulk loading)
- Data persistence: /volume1/postgresql_data
- SMB access: /Volumes/postgresql_data

**OpenAlex Snapshot Source:**
- Location: /Volumes/OA_snapshot/24OCT2025/data/
- Snapshot Date: October 24, 2025
- Format: Gzipped JSON files in dated subdirectories
- Ready for parsing via orchestrator

**Target Data Scale:**
- 277M works
- 102M authors
- 1.1B authorship records
- 2.3B work-concept relationships

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
