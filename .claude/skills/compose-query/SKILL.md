---
name: compose-query
description: Compose a new ggsql query in the jx repo to answer a SQL-shaped question against the canonical JUMP metadata DuckDB (`queries/data/jump_metadata.duckdb`) — plate/well/perturbation/compound demographics, source breakdowns, perturbation-type counts, joins across the metadata schema, anything visualizable as a single chart from one SELECT. Trigger when the user asks for a count, distribution, breakdown, summary, or "show me X across Y" question that maps cleanly to SQL + a chart, and the answer fits in one screen. Use this instead of writing a marimo notebook when no Python (image fetching, AnnData profiles, broad-babel translation, copairs computation) is needed. The companion skill `compose-notebook` covers the marimo path; cross-check before composing.
---

# Compose a new ggsql query in the jx catalog

## What this skill is for

The jx repo holds two parallel catalogs:

- `notebooks/nb01_*.py` through `nb06_*.py` — marimo notebooks for questions that need Python glue (image S3 fetches, AnnData profiles, broad-babel ID translation, copairs computation, similarity matrices).
- `queries/q01_*.gsql` through `q<NN>_*.gsql` — self-contained ggsql files for questions that are pure SQL + chart against the canonical JUMP metadata DuckDB.

This skill is for the second catalog. When the user asks a question answerable from `jump_metadata.duckdb` alone, write a `.gsql` file. Don't reach for marimo unless the question genuinely needs Python.

## Surface decision in one paragraph

If the question is answerable as `SELECT ... GROUP BY ...` plus a chart, write a `.gsql`. If the question needs to fetch images, load profiles, query NCBI, translate IDs via broad-babel, or compute mAP / similarity, write or extend a marimo notebook (see the `compose-notebook` skill).

## The catalog at a glance

`queries/q*.gsql` files. Each is one chart, fully self-contained — repeat CTEs and joins per file, don't try to share logic across files. The naming is `q<NN>_<topic>.gsql` and the first two header lines are required:

```sql
-- title: Short title shown in the README index
-- description: One sentence on what the query shows.
```

An optional third line overrides the default reader for cross-DB queries (rare):

```sql
-- reader: duckdb://data/some_other.duckdb
```

The default reader is `duckdb://data/jump_metadata.duckdb` (relative to `queries/`).

## Where the data lives

