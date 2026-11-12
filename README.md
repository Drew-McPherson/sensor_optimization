# Sensor Project

This repository contains the temperature sensor transformation and monitoring workflow for the distributed monitoring proof of concept.

## Repository layout

- [AGENTS.md](AGENTS.md) — repository instructions and workflow rules for agents and contributors.
- [instructions/README.md](instructions/README.md) — index for instruction-oriented documentation.
- [Distributed_Monitoring_POC_Project_Plan.md](Distributed_Monitoring_POC_Project_Plan.md) — canonical project plan and implementation rules.
- [scripts/README_scripts.md](scripts/README_scripts.md) — script usage and Phase 1/Phase 2/Phase 3 workflow notes.
- [artifacts/README_artifacts.md](artifacts/README_artifacts.md) — generated artifact inventory and expectations.

## Python environment setup

Install Python and VS Code, and make the repository available locally. Create a
separate virtual environment on each computer, outside Dropbox or other synced
folders: virtual environments contain machine-specific paths and should not be
synced between computers.

In PowerShell, replace the example paths with your repository and local
environment paths, then run:

```powershell
$RepoPath = 'C:\Projects\sensor_project'
$VenvPath = 'C:\venvs\sensor_project'
Set-Location -LiteralPath $RepoPath
python -m venv $VenvPath
& "$VenvPath\Scripts\Activate.ps1"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

In VS Code, use **Python: Select Interpreter** to select
`<venv-path>\Scripts\python.exe`, then select the same environment in the
notebook kernel picker. Install notebook support if VS Code prompts for it.
Verify the interpreter and dependencies in a notebook cell:

```python
import sys
print(sys.executable)
import numpy, pandas
print("Environment OK")
```

The printed executable should be the Python in the local environment. For
current notebook and script commands, prerequisites, and workflow order, see
[script usage](scripts/README_scripts.md).

For subsequent sessions, open a terminal in the repository and activate that
computer's environment again with `& "<venv-path>\Scripts\Activate.ps1"`.
If activation is blocked by PowerShell policy, run
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal,
then activate again. If `python` is not recognized, install Python and restart
VS Code; if imports fail, check `python -c "import sys; print(sys.executable)"`
and ensure dependencies were installed into that interpreter.

If VS Code settings force the old repository `.venv` interpreter, remove that
setting and select the local interpreter. Delete an old synced `.venv` only
after each computer is working with its own local environment. For a
single-computer workflow, an in-repository `.venv` is also an option; keep it
ignored by Git.

## Phase 1 implementation (US-1.16)

Run [phase1_implement.ipynb](scripts/phase1_implement.ipynb) top-to-bottom from a
fresh kernel, launched from the repository root or `scripts/`. It owns the
general transformation and optional duplicate investigations. Definitions can
be loaded without execution through the shared engine's
`load_phase1_definitions(root, audit=False)` API. The old transformation script
and misplaced duplicate-audit script are preserved under
`artifacts/phase1_archive/us116_retired_sources/`, not maintained entry points.

Phase 1 no longer reads or rewrites monitoring experiment configuration or
publishes a monitoring-cohort statistics row. The shared engine derives the
same full-precision cohort P90 from aligned data, verifies the successful Phase 1
publication, and embeds preparation evidence in downstream run records. Run
Phase 2 implementation and independent testing before Phase 3 validation and
production. Phase 2/3 readers reject stale preparation and receipts.

Production writes the aligned CSV, source inventory and consolidated run
record in `artifacts/phase1_operational/`. The record includes producer status,
settings, statistics, QC, gates and companion hashes. Limited runs require a
separate explicit destination and cannot overwrite current production.
See [Phase 1 usage](scripts/README_scripts.md#phase-1-implementation-us-116).

## Phase 1 independent testing (US-1.17)

After producing Phase 1 and current Phase 2/3 evidence, run
[phase1_test.ipynb](scripts/phase1_test.ipynb) in a fresh kernel. It exercises
independent fixture tests, verifies saved scientific evidence and creates a
separate Phase 1 validation receipt in `phase1_operational/`. Recorded scientific
baseline identities are checked without reading the recovery archive. The
exhaustive raw duplicate investigation is not part of its default run.

## Phase 1 analysis (US-1.18)

[phase1_analyze.ipynb](scripts/phase1_analyze.ipynb) combines the existing raw
temperature charts and tables with retained quality and duplicate findings.
It reads the retained aggregate and saved evidence without rebuilding inputs
or publishing artifacts. Historical aggregate-inclusive and source-only
populations are explicitly distinguished.

## Phase 3 reporting output

Phase 3 now has three maintained executable files:
[implementation](scripts/phase3_implement.py),
[independent testing](scripts/phase3_test.py), and
[saved-results analysis](scripts/phase3_analyze.ipynb).
See [current Phase 3 commands, prerequisites and rollback](scripts/README_scripts.md#us-334-phase3-output-and-operational-layout).
Current Phase 3 results use the approved
[`phase3_outputs` / `phase3_operational` layout](scripts/README_scripts.md#us-334-phase3-output-and-operational-layout):
four user-readable result files are paired with a separate run manifest, complete
C0 event evidence, and independent validation receipt. The removable
`phase3_archive` contains only superseded Phase 3 material and is not required
by any current workflow. The Phase 2 matched summary and events now use
`phase2_outputs/` and `phase2_operational/` respectively. See the US-3.34 removal proof and
manual archival instructions.
The original production notebook and compatibility modules were retired after
full-matrix equivalence; historical artifacts and the recoverable checkpoint
remain unchanged.

## Phase 2 current workflow (US-2.16)

The current Phase 2 experiment is the matched `phase3a_stable_cohort` run:
six sensors (A/C/D/E/F/G), 19,984 one-minute buckets, and the authoritative
cohort P90. Its saved baseline records 9,159 transmissions, 467
synchronizations, and zero false-safe/false-violated root states. Run the
implementation notebook, the isolated regression/saved-result test notebook,
and the read-only saved-results analysis notebook as documented in
[scripts/README_scripts.md](scripts/README_scripts.md#us-216-matched-phase-2-notebooks).
The test notebook generates a separate receipt required by analysis and Phase 3.
Both phases use the import-safe [shared monitoring engine](scripts/shared_monitoring_engine.py),
which also handles Phase 2 artifact publication and receipt verification.
The superseded Phase 2 files are preserved in `artifacts/phase2_archive/`.
Phase 3 production has been regenerated using a current independent receipt.

The local, Git-ignored [US-2.15 checkpoint](artifacts/phase2_baseline_us215/)
preserves a SHA-256 inventory, exact source copies, and unrounded per-bucket
behavior evidence. Its report records the pre-change Phase 2 test pass and the
pre-existing Phase 3 saved-result validation failure; neither result is
silently refreshed or hidden.

US-2.19 verified all 19,984 unrounded bucket rows against that checkpoint and
reran the current workflows in an isolated copy without the Phase 2 archive or
retired paths. See the [verification and manual-removal details](scripts/README_scripts.md#us-219-final-equivalence-and-archive-independence).
The checkpoint is separate from the removal queue and should be backed up
before you move it outside the workspace.

The general-dataset workflow is not part of the current path. Its notebook and
runner are retained under `artifacts/phase2_archive/scripts/`; neither is needed
by the matched notebooks or regression suite. They are preserved as historical
files and must be restored to `scripts/` before using their original paths.
No separate historical signed-margin
notebook was identified; the signed-margin baseline is a retained JSON
reference. Archived general-data artifacts and run logs have mixed-generation
policy/threshold metadata and are not matched outputs; see the
checkpoint inventory and lineage report.

## US-3.23 reproducibility and validation

The matched Phase 2 event CSV explicitly uses LF (`\n`) line endings on every
platform, with unchanged column/row ordering, values, and precision. Its SHA-256
changed intentionally from CRLF normalization only; monitoring policy and all
production numerical results remain unchanged. Historical Phase 2 and published
US-3.21/US-3.22 artifacts are preserved.

Run the automated two-fresh-process synthetic regression from the repository root:

```powershell
python -B -m unittest scripts.test_shared_monitoring.MatchedProductionTests.test_fresh_process_reproducibility_and_lf_events -v
```

Validation distinguishes state-machine **consistency replay** (not independent
proof), the offline **independent root-state correctness oracle** against
centralized observations, and **synthetic regression tests** with independently
specified fixtures, boundaries, hand counts, and injected defects.
See [US-3.23 details](scripts/README_scripts.md#phase-2-two-sided-monitoring-us-323) for
old/new event hashes, production metrics, full-suite commands, and provenance
comparison scope. The reproducibility test compares complete deterministic
summaries and byte-identical CSVs without rerunning the production dataset.

## Instruction documents

Additional instruction-style documentation lives under [instructions](instructions):

- [instructions/distributed_monitoring_notebook_required_changes.md](instructions/distributed_monitoring_notebook_required_changes.md)

## Archive note

The archived plan copy at [Archive/Distributed_Monitoring_POC_Project_Plan.md](Archive/Distributed_Monitoring_POC_Project_Plan.md) is intentionally preserved as historical reference material.

## Source-only GitHub note

This repository is prepared as a source-oriented project.

1. Raw dataset payloads under `Data/files_csv` are treated as local inputs and are not intended for normal Git tracking.
2. Generated pipeline outputs under `artifacts/` are expected to be produced locally from the scripts and config in this repo.
3. Local virtual environments, notebook execution outputs, and machine-specific editor settings should remain untracked.
