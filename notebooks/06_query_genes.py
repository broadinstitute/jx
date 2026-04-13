# /// script
# requires-python = ">=3.11"
# dependencies = ["marimo", "polars", "broad-babel", "biopython"]
# ///

import marimo

__generated_with = "0.23.1"
app = marimo.App(width="medium")

with app.setup:
    import marimo as mo
    import polars as pl
    from Bio import Entrez
    from broad_babel.query import get_mapper

    ENTREZ_FIELDS = ("Name", "Description", "Summary", "OtherDesignations")


@app.function
def gene_symbols_to_ncbi(symbols: tuple[str, ...]) -> dict[str, str]:
    """Resolve a tuple of gene symbols to their NCBI Gene IDs via broad-babel."""
    return get_mapper(
        query=symbols,
        input_column="standard_key",
        output_columns="standard_key,NCBI_Gene_ID",
    )


@app.function
def entrez_gene_info(
    ncbi_ids: tuple[str, ...],
    email: str,
    fields: tuple[str, ...] = ENTREZ_FIELDS,
) -> pl.DataFrame:
    """Fetch Entrez gene summaries for a list of NCBI Gene IDs."""
    Entrez.email = email
    entries = []
    for id_ in ncbi_ids:
        stream = Entrez.esummary(db="gene", id=id_)
        record = Entrez.read(stream)
        entries.append(
            {k: record["DocumentSummarySet"]["DocumentSummary"][0][k] for k in fields}
        )
    return pl.DataFrame(entries)


@app.function
def parse_gene_list(raw: str) -> tuple[str, ...]:
    """Split a comma-separated gene symbol string into a cleaned tuple."""
    return tuple(g.strip() for g in raw.split(",") if g.strip())


@app.cell
def intro():
    mo.md(
        """
        # Query genes externally

        Link JUMP gene perturbations to the
        [NCBI Entrez](https://www.ncbi.nlm.nih.gov/books/NBK25501/) database for
        gene summaries, descriptions, and synonyms using
        [Biopython](https://biopython.org/).
        """
    )
    return


@app.cell
def controls():
    gene_input = mo.ui.text(
        value="CHRM4, SCAPER, GPR176, LY6K",
        label="Gene symbols (comma-separated)",
    )
    email_input = mo.ui.text(
        value="example@email.com",
        label="Email for NCBI (required by Entrez)",
    )
    mo.vstack([gene_input, email_input])
    return email_input, gene_input


@app.cell
def gene_table(gene_input, email_input):
    genes = parse_gene_list(gene_input.value)
    ids = gene_symbols_to_ncbi(genes)
    gene_info = entrez_gene_info(tuple(ids.values()), email_input.value)
    gene_info
    return


if __name__ == "__main__":
    app.run()
