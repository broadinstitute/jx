# jx queries

Catalog of self-contained ggsql queries against the canonical JUMP metadata DuckDB.
Each `q*.gsql` file answers one question; `just render` regenerates this index.

Each row links to the rendered SVG (click to enlarge), the `.gsql` source, and the raw Vega-Lite spec — paste the JSON into [vega.github.io/editor](https://vega.github.io/editor) to debug encoding.

## Catalog

| | Query | Description |
|---|---|---|
| <a href="rendered/q01_plates_per_source.svg"><img src="rendered/q01_plates_per_source.svg" width="240"></a> | **Plates per source by plate type**<br>[`q01_plates_per_source.gsql`](q01_plates_per_source.gsql) · [spec](rendered/q01_plates_per_source.json) | Composition of JUMP plates across the 13 data-generating sources, stacked by plate type. |
| <a href="rendered/q02_wells_per_source_faceted.svg"><img src="rendered/q02_wells_per_source_faceted.svg" width="240"></a> | **Wells per source, faceted by plate type**<br>[`q02_wells_per_source_faceted.gsql`](q02_wells_per_source_faceted.gsql) · [spec](rendered/q02_wells_per_source_faceted.json) | Well-level breakdown joining well + plate, faceted by perturbation modality (COMPOUND, CRISPR, ORF, TARGET2). Shows which sources contributed which kinds of plates. |
| <a href="rendered/q03_perturbation_type_counts.svg"><img src="rendered/q03_perturbation_type_counts.svg" width="240"></a> | **Perturbation counts by modality**<br>[`q03_perturbation_type_counts.gsql`](q03_perturbation_type_counts.gsql) · [spec](rendered/q03_perturbation_type_counts.json) | Total perturbations in the JUMP catalog grouped by modality (compound, CRISPR, ORF, controls), pulled from the perturbation table. |
