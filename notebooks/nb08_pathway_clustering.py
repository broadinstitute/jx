# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo",
#     "polars",
#     "requests",
#     "matplotlib",
#     "seaborn",
#     "numpy",
#     "pandas",
#     "broad-babel",
# ]
# ///

import marimo

__generated_with = "0.23.1"
app = marimo.App(width="medium")

with app.setup:
    import os
    from pathlib import Path

    import marimo as mo
    import numpy as np
    import pandas as pd
    import polars as pl
    import requests
    import seaborn as sns
    from broad_babel.query import run_query

    CACHE_DIR = Path(os.environ.get("JX_CACHE", Path.home() / ".cache" / "jx"))
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    ZENODO_RECORD = "15029005"


@app.function
def parse_kegg_pathway_genes(pathway_id: str) -> tuple[str, ...]:
    """Fetch a KEGG pathway record and return its unique gene symbols."""
    text = requests.get(f"https://rest.kegg.jp/get/{pathway_id}", timeout=30).text
    in_gene = False
    symbols: list[str] = []
    for line in text.splitlines():
        if line.startswith("GENE"):
            in_gene = True
            content = line[4:].lstrip()
        elif line and not line[0].isspace():
            in_gene = False
            content = ""
        elif in_gene:
            content = line.strip()
        else:
            content = ""
        if content and in_gene:
            parts = content.split(maxsplit=1)
            if len(parts) >= 2:
                symbol = parts[1].split(";", 1)[0].strip()
                if symbol:
                    symbols.append(symbol)
    return tuple(sorted(set(symbols)))


@app.function
def resolve_jcp_for_genes(symbols: tuple[str, ...], dataset: str) -> pl.DataFrame:
    """Map gene symbols to JCP2022 IDs, filtered to a JUMP modality (crispr/orf)."""
    rows = run_query(
        query=tuple(symbols),
        input_column="standard_key",
        output_columns="JCP2022,standard_key,plate_type",
    )
    df = pl.DataFrame(
        rows, schema=["JCP2022", "standard_key", "plate_type"], orient="row"
    )
    return (
        df.filter(pl.col("plate_type") == dataset)
        .unique(subset=["standard_key"])
        .sort("standard_key")
    )


@app.function
def cache_similarity_matrix(dataset: str) -> Path:
    """Download the cosine-similarity matrix for a dataset into CACHE_DIR (idempotent)."""
    cached = CACHE_DIR / f"{dataset}_cosinesim_full.parquet"
    if cached.exists():
        return cached
    latest = requests.get(
        f"https://zenodo.org/api/records/{ZENODO_RECORD}/versions/latest",
        timeout=30,
    ).json()["id"]
    url = (
        f"https://zenodo.org/api/records/{latest}/files/"
        f"{dataset}_cosinesim_full.parquet/content"
    )
    with requests.get(url, stream=True, timeout=900) as r:
        r.raise_for_status()
        tmp = cached.with_suffix(".part")
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
        tmp.rename(cached)
    return cached


@app.function
def submatrix_for_jcps(
    matrix_path: Path, jcp_ids: tuple[str, ...]
) -> tuple[list[str], pl.DataFrame]:
    """Pull the square submatrix corresponding to a set of JCP IDs.

    Row i of the on-disk matrix is the cosine row for column i, so rows and
    columns must be sliced in the same order. We sort the requested JCPs by
    their position in the column list to keep the result aligned.
    """
    lf = pl.scan_parquet(matrix_path)
    cols = lf.collect_schema().names()
    col_pos = {c: i for i, c in enumerate(cols)}
    found = [(col_pos[j], j) for j in jcp_ids if j in col_pos]
    if not found:
        raise ValueError("none of the requested JCP IDs are in the matrix")
    found.sort()
    ordered_idx = [i for i, _ in found]
    ordered_jcps = [j for _, j in found]
    sub = (
        lf.with_row_index()
        .filter(pl.col("index").is_in(ordered_idx))
        .select(pl.col(ordered_jcps))
        .collect()
    )
    return ordered_jcps, sub


@app.function
def relabel_with_symbols(
    jcp_ids: list[str], sub: pl.DataFrame, resolved_df: pl.DataFrame
) -> pd.DataFrame:
    """Relabel the rows/cols of a submatrix from JCP2022 IDs to gene symbols."""
    sym_lookup = dict(
        zip(
            resolved_df.get_column("JCP2022").to_list(),
            resolved_df.get_column("standard_key").to_list(),
        )
    )
    labels = [sym_lookup.get(j, j) for j in jcp_ids]
    arr = sub.to_numpy().astype(np.float32)
    return pd.DataFrame(arr, index=labels, columns=labels)


