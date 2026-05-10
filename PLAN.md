# Plan — agent-composable scientific knowledge

**Lead:** Shantanu Singh
**Status:** Four public catalog instances shipped; paper in progress
**Last revised:** 2026-05-10

## Hypothesis

To do agent-driven scientific data analysis, three things are sufficient: a curated catalog of runnable [marimo](https://marimo.io) vignettes, a thin orientation skill, and a live kernel ([marimo-pair](https://github.com/marimo-team/marimo-pair)).

A vignette is a working analysis paired with the pure functions it produces.
Functions are hoisted from the cells in which they were written and are importable by later vignettes; the catalog forms a cumulative DAG.
The skill points an agent at the catalog and explains how to compose.
The live kernel gives the agent feedback on running code as it composes.
Given a question, the agent picks relevant vignettes, imports their functions, composes them in a live kernel, and produces a composed notebook as a self-contained, re-runnable artifact.

The closest precedent is fast.ai's [nbdev](https://nbdev.fast.ai/): notebooks as source of truth, library exported from them.
The pattern here differs in that the factoring step — deciding which functions to extract into a library — is deferred.
When agents maintain the abstraction, that step may be deferrable indefinitely.
Whether packaging eventually becomes necessary at scale is an open question.

## Vignettes vs composed notebooks

These are different artifacts and we keep them distinct.

- **Vignettes** are the catalog.
  Curated, each teaching one move from the school of thought.
  Pure functions hoisted from vignettes are the tools the school uses.
  Vignettes are what we publish, what visitors read, what the agent grounds itself in.
- **Composed notebooks** are what an agent or a user produces by importing from the catalog and answering a question.
  They only have to answer the question.

Some composed notebooks may be promoted back to vignette-grade through deliberate curation.
Most won't.
A vignette has to teach, and the bar for catalog entry is high.
The catalog stays small on purpose: a catalog that absorbs every analysis the team runs loses the curatorial signal the agent depends on.

## Building a catalog

The catalog is built through an apprenticeship loop in an instrumented environment.

The mindset is the MOOC mindset: each vignette should be small, runnable, and self-contained, the way you would prepare material for students who have to execute it on their own without the instructor in the room.
Once the catalog is in place, agents — and other users — work against it on their own.

What makes this tractable is that a coding-agent environment (e.g., Claude Code) instruments the work.
A scientist solves a real problem in natural language; the interaction is logged; the agent introspects the log and drafts a vignette; the scientist curates.
Over iterations, the catalog accumulates tacit knowledge the scientist would never have written down voluntarily — the kind of knowledge Polanyi pointed at when he said *we know more than we can tell*.
The apprenticeship loop extends the boundary of what can be made explicit, adding new vignettes or updating existing ones.

## Instances

Instances of the pattern, each targeting a different scientific dataset:

- **[jx](https://github.com/broadinstitute/jx)** — JUMP Cell Painting (imaging).
  Profile retrieval, metadata annotation, mAP activity, Cell Painting image display, similarity search, and gene annotation, plus a composition demo; DuckDB metadata, parquet profiles, S3 image fetches; polars + duckdb + broad-babel + jump-portrait.
  The most developed instance; ships with `CITATION.cff` and a Zenodo concept DOI ([`10.5281/zenodo.19598884`](https://doi.org/10.5281/zenodo.19598884)).
- **[fgx](https://github.com/broadinstitute/fgx)** — FinnGen (genetics, GWAS).
  Vignettes against FinnGenie's `/api/v1/*` REST surface via `httpx.get`; polars + altair.
  The same bearer token works for both the REST API and the FinnGenie MCP server.
- **[prx](https://github.com/broadinstitute/prx)** — PROSPECT (chemical-genetics).
  Vignettes pulling Bond et al. 2025 data from Figshare via pooch; sGR GCT matrices, PCL clusters, MOA inference; polars + rdkit + scikit-learn.
- **[dmx](https://github.com/broadinstitute/dmx)** — DepMap (cancer dependencies).
  Vignettes against the public Breadbox REST API; read-only examples require no API key; requests + polars + altair.

All four instances are skill-light marimo catalogs that share the contract below.

## Shared repository contract

The instances should look the same by default.
A reader or agent opening any of `jx`, `fgx`, `prx`, or `dmx` should find the same public contract:

- `README.md` is the human entry point: what the catalog is for, the notebook list, how to get started, license, and links to sibling catalogs.
- `AGENTS.md` is the agent entry point: validation rules, settled architecture, repo-specific gotchas, and when to use the catalog.
  Tool-specific files such as `CLAUDE.md` should point to it rather than fork the guidance.
- `.claude/skills/getting-started/SKILL.md` launches the first notebook in a marimo sandbox and installs the upstream marimo skills for the user's agent of choice.
- `.claude/skills/compose-notebook/SKILL.md` is the detailed composition contract: the catalog table, reusable helpers, import recipe, dependency rules, validation steps, and promotion rules for new helpers.
- `notebooks/nbNN_<topic>.py` are the catalog vignettes.
  They use PEP 723 inline dependencies, `with app.setup`, and top-level `@app.function` helpers so later notebooks can import them as plain Python modules.
- `notebooks/__marimo__/session/*.json` are committed when a notebook exports reliably, so molab previews render outputs without re-running.
  A snapshot that fails to execute is a signal of a real bug in the notebook, not in the snapshot.
- `pyproject.toml` carries shared tool configuration: `line-length = 120` and ruff per-file ignores for marimo notebooks (`B018, F401, F821, F841`) so bare display expressions, setup-block imports, and cross-notebook helpers do not trip the linter.

The validation bar is also common: after editing a notebook, run it in a marimo sandbox, inspect the actual outputs, export or refresh the molab session snapshot when appropriate, and run static checks (`ruff` plus `marimo check`).
Static checks alone are not sufficient for scientific notebooks; they do not catch empty tables, stale endpoint assumptions, wrong sign conventions, or plots that render but say nothing.

Intentional differences should be explicit and dataset-driven:

| Repo | Data surface | Auth | Cache / data policy | Extra surface |
|---|---|---|---|---|
| `jx` | DuckDB metadata, parquet profiles, S3 images, Zenodo similarity matrices | Public data, no repo secret required | Cache large remote artifacts under `~/.cache/jx` or equivalent | Primary repo: holds `PLAN.md`, `CITATION.cff`, release workflows, and the `queries/` ggsql catalog |
| `fgx` | FinnGenie `/api/v1/*` REST endpoints via `httpx` | `FINNGENIE_TOKEN` in local `.env`; same key works for REST and MCP | Live API reads; no committed cache | `Justfile` shortcut (`just notebook`) for direct launch |
| `prx` | Bond et al. 2025 Figshare/Dryad downloads via `pooch` | Public data, no repo secret required | Raw downloads under ignored `data/`; pin SHA-256 on every fetched artifact | Heavier scientific deps (`rdkit`, `scikit-learn`) |
| `dmx` | Public DepMap Breadbox REST API via `requests` | Public read-only examples need no API key | Live API reads; summarize large responses before display | — |

Everything else should converge unless there is a concrete reason not to.

## Computational screens

Once a catalog is mature, screens become possible.
The vignettes define what you can sweep over - genes, compounds, cell lines, conditions - and the agent composes one analysis per point in that space.
Each composed notebook is a re-runnable artifact, independent of the agent run that produced it.
The ranked output gets triaged the way a Cell Painting or a CRISPR screen does: most hits are noise, a few hold up under follow-up.

Whole-genome screens taught us how to fan out across a perturbation set, score, rank, validate, and cull.
Same idea here - but the unit being screened is a hypothesis rather than a guide RNA or a compound.

Three subproblems:

- **What can be swept.** The vignettes determine this.
  A catalog with notebooks for compound activity, gene-gene morphological similarity, and chemical-genetic interaction defines a different sweepable space than a catalog of summary-statistics notebooks.
  Designing the catalog is designing the search space.

- **What counts as a hit.** Standard screen output: ranked lists, hit rates, complementary sweeps to break ties, downstream validation for the few survivors.
  A reviewer agent in the loop catches obvious slop.
  Which surviving hit is *interesting* still needs a scientist.

- **What it costs.** Reusing hoisted functions and a live kernel is cheaper per point than ad-hoc agent generation.
  A screen-grade evaluation reports tokens and time per analysis alongside hit rate.

A project's open questions are the place to start - the issues, follow-up lists, and "we never got to..." notes that accumulate around any flagship dataset.
Most of this is already written down somewhere.
The screen is just executing it.

Once several instances exist alongside each other, a sweep can run across them.
Each catalog (jx, fgx, prx, dmx) covers a different hypothesis space, and pulling from more than one lets you ask questions no single dataset can answer alone.

*The framing in this section draws on conversations with Blake Lash (CRISPR-screen analogy, fan-out and triage), Yasha Ektefaie (running JUMP as a live screen), Anne Carpenter (real discovery and prioritization, not verification), and Eric Lander (triage at thousand-notebook scale) - personal communication, 2026.*

## The paper

A paper introducing the pattern, with the instances as evidence and formal evaluation across them.

**Working title:** *Curated vignette catalogs for agent-driven scientific data analysis*
**Form:** Methods/software paper; bioRxiv preprint posted at journal submission
**Target venues:** *Patterns* or *PLOS Computational Biology*
**Target:** Submission August 2026

### Core claim

A small, curated catalog of vignettes plus a thin orientation skill plus a live kernel is a viable unit of agent-composable scientific knowledge, on the properties of reproducibility, composition, extensibility, and human + agent dual-readability.

### Structure

1. Introduction.
2. Related work — nbdev, MCP tool servers, direct REST/API access, Python libraries, flat skill files, Biomni.
3. The pattern — vignettes vs composed notebooks; thin skill + curated catalog + marimo-pair; cell hoisting, parameterization, live kernel execution.
4. Building a catalog — the apprenticeship loop in an instrumented environment; MOOC-style vignette design; scientist solves, agent drafts, scientist curates.
5. Instances — jx, fgx, prx, dmx.
6. Evaluation — quantitative and qualitative across the instances.
7. Discussion — what transfers, what doesn't; the curatorial claim and its limits; the runnable-document lineage (Knuth, Jupyter, nbdev).
8. Conclusion and future work — including computational screens as the natural next step (sweep a hypothesis space, compose one analysis per point, rank the hits).

### Evaluation

- **Quantitative.** Catalog size; composed-notebook export sizes; hit-rate for catalog reuse on a small set of evaluation questions per instance; response-size comparison versus MCP-wrapped equivalents.
- **Qualitative.** Composition demo per instance, end-to-end runnable.
  Time-to-second-instance: how long for a domain expert to ship a vignette catalog from scratch.

### Figures and tables

- **Figure 1.** Composition flow: skill → vignette catalog → marimo kernel → composed notebook.
- **Figure 2.** Composition demo output — jx primarily, with sibling demos from fgx, prx, and dmx.
- **Table 1.** Instances summary: dataset, data surface (DuckDB / REST / API), vignette count, status.
- **Table 2.** Comparison across approaches: MCP tools / Python library / flat skill file / vignette catalog × reproducibility, composition, extensibility, dual-readability, scaling, response sizes.

### Timeline

Draft May-June, revision and bioRxiv preprint July, journal submission August, review response September.

### Remaining

The manuscript itself; Figures 1 and 2; Tables 1 and 2; evaluation questions and composed-demo notebooks for fgx, prx, and dmx; dmx curation beyond the initial scaffold.

## Open questions

- How far can deferred factoring go?
  The catalog leaves factoring undone.
  Whether this scales beyond ~10 vignettes per instance is an empirical question.
- Catalog hit rate.
  A thin skill suggests; it cannot enforce.
  Whether agents preferentially compose from the catalog or generate ad-hoc code is measurable.
- Promotion criteria.
  When does a composed notebook earn its way back into the vignette catalog?
  Currently judged case-by-case.
- External adoption.
  The pattern's value depends on domain experts other than the original author being able to ship a vignette catalog for their dataset.
  Time-to-second-instance is the metric.
- Catalog evolution.
  What does federated-learning-style improvement look like in practice — distribute catalog v1, observe what users compose against it, aggregate signals (reuse rates, missing vignettes, hoist-worthy one-off helpers) into a curated v2?
- Screen volume vs. inspectability.
  The promise that every hit and every miss is a re-runnable notebook is what distinguishes this from a black-box generation pipeline.
  Whether that holds at thousand-analysis scale, or whether triage itself becomes the bottleneck, is unresolved.

## Authors

The author list grows by concrete contribution — a written section, a catalog, a figure, evaluation data.
The current jx contributors (Munoz, Gogoberidze, Singh) are the seed; fgx, prx, and dmx contributors join as their instances are written up.

## License

BSD 3-Clause.
