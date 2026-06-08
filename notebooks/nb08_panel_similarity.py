# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "broad-babel==0.1.31",
#     "duckdb",
#     "marimo",
#     "numpy",
#     "pandas",
#     "plotly",
#     "requests",
#     "scipy",
# ]
# ///

import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium")

with app.setup:
    import re

    # Explicit `import sqlite3` so Pyodide's `loadPackagesFromImports` pulls in the
    # sqlite3 wheel before `broad_babel.query` does its own `import sqlite3`. Without
    # this, broad_babel fails on WASM with `ModuleNotFoundError: No module named 'sqlite3'`.
    import sqlite3  # noqa: F401

    import duckdb
    import marimo as mo
    import numpy as np
    import pandas as pd
    import plotly.graph_objects as go
    import requests
    from broad_babel.query import run_query
    from scipy.cluster.hierarchy import leaves_list, linkage
    from scipy.spatial.distance import squareform

    ZENODO_RECORD = "15029005"
    GENE_MODALITIES = ("orf", "crispr")
    COMPOUND_MODALITY = "compound"

    ACTIVE_COLOR = "#1b5e20"  # dark green — corrected p < threshold
    INACTIVE_COLOR = "#bf5b00"  # dark orange — corrected p >= threshold
    MISSING_COLOR = "#777777"  # grey — no activity row at all
    P_THRESHOLD = 0.05

    DEFAULT_GENE_PANEL = (
        "MMP1 MMP2 MMP3 MMP7 MMP8 MMP9 MMP10 MMP11 MMP12 MMP13 MMP14 MMP15 "
        "MMP16 MMP17 MMP19 MMP20 MMP21 MMP23A MMP23B MMP24 MMP25 MMP26 MMP27 MMP28"
    )
    DEFAULT_COMPOUND_PANEL = ""

    # Per-modality cosine-similarity tail thresholds, ordered most-extreme first.
    # Hover tags each cell with the rarity of its similarity. Values copied from
    # notebooks/nb25_jfh_gene_similarity_heatmap.py (computed by nb26 over the
    # full pairwise distribution per modality).
    COSINE_PERCENTILES: dict[str, dict[str, list[tuple[float, str]]]] = {
        "compound": {
            "top": [
                (0.77, "0.01 %"),
                (0.64, "0.1 %"),
                (0.54, "0.5 %"),
                (0.50, "1 %"),
                (0.37, "5 %"),
                (0.29, "10 %"),
                (0.17, "25 %"),
            ],
            "bot": [
                (-0.67, "0.01 %"),
                (-0.59, "0.1 %"),
                (-0.51, "0.5 %"),
                (-0.47, "1 %"),
                (-0.34, "5 %"),
                (-0.26, "10 %"),
                (-0.13, "25 %"),
            ],
        },
        "orf": {
            "top": [
                (0.70, "0.01 %"),
                (0.58, "0.1 %"),
                (0.49, "0.5 %"),
                (0.44, "1 %"),
                (0.32, "5 %"),
                (0.25, "10 %"),
                (0.13, "25 %"),
            ],
            "bot": [
                (-0.64, "0.01 %"),
                (-0.55, "0.1 %"),
                (-0.48, "0.5 %"),
                (-0.43, "1 %"),
                (-0.32, "5 %"),
                (-0.25, "10 %"),
                (-0.13, "25 %"),
            ],
        },
        "crispr": {
            "top": [
                (0.88, "0.01 %"),
                (0.82, "0.1 %"),
                (0.75, "0.5 %"),
                (0.71, "1 %"),
                (0.56, "5 %"),
                (0.45, "10 %"),
                (0.25, "25 %"),
            ],
            "bot": [
                (-0.85, "0.01 %"),
                (-0.80, "0.1 %"),
                (-0.73, "0.5 %"),
                (-0.69, "1 %"),
                (-0.55, "5 %"),
                (-0.45, "10 %"),
                (-0.24, "25 %"),
            ],
        },
    }


@app.function
def duck() -> "duckdb.DuckDBPyConnection":
    """Fresh in-memory DuckDB connection with httpfs loaded (CORS-friendly parquet reads)."""
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    return con


