# /// script
# requires-python = ">=3.11"
# dependencies = ["marimo", "polars", "requests", "matplotlib", "seaborn"]
# ///

import marimo

__generated_with = "0.23.1"
app = marimo.App(width="medium")

with app.setup:
    import marimo as mo
    import polars as pl
    import requests
    import seaborn as sns
    import matplotlib.pyplot as plt
    from random import choices, seed as seed_rng

    ZENODO_RECORD = "15029005"
    DISTANCE_DATASETS = ("crispr", "orf")


@app.function
def latest_zenodo_id(record: str = ZENODO_RECORD) -> str:
    """Resolve the latest versioned record ID for a Zenodo concept record."""
    return requests.get(
        f"https://zenodo.org/api/records/{record}/versions/latest"
    ).json()["id"]


@app.function
def load_distance_matrix(dataset: str) -> pl.LazyFrame:
    """Lazy-scan the all-vs-all cosine similarity matrix for a dataset."""
    latest_id = latest_zenodo_id()
    url = (
        f"https://zenodo.org/api/records/{latest_id}/files/"
        f"{dataset}_cosinesim_full.parquet/content"
    )
    return pl.scan_parquet(url)


@app.function
def sample_submatrix(
    distances: pl.LazyFrame, n: int, rseed: int = 42
) -> pl.DataFrame:
    """Pick n random rows+cols and return the corresponding square submatrix."""
    seed_rng(rseed)
    cols = distances.collect_schema().names()
    idx = sorted(choices(range(len(cols)), k=n))
    sampled_cols = [cols[i] for i in idx]
    return (
        distances.with_row_index()
        .filter(pl.col("index").is_in(idx))
        .select(pl.col(sampled_cols))
        .collect()
    )


@app.function
def plot_similarity_heatmap(submatrix: pl.DataFrame):
    """Render a labeled square cosine similarity heatmap (1=identical, -1=anticorrelated)."""
    pdf = submatrix.to_pandas()
    pdf.index = pdf.columns
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(
        pdf,
        annot=True,
        fmt=".3f",
        vmin=-1,
        vmax=1,
        cmap=sns.color_palette("vlag", as_cmap=True),
        ax=ax,
    )
    plt.yticks(rotation=30)
    plt.tight_layout()
    return fig


@app.cell
def intro():
    mo.md(
        """
        # Explore perturbation similarity

        Query all-vs-all cosine similarity matrices from
        [Zenodo](https://zenodo.org/records/13259495) to find phenotypically
        similar perturbations.

        Values are cosine similarities ranging from 1 (identical profiles)
        through 0 (uncorrelated) to -1 (perfectly anticorrelated). Sort
        descending to find nearest neighbors.
        """
    )
    return


@app.cell
def controls():
    dataset_selector = mo.ui.dropdown(
        options=list(DISTANCE_DATASETS),
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
def loaded_distances(dataset_selector):
    distances = load_distance_matrix(dataset_selector.value)
    return (distances,)


@app.cell
def submatrix_header():
    mo.md("## Sampled distance matrix")
    return


@app.cell
def sampled_distances(distances, n_perturbations, random_seed):
    submatrix = sample_submatrix(distances, n_perturbations.value, random_seed.value)
    submatrix
    return (submatrix,)


@app.cell
def heatmap_header():
    mo.md("## Similarity heatmap")
    return


@app.cell
def heatmap(submatrix):
    plot_similarity_heatmap(submatrix)
    return


if __name__ == "__main__":
    app.run()
