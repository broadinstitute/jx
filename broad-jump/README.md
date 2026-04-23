# broad-jump

Static site that lets anyone run live SQL+grammar-of-graphics queries against JUMP Cell Painting metadata from a browser, no install.

Runtime is [ggsql](https://ggsql.org) compiled to WebAssembly. Data is JUMP metadata flattened to SNAPPY parquets on S3 (`cellpainting-gallery/cpg0042-chandrasekaran-jump/source_all/workspace/publication_data/datasets/v0.13/parquet/`). All query execution and chart compilation happen client-side.

Deployed at <https://broadinstitute.github.io/jx/broad-jump/>.

## Local dev

Prereq: `ggsql-wasm/pkg/` built from the `nix-dev` branch of <https://github.com/shntnu/ggsql>. See `ggsql/.claude/worktrees/nix-dev/HANDOFF.md` for the incantation. The package path is hard-coded in `package.json` as `file:../../ggsql/.claude/worktrees/nix-dev/ggsql-wasm/pkg`; override `GGSQL_ROOT` env var in `build.mjs` if you have it elsewhere.

```bash
npm install
npm run dev      # watch build into dist/
npm run serve    # http-server on :8080
# open http://localhost:8080/
```

## Deploy

Automatic via `.github/workflows/deploy-broad-jump.yml` on push to `main`.
