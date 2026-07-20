#!/usr/bin/env python3
"""Render every q*.gsql in this dir to SVG + Vega-Lite JSON, regenerate README."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import vl_convert as vlc

HERE = Path(__file__).parent
RENDERED = HERE / "rendered"
README = HERE / "README.md"
DB = HERE / "data" / "jump_metadata.duckdb"
GGSQL = os.environ.get("GGSQL", "ggsql")

TITLE_RX = re.compile(r"^--\s*title:\s*(.+)$", re.MULTILINE)
DESC_RX = re.compile(r"^--\s*description:\s*(.+)$", re.MULTILINE)
READER_RX = re.compile(r"^--\s*reader:\s*(.+)$", re.MULTILINE)
SORT_RX = re.compile(r"^--\s*sort:\s*(.+)$", re.MULTILINE)


def parse_header(text: str) -> dict[str, str]:
    return {
        "title": (m.group(1).strip() if (m := TITLE_RX.search(text)) else ""),
        "description": (m.group(1).strip() if (m := DESC_RX.search(text)) else ""),
        "reader": (m.group(1).strip() if (m := READER_RX.search(text)) else f"duckdb://{DB.relative_to(HERE)}"),
        # Optional `-- sort: value-desc|value-asc` orders a bar chart's categorical
        # axis by its paired numeric value. ggsql bakes an alphabetical scale domain
        # that overrides Vega-Lite `sort`, so we reorder the domain here instead.
        "sort": (m.group(1).strip().lower() if (m := SORT_RX.search(text)) else ""),
    }


def apply_value_sort(spec: dict, descending: bool) -> None:
    """Reorder a categorical position axis by its paired quantitative value.

    Derives the order from the spec's own embedded data, so nothing is hard-coded.
    Applies to any layer whose x/y pair is one categorical + one quantitative
    aesthetic with a single value per category (e.g. a pre-aggregated bar chart).
    """
    rows = spec.get("data", {}).get("values", [])
    layers = spec.get("layer", [spec])
    for layer in layers:
        enc = layer.get("encoding", {})
        pair = [enc.get("x"), enc.get("y")]
        cat = next((e for e in pair if e and e.get("type") in ("nominal", "ordinal")), None)
        val = next((e for e in pair if e and e.get("type") == "quantitative"), None)
        if not (cat and val):
            continue
        cf, vf = cat.get("field"), val.get("field")
        values: dict = {}
        for r in rows:
            if cf in r and isinstance(r.get(vf), (int, float)):
                values[r[cf]] = max(values.get(r[cf], r[vf]), r[vf])
        if not values:
            continue
        order = [c for c, _ in sorted(values.items(), key=lambda kv: (kv[1], str(kv[0])), reverse=descending)]
        cat.setdefault("scale", {})["domain"] = order


def render_one(gsql_path: Path) -> dict:
    name = gsql_path.stem
    text = gsql_path.read_text()
    header = parse_header(text)

    json_out = RENDERED / f"{name}.json"
    cmd = [GGSQL, "run", str(gsql_path), "--reader", header["reader"], "--output", str(json_out)]
    proc = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"  FAIL {name}: {proc.stderr.strip()}", file=sys.stderr)
        return {"name": name, "ok": False, **header}

    # ggsql emits width/height as "container", which vl-convert resolves to
    # tiny defaults when there is no host. Pin them so titles don't clip and
    # faceted panels have room. Faceted specs (presence of `columns`) get
    # extra width per panel.
    spec = json.loads(json_out.read_text())
    n_cols = spec.get("columns", 1)
    spec["width"] = max(900, 280 * n_cols)
    spec["height"] = 500
    if header["sort"] in ("value-desc", "value-asc"):
        apply_value_sort(spec, descending=header["sort"] == "value-desc")
    rendered_spec = json.dumps(spec)
    json_out.write_text(rendered_spec)
    (RENDERED / f"{name}.svg").write_text(vlc.vegalite_to_svg(rendered_spec))
    print(f"  ok   {name}")
    return {"name": name, "ok": True, **header}


def write_readme(entries: list[dict]) -> None:
    lines = [
        "# jx queries",
        "",
        "Catalog of self-contained ggsql queries against the canonical JUMP metadata DuckDB.",
        "Each `q*.gsql` file answers one question; `just render` regenerates this page.",
        "",
        "## Prerequisites",
        "",
        "- [`ggsql`](https://ggsql.org/get_started/installation.html) — runs each `.gsql` file and emits a Vega-Lite spec.",
        "- [`curl`](https://curl.se/) — used by `just setup` to download the prebuilt DuckDBs from the public S3 datastore.",
        "- [`uv`](https://docs.astral.sh/uv/) — `just render` uses `uv run` to load `vl-convert-python` for SVG generation.",
        "",
        "Run `just setup` once to download `data/jump_metadata.duckdb` (base) and `data/jump_metadata_augmented.duckdb` (adds `compound_metadata`: repurposing MOA, chemical-probe targets, compound properties), then `just render` to (re)generate this page and the `rendered/*.svg` thumbnails. A query targets the augmented DB with a `-- reader: duckdb://data/jump_metadata_augmented.duckdb` header. Both DuckDBs are built by the [`jump-cellpainting/datasets`](https://github.com/jump-cellpainting/datasets) / jump_production pipelines; `just build` rebuilds the base DB locally from a sibling `datasets` clone if you need it offline.",
        "",
        "Each entry below shows the rendered SVG (click to enlarge) and the `.gsql` source. Vega-Lite JSON specs are regenerated by `just render` into `rendered/` (gitignored) — paste one into [vega.github.io/editor](https://vega.github.io/editor) to debug encoding.",
        "",
    ]
    for e in entries:
        lines.append(f"## {e['title'] or e['name']}")
        lines.append("")
        if not e["ok"]:
            lines.append(f"_Render failed for [`{e['name']}.gsql`]({e['name']}.gsql)._")
            lines.append("")
            continue
        svg = f"rendered/{e['name']}.svg"
        src = f"{e['name']}.gsql"
        lines.append(f"{e['description']}")
        lines.append("")
        lines.append(f"[![{e['title']}]({svg})]({svg})")
        lines.append("")
        lines.append(f"Source: [`{e['name']}.gsql`]({src})")
        lines.append("")
    README.write_text("\n".join(lines))


def main() -> int:
    RENDERED.mkdir(exist_ok=True)
    if not DB.exists():
        print(f"Missing {DB}. Run `just setup` first.", file=sys.stderr)
        return 1

    queries = sorted(HERE.glob("q*.gsql"))
    if not queries:
        print("No q*.gsql files found.", file=sys.stderr)
        return 1

    print(f"Rendering {len(queries)} queries...")
    entries = [render_one(q) for q in queries]
    write_readme(entries)
    print(f"Wrote {README}")
    return 0 if all(e["ok"] for e in entries) else 2


if __name__ == "__main__":
    sys.exit(main())
