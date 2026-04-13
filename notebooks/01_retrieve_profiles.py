# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "broad-babel==0.1.31",
#     "duckdb==1.5.2",
#     "jump-portrait==0.1.0",
#     "marimo",
#     "polars",
#     "requests",
#     "seaborn==0.13.2",
# ]
# ///

import marimo

__generated_with = "0.23.1"
app = marimo.App(width="medium")

with app.setup:
    import marimo as mo
    import polars as pl
    import requests

    PROFILE_INDEX_URL = "https://raw.githubusercontent.com/jump-cellpainting/datasets/v0.11.0/manifests/profile_index.json"
    SUBSETS = ("crispr", "orf", "compound")


@app.function
def load_profile_index() -> list[dict]:
    """Fetch the JUMP profile manifest as a list of subset entries."""
    return requests.get(PROFILE_INDEX_URL).json()


@app.function
def load_profiles(subset: str) -> pl.LazyFrame:
    """Lazy-scan the parquet file for a named JUMP subset (e.g. 'crispr')."""
    index = load_profile_index()
    url = pl.DataFrame(index).filter(pl.col("subset") == subset).item(0, "url")
    return pl.scan_parquet(url)


@app.function
def profile_stats(subsets: tuple[str, ...] = SUBSETS) -> pl.DataFrame:
    """Row/column/size stats for each named subset."""
    info = {k: [] for k in ("dataset", "#rows", "#cols", "#Metadata cols", "Size (MB)")}
    for name in subsets:
        data = load_profiles(name)
        n_rows = data.select(pl.len()).collect().item()
        schema = data.collect_schema()
        n_cols = schema.len()
        n_meta = sum(1 for c in schema if c.startswith("Metadata"))
        est_mb = int(round(4.03 * n_rows * n_cols / 1e6))
        for k, v in zip(info, (name, n_rows, n_cols, n_meta, est_mb)):
            info[k].append(v)
    return pl.DataFrame(info)


@app.cell
def intro():
    mo.md("""
    # Retrieve JUMP profiles

    The JUMP Cell Painting project provides processed morphological profiling datasets.
    Choose the dataset that matches your perturbation type:

    - **`crispr`**: CRISPR knockout genetic perturbations
    - **`orf`**: Open Reading Frame (ORF) overexpression perturbations
    - **`compound`**: Chemical compound perturbations
    - **`all`**: Combined dataset (use for cross-modality comparisons)

    Each dataset comes in two processing versions:

    - **Standard** (e.g., `crispr`): Fully processed including batch correction. Recommended for most analyses.
    - **Interpretable** (e.g., `crispr_interpretable`): Without batch correction transformations. Use when interpreting individual features.

    All datasets are Parquet files on AWS S3. The manifest below contains recommended profiles with links to the processing recipe and configuration used.
    """)
    return


@app.cell
def manifest_table():
    profile_index = load_profile_index()
    display_df = pl.DataFrame(profile_index).select(
        "subset",
        pl.col("url").str.extract(r"([^/]+)\.parquet$").alias("filename"),
        pl.col("recipe_permalink")
        .str.extract(r"tree/([^/]+)$")
        .str.slice(0, 7)
        .alias("recipe_version"),
        pl.col("config_permalink")
        .str.extract(r"([^/]+)\.json$")
        .alias("config"),
    )
    mo.ui.table(display_df)
    return


@app.cell
def subset_picker():
    subset_selector = mo.ui.dropdown(
        options=list(SUBSETS),
        value="crispr",
        label="Dataset",
    )
    subset_selector
    return (subset_selector,)


@app.cell
def selected_profiles(subset_selector):
    data = load_profiles(subset_selector.value)
    return (data,)


@app.cell
def stats_header():
    mo.md("## Dataset statistics")
    return


@app.cell
def stats_table():
    profile_stats()
    return


@app.cell
def metadata_header():
    mo.md("## Metadata columns (sample)")
    return


@app.cell
def metadata_sample(data):
    data.select(pl.col("^Metadata.*$")).head(5).collect()
    return


@app.cell
def features_header():
    mo.md("## Feature columns (sample)")
    return


@app.cell
def features_sample(data):
    data.select(pl.all().exclude("^Metadata.*$")).head(5).collect()
    return


if __name__ == "__main__":
    app.run()
