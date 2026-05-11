# jx — JUMP eXplore

An experiment in agent-driven scientific data exploration, built around [JUMP Cell Painting](https://jump-cellpainting.broadinstitute.org/) — the largest public morphological profiling dataset (~116K compounds, ~8K CRISPR knockouts, ~15K gene overexpressions, 1.6 billion cells).

jx is a curated catalog of [marimo](https://marimo.io) vignettes for JUMP analysis, plus a thin skill that lets an agent compose new analyses from them.
Each vignette is both a runnable demonstration and a source of pure functions other notebooks can [import and reuse](https://docs.marimo.io/guides/reusing_functions/) directly.
Given a new biological question, the agent picks relevant vignettes, composes their functions into a new notebook, executes it in a live kernel, and hands back a self-contained, re-runnable result.

For the hypothesis, the catalog walkthrough, and the project roadmap, see [PLAN.md](PLAN.md).

## The catalog

Each notebook ships with a committed session snapshot under [`notebooks/__marimo__/session/`](notebooks/__marimo__/session/) so the molab preview renders cell outputs without re-executing.

Six vignettes adapted from [JUMP-Hub](https://github.com/broadinstitute/jump_hub), covering the building blocks of JUMP analysis: profile retrieval, metadata annotation, morphological activity (mAP), Cell Painting image display, similarity search, and gene annotation.
A seventh notebook (`nb07_compound_neighborhood.py`) is the composition demo — given a compound of interest, find what's morphologically similar, annotate the neighbors with targets, and show the images side by side.
It composes the first six and runs end to end.

| Notebook | Role | Preview |
|---|---|---|
| [`nb01_retrieve_profiles.py`](notebooks/nb01_retrieve_profiles.py) | Pull JUMP morphological profiles by perturbation | [![Open in molab](https://marimo.io/molab-shield.svg)](https://molab.marimo.io/github/broadinstitute/jx/blob/main/notebooks/nb01_retrieve_profiles.py) |
| [`nb02_add_metadata.py`](notebooks/nb02_add_metadata.py) | Annotate profiles with plate, well, and perturbation metadata | [![Open in molab](https://marimo.io/molab-shield.svg)](https://molab.marimo.io/github/broadinstitute/jx/blob/main/notebooks/nb02_add_metadata.py) |
| [`nb03_calculate_activity.py`](notebooks/nb03_calculate_activity.py) | Score morphological activity via mAP (copairs) | [![Open in molab](https://marimo.io/molab-shield.svg)](https://molab.marimo.io/github/broadinstitute/jx/blob/main/notebooks/nb03_calculate_activity.py) |
| [`nb04_display_images.py`](notebooks/nb04_display_images.py) | Fetch and display Cell Painting site images | [![Open in molab](https://marimo.io/molab-shield.svg)](https://molab.marimo.io/github/broadinstitute/jx/blob/main/notebooks/nb04_display_images.py) |
| [`nb05_explore_similarity.py`](notebooks/nb05_explore_similarity.py) | Cosine-similarity search over JUMP profiles | [![Open in molab](https://marimo.io/molab-shield.svg)](https://molab.marimo.io/github/broadinstitute/jx/blob/main/notebooks/nb05_explore_similarity.py) |
| [`nb06_query_genes.py`](notebooks/nb06_query_genes.py) | Translate gene / compound identifiers via `broad-babel` | [![Open in molab](https://marimo.io/molab-shield.svg)](https://molab.marimo.io/github/broadinstitute/jx/blob/main/notebooks/nb06_query_genes.py) |
| [`nb07_compound_neighborhood.py`](notebooks/nb07_compound_neighborhood.py) | Composition demo: compound -> similar perturbations -> annotated neighborhood with images | [![Open in molab](https://marimo.io/molab-shield.svg)](https://molab.marimo.io/github/broadinstitute/jx/blob/main/notebooks/nb07_compound_neighborhood.py) |

A parallel SQL surface ([`queries/`](queries/)) holds self-contained [ggsql](https://ggsql.org) files that answer single-chart questions against the canonical JUMP metadata DuckDB.
The [`compose-query`](.claude/skills/compose-query/SKILL.md) skill teaches the agent which surface to pick (notebooks for Python-glue analyses, queries for pure-SQL questions).

Related public catalogs of the same pattern: [fgx](https://github.com/broadinstitute/fgx) for FinnGenie human genetics, [prx](https://github.com/broadinstitute/prx) for PROSPECT chemical genetics, and [dmx](https://github.com/broadinstitute/dmx) for DepMap Breadbox.

## Getting started

Clone this repo, open [Claude Code](https://code.claude.com/docs) inside it, and ask: *help me get started*.
The `getting-started` skill installs prereqs ([uv](https://docs.astral.sh/uv/) and the [marimo-pair](https://github.com/marimo-team/marimo-pair) skill), launches `nb07_compound_neighborhood` in a live marimo kernel, and hands off to the `compose-notebook` skill for the actual analysis.

If you prefer to run setup by hand:

```bash
uv --version  # or: curl -LsSf https://astral.sh/uv/install.sh | sh
AGENT=claude-code  # or: codex
npx skills add marimo-team/marimo-pair -g --agent "$AGENT" -y
uvx marimo edit --sandbox notebooks/nb07_compound_neighborhood.py
```

There is no `npx skills add broadinstitute/jx` flow: the skills reference in-repo paths (the notebook catalog, `queries/data/jump_metadata.duckdb`, rendered SVGs) and only work alongside the rest of the repo, so installing the markdown into an unrelated project leaves the skill with dangling pointers.
Clone the repo to install.

## License

BSD 3-Clause — see [LICENSE](LICENSE).
