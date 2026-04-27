# Progress Log

## 2026-04-27

### Session 1: Tutoring on Evolutionary Analysis (Lecture 12)
- Walked through all lecture concepts: Lehman's Law, three drivers of change, logical coupling, churn/hotspots, ArchLens
- Ran hands-on evolutionary analysis on itu-minitwit repo (churn, logical coupling, commit message quality)
- Key insight: main.go is the clear hotspot, db.go and main.go are logically coupled

### Session 2: Assignment planning
- Read assignment requirements for Deliverable 5
- Decided on approach: analyse Zeeguu-API, recover module view + evolutionary enrichment
- Chose Zeeguu-API (Python backend) over doing both systems — depth over breadth

### Session 3: Project setup
- Created repo at ~/Dev/zeeguu-architecture-recovery/
- Connected Overleaf for LaTeX report (report/ subfolder synced via git)
- Set up report skeleton matching assignment structure
- Wrote draft introduction

### Session 4: Exploring Zeeguu-API
- Cloned repo, explored structure
- Found 424 Python files in zeeguu/ package
- Three main layers: api/, core/, and supporting modules (config, logging, operations)
- Found existing archlens.json with architectural views — potential hypothetical view for reflexion model

### Session 5: Building analysis scripts
- **Script 1: extract_imports.py** — AST-based import extraction
  - Scans all .py files, parses with ast module, extracts internal imports
  - Result: 1577 internal dependencies across 424 files
  - This is the raw source view (not yet architectural)
- **Script 2: abstract_modules.py** — module-level abstraction (DONE)
  - Aggregates file-level deps along folder hierarchy
  - Configurable depth (depth 1 = top-level, depth 2 = sub-packages)
  - Depth 1 results: 8 modules, 13 dependencies. api->core dominates (weight 322)
  - Depth 2 results: 54 modules, 192 dependencies. api.endpoints->core.model dominates (weight 174)
  - Found potential issue: core->api dependency (weight 1) goes "wrong" direction
  - Decision: use depth 1 as main view in report, depth 2 as supporting detail

### Decisions made
- Pick one system (Zeeguu-API) instead of both — report is only 3-4 pages
- Module view as primary viewpoint, evolutionary analysis as secondary
- Start from course Colab notebooks approach, adapt into own scripts
- Use AST over regex for reliability (as recommended in Lecture 1)
- Use depth 1 for the main architectural view, depth 2 for zooming in

- **Script 3: churn_analysis.py** — evolutionary hotspots (DONE)
  - File-level: article.py (142), user.py (132), article_downloader.py (114) are top hotspots
  - Depth 1: core (3448) vs api (1394) — 70% of work happens in core
  - Depth 2: core.model (1508) is the mega-hotspot, core.audio_lessons (139) and core.llm_services (94) are active new features

- **Script 4: logical_coupling.py** — implicit dependencies (DONE)
  - File-level: elastic_recommender <-> elastic_query_builder (35) is top pair — implicit contract
  - friends endpoint <-> friend model (34) — cross-layer coupling
  - Depth 1: api <-> core dominates (1936)
  - Depth 2: core.model appears in almost every pair. core.model <-> core.user_statistics (466) is surprisingly strong
  - Finding: core.sql tightly coupled to core.model (152) — raw SQL queries depend on model structure

### Key findings so far
- core.model is the gravitational center — highest churn, most dependencies, most coupling
- api->core is the main artery (322 imports, 1936 co-changes)
- core->api (weight 1) is a small dependency going the "wrong" direction
- core.user_statistics is unexpectedly tightly coupled to core.model
- elastic_recommender and elastic_query_builder have strong implicit coupling

### Still to do
- Generate visualisations (module graph with churn overlay)
- Write methodology, results, and discussion sections
