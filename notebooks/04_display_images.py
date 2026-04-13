# /// script
# requires-python = ">=3.11"
# dependencies = ["marimo", "duckdb", "matplotlib", "numpy", "jump-portrait"]
# ///

import marimo

__generated_with = "0.23.1"
app = marimo.App(width="medium")

with app.setup:
    import marimo as mo
    import duckdb
    import matplotlib.colors as mplcolors
    import numpy as np
    from jump_portrait.fetch import get_item_location_metadata, get_jump_image
    from matplotlib import pyplot as plt

    CHANNEL_RGB = {
        "AGP": "#FF7F00",
        "DNA": "#0000FF",
        "ER": "#00FF00",
        "Mito": "#FF0000",
        "RNA": "#FFFF00",
    }
    SITE_FIELDS = ("Source", "Batch", "Plate", "Well", "Site")


@app.function
def lookup_site_metadata(query: str, input_column: str = "standard_key"):
    """Resolve a gene / InChIKey / JCP ID to jump_portrait imaging site rows."""
    if input_column == "standard_key":
        return get_item_location_metadata(query)
    return get_item_location_metadata(query, input_column=input_column)


@app.function
def pick_first_site(location_info) -> dict[str, str]:
    """Return the first imaging site as a {Source, Batch, Plate, Well, Site} dict."""
    with duckdb.connect() as con:
        row = (
            con.sql(
                "SELECT COLUMNS('Metadata_(Source|Batch|Plate|Well|Site)') FROM location_info"
            )
            .to_arrow_table()
            .to_batches()[0]
            .to_pylist()[0]
        )
    return {k: row[f"Metadata_{k}"] for k in SITE_FIELDS}


@app.function
def display_site(
    source: str,
    batch: str,
    plate: str,
    well: str,
    site: str | int,
    label: str,
    int_percentile: float = 99.5,
):
    """Plot all 5 JUMP channels from one imaging site as a 2x3 grid with a label."""
    n_rows, n_cols = 2, 3
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(2.6 * n_cols, 2.6 * n_rows))
    axes = axes.ravel()

    for ax, (channel, rgb) in zip(axes, CHANNEL_RGB.items()):
        cmap = mplcolors.LinearSegmentedColormap.from_list(channel, ("#000", rgb))
        img = get_jump_image(source, batch, plate, well, channel, site)
        ax.imshow(img, vmin=0, vmax=np.percentile(img, int_percentile), cmap=cmap)
        ax.axis("off")
        ax.text(
            0.05, 0.95, channel,
            ha="left", va="top", fontsize=18, color="black",
            bbox=dict(facecolor="white", alpha=0.8, edgecolor="none", boxstyle="round,pad=0.3"),
            transform=ax.transAxes,
        )

    ax = axes[-1]
    ax.text(0.5, 0.5, label, ha="center", va="center", fontsize=20, transform=ax.transAxes)
    ax.axis("off")
    plt.tight_layout()
    return fig


@app.cell
def intro():
    mo.md(
        """
        # Display perturbation images

        Retrieve and plot 5-channel fluorescence images from the JUMP Cell Painting
        dataset using [jump_portrait](https://github.com/broadinstitute/monorepo/tree/main/libs/jump_portrait).

        Enter a gene name, InChIKey, or JCP2022 ID below.
        """
    )
    return


@app.cell
def controls():
    query_input = mo.ui.text(value="RAB30", label="Gene / InChIKey / JCP ID")
    input_col_selector = mo.ui.dropdown(
        options=["standard_key", "InChIKey", "JCP2022"],
        value="standard_key",
        label="Query type",
    )
    intensity_pct = mo.ui.slider(
        start=95.0, stop=100.0, step=0.5, value=99.5, label="Intensity percentile"
    )
    mo.hstack([query_input, input_col_selector, intensity_pct])
    return input_col_selector, intensity_pct, query_input


@app.cell
def resolved_sites(query_input, input_col_selector):
    location_info = lookup_site_metadata(query_input.value, input_col_selector.value)
    mo.md(f"Found **{location_info.shape[0]}** image sites for `{query_input.value}`")
    return (location_info,)


@app.cell
def first_site_grid(location_info, intensity_pct, query_input):
    site = pick_first_site(location_info)
    label = (
        f"{query_input.value}\n\nplate:\n{site['Plate']}\n"
        f"well: {site['Well']}\nsite: {site['Site']}"
    )
    display_site(
        site["Source"],
        site["Batch"],
        site["Plate"],
        site["Well"],
        site["Site"],
        label,
        intensity_pct.value,
    )
    return


if __name__ == "__main__":
    app.run()
