import * as esbuild from "esbuild";
import { copyFileSync, mkdirSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const isWatch = process.argv.includes("--watch");
const distDir = join(__dirname, "dist");

const GGSQL_ROOT = process.env.GGSQL_ROOT
  || join(__dirname, "../../ggsql/.claude/worktrees/nix-dev");

mkdirSync(distDir, { recursive: true });

console.log("Copying static files...");
copyFileSync(join(__dirname, "index.html"), join(distDir, "index.html"));
copyFileSync(
  join(GGSQL_ROOT, "ggsql-wasm/pkg/ggsql_wasm_bg.wasm"),
  join(distDir, "ggsql_wasm_bg.wasm"),
);
copyFileSync(
  join(__dirname, "node_modules/vscode-oniguruma/release/onig.wasm"),
  join(distDir, "onig.wasm"),
);
copyFileSync(
  join(GGSQL_ROOT, "ggsql-vscode/syntaxes/ggsql.tmLanguage.json"),
  join(distDir, "ggsql.tmLanguage.json"),
);

console.log("Building Monaco editor worker...");
await esbuild.build({
  entryPoints: [
    join(__dirname, "node_modules/monaco-editor/esm/vs/editor/editor.worker.js"),
  ],
  bundle: true,
  outfile: join(distDir, "editor.worker.js"),
  format: "iife",
});

const playgroundOptions = {
  bundle: true,
  format: "esm",
  platform: "browser",
  target: "es2020",
  sourcemap: true,
  nodePaths: [join(__dirname, "node_modules")],
  loader: { ".ttf": "file" },
  entryPoints: [join(__dirname, "src/main.ts")],
  outfile: join(distDir, "bundle.js"),
};

if (isWatch) {
  console.log("Starting watch mode...");
  const ctx = await esbuild.context(playgroundOptions);
  await ctx.watch();
  console.log("Watching for changes...");
} else {
  console.log("Building bundle...");
  await esbuild.build(playgroundOptions);
  console.log("Build complete!");
}