@app.function
def parse_items(text: str) -> list[str]:
    """Split by commas / whitespace / newlines; strip empties; preserve order; dedupe."""
    seen, out = set(), []
    for tok in re.split(r"[,\s]+", text or ""):
        tok = tok.strip()
        if tok and tok not in seen:
            seen.add(tok)
            out.append(tok)
    return out


@app.function
def latest_zenodo_id() -> str:
    """Follow Zenodo's `/versions/latest` redirect to the actual record id."""
    return requests.get(f"https://zenodo.org/api/records/{ZENODO_RECORD}/versions/latest", allow_redirects=True).json()[
        "id"
    ]


@app.function
def zenodo_file_url(filename: str) -> str:
    return f"https://zenodo.org/api/records/{latest_zenodo_id()}/files/{filename}/content"


@app.function
def resolve_jcps(items: list[str], allowed_modalities: tuple[str, ...]) -> dict[str, dict[str, list[str]]]:
    """{item -> {modality -> [jcp_ids]}} via broad-babel exact match on standard_key."""
    out: dict[str, dict[str, list[str]]] = {}
    for item in items:
        rows = run_query(
            query=item,
            input_column="standard_key",
            output_columns="standard_key,JCP2022,pert_type,plate_type",
            operator="=",
        )
        for sk, jcp, pt, plt_type in rows:
            if pt != "trt" or not plt_type:
                continue
            plt_low = plt_type.lower()
            modality = next((m for m in allowed_modalities if m in plt_low), None)
            if modality is None:
                continue
            out.setdefault(sk, {}).setdefault(modality, []).append(jcp)
    return out


@app.function
def activity_table(modality: str) -> pd.DataFrame:
    """Per-perturbation corrected p / activity via DuckDB over Zenodo `{modality}_gallery.parquet`.
    Reads only the columns we need, no local cache (works in pyodide/WASM)."""
    url = zenodo_file_url(f"{modality}_gallery.parquet")
    con = duck()
    df = con.execute(
        f"""
        SELECT Perturbation,
               FIRST("Corrected p-value") AS corrected_p,
               FIRST("Phenotypic activity") AS phenotypic_activity,
               FIRST("JCP2022") AS jcp
        FROM read_parquet('{url}')
        GROUP BY Perturbation
        """
    ).df()
    con.close()
    return df


@app.function
def panel_submatrix(modality: str, jcp_to_label: dict[str, str]) -> pd.DataFrame:
    """Slice the Zenodo cosine matrix to panel JCPs via DuckDB column projection
    (HTTP range requests pull only the needed column chunks). Aggregate to per-label means."""
    if not jcp_to_label:
        return pd.DataFrame()
    url = zenodo_file_url(f"{modality}_cosinesim_full.parquet")
    con = duck()
    all_cols = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{url}') LIMIT 0").df()["column_name"].tolist()
    keep = [c for c in all_cols if c in jcp_to_label]
    if not keep:
        con.close()
        return pd.DataFrame()
    keep_idx = sorted(all_cols.index(c) for c in keep)
    col_list = ", ".join(f'"{c}"' for c in keep)
    col_only = con.execute(f"SELECT {col_list} FROM read_parquet('{url}')").df()
    con.close()
    sub_np = col_only.to_numpy()[keep_idx, :]
    row_jcps = [all_cols[i] for i in keep_idx]
    pdf = pd.DataFrame(
        sub_np,
        index=[jcp_to_label[j] for j in row_jcps],
        columns=[jcp_to_label[c] for c in keep],
    )
    pdf = pdf.groupby(level=0).mean()
    pdf = pdf.T.groupby(level=0).mean().T
    return pdf.sort_index(axis=0).sort_index(axis=1)


@app.function
def build_panel(family_map: dict[str, dict[str, list[str]]], modality: str) -> tuple[dict[str, str], list[str]]:
    """(jcp→label, sorted unique labels) for one modality."""
    jcp_to_label: dict[str, str] = {}
    labels: set[str] = set()
    for sk, mods in family_map.items():
        for jcp in mods.get(modality, []):
            jcp_to_label[jcp] = sk
            labels.add(sk)
    return jcp_to_label, sorted(labels)


