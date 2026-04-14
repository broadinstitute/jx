# /// script
# requires-python = ">=3.11"
# dependencies = ["marimo", "polars", "requests", "broad-babel"]
# ///

import marimo

__generated_with = "0.23.1"
app = marimo.App(width="medium")

with app.setup:
    import marimo as mo
    import polars as pl
    import requests
    from broad_babel.query import get_mapper

    PROFILE_INDEX_URL = "https://raw.githubusercontent.com/jump-cellpainting/datasets/v0.11.0/manifests/profile_index.json"
    SUBSETS = ("crispr", "orf", "compound")
    NEGCON_JCP = "JCP2022_800002"


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
    """Sample n perturbation IDs from a profile frame, appending a known negcon."""
    jcp_ids = (
        profiles.select(pl.col("Metadata_JCP2022")).unique().collect().to_series().sort()
    )
    sample = jcp_ids.sample(n, seed=seed)
    return (*sample, negcon)


@app.function
def build_mapper(jcp_ids: tuple[str, ...], output_column: str) -> dict[str, str]:
    """broad-babel mapper from JCP2022 IDs to any metadata column."""
    return get_mapper(
        jcp_ids,
        input_column="JCP2022",
        output_columns=f"JCP2022,{output_column}",
    )


@app.function
def annotate_profiles(
    profiles: pl.LazyFrame, jcp_ids: tuple[str, ...]
) -> pl.DataFrame:
    """Filter to a JCP subsample and attach pert_type + standard name columns."""
    subset = profiles.filter(pl.col("Metadata_JCP2022").is_in(jcp_ids)).collect()
    pert_mapper = build_mapper(jcp_ids, "pert_type")
    name_mapper = build_mapper(jcp_ids, "standard_key")
    return subset.with_columns(
        pl.col("Metadata_JCP2022").replace(pert_mapper).alias("pert_type"),
        pl.col("Metadata_JCP2022").replace(name_mapper).alias("name"),
    )


@app.cell
def intro():
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
def controls():
    subset_selector = mo.ui.dropdown(
        options=list(SUBSETS),
        value="crispr",
        label="Dataset",
    )
    n_samples = mo.ui.slider(
        start=5, stop=50, step=5, value=10, label="Number of samples"
    )
    mo.hstack([subset_selector, n_samples])
    return n_samples, subset_selector


@app.cell
def loaded_profiles(subset_selector):
    profiles = load_profiles(subset_selector.value)
    return (profiles,)


@app.cell
def sampled_ids(profiles, n_samples):
    subsample = sample_with_negcon(profiles, n_samples.value)
    return (subsample,)


@app.cell
def pert_header():
    mo.md("## Perturbation type mapper")
    return


@app.cell
def pert_table(subsample):
    pert_mapper = build_mapper(subsample, "pert_type")
    pl.DataFrame(
        {"JCP2022": list(pert_mapper.keys()), "pert_type": list(pert_mapper.values())}
    )
    return


@app.cell
def name_header():
    mo.md("## Standard name mapper")
    return


@app.cell
def name_table(subsample):
    name_mapper = build_mapper(subsample, "standard_key")
    pl.DataFrame(
        {"JCP2022": list(name_mapper.keys()), "standard_key": list(name_mapper.values())}
    )
    return


@app.cell
def annotated_header():
    mo.md("## Profiles with metadata")
    return


@app.cell
def annotated_table(profiles, subsample):
    profiles_with_meta = annotate_profiles(profiles, subsample)
    profiles_with_meta.select(
        pl.col(("name", "pert_type", "^Metadata.*$", "^X_[0-3]$"))
    ).sort(by="pert_type")
    return


if __name__ == "__main__":
    app.run()
