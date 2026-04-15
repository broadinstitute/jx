# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo",
#     "polars",
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
app = marimo.App(
    width="medium",
    layout_file="layouts/07_compound_neighborhood.grid.json",
)

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
    from nb04_display_images import (
        display_site,
        lookup_site_metadata,
        pick_first_site,
    )
    from nb05_explore_similarity import load_distance_matrix


@app.function
def load_similarity_matrix(dataset: str) -> pl.LazyFrame:
    """Lazy-scan the cosine-similarity matrix, preferring the local cache."""
    cached = CACHE_DIR / f"{dataset}_cosinesim_full.parquet"
    if cached.exists():
        return pl.scan_parquet(cached)
    return load_distance_matrix(dataset)


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
    mo.md("""
    # Compound neighborhood vignette

    *"I've seen an interesting phenotype from compound X. What else in JUMP
    looks like it? What do those neighbors target? Show me the images."*

    This notebook composes four catalog notebooks via plain Python imports
    (`from nb01_retrieve_profiles import load_profiles`, etc.), available
    because each catalog file is a marimo notebook with hoisted
    `@app.function`s.

    The full ~250 MB cosine matrix is large enough that it's worth caching
    once to `~/.cache/jx/` (override with `JX_CACHE`).
    """)
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
def neighbors_table(dataset_selector, k_neighbors, query_input):
    similarities = load_similarity_matrix(dataset_selector.value)
    neighbors = nearest_neighbors(
        similarities, query_input.value, k_neighbors.value
    )
    return (neighbors,)


@app.cell
def annotation_header():
    mo.md("""
    ## Top neighbors with annotations (interactive)
    """)
    return


@app.cell
def annotated_neighbors(dataset_selector, neighbors, query_input):
    jcp_ids = (query_input.value, *neighbors.get_column("JCP2022").to_list())
    profiles = load_profiles(dataset_selector.value)
    gene_id_mapper = build_mapper(jcp_ids, "NCBI_Gene_ID")
    annotated = (
        annotate_profiles(profiles, jcp_ids)
        .select("Metadata_JCP2022", "name", "pert_type")
        .unique(subset=["Metadata_JCP2022"])
        .with_columns(
            pl.col("Metadata_JCP2022")
            .replace(gene_id_mapper)
            .alias("ncbi_gene_id")
        )
    )
    merged = neighbors.join(
        annotated, left_on="JCP2022", right_on="Metadata_JCP2022", how="left"
    )

    merged_table = mo.ui.table(
        merged,
        selection="single",
        page_size=10,
        label="Click a row to display its 5-channel images alongside the query.",
    )
    merged_table
    return merged, merged_table


@app.cell
def images_header():
    mo.md("""
    ## Side-by-side images — query vs selected neighbor
    """)
    return


@app.cell
def image_grid(merged, merged_table, query_input):
    selected = merged_table.value
    if selected is not None and not selected.is_empty():
        top_hit = selected.row(0, named=True)["JCP2022"]
    else:
        top_hit = merged.row(0, named=True)["JCP2022"]

    figures = []
    for jcp in (query_input.value, top_hit):
        sites = lookup_site_metadata(jcp, input_column="JCP2022")
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
    mo.hstack([mo.as_html(f) for f in figures], justify="start", gap=2)
    return


if __name__ == "__main__":
    app.run()