@app.function
def shorten_inchikey(label: str) -> str:
    return label[:14] if len(label) > 14 and "-" in label else label


@app.function
def color_for_activity(active: object) -> str:
    """Map an `active` flag (bool / None / NaN) to a tick-label color.

    Three states, matching nb25:
      - True  → dark green (corrected p < threshold)
      - False → dark orange (corrected p >= threshold)
      - None / missing → grey (no activity row at all)
    """
    if active is None or (isinstance(active, float) and np.isnan(active)):
        return MISSING_COLOR
    return ACTIVE_COLOR if bool(active) else INACTIVE_COLOR


@app.function
def cosine_rank_label(modality_name: str, value: float) -> str:
    """Tag a cosine value with its rarity in the modality's pairwise distribution
    (e.g. `top 1 %`, `bottom 0.1 %`, `middle 50 %`, or `self (cos = 1)`)."""
    if value is None:
        return ""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return ""
    if np.isnan(v):
        return ""
    if abs(v - 1.0) < 1e-9:
        return "self (cos = 1)"
    tails = COSINE_PERCENTILES.get(modality_name)
    if tails is None:
        return ""
    for thr, label in tails["top"]:
        if v >= thr:
            return f"top {label}"
    for thr, label in tails["bot"]:
        if v <= thr:
            return f"bottom {label}"
    return "middle 50 %"


@app.function
def fmt_hover_val(v, fmt: str = "{}") -> str:
    """Format a single field value for hover; returns '—' for missing."""
    if v is None:
        return "—"
    if isinstance(v, float) and np.isnan(v):
        return "—"
    s = str(v)
    if s in ("nan", "<NA>", "None", ""):
        return "—"
    try:
        return fmt.format(v)
    except (TypeError, ValueError):
        return s


@app.function
def build_hover_strings(
    labels: list[str],
    label_active: dict[str, object],
    label_corrected_p: dict[str, float | None],
    label_nmap: dict[str, float | None],
    label_jcps: dict[str, list[str]],
) -> list[str]:
    """One multi-line HTML hover string per label, aligned to `labels`."""
    out: list[str] = []
    for lbl in labels:
        flag = label_active.get(lbl)
        if flag is True:
            act_str = f"<b style='color:{ACTIVE_COLOR}'>active</b>"
        elif flag is False:
            act_str = f"<span style='color:{INACTIVE_COLOR}'>not active</span>"
        else:
            act_str = f"<span style='color:{MISSING_COLOR}'>no activity row</span>"
        jcps = label_jcps.get(lbl, [])
        jcps_str = ", ".join(jcps) if jcps else "—"
        lines = [
            f"<b>{lbl}</b>",
            f"Activity: {act_str}",
            f"nmAP: {fmt_hover_val(label_nmap.get(lbl), '{:.3f}')}"
            f"  |  corrected p: {fmt_hover_val(label_corrected_p.get(lbl), '{:.3g}')}",
            f"JCP IDs: {jcps_str}",
        ]
        out.append("<br>".join(lines))
    return out


@app.function
def cluster_order(sim: np.ndarray) -> list[int]:
    """Hierarchical clustering leaf order on (1 - cosine) distances. Returns positional order."""
    n = sim.shape[0]
    if n < 2:
        return list(range(n))
    dist = 1.0 - sim
    dist = (dist + dist.T) / 2.0
    np.fill_diagonal(dist, 0.0)
    try:
        cond = squareform(dist, checks=False)
        z = linkage(cond, method="average")
        return [int(i) for i in leaves_list(z)]
    except (ValueError, FloatingPointError):
        return list(range(n))


@app.function
def colorize_tick(label: str, active: object) -> str:
    """Wrap a tick label in an HTML span colored by activity status (3-state)."""
    return f'<span style="color:{color_for_activity(active)};font-weight:600">{label}</span>'


