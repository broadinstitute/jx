# jx — JUMP eXplore

An experiment in agent-driven scientific data exploration, built around [JUMP Cell Painting](https://jump-cellpainting.broadinstitute.org/) — the largest public morphological profiling dataset (~116K compounds, ~8K CRISPR knockouts, ~15K gene overexpressions, 1.6 billion cells).

## The hypothesis

A catalog of real analyses — working [marimo](https://marimo.io) notebooks, each embodying an actual use case — is a more useful artifact than a library. Marimo notebooks are plain Python files. Their functions, when written without notebook-local state, are directly importable by other notebooks. A thin skill file tells an AI agent (Claude Code + [marimo-pair](https://github.com/marimo-team/marimo-pair)) what's in the catalog and how to compose from it. Given a new biological question, the agent picks relevant notebooks, composes their reusable functions into a new notebook, executes it in a live kernel, and hands back a self-contained, re-runnable result. The catalog grows as new analyses are added. The skill stays thin on purpose.

If this works for JUMP, the pattern transfers: new dataset = new catalog + new skill, same machinery.

## The catalog

A starter pack of six notebooks adapted from [JUMP-Hub](https://github.com/jump-cellpainting/jump-hub), covering the building blocks of JUMP analysis: profile retrieval, metadata annotation, morphological activity (mAP), Cell Painting image display, similarity search, and gene annotation. A seventh notebook (`07_compound_neighborhood.py`) is the demo vignette — given a compound of interest, find what's morphologically similar in JUMP, annotate the neighbors with targets, and show the images side by side. It composes the first six and runs end to end.

## Getting started

Each notebook is a self-contained [PEP 723](https://peps.python.org/pep-0723/) script — dependencies are declared inline and managed by [uv](https://docs.astral.sh/uv/). To run any notebook standalone:

```bash
uv run --script notebooks/nb01_retrieve_profiles.py
```

For interactive exploration, open it in marimo:

```bash
# Nix users: unset PYTHONPATH first to avoid websockets conflicts
env -u PYTHONPATH marimo edit notebooks/nb01_retrieve_profiles.py
```

The demo vignette (`07_compound_neighborhood.py`) queries the all-vs-all cosine similarity matrix from Zenodo (~250 MB per modality). Cache it first to avoid re-downloading on every run:

```bash
mkdir -p ~/.cache/jx
curl -L -o ~/.cache/jx/crispr_cosinesim_full.parquet \
  "https://zenodo.org/api/records/$(curl -s https://zenodo.org/api/records/13259495 | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")/files/crispr_cosinesim_full.parquet/content"
```

Or set `JX_CACHE` to point to an existing copy.

## License

BSD 3-Clause — see [LICENSE](LICENSE).

## Status

Active experiment by a team at the Broad Institute. Watch this repo for periodic updates as the hypothesis develops.
