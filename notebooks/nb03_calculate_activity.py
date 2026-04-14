# /// script
# requires-python = ">=3.11"
# dependencies = ["marimo", "polars", "requests", "broad-babel", "copairs", "seaborn", "matplotlib"]
# ///

import marimo

__generated_with = "0.23.1"
app = marimo.App(width="medium")

with app.setup:
    import marimo as mo
    import polars as pl
    import polars.selectors as cs
    import requests
    import seaborn as sns
    from broad_babel.query import get_mapper
    from copairs.map import average_precision

    PROFILE_INDEX_URL = "https://raw.githubusercontent.com/jump-cellpainting/datasets/v0.11.0/manifests/profile_index.json"
    SUBSETS = ("crispr", "orf", "compound")
    NEGCON_JCP = "JCP2022_800002"
    COPAIRS_BATCH_SIZE = 20000


@app.function
def load_profiles(subset: str) -> pl.LazyFrame:
    """Lazy-scan the parquet file for a named JUMP subset."""
    index = requests.get(PROFILE_INDEX_URL).json()
    url = pl.DataFrame(index).filter(pl.col("subset") == subset).item(0, "url")
    return pl.scan_parquet(url)


@app.function
def sample_with_negcon(
    profiles: pl.LazyFrame, n: int, seed: int = 42, negcon: str = NEGCON_JCP
) -> tuple[str, ...]:
    """Sample n perturbation IDs, appending a known negative control."""
    jcp_ids = (
        profiles.select(pl.col("Metadata_JCP2022")).unique().collect().to_series().sort()
    )
    sample = jcp_ids.sample(n, seed=seed)
    return (*sample, negcon)


@app.function
def filter_to_complete_plates(
    profiles: pl.LazyFrame, jcp_ids: tuple[str, ...], negcon: str = NEGCON_JCP
) -> pl.DataFrame:
    """Collect sampled perturbations plus every row on the plates they live on."""
    sampled = profiles.filter(pl.col("Metadata_JCP2022").is_in(jcp_ids)).collect()
    unique_plates = sampled.filter(pl.col("Metadata_JCP2022") != negcon)[
        "Metadata_Plate"
    ].unique()
    return sampled.filter(pl.col("Metadata_Plate").is_in(unique_plates))


@app.function
def attach_pert_type(df: pl.DataFrame, jcp_ids: tuple[str, ...]) -> pl.DataFrame:
    """Attach a broad-babel `pert_type` column to a profile frame."""
    pert_mapper = get_mapper(
        jcp_ids, input_column="JCP2022", output_columns="JCP2022,pert_type"
    )
    return df.with_columns(
        pl.col("Metadata_JCP2022").replace(pert_mapper).alias("pert_type")
    )


@app.function
def compute_map(
    df: pl.DataFrame,
    pos_sameby: list[str],
    pos_diffby: list[str],
    neg_sameby: list[str],
    neg_diffby: list[str],
    batch_size: int = COPAIRS_BATCH_SIZE,
) -> pl.DataFrame:
    """Run copairs average-precision with arbitrary same-by / diff-by columns."""
    metadata_selector = cs.starts_with(("Metadata", "pert_type"))
    meta = df.select(metadata_selector)
    features = df.select(~metadata_selector)
    return pl.DataFrame(
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


@app.cell
def intro():
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
def controls():
    subset_selector = mo.ui.dropdown(
        options=list(SUBSETS),
        value="crispr",
        label="Dataset",
    )
    n_samples = mo.ui.slider(
        start=5, stop=50, step=5, value=10, label="Number of perturbations to sample"
    )
    mo.hstack([subset_selector, n_samples])
    return n_samples, subset_selector


@app.cell
def loaded_profiles(subset_selector):
    profiles = load_profiles(subset_selector.value)
    return (profiles,)


@app.cell
def built_inputs(profiles, n_samples):
    subsample = sample_with_negcon(profiles, n_samples.value)
    perts_controls = filter_to_complete_plates(profiles, subsample)
    perts_controls_annotated = attach_pert_type(perts_controls, subsample)
    return (perts_controls_annotated, subsample)


@app.cell
def map_header():
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
def map_result(perts_controls_annotated):
    result = compute_map(
        perts_controls_annotated,
        pos_sameby=["Metadata_JCP2022"],
        pos_diffby=[],
        neg_sameby=[],
        neg_diffby=["pert_type"],
    )
    result.head()
    return (result,)


@app.cell
def activity_header():
    mo.md("## Activity distribution by gene")
    return


@app.cell
def activity_plot(result, subsample):
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