`queries/data/jump_metadata.duckdb` — built by `just setup` from a sibling clone of [jump-cellpainting/datasets](https://github.com/jump-cellpainting/datasets) (default path `../../datasets/`, override with `just datasets=PATH setup`). The schema is defined by `datasets/metadata/db/setup.sql`.

Tables you'll actually use:

| Table | Rows | What it has |
|---|---|---|
| `plate` | ~2.5K | `Metadata_Source`, `Metadata_Batch`, `Metadata_Plate`, `Metadata_PlateType` |
| `well` | ~1.15M | `Metadata_Source`, `Metadata_Plate`, `Metadata_Well`, `Metadata_JCP2022` |
| `perturbation` | varies | `Metadata_JCP2022`, `Metadata_pert_type` |
| `perturbation_control` | small | controls only — `Metadata_JCP2022`, `Metadata_pert_type`, `Metadata_Name` |
| `compound` | ~116K | `Metadata_JCP2022`, `Metadata_InChIKey`, `Metadata_InChI`, `Metadata_SMILES` |
| `compound_source` | varies | provenance per (`Metadata_JCP2022`, source) |
| `crispr` | ~8K | CRISPR perturbation metadata |
| `orf` | ~15K | ORF perturbation metadata |
| `microscope_filter`, `microscope_config`, `cellprofiler_version` | small | acquisition-side metadata |

Discover columns with `SELECT * FROM duckdb_columns() WHERE table_name = 'compound'` inside a one-off `duckdb data/jump_metadata.duckdb` session — don't guess.

The augmented metadata DB (`jump_metadata_augmented.duckdb`) with ChEMBL / Repurposing Hub / MOTIVE / ToxCast annotations is built by jump_production's Snakemake pipeline, not by `just setup`. When that DB is on disk, point at it via the `-- reader:` header in a query.

## Canonical query skeleton

Use this as the starting point. Self-contained — repeat CTEs per file.

```sql
-- title: <one-line title>
-- description: <one-sentence description>

WITH base AS (
    SELECT ...
    FROM <table> [JOIN ... ON ...]
    [WHERE ...]
)
SELECT
    <category_col> AS <axis_name>,
    <other_dim>    AS <fill_or_facet>,
    COUNT(*)       AS <metric>
FROM base
GROUP BY <category_col>, <other_dim>

VISUALISE <axis_name> AS y, <metric> AS x, <fill_or_facet> AS fill
DRAW bar
[FACET <fill_or_facet> SETTING ncol => 4]
LABEL title => '<chart title>'
```

The `WITH base AS (...)` step is conventional even for simple queries — it makes the SELECT/VISUALISE split easy to read and gives a place to add filters later without reshuffling.

## ggsql syntax reference

- Top-level clauses: `SELECT ... <visualisation block>`. Visualisation block is `VISUALISE` (mandatory) + any of `DRAW`, `PLACE`, `SCALE`, `FACET`, `LABEL`, `PROJECT`.
- Aesthetics on `VISUALISE`: `<col> AS x|y|fill|color|stroke|size|shape|alpha`.
- Geoms via `DRAW`: `point`, `bar`, `line`, `path`, `segment`, `rule`, `area`, `ribbon`, `polygon`, `text`, `density`, `violin`, `histogram`, `boxplot`, `errorbar`, `smooth`.
- Faceting: `FACET <col> [BY <col>] [SETTING ncol => N, free => ['x','y']]`.
- Full ggsql syntax docs: https://ggsql.org/syntax/. Gallery examples: https://ggsql.org/gallery/.

## Workflow

1. Pick the next `q<NN>_<topic>.gsql` filename (look at the highest existing number).
2. Write the file with the required `-- title:` and `-- description:` headers and a self-contained query body.
3. Run `just render` from `queries/`. It will:
   - run `ggsql run` for each `q*.gsql` and capture the Vega-Lite JSON spec
   - generate an `.svg` thumbnail via `vl-convert`
   - regenerate `README.md` with the catalog table
4. Read your own README.md to see the new entry in context. If the title or description reads poorly next to the others, edit the headers and re-render. Click the SVG to view full size; paste the JSON spec into [vega.github.io/editor](https://vega.github.io/editor) to debug encoding.

## Known gotchas

- **HTTPFS does not work** in ggsql v0.2.7. `INSTALL httpfs; LOAD httpfs;` inside a `.gsql` file is silently ignored. Stick to local DuckDB files. (Tracking upstream.)
- **The `--reader` URI parser drops leading slashes** — absolute paths fail silently and create phantom DuckDB files at the wrong relative path. Always use relative paths from `queries/`. ([posit-dev/ggsql#345](https://github.com/posit-dev/ggsql/issues/345))
- **Only one writer ships in v0.2.7**: `vegalite`. SVG conversion happens in `render.py` via `vl-convert-python`. (`plotters` for native SVG/PNG is gated behind a non-default Cargo feature.)
- **`VISUALISE` not `VISUALIZE`.** ggsql uses British spelling for the keyword.
- **`SELECT * FROM read_csv_auto('https://...')` looks like it should work but doesn't** — same HTTPFS gap. Use `just setup` to build the DuckDB locally first.

## Out of scope

- copairs activity / consistency results (different DB, requires `jump_metadata_augmented.duckdb` or `copairs_results.duckdb` — not built by `just setup`)
- Interactive widgets / parameterized queries (no ggsql support yet)
- Anything requiring image fetching, broad-babel translation, copairs, AnnData, or NCBI lookups → use the marimo catalog and the `compose-notebook` skill instead
