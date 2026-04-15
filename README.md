# jx — JUMP eXplore

An experiment in agent-driven scientific data exploration, built around [JUMP Cell Painting](https://jump-cellpainting.broadinstitute.org/) — the largest public morphological profiling dataset (~116K compounds, ~8K CRISPR knockouts, ~15K gene overexpressions, 1.6 billion cells).

## The hypothesis

A catalog of real analyses — working [marimo](https://marimo.io) notebooks, each embodying an actual use case — is a better artifact than a Python library, or even an extensive skills library. Each notebook is both a runnable demonstration of a use case and a source of pure functions that other notebooks can [import and reuse](https://docs.marimo.io/guides/reusing_functions/) directly. This means the catalog is simultaneously documentation, working code, and a compositional building block — without the maintenance overhead of a separate library. Outside of reusable functions, existing notebooks have cells which use them to display rich outputs (plots, widgets, tables, etc.). These also are usable as valuable examples for agents to use downstream.

A thin skill file tells an AI agent (Claude Code + [marimo-pair](https://github.com/marimo-team/marimo-pair)) what's in the catalog and how to compose from it. Given a new biological question, the agent picks relevant notebooks, composes their reusable functions into a new notebook, generates any custom glue code, executes it in a live kernel, and hands back a self-contained, re-runnable result. The catalog grows as new analyses are added. The skill stays thin on purpose.

If this works for JUMP, the pattern transfers: new dataset = new catalog + new skill, same machinery.

The idea that notebooks can serve as both documentation and library isn't new — [fast.ai](https://www.fast.ai/) developed its deep learning library this way at scale using [nbdev](https://nbdev.fast.ai/). What's different here is the agent composition angle: rather than publishing a package, the catalog is the substrate an agent reasons over and builds from.

## The catalog

An initial starter pack of six notebooks adapted from [JUMP-Hub](https://github.com/jump-cellpainting/jump-hub), covering the building blocks of JUMP analysis: profile retrieval, metadata annotation, morphological activity (mAP), Cell Painting image display, similarity search, and gene annotation. A seventh notebook (`nb07_compound_neighborhood.py`) is the demo vignette — given a compound of interest, find what's morphologically similar in JUMP, annotate the neighbors with targets, and show the images side by side. It composes the first six and runs end to end.

## Getting started

Requires Python ≥ 3.11 and [uv](https://docs.astral.sh/uv/).

Each notebook is a self-contained [PEP 723](https://peps.python.org/pep-0723/) script — dependencies are declared inline.

**Local machine:**
```bash
git clone https://github.com/broadinstitute/jx && cd jx && uvx marimo edit
```

If you're on a **Nix-managed machine**, marimo will fail with a `websockets` import error. Prefix with `env -u PYTHONPATH`:

```bash
env -u PYTHONPATH uvx marimo edit
```

The demo vignette (`nb07_compound_neighborhood.py`) queries the all-vs-all cosine similarity matrix from Zenodo (~250 MB per modality). It was built using the previous ones.

## License

BSD 3-Clause — see [LICENSE](LICENSE).

## Status

Active experiment by a team at the Broad Institute. Watch this repo for periodic updates as the hypothesis develops.
