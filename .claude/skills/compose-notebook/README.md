# compose-notebook

A Claude Code skill for composing marimo notebooks from the jx JUMP Cell
Painting catalog.

## Install

### Via Claude CLI (recommended)

```bash
# Add the marketplace
claude plugin marketplace add broadinstitute/jx

# Install the skill
claude plugin install compose-notebook@jx
```

### Manual

```bash
cp -r /path/to/jx/.claude/skills/compose-notebook .claude/skills/
```

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
