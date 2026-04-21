---
name: getting-started
description: Walk a first-time jx user from a fresh clone to a running marimo kernel with agent composition enabled. Trigger when the user says "help me get started", "onboard me", "set me up", "I'm new to jx", "first time using jx", "what do I do next", or asks any JUMP-composition question before a marimo kernel is running and marimo-pair is connected. Sets up uv, prompts the user to install the marimo-pair plugin, launches the marimo server on nb07. Use before compose-notebook: once setup is verified, hand off to that skill for the actual analysis.
---

# Getting started with jx

Your job: get this user from a cold clone to a live marimo kernel, then
hand off to the `compose-notebook` skill for the actual composition.

## Setup flow

### 1. Verify uv is installed

Run `uv --version`. If it fails, tell the user to run:

    curl -LsSf https://astral.sh/uv/install.sh | sh

Then have them source their shell profile (`. ~/.zshrc`) or open a new
terminal. Re-check `uv --version`.

### 2. Verify the marimo-pair plugin is installed

You cannot install a Claude Code plugin on the user's behalf - plugin
install is a slash command they run in their Claude Code UI. Ask them
to run:

    /plugin marketplace add marimo-team/marimo-pair
    /plugin install marimo-pair@marimo-team-marimo-pair

After they do, marimo-pair's tools (e.g. `execute_code`) appear in the
session. If you don't see those tools, the plugin isn't loaded yet.

### 3. Launch the marimo server

From the jx repo root, pick a free port and start nb07 in `--sandbox`
mode so the PEP 723 header provisions a venv automatically:

    PORT=$(python -c "import socket; s=socket.socket(); s.bind(('127.0.0.1',0)); print(s.getsockname()[1])")
    env -u PYTHONPATH uvx marimo edit --sandbox --headless --no-token \
        --port $PORT notebooks/nb07_compound_neighborhood.py

Use `run_in_background=true` on the Bash call so you can poll while
deps install. First launch installs ~84 packages (~2 min); subsequent
launches are near-instant. Verify the server is up with:

    curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:$PORT/

Expect HTTP 200. Tell the user the URL so they can open the browser UI
alongside your session if they want to watch cells render.

### 4. Hand off to compose-notebook

Once the kernel is live and marimo-pair is connected:

1. Ask the user what biological question they want to explore (a
   compound of interest, a gene, a morphological phenotype).
2. Invoke the `compose-notebook` skill and follow its "Process for a
   new composition" checklist against the running kernel.

## Gotchas

- **Nix shells poison PYTHONPATH** with a bad websockets shim that
  crashes `marimo edit` on startup. The `env -u PYTHONPATH` prefix in
  step 3 avoids this. Apply it to any marimo invocation on Nix.
- **`--sandbox` is required.** Without it, `uvx marimo edit` opens the
  file picker but does not provision a venv from the PEP 723 header -
  opening any notebook then fails with `ModuleNotFoundError: polars`.
- **Ports 2718-2720 are often taken** on shared machines. The step-3
  picker grabs a random free port. Don't hardcode.
- **First nb07 run downloads ~250 MB** (Zenodo similarity matrix),
  cached under `~/.cache/jx/`. One-time cost - warn the user if they're
  on a slow network.

## Don't

- Don't write JUMP query code before setup is verified - you'll burn
  the user's time debugging import errors and missing deps.
- Don't vendor marimo-pair into this repo. It's upstream at
  `marimo-team/marimo-pair`; installing via the plugin marketplace
  keeps users current with fixes.
- Don't bypass `compose-notebook` after setup completes. The whole
  point is composition from the catalog; writing ad-hoc queries
  defeats the skill's purpose.
