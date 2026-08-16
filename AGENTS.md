# AGENTS.md - jx

Project-specific guidance for agents working in this repository.
This is the primary repo for the VOA catalog pattern: it contains the public JUMP Cell Painting catalog, the project plan, release metadata, and the cross-instance contract for `jx`, `fgx`, `prx`, and `dmx`.

`README.md` is the human entry point.
`PLAN.md` is the planning and paper source of truth.
This catalog uses the shared [vignette-catalog-skills](https://github.com/carpenter-singh-lab/vignette-catalog-skills), with `vignette-catalog-compose-notebook` handling setup, execution, and composition; its specifics live in `catalog.toml`.
Third-party skills are recorded in the tracked `skills-lock.json`, but **not vendored** (`.claude/skills/*` and `.agents/` are gitignored).
After cloning, run these exact commands from the repo root:

```bash
npx skills@1.5.20 add carpenter-singh-lab/vignette-catalog-skills -s vignette-catalog-compose-notebook -s vignette-catalog-scaffold -a claude-code -a codex -y
npx skills@1.5.20 add marimo-team/skills -s marimo-notebook -a claude-code -a codex -y
npx skills@1.5.20 add marimo-team/marimo-pair -s marimo-pair -a claude-code -a codex -y
```

The lock records observed hashes but not agent targets or immutable revisions for these plain sources, so it is a drift record rather than a reproducible installer input.
Replay the same commands to update, then inspect `git diff -- skills-lock.json` before committing an intentional upstream change.
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

Then run the installed skill's final gate:

```bash
VALIDATE=$(ls .agents/skills/vignette-catalog-compose-notebook/scripts/validate-notebook.sh .claude/skills/vignette-catalog-compose-notebook/scripts/validate-notebook.sh 2>/dev/null | head -1)
bash "$VALIDATE" notebooks/nbNN_*.py
```

The validator runs stable static checks, formatting, cold execution, and refreshes the molab session snapshot last.
Session snapshots store a `code_hash` per cell, and molab attaches the stored output only when the snapshot hash matches the source cell.
Run it after the final source edit, and commit regenerated `.json` files with changed notebooks.

## Architecture

- Catalog over library.
  Helpers live as `@app.function` cells in numbered notebooks.
  Later notebooks import from earlier notebooks by adding `notebooks/` to `sys.path`.
- `jx` has two surfaces: marimo notebooks for Python-glue analyses and `queries/` ggsql files for pure metadata queries.
- Keep notebook helpers close to data primitives: `polars`, `duckdb`, `broad-babel`, `jump-portrait`, and small parsing or plotting functions.
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
- mixed-modality panel activity and similarity -> `nb08_panel_similarity`

Read the installed `vignette-catalog-compose-notebook` skill (and `catalog.toml`'s `[[vignette]]` table) before writing new notebook code.
For pure SQL + chart questions against JUMP metadata, use the repo-local `.claude/skills/compose-query/SKILL.md` instead.

## jx-specific gotchas

These do not live in the shared skill (the generic marimo/molab/PYTHONPATH ones do).

- **`jump_portrait` + `broad_babel` versions must stay compatible.** The old `jump-portrait==0.1.0` / `broad-babel==0.1.31` combination is broken; current cold runs pass with `jump-portrait==0.1.1` and `broad-babel==0.1.31`.
- **Treat matrix caching as an explicit choice.** Nb07 reads a preseeded `JX_CACHE` entry but does not populate it, while nb08 uses DuckDB `httpfs` and does not use `JX_CACHE`.
  The CRISPR, ORF, and compound matrices are about 228 MiB, 813 MiB, and 46 GiB, so project columns remotely and never seed the compound matrix casually.