@app.function
def plot_similarity_clustermap(
    sim: pd.DataFrame,
    label_active: dict[str, object],
    hover_strings: list[str] | None,
    title: str,
    modality_name: str,
) -> go.Figure:
    """Plotly heatmap with hierarchical-cluster row/col reorder, activity-colored tick labels
    (green / orange / grey), and rich hover annotated with percentile rank."""
    labels = list(sim.index)
    n = len(labels)
    if n == 0:
        return go.Figure().update_layout(
            title=title,
            annotations=[
                dict(
                    text="No perturbations matched",
                    xref="paper",
                    yref="paper",
                    x=0.5,
                    y=0.5,
                    showarrow=False,
                    font=dict(size=14),
                )
            ],
            height=200,
        )
    sim_np = sim.to_numpy()
    order = cluster_order(sim_np) if n > 1 else [0]
    sim_o = sim_np[np.ix_(order, order)]
    labels_o = [labels[i] for i in order]
    hovers_o = [hover_strings[i] for i in order] if hover_strings is not None and len(hover_strings) == n else [""] * n

    customdata = [
        [
            [
                hovers_o[r],
                hovers_o[c],
                cosine_rank_label(modality_name, float(sim_o[r, c])),
            ]
            for c in range(n)
        ]
        for r in range(n)
    ]
    tick_labels = [colorize_tick(lbl, label_active.get(lbl)) for lbl in labels_o]

    fig = go.Figure(
        data=go.Heatmap(
            z=sim_o,
            x=tick_labels,
            y=tick_labels,
            zmin=-1,
            zmax=1,
            colorscale=[[0.0, "#053061"], [0.5, "#f7f7f7"], [1.0, "#67001f"]],
            customdata=customdata,
            hovertemplate=(
                "<b>Cosine sim:</b> %{z:.3f}  ·  <i>%{customdata[2]}</i><br>"
                "──── <b>Row</b> ────<br>%{customdata[0]}<br>"
                "──── <b>Col</b> ────<br>%{customdata[1]}"
                "<extra></extra>"
            ),
            colorbar=dict(
                title=dict(text="cosine<br>sim", side="right", font=dict(size=10)),
                tickvals=[-1.0, -0.5, 0.0, 0.5, 1.0],
                tickfont=dict(size=9),
                thickness=14,
            ),
        )
    )
    side = max(540, 26 * n + 220)
    fig.update_layout(
        title=dict(text=title, x=0.5),
        xaxis=dict(side="bottom", tickangle=45, automargin=True),
        yaxis=dict(autorange="reversed", automargin=True),
        height=side,
        width=side + 160,
        margin=dict(l=10, r=180, t=60, b=120),
    )
    return fig


