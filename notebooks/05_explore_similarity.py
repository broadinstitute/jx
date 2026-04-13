# /// script
# requires-python = ">=3.11"
# dependencies = ["marimo", "polars", "requests", "matplotlib", "seaborn"]
# ///

import marimo

__generated_with = "0.13.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import polars as pl
    import requests
    import matplotlib.pyplot as plt
    import seaborn as sns
    from random import choices, seed
    return choices, mo, pl, plt, requests, seed, sns


@app.cell
def _(mo):
    mo.md(
        """
        # Explore perturbation similarity

        Query all-vs-all cosine similarity matrices from
        [Zenodo](https://zenodo.org/records/13259495) to find phenotypically
        similar perturbations.

        Values range from 0 (identical profiles) through 1 (uncorrelated) to 2
        (perfectly anticorrelated).
        """
    )
    return


@app.cell
def _(mo):
    dataset_selector = mo.ui.dropdown(
        options=["crispr", "orf"],
        value="crispr",
        label="Dataset",
    )
    n_perturbations = mo.ui.slider(
        start=3, stop=20, step=1, value=3, label="Number of perturbations to sample"
    )
    random_seed = mo.ui.number(value=42, label="Random seed")
    mo.hstack([dataset_selector, n_perturbations, random_seed])
    return dataset_selector, n_perturbations, random_seed


@app.cell
def _(dataset_selector, pl, requests):
    latest_id = requests.get(
        "https://zenodo.org/api/records/15029005/versions/latest"
    ).json()["id"]
    distances = pl.scan_parquet(
        f"https://zenodo.org/api/records/{latest_id}/files/{dataset_selector.value}_cosinesim_full.parquet/content"
    )
    return (distances,)


@app.cell
def _(mo):
    mo.md("## Sampled distance matrix")
    return


@app.cell
def _(choices, distances, n_perturbations, pl, random_seed, seed):
    seed(random_seed.value)
    cols = distances.collect_schema().names()
    ncols = len(cols)
    sampled_col_idx = sorted(choices(range(ncols), k=n_perturbations.value))
    sampled_cols = [cols[ix] for ix in sampled_col_idx]
    sampled_distances = (
        distances.with_row_index()
        .filter(pl.col("index").is_in(sampled_col_idx))
        .select(pl.col(sampled_cols))
        .collect()
    )
    sampled_distances
    return (sampled_distances,)


@app.cell
def _(mo):
    mo.md("## Similarity heatmap")
    return


@app.cell
def _(plt, sampled_distances, sns):
    _pdf = sampled_distances.to_pandas()
    _pdf.index = _pdf.columns
    _fig, _ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(
        _pdf,
        annot=True,
        fmt=".3f",
        vmin=0,
        vmax=2,
        cmap=sns.color_palette("vlag", as_cmap=True),
        ax=_ax,
    )
    plt.yticks(rotation=30)
    plt.tight_layout()
    _fig
    return


if __name__ == "__main__":
    app.run()
