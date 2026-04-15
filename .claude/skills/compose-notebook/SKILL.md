---
name: compose-notebook
description: Compose a new marimo notebook in the jx repo by reusing @app.function helpers from the existing catalog (notebooks/nb01_retrieve_profiles.py through nb06_query_genes.py) to answer a JUMP Cell Painting biological question end-to-end — e.g. "find perturbations morphologically similar to X and show their images", "annotate these hits with gene/target info", "pull activity mAP for these perturbations". Trigger whenever the user asks for a notebook, analysis, figure, or vignette that touches JUMP profiles, cosine similarity, perturbation metadata, Cell Painting images, or morphological activity — even if they don't explicitly say "marimo" or "reuse the catalog". Use this instead of writing standalone query code from scratch, and instead of duplicating functions that already exist in the catalog. Also trigger when the user says "write me a notebook that…" inside jx, or asks to build on top of notebooks 01–06 / nb01–nb06.
---

# Compose a new marimo notebook from the jx catalog

## What this skill is for

The jx repo holds a catalog of marimo notebooks (`notebooks/nb01_*.py` through
`notebooks/nb06_*.py`) whose top-level `@app.function` helpers do all the
expensive plumbing for JUMP Cell Painting: loading profiles, attaching
metadata, computing activity, fetching 5-channel images from S3, querying
similarity matrices, and looking up gene annotations. When a user wants to
answer a biological question — "find things that look like compound X",
"show me images of these knockouts side-by-side", "what's the activity of
these genes" — the right move is almost always to **compose an existing
notebook from these helpers**, not to write a new query pipeline from
scratch. This skill tells you how.

## The catalog at a glance

Every catalog file defines its setup cell, a handful of `@app.function`s
(top-level pure functions, safe to import), and UI cells that exercise the
helpers. The functions are the contract; the UI cells are illustrative.

| Module | Reusable functions | What they do |
|---|---|---|
| `nb01_retrieve_profiles` | `load_profile_index()`, `load_profiles(subset)`, `profile_stats()` | Fetch the JUMP profile manifest and lazy-scan well-level parquet profiles for `crispr` / `orf` / `compound`. Returns `pl.LazyFrame`. |
| `nb02_add_metadata` | `load_profiles(subset)`, `sample_with_negcon(profiles, n)`, `build_mapper(jcp_ids, output_column)`, `annotate_profiles(profiles, jcp_ids)` | Join broad-babel annotations onto JCP2022 IDs. `build_mapper` is a generic `{JCP2022 → any column}` lookup using `broad_babel.query.get_mapper`. |
| `nb03_calculate_activity` | `sample_with_negcon`, `filter_to_complete_plates`, `attach_pert_type`, `compute_map` | Activity (mAP) via copairs. Use when the question is "how active is this perturbation?" |
| `nb04_display_images` | `lookup_site_metadata(query, input_column)`, `pick_first_site(location_info)`, `display_site(source, batch, plate, well, site, label)` | Pull well metadata via `jump_portrait.fetch.get_item_location_metadata`, pick a single imaging site, render a 5-channel image grid (matplotlib). `input_column` is `"standard_key"`, `"InChIKey"`, or `"JCP2022"`. |
| `nb05_explore_similarity` | `latest_zenodo_id()`, `load_distance_matrix(dataset)`, `sample_submatrix`, `plot_similarity_heatmap` | Lazy-scan the full all-vs-all cosine matrix from Zenodo. **Gotcha:** despite the filename `*_cosinesim_full.parquet` and the "0 = identical, 2 = anticorrelated" wording in that notebook's docstring, the actual values are cosine **similarities** in `[-1, 1]` (self-similarity ≈ 1), not distances. Sort descending. |
| `nb06_query_genes` | `gene_symbols_to_ncbi`, `entrez_gene_info`, `parse_gene_list` | NCBI Entrez lookups for gene symbols. Use when annotating CRISPR/ORF hits with gene descriptions. |

When the biological question isn't obviously one of the above, read the
catalog file itself (not just this table) before inventing new code. The
helpers have short docstrings and the UI cells are worked examples.

## The composition pattern

A composed notebook is a new file in `notebooks/` (e.g., `07_compound_neighborhood.py`)
that imports catalog helpers as plain Python and glues them together.
Three things matter: **imports**, **interactive UI**, and **caching**.

### 1. The setup cell — plain Python imports

Each catalog file uses an `nbNN_` prefix precisely so the file is a valid
Python module name. Import them by adding `notebooks/` to `sys.path` and
using a regular `from …` line. No `importlib`, no dynamic loading —
marimo's `@app.function` decorator exposes the functions at module top
level, so a normal import is all you need.

