export interface Example {
  name: string;
  query: string;
  section: string;
}

export const examples: Example[] = [
  // === Perturbations ===
  {
    section: "Perturbations",
    name: "By modality",
    query: `SELECT Metadata_perturbation_modality AS modality, COUNT(*) AS n
FROM perturbation
GROUP BY modality
ORDER BY n DESC

VISUALISE modality AS y, n AS x, modality AS fill
DRAW bar
LABEL title => 'JUMP perturbations by modality'`,
  },
  // === Plates & wells ===
  {
    section: "Plates & wells",
    name: "Plates per source (stacked)",
    query: `SELECT
    Metadata_Source AS source,
    Metadata_PlateType AS plate_type,
    COUNT(*) AS n_plates
FROM plate
GROUP BY source, plate_type

VISUALISE source AS y, n_plates AS x, plate_type AS fill
DRAW bar
LABEL title => 'JUMP plates per source, by plate type'`,
  },
  {
    section: "Plates & wells",
    name: "Wells per source, faceted",
    query: `WITH well_with_type AS (
    SELECT
        w.Metadata_Source AS source,
        p.Metadata_PlateType AS plate_type
    FROM well w
    JOIN plate p
      ON w.Metadata_Source = p.Metadata_Source
     AND w.Metadata_Plate  = p.Metadata_Plate
    WHERE p.Metadata_PlateType IN ('COMPOUND', 'CRISPR', 'ORF', 'TARGET2')
)
SELECT source, plate_type, COUNT(*) AS n_wells
FROM well_with_type
GROUP BY source, plate_type

VISUALISE source AS y, n_wells AS x, plate_type AS fill
DRAW bar
FACET plate_type
  SETTING ncol => 4
LABEL title => 'JUMP wells per source, faceted by plate type'`,
  },

  // === Chemistry ===
  {
    section: "Chemistry",
    name: "Compounds per source (shared vs unique)",
    query: `WITH pair_counts AS (
    SELECT
        cs.Metadata_Compound_Source AS source,
        cs.Metadata_JCP2022 AS jcp,
        COUNT(cs2.Metadata_Compound_Source) AS n_other_sources
    FROM compound_source cs
    LEFT JOIN compound_source cs2
      ON cs.Metadata_JCP2022 = cs2.Metadata_JCP2022
     AND cs.Metadata_Compound_Source != cs2.Metadata_Compound_Source
    GROUP BY cs.Metadata_Compound_Source, cs.Metadata_JCP2022
)
SELECT
    source,
    CASE WHEN n_other_sources = 0 THEN 'unique to this source' ELSE 'shared with other sources' END AS sharing_status,
    COUNT(*) AS n_compounds
FROM pair_counts
GROUP BY source, sharing_status

VISUALISE source AS y, n_compounds AS x, sharing_status AS fill
DRAW bar
LABEL title => 'JUMP compounds per source (115,796 unique total)'`,
  },
  {
    section: "Chemistry",
    name: "InChIKey completeness",
    query: `WITH annotated AS (
    SELECT
        cs.Metadata_Compound_Source AS source,
        CASE
            WHEN c.Metadata_InChIKey IS NULL
              OR c.Metadata_InChIKey IN ('', 'NA')
              OR length(c.Metadata_InChIKey) != 27
            THEN 'missing'
            ELSE 'present'
        END AS inchikey_status
    FROM compound_source cs
    LEFT JOIN compound c
      ON cs.Metadata_JCP2022 = c.Metadata_JCP2022
)
SELECT source, inchikey_status, COUNT(*) AS n_compounds
FROM annotated
GROUP BY source, inchikey_status

VISUALISE source AS y, n_compounds AS x, inchikey_status AS fill
DRAW bar
LABEL title => 'Compound InChIKey completeness per source'`,
  },

  // === Genetics ===
  {
    section: "Genetics",
    name: "CRISPR guides",
    query: `SELECT COUNT(*) AS n_guides, COUNT(DISTINCT Metadata_Symbol) AS n_genes
FROM crispr`,
  },
  {
    section: "Genetics",
    name: "ORF reagents",
    query: `SELECT COUNT(*) AS n_orfs, COUNT(DISTINCT Metadata_Symbol) AS n_genes
FROM orf`,
  },

  // === Infrastructure ===
  {
    section: "Infrastructure",
    name: "Microscope configurations",
    query: `SELECT * FROM microscope_config`,
  },
  {
    section: "Infrastructure",
    name: "CellProfiler versions",
    query: `SELECT * FROM cellprofiler_version`,
  },
];
