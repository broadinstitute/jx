# AGENTS.md - jx

Project-specific guidance for agents working in this repository. This is the
primary repo for the VOA catalog pattern: it contains the public JUMP Cell
Painting catalog, the project plan, release metadata, and the cross-instance
contract for `jx`, `fgx`, `prx`, and `dmx`.

`README.md` is the human entry point. `PLAN.md` is the planning and paper
source of truth. The skills under `.claude/skills/` are the operational entry
points: `getting-started` for first-run setup, `compose-notebook` for marimo
composition, and `compose-query` for ggsql queries.

## Validation Rule

After composing or editing any notebook in `notebooks/`, launch it in a
marimo sandbox kernel and run all cells before reporting the task complete.
Static checks do not catch wrong outputs, empty tables, stale endpoint
assumptions, broken plots, or sign-convention mistakes.

Minimal launch:

```bash
PORT=$(python -c "import socket; s=socket.socket(); s.bind(('127.0.0.1',0)); print(s.getsockname()[1])")
env -u PYTHONPATH uvx marimo edit --sandbox --headless --no-token --port $PORT notebooks/nbNN_*.py
```

For notebooks that can export reliably, refresh the molab session snapshot:

```bash
env -u PYTHONPATH uvx marimo export session --sandbox notebooks/nbNN_*.py
```

Then run static checks:

```bash
uvx ruff format --check notebooks/
uvx ruff check notebooks/
uvx marimo check notebooks/*.py
```

## Architecture

- Catalog over library. Helpers live as `@app.function` cells in numbered
  notebooks. Later notebooks import from earlier notebooks by adding
  `notebooks/` to `sys.path`.
- `jx` has two surfaces: marimo notebooks for Python-glue analyses and
  `queries/` ggsql files for pure metadata queries.
- Keep notebook helpers close to data primitives: `polars`, `duckdb`,
  `broad-babel`, `jump-portrait`, and small parsing or plotting functions.
- Cache large remote artifacts under `~/.cache/jx` or `JX_CACHE`; do not commit
  downloaded data.
- Do not add a Python package until repeated cross-notebook imports make the
  notebook-as-library pattern painful.

## When the Question Fits the Catalog

Almost every JUMP analysis request should start from the catalog:

- profile retrieval -> `nb01_retrieve_profiles`
- metadata annotation -> `nb02_add_metadata`
- activity / mAP -> `nb03_calculate_activity`
- Cell Painting image display -> `nb04_display_images`
- morphological similarity -> `nb05_explore_similarity`
- gene annotation -> `nb06_query_genes`
- compound-neighborhood composition demo -> `nb07_compound_neighborhood`

Read `.claude/skills/compose-notebook/SKILL.md` before writing new notebook
code. For pure SQL + chart questions against JUMP metadata, use
`.claude/skills/compose-query/SKILL.md` instead.
