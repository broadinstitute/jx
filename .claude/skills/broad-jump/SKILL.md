---
name: broad-jump
description: Answer a biological or bookkeeping question about JUMP Cell Painting metadata by writing and running an SQL (or ggsql VISUALISE) query against the canonical metadata DB. Trigger whenever the user asks something that can be answered by counting, grouping, joining, or charting JUMP compounds, CRISPR guides, ORFs, wells, plates, or data-generating sources - e.g. "how many compounds does source_3 have", "which sources share the most plates", "plot perturbations by modality", "find compounds with missing InChIKeys", "list ORFs for gene TP53". Use this when the question is about the catalog itself (what's in JUMP), not about morphological profiles (use compose-notebook for profile-level analysis). Also trigger when the user references the live broad-jump site (https://broadinstitute.github.io/jx/broad-jump/) or says "run this query" / "write a ggsql file".
---

# Query JUMP metadata with SQL / ggsql

## What this skill is for

jx contains the canonical JUMP Cell Painting metadata catalog: ~116K
compounds, ~8K CRISPR guides, ~15K ORFs, 1.15M wells, and the plates /
sources / microscope configs that produced them. This skill is the
agent-facing counterpart to the live [broad-jump site](https://broadinstitute.github.io/jx/broad-jump/):
the site is where a human clicks an example and sees a Vega chart; this
skill is where an agent composes a new query against the same data,
verifies it, and adds it to the gallery if useful.

Use for questions that are answerable by SQL over the 11 metadata tables
listed below. For profile-level analysis (similarity, activity, images)
use `compose-notebook` instead — broad-jump has no profile data.

## Data layout

Two physical surfaces, same content:

1. **Local DuckDB** (default for agents): `jx/queries/data/jump_metadata.duckdb`
   (~170 MB, committed to the repo). 11 tables. Fastest path.
2. **S3 parquet shards** (for the web site + reproducibility): 11 files
   at `https://cellpainting-gallery.s3.amazonaws.com/cpg0042-chandrasekaran-jump/source_all/workspace/publication_data/datasets/v0.13/parquet/<table>.parquet`.
   SNAPPY-compressed (hyparquet in the browser wasm reader doesn't
   support ZSTD — keep this in mind if you regenerate). CORS + range
   requests verified.

Prefer the local DuckDB for agent work. The parquet shards exist so the
browser and anyone without the repo can query the same rows.

## Tables at a glance

Every table is keyed on `Metadata_JCP2022` (e.g. `JCP2022_012345`). The
9th character encodes perturbation modality: `0` = compound, `8` = CRISPR,
`9` = ORF — though the authoritative modality lookup is the `perturbation`
table (see below), which also includes `unknown` / controls.

| Table | Rows | Key columns |
|---|---|---|
| `perturbation` | ~139K | `Metadata_JCP2022`, `Metadata_perturbation_modality` (`compound` / `crispr` / `orf` / `unknown`) |
| `perturbation_control` | 18 | control type + JCP mapping (schema varies - inspect before assuming columns) |
| `compound` | ~116K | `Metadata_JCP2022`, `Metadata_InChIKey`, `Metadata_InChI`, `Metadata_SMILES` |
| `compound_source` | ~126K | `Metadata_JCP2022`, `Metadata_Compound_Source` (many-to-many — a compound can be at multiple sources) |
| `crispr` | ~8K | `Metadata_JCP2022`, `Metadata_Symbol` (gene), plus guide/sequence fields |
| `orf` | ~15K | `Metadata_JCP2022`, `Metadata_Symbol` (gene), plus taxon/transcript fields |
| `plate` | ~2.5K | `Metadata_Source`, `Metadata_Batch`, `Metadata_Plate`, `Metadata_PlateType` (`COMPOUND` / `CRISPR` / `ORF` / `TARGET1` / `TARGET2` / `DMSO` / `POSCON`) |
| `well` | ~1.15M | `Metadata_Source`, `Metadata_Plate`, `Metadata_Well`, `Metadata_JCP2022` — joins a JCP perturbation to a physical well |
| `microscope_config`, `microscope_filter`, `cellprofiler_version` | tiny | reference tables for imaging infrastructure |

Run `DESCRIBE SELECT * FROM <table>` before writing anything non-trivial —
the `perturbation_control`, `microscope_*`, and `cellprofiler_version`
tables are small enough that their schemas are worth checking live rather
than trusting memory.

## Query language

ggsql is regular DuckDB-flavored SQL plus an optional `VISUALISE ... DRAW
... MAPPING ... LABEL ...` trailer that compiles to Vega-Lite. Shape:

```sql
-- Standard SQL up here
WITH ... AS (...)
SELECT col_a, col_b, COUNT(*) AS n
FROM <table>
GROUP BY col_a, col_b

-- Optional plot spec
VISUALISE col_a AS y, n AS x, col_b AS fill
DRAW bar
FACET col_b SETTING ncol => 4          -- optional
LABEL title => 'human-readable title'   -- optional
```

Common `DRAW` layers: `bar`, `line`, `point`, `area`, `histogram`,
`boxplot`, `density`, `path`, `polygon`, `ribbon`, `violin`.

For a plain tabular answer (no chart) omit the `VISUALISE` trailer. Both
the local DuckDB CLI and the ggsql CLI accept SQL-only queries.

## Run a query

**Plain SQL, tabular result.** Fastest loop for exploration:

```bash
duckdb jx/queries/data/jump_metadata.duckdb -c "
  SELECT Metadata_perturbation_modality AS modality, COUNT(*) AS n
  FROM perturbation GROUP BY modality ORDER BY n DESC
"
```

**ggsql, chart output.** Put the query in a file so the `VISUALISE`
trailer is syntactically legal:

```bash
echo "
SELECT Metadata_perturbation_modality AS modality, COUNT(*) AS n
FROM perturbation GROUP BY modality ORDER BY n DESC
VISUALISE modality AS y, n AS x, modality AS fill
DRAW bar LABEL title => 'JUMP perturbations by modality'
" > /tmp/q.gsql

ggsql run /tmp/q.gsql --reader 'duckdb://jx/queries/data/jump_metadata.duckdb'
```

The `duckdb://` URI must resolve to the DuckDB file (relative or absolute
paths both work since ggsql #345 landed — note the convention is
`duckdb://<path>` with a single slash for relative paths, `duckdb:///<abs>`
for absolute).

## Finding working examples

Two sources of pre-vetted queries — read these before writing from
scratch:

1. **`jx/broad-jump/src/examples.ts`** — the preloaded gallery on the
   live site. 9 queries organized by section (Perturbations / Plates &
   wells / Chemistry / Genetics / Infrastructure). Each is a
   `{section, name, query}` object — the `query` field is valid ggsql.
   Copy the text directly; don't re-derive patterns like the InChIKey
   completeness CASE-expression or the compound-sharing self-join if an
   example already demonstrates it.
2. **`jx/queries/q04_compound_inchikey_completeness.gsql`** and
   **`q05_compound_counts_per_source.gsql`** — file-on-disk variants of
   two of the examples above, with header comments. Match this style
   (`-- title:` and `-- description:` lines) when adding new .gsql files.

## Visual verification via the live site

Because the live site shares the exact same query runtime (ggsql-wasm
against the same SNAPPY parquets), pasting an agent-composed query into
the Monaco editor at <https://broadinstitute.github.io/jx/broad-jump/>
runs it under identical semantics. Use this as a cheap correctness check
when it matters — especially for VISUALISE queries where the chart
rendering is easier to sanity-check than the underlying data.

Workflow: write the query, run it locally via the commands above, paste
into the live editor, compare. If the local DuckDB and the browser
disagree, suspect either ZSTD vs SNAPPY drift (re-run the parquet
regeneration) or a function that DuckDB has but ggsql-wasm's subset
doesn't.

## Gotchas

- **Column-name prefix.** Every metadata column in the DuckDB tables
  starts with `Metadata_` (e.g. `Metadata_JCP2022`, `Metadata_Source`).
  This is a JUMP convention — profile-level parquets drop the prefix, but
  these tables keep it. Don't silently strip it in queries.
- **Modality casing.** `Metadata_perturbation_modality` values are
  lowercase: `compound`, `crispr`, `orf`, `unknown`. Don't match on
  `'COMPOUND'`.
- **Plate type casing.** `Metadata_PlateType` values are uppercase:
  `COMPOUND`, `CRISPR`, `ORF`, `TARGET2`, etc. Opposite convention from
  modality. Inconsistent but authoritative.
- **`compound_source` is many-to-many.** One `Metadata_JCP2022` can have
  multiple rows in `compound_source`, one per source where that compound
  appears. Joining `compound` and `compound_source` on JCP2022 will
  multiply rows if you don't aggregate. See the existing "Compounds per
  source (shared vs unique)" example for the self-join pattern.
- **Missing InChIKey sentinel values.** Use the same predicate as q04:
  `IS NULL OR IN ('', 'NA') OR length(...) != 27`. Every source
  currently resolves 100%, but that may not stay true.
- **Profile-level data is not here.** The DuckDB has metadata only — no
  morphological features, no images, no similarity. For those, stop and
  invoke `compose-notebook` instead.

## When to add to the gallery

If you compose a query that's genuinely useful — not one-off diagnostic
work — append it to `jx/broad-jump/src/examples.ts` as a new entry with
a good `section` and `name`, then rebuild (`cd jx/broad-jump && npm run
build`) and push. The deploy workflow will republish the site at
<https://broadinstitute.github.io/jx/broad-jump/>. Do NOT add
diagnostic or exploratory queries to the gallery — the gallery is a
curated surface, not a scratchpad.
