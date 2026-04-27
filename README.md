# Zeeguu Architecture Recovery

Individual assignment for Software Architecture (KSSOARC2KU), ITU Copenhagen, Spring 2026.

Recovers the architecture of [Zeeguu-API](https://github.com/zeeguu/API) using static import analysis and evolutionary analysis from Git history.

## Scripts

- `scripts/extract_imports.py` — AST-based import extraction
- `scripts/abstract_modules.py` — aggregate file deps to module level
- `scripts/churn_analysis.py` — churn & hotspots from Git history
- `scripts/logical_coupling.py` — co-change / logical coupling analysis
- `scripts/visualise.py` — generate polymetric module view figures

## How to run

Clone [Zeeguu-API](https://github.com/zeeguu/API) into `zeeguu-api/`, then:

```bash
python scripts/extract_imports.py
python scripts/abstract_modules.py --depth 1
python scripts/churn_analysis.py
python scripts/logical_coupling.py
python scripts/visualise.py
```

Output goes to `scripts/data/` (JSON) and `report/figures/` (PNG).
