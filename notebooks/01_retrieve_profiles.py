# /// script
# requires-python = ">=3.11"
# dependencies = ["marimo", "polars", "requests"]
# ///

import marimo

__generated_with = "0.23.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import polars as pl
    import requests

    return mo, pl, requests


@app.cell
def _(mo):
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
def _(requests):
    INDEX_FILE = "https://raw.githubusercontent.com/jump-cellpainting/datasets/v0.11.0/manifests/profile_index.json"
    response = requests.get(INDEX_FILE)
    profile_index = response.json()
    return (profile_index,)


@app.cell
def _(mo, pl, profile_index):
    profile_df = pl.DataFrame(profile_index)
    display_df = profile_df.select(
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
def _(mo):
    subset_selector = mo.ui.dropdown(
        options=["crispr", "orf", "compound"],
        value="crispr",
        label="Dataset",
    )
    subset_selector
    return (subset_selector,)


@app.cell
def _(pl, profile_index, subset_selector):
    filepaths = {
        d["subset"]: d["url"]
        for d in profile_index
        if d["subset"] in ("crispr", "orf", "compound")
    }
    selected_url = filepaths[subset_selector.value]
    data = pl.scan_parquet(selected_url)
    return data, filepaths


@app.cell
def _(mo):
    mo.md("""
    ## Dataset statistics
    """)
    return


@app.cell
def _(filepaths, pl):
    info = {k: [] for k in ("dataset", "#rows", "#cols", "#Metadata cols", "Size (MB)")}
    for name, path in filepaths.items():
        _data = pl.scan_parquet(path)
        n_rows = _data.select(pl.len()).collect().item()
        schema = _data.collect_schema()
        metadata_cols = [col for col in schema.keys() if col.startswith("Metadata")]
        n_cols = schema.len()
        n_meta_cols = len(metadata_cols)
        estimated_size = int(round(4.03 * n_rows * n_cols / 1e6, 0))
        for k, v in zip(info.keys(), (name, n_rows, n_cols, n_meta_cols, estimated_size)):
            info[k].append(v)
    stats_df = pl.DataFrame(info)
    stats_df
    return


@app.cell
def _(mo):
    mo.md("""
    ## Metadata columns (sample)
    """)
    return


@app.cell
def _(data, pl):
    data.select(pl.col("^Metadata.*$")).head(5).collect()
    return


@app.cell
def _(mo):
    mo.md("""
    ## Feature columns (sample)
    """)
    return


@app.cell
def _(data, pl):
    features_sample = data.select(pl.all().exclude("^Metadata.*$")).head(5).collect()
    features_sample
    return


if __name__ == "__main__":
    app.run()
