# compose-notebook

A Claude Code skill for composing marimo notebooks from the jx JUMP Cell
Painting catalog.

## Install

From any project that works with JUMP Cell Painting data:

```bash
# One-liner: clone into your project's .claude/skills/
git clone https://github.com/broadinstitute/jx.git /tmp/jx \
  && mkdir -p .claude/skills \
  && cp -r /tmp/jx/.claude/skills/compose-notebook .claude/skills/ \
  && rm -rf /tmp/jx

# Or if you already have the repo cloned locally:
cp -r /path/to/jx/.claude/skills/compose-notebook .claude/skills/
```

The skill is automatically discovered by Claude Code once the `SKILL.md`
file is in `.claude/skills/compose-notebook/`.

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
