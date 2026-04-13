# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo",
#     "polars",
#     "pandas",
#     "requests",
#     "matplotlib",
#     "seaborn",
#     "duckdb",
#     "numpy",
#     "broad-babel",
#     "jump-portrait",
# ]
# ///

import marimo

__generated_with = "0.23.1"
app = marimo.App(width="medium")

with app.setup:
    import importlib.util
    import os
    from pathlib import Path

    import duckdb
    import marimo as mo
    import pandas as pd
    import polars as pl
    from broad_babel import query as bq
    from jump_portrait.fetch import get_index_file, get_table

    NOTEBOOK_DIR = Path(__file__).parent
    CACHE_DIR = Path(os.environ.get("JX_CACHE", Path.home() / ".cache" / "jx"))

    def _load_catalog(stem: str):
        path = NOTEBOOK_DIR / f"{stem}.py"
        spec = importlib.util.spec_from_file_location(stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    nb01 = _load_catalog("01_retrieve_profiles")
    nb02 = _load_catalog("02_add_metadata")
    nb04 = _load_catalog("04_display_images")
    nb05 = _load_catalog("05_explore_similarity")

    load_profiles = nb01.load_profiles
    annotate_profiles = nb02.annotate_profiles
    build_mapper = nb02.build_mapper
    pick_first_site = nb04.pick_first_site
    display_site = nb04.display_site


@app.function
def lookup_site_metadata(jcp: str):
    """Resolve a JCP2022 ID to its imaging-site rows.

    Replaces ``nb04.lookup_site_metadata`` because the upstream
    ``jump_portrait.fetch.get_item_location_metadata`` uses a duckdb
    replacement scan against ``meta_wells``, which ``get_table('well')``
    returns as a path string instead of a DataFrame. We materialise it
    here and run the same join.
    """
    meta_wells = pd.read_csv(get_table("well"))  # noqa: F841 — used by duckdb scan
    index_file = get_index_file()
    jcp_pairs = bq.run_query(
        query=jcp, input_column="JCP2022", output_columns="JCP2022,standard_key"
    )
    jcp_keys = tuple(dict(jcp_pairs).keys())
    with duckdb.connect() as con:
        found_rows = con.sql(
            f"SELECT *, '{jcp}' AS standard_key FROM meta_wells "
            f"WHERE Metadata_JCP2022 IN {list(jcp_keys)}"
        )
        return con.sql(
            f"FROM found_rows JOIN (FROM read_parquet('{index_file}')) "
            "USING(Metadata_Source,Metadata_Plate,Metadata_Well)"
        ).to_arrow_table()


@app.function
def load_similarity_matrix(dataset: str) -> pl.LazyFrame:
    """Lazy-scan the cosine-similarity matrix, preferring the local cache."""
    cached = CACHE_DIR / f"{dataset}_cosinesim_full.parquet"
    if cached.exists():
        return pl.scan_parquet(cached)
    return nb05.load_distance_matrix(dataset)


@app.function
def nearest_neighbors(
    similarities: pl.LazyFrame, query_jcp: str, k: int
) -> pl.DataFrame:
    """Top-k JCP2022 IDs by cosine similarity to a query (excluding self)."""
    cols = similarities.collect_schema().names()
    if query_jcp not in cols:
        raise ValueError(f"{query_jcp} not in similarity matrix ({len(cols)} cols)")
    query_idx = cols.index(query_jcp)
    row = similarities.slice(query_idx, 1).collect().row(0)
    return (
        pl.DataFrame({"JCP2022": cols, "similarity": list(row)})
        .filter(pl.col("JCP2022") != query_jcp)
        .sort("similarity", descending=True)
        .head(k)
    )


@app.cell
def intro():
    mo.md(
        """
        # Compound neighborhood vignette

        *"I've seen an interesting phenotype from compound X. What else in JUMP
        looks like it? What do those neighbors target? Show me the images."*

        This notebook composes four catalog notebooks:

        - **01_retrieve_profiles** — `load_profiles`
        - **02_add_metadata** — `annotate_profiles`, `build_mapper`
        - **04_display_images** — `lookup_site_metadata`, `pick_first_site`, `display_site`
        - **05_explore_similarity** — `load_distance_matrix`

        Functions are imported from sibling notebooks via `importlib`; the only
        new logic is the `load_similarity_matrix` cache wrapper and the
        `nearest_neighbors` helper.

        The full ~250 MB cosine matrix is large enough that it's worth caching
        once to `~/.cache/jx/` (override with `JX_CACHE`) — set the cache up
        with `curl -o ~/.cache/jx/crispr_cosinesim_full.parquet
        https://zenodo.org/api/records/<id>/files/crispr_cosinesim_full.parquet/content`.
        """
    )
    return


@app.cell
def controls():
    dataset_selector = mo.ui.dropdown(
        options=["crispr", "orf"],
        value="crispr",
        label="Similarity matrix",
    )
    query_input = mo.ui.text(
        value="JCP2022_806962",
        label="Query JCP2022 ID",
    )
    k_neighbors = mo.ui.slider(
        start=3, stop=12, step=1, value=5, label="Top-k neighbors"
    )
    mo.hstack([dataset_selector, query_input, k_neighbors])
    return dataset_selector, k_neighbors, query_input


@app.cell
def neighbors_header():
    mo.md("## Nearest neighbors by cosine distance")
    return


@app.cell
def neighbors_table(dataset_selector, query_input, k_neighbors):
    similarities = load_similarity_matrix(dataset_selector.value)
    neighbors = nearest_neighbors(similarities, query_input.value, k_neighbors.value)
    neighbors
    return (neighbors,)


@app.cell
def annotation_header():
    mo.md("## Annotate neighbors with names and targets")
    return


@app.cell
def annotated_neighbors(dataset_selector, query_input, neighbors):
    jcp_ids = (query_input.value, *neighbors.get_column("JCP2022").to_list())
    profiles = load_profiles(dataset_selector.value)
    gene_id_mapper = build_mapper(jcp_ids, "NCBI_Gene_ID")
    annotated = (
        annotate_profiles(profiles, jcp_ids)
        .select("Metadata_JCP2022", "name", "pert_type")
        .unique(subset=["Metadata_JCP2022"])
        .with_columns(
            pl.col("Metadata_JCP2022").replace(gene_id_mapper).alias("ncbi_gene_id")
        )
    )
    merged = neighbors.join(
        annotated, left_on="JCP2022", right_on="Metadata_JCP2022", how="left"
    )
    merged
    return (merged,)


@app.cell
def images_header():
    mo.md("## Side-by-side images (query + top hit)")
    return


@app.cell
def image_grid(query_input, merged):
    top_hit = merged.row(0, named=True)["JCP2022"]
    figures = []
    for jcp in (query_input.value, top_hit):
        sites = lookup_site_metadata(jcp)
        site = pick_first_site(sites)
        figures.append(
            display_site(
                site["Source"],
                site["Batch"],
                site["Plate"],
                site["Well"],
                site["Site"],
                jcp,
            )
        )
    mo.vstack([mo.as_html(f) for f in figures])
    return


if __name__ == "__main__":
    app.run()