@app.function
def caption_md(modality_name: str, view: str) -> str | None:
    """Long-form 'how to read this plot' caption per (modality, view). Returns None if absent."""
    if modality_name == "compound" and view == "all":
        return f"""
### All compounds (no activity filter)

Includes **every compound whose `standard_key` (InChIKey) matches the entered panel**.

- Each cell is the **cosine similarity** between the morphological profiles of two compounds.
  - **red** ≈ very similar (cosine near +1)
  - **white** ≈ uncorrelated (cosine near 0)
  - **dark blue** ≈ opposite / anti-similar (cosine near −1)
- Rows and columns are reordered as a **clustermap** (hierarchical clustering on `1 − cosine`,
  average linkage) so similar compounds cluster as **blocks of dark red along the diagonal**.
  **Blue squares off the diagonal** are pairs of compounds with anti-similar profiles.
- **Tick-label text color** encodes phenotypic activity:
  **dark green** = active (`corrected p < {P_THRESHOLD}`),
  **dark orange** = not active,
  **grey** = no activity row in the JUMP-rr gallery at all.
  Perturbations just short of the activity threshold sometimes still neighbor their expected
  matches; the color is a hint, not a hard filter.
- **Hover** shows the cosine value with its **percentile rank** (e.g. *top 1 %*, *bottom 5 %*,
  *middle 50 %* — these tags refer to the calibration table below), the row and column
  perturbation labels, JCP IDs, activity status, nmAP and corrected p-value.

**Calibration — what counts as a large cosine?** From the full pairwise distribution within
compound perturbations (20,000-perturbation random sample of the 112,604 in
`compound_no_source7`; n_pairs ≈ 2×10⁸):

| Pair is in the…           | top/bot 25 % | 10 %  | 5 %   | 1 %   | 0.5 % | 0.1 % | 0.01 % |
|---|---|---|---|---|---|---|---|
| **top tail** if cos ≥     | +0.17 | +0.29 | +0.37 | +0.50 | +0.54 | +0.64 | +0.77 |
| **bottom tail** if cos ≤  | −0.13 | −0.26 | −0.34 | −0.47 | −0.51 | −0.59 | −0.67 |

So a cosine of **+0.5** between two compounds is in the **top 1 %** of all pairs;
**+0.64** is a **1-in-1000** pairing; **+0.77** is **1-in-10000**.
(Thresholds copied from `notebooks/nb26_jfh_cosine_similarity_percentiles.py` in jump_production.)
"""
    if modality_name == "compound" and view == "active":
        return f"""
### Active compounds (phenotypically active only)

Same compound set as above, **filtered to compounds whose morphological profile is significantly
different from negative controls** (`corrected p < {P_THRESHOLD}` in the JUMP-rr gallery
`copairs` mAP run). Inactive and unscored compounds are dropped.

The cosine color scale, clustermap layout and hover content are identical to the unfiltered plot.
Because every remaining row is active by construction, **tick-label text is uniformly dark green**.
"""
    if modality_name == "orf" and view == "all":
        return f"""
### All ORFs (no activity filter)

Includes **every ORF over-expression reagent whose gene symbol is in the entered panel**.

- Each cell is the **cosine similarity** between two ORFs' morphological profiles
  (**red** ≈ similar, **white** ≈ uncorrelated, **dark blue** ≈ anti-similar).
- Rows and columns are reordered as a **clustermap** so blocks of dark red along the diagonal
  highlight ORFs with similar phenotypes. Off-diagonal blue squares = anti-similar pairs.
- **Tick-label text color** encodes phenotypic activity:
  **dark green** = active (`corrected p < {P_THRESHOLD}`),
  **dark orange** = not active,
  **grey** = no activity row in the JUMP-rr gallery.
- **Hover** shows the cosine value with its **percentile rank**, row/column labels, JCP IDs,
  activity status, nmAP and corrected p.

**Calibration — what counts as a large cosine?** From the full pairwise distribution within
the 15,131 ORF perturbations (n_pairs ≈ 1.1×10⁸):

| Pair is in the…           | top/bot 25 % | 10 %  | 5 %   | 1 %   | 0.5 % | 0.1 % | 0.01 % |
|---|---|---|---|---|---|---|---|
| **top tail** if cos ≥     | +0.13 | +0.25 | +0.32 | +0.44 | +0.49 | +0.58 | +0.70 |
| **bottom tail** if cos ≤  | −0.13 | −0.25 | −0.32 | −0.43 | −0.48 | −0.55 | −0.64 |

A cosine of **+0.4** between two ORFs is already in the **top ~1 %** of all pairs;
**+0.58** is a **1-in-1000** pairing; **+0.70** is **1-in-10000**.
"""
    if modality_name == "orf" and view == "active":
        return f"""
### Active ORFs (phenotypically active only)

Same ORF set as above, **filtered to ORFs whose profile is significantly different from
negative controls** (`corrected p < {P_THRESHOLD}`). Inactive and unscored ORFs are dropped.
Tick labels are uniformly dark green.
"""
    if modality_name == "crispr" and view == "all":
        return f"""
### All CRISPR guides (no activity filter)

Includes **every CRISPR reagent whose gene symbol is in the entered panel**.

- Each cell is the **cosine similarity** between two CRISPR perturbations' morphological
  profiles (**red** ≈ similar, **white** ≈ uncorrelated, **dark blue** ≈ anti-similar).
- Rows and columns are reordered as a **clustermap**. Diagonal blocks of dark red = groups
  of knockouts with similar phenotypes. Off-diagonal blue = anti-similar pairs.
- **Tick-label text color** encodes phenotypic activity:
  **dark green** = active (`corrected p < {P_THRESHOLD}`),
  **dark orange** = not active,
  **grey** = no activity row in the JUMP-rr gallery.
- **Hover** shows the cosine value with its **percentile rank**, row/column labels, JCP IDs,
  activity status, nmAP and corrected p.

**Calibration — what counts as a large cosine?** From the full pairwise distribution within
the 7,977 CRISPR perturbations (n_pairs ≈ 3.2×10⁷):

| Pair is in the…           | top/bot 25 % | 10 %  | 5 %   | 1 %   | 0.5 % | 0.1 % | 0.01 % |
|---|---|---|---|---|---|---|---|
| **top tail** if cos ≥     | +0.25 | +0.45 | +0.56 | +0.71 | +0.75 | +0.82 | +0.88 |
| **bottom tail** if cos ≤  | −0.24 | −0.45 | −0.55 | −0.69 | −0.73 | −0.80 | −0.85 |

CRISPR profiles are noticeably more variable than ORF or compound (pairwise SD ≈ 0.33 vs ~0.19–0.21),
so **larger thresholds** are needed before a pair is genuinely surprising.
"""
    if modality_name == "crispr" and view == "active":
        return f"""
### Active CRISPR guides (phenotypically active only)

Same CRISPR set as above, **filtered to guides whose profile is significantly different from
negative controls** (`corrected p < {P_THRESHOLD}`). Inactive and unscored guides are dropped.
Tick labels are uniformly dark green.
"""
    return None


