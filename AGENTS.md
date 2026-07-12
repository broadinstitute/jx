# AGENTS.md - jx

Project-specific guidance for agents working in this repository.
This is the primary repo for the VOA catalog pattern: it contains the public JUMP Cell Painting catalog, the project plan, release metadata, and the cross-instance contract for `jx`, `fgx`, `prx`, and `dmx`.

`README.md` is the human entry point.
`PLAN.md` is the planning and paper source of truth.
This catalog uses the shared [vignette-catalog-skills](https://github.com/carpenter-singh-lab/vignette-catalog-skills) (`vignette-catalog-setup` for first-run setup, `vignette-catalog-compose-notebook` for marimo composition); its specifics live in `catalog.toml`.
Those are installed via `npx skills add carpenter-singh-lab/vignette-catalog-skills --agent claude-code -y`, recorded in the tracked `skills-lock.json`, but **not vendored** (`.claude/skills/*` is gitignored) - restore them on a fresh clone.
The repo-local `compose-query` skill (ggsql; no upstream counterpart) stays tracked under `.claude/skills/compose-query/` for the parallel `queries/` catalog.

## Launching notebooks

Always use `--sandbox` so the PEP 723 inline metadata is provisioned:

```bash
uvx marimo edit --sandbox notebooks/nbNN_*.py
```

Do not improvise alternative launch commands.
`--sandbox` is what makes `uvx marimo` read each notebook's `/// script` dependency block; without it every notebook fails with `ModuleNotFoundError`.

## Validation Rule

After composing or editing any notebook in `notebooks/`, launch it in a marimo sandbox kernel and run all cells before reporting the task complete.
Static checks do not catch wrong outputs, empty tables, stale endpoint assumptions, broken plots, or sign-convention mistakes.

Minimal launch:

```bash
PORT=$(python -c "import socket; s=socket.socket(); s.bind(('127.0.0.1',0)); print(s.getsockname()[1])")
env -u PYTHONPATH uvx marimo edit --sandbox --headless --no-token --port $PORT notebooks/nbNN_*.py
```

Then run static checks:

```bash
uvx ruff check notebooks/
uvx ruff format notebooks/
uvx marimo check notebooks/*.py
```

**Then, last, refresh the molab session snapshot** for any notebook whose source changed in this task:

```bash
env -u PYTHONPATH uvx marimo export session --sandbox notebooks/nbNN_*.py
```

Order matters.
Session snapshots store a `code_hash` per cell, and molab attaches the stored output only when the snapshot hash matches the source cell.
Any later edit to the notebook source - including a `ruff format` whitespace pass - shifts every `code_hash` and silently strips outputs in the public molab preview.
Always regenerate snapshots **after** the final formatter / source edit, and commit the regenerated `.json` files in the same change that touched the `.py` files.

## Architecture

- Catalog over library.
  Helpers live as `@app.function` cells in numbered notebooks.
  Later notebooks import from earlier notebooks by adding `notebooks/` to `sys.path`.
- `jx` has two surfaces: marimo notebooks for Python-glue analyses and `queries/` ggsql files for pure metadata queries.
- Keep notebook helpers close to data primitives: `polars`, `duckdb`, `broad-babel`, `jump-portrait`, and small parsing or plotting functions.
- Cache large remote artifacts under `~/.cache/jx` or `JX_CACHE`; do not commit downloaded data.
- Do not add a Python package until repeated cross-notebook imports make the notebook-as-library pattern painful.

## Conventions

- Prose in `.md` files uses semantic line breaks: one sentence per line, no hard wrapping at a column count.
  Markdown collapses single newlines inside a paragraph, so the rendered output is unchanged, but diffs stay local to the edited sentence instead of re-flowing every line below it.
  Applies to `AGENTS.md`, `.claude/skills/**/SKILL.md`, and any other prose-heavy markdown we revise often.
  `ruff`'s `line-length = 120` setting is for Python only; there is no column rule on markdown.

## When the Question Fits the Catalog

Almost every JUMP analysis request should start from the catalog:

- profile retrieval -> `nb01_retrieve_profiles`
- metadata annotation -> `nb02_add_metadata`
- activity / mAP -> `nb03_calculate_activity`
- Cell Painting image display -> `nb04_display_images`
- morphological similarity -> `nb05_explore_similarity`
- gene annotation -> `nb06_query_genes`
- compound-neighborhood composition demo -> `nb07_compound_neighborhood`

Read the installed `vignette-catalog-compose-notebook` skill (and `catalog.toml`'s `[[vignette]]` table) before writing new notebook code.
For pure SQL + chart questions against JUMP metadata, use the repo-local `.claude/skills/compose-query/SKILL.md` instead.
