# Sensor Project

This repository contains the temperature sensor transformation and monitoring workflow for the distributed monitoring proof of concept.

## Repository layout

- [AGENTS.md](AGENTS.md) — repository instructions and workflow rules for agents and contributors.
- [instructions/README.md](instructions/README.md) — index for instruction-oriented documentation.
- [Distributed_Monitoring_POC_Project_Plan.md](Distributed_Monitoring_POC_Project_Plan.md) — canonical project plan and implementation rules.
- [scripts/README.md](scripts/README.md) — script usage and Phase 1/Phase 2 workflow notes.
- [artifacts/README.md](artifacts/README.md) — generated artifact inventory and expectations.

## Reporting output

CSV-first report artifacts are generated directly by the Phase 2 notebook run:

1. Run [scripts/run_phase2_notebook.py](scripts/run_phase2_notebook.py).
2. Outputs are written to:
3. [artifacts/phase2_data_dictionary.csv](artifacts/phase2_data_dictionary.csv)
4. [artifacts/phase2_sensor_reduction_analysis.csv](artifacts/phase2_sensor_reduction_analysis.csv)

## Instruction documents

Instruction-style documentation now lives under [instructions](instructions):

- [instructions/PYTHON_ENV_SETUP_GUIDE.md](instructions/PYTHON_ENV_SETUP_GUIDE.md)
- [instructions/distributed_monitoring_notebook_required_changes.md](instructions/distributed_monitoring_notebook_required_changes.md)

## Archive note

The archived plan copy at [Archive/Distributed_Monitoring_POC_Project_Plan.md](Archive/Distributed_Monitoring_POC_Project_Plan.md) is intentionally preserved as historical reference material.

## Source-only GitHub note

This repository is prepared as a source-oriented project.

1. Raw dataset payloads under `Data/files_csv` are treated as local inputs and are not intended for normal Git tracking.
2. Generated pipeline outputs under `artifacts/` are expected to be produced locally from the scripts and config in this repo.
3. Local virtual environments, notebook execution outputs, and machine-specific editor settings should remain untracked.
