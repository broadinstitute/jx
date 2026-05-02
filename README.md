# jx — JUMP eXplore

An experiment in agent-driven scientific data exploration, built around [JUMP Cell Painting](https://jump-cellpainting.broadinstitute.org/) — the largest public morphological profiling dataset (~116K compounds, ~8K CRISPR knockouts, ~15K gene overexpressions, 1.6 billion cells).

## The hypothesis

jx is a catalog of real JUMP analyses - working [marimo](https://marimo.io) notebooks, each embodying an actual use case. Each notebook is both a runnable demonstration and a source of pure functions that other notebooks can [import and reuse](https://docs.marimo.io/guides/reusing_functions/) directly. Three properties make this work for agent composition:

- **Cumulative DAG.** Later notebooks import functions from earlier ones. Notebook 7 depends on notebooks 1-6, and custom analyses chain further.
- **Live environment.** [marimo-pair](https://github.com/marimo-team/marimo-pair) gives the agent kernel feedback while composing - running code, inspecting outputs, adjusting - rather than a write-build-inspect loop against a static CI artifact.
- **Data alongside code.** Each cell ships both the code and its output: computed values, dataframe heads, plots rendered from real JUMP data. An agent sees what functions produce, not just what they accept - composition is grounded in concrete shapes and values, not type hints.

The underlying libraries (parquet, polars, duckdb, pooch, [jump-portrait](https://github.com/broadinstitute/monorepo/tree/main/libs/jump_portrait)) already exist; what's missing is how to *analyze* this dataset - its conventions, query patterns, and how you get from raw profiles to biological conclusions. Some of this is uniquely JUMP lore. The cosine similarity matrices are partitioned by modality, so a query of a compound JCP2022 ID against the CRISPR matrix silently returns nothing - the kind of thing you learn by hitting it, rather than from polars docs. Helper functions in the catalog sit close to the underlying APIs on purpose - an agent composing a new analysis sees polars, duckdb, and pooch primitives in use, directly, instead of being hidden behind a wrapper.

A thin skill file tells an AI agent (Claude Code + marimo-pair) what's in the catalog and how to compose from it. Given a new biological question, the agent picks relevant notebooks, composes their reusable functions into a new notebook, generates any custom glue code, executes it in a live kernel, and hands back a self-contained, re-runnable result. The catalog grows as new analyses are added. The skill stays thin on purpose.

If this works for JUMP, the pattern transfers: new dataset = new catalog + new skill, same machinery.

How far does it go? A library is pre-factored knowledge - someone decided what was worth extracting, and everyone else reuses those decisions. A catalog of worked examples leaves the factoring undone. [nbdev](https://nbdev.fast.ai/) answered a version of this for deep learning: notebooks as source of truth, library exported from them. But a human still decided what to export. The jx bet is that agents composing from examples can defer that step - maybe indefinitely. Whether packaging still becomes necessary at scale, or stops being necessary at all, is open.

## The catalog

An initial starter pack of six notebooks adapted from [JUMP-Hub](https://github.com/broadinstitute/jump_hub), covering the building blocks of JUMP analysis: profile retrieval, metadata annotation, morphological activity (mAP), Cell Painting image display, similarity search, and gene annotation. A seventh notebook (`nb07_compound_neighborhood.py`) is the demo vignette — given a compound of interest, find what's morphologically similar in JUMP, annotate the neighbors with targets, and show the images side by side. It composes the first six and runs end to end.

Each notebook ships with a committed session snapshot under [`notebooks/__marimo__/session/`](notebooks/__marimo__/session/) so the molab preview renders cell outputs (plots, tables, dropdowns) without re-executing. Click a badge to view the rendered notebook in [molab](https://docs.marimo.io/guides/molab/), or fork it from there.

| Notebook | Role | Preview |
|---|---|---|
| [`nb01_retrieve_profiles.py`](notebooks/nb01_retrieve_profiles.py) | Pull JUMP profile parquets via the manifest | [![Open in molab](https://marimo.io/molab-shield.svg)](https://molab.marimo.io/github/broadinstitute/jx/blob/main/notebooks/nb01_retrieve_profiles.py) |
| [`nb02_add_metadata.py`](notebooks/nb02_add_metadata.py) | Annotate JCP2022 IDs with compound/gene metadata | [![Open in molab](https://marimo.io/molab-shield.svg)](https://molab.marimo.io/github/broadinstitute/jx/blob/main/notebooks/nb02_add_metadata.py) |
| [`nb03_calculate_activity.py`](notebooks/nb03_calculate_activity.py) | Per-perturbation morphological activity (mAP) | [![Open in molab](https://marimo.io/molab-shield.svg)](https://molab.marimo.io/github/broadinstitute/jx/blob/main/notebooks/nb03_calculate_activity.py) |
| [`nb04_display_images.py`](notebooks/nb04_display_images.py) | Pull and display Cell Painting images from S3 | [![Open in molab](https://marimo.io/molab-shield.svg)](https://molab.marimo.io/github/broadinstitute/jx/blob/main/notebooks/nb04_display_images.py) |
| [`nb05_explore_similarity.py`](notebooks/nb05_explore_similarity.py) | Cosine similarity neighbors over Zenodo matrices | [![Open in molab](https://marimo.io/molab-shield.svg)](https://molab.marimo.io/github/broadinstitute/jx/blob/main/notebooks/nb05_explore_similarity.py) |
| [`nb06_query_genes.py`](notebooks/nb06_query_genes.py) | Resolve gene symbols and pull annotations | [![Open in molab](https://marimo.io/molab-shield.svg)](https://molab.marimo.io/github/broadinstitute/jx/blob/main/notebooks/nb06_query_genes.py) |
| [`nb07_compound_neighborhood.py`](notebooks/nb07_compound_neighborhood.py) | End-to-end: compound -> neighbors -> targets -> images | [![Open in molab](https://marimo.io/molab-shield.svg)](https://molab.marimo.io/github/broadinstitute/jx/blob/main/notebooks/nb07_compound_neighborhood.py) |

A parallel SQL catalog ([`queries/`](queries/)) holds self-contained [ggsql](https://ggsql.org) files that answer single-chart questions against the canonical JUMP metadata DuckDB — plate/well/perturbation demographics, source breakdowns, joins across the metadata schema. Each `q*.gsql` file is one chart with no Python in the loop; the [`compose-query`](.claude/skills/compose-query/SKILL.md) skill teaches the agent which surface to pick (notebooks for Python-glue analyses, queries for pure-SQL questions).

## Getting started

Clone this repo, open [Claude Code](https://code.claude.com/docs) inside the clone, and ask: *help me get started*. The `getting-started` skill (at [`.claude/skills/getting-started/SKILL.md`](.claude/skills/getting-started/SKILL.md)) installs prereqs ([uv](https://docs.astral.sh/uv/) and the [marimo-pair](https://github.com/marimo-team/marimo-pair) skill), launches the demo notebook (`nb07_compound_neighborhood.py`) in a live marimo kernel, and hands off to the `compose-notebook` skill so you can compose analyses against the catalog. Claude Code auto-loads `.claude/skills/` from the working directory, so no separate install step is needed.

The skill file is the canonical setup doc. Read it directly if you want to run the commands by hand without the agent.

> **Why no `npx skills add broadinstitute/jx`?** The skills here reference in-repo paths (the notebook catalog, `queries/data/jump_metadata.duckdb`, rendered SVGs) and only work alongside that substrate — installing the markdown into an unrelated project leaves the skill with dangling pointers. Clone the repo; that's the install.

## License

BSD 3-Clause — see [LICENSE](LICENSE).

## Status

Active experiment by a team at the Broad Institute. Watch this repo for periodic updates as the hypothesis develops.

## Archived branches

- **`broad-jump-wasm`** — static [ggsql-wasm](https://ggsql.org/wasm/) explorer over JUMP metadata parquets, shipped then reverted from `main` ([PR #4](https://github.com/broadinstitute/jx/pull/4)). Preserved as a pointer to the pre-revert state; ggsql is now a separate track from the jx notebook catalog. Check out the branch to resurrect the demo.
