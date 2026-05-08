# jx — JUMP eXplore

An experiment in agent-driven scientific data exploration, built around [JUMP Cell Painting](https://jump-cellpainting.broadinstitute.org/) — the largest public morphological profiling dataset (~116K compounds, ~8K CRISPR knockouts, ~15K gene overexpressions, 1.6 billion cells).

## What this is

jx is a curated catalog of [marimo](https://marimo.io) vignettes for JUMP analysis, plus a thin skill that lets an agent compose new analyses from them. Each vignette is both a runnable demonstration and a source of pure functions other notebooks can [import and reuse](https://docs.marimo.io/guides/reusing_functions/) directly. Given a new biological question, the agent picks relevant vignettes, composes their functions into a new notebook, executes it in a live kernel, and hands back a self-contained, re-runnable result.

For the hypothesis, the catalog walkthrough, and the project roadmap, see **[PLAN.md](PLAN.md)**.

## The catalog

Six vignettes adapted from [JUMP-Hub](https://github.com/broadinstitute/jump_hub), covering the building blocks of JUMP analysis: profile retrieval, metadata annotation, morphological activity (mAP), Cell Painting image display, similarity search, and gene annotation. A seventh notebook (`nb07_compound_neighborhood.py`) is the composition demo — given a compound of interest, find what's morphologically similar, annotate the neighbors with targets, and show the images side by side. It composes the first six and runs end to end.

A parallel SQL surface ([`queries/`](queries/)) holds self-contained [ggsql](https://ggsql.org) files that answer single-chart questions against the canonical JUMP metadata DuckDB. The [`compose-query`](.claude/skills/compose-query/SKILL.md) skill teaches the agent which surface to pick (notebooks for Python-glue analyses, queries for pure-SQL questions).

## Getting started

Clone this repo, open [Claude Code](https://code.claude.com/docs) inside the clone, and ask: *help me get started*. The `getting-started` skill (at [`.claude/skills/getting-started/SKILL.md`](.claude/skills/getting-started/SKILL.md)) installs prereqs ([uv](https://docs.astral.sh/uv/) and the [marimo-pair](https://github.com/marimo-team/marimo-pair) skill), launches the demo notebook in a live marimo kernel, and hands off to the `compose-notebook` skill so you can compose analyses against the catalog. Claude Code auto-loads `.claude/skills/` from the working directory, so no separate install step is needed.

The skill file is the canonical setup doc. Read it directly if you want to run the commands by hand without the agent.

> **Why no `npx skills add broadinstitute/jx`?** The skills here reference in-repo paths (the notebook catalog, `queries/data/jump_metadata.duckdb`, rendered SVGs) and only work alongside the rest of the repo — installing the markdown into an unrelated project leaves the skill with dangling pointers. Clone the repo; that's the install.

## License

BSD 3-Clause — see [LICENSE](LICENSE).

## Status

Active experiment by a team at the Broad Institute. See [PLAN.md](PLAN.md) for current direction.
