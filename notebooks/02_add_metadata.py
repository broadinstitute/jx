# /// script
# requires-python = ">=3.11"
# dependencies = ["marimo", "polars", "requests", "broad-babel"]
# ///

import marimo

__generated_with = "0.13.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import polars as pl
    import requests
    from broad_babel.query import get_mapper
    return get_mapper, mo, pl, requests


@app.cell
def _(mo):
    mo.md(
        """
        # Add metadata to profiles

        Morphological profiles ship with minimal metadata (source, plate, well, JCP ID).
        Use [broad-babel](https://github.com/broadinstitute/monorepo/tree/main/libs/jump_babel)
        to expand: perturbation type (`trt`, `negcon`, `poscon`) and standard gene/compound names.
        """
    )
    return


@app.cell
def _(mo):
    subset_selector = mo.ui.dropdown(
        options=["crispr", "orf", "compound"],
        value="crispr",
        label="Dataset",
    )
    n_samples = mo.ui.slider(
        start=5, stop=50, step=5, value=10, label="Number of samples"
    )
    mo.hstack([subset_selector, n_samples])
    return n_samples, subset_selector


@app.cell
def _(pl, requests, subset_selector):
    INDEX_FILE = "https://raw.githubusercontent.com/jump-cellpainting/datasets/v0.11.0/manifests/profile_index.json"
    response = requests.get(INDEX_FILE)
    profile_index = response.json()
    url = (
        pl.DataFrame(profile_index)
        .filter(pl.col("subset") == subset_selector.value)
        .item(0, "url")
    )
    profiles = pl.scan_parquet(url)
    return (profiles,)


@app.cell
def _(n_samples, pl, profiles):
    jcp_ids = (
        profiles.select(pl.col("Metadata_JCP2022")).unique().collect().to_series().sort()
    )
    subsample = jcp_ids.sample(n_samples.value, seed=42)
    # Add a well-known negative control
    subsample = (*subsample, "JCP2022_800002")
    return jcp_ids, subsample


@app.cell
def _(mo):
    mo.md("## Perturbation type mapper")
    return


@app.cell
def _(get_mapper, pl, subsample):
    pert_mapper = get_mapper(
        subsample, input_column="JCP2022", output_columns="JCP2022,pert_type"
    )
    pl.DataFrame(
        {"JCP2022": list(pert_mapper.keys()), "pert_type": list(pert_mapper.values())}
    )
    return (pert_mapper,)


@app.cell
def _(mo):
    mo.md("## Standard name mapper")
    return


@app.cell
def _(get_mapper, pl, subsample):
    name_mapper = get_mapper(
        subsample, input_column="JCP2022", output_columns="JCP2022,standard_key"
    )
    pl.DataFrame(
        {"JCP2022": list(name_mapper.keys()), "standard_key": list(name_mapper.values())}
    )
    return (name_mapper,)


@app.cell
def _(mo):
    mo.md("## Profiles with metadata")
    return


@app.cell
def _(name_mapper, pert_mapper, pl, profiles, subsample):
    subsample_profiles = profiles.filter(
        pl.col("Metadata_JCP2022").is_in(subsample)
    ).collect()
    profiles_with_meta = subsample_profiles.with_columns(
        pl.col("Metadata_JCP2022").replace(pert_mapper).alias("pert_type"),
        pl.col("Metadata_JCP2022").replace(name_mapper).alias("name"),
    )
    profiles_with_meta.select(
        pl.col(("name", "pert_type", "^Metadata.*$", "^X_[0-3]$"))
    ).sort(by="pert_type")
    return


if __name__ == "__main__":
    app.run()
