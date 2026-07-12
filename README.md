# jx — JUMP eXplore

An experiment in agent-driven scientific data exploration, built around [JUMP Cell Painting](https://jump-cellpainting.broadinstitute.org/) — the largest public morphological profiling dataset (~116K compounds, ~8K CRISPR knockouts, ~15K gene overexpressions, 1.6 billion cells).

jx is a curated catalog of [marimo](https://marimo.io) vignettes for JUMP analysis, plus a thin skill that lets an agent compose new analyses from them.
Each vignette is both a runnable demonstration and a source of pure functions other notebooks can [import and reuse](https://docs.marimo.io/guides/reusing_functions/) directly.
Given a new biological question, the agent picks relevant vignettes, composes their functions into a new notebook, executes it in a live kernel, and hands back a self-contained, re-runnable result.

For the hypothesis, the catalog walkthrough, and the project roadmap, see [PLAN.md](PLAN.md).

## The catalog

Each notebook ships with a committed session snapshot under [`notebooks/__marimo__/session/`](notebooks/__marimo__/session/) so the molab preview renders cell outputs without re-executing.

| Notebook | Role | Preview |
|---|---|---|
| [`nb01_retrieve_profiles.py`](notebooks/nb01_retrieve_profiles.py) | Pull JUMP morphological profiles by perturbation | [![Open in molab](https://marimo.io/molab-shield.svg)](https://molab.marimo.io/github/broadinstitute/jx/blob/main/notebooks/nb01_retrieve_profiles.py) |
| [`nb02_add_metadata.py`](notebooks/nb02_add_metadata.py) | Annotate profiles with plate, well, and perturbation metadata | [![Open in molab](https://marimo.io/molab-shield.svg)](https://molab.marimo.io/github/broadinstitute/jx/blob/main/notebooks/nb02_add_metadata.py) |
| [`nb03_calculate_activity.py`](notebooks/nb03_calculate_activity.py) | Score morphological activity via mAP (copairs) | [![Open in molab](https://marimo.io/molab-shield.svg)](https://molab.marimo.io/github/broadinstitute/jx/blob/main/notebooks/nb03_calculate_activity.py) |
| [`nb04_display_images.py`](notebooks/nb04_display_images.py) | Fetch and display Cell Painting site images | [![Open in molab](https://marimo.io/molab-shield.svg)](https://molab.marimo.io/github/broadinstitute/jx/blob/main/notebooks/nb04_display_images.py) |
| [`nb05_explore_similarity.py`](notebooks/nb05_explore_similarity.py) | Cosine-similarity search over JUMP profiles | [![Open in molab](https://marimo.io/molab-shield.svg)](https://molab.marimo.io/github/broadinstitute/jx/blob/main/notebooks/nb05_explore_similarity.py) |
| [`nb06_query_genes.py`](notebooks/nb06_query_genes.py) | Translate gene / compound identifiers via `broad-babel` | [![Open in molab](https://marimo.io/molab-shield.svg)](https://molab.marimo.io/github/broadinstitute/jx/blob/main/notebooks/nb06_query_genes.py) |
| [`nb07_compound_neighborhood.py`](notebooks/nb07_compound_neighborhood.py) | Composition demo: compound -> similar perturbations -> annotated neighborhood with images | [![Open in molab](https://marimo.io/molab-shield.svg)](https://molab.marimo.io/github/broadinstitute/jx/blob/main/notebooks/nb07_compound_neighborhood.py) |

Related public catalogs of the same pattern: [fgx](https://github.com/broadinstitute/fgx) for FinnGenie human genetics, [prx](https://github.com/broadinstitute/prx) for PROSPECT chemical genetics, and [dmx](https://github.com/broadinstitute/dmx) for DepMap Breadbox.

## Getting started

This catalog follows the [vignette-catalog-skills](https://github.com/carpenter-singh-lab/vignette-catalog-skills) pattern.
The installed skill stores are gitignored, so a fresh clone has `skills-lock.json` plus the repo-local `compose-query` skill (see below); restore the installed skill content first:

```bash
uv --version  # or: curl -LsSf https://astral.sh/uv/install.sh | sh
npx skills add carpenter-singh-lab/vignette-catalog-skills --agent claude-code -y
npx skills add marimo-team/marimo-pair --agent claude-code -y
```

Then open [Claude Code](https://code.claude.com/docs) in this repo and ask to *get started* - the `vignette-catalog-setup` skill installs prereqs ([uv](https://docs.astral.sh/uv/) and the [marimo-pair](https://github.com/marimo-team/marimo-pair) skill), launches `nb07_compound_neighborhood` in a live marimo kernel, and hands off to `vignette-catalog-compose-notebook` for the actual analysis.

jx also ships a repo-local `compose-query` skill (tracked under `.claude/skills/compose-query/`) for the parallel ggsql catalog under `queries/` - pure SQL + chart questions against the JUMP metadata DuckDB that don't need a marimo notebook.

## License

BSD 3-Clause — see [LICENSE](LICENSE).