@app.function
def next_steps_md(modality_name: str) -> str:
    """Closing 'Digging deeper' pointer at the end of each modality section."""
    noun = "compound" if modality_name == "compound" else "gene"
    return (
        f"### Digging deeper\n\n"
        f"Copy the **JCP ID** of an interesting {noun} from the hover or the summary table and "
        f"follow the "
        f"[jump_rr lookup guide](https://broadinstitute.github.io/jump_hub/howto/interactive/1_jumprr_steps.html) "
        f"to see differential features and example Cell-Painting images for that reagent."
    )


@app.function
def render_modality_section(modality_name: str, requested: list[str], panel_kind: str):
    """Full nb25-style pipeline for one modality: hits → activity → similarity → clustermap →
    summary table → next-steps. Returns (vstack_for_display, summary_dict)."""
    header = mo.md(f"## {modality_name.upper()}")
    if not requested:
        return mo.vstack([header, mo.md("_Enter at least one item in the sidebar._")]), None

    family_map = resolve_jcps(requested, (modality_name,))
    jcp_map, panel_labels = build_panel(family_map, modality_name)
    if not panel_labels:
        return (
            mo.vstack([header, mo.md(f"_No `{modality_name}` perturbations match the requested set._")]),
            None,
        )

    activity_df = activity_table(modality_name)
    # Compose per-label (= per gene / per InChIKey) activity + nmAP + corrected_p.
    act_lookup = activity_df.set_index("Perturbation").to_dict("index")
    label_corrected_p: dict[str, float | None] = {}
    label_nmap: dict[str, float | None] = {}
    label_active: dict[str, object] = {}
    label_jcps: dict[str, list[str]] = {lbl: list(family_map[lbl].get(modality_name, [])) for lbl in panel_labels}
    for lbl in panel_labels:
        row = act_lookup.get(lbl)
        if row is None:
            label_corrected_p[lbl] = None
            label_nmap[lbl] = None
            label_active[lbl] = None
        else:
            cp = row.get("corrected_p")
            label_corrected_p[lbl] = None if cp is None or (isinstance(cp, float) and np.isnan(cp)) else float(cp)
            np_val = row.get("phenotypic_activity")
            label_nmap[lbl] = (
                None if np_val is None or (isinstance(np_val, float) and np.isnan(np_val)) else float(np_val)
            )
            label_active[lbl] = None if label_corrected_p[lbl] is None else label_corrected_p[lbl] < P_THRESHOLD

    # Cosine submatrix on panel JCPs, aggregated to per-label means.
    sim_all = panel_submatrix(modality_name, jcp_map)
    if sim_all.empty:
        return (
            mo.vstack(
                [
                    header,
                    mo.md(
                        f"_{len(panel_labels):,} `{modality_name}` perturbations matched the panel, "
                        f"but none have rows in the cosine matrix._"
                    ),
                ]
            ),
            None,
        )

    # For compound mode, present InChIKey labels as their short structural prefix.
    if panel_kind == "compounds":
        display_map = {lbl: shorten_inchikey(lbl) for lbl in sim_all.index}
        sim_all = sim_all.rename(index=display_map, columns=display_map)
        label_active = {display_map.get(k, k): v for k, v in label_active.items()}
        label_corrected_p = {display_map.get(k, k): v for k, v in label_corrected_p.items()}
        label_nmap = {display_map.get(k, k): v for k, v in label_nmap.items()}
        label_jcps = {display_map.get(k, k): v for k, v in label_jcps.items()}

    hover_all = build_hover_strings(list(sim_all.index), label_active, label_corrected_p, label_nmap, label_jcps)
    n_matched = len(sim_all.index)
    active_set = {lbl for lbl, flag in label_active.items() if flag is True}
    n_active = sum(1 for lbl in sim_all.index if lbl in active_set)

    fig_all = plot_similarity_clustermap(
        sim_all,
        label_active,
        hover_all,
        title=f"{modality_name}: all matched ({n_matched})",
        modality_name=modality_name,
    )

    elements: list = [
        header,
        mo.md(
            f"Found **{n_matched:,}** `{modality_name}` perturbations in the cosine matrix; "
            f"**{n_active:,}** are phenotypically active (`corrected p < {P_THRESHOLD}`)."
        ),
    ]

    desc_all = caption_md(modality_name, "all")
    if desc_all:
        elements.append(mo.accordion({"How to read this plot — full panel": mo.md(desc_all)}))
    elements.append(mo.ui.plotly(fig_all))

    # Active-only subset
    if n_active == 0:
        elements.append(
            mo.md(f"_No active `{modality_name}` perturbations in this panel — active-only clustermap skipped._")
        )
    else:
        active_labels = [lbl for lbl in sim_all.index if lbl in active_set]
        sim_active = sim_all.loc[active_labels, active_labels]
        hover_active = build_hover_strings(active_labels, label_active, label_corrected_p, label_nmap, label_jcps)
        fig_active = plot_similarity_clustermap(
            sim_active,
            label_active,
            hover_active,
            title=f"{modality_name}: active only ({n_active})",
            modality_name=modality_name,
        )
        desc_active = caption_md(modality_name, "active")
        if desc_active:
            elements.append(mo.accordion({"How to read this plot — active only": mo.md(desc_active)}))
        elements.append(mo.ui.plotly(fig_active))

    # Summary table
    summary = pd.DataFrame(
        {
            "label": list(sim_all.index),
            "n_jcps": [len(label_jcps.get(lbl, [])) for lbl in sim_all.index],
            "jcps": [", ".join(label_jcps.get(lbl, [])) for lbl in sim_all.index],
            "corrected_p": [label_corrected_p.get(lbl) for lbl in sim_all.index],
            "nmAP": [label_nmap.get(lbl) for lbl in sim_all.index],
            "active": [label_active.get(lbl) for lbl in sim_all.index],
        }
    ).sort_values(by="corrected_p", na_position="last")
    elements.append(mo.md("**Summary table**"))
    elements.append(mo.ui.table(summary, page_size=15))
    elements.append(mo.md(next_steps_md(modality_name)))

    return mo.vstack(elements), {
        "modality": modality_name,
        "n_matched": n_matched,
        "n_active": n_active,
    }


