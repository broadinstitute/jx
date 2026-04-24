# jx — JUMP eXplore

An experiment in agent-driven scientific data exploration, built around [JUMP Cell Painting](https://jump-cellpainting.broadinstitute.org/) — the largest public morphological profiling dataset (~116K compounds, ~8K CRISPR knockouts, ~15K gene overexpressions, 1.6 billion cells).

**Try it in 30 seconds (no install):** <https://broadinstitute.github.io/jx/broad-jump/> — a browser-native query surface over JUMP metadata, running [ggsql](https://ggsql.org/wasm/) compiled to WebAssembly. Pick an example query from the sidebar and watch the chart render locally. Good for the catalog-level questions ("how many compounds per source", "which plate types at which center"); for morphological analysis that touches profiles, similarity matrices, or images, use the marimo catalog below.

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

A parallel SQL catalog ([`queries/`](queries/)) holds self-contained [ggsql](https://ggsql.org) files that answer single-chart questions against the canonical JUMP metadata DuckDB — plate/well/perturbation demographics, source breakdowns, joins across the metadata schema. Each `q*.gsql` file is one chart with no Python in the loop; the [`compose-query`](.claude/skills/compose-query/SKILL.md) skill teaches the agent which surface to pick (notebooks for Python-glue analyses, queries for pure-SQL questions).

## broad-jump — a metadata-only companion surface

Alongside the catalogs sits [`broad-jump/`](broad-jump/), a static web demo that runs ggsql (SQL + grammar-of-graphics) in the browser against the 11 JUMP metadata tables flattened to SNAPPY parquet shards on `cellpainting-gallery` (public S3, CORS + range-request enabled). Live at <https://broadinstitute.github.io/jx/broad-jump/>. Deploys on every push that touches `broad-jump/**` via `.github/workflows/deploy-broad-jump.yml`.

The agent-facing counterpart is the [`broad-jump` skill](.claude/skills/broad-jump/SKILL.md), which teaches a Claude Code session to compose new SQL or ggsql queries against the same data (using the local DuckDB at `queries/data/jump_metadata.duckdb` or the S3 parquets), points at [`broad-jump/src/examples.ts`](broad-jump/src/examples.ts) as a pre-vetted vignette library, and enforces the JUMP-specific gotchas the browser UI already hides (modality casing, plate-type casing, `compound_source` being many-to-many).

Deliberately metadata-only, and overlapping in scope with `queries/`. The split is by runtime: `queries/` is a committed file-on-disk gallery rendered via `just render`; `broad-jump/` is the browser-runnable view of the same data shape. When a question needs morphological features, images, or similarity matrices, stop and use the marimo catalog — neither SQL surface has any of that.

## Getting started

Clone this repo, open [Claude Code](https://code.claude.com/docs) inside the clone, and ask: *help me get started*. The `getting-started` skill (at [`.claude/skills/getting-started/SKILL.md`](.claude/skills/getting-started/SKILL.md)) installs prereqs ([uv](https://docs.astral.sh/uv/) and the [marimo-pair](https://github.com/marimo-team/marimo-pair) plugin), launches the demo notebook (`nb07_compound_neighborhood.py`) in a live marimo kernel, and hands off to the `compose-notebook` skill so you can compose analyses against the catalog.

The skill file is the canonical setup doc. Read it directly if you want to run the commands by hand without the agent.

## License

BSD 3-Clause — see [LICENSE](LICENSE).

## Status

Active experiment by a team at the Broad Institute. Watch this repo for periodic updates as the hypothesis develops.
