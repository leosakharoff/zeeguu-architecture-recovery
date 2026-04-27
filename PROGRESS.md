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
- **Script 2: abstract_modules.py** — module-level abstraction (IN PROGRESS)
  - Aggregates file-level deps along folder hierarchy
  - Configurable depth (depth 1 = top-level, depth 2 = sub-packages)
  - Waiting to run and compare depth 1 vs depth 2

### Decisions made
- Pick one system (Zeeguu-API) instead of both — report is only 3-4 pages
- Module view as primary viewpoint, evolutionary analysis as secondary
- Start from course Colab notebooks approach, adapt into own scripts
- Use AST over regex for reliability (as recommended in Lecture 1)

### Still to do
- Run abstract_modules.py at depth 1 and 2
- Script 3: Churn & hotspot analysis
- Script 4: Logical coupling analysis
- Generate visualisations
- Write methodology, results, and discussion sections