@app.cell
def intro():
    _md = mo.md(rf"""
    # Perturbation panel — phenotypic activity & cosine similarity

    Pick **genes** (ORF + CRISPR heatmaps) **or** **compounds** (compound heatmap) and provide
    the list in the sidebar. The pipeline (one section per enabled modality) follows
    `notebooks/nb25_jfh_gene_similarity_heatmap.py` in `jump_production`:

    1. Resolve the input panel to JCP IDs via `broad-babel`.
    2. Pull per-perturbation activity from the JUMP-rr `{{modality}}_gallery.parquet` on Zenodo
       (DuckDB column projection, HTTP range requests).
    3. Slice the published `{{modality}}_cosinesim_full.parquet` to the panel JCPs and aggregate
       to per-label means (mean across multiple reagents per gene / compound).
    4. Render a **plotly clustermap** with hierarchical row/col reorder.
    5. Render an **active-only** clustermap (filtered to `corrected p < {P_THRESHOLD}`).
    6. Show a **summary table** of matched perturbations + activity stats.

    **Indicators (matches nb25):**

    - Tick-label color encodes phenotypic activity: **dark green** = active, **dark orange** =
      not active, **grey** = no activity row in the JUMP-rr gallery.
    - Hover spells out cosine value, **percentile rank** (`top 1 %` / `bottom 5 %` / `middle 50 %`,
      from the nb26 calibration tables), JCP IDs, nmAP, corrected p.
    - Hierarchical clustering (average linkage on `1 − cosine`) groups similar perturbations
      into diagonal blocks.

    Long-form per-plot glossaries (color scale, calibration tables, etc.) are collapsed into
    "How to read this plot" toggles below each heatmap.
    """)
    mo.accordion({"Overview & data sources": _md}, lazy=False)
    return