```python
with app.setup:
    import os
    import sys
    from pathlib import Path

    import marimo as mo
    import polars as pl

    NOTEBOOK_DIR = Path(__file__).parent
    CACHE_DIR = Path(os.environ.get("JX_CACHE", Path.home() / ".cache" / "jx"))

    if str(NOTEBOOK_DIR) not in sys.path:
        sys.path.insert(0, str(NOTEBOOK_DIR))

    from nb01_retrieve_profiles import load_profiles
    from nb02_add_metadata import annotate_profiles, build_mapper
    from nb04_display_images import display_site, lookup_site_metadata, pick_first_site
    from nb05_explore_similarity import load_distance_matrix
```

Why this works: marimo notebooks are just Python files, and their
`@app.function`-decorated helpers are ordinary top-level `def`s. Python
can't import a module whose filename starts with a digit, which is why
the catalog uses the `nb0N_` prefix — it's the boring constraint that
makes marimo's "reusing functions" guide work on this repo.

### 2. Interactive UI — widgets, not raw prints

The point of a composed notebook is to let the user *explore* — change
the query, click a different neighbor, regenerate images — not to
produce a single static figure. Lean on marimo's widgets. Two patterns
carry most of the weight:

- **Sidebar for controls**: consolidate inputs in `mo.sidebar()` so they
  stay visible while scrolling results. Use `mo.ui.dropdown` for
  categorical choices, `mo.ui.text` for queries, `mo.ui.slider` for
  numeric ranges:

  ```python
  mo.sidebar([
      mo.md("### Controls"),
      dataset_select,
      query_input,
      k_neighbors,
      run_button,
  ])
  ```