@app.function
def render_clustermap(sim_values, labels: tuple[str, ...], title: str):
    """Hierarchically clustered cosine-similarity heatmap (vlag, vmin/vmax = +/-1)."""
    df = pd.DataFrame(sim_values, index=list(labels), columns=list(labels))
    n = len(df)
    fig_size = max(6, min(20, 0.18 * n + 4))
    g = sns.clustermap(
        df,
        method="average",
        metric="euclidean",
        cmap=sns.color_palette("vlag", as_cmap=True),
        vmin=-1,
        vmax=1,
        center=0,
        figsize=(fig_size, fig_size),
        xticklabels=True,
        yticklabels=True,
        cbar_kws={"label": "cosine similarity"},
    )
    fontsize = max(5, 9 - n // 25)
    g.ax_heatmap.set_xticklabels(
        g.ax_heatmap.get_xticklabels(), rotation=90, fontsize=fontsize
    )
    g.ax_heatmap.set_yticklabels(
        g.ax_heatmap.get_yticklabels(), rotation=0, fontsize=fontsize
    )
    g.fig.suptitle(title, y=1.02)
    return g.fig


@app.cell
def intro():
    mo.md(
        """
        # Pathway clustering

        Find every gene in a KEGG pathway, look up its JCP2022 perturbation ID
        via [broad-babel](https://github.com/broadinstitute/monorepo/tree/main/libs/jump_babel),
        and render a hierarchically clustered cosine-similarity heatmap of the
        JUMP morphological profiles.

        Default pathway is `hsa04010` (MAPK signalling). Switch the dataset to
        `crispr` for knockouts or `orf` for over-expression. The slider trims
        the heatmap so seaborn's tick budget stays sane on large pathways.
        """
    )
    return


@app.cell
def controls():
    dataset_selector = mo.ui.dropdown(
        options=["crispr", "orf"], value="crispr", label="Dataset"
    )
    pathway_input = mo.ui.text(
        value="hsa04010",
        label="KEGG pathway ID (e.g. hsa04010=MAPK, hsa04210=apoptosis)",
    )
    max_genes = mo.ui.slider(
        start=10,
        stop=120,
        step=5,
        value=60,
        label="Max genes in heatmap",
    )

    mo.sidebar(
        [
            mo.md("### Controls"),
            dataset_selector,
            pathway_input,
            max_genes,
        ]
    )
    return dataset_selector, max_genes, pathway_input


@app.cell
def pathway_genes(pathway_input):
    pathway_symbols = parse_kegg_pathway_genes(pathway_input.value)
    mo.md(
        f"Pulled **{len(pathway_symbols)}** unique gene symbols from "
        f"`{pathway_input.value}`."
    )
    return (pathway_symbols,)


@app.cell
def jcp_mapping(dataset_selector, pathway_symbols):
    resolved = resolve_jcp_for_genes(pathway_symbols, dataset_selector.value)
    missing = sorted(
        set(pathway_symbols) - set(resolved.get_column("standard_key").to_list())
    )
    mo.vstack(
        [
            mo.md(
                f"**{resolved.height}** of {len(pathway_symbols)} symbols have "
                f"a `{dataset_selector.value}` JCP2022 ID. {len(missing)} missing."
            ),
            mo.ui.table(resolved, page_size=8, label="Resolved gene -> JCP2022"),
        ]
    )
    return (resolved,)


@app.cell
def matrix_load(dataset_selector):
    with mo.status.spinner(
        title=f"Caching {dataset_selector.value} similarity matrix"
    ):
        matrix_path = cache_similarity_matrix(dataset_selector.value)
    mo.md(
        f"Matrix at `{matrix_path}` "
        f"(`{matrix_path.stat().st_size / 1e6:.1f}` MB)."
    )
    return (matrix_path,)


@app.cell
def submatrix_compute(matrix_path, max_genes, resolved):
    all_jcps = resolved.get_column("JCP2022").to_list()
    truncated_jcps = sorted(all_jcps)[: max_genes.value]
    keep_jcps, sub = submatrix_for_jcps(matrix_path, tuple(truncated_jcps))
    sim_df = relabel_with_symbols(keep_jcps, sub, resolved)
    mo.md(
        f"Submatrix shape **{sim_df.shape[0]} x {sim_df.shape[1]}**. Showing "
        f"top {len(truncated_jcps)} (of {len(all_jcps)}) genes."
    )
    return (sim_df,)


@app.cell
def clustermap(dataset_selector, pathway_input, sim_df):
    fig = render_clustermap(
        sim_df.values,
        tuple(sim_df.index),
        f"Cosine similarity clustermap - {pathway_input.value} "
        f"({dataset_selector.value})",
    )
    mo.as_html(fig)
    return


if __name__ == "__main__":
    app.run()
