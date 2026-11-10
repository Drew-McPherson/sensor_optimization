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

## US-3.23 reproducibility and validation

The matched Phase 2 event CSV explicitly uses LF (`\n`) line endings on every
platform, with unchanged column/row ordering, values, and precision. Its SHA-256
changed intentionally from CRLF normalization only; monitoring policy and all
production numerical results remain unchanged. Historical Phase 2 and published
US-3.21/US-3.22 artifacts are preserved.

Run the automated two-fresh-process synthetic regression from the repository root:

```powershell
python -B -m unittest scripts.test_phase2_monitoring.MatchedProductionTests.test_fresh_process_reproducibility_and_lf_events -v
```

Validation distinguishes state-machine **consistency replay** (not independent
proof), the offline **independent root-state correctness oracle** against
centralized observations, and **synthetic regression tests** with independently
specified fixtures, boundaries, hand counts, and injected defects.
See [US-3.23 details](scripts/README.md#phase-2-two-sided-monitoring-us-323) for
old/new event hashes, production metrics, full-suite commands, and provenance
comparison scope. The reproducibility test compares complete deterministic
summaries and byte-identical CSVs without rerunning the production dataset.

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
