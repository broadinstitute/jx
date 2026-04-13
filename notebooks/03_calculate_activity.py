# /// script
# requires-python = ">=3.11"
# dependencies = ["marimo", "polars", "requests", "broad-babel", "copairs", "seaborn", "matplotlib"]
# ///

import marimo

__generated_with = "0.13.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import polars as pl
    import polars.selectors as cs
    import requests
    import seaborn as sns
    from broad_babel.query import get_mapper
    from copairs.map import average_precision
    return average_precision, cs, get_mapper, mo, pl, requests, sns


@app.cell
def _(mo):
    mo.md(
        """
        # Calculate phenotypic activity

        Compute mean average precision (mAP) replicability scores using
        [copairs](https://github.com/cytomining/copairs). mAP measures how
        similar replicates of a perturbation are relative to negative controls —
        higher values indicate stronger, more reproducible phenotypes.
        """
    )
    return


@app.cell
def _(mo):
    n_samples = mo.ui.slider(
        start=5, stop=50, step=5, value=10, label="Number of perturbations to sample"
    )
    n_samples
    return (n_samples,)


@app.cell
def _(pl, requests):
    INDEX_FILE = "https://raw.githubusercontent.com/jump-cellpainting/datasets/v0.11.0/manifests/profile_index.json"
    response = requests.get(INDEX_FILE)
    profile_index = response.json()
    CRISPR_URL = (
        pl.DataFrame(profile_index).filter(pl.col("subset") == "crispr").item(0, "url")
    )
    profiles = pl.scan_parquet(CRISPR_URL)
    return (profiles,)


@app.cell
def _(n_samples, pl, profiles):
    jcp_ids = (
        profiles.select(pl.col("Metadata_JCP2022")).unique().collect().to_series().sort()
    )
    subsample = jcp_ids.sample(n_samples.value, seed=42)
    subsample = (*subsample, "JCP2022_800002")  # negative control
    profiles_subset = profiles.filter(pl.col("Metadata_JCP2022").is_in(subsample)).collect()
    # Keep only plates that contain our sampled perturbations (excluding control)
    unique_plates = profiles_subset.filter(pl.col("Metadata_JCP2022") != subsample[-1])[
        "Metadata_Plate"
    ].unique()
    perts_controls = profiles_subset.filter(pl.col("Metadata_Plate").is_in(unique_plates))
    return perts_controls, subsample


@app.cell
def _(get_mapper, perts_controls, pl, subsample):
    pert_mapper = get_mapper(
        subsample, input_column="JCP2022", output_columns="JCP2022,pert_type"
    )
    perts_controls_annotated = perts_controls.with_columns(
        pl.col("Metadata_JCP2022").replace(pert_mapper).alias("pert_type")
    )
    return (perts_controls_annotated,)


@app.cell
def _(mo):
    mo.md(
        """
        ## copairs mean average precision

        Parameters: perturbations matched by `Metadata_JCP2022`, negative controls
        distinguished by `pert_type`. See the
        [copairs wiki](https://github.com/cytomining/copairs/wiki/Defining-parameters)
        for details.
        """
    )
    return


@app.cell
def _(average_precision, cs, perts_controls_annotated, pl):
    pos_sameby = ["Metadata_JCP2022"]
    pos_diffby = []
    neg_sameby = []
    neg_diffby = ["pert_type"]
    batch_size = 20000

    metadata_selector = cs.starts_with(("Metadata", "pert_type"))
    meta = perts_controls_annotated.select(metadata_selector)
    features = perts_controls_annotated.select(~metadata_selector)

    result = pl.DataFrame(
        average_precision(
            meta.to_pandas(),
            features.to_numpy(),
            pos_sameby,
            pos_diffby,
            neg_sameby,
            neg_diffby,
            batch_size,
        )
    )
    result.head()
    return (result,)


@app.cell
def _(mo):
    mo.md("## Activity distribution by gene")
    return


@app.cell
def _(get_mapper, pl, result, sns, subsample):
    name_mapper = get_mapper(
        subsample, input_column="JCP2022", output_columns="JCP2022,standard_key"
    )
    to_plot = result.filter(pl.col("pert_type") == "trt").with_columns(
        pl.col("Metadata_JCP2022").replace(name_mapper).alias("Perturbed gene")
    )
    _ax = sns.stripplot(data=to_plot.to_pandas(), x="average_precision", y="Perturbed gene")
    _ax.figure
    return


if __name__ == "__main__":
    app.run()
