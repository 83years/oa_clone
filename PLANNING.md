# OpenAlex Clinical Flow Cytometry Gender Analysis Project
## Comprehensive Planning Document

**Project Title**: Analysis of Gender Roles Within a Clinical Flow Cytometry Co-Author Network
**Last Updated**: 2025-10-28
**Status**: Phase 3 (Data Pipeline) in progress → Moving to completion and validation

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Current State Assessment](#current-state-assessment)
3. [Project Architecture](#project-architecture)
4. [Phase-by-Phase Strategy](#phase-by-phase-strategy)
5. [Computational Strategy](#computational-strategy)
6. [Reproducibility Framework](#reproducibility-framework)
7. [Documentation Standards](#documentation-standards)
8. [Risk Register](#risk-register)
9. [Publication Roadmap](#publication-roadmap)
10. [Decision Log](#decision-log)

---

## 1. Executive Summary

### Project Vision
Systematically investigate gender disparities in clinical flow cytometry research through comprehensive network analysis of ~292,000 works and ~2 million author profiles from the OpenAlex database. Test whether women occupy less central network positions, have smaller collaborative networks, and are underrepresented at highly connected institutions.

### Core Research Question
**Do gender disparities exist within the ckinical cytometry research collaboration network, with women systematically occupying less central network positions, having smaller collaborative networks, and being underrepresented at highly connected institutions? If disparities exist, do they show associations with time and career stage?**

### Primary Hypotheses (6 major hypothesis families)
- **H1**: Gender disparities in network centrality (degree, closeness, eigenvector, pagerank, betweenness etc.)
- **H2**: Institutional gender stratification
- **H3**: Author typology and gender disparities across academic role types
- **H4**: Temporal trends in gender equity (extended historical analysis)
- **H5**: Career trajectory gender differences
- **H6**: Collaborative pattern gender differences

### Project Scope
- **Corpus**: ~292,000 works in clinical flow cytometry (multi-method identification)
- **Authors**: ~2 million total authors, ~306,000 with >1 publication
- **Time Range**: Data-driven (query back until quality degrades, likely 1980s-2024)
- **Network Scale**: Three network types (co-author, author-institution, co-institution)
- **Analysis Approach**: Network-first, H1 as foundation, build out systematically

### Success Criteria
1. Complete, validated local OpenAlex database clone (>95% accuracy vs. API)
2. Comprehensive author profiles with gender inference (validated on sample)
3. Multiple network types constructed and analyzed
4. Systematic testing of all 6 hypothesis families with robust statistics
5. Publication-grade reproducibility (documented methods, versioned data, seeded analyses)
6. Reusable infrastructure for future research questions

---

## 2. Current State Assessment

### Completed Work (as of 2025-10-28)

#### Phase 01: OpenAlex Snapshot Download ✅
- **Status**: FUNCTIONAL
- **Evidence**: Active logs, multi-threaded downloader operational
- **Data Location**: `/Volumes/OA_snapshot/03OCT2025/`
- **Completeness**: Snapshot downloaded with entity-type partitioning

#### Phase 02: PostgreSQL Database Setup ✅
- **Status**: COMPLETE
- **Configuration**:
  - Host: `192.168.1.100:55432`
  - Database: `OADB`
  - Users: `admin` (full), `user1` (read-only)
- **Schema**: 31 tables created including:
  - Core entities: works, authors, institutions, sources, publishers, funders, concepts, topics
  - Relationship tables: authorship, citations, work_concepts, author_topics, etc.
  - Supporting tables: institution_geo, author_name_variants, apc
  - Audit infrastructure: data_modification_log with triggers
- **Features**: Foreign keys, indexes, trigram extension, row-level security

#### Phase 03: Snapshot Parsing (Partial) 🔄
- **Small Tables**: ✅ COMPLETE (Oct 26, 09:37)
  - Topics: 4,516 records
  - Concepts: 65,073 records
  - Publishers: 10,741 records
  - Funders: 32,437 records
  - Sources: 260,789 records
  - Institutions: 117,061 records
  - Processing: 831 files, 12m 18s, 0 failures

- **Authors Table**: 🔄 IN PROGRESS (288 files completed as of Oct 28, 09:40)
  - Processing: authors, author_topics, author_concepts, author_name_variants
  - State tracking with orchestrator_state.json
  - Estimated: ~110M total authors expected

- **Works Table**: 🔄 ACTIVELY PROCESSING (Oct 28, 08:22-08:40)
  - Rate: ~3,000-4,000 works/second
  - Recent batch: 339,617 works in 17.6 minutes
  - Architecture: 100K batch COPY with 5-6 minute commits
  - Status: 0 errors, 0 duplicates in recent runs
  - Estimated: ~250M works total (full OpenAlex)

- **Works Relationships**: ⏸️ QUEUED BUT NOT STARTED
  - `parse_works_relationships.py` exists but not executed
  - Covers: authorship, work_concepts, work_topics relationships
  - Critical for network construction

#### Phase 04: Author Profile Building (Partial) 🟡
- **Status**: CODE COMPLETE, NOT INTEGRATED
- **Gender Inference Pipeline (R)**:
  - Multi-method: Gender R package, gender-guesser, Genderize.io API
  - Country-aware predictions
  - Caching and validation framework
  - Expected coverage: 85-95%
  - **NOT YET RUN** on full dataset - all ~110 million authors 
- **Career Stage Modeling**: Code exists (`99_Career_stage_Calculation.R` - file needs renaming 99_ refers to vinsualisation) but needs model definition
- **Integration**: Gender predictions not yet written to authors.gender column

### In-Progress / Incomplete Work

**Immediate Needs**:
1. Complete works table loading (continuing in background)
2. Execute works relationships parsing (authorship table critical)
3. Complete authors table loading
4. Run gender inference validation (1,000 author sample)
5. Define and implement career stage model
6. Validate database against OpenAlex API (1,000 queries, >95% accuracy)

**Not Started** (Phases 05-12):
- 05: Database query system for corpus definition
- 06: Network building infrastructure
- 07: Network analysis (centrality measures)
- 08: ERGM analysis
- 09: Subnetwork analysis (ego networks, temporal)
- 10: Gender hypothesis testing (PRIMARY GOAL)
- 11: Geography hypothesis testing (secondary)
- 12: Key opinion leader identification
- 99: Visualization infrastructure

### Critical Gaps Identified

1. **Data Completeness**: Works relationships not yet extracted from JSON → authorship table empty
2. **Validation**: No systematic validation of ETL accuracy vs. OpenAlex API
3. **Gender Integration**: R pipeline ready but not integrated with database
4. **Career Model**: Needs definition (hybrid approach: domain knowledge + data-driven)
5. **Corpus Query**: No system yet for defining clinical flow cytometry corpus (292k works)
6. **Performance**: Column size issues (`fix_column_sizes.py` exists), batch commit slowdowns

---

## 3. Project Architecture

### 3.1 Data Architecture

#### OADB Database Schema (PostgreSQL on NAS)
```
Core Entities
├── works (~200M)
├── authors (Primary ~110M)
├── institutions (117k)
├── sources (261k journals/venues)
├── publishers (11k)
├── funders (32k)
├── concepts (65k)
└── topics (4.5k)

Relationships (Many-to-Many)
├── authorship (works ↔ authors) [CRITICAL - NOT YET POPULATED]
├── citations (works ↔ works)
├── work_concepts (works ↔ concepts)
├── work_topics (works ↔ topics)
├── author_concepts (authors ↔ concepts)
├── author_topics (authors ↔ topics)
└── author_institutions (authors ↔ institutions over time)

Enrichment Tables
├── author_name_variants (for disambiguation)
├── institution_geo (location data)
├── apc (article processing charges)
└── search_metadata (corpus query tracking)

Future Extensions
├── journal_editorial_boards (for colleague's committee analysis)
├── journal_metrics (impact factor, quartile, etc.)
└── author_career_profiles (computed features table)
```

#### Computed Author Profile Features (Phased Approach)

**Phase 1 - Minimal Set** (for initial H1 testing):
- `author_id` (OpenAlex ID)
- `display_name` (for gender inference)
- `gender` (inferred: M/F/Unknown)
- `works_count` (publication count)
- `cited_by_count` (total citations)
- `current_affiliation_id` & `current_affiliation_name`
- `current_affiliation_country`
- `career_stage` (to be defined)

**Phase 2 - Standard Set** (for H1-H3):
- Add: `first_publication_year`, `last_publication_year`, `career_length_years`
- Add: `freq_first_author`, `freq_last_author`, `freq_corresponding`
- Add: `is_current` (published in last 3 years)
- Add: `primary_topic`, `primary_concept`

**Phase 3 - Comprehensive** (as needed for H4-H6):
- Add: `most_cited_work`, `max_citations`
- Add: `h_index`, `i10_index` (if computable)
- Add: `coauthor_count`, `unique_institutions_count`
- Add: `international_collaborations` (country diversity)
- Add: temporal metrics (productivity trends, citation trajectories)

### 3.2 Computational Architecture

#### Data Flow
```
OpenAlex Snapshot (S3)
    ↓ (Phase 01: Download)
Local Storage (/Volumes/OA_snapshot/)
    ↓ (Phase 03: Parse & Load)
PostgreSQL Database (192.168.1.100:55432)
    ↓ (Phase 04: Enrich)
Author Profiles (R pipeline → Python integration)
    ↓ (Phase 05: Query)
Clinical Flow Cytometry Corpus (292k works, 2M authors)
    ↓ (Phase 06: Extract)
Network Edge Lists (loacal postgres database)
    ↓ (Phase 07-09: Analyze locally)
Network Analysis (NetworkX/igraph on local machine)
    ↓ (Phase 10: Test)
Statistical Results (hypothesis testing)
    ↓ (Phase 99: Visualize)
Publication Figures & Tables
```

#### Computation Strategy

**Local Machine Constraints**:
- Standard laptop/desktop (no HPC)
- Memory-efficient algorithms required
- Chunked processing for large operations
- Flexible timeline (overnight/weekend runs acceptable)

**Performance Optimizations**:
1. **Development Sampling**: Build all code on 10% data samples, run full scale only for final analyses
2. **Database Optimization**: Indexes on join keys, materialized views for common queries
3. **Network Sparsification**: Store networks as sparse matrices, use adjacency lists
4. **Incremental Processing**: Checkpoint-based workflows, resume capability
5. **Lazy Loading**: Load network data on-demand, not all at once

**Critical Performance Decisions**:
- **Networks built locally**: Export edge lists, analyze in Python/R
- **Ego networks on-demand**: Compute when needed, don't pre-compute 2M ego networks
- **ERGM sampling approach**: Run on subnetworks (~10k nodes each), not full network
- **Visualization**: Summary stats + selective visualizations, not full 306k node graphs

### 3.3 Analysis Architecture

#### Network Types (in order of implementation)

1. **Co-Author Network** (Priority 1)
   - Nodes: Authors (start with 306k with >1 paper)
   - Edges: Co-authorship on papers
   - Weights: Number of shared papers
   - Purpose: Direct test of H1 (gender centrality gaps)

2. **Author-Institution Network** (Priority 2)
   - Nodes: Authors + Institutions (bipartite)
   - Edges: Author affiliation relationships
   - Weights: Number of papers at institution
   - Purpose: Test H2 (institutional stratification)

3. **Co-Institution Network** (Priority 3)
   - Nodes: Institutions
   - Edges: Shared authors or co-authored papers
   - Weights: Collaboration strength
   - Purpose: Field-level structure, contextual analysis

#### Network Analysis Pipeline

```
Network Construction (Phase 06)
    ↓
Descriptive Statistics (Phase 07 - Part 1)
    ├── Node count, edge count, density
    ├── Degree distribution
    ├── Connected components
    └── Basic clustering coefficient
    ↓
Centrality Measures (Phase 07 - Part 2)
    ├── Degree centrality (all nodes)
    ├── PageRank (all nodes)
    ├── Eigenvector centrality (all nodes)
    ├── Clustering coefficient (all nodes)
    ├── Katz centrality (all nodes)
    ├── Closeness centrality (if network <300k nodes)
    └── Betweenness centrality (if network <500k nodes)
    └── Community detection (Leiden algorithm)
    ↓
Network Comparison (Phase 08 - ERGM)
    ├── Configuration model baseline
    ├── Sampled ERGM analysis (10-20 subnetworks)
    └── Statistical comparison (real vs. random)
    ↓
Subnetwork Analysis (Phase 09)
    ├── Tiered full network (all authors, then >1, >5, >10, >20 papers)
    ├── Ego networks (top 5-10% centrality + stratified sample)
    ├── Temporal networks (5-year rolling windows)
    └── Community detection (Leiden algorithm)
    ↓
Hypothesis Testing (Phase 10)
    ├── H1: Gender × Centrality (t-tests, regression, effect sizes)
    ├── H2: Gender × Institution Centrality (stratified analysis)
    ├── H3: Author typology (clustering) + Gender × Type
    ├── H4: Temporal trends (time series, change point analysis)
    ├── H5: Career trajectories (longitudinal analysis)
    └── H6: Homophily & clustering patterns
```

### 3.4 Software Stack

#### Data Pipeline (Phases 01-04)
- **Python 3.x**: ETL, orchestration, database operations
  - `psycopg2`: PostgreSQL interface
  - `boto3`: S3 downloads
  - `pandas`: Data manipulation
  - `gzip`, `json`: File handling
- **R 4.x**: Gender inference, career modeling
  - `gender`: Gender inference
  - `genderizeR`: API-based inference
  - `DBI`, `RPostgres`: Database connection

#### Analysis & Visualization (Phases 05-12)
- **Python**: Primary analysis language
  - `networkx`: Network construction and analysis
  - `igraph`: Alternative for large networks (C-backed)
  - `pandas`, `numpy`: Data manipulation
  - `scipy`, `statsmodels`: Statistical testing
  - `matplotlib`, `seaborn`: Static plots
  - `plotly`: Interactive visualizations
  - `dash`: Web dashboard (stretch goal)
- **R**: Statistical modeling (if needed)
  - `ergm`: ERGM analysis (if feasible at scale)
  - `igraph`: Network analysis
  - `tidyverse`: Data manipulation

#### Infrastructure
- **PostgreSQL 14+**: Primary database
- **Git**: Version control
- **Jupyter/RMarkdown**: Literate programming, documentation
- **pytest**: Python testing
- **testthat**: R testing

---

## 4. Phase-by-Phase Strategy

### Phase 03: Complete Data Pipeline ⏳ (Current Priority)

**Objective**: Finish loading OpenAlex data and validate completeness

**Tasks**:
1. ✅ Monitor and complete works table loading (background process)
2. ⚠️ Execute `parse_works_relationships.py` → populate authorship table (CRITICAL)
3. ⚠️ Complete authors table loading
4. ⚠️ Investigate and fix column size issues (`fix_column_sizes.py`)
5. ⚠️ Validate database accuracy (1,000 API queries, accept >95% match)

**Acceptance Criteria**:
- All entity tables populated with 0 failures
- Authorship table populated with ~2M rows (292k works × ~7 authors avg)
- Validation report showing >95% accuracy vs. OpenAlex API
- Data completeness report (record counts, null percentages)
- No blocking errors in logs

**Testing**:
- Systematic validation script: query API for random sample, compare to DB
- Referential integrity checks (all foreign keys valid)
- Data quality metrics (null rates, duplicate rates, outlier detection)

**Dependencies**: None (prerequisite for all downstream work)

**Estimated Duration**: 1-2 weeks (mostly waiting for background processes)

---

### Phase 04: Author Profile Enrichment 🔜 (Next Priority)

**Objective**: Enrich author profiles with gender and minimal career features

#### Sub-Phase 4.1: Gender Inference Validation
**Tasks**:
1. Sample 1,000 diverse authors (various countries, name patterns)
2. Run R gender inference pipeline on sample
3. Generate validation HTML report
4. Manually review sample for accuracy
5. Adjust confidence thresholds if needed
6. Document method and accuracy for publication

**Acceptance Criteria**:
- Validation report generated
- Manual review completed (target >80% accuracy)
- Method documented in `04_author_profile_building/README.md`
- Reproducibility: random seed set, sample IDs logged

#### Sub-Phase 4.2: Full Gender Inference
**Tasks**:
1. Run full gender inference pipeline on all 2M authors
2. Write results back to `authors.gender` column
3. Generate coverage report (M/F/Unknown percentages by country)
4. Flag low-confidence predictions for potential exclusion

**Acceptance Criteria**:
- `authors.gender` column populated for all authors
- Coverage report shows 70-85% gender assignment (M or F)
- Low-confidence flags documented
- Processing log clean (errors handled gracefully)

#### Sub-Phase 4.3: Career Stage Model Definition
**Tasks**:
1. Collaborate with Lucas to define career stage taxonomy
   - Propose: Early (0-5 yrs), Established (6-15 yrs), Senior (16-20 yrs), Veteran (>21 yrs), Emeritus (Senior OR Veteran AND inactive >5 yrs), Rising (strong recent activity). Rates of first author, last author and corrisponding author positions will need to be factored into the analysis of career stage. 
2. Define decision rules (years since first pub, recent activity, authorship patterns)
3. Implement in `99_Career_stage_Calculation.R` - file needs renaming (99_ refers to visualisation)
4. Validate on known authors (if domain knowledge available)
5. Generate distribution report (how many authors in each stage)

**Acceptance Criteria**:
- Career stage model documented in `04_author_profile_building/career_stage_model.md`
- Implementation tested on sample
- Distribution report generated (check for reasonable proportions)

#### Sub-Phase 4.4: Minimal Feature Computation
**Tasks**:
1. Compute minimal feature set for all authors:
   - `works_count`, `cited_by_count` (from OpenAlex)
   - `first_publication_year`, `last_publication_year` (from works)
   - `career_length_years` (computed)
   - `current_affiliation_*` (most recent authorship)
   - `is_current` (published 2022-2025)
2. Create `author_profiles` table or update `authors` table
3. Generate summary statistics report

**Acceptance Criteria**:
- All 2M authors have computed features
- Null rates documented (some authors may lack affiliations)
- Summary stats report shows reasonable distributions
- Code documented and tested

**Dependencies**: Phase 03 complete (need authorship table)

**Estimated Duration**: 2-3 weeks

---

### Phase 05: Corpus Definition & Query System 🔜

**Objective**: Identify and validate the ~292k clinical flow cytometry works

#### Sub-Phase 5.1: Query System Design
**Tasks**:
1. Design reusable query framework with versioning
2. Implement query logging (track what was queried when)
3. Build multi-method query capability:
   - Title/abstract text search
   - MeSH term lookup
   - Journal filtering
   - Topic/concept filtering
4. Create comparison framework (Venn diagrams of overlaps)

**Acceptance Criteria**:
- Query system documented in `05_db_query/README.md`
- All queries logged to `search_metadata` table
- Reproducible (same query → same results)
- Code tested on small examples

#### Sub-Phase 5.2: Multi-Method Query Execution
**Tasks**:
1. **Method 1**: Text search - "clinical flow cytometry" in title/abstract
2. **Method 2**: Topic/concept search - OpenAlex topic taxonomy
3. **Method 3**: Journal filtering - target journals (if needed for validation)
4. Run all three methods
5. Compare overlaps (Venn diagram analysis)
6. Generate summary report

**Acceptance Criteria**:
- Each method produces work ID list
- Overlap analysis completed
- Method comparison report generated
- Decision on final corpus documented

#### Sub-Phase 5.3: Corpus Validation & Finalization
**Tasks**:
1. Sample 100 works from corpus, manually review relevance
2. Sample 100 works from excluded set, check for false negatives
3. Refine query if needed based on validation
4. Create final corpus table: `clinical_flow_cytometry_works`
5. Generate corpus statistics (works per year, authors, institutions)
6. Document final query for publication methods section

**Acceptance Criteria**:
- Final corpus ≥ 250k works (target 292k)
- Validation shows >90% relevance
- Corpus table created with metadata (query method, date, version)
- Detailed statistics report generated

#### Sub-Phase 5.4: Historical Data Quality Assessment
**Tasks**:
1. Analyze corpus completeness by decade (1980s, 1990s, 2000s, 2010s, 2020s)
2. Check: works count, author name completeness, affiliation completeness
3. Determine historical cutoff (where quality degrades)
4. Document decision for final time range

**Acceptance Criteria**:
- Data quality report by decade
- Cutoff decision documented with rationale
- Final time range set (e.g., 1985-2024 if 1980s too sparse)

**Dependencies**: Phase 03 (need works table), Phase 04 (need author profiles)

**Estimated Duration**: 2-3 weeks

---

### Phase 06: Network Construction 🔮

**Objective**: Build co-author, author-institution, and co-institution networks

#### Sub-Phase 6.1: Network Data Extraction
**Tasks**:
1. Extract co-author edge list from authorship table
   - Query: all author pairs on same paper in corpus
   - Output: `author1_id, author2_id, paper_count, first_year, last_year`
2. Extract author-institution edges
   - Query: author-institution pairs from authorship records
   - Output: `author_id, institution_id, paper_count, years_active`
3. Extract co-institution edges (if needed)
   - Compute: institutions sharing authors or papers
   - Output: `institution1_id, institution2_id, collaboration_strength`

**Acceptance Criteria**:
- Edge lists exported as local postgres database 
- Sample validation (spot-check edges against database)

#### Sub-Phase 6.2: Network Object Construction
**Tasks**:
1. Load edge lists into NetworkX graphs
2. Add node attributes (from author_profiles):
   - Gender, career_stage, works_count, etc.
3. Test network loading and memory usage on sample
4. Build full networks (may take hours)
5. Save networks as pickle/GraphML for reuse

**Acceptance Criteria**:
- Networks successfully loaded into NetworkX
- Node count, edge count match expectations
- Node attributes correctly attached
- Networks saved for future use

#### Sub-Phase 6.3: Tiered Network Construction
**Tasks**:
1. Build "full" co-author network (all 2M authors)
2. Build filtered networks:
   - Authors with >1 paper (306k nodes)
   - Authors with >5 papers
   - Authors with >10 papers
   - Authors with >20 papers
3. Compare network properties across tiers
4. Document tier definitions

**Acceptance Criteria**:
- 5 network versions constructed
- Comparison table (nodes, edges, density, components)
- Decision on primary network for analysis

**Dependencies**: Phase 05 (need corpus), Phase 04 (need author attributes)

**Estimated Duration**: 2-3 weeks (includes troubleshooting performance)

---

### Phase 07: Network Analysis 🔮

**Objective**: Compute centrality measures and structural properties

#### Sub-Phase 7.1: Descriptive Network Statistics
**Tasks**:
1. Compute basic properties (all network tiers):
   - Node count, edge count, density
   - Degree distribution (histogram, summary stats)
   - Connected components (size of largest component)
   - Average clustering coefficient
2. Generate summary report for each network
3. Visualize degree distributions, component sizes

**Acceptance Criteria**:
- Summary stats table for all network tiers
- Distributions plotted and interpretable
- Report generated as Jupyter notebook

#### Sub-Phase 7.2: Centrality Measures (Scalable)
**Tasks**:
1. Compute for all authors in primary network:
   - Degree centrality
   - PageRank
   - Eigenvector centrality
   - Local clustering coefficient
   - Katz centrality
2. Save centrality scores to database
3. Generate distributions by gender (first glimpse of H1!)

**Acceptance Criteria**:
- Centrality scores computed for all nodes
- Results saved (don't re-compute unnecessarily)
- Gender comparison plots generated (preliminary H1 test)

#### Sub-Phase 7.3: Centrality Measures (Conditional)
**Tasks**:
1. Assess feasibility of closeness/betweenness
2. If network <300k nodes: compute closeness centrality
3. If network <500k nodes: consider betweenness
4. Document which measures computed and why

**Acceptance Criteria**:
- Feasibility documented
- Available centrality measures computed
- Limitations noted for publication

#### Sub-Phase 7.4: Community Detection
**Tasks**:
1. Run Leiden algorithm for community detection
2. Characterize communities (size, gender composition, topics)
3. Visualize community structure (summary, not full network)
4. Export community assignments for hypothesis testing

**Acceptance Criteria**:
- Communities identified
- Community characterization report
- Visualization of major communities

**Dependencies**: Phase 06 (networks built)

**Estimated Duration**: 3-4 weeks (computation intensive)

---

### Phase 08: ERGM Analysis 🔮

**Objective**: Test how network differs from random with matched features

#### Sub-Phase 8.1: Baseline Random Network
**Tasks**:
1. Compute configuration model (preserve degree sequence)
2. Generate 100 random realizations
3. Compare real network to random:
   - Clustering coefficient
   - Assortativity (gender, career stage)
   - Path lengths (if computable)
4. Statistical tests (real vs. random distribution)

**Acceptance Criteria**:
- Configuration model implemented
- 100 random networks generated
- Comparison report with p-values

#### Sub-Phase 8.2: Subnetwork ERGM Sampling (if full ERGM infeasible)
**Tasks**:
1. Sample 10-20 subnetworks (~10k nodes each)
   - Random samples
   - Stratified by gender/career stage
   - Community-based samples
2. Run ERGM on each subnetwork
   - Terms: edges, gender homophily, career stage, reciprocity
3. Aggregate findings across subnetworks
4. Test: does gender predict tie formation beyond chance?

**Acceptance Criteria**:
- Subnetworks sampled and documented
- ERGMs successfully fitted
- Results aggregated with confidence intervals
- Gender effects tested statistically

**Dependencies**: Phase 07 (need centrality measures)

**Estimated Duration**: 3-4 weeks (ERGM fitting slow)

---

### Phase 09: Subnetwork Analysis 🔮

**Objective**: Analyze ego networks and temporal dynamics

#### Sub-Phase 9.1: Ego Network Construction
**Tasks**:
1. Identify key authors:
   - Top 5% by degree centrality
   - Top 5% by PageRank
   - Stratified random sample (1000 authors, balanced by gender/career)
2. Extract 1-hop and 2-hop ego networks
3. Compute ego network metrics:
   - Size, density, gender composition
   - Brokerage (structural holes)
   - Constraint, effective size
4. Compare ego networks by author gender

**Acceptance Criteria**:
- Ego networks extracted for ~5,000 authors
- Metrics computed and saved
- Gender comparison analysis (ego network size, density, homophily)

#### Sub-Phase 9.2: Temporal Network Analysis
**Tasks**:
1. Define time windows (e.g., 5-year rolling: 2000-2004, 2005-2009, ..., 2020-2024)
2. Build network for each time window
3. Compute centrality measures for each window
4. Track author centrality over time (longitudinal)
5. Test H4: Are gender gaps closing over time?

**Acceptance Criteria**:
- Temporal networks constructed
- Centrality tracked longitudinally
- Time series plots (gender gaps over time)
- Statistical test of temporal trends

#### Sub-Phase 9.3: On-Demand Ego Network Tool (Stretch Goal)
**Tasks**:
1. Build simple query interface (command-line or web form)
2. Input: author name/ID
3. Output: ego network visualization + metrics
4. Shiny/web interface for exploration
5. Optimize for speed (pre-compute adjacency, lazy rendering)

**Acceptance Criteria**:
- Tool functional for ad-hoc queries
- Renders ego network in <10 seconds
- Basic visualization (not publication-quality)

**Dependencies**: Phase 07 (centrality measures), Phase 08 (random baselines)

**Estimated Duration**: 3-4 weeks

---

### Phase 10: Gender Hypothesis Testing 🎯 (PRIMARY GOAL)

**Objective**: Systematically test all 6 hypothesis families

#### Sub-Phase 10.1: H1 - Gender Disparities in Network Centrality
**Tasks**:
1. Compare centrality measures by gender (M vs F):
   - Degree, PageRank, Eigenvector, Clustering
   - T-tests, effect sizes (Cohen's d)
   - Control for career stage, productivity
2. Regression models:
   - DV: Centrality measures
   - IV: Gender (+ controls: career stage, works count, field)
3. Test H1b: Do gaps vary by centrality type?
4. Generate publication-quality tables and figures

**Acceptance Criteria**:
- Statistical tests completed for all centrality measures
- Regression results with confidence intervals
- Effect sizes reported (not just p-values)
- Publication-ready table summarizing results

#### Sub-Phase 10.2: H2 - Institutional Gender Stratification
**Tasks**:
1. Rank institutions by network centrality (degree, betweenness)
2. Compute gender composition at each institution
3. Test: Are women underrepresented at top institutions?
   - Chi-square tests by quartile
   - Logistic regression (odds of being at top institution ~ gender)
4. Test H2b: Is gap largest at most central institutions?

**Acceptance Criteria**:
- Institutional ranking with gender composition
- Statistical tests of stratification
- Visualization (gender % vs. institution centrality)

#### Sub-Phase 10.3: H3 - Author Typology & Gender Disparities
**Tasks**:
1. Cluster authors into role types:
   - Features: centrality measures, authorship patterns, career metrics
   - Method: K-means or hierarchical clustering (5-8 clusters)
   - Validation: silhouette scores, domain interpretation
2. Label clusters (e.g., "Peripheral", "Collaborator", "Central PI", "Bridge")
3. Test H3b: Gender distribution across types (chi-square)
4. Test H3c: Within-type gender differences in centrality
5. Test H3d: Interaction (gender × career stage → type membership)

**Acceptance Criteria**:
- Author typology defined and validated
- Cluster characterization report
- Statistical tests of gender × type associations
- Visualization (type profiles, gender distributions)

#### Sub-Phase 10.4: H4 - Temporal Trends in Gender Equity
**Tasks**:
1. Use temporal networks from Phase 09
2. Plot gender gaps in centrality over time
3. Test linear trends (are gaps closing?)
4. Test for acceleration (pre/post 2010 slope comparison)
5. Change point analysis (when did gaps start closing, if at all?)

**Acceptance Criteria**:
- Time series plots (gender gaps by decade/5-year window)
- Statistical tests of temporal trends
- Interpretation: improving, stable, or worsening?

#### Sub-Phase 10.5: H5 - Career Trajectory Gender Differences
**Tasks**:
1. Longitudinal analysis (track authors over time)
2. Mixed-effects models: centrality growth ~ gender + time + (random: author)
3. Compare early-career vs. late-career slopes by gender
4. Test: Do women's networks grow more slowly?

**Acceptance Criteria**:
- Longitudinal models fitted
- Gender differences in trajectory slopes quantified
- Visualization (spaghetti plots, average trajectories by gender)

#### Sub-Phase 10.6: H6 - Collaborative Pattern Gender Differences
**Tasks**:
1. Ego network metrics by gender (from Phase 09):
   - Size, density, clustering
   - Gender homophily (E-I index, assortativity)
2. Compare: Do women have smaller, more clustered networks?
3. Test homophily: Do women collaborate more with women?
4. Control for career stage and productivity

**Acceptance Criteria**:
- Ego network comparisons (M vs F)
- Homophily analysis (statistical tests)
- Interpretation: clustered vs. bridging patterns by gender

**Dependencies**: Phases 07-09 (all network analyses complete)

**Estimated Duration**: 4-6 weeks (most complex phase)

---

### Phase 11: Geography Hypothesis Testing 🌍 (Secondary)

**Objective**: Test geographic disparities (if time permits)

**Tasks**:
1. Extend analyses to include country/continent as factor
2. Test: Do gender patterns vary by geography?
3. Network analysis by region
4. Institutional differences by country

**Acceptance Criteria**:
- Geographic extension of H1-H6
- Cross-regional comparisons

**Dependencies**: Phase 10 complete

**Estimated Duration**: 2-3 weeks

---

### Phase 12: Key Opinion Leader Identification 🔮 (Exploratory)

**Objective**: Identify current/emerging KOLs using network + career features

**Tasks**:
1. Define KOL criteria (high centrality + productivity + recent activity)
2. Identify historical KOLs (past leaders)
3. Model KOL trajectories (what predicts becoming a KOL?)
4. Predict emerging KOLs (early-career authors with KOL-like trajectories)

**Acceptance Criteria**:
- KOL list generated
- Trajectory model documented
- Emerging KOL predictions with confidence scores

**Dependencies**: Phase 10 complete

**Estimated Duration**: 2-3 weeks

---

### Phase 99: Visualization & Communication 🎨

**Objective**: Create publication-quality figures and interactive dashboard
gender should always be erfered to as "M", "Male", "F" or "Female" never "Man" or "Woman" 

#### Standard Visualizations (Throughout)
**Tasks**:
1. Theme development (consistent colors, fonts, style)
2. Standard plots:
   - Degree distributions
   - Gender comparison bar/violin plots
   - Time series (trends over time)
   - Scatter plots (centrality vs. productivity)
   - Heatmaps (correlation matrices)

#### Publication Figures (Phase 10+)
**Tasks**:
1. Main text figures (4-6 high-impact visualizations)
2. Supplementary figures (detailed results)
3. Tables (formatted for journal submission)
4. Network visualizations (selected subnetworks only)

#### Interactive Dashboard (Stretch Goal)
**Tasks**:
1. Build Dash/Plotly dashboard
2. Features:
   - Corpus overview (works, authors, trends)
   - Author search (profile + ego network)
   - Network explorer (zoomable subnetworks)
   - Hypothesis results (interactive plots)
3. Deploy locally (or web if feasible)

**Dependencies**: Ongoing (start in Phase 07, finalize in Phase 10)

**Estimated Duration**: Ongoing + 2 weeks for dashboard

---

## 5. Computational Strategy

### 5.1 Scale Management

**Challenge**: 2M authors, 292k works, ~2M authorships, 306k+ network nodes, millions of edges

**Strategies**:

1. **Sampling for Development**
   - Build all code on 10% sample (30k works, 200k authors)
   - Test functionality and performance
   - Scale to full data only when code proven

2. **Chunked Processing**
   - Process large tables in chunks (100k rows at a time)
   - Use generators/iterators (don't load full datasets into memory)
   - Checkpoint progress (resume if interrupted)

3. **Efficient Data Structures**
   - Sparse matrices for networks (scipy.sparse)
   - Adjacency lists (not full adjacency matrices)
   - Pandas with categorical dtypes (reduce memory)
   - Parquet format for intermediate files (compressed columnar)

4. **Selective Computation**
   - Closeness/betweenness only if feasible (check network size)
   - Ego networks on-demand (not pre-computed)
   - ERGM on samples (not full network)

5. **Database Optimization**
   - Index all foreign keys
   - Materialized views for common queries
   - EXPLAIN ANALYZE for slow queries
   - VACUUM/ANALYZE regularly

6. **Parallelization (where possible)**
   - Embarrassingly parallel tasks (centrality per node, ego networks)
   - Python multiprocessing for CPU-bound tasks
   - Database: parallel queries if supported

### 5.2 Memory Management
Memory on the primary coputer is 72GB DDR4 
Momory on the NAS is 64GB DDR5 
Memory is not a constraining factor for most analysis

**Estimated Memory Usage**:
- Full co-author network (306k nodes, ~1-5M edges): 2-10 GB
- Node attributes (306k × 10 features): ~100 MB
- Edge list (5M edges × 3 columns): ~120 MB

**Tactics**:
- Load networks only when needed (pickle for reuse)
- Delete intermediate objects (force garbage collection)
- Use memory profilers (memory_profiler) to identify leaks
- Consider dask for out-of-core computation if needed

### 5.3 Performance Expectations

**Network Construction** (Phase 06):
- Edge list extraction: 1-2 hours (database query)
- Network loading: 10-30 minutes (NetworkX)
- Total: Half day per network type

**Centrality Computation** (Phase 07):
- Degree, PageRank, Eigenvector: Minutes to 1 hour each
- Closeness (if feasible): Hours to day
- Betweenness (if feasible): Days (likely skip)
- Total: 1-3 days for all feasible measures

**ERGM Analysis** (Phase 08):
- Single ERGM (10k nodes): Hours
- 20 subnetworks: Days to week
- Total: 1-2 weeks

**Ego Networks** (Phase 09):
- 5,000 ego networks: Hours (parallelizable)
- On-demand queries: <10 seconds each

---

## 6. Reproducibility Framework

### 6.1 Random Seed Management

**Principle**: Set seeds for all stochastic operations

**Implementation**:
```python
# In config.py or at top of each script
RANDOM_SEED = 428

import random
import numpy as np
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

# For sampling
authors_sample = authors.sample(n=1000, random_state=RANDOM_SEED)

# For train/test splits
train, test = train_test_split(data, random_state=RANDOM_SEED)
```

**Critical Points**:
- Corpus sampling (if used)
- Gender inference validation sample
- Subnetwork sampling for ERGM
- Random network generation
- Clustering initialization
- Train/test splits

### 6.2 Environment Specification

**Python Environment**:
```bash
# Generate requirements.txt with versions
pip freeze > requirements.txt

# Or use conda environment.yml
conda env export > environment.yml
```

**R Environment**:
```r
# Document package versions
sessionInfo() # save output to session_info.txt
```

**Database Version**:
- Document PostgreSQL version
- Document OpenAlex snapshot date (2025-10-03)

### 6.3 Data Versioning

**Corpus Versioning**:
- Log query parameters to `search_metadata` table
- Include: query string, date run, work count, version label
- Save corpus work IDs to versioned file: `corpus_v1_20251028.csv`

**Network Versioning**:
- Save edge lists with version: `coauthor_edgelist_v1.parquet`
- Document: construction date, corpus version, filters applied
- Save networks with metadata: `coauthor_network_v1.pkl.gz`

**Analysis Versioning**:
- Git commit hash in analysis outputs
- Timestamp all result files
- Link results to data version in filenames

### 6.4 Computational Reproducibility

**Documentation Requirements**:
1. **Code**: Fully documented (docstrings, inline comments for complex logic)
2. **Notebooks**: Narrative explaining each step
3. **Parameters**: All thresholds, cutoffs, parameters documented
4. **Decisions**: Why certain choices made (in decision log)

**Testing**:
- Unit tests for utility functions
- Integration tests for pipelines
- Regression tests (outputs match previous runs)

**Execution Logs**:
- Save stdout/stderr for all major runs
- Log start time, end time, parameters, results summary
- Store logs in dated folders: `logs/20251028_phase06_network_build/`

---

## 7. Documentation Standards

### 7.1 Per-Phase Documentation

**Required Files per Phase Folder**:

1. **README.md**: Phase overview
   - Purpose and objectives
   - Dependencies (what must be complete first)
   - Scripts/notebooks in this phase (execution order)
   - Inputs and outputs
   - How to run (step-by-step)
   - Expected runtime
   - Troubleshooting common issues

2. **requirements.txt** or **environment.yml**: Dependencies specific to this phase

3. **RESULTS_SUMMARY.md**: Key findings (once phase complete)
   - Summary statistics
   - Key figures (embedded or linked)
   - Interpretation
   - Decisions made based on results

4. **CHANGELOG.md**: Track changes over time
   - Date, change description, reason

### 7.2 Code Documentation

**Python Scripts**:
```python
"""
Script: parse_works.py
Purpose: Parse OpenAlex works from gzipped JSON into PostgreSQL
Author: Lucas Black
Date: 2025-10-15
Dependencies: psycopg2, pandas, gzip, json

Usage:
    python parse_works.py --manifest works_manifest.txt --batch-size 100000

Inputs:
    - Gzipped JSON files (OpenAlex works format)
    - Database connection config

Outputs:
    - Populated works table in OADB
    - Log file with processing stats

Notes:
    - Foreign keys disabled during COPY for performance
    - Commit every 100k records (configurable)
"""

def parse_work_json(json_obj):
    """
    Extract work fields from OpenAlex JSON object.

    Args:
        json_obj (dict): OpenAlex work JSON

    Returns:
        dict: Flattened work fields ready for database insert

    Notes:
        - Handles missing fields gracefully (returns None)
        - Extracts nested fields (e.g., primary_location.source.id)
    """
    # implementation
```

**R Scripts**: Similar docstring style using roxygen2 format

**Jupyter Notebooks**:
- Markdown cells explaining each section
- "Story" flow: question → analysis → interpretation
- Figures with captions
- Summary/conclusion cell at end

### 7.3 Methods Documentation (for Publication)

**File**: `METHODS_LOG.md` (project root)

**Structure**:
```markdown
# Methods Log: Clinical Flow Cytometry Gender Analysis

## Data Source
- OpenAlex Snapshot: 2025-10-03
- Database: PostgreSQL 14.5
- Total records: 250M works, 110M authors

## Corpus Definition
- Query: [exact query string]
- Filters: [inclusion/exclusion criteria]
- Date range: [final range]
- Final corpus: 292,156 works
- Query date: 2025-11-15
- Version: corpus_v1

## Gender Inference
- Methods: genderizeR, gender-guesser, Genderize.io API
- Validation: 1,000 author sample, 83% accuracy
- Coverage: 78% M/F assigned, 22% unknown
- Country-aware: Yes
- Code: 04_author_profile_building/02_predict_gender_multi.R

## Career Stage Model
- [Document exact model used]

## Network Construction
- [Exact construction rules]

## Statistical Tests
- [All tests, parameters, software versions]
```

### 7.4 Decision Log

**File**: `DECISION_LOG.md` (project root)

**Format**:
```markdown
## Decision: [Brief title]
**Date**: 2025-11-20
**Context**: [Why this decision needed]
**Options Considered**:
1. Option A: [description, pros, cons]
2. Option B: [description, pros, cons]
**Decision**: [What was chosen]
**Rationale**: [Why this option]
**Implications**: [What this means for analysis]
**Reversible**: [Yes/No - can we change later?]
```

**Example**:
```markdown
## Decision: Exclude single-publication authors from primary network
**Date**: 2025-12-01
**Context**: 2M authors total, but 1.7M have only 1 publication. Including all creates memory issues and may dilute analysis.
**Options Considered**:
1. Include all authors (2M nodes)
   - Pros: Complete picture
   - Cons: Memory intensive, many isolated nodes, hard to interpret
2. Exclude single-pub authors (306k nodes)
   - Pros: Focuses on "real" field participants, manageable size
   - Cons: May miss some emerging researchers
3. Tiered approach (build both, compare)
   - Pros: See how filtering affects results
   - Cons: More computation
**Decision**: Tiered approach - build both, use >1 pub network as primary
**Rationale**: Best of both worlds. Can report how filtering affects results. Standard practice in network analysis.
**Implications**: Will build and analyze 5 network tiers (all, >1, >5, >10, >20 papers)
**Reversible**: Yes - have data for all options
```

---

## 8. Risk Register

### 8.1 Technical Risks

#### Risk: Computational Infeasibility (High Impact, Medium Likelihood)
**Description**: Network too large for local machine; ERGM/betweenness impossible
**Mitigation**:
- Sample-based approaches (ERGM on subnetworks)
- Skip infeasible measures (document why)
- Use more efficient algorithms (igraph C backend)
- Set realistic expectations upfront
**Contingency**: If local compute insufficient, prioritize core analyses (H1), skip extensions (H5-H6)

#### Risk: Database Performance Degradation (Medium Impact, Medium Likelihood)
**Description**: Queries slow down as tables grow; joins take hours
**Mitigation**:
- Index all foreign keys
- Regularly VACUUM/ANALYZE
- Use EXPLAIN to optimize queries
- Consider materialized views
**Contingency**: Export to local files (Parquet) for analysis if database too slow

#### Risk: Memory Errors (High Impact, High Likelihood)
**Description**: NetworkX runs out of memory loading 306k node network
**Mitigation**:
- Use sparse formats
- Load only needed node attributes
- Process in chunks
- Monitor memory usage
**Contingency**: Use igraph (more memory-efficient) or downsample network

#### Risk: Gender Inference Inaccuracy (High Impact, Low Likelihood)
**Description**: Gender predictions <70% accurate, undermines analysis validity
**Mitigation**:
- Validate on sample first
- Use multi-method consensus
- Document uncertainty
- Sensitivity analysis (exclude low-confidence predictions)
**Contingency**: If accuracy too low, restrict to high-confidence only or collaborate with domain experts for manual validation

### 8.2 Analytical Risks

#### Risk: Network Too Fragmented (Medium Impact, Medium Likelihood)
**Description**: Clinical flow cytometry network has many disconnected components, can't compute global centrality
**Mitigation**:
- Analyze largest connected component
- Report component structure
- Use local measures (degree, clustering) instead of global (closeness, betweenness)
**Contingency**: Shift focus to ego networks and local structure (still valid for H1, H3, H6)

#### Risk: No Gender Differences Found (Low Impact, Low Likelihood)
**Description**: Null result - no significant gender disparities in network positions
**Mitigation**:
- Ensure sufficient statistical power (2M authors should provide this)
- Check for subtle effects (small effect sizes)
- Interpret null findings (also a valid result!)
**Contingency**: Null findings still publishable if methods rigorous. Shift narrative to "clinical flow cytometry may be more equitable than other fields."

#### Risk: Temporal Trends Not Detectable (Medium Impact, Medium Likelihood)
**Description**: Historical data too sparse or noisy to detect trends reliably
**Mitigation**:
- Assess data quality by decade first
- Use robust statistical methods (smoothing, rolling windows)
- Focus on recent decades if historical data poor
**Contingency**: Report temporal analysis as exploratory, focus on cross-sectional findings (H1-H3)

### 8.3 Project Management Risks

#### Risk: Scope Creep (High Impact, High Likelihood)
**Description**: Interesting tangents derail timeline; try to analyze everything
**Mitigation**:
- Strict phased approach (complete phase before moving on)
- Prioritize H1 (core finding) over H5-H6 (extensions)
- Document "future work" ideas without implementing
- Regular check-ins on progress vs. plan
**Contingency**: Cut secondary hypotheses (H11 geography, Phase 12 KOLs) if behind schedule. Always question Lucas if analysis is in-scope.

#### Risk: Dependency Delays (Medium Impact, Medium Likelihood)
**Description**: Works table loading takes longer than expected, blocks all downstream work
**Mitigation**:
- Monitor loading progress regularly
- Use sample data for development (don't wait for full load)
- Parallelize where possible (R gender pipeline independent)
**Contingency**: Proceed with development on samples, scale up when data ready

#### Risk: Reproducibility Failures (High Impact, Low Likelihood)
**Description**: Can't reproduce earlier results; forgot random seeds or parameters
**Mitigation**:
- Set seeds from day 1
- Version everything (data, code, results)
- Document decisions in real-time (not retroactively)
- Test reproducibility periodically
**Contingency**: If reproducibility lost, document break, establish new baseline, proceed carefully

### 8.4 Publication Risks

#### Risk: Committee/Journal Data Not Integrable (Low Impact, Medium Likelihood)
**Description**: Colleague's committee analysis can't be merged with network findings
**Mitigation**:
- Plan for integration (journal metadata fields)
- Regular communication with colleague
- Separate but complementary analyses acceptable
**Contingency**: Publish network analysis separately, collaborate on second paper integrating committee data

#### Risk: Methods Too Complex for Journal (Low Impact, Low Likelihood)
**Description**: Reviewers don't understand ERGM or network methods
**Mitigation**:
- Clear, accessible methods writing
- Supplementary materials for technical details
- Focus on interpretable results, not just methods
- Choose appropriate journal (methods-friendly)
**Contingency**: Simplify analyses (skip ERGM if too complex to explain), focus on descriptive network stats + hypothesis tests

---

## 9. Publication Roadmap

### 9.1 Target Journals

**Primary Targets** (methods-friendly, interdisciplinary):
- *Nature Communications* (high impact, network analysis precedent)
- *PLOS ONE* (rigorous, open access, interdisciplinary)
- *Science Advances* (broad readership, policy relevance)

**Domain-Specific**:
- *Cytometry Part A* or *Cytometry Part B* (if emphasizing field-specific findings)
- *Blood Advances* (clinical hematology focus)

**Methods-Focused** (if emphasizing network approach):
- *Social Networks*
- *Network Science*

**Gender in STEM**:
- *Gender, Work & Organization*
- *Research Policy*

### 9.2 Manuscript Structure (Anticipated)

**Title**: Gender Disparities in Clinical Flow Cytometry Research: A Network Analysis of 292,000 Publications

**Abstract** (250 words):
- Context (gender gaps in STEM)
- Objective (test network disparities in clinical flow cytometry)
- Methods (OpenAlex data, network analysis, 2M authors)
- Results (key findings from H1-H4)
- Conclusions (implications for equity)

**Introduction**:
1. Gender gaps in STEM (broad context)
2. Network position as mechanism (theory)
3. Clinical flow cytometry as case study (why this field?)
4. Research questions (H1-H6 framed as questions)

**Methods**:
1. Data source (OpenAlex, corpus definition, validation)
2. Author profiles (gender inference, career stage)
3. Network construction (co-author, author-institution)
4. Network measures (centrality definitions)
5. Statistical analysis (tests, models, controls)
6. Reproducibility (code/data availability)

**Results**:
1. Corpus overview (292k works, temporal trends, field growth)
2. Network structure (size, density, components, degree distribution)
3. H1: Gender × centrality (main finding)
4. H2: Institutional stratification
5. H3: Author typologies
6. H4: Temporal trends
7. H5-H6: Career trajectories and homophily (if space)

**Discussion**:
1. Summary of key findings
2. Mechanisms (why do disparities exist?)
3. Comparison to other fields
4. Implications (for women in research, policy)
5. Limitations (gender inference uncertainty, causality)
6. Future directions

**Figures** (6-8 main + supplementary):
1. Fig 1: Corpus overview (works per year, author growth)
2. Fig 2: Network structure (degree distribution, components)
3. Fig 3: H1 results (centrality by gender, effect sizes)
4. Fig 4: H2 institutional stratification (gender % vs. centrality)
5. Fig 5: H3 author typology (cluster profiles, gender distribution)
6. Fig 6: H4 temporal trends (gender gaps over time)
7. Supp: Ego network examples
8. Supp: Sensitivity analyses

**Tables** (3-5):
1. Table 1: Corpus characteristics
2. Table 2: Network descriptive statistics
3. Table 3: Regression results (centrality ~ gender + controls)
4. Table S1: Data quality validation
5. Table S2: Full statistical results

### 9.3 Supplementary Materials

**Code/Data Availability**:
- GitHub repository (code, documentation, notebooks)
- Zenodo DOI (archived version at submission)
- Data: Edge lists, author attributes (anonymized if needed)
- Analysis notebooks (fully reproducible)

**Supplementary Methods**:
- Detailed gender inference validation
- Career stage model specification
- ERGM technical details
- Sensitivity analyses (alternative thresholds, subsets)

**Supplementary Results**:
- Full regression tables
- Additional network measures
- Geographic analysis (if completed)
- Robustness checks

### 9.4 Timeline to Submission (Tentative)

**Assumptions**: Work starts 2025-11-01, full-time effort

| Phase | Duration | Completion Date |
|-------|----------|-----------------|
| Phase 03 completion | 2 weeks | 2025-11-15 |
| Phase 04 (profiles) | 3 weeks | 2025-12-06 |
| Phase 05 (corpus) | 3 weeks | 2025-12-27 |
| Phase 06 (networks) | 3 weeks | 2026-01-17 |
| Phase 07 (analysis) | 4 weeks | 2026-02-14 |
| Phase 08 (ERGM) | 4 weeks | 2026-03-14 |
| Phase 09 (subnetworks) | 3 weeks | 2026-04-04 |
| Phase 10 (hypotheses) | 6 weeks | 2026-05-16 |
| Manuscript writing | 4 weeks | 2026-06-13 |
| Internal review & revision | 2 weeks | 2026-06-27 |
| **Submission** | - | **2026-07-01** |

**Adjustments for Part-Time Work**: Double timeline (~18 months to submission)

---

## 10. Decision Log

### Initial Decisions (from Planning Phase)

#### Decision: Complete Data Pipeline Before Analysis
**Date**: 2025-10-28
**Rationale**: Need solid foundation; avoid rework if data issues discovered mid-analysis
**Implications**: Phases 03-04 complete before Phase 05+

#### Decision: Network-First Approach
**Date**: 2025-10-28
**Rationale**: Aligns with primary research questions (H1-H6 all network-based). Committee data as future extension.
**Implications**: Focus on co-author network infrastructure, add journal metadata for future integration

#### Decision: Multi-Method Corpus Definition with Validation
**Date**: 2025-10-28
**Rationale**: Rigorous corpus definition critical for publication. Compare methods to ensure robustness.
**Implications**: Phase 05 includes comparison framework, not just single query

#### Decision: Tiered Network Approach (All Authors + Filtered)
**Date**: 2025-10-28
**Rationale**: Build full network (2M) for completeness, but analyze filtered (306k+ with >1 paper) for interpretability. Report how filtering affects results.
**Implications**: Phase 06 builds 5 network tiers, compare properties

#### Decision: H1 as Foundation, Then Build Out
**Date**: 2025-10-28
**Rationale**: H1 (gender centrality gaps) is most fundamental. If no differences, affects interpretation of H2-H6. Test first.
**Implications**: Phase 10 prioritizes H1, then sequentially tests others

#### Decision: Local Machine Computation with Sampling Strategy
**Date**: 2025-10-28
**Rationale**: No HPC access. Use sampling for development, optimize for efficiency, patient timeline.
**Implications**: All code must be memory-efficient. Expect days-weeks for some computations.

#### Decision: Publication-Grade Reproducibility from Start
**Date**: 2025-10-28
**Rationale**: Retrofitting reproducibility is hard. Build in from beginning (seeds, versioning, documentation).
**Implications**: All scripts log parameters, set seeds, version outputs. More upfront effort but cleaner publication.

#### Decision: Phased Author Profile Features
**Date**: 2025-10-28
**Rationale**: 20+ features ambitious. Start minimal (5 features), add as analyses require. Avoid premature optimization.
**Implications**: Phase 04 starts with minimal set, extend in Phase 10 if needed

#### Decision: Gender Inference Validation Before Full Run
**Date**: 2025-10-28
**Rationale**: Gender inference accuracy critical for validity. Validate on 1,000 sample, adjust if needed, then scale.
**Implications**: Phase 04 includes validation sub-phase before full inference

#### Decision: Ego Networks On-Demand, Not Pre-Computed
**Date**: 2025-10-28
**Rationale**: 2M ego networks infeasible to compute/store. Compute for key authors + stratified sample. Build tool for ad-hoc queries (stretch goal).
**Implications**: Phase 09 selective ego networks, Phase 99 interactive tool (if time)

---

## Appendices

### A. Key Contacts & Resources

**Database**: 192.168.1.100:55432 (OADB)
**Data Storage**: /Volumes/OA_snapshot/03OCT2025/
**OpenAlex API Email**: s.lucasblack@gmail.com
**GitHub Repository**: [To be created]

### B. Glossary of Network Terms

- **Degree Centrality**: Number of direct connections (co-authors)
- **PageRank**: Importance based on connections to important others (Google's algorithm)
- **Eigenvector Centrality**: Centrality based on being connected to central others
- **Betweenness Centrality**: Frequency of being on shortest paths between other nodes (broker role)
- **Closeness Centrality**: Average distance to all other nodes (efficient information access)
- **Clustering Coefficient**: Extent to which neighbors are connected to each other (network closure)
- **Ego Network**: Network centered on one individual (1-hop: direct connections, 2-hop: friends of friends)
- **ERGM**: Exponential Random Graph Model - statistical model for networks
- **Homophily**: Tendency to connect with similar others (e.g., same gender)
- **Assortativity**: Correlation of node attributes on connected nodes

### C. Clinical Flow Cytometry Background (Brief)

**What is it?**: Technique to measure cell characteristics using lasers and antibodies. Critical for diagnosing blood cancers, immune disorders.

**Why study this field?**:
- Specialized niche (not too broad like "medicine", not too narrow like single disease)
- Clinical + research blend (diverse career paths)
- Strong collaborative nature (requires multi-disciplinary teams)
- Well-defined journals and professional societies
- Reasonable corpus size (hundreds of thousands of papers, not millions)

**Key Journals**: Cytometry Part B (clinical), Cytometry Part A, Blood, Haematologica, clinical hematology journals

---

## Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-28 | Claude + Lucas | Initial comprehensive planning document created after extensive Q&A session |

---

**END OF PLANNING DOCUMENT**

*This is a living document. Update as project evolves, decisions are made, and risks materialize or resolve.*