@app.cell
def controls():
    panel_kind = mo.ui.dropdown(options=["genes", "compounds"], value="genes", label="Panel kind")
    items_input = mo.ui.text_area(
        value=DEFAULT_GENE_PANEL,
        label="Items (gene symbols or InChIKeys, whitespace/comma/newline-separated)",
        rows=8,
        full_width=True,
    )
    mo.sidebar(
        [
            mo.md("## Panel"),
            panel_kind,
            items_input,
            mo.md(
                "_Switch to **compounds** and paste 27-char InChIKeys to render the compound heatmap "
                "instead. One kind per run._"
            ),
        ]
    )
    return items_input, panel_kind


@app.cell
def parsed(items_input, panel_kind):
    requested = parse_items(items_input.value)
    if panel_kind.value == "genes":
        modalities = list(GENE_MODALITIES)
    else:
        modalities = [COMPOUND_MODALITY]
    return modalities, requested


@app.cell
def orf_section(modalities, panel_kind, requested):
    if "orf" not in modalities:
        _out = mo.md("")
    else:
        _section, _ = render_modality_section("orf", requested, panel_kind.value)
        _out = _section
    _out


@app.cell
def crispr_section(modalities, panel_kind, requested):
    if "crispr" not in modalities:
        _out = mo.md("")
    else:
        _section, _ = render_modality_section("crispr", requested, panel_kind.value)
        _out = _section
    _out


@app.cell
def compound_section(modalities, panel_kind, requested):
    if "compound" not in modalities:
        _out = mo.md("")
    else:
        _section, _ = render_modality_section("compound", requested, panel_kind.value)
        _out = _section
    _out


@app.cell
def footnotes():
    _md = mo.md(rf"""
    ## Caveats

    - **Compound panel ≠ MMP-target compounds.** JUMP identifies compounds by InChIKey; broad-babel
      doesn't expose a compound→target gene mapping. An `MMP%` query against compounds matches
      InChIKeys whose first letters happen to spell MMP — included for completeness, not biological
      validity.
    - **Per-label means.** A gene with multiple ORF constructs / CRISPR guides becomes a single
      heatmap row, averaged across reagents. Use the `summary table` to see how many JCPs back each
      label.
    - **Activity threshold.** `corrected p < {P_THRESHOLD}`, matching nb09's prior convention.
      `nb25_jfh_gene_similarity_heatmap.py` uses `0.10` instead — switch in `P_THRESHOLD` if you
      prefer that.
    - **No cell-count ribbon.** nb25 layers per-site median cell counts as a viridis side strip;
      that data isn't exposed via the JUMP-rr Zenodo bundle, so it's omitted here.
    """)
    mo.accordion({"Caveats & differences from nb25": _md}, lazy=False)
    return


if __name__ == "__main__":
    app.run()
