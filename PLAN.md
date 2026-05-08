# Plan — agent-composable scientific knowledge

**Lead:** Shantanu Singh
**Status:** First instance (jx) catalog shipped; paper in progress
**Last revised:** 2026-05-08

## Hypothesis

To do agent-driven scientific data analysis, three things are sufficient: a curated catalog of runnable [marimo](https://marimo.io) vignettes, a thin orientation skill, and a live kernel ([marimo-pair](https://github.com/marimo-team/marimo-pair)).

A vignette is a working analysis paired with the pure functions it produces. Functions are hoisted from the cells in which they were written and are importable by later vignettes; the catalog forms a cumulative DAG. The skill points an agent at the catalog and explains how to compose. The live kernel gives the agent feedback on running code as it composes. Given a question, the agent picks relevant vignettes, imports their functions, composes them in a live kernel, and produces a composed notebook as a self-contained, re-runnable artifact.

The closest precedent is fast.ai's [nbdev](https://nbdev.fast.ai/): notebooks as source of truth, library exported from them. The pattern here differs in that the factoring step — deciding which functions to extract into a library — is deferred. When agents maintain the abstraction, that step may be deferrable indefinitely. Whether packaging eventually becomes necessary at scale is an open question.

## Vignettes vs composed notebooks

These are different artifacts and we keep them distinct.

- **Vignettes** are the catalog. Curated, each teaching one move from the school of thought. Pure functions hoisted from vignettes are the tools the school uses. Vignettes are what we publish, what visitors read, what the agent grounds itself in.
- **Composed notebooks** are what an agent or a user produces by importing from the catalog and answering a question. They only have to answer the question.

Some composed notebooks may be promoted back to vignette-grade through deliberate curation. Most won't. A vignette has to teach, and the bar for catalog entry is high. The catalog stays small on purpose: a catalog that absorbs every analysis the team runs loses the curatorial signal the agent depends on.

## Building a catalog

The catalog is built through an apprenticeship loop in an instrumented environment.

The mindset is the MOOC mindset: each vignette should be small, runnable, and self-contained, the way you would prepare material for students who have to execute it on their own without the instructor in the room. Once the catalog is in place, agents — and other users — work against it on their own.

What makes this tractable is that a coding-agent environment (e.g., Claude Code) instruments the work. A scientist solves a real problem in natural language; the interaction is logged; the agent introspects the log and drafts a vignette; the scientist curates. Over iterations, the catalog accumulates tacit knowledge the scientist would never have written down voluntarily — the kind of knowledge Polanyi pointed at when he said *we know more than we can tell*. The apprenticeship loop extends the boundary of what can be made explicit, one vignette at a time.

## Instances

Instances of the pattern, each targeting a different scientific dataset:

- **[jx](https://github.com/broadinstitute/jx)** — JUMP Cell Painting (imaging). Six vignettes plus a composition demo. DuckDB metadata, parquet profiles, image fetches. The most developed instance; ships with `CITATION.cff` and a Zenodo concept DOI ([`10.5281/zenodo.19598884`](https://doi.org/10.5281/zenodo.19598884)).
- **[fgx](https://github.com/broadinstitute/fgx)** — FinnGen (genetics, GWAS). Vignettes against FinnGenie's `/api/v1/*` REST surface via `httpx.get`.
- **[prx](https://github.com/broadinstitute/prx)** — PROSPECT (chemical-genetics). Vignettes against PROSPECT data; same skill pattern.
- **dmx** (planned) — DepMap (cancer dependencies). To be built around the existing [`depmap-breadbox`](https://github.com/broadinstitute/depmap-breadbox) data API.

All instances are skill-light marimo catalogs.

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
2. Related work — nbdev, MCP tool servers, Python libraries, flat skill files, Biomni.
3. The pattern — vignettes vs composed notebooks; thin skill + curated catalog + marimo-pair; cell hoisting, parameterization, live kernel execution.
4. Building a catalog — the apprenticeship loop in an instrumented environment; MOOC-style vignette design; scientist solves, agent drafts, scientist curates.
5. Instances — jx, fgx, prx, dmx.
6. Evaluation — quantitative and qualitative across the instances.
7. Discussion — what transfers, what doesn't; the curatorial claim and its limits; the runnable-document lineage (Knuth, Jupyter, nbdev).
8. Conclusion and future work — including computational screens as the natural next step (sweep a hypothesis space, compose one analysis per point, rank the hits).

### Evaluation

- **Quantitative.** Catalog size; composed-notebook export sizes; hit-rate for catalog reuse on a small set of evaluation questions per instance; response-size comparison versus MCP-wrapped equivalents.
- **Qualitative.** Composition demo per instance, end-to-end runnable. Time-to-second-instance: how long for a domain expert to ship a vignette catalog from scratch.

### Figures and tables

- **Figure 1.** Composition flow: skill → vignette catalog → marimo kernel → composed notebook.
- **Figure 2.** Composition demo output — jx primarily, with siblings if their demos are end-to-end runnable by submission.
- **Table 1.** Instances summary: dataset, data surface (DuckDB / REST / API), vignette count, status.
- **Table 2.** Comparison across approaches: MCP tools / Python library / flat skill file / vignette catalog × reproducibility, composition, extensibility, dual-readability, scaling, response sizes.

### Timeline

Draft May-June, revision and bioRxiv preprint July, journal submission August, review response September.

### Remaining

The manuscript itself; Figures 1 and 2; Tables 1 and 2; dmx scaffold so it can be referenced as in-progress rather than aspirational.

## Open questions

- How far can deferred factoring go? The catalog leaves factoring undone. Whether this scales beyond ~10 vignettes per instance is an empirical question.
- Catalog hit rate. A thin skill suggests; it cannot enforce. Whether agents preferentially compose from the catalog or generate ad-hoc code is measurable.
- Promotion criteria. When does a composed notebook earn its way back into the vignette catalog? Currently judged case-by-case.
- External adoption. The pattern's value depends on domain experts other than the original author being able to ship a vignette catalog for their dataset. Time-to-second-instance is the metric.
- Catalog evolution. What does federated-learning-style improvement look like in practice — distribute catalog v1, observe what users compose against it, aggregate signals (reuse rates, missing vignettes, hoist-worthy one-off helpers) into a curated v2?
- Computational screens. Once a catalog is mature, the agent can sweep a space of hypotheses, composing one analysis per point and ranking the results — analogous to a whole-genome screen at the level of concepts rather than genes. Two subproblems: what defines the enumerable search space (the catalog's parameterization vocabulary determines what's sweepable), and what makes a hit a "good discovery."

## Authors

The author list grows by concrete contribution — a written section, a catalog, a figure, evaluation data. The current jx contributors (Munoz, Gogoberidze, Singh) are the seed; fgx, prx, and dmx contributors join as their instances are written up.

## License

BSD 3-Clause.
