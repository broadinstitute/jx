# /// script
# requires-python = ">=3.11"
# dependencies = ["marimo", "polars", "broad-babel", "biopython"]
# ///

import marimo

__generated_with = "0.13.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import polars as pl
    from Bio import Entrez
    from broad_babel.query import get_mapper
    return Entrez, get_mapper, mo, pl


@app.cell
def _(mo):
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
def _(mo):
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
def _(Entrez, email_input, gene_input, get_mapper, pl):
    genes = tuple(g.strip() for g in gene_input.value.split(",") if g.strip())
    Entrez.email = email_input.value

    fields = ("Name", "Description", "Summary", "OtherDesignations")

    ids = get_mapper(
        query=genes,
        input_column="standard_key",
        output_columns="standard_key,NCBI_Gene_ID",
    )

    entries = []
    for id_ in ids.values():
        stream = Entrez.esummary(db="gene", id=id_)
        record = Entrez.read(stream)
        entries.append(
            {k: record["DocumentSummarySet"]["DocumentSummary"][0][k] for k in fields}
        )

    gene_info = pl.DataFrame(entries)
    gene_info
    return


if __name__ == "__main__":
    app.run()
