# jx — JUMP eXplore

An experiment in agent-driven scientific data exploration, built around [JUMP Cell Painting](https://jump-cellpainting.broadinstitute.org/) — the largest public morphological profiling dataset (~116K compounds, ~8K CRISPR knockouts, ~15K gene overexpressions, 1.6 billion cells).

## The hypothesis

jx is a catalog of real JUMP analyses — working [marimo](https://marimo.io) notebooks, each embodying an actual use case. The underlying libraries (parquet, polars, duckdb, pooch, [jump-portrait](https://github.com/jump-cellpainting/jump-portrait)) already exist; what's missing is how to *analyze* this dataset — its conventions, query patterns, common gotchas, and the compositional moves that turn raw profiles into biological conclusions. The catalog fills that gap. Each notebook is both a runnable demonstration and a source of pure functions that other notebooks can [import and reuse](https://docs.marimo.io/guides/reusing_functions/) directly. Helper functions sit close to the underlying APIs on purpose — an agent composing a new analysis sees polars, duckdb, and pooch primitives in use, not a wrapper that hides them.

A thin skill file tells an AI agent (Claude Code + [marimo-pair](https://github.com/marimo-team/marimo-pair)) what's in the catalog and how to compose from it. Given a new biological question, the agent picks relevant notebooks, composes their reusable functions into a new notebook, generates any custom glue code, executes it in a live kernel, and hands back a self-contained, re-runnable result. The catalog grows as new analyses are added. The skill stays thin on purpose.

Three properties make this work for agent composition:

- **Cumulative DAG.** Later notebooks import functions from earlier ones. The catalog is not a flat gallery of independent examples — notebook 7 depends on notebooks 1–6, and custom analyses chain further.
- **Live environment.** marimo-pair gives the agent kernel feedback while composing — running code, inspecting outputs, adjusting — rather than a write-build-inspect loop against a static CI artifact.
- **Data alongside code.** Each cell ships both the code and its output: computed values, dataframe heads, plots rendered from real JUMP data. An agent sees what functions produce, not just what they accept — composition is grounded in concrete shapes and values, not type hints.

If this works for JUMP, the pattern transfers: new dataset = new catalog + new skill, same machinery.

How far does this pattern go? At a starter pack of six notebooks plus a demo vignette — jx's current scope — a catalog of worked examples beats building a JUMP-specific wrapper library. The conventional software-engineering answer says: at dozens of notebooks with multiple contributors, factoring shared helpers into a package becomes necessary. [fast.ai](https://www.fast.ai/) and [nbdev](https://nbdev.fast.ai/) did exactly this at scale for deep learning.

But that answer assumes human maintainers. In an agentic era — thousands of agents running experiments, chasing hypotheses, and refactoring the catalog itself — the scale at which a library becomes necessary may be much higher, or may not be a fixed boundary at all. If agents can curate the resource and keep the DAG coherent, packaging becomes a choice rather than a requirement, and an older question reopens: what is a library *for*, when agents rather than humans are the primary maintainers of a growing body of analysis?

## The catalog

An initial starter pack of six notebooks adapted from [JUMP-Hub](https://github.com/jump-cellpainting/jump-hub), covering the building blocks of JUMP analysis: profile retrieval, metadata annotation, morphological activity (mAP), Cell Painting image display, similarity search, and gene annotation. A seventh notebook (`nb07_compound_neighborhood.py`) is the demo vignette — given a compound of interest, find what's morphologically similar in JUMP, annotate the neighbors with targets, and show the images side by side. It composes the first six and runs end to end.

## Getting started

Requires Python ≥ 3.11 and [uv](https://docs.astral.sh/uv/).

Each notebook is a self-contained [PEP 723](https://peps.python.org/pep-0723/) script — dependencies are declared inline.

**Local machine:**
```bash
git clone https://github.com/broadinstitute/jx && cd jx
uvx marimo edit --sandbox notebooks/nb07_compound_neighborhood.py
```

`--sandbox` reads each notebook's PEP 723 header and provisions an isolated venv on the fly - no manual `uv sync` needed. The first launch takes ~2 minutes while deps install; subsequent launches are instant. To browse the catalog instead of opening a specific notebook, drop the filename.

If you're on a **Nix-managed machine**, marimo will fail with a `websockets` import error. Prefix with `env -u PYTHONPATH`:

```bash
env -u PYTHONPATH uvx marimo edit --sandbox notebooks/nb07_compound_neighborhood.py
```

The demo vignette (`nb07_compound_neighborhood.py`) queries the all-vs-all cosine similarity matrix from Zenodo (~250 MB per modality), cached to `~/.cache/jx/` after the first fetch. It was built using the previous ones.

## License

BSD 3-Clause — see [LICENSE](LICENSE).

## Status

Active experiment by a team at the Broad Institute. Watch this repo for periodic updates as the hypothesis develops.
