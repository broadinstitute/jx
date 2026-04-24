# compose-notebook

A Claude Code skill for composing marimo notebooks from the jx JUMP Cell
Painting catalog.

## Install

Via [skills.sh](https://skills.sh):

```bash
npx skills add broadinstitute/jx --skill compose-notebook
```

Or pull all three jx skills at once with `--skill '*'`.

## What it does

Triggers when you ask Claude to build a notebook that touches JUMP
profiles, cosine similarity, perturbation metadata, Cell Painting images,
or morphological activity. It knows the full catalog (nb01–nb06) and
composes new notebooks from existing `@app.function` helpers instead of
writing queries from scratch.

Includes a "General marimo patterns" section with non-project-specific
best practices for `with app.setup`, plotly dark themes, default
selections, DuckDB in marimo cells, and more.

## Requirements

- marimo >= 0.25 (for `with app.setup` support)
- The jx notebook catalog in `notebooks/nb*.py`
