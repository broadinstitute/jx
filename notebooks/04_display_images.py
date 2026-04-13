# /// script
# requires-python = ">=3.11"
# dependencies = ["marimo", "duckdb", "matplotlib", "numpy", "jump-portrait"]
# ///

import marimo

__generated_with = "0.13.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import duckdb
    import matplotlib.colors as mplcolors
    import numpy as np
    from jump_portrait.fetch import get_item_location_metadata, get_jump_image
    from matplotlib import pyplot as plt
    return duckdb, get_item_location_metadata, get_jump_image, mo, mplcolors, np, plt


@app.cell
def _(mo):
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
def _(mo):
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
def _(get_item_location_metadata, input_col_selector, mo, query_input):
    query_val = query_input.value
    input_col = input_col_selector.value

    if input_col == "standard_key":
        location_info = get_item_location_metadata(query_val)
    else:
        location_info = get_item_location_metadata(query_val, input_column=input_col)

    mo.md(f"Found **{location_info.shape[0]}** image sites for `{query_val}`")
    return (location_info,)


@app.cell
def _(get_jump_image, mplcolors, np, plt):
    def display_site(source, batch, plate, well, site, label, int_percentile):
        """Plot all 5 channels from one imaging site."""
        n_rows, n_cols = 2, 3
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(2.6 * n_cols, 2.6 * n_rows))
        axes = axes.ravel()

        channel_rgb = {
            "AGP": "#FF7F00",
            "DNA": "#0000FF",
            "ER": "#00FF00",
            "Mito": "#FF0000",
            "RNA": "#FFFF00",
        }

        for ax, (channel, rgb) in zip(axes, channel_rgb.items()):
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

        # Label in last subplot
        ax = axes[-1]
        ax.text(0.5, 0.5, label, ha="center", va="center", fontsize=20, transform=ax.transAxes)
        ax.axis("off")
        plt.tight_layout()
        return fig
    return (display_site,)


@app.cell
def _(display_site, duckdb, intensity_pct, location_info, query_input):
    _meta_fields = ("Source", "Batch", "Plate", "Well", "Site")
    with duckdb.connect() as con:
        _row = (
            con.sql(
                "SELECT COLUMNS('Metadata_(Source|Batch|Plate|Well|Site)') FROM location_info"
            )
            .to_arrow_table()
            .to_batches()[0]
            .to_pylist()[0]
        )
    _source, _batch, _plate, _well, _site = [_row[f"Metadata_{k}"] for k in _meta_fields]
    _label = f"{query_input.value}\n\nplate:\n{_plate}\nwell: {_well}\nsite: {_site}"
    display_site(_source, _batch, _plate, _well, _site, _label, intensity_pct.value)
    return


if __name__ == "__main__":
    app.run()
