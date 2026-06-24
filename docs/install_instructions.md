# Installation for skysat_stereo

`skysat_stereo` uses [pixi](https://pixi.sh) to manage all of its dependencies
and to install the command line tools. Everything — the Python stack, the
git-based `pygeotools`/`demcoreg`/`rpcm` packages, **and the NASA Ames Stereo
Pipeline (ASP)** — is pinned in `pixi.toml` and locked in `pixi.lock`. There is
no separate, manual ASP download or `PATH` setup.

## Prerequisites

- Install `pixi` (see https://pixi.sh/latest/#installation), e.g.
  `curl -fsSL https://pixi.sh/install.sh | bash`.

## Install

1. Clone the repository:
   `git clone https://github.com/uw-cryo/skysat_stereo.git`
2. From the repository root, install the environment:
   `pixi install`

   This creates the `skysat_stereo` environment and installs:
   - the Python dependencies from `conda-forge`,
   - the Ames Stereo Pipeline (`stereo-pipeline`) from the
     `nasa-ames-stereo-pipeline` channel (which bundles ISIS), and
   - this package (editable) together with every command line tool in
     `scripts/` as an executable.

### Notes on the environment

- ASP ships custom "asp"-flavored builds of a few shared libraries, so the
  workspace disables strict channel priority (`channel-priority = "disabled"`),
  matching ASP's recommended flexible channel priority.
- The conda ASP package requires a modern stack (Python ≥3.13, GDAL 3.12,
  GEOS 3.14), so the dependency pins are deliberately loose on their upper
  bounds.
- ISIS (bundled with ASP) needs `ISISROOT` to point at the environment prefix.
  `pixi.toml`'s `[activation.env]` sets `ISISROOT = "$CONDA_PREFIX"`
  automatically, so the ASP binaries work out of the box.

## Usage

- Run a command directly through pixi, e.g.
  `pixi run skysat_triplet_pipeline.py --help`
- Or drop into an activated shell where all of the skysat_stereo commands and
  the ASP binaries (`parallel_stereo`, `point2dem`, `dem_mosaic`,
  `bundle_adjust`, ...) are on your `PATH`:
  `pixi shell`
  then `skysat_triplet_pipeline.py --help`, `skysat_overlap.py ...`, etc.

The available command line tools are listed in the [README](../README.md#contents).
