import { WasmContextManager } from "./context";

const S3_PREFIX =
  "https://cellpainting-gallery.s3.amazonaws.com/cpg0042-chandrasekaran-jump/source_all/workspace/publication_data/datasets/v0.13/parquet";

export const JUMP_TABLES = [
  "well",
  "perturbation",
  "compound",
  "compound_source",
  "orf",
  "crispr",
  "plate",
  "perturbation_control",
  "cellprofiler_version",
  "microscope_config",
  "microscope_filter",
];

export interface BootstrapProgress {
  loaded: number;
  total: number;
  lastTable?: string;
}

export async function registerJumpDatasets(
  contextManager: WasmContextManager,
  onProgress?: (p: BootstrapProgress) => void,
): Promise<void> {
  const total = JUMP_TABLES.length;
  let loaded = 0;
  onProgress?.({ loaded, total });

  await Promise.all(
    JUMP_TABLES.map(async (table) => {
      const url = `${S3_PREFIX}/${table}.parquet`;
      const res = await fetch(url);
      if (!res.ok) {
        throw new Error(`Failed to fetch ${table}.parquet: ${res.status} ${res.statusText}`);
      }
      const bytes = new Uint8Array(await res.arrayBuffer());
      await contextManager.registerParquet(table, bytes);
      loaded += 1;
      onProgress?.({ loaded, total, lastTable: table });
    }),
  );
}