- **`mo.ui.table(df, selection="single")`** for result tables. Its
  `.value` is a `polars.DataFrame` containing the selected rows (or an
  empty DataFrame if nothing's picked). A downstream cell reads that
  selection and re-renders — so clicking a row in a neighbor table can
  drive which image appears below.

- **`mo.ui.plotly` for interactive scatter plots.** Use
  `mo.ui.plotly(fig, render_mode="webgl")` when you need reactive point
  selection (e.g., UMAP embeddings, similarity scatter). Its `.value`
  gives you the selected points. For large point clouds, `webgl` mode
  keeps rendering responsive.

```python
@app.cell
def neighbors_table(dataset_selector, query_input, k_neighbors):
    similarities = load_similarity_matrix(dataset_selector.value)
    neighbors = nearest_neighbors(similarities, query_input.value, k_neighbors.value)
    return (neighbors,)

@app.cell
def merged_view(neighbors, query_input, dataset_selector):
    # …join neighbors with annotate_profiles + build_mapper…
    merged_table = mo.ui.table(merged, selection="single", page_size=10)
    merged_table

@app.cell
def image_grid(merged_table, merged, query_input):
    selected = merged_table.value
    if selected is not None and not selected.is_empty():
        top_hit = selected.row(0, named=True)["JCP2022"]
    else:
        top_hit = merged.row(0, named=True)["JCP2022"]
    figures = []
    for jcp in (query_input.value, top_hit):
        sites = lookup_site_metadata(jcp, input_column="JCP2022")
        site = pick_first_site(sites)
        figures.append(display_site(site["Source"], site["Batch"], site["Plate"],
                                    site["Well"], site["Site"], jcp))
    mo.hstack([mo.as_html(f) for f in figures], justify="start", gap=2)
```

Matplotlib figures are displayed with `mo.as_html(fig)` inside an
`mo.hstack` / `mo.vstack`. Don't rely on the "last expression is the
output" magic for figures — wrap them explicitly so the layout works.

**Guard expensive steps with a run button.** Marimo re-runs downstream
cells on every upstream change, which is exactly wrong for things like
fetching a 250 MB matrix or rendering images from S3. Wrap those cells
behind `mo.ui.run_button()` + `mo.stop(not run_button.value)` so they
only execute on explicit user click:

```python
@app.cell
def _(mo):
    run_button = mo.ui.run_button(label="Fetch neighbors")
    run_button
    return (run_button,)

@app.cell
def _(mo, run_button, query_input, dataset_selector):
    mo.stop(not run_button.value)
    similarities = load_similarity_matrix(dataset_selector.value)
    neighbors = nearest_neighbors(similarities, query_input.value, 10)
    return (neighbors,)
```

### 3. Selection + paging

When a widget's `.value` drives both a control and a display, split them
into separate cells. Marimo doesn't let a cell read `.value` from a
widget it also creates. The pattern:

- **Cell 1** — create the paging slider, output it
- **Cell 2** — read `page_select.value`, render the page

```python
@app.cell
def _(mo, total_pages):
    page_select = mo.ui.slider(1, total_pages, value=1, label="Page")
    page_select
    return (page_select,)

@app.cell
def _(page_select, items, page_size):
    start = (page_select.value - 1) * page_size
    mo.vstack([render(item) for item in items[start : start + page_size]])
```

### 4. DuckDB for table wrangling

When using DuckDB inside `@app.function` bodies, always create an
explicit connection. The default connection (`duckdb.sql(...)`) shares a
single transaction — a failed query poisons it for all subsequent calls:

```python
con = duckdb.connect()
result = con.sql("SELECT ... FROM df").pl()
con.close()
```

### 5. Plotly dark theme (plotly 6+ compatible)

Use `copy.deepcopy` to derive a custom theme. Direct assignment then
`.update()` throws ValueError in plotly 6+:

```python
import copy
t = copy.deepcopy(pio.templates["plotly_dark"])
t.layout.paper_bgcolor = "rgba(0,0,0,0)"
t.layout.plot_bgcolor = "rgba(30,30,30,1)"
t.layout.font.color = "#e0e0e0"
t.layout.colorway = px.colors.qualitative.Set2
pio.templates["marimo_dark"] = t
```

### 6. Caching large artifacts

The cosine similarity matrices on Zenodo are ~250 MB each. A lazy scan
over a remote parquet that tries to pull a single row still re-downloads
large chunks on every re-run, which makes exploration unusable. Cache
once to `~/.cache/jx/` and read locally:

```python
@app.function
def load_similarity_matrix(dataset: str) -> pl.LazyFrame:
    cached = CACHE_DIR / f"{dataset}_cosinesim_full.parquet"
    if cached.exists():
        return pl.scan_parquet(cached)
    return load_distance_matrix(dataset)  # falls back to the Zenodo URL
```

Tell the user once how to seed the cache (`curl -o ~/.cache/jx/<file>
<zenodo-url>`), then assume it's there. The `JX_CACHE` env var lets them
point it somewhere else. Apply the same pattern to any other large
remote artifact (profiles, index files) you discover you're re-fetching.

## Running the notebook

The notebook is usable standalone (`uv run --script notebooks/07_*.py`)
because of its PEP 723 dependency header. But for interactive
development, the **marimo-pair** skill is the right tool — it lets you
edit cells, run them, and inspect outputs in a live kernel without
restarting. Once the notebook exists on disk, either open it in a new
marimo server (start with `env -u PYTHONPATH VIRTUAL_ENV=<venv>
marimo edit …`, see Gotchas below) or add it to an already-running
session.

When working against a running server via marimo-pair, use `code_mode`
to create and edit cells — don't write to the `.py` file, the kernel
owns it while it's open.

### Saving from code_mode

Marimo's `code_mode` edits are live in memory but not auto-saved to disk.
To persist changes programmatically:

```python
import marimo._code_mode as cm
async with cm.get_context() as ctx:
    doc = ctx._document
    from marimo._ast.codegen import generate_filecontents
    from marimo._runtime.context.utils import get_context
    from pathlib import Path

    names = [c.name if c.name else "_" for c in doc.cells]
    contents = generate_filecontents(
        codes=[c.code for c in doc.cells],
        names=names,
        cell_configs=[c.config for c in doc.cells],
    )
    Path(get_context().filename).write_text(contents)
```

After saving, restore the `# /// script` PEP 723 header and
`App(width=...)` config — `generate_filecontents` strips both. Also
ensure no cell has an empty name (`""`) — replace with `"_"` to avoid
`_unparsable_cell` wrappers.

## Known gotchas

These have bitten real composition work. Know them before you debug.

- **ruff F821 on marimo notebooks.** `@app.function` cells reference
  setup-cell symbols that ruff can't see statically. Add
  `"notebooks/nb*.py" = ["F821", "F841"]` to
  `[tool.ruff.lint.per-file-ignores]` in `pyproject.toml`.
- **`@app.function` with `_` prefix names.** Functions named `_helper()`
  become private to their cell and can't be called from other cells.
  Remove the `_` prefix for any function you want to reuse.
- **Underscore-prefixed variables in DuckDB queries.** `duckdb.sql("FROM _var")`
  can't resolve `_var` in marimo cells because marimo name-mangles
  private names. Use non-underscore names for variables referenced in
  DuckDB SQL.
- **`mo.stop` shows as "exception" in code_mode.** This is expected —
  `mo.stop` raises an internal exception. Downstream cells show
  "cancelled". Both are normal behavior.
- **plotly 6 template assignment.** Use `copy.deepcopy()` then set
  attributes. Direct `pio.templates["x"] = pio.templates["y"]` then
  `.update()` throws ValueError.
- **Bare widget expressions trigger ruff B018.** Marimo renders the
  last expression in a cell, so `dataset_dropdown` on a bare line is
  intentional. Add `# noqa: B018` to suppress the lint warning.
- **`create_cell` produces empty names.** Cells created via
  `ctx.create_cell()` get `name=""` instead of `"_"`. Fix names before
  saving with `generate_filecontents`, or codegen will produce
  `_unparsable_cell` wrappers.
- **`generate_filecontents` strips script headers.** The `# /// script`
  PEP 723 block and `App(width=...)` config are lost on codegen save.
  Re-add them after writing the file.
- **Cosine similarity, not distance.** `nb05`'s `load_distance_matrix`
  returns values in `[-1, 1]` where 1 is identical. Sort descending for
  "nearest neighbors". The docstring in that file is misleading and
  should eventually be fixed upstream.
- **broad-babel's column set is small.** It exposes `standard_key`,
  `JCP2022`, `plate_type`, `NCBI_Gene_ID`, `broad_sample`, `pert_type`
  — and that's it. There is no `target` column. For CRISPR/ORF, the
  gene symbol (`standard_key`) is the target. For compounds you need
  different annotation sources entirely.
- **Similarity matrices are partitioned by modality.** The CRISPR
  matrix only contains CRISPR JCP IDs (`JCP2022_8…`), the ORF matrix
  only ORF (`JCP2022_9…`). Don't query a compound JCP against the
  CRISPR matrix.
- **`jump_portrait` + `broad_babel` versions must be in sync.** The
  PyPI 0.1.0 / 0.1.31 combo has a latent bug where
  `get_item_location_metadata` does a duckdb replacement scan against
  `meta_wells`, but `broad_babel.data.get_table("well")` returns a
  path string in that release, not a DataFrame. The fix lives in
  the `add_ci` branch of the Carpenter-Singh lab monorepo — if
  the user hits this, install both from that branch via
  `ctx.install_packages(
      "git+https://github.com/broadinstitute/monorepo.git@add_ci#subdirectory=libs/broad_babel",
      "git+https://github.com/broadinstitute/monorepo.git@add_ci#subdirectory=libs/jump_portrait"
  )` inside a marimo-pair session. Don't workaround it by reimplementing
  `lookup_site_metadata` in the composed notebook — fix the upstream
  package and keep the composed notebook clean.
- **Nix shells poison `PYTHONPATH`.** On this machine the shell exports
  `PYTHONPATH=/nix/store/…websockets-13.1/…`, which shadows the venv's
	  websockets and crashes `marimo edit` on startup with
  `ImportError: cannot import name 'ClientConnection' from 'websockets'`.
  Launch marimo with `env -u PYTHONPATH VIRTUAL_ENV=<venv-path>
  PATH=<venv-path>/bin:$PATH marimo edit …`.
- **Ports are shared.** 2718–2720 are often in use by other users. Ask
  for a free port programmatically (`python -c "import socket; s =
  socket.socket(); s.bind(('127.0.0.1', 0)); print(s.getsockname()[1])"`)
  or pick something in the 27xx–28xx range after checking `ss -ltn`.

## Process for a new composition

When the user gives you a question like "compound X → similar things →
images side by side", work through this:

1. **Turn the English into catalog calls.** Which nbN functions give
   you each step? If you need something not in the table above, read
   the catalog file for details before deciding it's missing.
2. **Validate IDs against the data first.** Before writing the whole
   notebook, run a quick kernel check: does the query JCP exist in the
   similarity matrix? Does `broad_babel` know about it? Otherwise you
   burn time rendering failures.
3. **Draft the notebook with `@app.function` helpers first**, then
   `@app.cell` UI on top. Keep the setup cell to imports, constants,
   and a `sys.path.insert` — nothing reactive.
4. **Use `mo.sidebar` for all controls.** Don't scatter dropdowns across
   the main area — consolidate them so they stay visible while scrolling.
5. **Use `mo.ui.table(..., selection="single")` for any result set the
   user might want to click through**, and wire downstream cells to
   `.value`. Use `mo.ui.plotly` with `render_mode="webgl"` for scatter
   plots that need point selection. That's the difference between a
   notebook and a figure.
6. **Run it in a live kernel (marimo-pair) and iterate on cells in
   place.** Don't edit the `.py` file while the kernel has it open.
7. **After the first successful run, look for anything expensive
   you're about to repeat on every edit** and cache it.

## When *not* to use this skill

- If the user wants to modify an existing catalog notebook (e.g., fix
  a bug in `nb03_calculate_activity`), edit that file directly.
- If the task is pure infrastructure (set up a venv, configure CI, add
  a CLI), skill scope doesn't help.
- If the user is asking about the broader VOA project plan or jx-dev
  sprint state, point them at `docs/plan.md` and `PROGRESS_LOG.md` in
  the `jx-dev` repo instead of writing code.
