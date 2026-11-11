# Change Log

This file tracks implemented changes in this repository.

## Logging Policy

## 2026-11-11

### Restored the GitHub root README filename
- Summary: Restored the project overview to the root `README.md` filename while keeping the scripts and artifacts guides purpose-specific.
- Affected files: `README.md`, `CHANGELOG.md`, `User Stories/US-3.34_organize_phase3_outputs_operational_and_archive.md`.
- Rationale and impact: GitHub automatically recognizes a root `README.md` for repository landing-page display. The overview's links still point to `scripts/README_scripts.md` and `artifacts/README_artifacts.md`; no runtime behavior changes.
- Validation: Verified the root README and its links to the purpose-specific guides.

### Renamed purpose-specific README documents
- Summary: Kept the script workflow guide and artifact inventory as `scripts/README_scripts.md` and `artifacts/README_artifacts.md`; the root project overview remains `README.md` for GitHub landing-page display. Updated active documentation links, notebook guidance, preflight output, and the Phase 3 path-safety test.
- Affected files: `README.md`, `scripts/README_scripts.md`, `artifacts/README_artifacts.md`, `scripts/run_phase2_notebook.py`, `scripts/phase3_test.py`, `scripts/build_phase2_temperature_sensors.ipynb`, `Distributed_Monitoring_POC_Project_Plan.md`, `User Stories/US-3.27_to_US-3.33_phase3_workflow_consolidation.md`, `User Stories/US-3.34_organize_phase3_outputs_operational_and_archive.md`, `CHANGELOG.md`.
- Rationale and impact: The three documents have distinct audiences and scopes; the two nested guides have descriptive names, while the root overview uses GitHub's conventional README filename. The separate `instructions/README.md` directory index is unchanged. No script behavior, data, or output format changes.
- Validation: Verified all renamed-file links and path references, and ran the focused path-safety test.

### Specified three-folder Phase 3 artifact cleanup (US-3.34)
- Summary: Created one user story for renaming phase3_current to phase3_outputs, separating necessary operational artifacts into phase3_operational, safely consolidating operational evidence, and moving unneeded files into the user-removable phase3_archive queue.
- Affected files: User Stories/US-3.34_organize_phase3_outputs_operational_and_archive.md; CHANGELOG.md.
- Rationale and impact: Defines dependency classification, versioned mappings, independent-reference preservation, coordinated writer/test/notebook changes and verification with archive/old paths physically absent. Acknowledges that previous migration folders have already been archived. This is a specification only; no runtime code, artifact contents, formats or locations were changed.
- Validation: Documentation-only change; reviewed against the existing user-story format and current workspace inventory. Implementation and execution verification are deferred to the story.

### Implemented and verified Phase 3 outputs/operational/archive layout (US-3.34)
- Summary:
  - Changed the default user-facing bundle to `artifacts/phase3_outputs/` and split its user-readable `phase3_summary.json` from the schema-version-2 operational manifest, complete C0 events, and independent validation receipt in `artifacts/phase3_operational/`.
  - Relocated 14 SHA-256-verified independent references into `phase3_operational/references/`; rewired Phase 2's historical-baseline lookup, Phase 3 implementation/tests, and saved-only analysis for the paired directories and candidate workflows.
  - Preserved the former six-file `phase3_current/` bundle and 28 superseded root-level Phase 3 files under the user-removable `phase3_archive/`; no archive contents are automatically deleted. The independently owned root-level Phase 2 two-sided baseline/events remain outside this cleanup.
- Affected files:
  - `scripts/implement_phase3.py`, `scripts/test_phase3.py`, `scripts/phase2_monitoring.py`, `scripts/test_phase2_monitoring.py`, `scripts/analyze_phase3.ipynb`
  - `README.md`, `scripts/README.md`, `artifacts/README.md`, `.gitignore`
  - `User Stories/US-3.34_organize_phase3_outputs_operational_and_archive.md`, `CHANGELOG.md`
  - `artifacts/phase3_outputs/`, `artifacts/phase3_operational/`, `artifacts/phase3_archive/`
- Rationale and impact:
  - Separates four user-facing results from three machine-owned run files and retained independent references. The old mixed-purpose `phase3_run.json` is split into an output summary and a schema-version-2 manifest with explicit same-run/hash-checked receipt linkage and durable in-progress/failure state.
  - Result, size, snapshot, and C0 event CSVs remained byte-identical to the former bundle. Phase 2 monitoring/scientific behavior and independently owned outputs were preserved; the root historical-baseline relocation is a path-only change, with its original producer hash explicitly pinned and documented.
  - Added output-directory creation for isolated candidates and normalized relative output paths before validating paired manifest locations.
- Validation:
  - Passed the full final-source receipt gate: 166 Phase 3 behavioral/replay and independent Phase 1/Phase 2 tests, zero skips/failures/errors.
  - Candidate and default production passed; saved-output verification and all six fresh-process replays passed for both pairings. Compared all result rows against independent references and confirmed byte identity for the three scientific CSVs and C0 events.
  - Both candidate and default analysis passed from clean kernels with the historical view enabled (12 displayed tables, 8 figures, no writes).
  - Repeated the full gate, default production, saved checks, replays, and notebook analysis with `phase3_archive/`, `phase3_current/`, and all old root-level Phase 3 paths physically unavailable. Restored the archive byte-for-byte; all 34 archived files retain their original SHA-256 values.
  - Final receipt SHA-256: `5AC84E60C9A390036142553ACCC177E5EFBCFB04E97464A2D005D95DBB84DB8D`. See `artifacts/README.md` for the complete original-to-current/archive mapping and final source/artifact hashes.

### Renamed maintained Phase 3 entry points with a consistent prefix
- Summary: Renamed `implement_phase3.py`, `test_phase3.py`, and `analyze_phase3.ipynb` to `phase3_implement.py`, `phase3_test.py`, and `phase3_analyze.ipynb`, respectively. Updated Python imports/module commands, runtime provenance paths, notebook discovery/imports, tests, and current documentation links.
- Affected files: `scripts/phase3_implement.py`, `scripts/phase3_test.py`, `scripts/phase3_analyze.ipynb`, `scripts/phase2_monitoring.py`, `scripts/test_phase2_monitoring.py`, `scripts/README.md`, `README.md`, `Distributed_Monitoring_POC_Project_Plan.md`, `Phase3A_Pivot_Plan.md`, `User Stories/US-3.27_to_US-3.33_phase3_workflow_consolidation.md`, `User Stories/US-3.34_organize_phase3_outputs_operational_and_archive.md`, `artifacts/README.md`, `CHANGELOG.md`.
- Rationale and impact: Gives all three maintained Phase 3 entry points the requested `phase3_` filename format without changing their roles or scientific behavior. Python CLI/module invocation changes from `scripts.implement_phase3` / `scripts.test_phase3` to `scripts.phase3_implement` / `scripts.phase3_test`; external commands and links must use the new names.
- Validation: Both renamed Python modules compiled and imported; `python -B -m scripts.phase3_test --record-validation artifacts\phase3_operational\phase3_validation.json` passed 166 tests with no skips/failures/errors; renamed production and saved/replay checks passed; the renamed analysis notebook executed successfully in a clean kernel. Regenerated the independent receipt (`190F120D134FB25F6FF98A66E3301004B6DC83663F054C686E49F8C4D5ADF538`) and production manifest for the renamed source paths. Existing scientific result and event CSV bytes are unchanged.

### Consolidated Phase 3 artifacts under the approved phase3_ contract (US-3.33)
- Summary:
  - User approved a six-file schema-version-1 bundle after requiring every filename to start with phase3_: results, cluster sizes, snapshots, equivalence events, run metadata and independent validation.
  - Combined the 3 control and 38 alpha-result records; combined all 246 cluster-size rows, preserving zero bins and explicit control alpha semantics. Kept compact selected snapshots distinct from complete C0 synchronization events.
  - Combined comparison/completion/failure/equivalence metadata into phase3_run.json with explicit status/kind/version, artifact hashes, keys, schemas, record counts and scientific semantics. Independent validation remains a hash-referenced phase3_validation.json rather than an embedded duplicate.
  - Updated production, runtime equivalence, saved verification, replay verification and the saved-only analysis notebook together. Old-format destinations fail without changes; failed/in-progress runs cannot certify leftover files.
- Affected files:
  - scripts/implement_phase3.py, scripts/test_phase3.py, scripts/analyze_phase3.ipynb
  - README.md, scripts/README.md, artifacts/README.md
  - User Stories/US-3.27_to_US-3.33_phase3_workflow_consolidation.md, .gitignore, CHANGELOG.md
  - artifacts/phase3_artifacts_us333/ (ignored preserved pre-migration bundle, isolated candidate and verification evidence); artifacts/phase3_current/ (verified current bundle after cutover)
- Rationale and impact:
  - Reduces the current bundle from eleven files to six purpose-oriented, phase-prefixed files without changing algorithms, scientific results, precision, comparator identity, initialization accounting, independent validation or saved-only analysis.
  - This is an approved current output schema/path change; old readers and receipts must not silently certify the new bundle. Historical root-level artifacts, PNGs, Phase 2 prerequisites and sealed migration/checkpoint evidence remain unchanged and separate.
  - The immediately preceding eleven-file bundle is preserved in a hash-verified archive before migration; no duplicate legacy-format exports or additional maintained migration script are introduced.
- Validation: outcomes and field/record preservation evidence are recorded with the story completion and the isolated artifacts/phase3_artifacts_us333/verified report.
  - Passed 166 final-source tests, production/all six fresh-process replays and independent saved/replay checks. Verified every field of 41 result records and 246 size-bin records; 2,372 snapshot rows and 467 C0 event rows remained byte-identical CSVs. Scientific comparison/equivalence/diagnostic JSON and core scientific ASTs were preserved.
  - Rejected eight deliberate corruptions, including changed scientific content with recomputed inventory hashes; real clean kernels passed five/eight-chart artist/table reconciliation and three expected missing/old-format/unsafe-export failures. Original references/current outputs/Phase 2 prerequisites and all 178 sealed checkpoint files retained their hashes during the gate.
  - Published the exact proven six-file bundle to artifacts/phase3_current, preserving the previous eleven-file directory at artifacts/phase3_artifacts_us333/previous_current plus its ZIP/inventory. Current receipt provenance, active saved/replay checks and five-chart real-kernel analysis passed without changing published bytes.
  - Initial Windows directory-rename publication failed after safely preserving the old current bundle. Retained failed evidence and switched only the transfer procedure to copying verified bytes into a new current directory, publishing phase3_run.json last; source/data/receipt hashes and scientific acceptance conditions were unchanged.

### Verified and switched Phase 3 to the three-file workflow (US-3.32)
- Summary:
  - Removed retired notebook/facade dependencies from implementation, tests, validation receipts and provenance; added the canonical isolated `--equivalence` mode.
  - Replaced the obsolete notebook architecture test with an exact three-file surface check and retained scientific regression coverage and independent cross-phase suites.
  - Removed Phase 2's integrity-check dependency on the retired Phase 3 notebook. Added an explicit separate output directory for genuinely regenerated current Phase 2 prerequisites; current Phase 3 selects `artifacts/phase2_current` when present and rejects incomplete/stale references without falling back.
  - Retirement is gated on an isolated final-source test/production/notebook run, exact full-matrix comparison, protected-file integrity and verified recovery archives. Original scientific artifacts and historical findings are not rewritten.
- Affected files:
  - scripts/implement_phase3.py, scripts/test_phase3.py
  - scripts/phase2_monitoring.py, scripts/test_phase2_monitoring.py
  - Retired scripts/build_phase3_temperature_clustering.ipynb, scripts/phase3a_protocol_equivalence.py, scripts/phase3a_us325.py, scripts/test_phase3_history.py, scripts/test_phase3_monitoring.py, scripts/test_phase3a_protocol_equivalence.py, scripts/test_phase3a_us325.py
  - README.md, scripts/README.md, artifacts/README.md, Distributed_Monitoring_POC_Project_Plan.md
  - User Stories/US-3.27_to_US-3.33_phase3_workflow_consolidation.md, .gitignore, CHANGELOG.md
  - artifacts/phase3_cutover_us332/ and artifacts/phase2_current/ (ignored local execution/recovery evidence and freshly generated prerequisite)
- Rationale and impact:
  - Leaves exactly implementation, testing and analysis as maintained Phase 3 executable surfaces, without dropping independent Phase 1/2 checks or altering monitoring algorithms.
  - Code/test hashes, integrity inventories, execution paths/run IDs, commands and removed notebook/facade provenance keys necessarily change. Historical root-level evidence stays immutable; fresh receipts and production are required for the final source.
  - Existing scientific CSV names/schemas/precision and saved-only analysis remain unchanged. Artifact consolidation remains US-3.33 and requires separate approval.
- Validation: final-source cutover evidence is recorded in artifacts/phase3_cutover_us332/verified/validation_report.json; see the story completion record for verified outcomes. The first comparison-harness attempt stopped because live tuples were compared to deserialized JSON arrays despite identical canonical fingerprints. Preserved that failure and corrected the harness to compare canonical JSON rows byte-for-byte; implementation/test sources and scientific comparison tolerances were unchanged.
  - Passed 162 final-source tests, production/all six fresh-process replays, independent saved verification, exact full summaries/raw events/canonical decisions for 41 configurations (819,344 decisions; 16,210 initialization/root-sync events), six byte-identical scientific CSVs and fresh Phase 2 event bytes, clean-kernel five/eight-chart analysis/artist/table audits and three expected rejection cases.
  - Verified all sealed baseline hashes and all 85 checkpoint ZIP members before retirement; preserved a hash-verified archive of the seven immediately preceding files. Twenty-eight Phase 3 scientific definitions and Phase 2 monitor definitions remain AST-identical.
  - After retirement, active-checkout fresh Phase 2 prerequisites matched the proven candidate byte-for-byte; the actual external 162-test receipt matched active provenance and was copied without edits. Default production, independent saved/replay checks, missing-current-reference rejection and five-chart real-kernel analysis passed. artifacts/phase3_current is ready to use; original scientific/historical files remained unchanged.

### Consolidated existing Phase 3 analysis into a saved-only notebook (US-3.31)
- Summary:
  - Created scripts/analyze_phase3.ipynb with existing source/moment methodology, hand calculations, protocol/accounting explanations, validation/C0/comparator context, matched tables, detailed interpretation, five revised charts, and limitations/deferred research gaps.
  - Relocated revised plotting and the AST-identical detailed interpretation out of production; retained numeric comparisons/tables/minima/limits and all scientific CSV contracts. Added explicit versioned presentation metadata and empty automatic plot exports.
  - Added an import-safe read-only analysis loader that validates saved schemas/accounting, source snapshots, run/completion/failure consistency, comparisons/minima, receipt integrity and current provenance without running monitors/tests/replays. Added analysis-isolation/presentation/receipt-separation regressions and wired loader verification into saved-output checks.
  - Preserved three historical chart views as an opt-in section with their original signed-margin comparator; default charts remain inline and optional PNG exports require a new separate directory.
- Affected files:
  - scripts/analyze_phase3.ipynb
  - scripts/implement_phase3.py
  - scripts/phase3a_us325.py
  - scripts/test_phase3.py
  - scripts/build_phase3_temperature_clustering.ipynb
  - scripts/README.md
  - artifacts/README.md
  - User Stories/US-3.27_to_US-3.33_phase3_workflow_consolidation.md
  - .gitignore
  - CHANGELOG.md
  - artifacts/phase3_analysis_us331/ (ignored local candidate, actual logs, clean-kernel notebooks, artist audits, checked optional exports, relocated source/procedure, and interrupted iteration evidence)
- Rationale and impact:
  - Makes existing scientific analysis readable in one executable saved-results narrative without new experiments, metrics, tuning, or expanded claims. Retains historical/revised/centralized denominators, prespecified alpha 0.10 versus in-sample minima, actual messages versus checks, and local-resolution versus avoided-synchronization distinctions.
  - Revised production no longer generates five PNGs or detailed narrative. Comparison JSON uses presentation.schema_version=1 and an analysis-notebook pointer instead of the detailed interpretation payload; outputs.plots is empty and completion visualization metadata identifies saved-only analysis. Former private _plot_results/_interpretation facade exports are removed. Historical PNGs and explicit legacy-sweep behavior remain intact until cutover.
  - Normal analysis preserves production/historical evidence and rejects missing/stale/mixed data rather than fabricating results. Analysis notebook output saves are intentionally not production-receipt dependencies; its exact source and execution are recorded separately. Original scientific files and sealed baseline are not overwritten.
  - Installed missing nbclient/nbformat in the selected environment only after the clean-kernel dependency check failed; these are optional validation tools, not added production dependencies. Preserved the interrupted raw-notebook receipt-coupling iteration and validated final source afresh.
- Validation:
  - Canonical external suite: 159 tests passed, including four new analysis/presentation/isolation/receipt-separation checks. Pylance syntax checks passed for the implementation and testing modules.
  - Isolated production passed three controls, 38 clustered configurations and six fresh-process replays without revised PNG/narrative generation. Independent saved-output verification also passed.
  - Real clean kernels rendered five revised charts by default and eight with historical view/explicit export enabled. Actual Matplotlib line/stacked-area/bar values and displayed table values reconciled with saved rows; eight optional PNGs were verified.
  - Missing outputs, stale provenance and unsafe export destinations failed explicitly. Instrumented kernels blocked monitor/production/replay calls and CSV writes, with no project testing modules imported. Analysis source/configuration/production/historical inputs remained unchanged.
  - Six scientific CSVs reproduced byte-for-byte against the sealed baseline; 28 scientific definitions and the relocated interpretation remained AST-identical. Sealed checkpoint hashes and original-file integrity verified.

### Consolidated Phase 3 testing and independent saved-output verification (US-3.30)
- Summary:
  - Relocated all maintained Phase 3 tests into scripts/test_phase3.py with explicit behavior/saved/replay selectors, executable coverage mapping, and compatibility-only former test modules. Preserved all 102 legacy cases, including inherited SMIC coverage and protocol defect injection.
  - Added independent saved schemas, configuration grids, finite values, transmission/pathway/check/cluster-size reconciliation, source-derived truths, snapshot/moment/allowance checks, summary/table/minimum reconciliation, current provenance/receipt verification, and read-only C0/six weighted-control replay checks.
  - Moved the external validation producer to the canonical test script. Schema-version-2 production receipts require actual complete behavioral/replay/external Phase 1/2 scope, test IDs/counts, zero skips/failures, unchanged protected files, and exact current input/code/configuration hashes.
- Affected files:
  - scripts/test_phase3.py
  - scripts/test_phase3_history.py
  - scripts/test_phase3_monitoring.py
  - scripts/test_phase3a_protocol_equivalence.py
  - scripts/test_phase3a_us325.py
  - scripts/implement_phase3.py
  - scripts/README.md
  - artifacts/README.md
  - User Stories/US-3.27_to_US-3.33_phase3_workflow_consolidation.md
  - .gitignore
  - CHANGELOG.md
  - artifacts/phase3_testing_us330/ (ignored local candidate, verification reports/logs, coverage evidence, failed/interrupted attempts, and archived one-off procedure)
- Rationale and impact:
  - Establishes one authoritative testing entry point without trusting saved pass flags, rewriting results, or copying Phase 1 statistics-generation tests. Former module commands still forward to canonical coverage; production never imports or launches tests.
  - Old receipts and saved validation metadata are intentionally stale for the new source revision and must be regenerated through real checks, not relabeled. Scientific algorithms, artifact basenames/schemas/precision/capture scope, historical references, and the sealed checkpoint remain unchanged.
  - Fixed an observed skipped-test diagnostic serialization failure by recording test IDs/reasons rather than unittest objects. Retained the failed and interrupted attempts and validated final source from a fresh isolated copy.
- Validation:
  - Canonical external suite: 155 tests passed (107 behavioral/verifier cases, two replay checks, 42 Phase 2 tests, four Phase 1 statistics tests). Pylance syntax checks passed for the canonical testing and implementation modules.
  - Unified production passed all three controls, 38 clustered configurations and six independent subprocess replays; the new current receipt was accepted and stale US-3.29 receipts rejected nonzero.
  - Separate saved-output/replay verification passed all three checks with unchanged result bytes. Mutated summary counts, snapshots, missing configurations, and stale provenance failed; unit regressions additionally rejected malformed schemas, duplicates, nonfinite moments/numbers, incorrect shares/grids and unsafe report destinations. Missing saved outputs produced an explicit failed report.
  - All six scientific CSVs reproduced byte-for-byte against the sealed baseline. Twenty-eight scientific definitions and ten of twelve legacy test classes remained AST-identical; the other two adapted receipt/provenance assertions only. Original code/configuration/artifact files remained unchanged during validation; sealed checkpoint hashes verified.

## 2026-11-10

### Unified revised Phase 3 production execution (US-3.29)
- Summary:
  - Integrated runtime equivalence and US-3.25/3.26 orchestration into the canonical implementation; former runners are thin compatibility facades. Revised C0/C1/C2 plus 38 clustered configurations are the default, with the historical sweep explicitly selected.
  - Added isolated output directories, current externally executed validation receipts, strict C0 cache provenance/event checks with genuine regeneration, read-only canonical subprocess replays, expanded protected-file checks, and durable current-run failure/completion records.
  - Added orchestration/receipt regressions and a transitional external receipt-producing interface in the existing test module. Production no longer imports or automatically runs regression suites.
- Affected files:
  - scripts/implement_phase3.py
  - scripts/phase3a_protocol_equivalence.py
  - scripts/phase3a_us325.py
  - scripts/test_phase3a_protocol_equivalence.py
  - scripts/test_phase3a_us325.py
  - scripts/README.md
  - artifacts/README.md
  - .gitignore
  - User Stories/US-3.27_to_US-3.33_phase3_workflow_consolidation.md
  - CHANGELOG.md
  - artifacts/phase3_production_us329/ (local isolated validation evidence, including initial failure and successful verified run)
- Rationale and impact:
  - Establishes one authoritative revised production entry point without copying Phase 1/2 or changing scientific algorithms. Default outputs intentionally move to artifacts/phase3_current; artifact basenames, scientific schemas/precision, capture scope, plots, and narrative are preserved.
  - Requires independently executed validation for the exact current source/inputs/configuration. Missing/stale receipts block evaluation; stale C0 evidence is regenerated in isolation rather than relabeled. Historical artifact roots and sealed evidence remain unchanged.
  - Removed an unnecessary immediate second write of freshly generated C0 metadata after an observed Windows access-denied failure; retained that failed attempt and reran validation with final source and a fresh receipt.
- Validation:
  - External six-module suite: 148 tests passed. Unified production and all six independent fresh-process replays passed; current C0 cache reuse, genuine stale-C0 regeneration, and missing/stale receipt failures verified.
  - All 41 complete summaries, 819,344 per-bucket decisions, and 16,210 initialization/synchronization events matched the sealed US-3.27 baseline exactly; six scientific CSVs reproduced byte-for-byte.
  - Twenty-eight original scientific definitions remained AST-identical. All 63 candidate production-protected files and original source/configuration/artifact files remained unchanged during validation; sealed checkpoint hashes verified. Pylance syntax checks passed for the implementation and updated test module.

### Extracted importable Phase 3 implementation (US-3.28)
- Summary:
  - Relocated 29 notebook definitions into one import-safe canonical module and replaced notebook implementation cells with imports. Retained the explicit historical sweep entry point and legacy Phase 2-scheduled regression helpers.
  - Rewired all Phase 3 tests and transitional runners to ordinary imports; removed tagged-cell execution and synthetic-module loading.
  - Added clean-process import/canonical-source checks and a negative-control provenance test; revised validation now requires the current implementation hash and rejects mismatched execution roots.
- Affected files:
  - scripts/implement_phase3.py
  - scripts/build_phase3_temperature_clustering.ipynb
  - scripts/phase3a_protocol_equivalence.py
  - scripts/phase3a_us325.py
  - scripts/test_phase3_history.py
  - scripts/test_phase3_monitoring.py
  - scripts/test_phase3a_protocol_equivalence.py
  - scripts/test_phase3a_us325.py
  - scripts/README.md
  - artifacts/README.md
  - .gitignore
  - User Stories/US-3.27_to_US-3.33_phase3_workflow_consolidation.md
  - CHANGELOG.md
  - artifacts/phase3_extraction_us328/ (local isolated validation outputs/report/logs)
- Rationale and impact:
  - Removes notebook-state dependencies while retaining one authoritative implementation and all existing scientific behavior. Twenty-eight definitions remained AST-identical; only the historical sweep's notebook-path fallback and implementation-source provenance changed. Revised orchestration unification remains US-3.29 work.
  - Implementation hashes are added to revised and historical sweep provenance; old reports are not silently re-certified. Original configuration/scientific artifacts and the sealed US-3.27 checkpoint were not overwritten.
- Validation:
  - Six-module regression suite: 141 tests passed, including import-safety and missing/stale implementation-hash rejection. Pylance syntax checks passed for the new implementation and updated integration tests.
  - Isolated fresh equivalence command: 123 tests passed; revised production runner: 137 tests and all six fresh-process replays passed (overlapping suites).
  - All 41 configurations exactly matched baseline summaries, raw events, and canonical decision traces (819,344 decisions; 16,210 initialization/synchronization events). Six scientific CSVs reproduced byte-for-byte.
  - All historical notebook code cells executed successfully from a clean process; explicit module CLI help and whitespace checks passed.

### Established recoverable Phase 3 pre-consolidation baseline (US-3.27)
- Summary:
  - Preserved 85 original source/configuration/documentation/artifact files, including required untracked sources, in a member-hash-verified archive with Git state, environment/package inventory, schemas, notebook tags, and provenance dependencies.
  - Executed existing tests and the unchanged revised evaluation in an isolated copy; retained full observational evidence for C0/C1/C2 and all 38 clustered configurations.
  - Added recovery/revalidation instructions, a story completion record, and a Git ignore rule for the generated checkpoint.
- Affected files:
  - .gitignore
  - scripts/README.md
  - artifacts/README.md
  - User Stories/US-3.27_to_US-3.33_phase3_workflow_consolidation.md
  - CHANGELOG.md
  - artifacts/phase3_baseline_us327/ (local generated archive, isolated workspace, reports, logs, capture/verification procedures, and full-matrix evidence)
- Rationale and impact:
  - Creates a recoverable, independently verified reference before implementation relocation. No production code, notebook definitions, configuration, or original scientific artifacts changed; no files staged or committed.
  - Found a pre-existing stale notebook hash in the original US-3.24 summary. Preserved the failed attempt and regenerated genuine equivalence evidence only in the isolated copy, with byte-identical scientific events; no gate or hash check was bypassed. The original summary remains stale and requires real revalidation before future production runs.
- Validation:
  - Existing six-module suite: 139 tests passed; fresh US-3.24 command: 122 tests passed; unchanged US-3.25 runner: 135 tests and six fresh-process replays passed (overlapping suites).
  - Captured and independently hash/reconciliation-verified 41 configurations, 819,344 decisions, and 16,210 initialization/synchronization events.
  - All 85 archive members verified. Five US-3.25 scientific CSVs plus US-3.24 equivalence events reproduced byte-for-byte; all 17 production protected artifacts remained unchanged during the revised evaluation.

### Planned Phase 3 three-file workflow consolidation (US-3.27 through US-3.33)
- Summary:
  - Added one consolidated story document covering baseline preservation, implementation extraction, unified execution, test consolidation, existing-analysis consolidation, verified cutover, and subsequent artifact consolidation.
- Affected files:
  - User Stories/US-3.27_to_US-3.33_phase3_workflow_consolidation.md
  - CHANGELOG.md
- Rationale and impact:
  - Defines a gated, recoverable migration to one implementation script, one testing script, and one analysis notebook. Separates script refactoring from artifact redesign and excludes new scientific analysis or algorithm changes. Planning documentation only; no code, experiments, or generated scientific outputs changed.

### Hardened US-3.25 validation, reproducibility, and reporting (US-3.26)
- Summary:
  - Moved the initial protected-artifact SHA-256 snapshot ahead of contract, prerequisite, and test validation; partial failures now attempt a final integrity comparison and atomically persist concise diagnostics.
  - Required a complete, passing 38-pair alpha grid before exploratory minima, checked US-3.25 output fingerprints and seven reference configurations before publication, and recorded hashes for all five executed regression modules.
  - Added fresh-process replays for C1/C2 and clustered FMIC/SMIC at alpha 0.10 and 0.65; added the saved-result singleton pathway-composition plot, a zero-failure current-run record, and a concise US-3.26 completion summary.
  - Added regressions for alpha-sensitive source clustering, alpha-order independence, fixed-weight partition comparisons with and without escalation, grid/ranking exclusion, and durable failure recording.
- Affected files:
  - scripts/phase3a_us325.py
  - scripts/test_phase3a_us325.py
  - scripts/README.md
  - CHANGELOG.md
  - artifacts/phase3a_us325_control_results.csv
  - artifacts/phase3a_us325_control_cluster_size_summary.csv
  - artifacts/phase3a_us325_alpha_results.csv
  - artifacts/phase3a_us325_cluster_size_summary.csv
  - artifacts/phase3a_us325_event_snapshots.csv
  - artifacts/phase3a_us325_comparison_summary.json
  - artifacts/phase3a_us325_singleton_communication_composition.png
  - artifacts/phase3a_us325_failed_configurations.json
  - artifacts/phase3a_us326_completion_summary.json
- Rationale and impact:
  - Makes validation failures inspectable and prevents failed/incomplete runs from being ranked or represented as a successful current run. No validated FMIC/SMIC mathematics, Phase 2 behavior, or scientific conclusions were changed; saved regression fingerprints passed and all 17 protected historical/prerequisite artifacts remained byte-identical.
- Validation:
  - `python -B -m unittest scripts.test_phase3a_us325 -q`: 13 focused tests passed.
  - `python -B -m scripts.phase3a_us325`: full five-module regression suite passed all 135 tests; all 38 clustered configurations and C0/C1/C2 passed correctness/accounting.
  - All six fresh-process replays passed; C0/C1/C2 remained 9,159/8,964/8,962 messages and 467/457/457 root synchronizations. The established FMIC/SMIC alpha=0.10 and alpha=0.65 values matched.
  - All five executed test-module hashes were recorded; protected artifact inventory captured and verified 17 unchanged files.

### Implemented US-3.25 weighting and clustering evaluation
- Summary:
  - Added a gated runner that reuses the US-3.24 C0 result, runs FMIC/SMIC weighted singleton controls, then validates the complete 19-alpha clustered grid for both methods.
  - Added actual-transmission pathway composition, controlled weighting/clustering contrasts, cluster-size check and repeat diagnostics, compact event snapshots, four saved-result plots, provenance, and fresh-process alpha=0.10 replays.
  - Added synthetic tests for communication accounting, alpha-independent singleton behavior, repeated local checks and reset behavior, exact zero-allowance boundaries, and zero-weight sensors; documented the workflow and output files.
- Affected files:
  - scripts/phase3a_us325.py
  - scripts/test_phase3a_us325.py
  - scripts/README.md
  - CHANGELOG.md
  - artifacts/phase3a_us325_control_results.csv
  - artifacts/phase3a_us325_control_cluster_size_summary.csv
  - artifacts/phase3a_us325_alpha_results.csv
  - artifacts/phase3a_us325_cluster_size_summary.csv
  - artifacts/phase3a_us325_event_snapshots.csv
  - artifacts/phase3a_us325_comparison_summary.json
  - artifacts/phase3a_us325_messages_vs_alpha.png
  - artifacts/phase3a_us325_synchronizations_vs_alpha.png
  - artifacts/phase3a_us325_clustering_vs_alpha.png
  - artifacts/phase3a_us325_communication_composition.png
- Rationale and impact:
  - Separates allowance-weighting effects from clustering effects without changing the validated Phase 2, FMIC/SMIC formulas, shared monitoring engine, or historical outputs. New experiment artifacts are isolated under the `phase3a_us325_` prefix.
- Validation:
  - `python -B -m unittest scripts.test_phase3a_us325 -q`: 9 focused tests passed.
  - The runner's combined US-3.25, Phase 2, Phase 3 history/monitoring, and US-3.24 equivalence regression command passed all 131 tests before the experiment.
  - `python -B -m scripts.phase3a_us325`: passed all three controls and all 38 clustered alpha runs. C0/C1/C2 totals were 9,159/8,964/8,962 messages and 467/457/457 root synchronizations; every configuration had zero false-safe and false-violated rows and reconciled messages.
  - At the prespecified alpha 0.10, FMIC/SMIC reproduced the historical baseline totals and sync counts (11,922/11,902 messages; 293/293 synchronizations). The exploratory in-sample tested-grid minima were 8,722 at alpha 0.65 for FMIC and 8,720 at alpha 0.65 for SMIC.
  - Both fresh-process alpha=0.10 replays passed; all 17 protected historical/prerequisite artifact hashes were unchanged. C0 retained its US-3.24 per-bucket equivalence result.

### Hardened US-3.24 equivalence diagnostics and provenance
- Summary:
  - Made comparison results schema-consistent on trace-length mismatches and added actionable diagnostics for synchronization-event timelines, singleton partitions, node/coordinator allowances, and nonzero peer traffic.
  - Added an absolute tolerance of `1e-12` for continuous comparison values while keeping protocol decisions, threshold states, synchronization flags, triggers, and message counts exact.
  - Restored Phase 3's established `math.fsum` global-mean calculation and added complete test-module hashes plus executed test count/result to validation provenance.
- Affected files:
  - scripts/phase3a_protocol_equivalence.py
  - scripts/test_phase3a_protocol_equivalence.py
  - scripts/build_phase3_temperature_clustering.ipynb
  - scripts/README.md
  - artifacts/phase3a_protocol_equivalence_summary.json (regenerated provenance and validation results)
  - artifacts/phase3a_protocol_equivalence_events.csv (regenerated; byte-identical)
  - CHANGELOG.md
- Rationale and impact:
  - Improves failure diagnosis and reproducibility without altering Phase 2 arithmetic, FMIC/SMIC moment formulas, clustering behavior, or communication accounting. Continuous rounding-level differences are tolerated only when all discrete decisions remain identical.
- Validation:
  - `python -B -m unittest scripts.test_phase3a_protocol_equivalence -q`: 13 tests passed, including trace truncation through the production runner, negative controls for partition/node/coordinator allowances/event timeline/peer traffic, and a check that continuous-value tolerance does not mask a state change.
  - `python -B -m unittest scripts.test_phase2_monitoring scripts.test_phase3_history scripts.test_phase3_monitoring -q`: 109 tests passed.
  - `python -B -m scripts.phase3a_protocol_equivalence`: production equivalence passed and its bundled regression run passed all 122 tests.
  - Production result: 19,984 buckets, 467 synchronizations, 753 trigger notifications, 9,159 messages for each implementation, zero Phase 3 peer transmissions, zero bucket mismatches, and zero false-safe/false-violated states. The accounting identity is `18 * 467 + 753 = 9,159`.
  - Replaying the former ordered-sum arithmetic to a temporary output directory produced the same US-3.24 event CSV SHA-256 (`ff4a89ecec934a96456eeefa5e154b580b6ddac2251ef2711250380f2d489fcf`) as restored `math.fsum`. The summary was regenerated to include the new runner/test hashes and actual test count; its recorded historical/protected artifact checks passed.

### Implemented US-3.24 Phase 2 / Phase 3 protocol equivalence gate
- Summary:
  - Added a reusable fixed-singleton/equal-allowance control around the current Phase 3 `FMICMonitor`; it pins and validates six singleton clusters at each synchronization, ignores moment/history values for control decisions, and reports alpha as not applicable.
  - Added a full-cohort runner that independently executes Phase 2 and Phase 3, compares every bucket's triggers, synchronization, references, allowances, root-known states, and mapped message categories, checks the independent root-state oracle and `18*S + L` ledger, and writes compact deterministic summary/event artifacts with provenance.
  - Added exact Phase 2 trace output as an opt-in while preserving the existing four-decimal default, plus synthetic lifecycle, boundary, ledger, negative-control, and fresh-process reproducibility tests.
- Affected files:
  - scripts/phase2_monitoring.py
  - scripts/test_phase2_monitoring.py
  - scripts/build_phase3_temperature_clustering.ipynb
  - scripts/phase3a_protocol_equivalence.py
  - scripts/test_phase3a_protocol_equivalence.py
  - scripts/README.md
  - artifacts/phase3a_protocol_equivalence_summary.json (generated)
  - artifacts/phase3a_protocol_equivalence_events.csv (generated)
  - artifacts/phase3a_phase2_two_sided_baseline.json (provenance refresh only)
  - CHANGELOG.md
- Rationale and impact:
  - Establishes a pass/fail no-clustering, equal-allowance reference before US-3.25; the production gate requires exact bucket-level parity, not merely matching totals.
  - Standard FMIC/SMIC algorithms and their historical outputs are not changed. The new decision trace is in-memory and opt-in; production equivalence outputs remain compact.
- Validation:
  - `python -B -m scripts.phase3a_protocol_equivalence`: passed the production gate and all 118 Phase 2/Phase 3 tests, including negative controls and two fresh-process full-cohort replays with byte-identical summary/event output.
  - `python -B -m scripts.phase2_monitoring`: passed the revised Phase 2 correctness/accounting gate. The revised baseline's provenance hash was refreshed; its 19,984-row event output and substantive results are unchanged.
  - Production equivalence: 19,984 buckets, 467 synchronizations, 753 sensor alerts, zero mismatches in all per-bucket comparisons, 9,159 messages per implementation, 1,999 true violations, zero false-safe/false-violated states, and zero Phase 3 peer transmissions. Each sensor's trigger count agrees.
  - Historical signed-margin Phase 2, FMIC/SMIC, US-3.21, and US-3.22 artifacts remained unchanged by SHA-256. Changed implementation syntax checks passed; Pylance reports no diagnostics in the equivalence runner or Phase 2 monitor. Existing timedelta deprecation warnings remain in the Phase 2 test module.

### Phase 3 protocol comparison instrumentation
- Summary:
  - Changed the Phase 3 global mean to Python's built-in `sum` over sorted sensor IDs, matching Phase 2's arithmetic expression and ordering.
  - Added opt-in `capture_decisions` instrumentation retaining compact per-bucket entry references, allowances, known state, triggering sensor IDs, synchronization outcome, post-sync state, and transmission counts in memory only.
  - Added regression tests and documented the rounding trade-off and trace behavior.
- Affected files:
  - scripts/build_phase3_temperature_clustering.ipynb
  - scripts/test_phase3_monitoring.py
  - scripts/README.md
  - CHANGELOG.md
- Rationale and impact:
  - Aligns Phase 3's mean calculation with Phase 2 for protocol-equivalence comparisons; floating-point results can still differ from `math.fsum` by Python version and input values, so boundary tests remain necessary.
  - Decision tracing is disabled by default and does not change standard saved FMIC/SMIC artifacts.
- Validation:
  - `python -B -m unittest scripts.test_phase3_monitoring scripts.test_phase2_monitoring -q`: 91 tests passed.
  - The edited notebook JSON and Phase 3 implementation cell compile successfully; Pylance reported no syntax errors in the Phase 3 test module.

### US-3.23 reproducibility and validation maintenance
- Summary:
  - Explicitly export matched Phase 2 event CSVs with LF line endings, retaining existing ordered columns/rows, values, precision, and actual-file SHA-256 calculation.
  - Reuse the matched synthetic fixture for an automated two-subprocess regression with isolated temporary roots, exact baseline/event byte comparisons, expected numerical/correctness/count checks, and protected-input/history checks.
  - Clarify consistency replay versus the independent offline root-state oracle and independently specified synthetic tests; document the targeted regression command and normalization-only hash change.
- Affected files:
  - scripts/phase2_monitoring.py
  - scripts/test_phase2_monitoring.py
  - scripts/README.md
  - README.md
  - artifacts/phase3a_phase2_two_sided_events.csv (generated)
  - artifacts/phase3a_phase2_two_sided_baseline.json (generated provenance)
  - CHANGELOG.md
- Rationale and impact:
  - Prevents platform-default CSV newlines from changing event hashes. The new production event bytes equal the previous bytes with only 468 CRLF endings replaced by LF.
  - Old event SHA-256: `881cbd6d225533c2194372a470d9bf66969ae74a4e6eabaf9f60dcf386114fea`.
  - New event SHA-256: `446d2e0b552ba603a0815e3275f5eba37513ac3298a63fb5129029dc3fba1d2e`.
  - No monitoring mathematics, synchronization, message accounting, configuration, or numerical results changed. Baseline provenance reflects the updated code/event hashes; historical Phase 2 and US-3.21/US-3.22 artifacts are unchanged.
- Validation:
  - `python -B -m unittest scripts.test_phase2_monitoring scripts.test_phase3_history scripts.test_phase3_monitoring -q`: 104 tests passed, including the new fresh-process regression and all existing Phase 2 tests.
  - One production matched replay retained A/C/D/E/F/G, 19,984 buckets, p90 22.428666649999997, 1,999 violations, zero false-safe/false-violated states, 467 synchronizations, 753 triggers, 2,802 each requests/responses/updates, and 9,159 messages. All non-provenance summary fields and 23 protected file hashes were unchanged.
  - Pylance syntax checks passed for both Python files.

### Implemented US-3.23 two-sided equal-allowance Phase 2 monitoring
- Summary:
  - Updated the existing shared Phase 2 engine to use absolute distance to the threshold, absolute local-deviation triggers, and retained root-known SAFE/VIOLATED state; removed negative-margin scheduling.
  - Added an independent offline two-sided root-state oracle and a locked matched-run CLI that writes a separately named revised baseline and compact synchronization events.
  - Migrated the Phase 2 notebook, metrics, dictionary, and validation to explicit allowance/root-state fields and separate legacy event diagnostics. General notebook output filenames now use `phase2_two_sided_*` to avoid overwriting historical files.
  - Added synthetic boundary, cooling/warming, zero-allowance, communication/oracle-control, historical-output-preservation, and matched-run input/provenance tests; documented policy, schema migration, commands, results, and remaining confounders.
- Affected files:
  - scripts/phase2_monitoring.py
  - scripts/test_phase2_monitoring.py
  - scripts/build_phase2_temperature_sensors.ipynb
  - scripts/README.md
  - Distributed_Monitoring_POC_Project_Plan.md
  - Phase3A_Pivot_Plan.md
  - artifacts/phase3a_phase2_two_sided_baseline.json (generated)
  - artifacts/phase3a_phase2_two_sided_events.csv (generated)
  - CHANGELOG.md
- Rationale and impact:
  - Repairs the threshold-policy comparability issue while preserving Phase 2's non-clustered equal allowances, initialization, availability/deferred synchronization, next-bucket reference activation, and actual-transmission accounting.
  - Revised matched run: 19,984 buckets, p90 22.428666649999997, 1,999 truly violated buckets, zero false-safe/false-violated states, 9,159 messages, and 467 synchronizations. Categories reconcile to 753 triggers plus 2,802 each of requests, responses, and updates.
  - The historical 38,087-message / 2,107-synchronization benchmark and all existing Phase 3 inputs, code, FMIC/SMIC artifacts, validation, and US-3.22 results/plots were preserved by hash. No Phase 3 denominator was replaced. Aggregate reductions are not a causal isolation of scheduling, clustering, moment weighting, or coordinator protocols.
- Validation:
  - `python -B -m unittest scripts.test_phase2_monitoring scripts.test_phase3_history scripts.test_phase3_monitoring -q`: 103 tests passed, including every Phase 2 notebook code cell on synthetic fixtures.
  - `python -B -m scripts.phase2_monitoring`: two fresh-process runs passed all correctness/input/accounting gates and produced byte-identical revised baseline and event files; protected historical hashes were unchanged.
  - Pylance syntax checks passed for the implementation and test module.

## 2026-11-03

### Completed US-3.22 alpha sensitivity and matched comparison
- Summary:
  - Parameterized the shared production runner with explicit alpha while retaining 0.10 as its default, and ran 19 fresh full-length FMIC and 19 fresh full-length SMIC simulations on the approved Phase 3A experiment.
  - Added 38-row results with per-run cohort, interval, threshold, correctness, message categories, cluster metrics, and provenance; consolidated synchronization events; a compact comparison summary; and three result-derived plots.
  - Documented initialization-inclusive cluster aggregation, updated Phase 3 usage and status plans, and added matplotlib as the plotting dependency.
- Affected files:
  - scripts/build_phase3_temperature_clustering.ipynb
  - scripts/test_phase3_monitoring.py
  - scripts/README.md
  - requirements.txt
  - Phase3A_Pivot_Plan.md
  - Distributed_Monitoring_POC_Project_Plan.md
  - artifacts/phase3a_alpha_results.csv
  - artifacts/phase3a_alpha_events.csv
  - artifacts/phase3a_comparison_summary.json
  - artifacts/phase3a_messages_vs_alpha.png
  - artifacts/phase3a_synchronizations_vs_alpha.png
  - artifacts/phase3a_clustering_vs_alpha.png
  - CHANGELOG.md
- Rationale and impact:
  - Completes the approved full-simulation alpha comparison without changing source-defined formulas or selecting configurations that fail correctness. All 38 runs use the locked cohort, interval, and full-precision P90; all have zero false-safe/false-violated states and reconciled messages. The 0.10 sweep reproduces the saved event fingerprints and baseline totals.
  - The final notebook path runs the sweep without invoking fixed-alpha output writers. During the first full-notebook validation, the then-present trailing SMIC call rewrote `artifacts/phase3a_smic_summary.json`; this call was removed before the final sweep. The current SMIC summary preserves the validated message/category metrics and event fingerprint, but its SHA-256 differs from its pre-task value; the final sweep preserved the current fixed-alpha artifacts by hash.
  - The minimum observed message total for both methods is at alpha 0.65 on this dataset and grid only (FMIC 8,722; SMIC 8,720); both sensitivity curves are irregular. This is not a universal or out-of-sample alpha recommendation.
- Validation:
  - `python -B -m unittest scripts.test_phase3_monitoring scripts.test_phase3_history scripts.test_phase2_monitoring -q` — 94 tests passed.
  - Executed the full production notebook; verified 38 unique runs, the approved 19,984-bucket inputs and threshold, zero correctness failures, category reconciliation, initialization-inclusive cluster metrics, all three plots, and unchanged final-sweep protected hashes.

### Completed US-3.21 synthetic validation gate
- Summary:
  - Added an explicit sender/recipient/purpose/category transmission ledger and a singleton-cluster protocol case for both FMIC and SMIC.
  - Strengthened the false-safe negative control to assert that the summary reports failure, and checked root-known state against independent truth at every FMIC synthetic observation.
  - Added a compact validation report with source references, commands, synthetic coverage, production replay results, and remaining limitations.
  - Updated the Pivot Plan and Project Plan implementation status to record US-3.21 as complete and US-3.22 as pending.
- Affected files:
  - scripts/test_phase3_monitoring.py
  - artifacts/phase3a_validation_summary.json
  - Phase3A_Pivot_Plan.md
  - Distributed_Monitoring_POC_Project_Plan.md
  - CHANGELOG.md
- Rationale and impact:
  - Closes US-3.21 validation gaps without changing either monitoring algorithm or production output schema.
  - The approved experiment remains the 19,984-bucket stable cohort; isolated full-data FMIC and SMIC replays matched their saved event and summary artifacts byte-for-byte, so existing production outputs were unchanged.
- Validation:
  - `python -B -m unittest scripts.test_phase3_monitoring scripts.test_phase3_history scripts.test_phase2_monitoring -q` — 91 tests passed.
  - The rendered source PDF was checked at printed p.10/PDF p.14 for the moment/weight definitions and Appendix 1, printed p.22/PDF p.26, for the central second-moment indexing and divisor.
  - Both isolated production replays processed 19,984 buckets, agreed on 1,999 violated buckets, passed both mismatch counts, and reconciled messages: FMIC 11,922 messages / 293 synchronizations; SMIC 11,902 / 293.

### Implemented and validated SMIC through the shared Phase 3A notebook engine
- Summary:
  - Added persistent discounted central second-moment state using the original PDF Appendix 1 stable recurrence, preserving the existing first-moment update.
  - Documented that the source uses an unnormalized squared-deviation sum, with no m or m-1 divisor; Appendix 1 resolves section 1.4's i=0 indexing discrepancy to i=1..m.
  - Added SMIC first-plus-second-moment weights and shared normalized node/coordinator allocation, explicit early-observation and project zero-weight handling.
  - Generalized the existing monitoring lifecycle and production runner to select FMIC or SMIC without duplicating triggering, clustering, escalation, communication accounting, or two-sided correctness checks.
  - Normal notebook execution now runs both methods independently at configured alpha 0.10, producing separate compact SMIC events/summary without overwriting FMIC or Phase 2 artifacts.
  - Added hand-derived second-moment/weight checks, explicit-vector and numerical-state checks, inherited SMIC protocol/failure tests, same-allocation equivalence, a pre-refactor FMIC fingerprint, and dual-run output-preservation/provenance tests.
- Affected files:
  - scripts/build_phase3_temperature_clustering.ipynb
  - scripts/test_phase3_monitoring.py
  - scripts/README.md
  - CHANGELOG.md
  - artifacts/phase3a_smic_events.csv (generated)
  - artifacts/phase3a_smic_summary.json (generated)
- Rationale and impact:
  - Implements US-3.20 with one shared monitoring architecture and the source-defined SMIC weighting, not a conventional variance estimator or a separate synchronization schedule.
  - Moment/weight payloads accompany existing root-sync responses and updates under the established transmission-counting policy; no additional exchanges are required.
  - Full SMIC run: 19,984 buckets, 1,999 centralized violated buckets, zero false-safe/false-violated, 11,902 messages, 293 synchronizations, 3,514 coordinator checks, 420 escalations.
  - Preliminary savings: 68.750492% versus the 38,087-message matched Phase 2 baseline; 20 fewer messages than unchanged FMIC. No tuning or final comparative claim.
- Validation:
  - All notebook cells executed successfully for both methods; protected FMIC outputs, Phase 2 baseline, aligned Phase 1 input/statistics/script, and config remained byte-for-byte unchanged.
  - All 87 focused FMIC/SMIC/history/Phase 2 tests passed, including the pre-refactor FMIC protocol fingerprint.
  - Independent raw-input replay verified all SMIC synchronization decisions, centralized states, communication categories/totals, and event moment/weight/allowance snapshots; the maximum central-sum discrepancy was 2.274e-13.
  - Each method had two synchronization timestamps absent from the other's schedule, despite equal synchronization counts.

### Documented and hand-validated the source first-moment recurrence
- Summary:
  - Added a direct chapter PDF reference (section 1.4, printed p.10/PDF p.14), explicit discounted vector set, algebraic sum recurrence, and observation-count divisor beside the notebook implementation.
  - Added a worked two-sensor, three-observation table; documented raw readings versus reference-relative clustering history, post-initialization sampling, and persistence across synchronization.
  - Strengthened the existing moment-recurrence test to verify hand-listed discounted vectors, intermediate sums, observation counts, and signed arithmetic means, independently of allocation formulas.
- Affected files:
  - scripts/build_phase3_temperature_clustering.ipynb
  - scripts/test_phase3_monitoring.py
  - scripts/README.md
  - CHANGELOG.md
- Rationale and impact:
  - Preserves the source-to-code derivation needed for FMIC interpretation and future SMIC work. Explicitly distinguishes arithmetic mean of discounted observations from an EMA and from signed clustering history.
  - Documentation and regression coverage only; numerical calculations, monitoring, and output schemas are unchanged.
- Validation:
  - Verified the discounted vector-set definition directly against the original PDF page 14.
  - All 35 focused FMIC/history/clustering tests passed, including the expanded hand-calculated recurrence and existing synchronization-persistence tests.
  - Executable-AST comparison confirmed only documentation changed in the notebook for this request, preserving the previously requested symmetric-status fix.

### Made FMIC summary correctness validation symmetric
- Summary:
  - Requires both `false_safe_count == 0` and `false_violated_count == 0` before reporting `correctness_status = passed`.
  - Adds regression coverage for all four zero/nonzero count combinations and a synthetic missed violated-to-safe transition.
- Affected files:
  - scripts/build_phase3_temperature_clustering.ipynb
  - scripts/test_phase3_monitoring.py
  - scripts/README.md
  - CHANGELOG.md
- Rationale and impact:
  - Makes the summary decision reflect the approved two-sided threshold-monitoring policy. Monitoring, message accounting, and the existing immediate false-safe exception are unchanged.
  - The current production run has zero mismatches in both directions, so its status and result values are expected to remain unchanged.
- Validation:
  - Both new regressions reproduced the prior false pass before the fix; all 35 focused FMIC/history/clustering tests now pass.
  - Every notebook code cell compiled and the full 19,984-bucket run completed successfully with both mismatch counts zero and status `passed`.
  - SHA-256 checks confirmed the regenerated FMIC summary/events and matched Phase 2 baseline remain byte-for-byte unchanged.

### Consolidated Phase 3 core into one notebook
- Summary:
  - Moved the unchanged clustering/history/input-validation and FMIC allocation/monitoring implementations into labeled, tagged notebook cells.
  - Kept automated tests separate and updated FMIC tests to load the tagged notebook definitions, using the existing history-test loader.
  - Removed the two redundant Phase 3 implementation modules; retained shared functions inside the notebook for future SMIC reuse.
- Affected files:
  - scripts/build_phase3_temperature_clustering.ipynb
  - scripts/phase3_clustering.py (removed)
  - scripts/phase3_monitoring.py (removed)
  - scripts/test_phase3_monitoring.py
  - scripts/README.md
  - artifacts/README.md
  - CHANGELOG.md
- Rationale and impact:
  - Makes the complete Phase 3 implementation reviewable in one notebook without changing the algorithms, transmission accounting, experiment contract, or output schemas.
  - Tests remain independently runnable; no alternative or duplicate core implementation is retained.
- Validation:
  - All 88 focused Phase 1/QC/Phase 2/Phase 3/FMIC regression tests passed, including a new assertion that the core definitions are present in notebook cells and the removed modules are not required.
  - Every notebook code cell compiled and executed successfully in a fresh kernel after deleting the external modules.
  - SHA-256 comparisons confirmed FMIC events, FMIC summary, and the matched Phase 2 baseline are byte-for-byte unchanged: 11,922 messages, 293 root synchronizations, and zero false-safe/false-violated buckets.
  - Execution produced only the previously observed non-blocking Windows Jupyter event-loop warning.

### Implemented and validated end-to-end Phase 3A FMIC (US-3.19)
- Summary:
  - Mechanically extracted the existing history, normalization, greedy clustering, and stable-input validation definitions into an importable shared module, preserving their mathematics and legacy helper regression behavior.
  - Implemented independent FMIC initialization, fixed-reference node monitoring, signed coordinator cancellation, escalation, root synchronization/reclustering, and persistent history.
  - Verified the first-moment definition against the authoritative chapter, printed p.10/PDF p.14: arithmetic mean of age-discounted raw observations, kept separate from clustering history. Implements first-moment-only weights, node/coordinator allowances, and the explicitly labeled project all-zero-weight fallback.
  - Implements the approved separate-root transmission model, absolute distance-to-boundary monitoring on both sides, inclusive trigger boundaries, deterministic simultaneous-trigger handling, and blocking false-safe validation.
  - Wired normal notebook execution to FMIC alpha 0.10 without replaying Phase 2 or overwriting its matched baseline; exports only compact FMIC events and summary.
- Affected files:
  - scripts/phase3_clustering.py
  - scripts/phase3_monitoring.py
  - scripts/test_phase3_monitoring.py
  - scripts/build_phase3_temperature_clustering.ipynb
  - scripts/README.md
  - artifacts/README.md
  - artifacts/phase3a_fmic_events.csv (generated)
  - artifacts/phase3a_fmic_summary.json (generated)
  - CHANGELOG.md
- Rationale and impact:
  - Completes FMIC's own monitoring lifecycle while retaining the fixed cohort, interval, threshold, validated clustering foundation, and matched Phase 2 comparison.
  - The root retains the last synchronized threshold state; centralized truth validates each bucket but never drives communication. This is explicitly distinct from Phase 2's same-row-resynchronization diagnostic definition.
  - No Phase 1/2 changes, SMIC, alpha sweep/tuning, dynamic availability, or exhaustive production traces are introduced.
- Validation and results:
  - Formula, allowance reconciliation, zero-weight fallback, boundary, cancellation, simultaneous-trigger, history/moment persistence, communication hand-count, randomized centralized-truth, and production-integration tests pass alongside the existing Phase 2/3 regressions.
  - Full notebook execution completed successfully for all 19,984 buckets; all 1,999 centralized violations were recognized with zero false-safe and zero false-violated buckets.
  - FMIC used 11,922 messages: node triggers 2,564; cluster requests 1,832; cluster responses 1,832; coordinator escalations 420; root requests/responses/updates 1,758 each. Categories reconcile exactly.
  - Recorded 293 root synchronizations (one initialization, 292 monitoring-triggered), 3,522 coordinator checks, and 420 escalations; multiple same-bucket escalations share one root synchronization.
  - Message reduction is 68.697981% versus the 38,087-message matched Phase 2 baseline, and 90.057046% versus 119,904 centralized sensor transmissions. No general superiority claim is made.
  - Independent replay of every raw-input bucket verified exported histories, moments, weights, allowances, runtime event schedule, seven transmission categories, and root-known states without invoking the FMIC monitor.
  - SHA-256 checks confirmed aligned Phase 1 input, statistics, experiment config, matched Phase 2 baseline, and historical clustering-event artifact remain unchanged.
  - All 87 focused Phase 1/QC/Phase 2/Phase 3/FMIC regression tests passed. New modules passed syntax checks; FMIC runtime/tests have no Pylance diagnostics. Full notebook execution emitted only a non-blocking Windows Jupyter event-loop warning.
  - Final outputs are compact: 293 event rows (435,851 bytes) and a 3,129-byte summary JSON; no full sensor-minute trace was generated.

### Excluded the temperature aggregate from Phase 1 source discovery
- Summary:
  - Explicitly excludes `temperature_raw.csv` by case-insensitive filename before applying the source-file limit, preserving timestamped source ordering and all transformation/deduplication logic.
  - Adds `excluded_non_source_csv_filenames` to the production QC CSV as a JSON array, run JSON as a list, and decisions log.
  - Adds discovery, first-wins regression, and end-to-end audit-metadata tests; documents the distinction from the standalone all-files QC investigation.
- Affected files:
  - scripts/build_phase1_temperature.py
  - scripts/test_phase1_source_discovery.py
  - scripts/README.md
  - artifacts/README.md
  - artifacts/raw_index.csv (regenerated)
  - artifacts/aligned_phase1_temperature.csv (regenerated)
  - artifacts/transformation_qc_report.csv (regenerated)
  - artifacts/phase1_average_statistics.csv (regenerated)
  - artifacts/transformation_decisions.md (appended)
  - config/phase3a_experiment_config.json (normal Phase 1 threshold refresh)
  - artifacts/phase1_duplicate_qc/phase1_source_exclusion_comparison.json (generated)
  - CHANGELOG.md
- Rationale and impact:
  - Removes the known non-source aggregate from transformation input while retaining the timestamped raw sources and unchanged first-observation deduplication.
  - Excluded filenames are recorded only when present and are not confused with files omitted by a smoke-test limit.
- Validation and results:
  - `python -B scripts/build_phase1_temperature.py --enforce-gates` completed with exit code 0; all four quality gates passed.
  - Processed 3,471 timestamped sources: 9,909,343 temperature rows before deduplication, 9,899,253 unique temperature keys, and 10,090 excess duplicate rows. The duplicate-row rate is 0.101823% versus the 0.5% maximum.
  - QC CSV, stdout JSON, and the appended decisions log record `["temperature_raw.csv"]` as the excluded non-source filenames.
  - The regenerated aligned CSV has exactly the same SHA-256 as the preserved previous output (`07f4eb49687e7f50e8d9179914e1f7b8a93ef83cef99b43cf9f073881051cb9b`): 218,148 rows, unchanged schema, zero timestamps added/removed/relabelled, zero availability changes, and zero differences across 1,626,090 populated sensor readings and 218,148 all-device averages. Maximum temperature difference is 0 degrees C.
  - Verified unique ordered minute-aligned epochs and timestamp consistency, finite observed sensor readings, availability/count/coverage/confidence invariants, average consistency, and the full 19,984-row Phase 3A input contract. Both statistics series and the authoritative Phase 3A P90 (22.428666649999997) are unchanged; downstream Phase 2/3 production outputs were not regenerated.
  - All 24 focused source-discovery/QC/Phase 1 statistics tests and 47 downstream Phase 2/3 regression tests passed (71 total). Updated Python files passed syntax checks; no new Pylance errors were found (the existing unused staleness-policy parameter hint remains untouched).

### Added aggregate-exclusion duplicate QC and exact source reconciliation
- Summary:
  - Added opt-in `--exclude-temperature-raw` mode to the standalone QC script, preserving its original all-files behavior and reports.
  - Recomputes all duplicate statistics after excluding the aggregate; reports strict spread exceedances at 1e-9, 1e-6, 0.001, 0.01, 0.05, and 0.1 degrees C plus non-overlapping bins.
  - Reads the existing configured gate and reports strict-below status separately from Phase 1's rounded-rate, inclusive gate rule.
  - Compares aggregate and timestamped-source full-record multisets with exact parsed values and multiplicities, exports all unmatched record groups in both directions, and reports invalid/non-finite observations explicitly.
- Affected files:
  - scripts/qc_phase1_duplicate_keys.py
  - scripts/test_qc_phase1_duplicate_keys.py
  - scripts/README.md
  - artifacts/README.md
  - artifacts/phase1_duplicate_qc/excluding_temperature_raw/qc_phase1_duplicate_summary.json (generated)
  - artifacts/phase1_duplicate_qc/excluding_temperature_raw/qc_phase1_duplicate_conflicts.csv (generated)
  - artifacts/phase1_duplicate_qc/excluding_temperature_raw/qc_phase1_unmatched_records.csv (generated)
  - CHANGELOG.md
- Rationale and impact:
  - Separates aggregate/source overlap from original-source duplicates without changing Phase 1, its inputs, its configuration, or pipeline outputs.
  - Exact value matching is intentionally not replaced by tolerance matching; equal row totals or key coverage do not establish multiset equivalence.
  - Exclusion-mode outputs are isolated beneath the already-ignored QC artifacts subfolder; the exhaustive unmatched CSV may be large.
- Validation and results:
  - All 20 standalone QC and existing Phase 1 statistics tests passed, including strict threshold boundaries, inclusive gate rounding, exact float precision, multiplicity mismatches, bidirectional exports, non-finite/invalid rows, CLI isolation, and original-mode regression coverage.
  - Both updated Python files passed syntax and Pylance diagnostic checks.
  - The full run excluded the aggregate and scanned 3,471 timestamped sources: 9,909,343 temperature rows, 9,899,253 unique keys, 10,090 excess duplicate rows, and 9,683 duplicated keys. Multiplicities are 2: 9,293 keys; 3: 373; 4: 17.
  - The duplicate-row rate is 0.10182309765642385% (Phase 1 rounded rate 0.101823%), strictly below 0.5% and passing the existing inclusive QC gate.
  - Identical-value duplicate keys: 4,963 (51.254776%); conflicting keys: 4,720 (48.745224%). Maximum spread is 0.44000244140625 degrees C; mean is 0.011461862515594966 degrees C.
  - Strict conflicting-spread exceedances are >1e-9: 4,720; >1e-6: 4,719; >0.001: 4,719; >0.01: 4,187; >0.05: 3; >0.1: 2.
  - Exact full-record multisets are not equal: 9,118,190 occurrences matched; 791,153 aggregate occurrences and 791,153 timestamped-source occurrences are unmatched. Each direction contains 790,814 unmatched record groups, exported exhaustively in a 204,090,611-byte CSV. Neither population contains invalid or non-finite temperature records.
  - All 1,581,628 unmatched CSV groups reconcile with the summary. Across 790,797 affected keys, per-key occurrence totals agree in both directions; exact values still do not all match.
  - Verified every report count/multiplicity/spread/gate invariant, all 100 conflicting examples, and 264 original raw records covering example provenance and systematic unmatched samples.
  - SHA-256 checks confirmed Phase 1, its configuration, existing pipeline artifacts, and the previous all-files QC reports are byte-for-byte unchanged.

### Added standalone raw Phase 1 duplicate-key investigation
- Summary:
  - Added a stdlib-only, bounded-memory SQLite audit of raw temperature keys with Phase 1-compatible parsing, validation, and first-occurrence ordering.
  - Reports counts, multiplicities, exact value agreement/conflicts, conflicting value spreads, source-file provenance, and cross-file versus within-file attribution.
  - Generates a compact conflicting-example CSV and JSON summary under `artifacts/phase1_duplicate_qc/`; added focused tests and usage documentation.
- Affected files:
  - scripts/qc_phase1_duplicate_keys.py
  - scripts/test_qc_phase1_duplicate_keys.py
  - scripts/README.md
  - artifacts/README.md
  - artifacts/phase1_duplicate_qc/qc_phase1_duplicate_conflicts.csv (generated)
  - artifacts/phase1_duplicate_qc/qc_phase1_duplicate_summary.json (generated)
  - .gitignore
  - CHANGELOG.md
- Rationale and impact:
  - Investigates whether source-file overlap explains Phase 1 duplicates without changing `build_phase1_temperature.py`, its deduplication behavior, or existing pipeline outputs.
  - Undefined percentages/spreads are explicit nulls; non-finite values are audited rather than silently discarded.
  - The new generated-output subfolder is ignored, consistent with the source-only repository policy.
- Validation:
  - All 12 focused QC/CLI and existing Phase 1 statistics tests passed; both new Python files passed syntax and editor diagnostic checks.
  - Scanned all 3,472 sources and 89,184,087 raw rows. The 19,818,686 temperature rows, 9,899,253 unique keys, and 9,919,433 excess duplicate rows reconcile exactly with the existing Phase 1 QC artifact.
  - Found 9,104,324 identical-value duplicate keys (91.969808%) and 794,929 conflicting keys (8.030192%). Maximum conflicting-key spread is 0.44000244140625; mean is approximately 0.0000680563812320563. Of the conflicting keys, 790,209 have spreads at most 1e-9.
  - All duplicate keys span files; 99.796601% of excess rows are attributable to cross-file repetition. The aggregate `temperature_raw.csv` participates in every duplicated key.
  - Validated report reconciliation and example ordering. Re-exported all 100 examples from their 430 original observations through the corrected production analyzer after detecting SQLite JSON float rounding; verified exact float provenance and unchanged non-provenance fields.
  - SHA-256 checks confirmed the Phase 1 script, configuration, and existing pipeline CSV/decision artifacts are byte-for-byte unchanged.

## 2026-11-02

### Simplified Phase 3 execution for the approved Phase 3A cohort
- Summary:
  - Replaced the Phase 3 production execution path with a fixed A/C/D/E/F/G cohort over the inclusive 19,984-bucket interval from 2022-02-24 18:50 UTC through 2022-03-10 15:53 UTC.
  - Added strict Phase 3A validation for the exact row count, inclusive endpoints, consecutive 60-second timestamps and epochs, and finite readings for all cohort sensors. Invalid inputs now fail rather than invoke availability or re-entry behavior.
  - Preserved the existing Phase 2 all-devices observed P90 threshold, synchronization timing, signed persistent history, normalization, all-zero fallback, and source-aligned clustering math.
  - Set normal Phase 3A production execution to baseline alpha 0.10, producing one compact selected-result row per clustering event. Retained the full 19-value alpha sweep as an explicit tuning option.
  - Removed the legacy availability-aware `SensorHistoryTracker` and its departure, re-entry, missing-observation, and zero-observation tests from the Phase 3A implementation path. The stable-cohort history recurrence and source-aligned clustering math remain unchanged.
  - Removed the generated sensor-by-minute history trace; internal greedy-search calculations remain available to focused tests.
  - Added deterministic coordinator labels using the lexicographically greatest member, and documented the convention.
  - Added focused Phase 3A tests for the one-alpha production output, opt-in sweep, fixed-cohort history behavior, and timestamp/value validation; updated the script README.
- Affected files:
  - scripts/build_phase3_temperature_clustering.ipynb
  - scripts/test_phase3_history.py
  - scripts/README.md
  - artifacts/phase3_sensor_history_events.csv (regenerated)
  - artifacts/phase3_sensor_history_trace.csv (removed from normal production output)
  - CHANGELOG.md
- Rationale and impact:
  - Matches the approved stable-cohort Phase 3A assumptions, avoids runtime availability branches and multi-gigabyte audit exports, and keeps the selected mathematical results reproducible from the aligned input, configuration, and tests. The event CSV schema and contents are intentionally compacted; the legacy per-sensor-per-minute trace is no longer produced.
- Validation:
  - All notebook code cells completed successfully against the 218,148-row Phase 1 input; Phase 3A validated the 19,984-bucket interval and used the existing P90 threshold of 24.343381.
  - `python -B -m unittest scripts.test_phase3_history scripts.test_phase2_monitoring -q` passed all 44 Phase 3A and Phase 2 regression tests.
  - Verified the production artifact contains exactly 33 rows, one alpha=0.10 result per clustering event, with complete A/C/D/E/F/G history and partition coverage, coordinator assignments, and no sensor-by-minute history trace. The CSV is 20,212 bytes; tests also verify the explicit full-sweep option retains all 19 alpha values.
  - Notebook emitted one non-blocking pandas warning that rounding has no effect on datetime columns; execution completed successfully.

### Established the Phase 3A stable input contract for US-3.17
- Summary:
  - Added `config/phase3a_experiment_config.json` as the authoritative source for the aligned input, fixed cohort, inclusive interval, expected bucket count, sampling interval, baseline alpha, boundary convention, and planned threshold series. The cohort-specific P90 remains null/pending; the historical all-devices P90 is identified as temporary development-only.
  - Wired the notebook to load the input/statistics paths and temporary threshold source from the config, preserve original input order, and validate config plus stable-cohort data before monitoring or clustering.
  - Added explicit rejection for cohort drift, missing columns/readings, non-finite values, incorrect row count/endpoints, duplicate or out-of-order timestamps, timestamp gaps, and epoch/timestamp mismatch. Added a concise validation summary before invoking the in-memory Phase 2 monitor for synchronization timing; no separate Phase 2 comparison run is produced.
  - Expanded tests for the config contract and required valid/invalid input cases; documented the config and validation behavior in the script README.
- Affected files:
  - config/phase3a_experiment_config.json
  - scripts/build_phase3_temperature_clustering.ipynb
  - scripts/test_phase3_history.py
  - scripts/README.md
  - artifacts/phase3_sensor_history_events.csv (regenerated)
  - CHANGELOG.md
- Rationale and impact:
  - Makes the approved Phase 3A population explicit and prevents silent repair or cohort drift before synchronization and clustering. The existing in-memory Phase 2 synchronization timing remains in use as approved; the authoritative Phase 3A threshold is deferred to the next story.
- Validation:
  - Notebook Stage 1 and Stage 5 executed successfully; validation reported 19,984 rows, the approved endpoints and cohort, zero missing readings, and zero timestamp gaps.
  - `python -B -m unittest scripts.test_phase3_history scripts.test_phase2_monitoring -q` passed all 45 tests.
  - Verified 33 output rows, one per clustering event at alpha 0.10, with temporary threshold metadata and no history trace. Changed-file whitespace checks passed apart from a harmless notebook line-ending notice.

## 2026-11-03

### Calculated the Phase 3A P90 and generated the matched Phase 2 baseline
- Summary:
  - Extended the existing Phase 1 production workflow to calculate the mean of exactly A/C/D/E/F/G for every validated Phase 3A bucket and append the `phase3a_stable_cohort` statistics row using the existing linear-interpolation percentile convention. P90 is stored at full precision; the historical all-device statistics row is preserved.
  - Updated `phase3a_experiment_config.json` with the authoritative P90 `22.428666649999997`, statistic, status, and Phase 1 script/artifact provenance. The Phase 3 notebook now reads the Phase 3A row with round-trip float parsing and rejects any config/statistics mismatch.
  - Reused the existing Phase 2 monitor on the exact Phase 3A input and threshold. Added the compact `phase3a_phase2_baseline.json` with communication categories, resynchronizations, membership checks, evaluated bucket count, and centralized transmission reference.
  - Updated Phase 3 event output to record the authoritative threshold, refreshed US-3.18 documentation, and added round-trip precision and matched-baseline checks.
- Affected files:
  - scripts/build_phase1_temperature.py
  - scripts/build_phase3_temperature_clustering.ipynb
  - scripts/test_phase1_phase3a_statistics.py
  - scripts/test_phase3_history.py
  - scripts/README.md
  - artifacts/README.md
  - config/phase3a_experiment_config.json
  - artifacts/phase1_average_statistics.csv
  - artifacts/phase3_sensor_history_events.csv (regenerated)
  - artifacts/phase3a_phase2_baseline.json (generated)
  - CHANGELOG.md
- Rationale and impact:
  - Establishes one authoritative Phase 3A threshold and a matched Phase 2 result for later FMIC/SMIC comparisons, without changing Phase 2 monitoring logic or writing a duplicate large row trace.
- Validation:
  - Phase 1 generated exactly 19,984 Phase 3A averages; P90 is `22.428666649999997`, consistent with the planning estimate. The existing all-device row remains `24.343381`.
  - Phase 3 notebook completed successfully: 19,984 buckets, zero missing readings/gaps, 2,107 compact event rows, and a matched baseline with 2,107 resynchronizations, zero membership changes, six observed sensors on every row, and 38,087 total messages. Category totals reconcile; centralized reference is 119,904 transmissions.
  - `python -B -m unittest scripts.test_phase1_phase3a_statistics scripts.test_phase3_history scripts.test_phase2_monitoring -q` passed all 51 tests.
  - The Phase 1 command with `--enforce-gates` returned nonzero because the pre-existing duplicate-key QC rate is 50.050912% versus its 0.5% limit. The other Phase 1 gates passed, and the Phase 3A statistics/config outputs were generated. No Phase 1 gate logic was changed for this story.

## 2026-11-01

### Consolidated the Phase 3 review sample to a single file
- Summary:
  - At user request, removed `phase3_alpha_summary_sampled_events.csv`, `phase3_trace_sample.csv`, and `README.md` from `artifacts/phase3_review_sample/`.
  - The review sample is now the single file `artifacts/phase3_review_sample/phase3_events_sample.csv` (62 MB): 353 full-fidelity event rows (first 20, every 100th, last 20 of the 31,364 synchronization events) with the complete `alpha_clustering_evaluations` JSON preserved.
- Affected files:
  - artifacts/phase3_review_sample/phase3_alpha_summary_sampled_events.csv (deleted)
  - artifacts/phase3_review_sample/phase3_trace_sample.csv (deleted)
  - artifacts/phase3_review_sample/README.md (deleted)
  - CHANGELOG.md
- Rationale and impact:
  - The user asked for one review file; the extra extracts were unnecessary. The full Phase 3 outputs remain untouched, so the removed extracts can be regenerated if needed.
- Validation:
  - Confirmed the folder now contains only `phase3_events_sample.csv` at 62 MB.

## 2026-11-01

### Created a sub-100MB Phase 3 review sample
- Summary:
  - Added `artifacts/phase3_review_sample/` (about 78 MB total) extracted from the full Phase 3 outputs for human review.
  - `phase3_events_sample.csv` (65 MB): 353 full-fidelity event rows, stratified as the first 20 events, every 100th event, and the last 20 events, with the complete `alpha_clustering_evaluations` JSON preserved.
  - `phase3_alpha_summary_sampled_events.csv` (0.9 MB): 6,707 flattened rows (353 events x 19 alphas) with cluster count, partition quality, selected candidate index, fallback flags, and compact selected partitions.
  - `phase3_trace_sample.csv` (12 MB): 83,288 per-sensor audit rows covering the complete first week plus every sampled event's bucket.
  - Added a README in the sample folder documenting selection criteria and column provenance.
- Affected files:
  - artifacts/phase3_review_sample/phase3_events_sample.csv (new, generated)
  - artifacts/phase3_review_sample/phase3_alpha_summary_sampled_events.csv (new, generated)
  - artifacts/phase3_review_sample/phase3_trace_sample.csv (new, generated)
  - artifacts/phase3_review_sample/README.md (new)
  - CHANGELOG.md
- Rationale and impact:
  - The full events file (5.59 GB) is impractical to open for review; the sample keeps exact original row content (no rounding or recomputation) while staying under the requested 100 MB. No pipeline code, notebooks, or configuration were modified, and the full outputs are untouched.
- Validation:
  - Verified the summary covers 353 events x 19 alphas with synchronization IDs spanning 1 to 31364, the trace sample contains 8 sensors across 10,411 buckets, and all three CSVs parse cleanly with pandas.

## 2026-11-01

### Executed the Phase 3 clustering notebook end-to-end on the full dataset
- Summary:
  - Ran all eight code cells of `scripts/build_phase3_temperature_clustering.ipynb` against the full 218,148-row Phase 1/2 dataset using the repository virtual environment.
  - Generated the first full-data Phase 3 outputs: `artifacts/phase3_sensor_history_events.csv` (31,364 synchronization-event snapshots with per-event normalization and 19-alpha clustering evaluations) and `artifacts/phase3_sensor_history_trace.csv` (1,745,184 per-sensor history-audit rows).
  - The run also deterministically regenerated the Phase 2 outputs (`phase2_temperature_sensors.csv`, `phase2_temperature_metrics.json`, `phase2_data_dictionary.csv`, `phase2_sensor_reduction_analysis.csv`) through the notebook's integrated Phase 2 validation stages; no tracked files changed.
- Affected files:
  - artifacts/phase3_sensor_history_events.csv (new, generated)
  - artifacts/phase3_sensor_history_trace.csv (new, generated)
  - artifacts/phase2_temperature_sensors.csv (regenerated, unchanged behavior)
  - artifacts/phase2_temperature_metrics.json (regenerated, unchanged behavior)
  - artifacts/phase2_data_dictionary.csv (regenerated, unchanged behavior)
  - artifacts/phase2_sensor_reduction_analysis.csv (regenerated, unchanged behavior)
  - CHANGELOG.md
- Rationale and impact:
  - Makes the US-3.2 through US-3.4 implementation reviewable on real data: spot checks confirmed the initialization event records the zero-history singleton fallback, and later events record non-trivial partitions (e.g., at synchronization 1000, alpha 0.05 selects {A,H}, {B,D,G}, {C,E}, {F}, with finer partitions at higher alpha). No notebook, script, or configuration code was modified.
- Validation:
  - `python -B -m unittest scripts.test_phase3_history scripts.test_phase2_monitoring -q` passed all 60 tests (test saves are mocked and do not touch the generated artifacts).
  - Notebook run completed with exit code 0 and passed its integrated Phase 2 validation gate; output CSV headers and sample rows verified.

## 2026-10-29

### Implemented US-3.4 partition quality and greedy merging
- Summary:
  - Added scalar cluster/partition quality and deterministic greedy merging inside the existing Phase 3 notebook.
  - Retained all candidate partitions through two clusters, scored partners by merged-cluster quality, and selected the earliest minimum-quality candidate using the approved tie rules.
  - Preserved empty deferral and all-zero singleton fallback; added explicit singleton/pair behavior and input validation.
  - Extended the existing event CSV with separate alpha evaluations, candidate qualities, partner scores, merge decisions, and final assignments linked to one shared normalization snapshot.
  - Extended the existing test harness and updated story implementation notes, run documentation, and the project plan. No new source or output files were introduced.
- Affected files:
  - scripts/build_phase3_temperature_clustering.ipynb
  - scripts/test_phase3_history.py
  - Phase_3_User_Stories.md
  - scripts/README.md
  - Distributed_Monitoring_POC_Project_Plan.md
  - CHANGELOG.md
- Rationale and impact:
  - Implements auditable source-aligned partition construction for every alpha while preserving raw history and Phase 2 behavior. FMIC/SMIC allowances, coordinator/runtime activation, and communication comparisons remain later work.
- Validation:
  - `python -B -m unittest scripts.test_phase3_history scripts.test_phase2_monitoring -q` passed all 60 tests, including the eight-sensor alpha sweep and near-equal-score decisions.
  - Notebook JSON and all eight Python cells parsed successfully; `git diff --check` passed.

## 2026-10-28

### Implemented scalar normalization for US-3.3
- Summary:
  - Added scalar history normalization to the existing Phase 3 notebook, restricted to selected-cohort sensors that are online with valid observations at a completed synchronization.
  - Added explicit no-eligible-sensors deferral and a nonempty all-zero-history case that records one singleton per eligible sensor as a no-information fallback without running merges.
  - Enriched the existing synchronization-event output with event-linked normalization snapshots, and created in-memory inputs for the full alpha sweep that share the same immutable snapshot.
  - Added tests for signed normalization, offline exclusion, tied maxima, empty/all-zero cases, raw-history preservation, and shared alpha inputs.
  - Clarified US-3.3, the project plan, and the scripts README. No new files or output artifacts were added.
- Affected files:
  - scripts/build_phase3_temperature_clustering.ipynb
  - scripts/test_phase3_history.py
  - scripts/README.md
  - Phase_3_User_Stories.md
  - Distributed_Monitoring_POC_Project_Plan.md
  - CHANGELOG.md
- Rationale and impact:
  - Makes eligibility and the zero-history behavior explicit, and ensures the alpha sweep starts from one consistent event normalization. Alpha-specific clustering results remain for the later clustering stories.
- Validation:
  - `python -m unittest scripts.test_phase3_history scripts.test_phase2_monitoring -v` passed all 49 tests.
  - Notebook JSON/Python syntax validation and `git diff --check` passed.

## 2026-10-28

### Tidied US-3.3 formatting
- Summary:
  - Streamlined US-3.3's mathematical layout by keeping simple expressions inline and grouping the normalization example into an aligned display block.
  - Reformatted the end-to-end sequence for readability without changing the story's requirements or wording.
- Affected files:
  - Phase_3_User_Stories.md
  - CHANGELOG.md
- Rationale and impact:
  - Makes the normalization rules and examples easier to scan; there is no behavior or requirement change.
- Validation:
  - Reviewed the edited US-3.3 section and checked patch whitespace.

## 2026-10-28

### Tidied US-3.2 formatting
- Summary:
  - Streamlined the mathematical layout in US-3.2 by keeping simple expressions inline and grouping related equations into aligned display blocks.
  - Reformatted the hand-calculated example as one aligned set of updates without changing the story's requirements or wording.
- Affected files:
  - Phase_3_User_Stories.md
  - CHANGELOG.md
- Rationale and impact:
  - Makes the history equations and timing easier to scan; there is no behavior or requirement change.
- Validation:
  - Reviewed the edited US-3.2 section and checked patch whitespace.

## 2026-10-28

### Expanded US-3.2 synchronization and history auditing
- Summary:
  - Added monotonically increasing synchronization IDs and stored each sensor reference's establishing ID in the notebook history tracker.
  - Added a normalized row-by-sensor trace for every input bucket, including missing sensors and rows without synchronization. It records entry references, pre/post history, signed deviation, whether an update occurred, and a reason when skipped.
  - Kept event snapshots as clustering inputs and added synchronization/reference IDs to those records. The notebook runner also validates row bucket alignment with the matched Phase 2 trace.
  - Expanded regression coverage for US-3.2's minimum hand-calculated example, signed alternating deviations, synchronization-row timing, ID linkage, and update/skip audit rows.
  - Updated the US-3.2 implementation notes, scripts README, and project plan to describe the two outputs and required trace.
- Affected files:
  - scripts/build_phase3_temperature_clustering.ipynb
  - scripts/test_phase3_history.py
  - scripts/README.md
  - Phase_3_User_Stories.md
  - Distributed_Monitoring_POC_Project_Plan.md
  - CHANGELOG.md
- Rationale and impact:
  - The revised story requires a reconstructable audit of each sensor's history update and the synchronization reference that authorized it. Event snapshots alone did not contain enough row-level detail. Phase 2 behavior and outputs are unchanged.
- Validation:
  - `python -m unittest scripts.test_phase3_history scripts.test_phase2_monitoring -v` passed all 44 tests.
  - Notebook JSON/tag validation and `git diff --check` passed.

## 2026-10-28

### Implemented source-aligned Phase 3 sensor history
- Summary:
  - Added `scripts/build_phase3_temperature_clustering.ipynb`, adapted from the Phase 2 notebook, with `SensorHistoryTracker` in a notebook code cell. It maintains one discounted history value and active synchronization reference per sensor, updates from the entry reference, and returns auditable snapshots when synchronization completes.
  - Implemented zero-history initialization, combined and deferred synchronization causes, automatic membership-change synchronization, missing/offline history retention, and synchronized re-entry without stale-reference updates.
  - Added a notebook runner stage that checks history synchronization against the Phase 2 reference and writes `artifacts/phase3_sensor_history_events.csv`.
  - Added a regression harness that executes the notebook implementation cells and hand-calculated tests for active-reference differences, synchronization-row ordering, multiple synchronizations, missing/returning sensors, zero-observation rows, and invalid inputs.
  - Added US-3.2 implementation notes, documented the notebook workflow in `scripts/README.md`, and listed the notebook/test artifacts and verification gate in the project plan.
- Affected files:
  - scripts/build_phase3_temperature_clustering.ipynb
  - scripts/test_phase3_history.py
  - scripts/README.md
  - Phase_3_User_Stories.md
  - Distributed_Monitoring_POC_Project_Plan.md
  - CHANGELOG.md
- Rationale and impact:
  - Keeps all Phase 3 implementation in the agreed notebook while providing regression coverage against its actual code cells. It emits event snapshots rather than adding history columns to every minute row. No Phase 2 behavior or output changes.
- Validation:
  - `python -m unittest scripts.test_phase3_history scripts.test_phase2_monitoring -v` passed all 41 tests.

## 2026-10-28

### Clarified US-3.2 history update lifecycle
- Summary:
  - Reformatted US-3.2 and specified the per-row history update order, including initialization, later synchronization rows, missing observations, return synchronization, and zero-observation rows.
  - Clarified that histories persist across offline periods and synchronizations, and that clustering-event snapshots are sufficient audit outputs without per-minute history columns.
  - Aligned the project plan's event-based lifecycle with these history timing rules.
- Affected files:
  - Phase_3_User_Stories.md
  - Distributed_Monitoring_POC_Project_Plan.md
  - CHANGELOG.md
- Rationale and impact:
  - Explicit operation order prevents implementations from disagreeing about which reference is used or whether history is discounted on missing data or reset at synchronization. This is a documentation clarification; runtime behavior is unchanged.
- Validation:
  - Documentation-only change; reviewed relevant sections and checked patch whitespace.

## 2026-10-27

### Validated the Phase 2 baseline and clarified US-3.1 implementation
- Summary:
  - Improved Phase 2 invariant failures to identify the affected bucket and field, including message-category totals, empty-observation rows, and forced synchronization traffic.
  - Added regressions for a corrupted exported CSV trace and a corrupted communication total.
  - Added explicit synchronization-policy metadata to Phase 2 run metrics and made integrated notebook validation require it.
  - Added plain-language US-3.1 implementation notes describing the baseline flow, state timing, diagnostic interpretation, and how validation is performed.
- Affected files:
  - scripts/phase2_monitoring.py
  - scripts/test_phase2_monitoring.py
  - scripts/build_phase2_temperature_sensors.ipynb
  - Phase_3_User_Stories.md
  - CHANGELOG.md
- Rationale and impact:
  - More actionable validation errors make it easier to distinguish and diagnose baseline failures before clustering results are interpreted.
  - Valid monitoring behavior and communication counts are unchanged; run metrics gain additive synchronization-policy metadata, and invalid traces now report specific bucket/field details. The user story now explains how the existing Phase 2 implementation meets the acceptance criteria for readers unfamiliar with the project.
- Validation:
  - `python -m unittest scripts.test_phase2_monitoring -v` passed all 31 tests.

## 2026-10-21

### 5. Adopted Approach A for matched Phase 3 comparisons
- Summary:
  - Replaced the fixed-versus-dynamic experiment split with one fixed selected cohort and synchronization on every observed-contributor change, shared by Phase 2, FMIC, and SMIC.
  - Updated US-3.1, US-3.8, US-3.9, related lifecycle/attribution stories, plan gates, sequence, risks, and deliverables to use the existing Phase 2 comparator rather than a duplicate no-availability-sync mode.
  - Added denominator regressions for a low-valued sensor departure raising the mean above threshold without remaining-sensor warming, and a return refreshing references on the next row.
- Affected files:
  - Phase_3_User_Stories.md
  - Distributed_Monitoring_POC_Project_Plan.md
  - scripts/README.md
  - instructions/distributed_monitoring_notebook_required_changes.md
  - scripts/test_phase2_monitoring.py
  - CHANGELOG.md
- Rationale and impact:
  - Fixed cohort does not imply constant observed contributors. Availability-triggered synchronization preserves the agreed observed-only monitoring policy across all algorithms.
  - Existing Phase 2 runtime behavior, metadata identifiers, and outputs remain unchanged. Phase 3 reclusters on completed availability synchronizations; identical fixed/dynamic experiments and a membership ablation are no longer required.
  - Algorithm savings are conditional on the shared availability policy; overlapping cause attribution is not an availability-free causal effect. Floating-point boundary changes remain deferred.
  - Validation: all 30 existing/expanded tests passed, including both denominator regressions and notebook integration. Changelog and whitespace checks passed; no production monitoring logic changed.

### 4. Hardened Phase 2 input loading and clarified comparison reporting
- Summary:
  - Added shared temperature normalization and wired notebook input loading to preserve empty CSV fields while rejecting nonempty invalid text and infinities with column/bucket errors.
  - Added full-precision computational p90 and source metadata without changing the existing rounded threshold field.
  - Made observed-availability communication reduction the explicit headline in metrics metadata and the first analysis-report row; retained existing configured-sensor and legacy metric names and calculations.
  - Expanded the existing suite to 28 tests, including real notebook loading, invalid/missing values, persisted precision, distinct denominators, negative savings, and undefined zero-observation reporting.
- Affected files:
  - scripts/phase2_monitoring.py
  - scripts/test_phase2_monitoring.py
  - scripts/build_phase2_temperature_sensors.ipynb
  - scripts/README.md
  - Distributed_Monitoring_POC_Project_Plan.md
  - CHANGELOG.md
- Rationale and impact:
  - Invalid observations must fail explicitly rather than masquerade as departures. Precision and comparison labels must support matched observed-only Phase 3 analysis.
  - Valid input monitoring behavior and existing metrics are preserved; reports gain additive metadata and a headline percentage row. Missing CSV values must be empty fields, not nonempty sentinel strings.
  - Floating-point boundary behavior is intentionally deferred at the user's request. The fixed-cohort comparator policy remains undecided and is not implemented.
  - Validation: all 28 targeted tests and the full 218,148-row notebook pipeline passed; every pre-existing metric remained exactly unchanged, including 663,650 total messages. The computational threshold is exported as 24.343381.

### 3. Corrected Phase 2 local-constraint reporting and strengthened baseline validation
- Summary:
  - Changed `distributed_constraint_state` to reflect entry sensor-local allowance violations, not synchronization; added reporting-only comparisons on forced rows and explicit incomplete/no-observation states.
  - Removed the redundant `distributed_alert` column. Retained reason/causes fields and labeled existing confusion, false-safe/false-alert, precision/recall, and delay calculations as synchronization diagnostics, not actual global-warning accuracy.
  - Extended the existing module with independent original-input trace replay before rounding and after CSV export, including bucket/field errors and precision-aware numeric checks.
  - Expanded the existing suite to 25 tests with cancellation, multi-sensor boundaries, cooling, comparison coverage, an independent reference oracle, and deliberate trace corruption.
- Affected files:
  - scripts/phase2_monitoring.py
  - scripts/test_phase2_monitoring.py
  - scripts/build_phase2_temperature_sensors.ipynb
  - scripts/README.md
  - instructions/distributed_monitoring_notebook_required_changes.md
  - Distributed_Monitoring_POC_Project_Plan.md
  - Phase_3_User_Stories.md
  - CHANGELOG.md
- Rationale and impact:
  - Separates local sensor constraints, the centralized global threshold oracle, and synchronization actions without adding clustering, a warning subsystem, or one-off repository scripts.
  - Reporting intentionally changes the local-state column and populates forced-row deviation/proximity values; startup/incomplete coverage is `NOT_EVALUABLE`, and all-offline state remains `UNDEFINED`.
  - Validation: all 25 tests and the full 218,148-row pipeline passed. A saved before/after comparison confirmed 71 preserved output columns and every pre-existing metric unchanged, including synchronization events and 663,650 total messages.

### 2. Implemented Phase 2 synchronization on every membership change
- Summary:
  - Added a tested observed-only state machine and wired it into the Phase 2 notebook: every departure/return triggers one synchronization, coinciding causes are retained, and negative-margin precedence/next-row state timing are preserved.
  - Counted startup synchronization and online-only request/response/threshold-update fanout, with free availability detection and no offline traffic. This supersedes the earlier offline-request assumption recorded below.
  - Removed look-ahead initialization and old-mean fallback for empty buckets; undefined global state remains pending with zero traffic and is excluded from classification/delay diagnostics.
  - Extended trace fields, policy metadata, cause attribution, observed-only centralized comparisons, data dictionary, and integrated validation; cleared stale notebook execution outputs.
- Affected files:
  - scripts/phase2_monitoring.py
  - scripts/test_phase2_monitoring.py
  - scripts/build_phase2_temperature_sensors.ipynb
  - scripts/README.md
  - instructions/distributed_monitoring_notebook_required_changes.md
  - Distributed_Monitoring_POC_Project_Plan.md
  - Phase_3_User_Stories.md
  - CHANGELOG.md
- Rationale and impact:
  - Implements the Phase 2 slice of US-3.9 directly, without clustering, coordinators, or new run modes.
  - Startup and previously missed membership events increase synchronization counts; traffic now excludes offline sensors. Legacy configured-cohort comparisons remain labeled separately from the matched observed-only baseline.
  - Validation: 14 synthetic/notebook-integration tests passed, and the full 218,148-row Phase 2 run passed integrated artifact validation. The run detected 10,170 membership changes, all synchronized, and reported zero diagnostic false-safe rows; these dataset results are not a general proof of correctness.

### 1. Locked the Phase 3 observed-only protocol and clustering lifecycle
- Summary:
  - Named `140516editor Book Chapter (Last Version).pdf` as the definitive methodology source and clarified source-preserving history retention across synchronization.
  - Replaced open-ended availability/imputation assumptions with observed-only fixed-cohort and dynamic-membership rules, including first-missing-bucket departure, return synchronization, no minimum active count, and undefined global state with zero observations.
  - Added US-3.15 for event-based clustering at initialization/every completed resynchronization, next-row activation, and highest-ID available coordinator selection.
  - Specified bundled cluster/threshold updates, synchronization-cause attribution without double-counting, and transmitted requests to offline sensors without fabricated responses.
- Affected files:
  - Phase_3_User_Stories.md
  - Distributed_Monitoring_POC_Project_Plan.md
  - CHANGELOG.md
- Rationale and impact:
  - Makes the agreed Phase 3 protocol consistent and testable across the plan and stories without adding the deferred reproducible-execution story.
  - Documentation only: no pipeline code, notebooks, generated artifacts, or historical changelog entries were changed. Runtime compliance remains subject to the documented implementation and correctness tests.

## 2026-10-08

### 1. Finalized the observed-only Phase 1 contract and removed legacy imputation references
- Summary:
  - Removed stale imputation parameters and naming from the active Phase 1 builder and regenerated the artifact set from the observed-only path.
  - Updated the Phase 2 notebook and project documentation to use the canonical `all_devices_observed` series instead of legacy imputation-era names.
- Affected files:
  - scripts/build_phase1_temperature.py
  - scripts/build_phase2_temperature_sensors.ipynb
  - scripts/README.md
  - Distributed_Monitoring_POC_Project_Plan.md
  - CHANGELOG.md
- Rationale and impact:
  - The active pipeline now keeps missing device values blank, reduces coverage/confidence on sparse snapshots, and does not invent values by carry-forward.
  - Regenerating `artifacts/phase1_average_statistics.csv` and downstream Phase 2 artifacts aligns the active output contract with the observed-only design and removes stale imputation labels from the repository workflow.

## 2026-10-07

### 1. Archived the replay validation notebook from the active source tree
- Summary:
  - Moved `scripts/phase2_replay_validation.ipynb` into `Archive/phase2_replay_validation.ipynb` so it is not part of the active repository workflow.
  - Kept the notebook in the archive directory because the repo ignores `Archive/` content and treats it as local, non-source material.
- Affected files:
  - Archive/phase2_replay_validation.ipynb
  - CHANGELOG.md
- Rationale and impact:
  - The core Phase 2 pipeline continues to run through `scripts/run_phase2_notebook.py` and `scripts/build_phase2_temperature_sensors.ipynb`.
  - The archived notebook remains available for historical replay/QA reference without polluting the active source tree or Git-tracked content.


## 2026-09-22

### 3. Added one-second guides to device reporting plot
- Summary:
  - Added higher-contrast vertical guide lines every 10 seconds in the first-five-minute temperature reporting scatterplot.
- Affected files:
  - scripts/phase_1_raw_data_summary.ipynb
  - CHANGELOG.md
- Rationale and impact:
  - Makes the timing and stagger between device reports easier to inspect while keeping square report blocks visible above the guides.

### 4. Added 30-second device reporting block chart
- Summary:
  - Added a binary reporting chart with one column per 30-second interval and one row per device.
  - Filled blocks indicate at least one temperature report in the interval; outlined light blocks indicate no observed report.
- Affected files:
  - scripts/phase_1_raw_data_summary.ipynb
  - CHANGELOG.md
- Rationale and impact:
  - Provides a compact interval-level view of device reporting continuity alongside the second-level scatterplot.

### 5. Added all-data device sample-count bar chart
- Summary:
  - Added a bar chart counting all temperature samples reported by each `DeviceId` across `temperature_raw`.
  - Sorted devices from the highest to the lowest sample count.
- Affected files:
  - scripts/phase_1_raw_data_summary.ipynb
  - CHANGELOG.md
- Rationale and impact:
  - Provides an overall device representation comparison independent of the five-minute reporting visualizations.

### 6. Added full-period device temperature line chart
- Summary:
  - Added a line chart plotting every temperature sample over time for all eight devices in `temperature_raw`.
- Affected files:
  - scripts/phase_1_raw_data_summary.ipynb
  - CHANGELOG.md
- Rationale and impact:
  - Enables comparison of device temperature trajectories, spikes, and longer-term changes without aggregation or smoothing.

### 7. Added per-device temperature summary table
- Summary:
  - Added a table containing the mean, median, standard deviation, first quartile, and third quartile for each device's temperature readings.
- Affected files:
  - scripts/phase_1_raw_data_summary.ipynb
  - CHANGELOG.md
- Rationale and impact:
  - Provides a compact statistical comparison of the temperature distributions across all devices.

### 8. Rounded device temperature summary statistics
- Summary:
  - Rounded the mean, median, standard deviation, first quartile, and third quartile columns in the device temperature summary table to two decimal places.
- Affected files:
  - scripts/phase_1_raw_data_summary.ipynb
  - CHANGELOG.md
- Rationale and impact:
  - Improves table readability while leaving the underlying raw temperature data unchanged.

### 2. Improved device reporting plot readability
- Summary:
  - Tightened the device-row spacing in the first-five-minute temperature reporting plot.
  - Replaced circular points with compact square blocks for each unique device-second report.
- Affected files:
  - scripts/phase_1_raw_data_summary.ipynb
  - CHANGELOG.md
- Rationale and impact:
  - Makes staggered reporting times and gaps between device events easier to see without changing the underlying report selection.

### 1. Updated temperature reporting plot window and dataframe name
- Summary:
  - Renamed the notebook's working temperature dataframe to `temperature_raw`.
  - Changed the device reporting scatterplot from the first hour to the first five minutes of observed temperature data.
- Affected files:
  - scripts/phase_1_raw_data_summary.ipynb
  - CHANGELOG.md
- Rationale and impact:
  - Aligns the notebook variable name with the saved temperature-only dataset and makes short-interval reporting patterns easier to inspect.

## 2026-09-21

### 4. Added device reporting scatterplot for the first temperature hour
- Summary:
  - Updated `scripts/phase_1_raw_data_summary.ipynb` to expose the temperature-only dataframe as `temperatures_raw` consistently for both fresh builds and saved-file reuse.
  - Added a first-hour scatterplot with `DeviceId` on the y-axis, UTC time on the x-axis, and one dot per unique device-second report.
- Affected files:
  - scripts/phase_1_raw_data_summary.ipynb
  - CHANGELOG.md
- Rationale and impact:
  - Makes device-level reporting continuity visible without duplicating multiple rows from the same device and second.
  - The plot uses the earliest observed temperature timestamp as the start of the one-hour window.

### 3. Replaced long-format missingness summaries with representation-share diagnostics
- Summary:
  - Updated `scripts/raw_data_summary.ipynb` to measure each sensor's and device's share of total long-format records instead of treating null `Value` fields as record missingness.
  - Removed value-completeness inputs from the credibility calculation and revised the assessment wording to describe a variability-based score.
- Affected files:
  - scripts/raw_data_summary.ipynb
  - CHANGELOG.md
- Rationale and impact:
  - In long-format telemetry, absent observations are absent rows, so row representation is the appropriate first diagnostic for over- or under-representation.
  - The notebook no longer presents value-null percentages as evidence of temporal completeness; expected-grid coverage remains a separate future analysis.

### 2. Added continuation notebook for replay validation, profiling, drift monitoring, and release gates
- Summary:
  - Added a staged continuation notebook at `scripts/phase2_replay_validation.ipynb` covering deterministic test fixtures, scenario replay, regression assertions, performance profiling, daily drift monitoring, and release-gate artifact diff checks.
  - The notebook is structured as Stage 5 through Stage 10 and is intended to run from the repository root as a self-contained validation and QA companion to the Phase 2 monitoring flow.
  - The fixture/replay section is designed to exercise offline recovery, local trigger cases, forced resyncs, and negative-delta scheduling without requiring large production-like input files.
- Affected files:
  - scripts/phase2_replay_validation.ipynb
  - CHANGELOG.md
- Rationale and impact:
  - Extends the deterministic monitoring pipeline beyond the core Phase 2 output generation into reusable regression, scale, drift, and release validation workflows.
  - Gives maintainers a reproducible QA path for CI checks, daily comparison, and artifact stability reviews without duplicating production logic.

### 1. Added raw-data summary notebook for dataset quality and sensor diagnostics
- Summary:
  - Added a new notebook at `scripts/raw_data_summary.ipynb` that reads all raw sensor CSVs from `Data/files_csv`, normalizes the schema, and generates a minimum useful summary set for dataset quality and sensor diagnostics.
  - The notebook writes CSV artifacts under `artifacts/` covering dataset overview, per-sensor summary statistics, per-device summaries, missingness, gap analysis, and basic quality flags.
  - The output package is designed to be CSV-first for easy downstream review and to support Phase 1/Phase 2 analysis decisions without adding modeling logic.
- Affected files:
  - scripts/raw_data_summary.ipynb
  - CHANGELOG.md
- Rationale and impact:
  - Establishes a reusable raw-data quality preflight before downstream monitoring or transformation work.
  - Gives project reviewers a compact, auditable view of time coverage, device coverage, value ranges, missingness, and obvious quality issues.

## 2026-08-28

### 4. Hardened notebook-centric Phase 2 export/validation pipeline
- Summary:
  - Added a hardening step in the notebook flow to re-apply the public row projection and regenerate report CSV artifacts from the public row schema before final validation.
  - Strengthened Stage 4 validation with internal-column leak checks, dictionary duplication/coverage checks, and cross-artifact consistency checks against metrics communication totals and row/sensor counts.
  - Improved notebook runner preflight by validating required input columns and improved runtime diagnostics with code-cell-index failure context.
  - Removed import-cell clutter by centralizing `re` import in the main import cell.
  - Preserved stakeholder-owned `artifacts/phase2_temperature_sensors.xlsx` unchanged.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - scripts/run_phase2_notebook.py
  - scripts/README.md
  - CHANGELOG.md
- Rationale and impact:
  - Reduces schema drift risk by ensuring report outputs derive from the final public row artifact rather than internal state columns.
  - Improves failure diagnosability and catches cross-artifact contract regressions within the integrated notebook validation path.
  - Keeps monitoring behavior and metric semantics unchanged while increasing reliability.

### 3. Consolidated CSV report export into the Phase 2 notebook and retired standalone exporter scripts
- Summary:
  - Merged CSV report generation logic into `scripts/build_phase2_temperature_sensors.ipynb` so a single notebook run now writes both report artifacts directly.
  - Removed standalone exporter scripts `scripts/export_phase2_report_csvs.py` and `scripts/export_phase2_to_excel.py` from active workflow.
  - Tightened notebook-integrated validation to require `phase2_data_dictionary.csv` and `phase2_sensor_reduction_analysis.csv` and validate their schema/coverage invariants.
  - Updated task and documentation references to remove separate report-export execution.
  - Explicitly preserved `artifacts/phase2_temperature_sensors.xlsx` as a stakeholder-owned analysis file (not generated/overwritten by this migration).
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - .vscode/tasks.json
  - scripts/README.md
  - README.md
  - scripts/export_phase2_report_csvs.py (deleted)
  - scripts/export_phase2_to_excel.py (deleted)
  - CHANGELOG.md
- Rationale and impact:
  - Reduces drift risk by keeping report generation and validation in the same execution path as Phase 2 artifact generation.
  - Removes duplicate exporter maintenance surfaces and simplifies operation to one canonical command path (`scripts/run_phase2_notebook.py`).
  - Preserves stakeholder-managed Excel analysis output while avoiding pipeline coupling to Excel tooling.

### 2. Removed duplicate Phase 2 raw-row CSV export artifact
- Summary:
  - Removed generation of `artifacts/phase2_raw_row_results.csv` from the Phase 2 CSV report exporter so the report pipeline now emits only the data dictionary and reduction-analysis outputs.
  - Removed the exporter CLI flag `--raw-output` and the corresponding return payload key.
  - Added a Windows-safe fallback in CSV writing so temporary file rename lock conflicts can fall back to direct overwrite and continue successfully.
  - Deleted stale local `artifacts/phase2_raw_row_results.csv` and `artifacts/phase2_raw_row_results.csv.tmp` artifacts from the active workspace.
- Affected files:
  - scripts/export_phase2_report_csvs.py
  - scripts/README.md
  - README.md
  - artifacts/phase2_raw_row_results.csv (deleted)
  - artifacts/phase2_raw_row_results.csv.tmp (deleted)
  - CHANGELOG.md
- Rationale and impact:
  - Removes a duplicate row-level output that provided no additional data beyond `artifacts/phase2_temperature_sensors.csv`.
  - Reduces storage pressure and avoids unnecessary copy operations.
  - Keeps the export contract simpler and more reliable on Windows-hosted workspaces.

### 1. Consolidated Phase 2 smoke and export-policy validation into notebook Stage 4
- Summary:
  - Added a new Stage 4 validation section inside the Phase 2 notebook that runs smoke-style checks and export-policy checks as part of notebook execution.
  - Retired standalone validation scripts by removing `scripts/phase2_smoke_check.py` and `scripts/validate_phase2_export_policy.py`.
  - Updated VS Code task wiring and documentation so notebook execution is now the primary path for Phase 2 validation.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - .vscode/tasks.json
  - scripts/README.md
  - instructions/distributed_monitoring_notebook_required_changes.md
  - scripts/phase2_smoke_check.py (deleted)
  - scripts/validate_phase2_export_policy.py (deleted)
  - CHANGELOG.md
- Rationale and impact:
  - Reduces script sprawl and keeps Phase 2 build/validate behavior in one execution flow.
  - Notebook runs now emit integrated validation output and fail in the same process when required invariants are violated.
  - The reduction-analysis `bucket_epoch` check is performed when `artifacts/phase2_sensor_reduction_analysis.csv` is present; if absent, the notebook reports a skip for that artifact-specific check.

## 2026-08-25

### 2. Restored exported local margin fields while retaining proximity score fields
- Summary:
  - Restored exported `entry_{sensor}_local_margin` columns in the Phase 2 row output.
  - Kept `event_{sensor}_margin_proximity_score` columns so both threshold state and proximity state are available in outputs.
  - Kept trigger/state-machine semantics unchanged (`event_{sensor}_local_deviation >= entry_{sensor}_local_margin`).
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - scripts/export_phase2_report_csvs.py
  - scripts/export_phase2_to_excel.py
  - scripts/validate_phase2_export_policy.py
  - scripts/phase2_smoke_check.py
  - scripts/README.md
  - instructions/distributed_monitoring_notebook_required_changes.md
  - artifacts/phase2_temperature_sensors.csv (regenerated)
  - artifacts/phase2_temperature_metrics.json (regenerated)
  - CHANGELOG.md
- Rationale and impact:
  - Restores explicit local-threshold visibility needed for auditability and compatibility with prior schema consumers.
  - Preserves proximity score reporting for distance-to-constraint analysis without changing trigger behavior.

### 1. Replaced exported local margin columns with per-sensor margin proximity scores
- Summary:
  - Updated the Phase 2 row export schema to remove exported `entry_{sensor}_local_margin` columns and add `event_{sensor}_margin_proximity_score` columns for each sensor.
  - The new score is calculated as `entry_delta_global - event_{sensor}_local_deviation`, where positive values are acceptable and negative values indicate violation.
  - Preserved the existing trigger/state-machine behavior (`local_deviation >= local_margin`) so this change is output-schema focused and does not alter core resync semantics.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - scripts/export_phase2_report_csvs.py
  - scripts/export_phase2_to_excel.py
  - scripts/validate_phase2_export_policy.py
  - scripts/phase2_smoke_check.py
  - scripts/README.md
  - instructions/distributed_monitoring_notebook_required_changes.md
  - artifacts/phase2_temperature_sensors.csv (regenerated)
  - artifacts/phase2_temperature_metrics.json (regenerated)
  - artifacts/phase2_data_dictionary.csv (regenerated)
  - artifacts/phase2_sensor_reduction_analysis.csv (regenerated)
  - artifacts/phase2_raw_row_results.csv (regenerated)
  - CHANGELOG.md
- Rationale and impact:
  - Removes duplicated margin information from exported outputs while preserving equivalent local-trigger observability through a single proximity score.
  - Strengthens export and smoke validations so future regressions on this schema are caught automatically.

## 2026-08-24

### 1. Hid redundant internal resync booleans from exported Phase 2 output
- Summary:
  - Kept the internal `event_resync_consumed_from_prior_row` and `event_resync_triggered_by_local_violation` flags available to the calculation path, but removed them from the exported row schema so the public Phase 2 output only exposes the canonical `event_resync_reason` cause field.
  - Left the state-machine timing, branching, and behavior unchanged while preserving all downstream metrics and communication totals.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - scripts/export_phase2_report_csvs.py
  - scripts/export_phase2_to_excel.py
  - scripts/README.md
  - CHANGELOG.md
- Behavior change:
  - The exported Phase 2 row output no longer contains the duplicated resync booleans, while internal calculations still use them to preserve the original state-machine logic.

## 2026-08-24

### 1. Added recovery-aware resync handling for sensors returning after offline gaps
- Summary:
  - Updated the Phase 2 notebook state machine to detect sensors that were absent in the prior synchronized baseline and force a re-sync when they return with valid readings.
  - Set the canonical reason precedence for `event_resync_reason` to:
    - `negative_delta_from_prior_row`
    - `local_constraint_violation`
    - `sensor_recovered_after_offline`
  - Kept the final export schema unchanged while documenting the recovery case through the existing resync reason field instead of creating a separate final-output column.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - CHANGELOG.md
- Rationale and impact:
  - Prevents stale local reference and margin state from masking real offline-sensor recovery events.
  - The algorithm now resets the baseline state when a sensor returns after an outage so the resumed sensor cannot remain falsely safe due to an outdated local reference.

## 2026-08-07

### 1. Reordered Phase 2 row output columns for resync state fields
- Summary:
  - Updated the Phase 2 row output schema so `exit_xbar_t0_if_resync` appears immediately after `entry_xbar_t0`, `exit_delta_global_if_resync` appears immediately after `entry_delta_global`, and the standalone `exit_delta_global` column is removed.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - artifacts/phase2_temperature_sensors.csv
  - artifacts/phase2_raw_row_results.csv
- Behavior change:
  - Generated Phase 2 row exports now present the resync-state columns in the requested order without the legacy `exit_delta_global` field.

### 2. Removed bucket_epoch from Phase 2 reduction-analysis exports
- Summary:
  - Hardened the Phase 2 CSV report export so the reduction-analysis output does not include a `bucket_epoch` column even if a future upstream change introduces it.
- Affected files:
  - scripts/export_phase2_report_csvs.py
  - artifacts/phase2_sensor_reduction_analysis.csv
- Behavior change:
  - The generated reduction-analysis CSV continues to expose only the metric summary columns and no longer carries a bucket epoch field.

### 3. Standardized Phase 2 export rounding to 4 decimal places
- Summary:
  - Updated the Phase 2 CSV report exporter to round exported numeric values to 4 decimal places consistently at the reporting boundary.
  - Added a lightweight validation script to check the exported schema and rounding policy for the Phase 2 artifacts.
- Affected files:
  - scripts/export_phase2_report_csvs.py
  - scripts/validate_phase2_export_policy.py
  - scripts/README.md
  - CHANGELOG.md
- Behavior change:
  - The exported row-trace and reduction-analysis CSVs now follow the same 4-decimal reporting convention without introducing a shared rounding helper abstraction.

### 4. Switched Phase 2 observed-global-average to the current row's sensor mean
- Summary:
  - Updated the Phase 2 notebook logic to derive `observed_global_average` from the arithmetic mean of the current row's sensor readings rather than the Phase 1 global-average column.
  - Updated the Phase 2 documentation to reflect the new row-level semantics for the observed global average.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - scripts/README.md
  - CHANGELOG.md
- Behavior change:
  - Generated Phase 2 row outputs now report the observed global average based on the same minute's sensor values that the state machine is evaluating.

### 4. Switched Phase 2 to the strict all-devices policy
- Summary:
  - Updated Phase 2 notebook logic to use `average_temperature_all_devices` as the global observation source.
  - Updated Phase 2 p90 selection to use the `all_devices_including_imputed` row from `phase1_average_statistics.csv`.
  - Updated Phase 2 documentation and generated metadata to reflect the new all-devices policy.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - scripts/README.md
  - Distributed_Monitoring_POC_Project_Plan.md
  - scripts/export_phase2_report_csvs.py
  - scripts/export_phase2_to_excel.py
  - artifacts/phase2_temperature_sensors.csv (regenerated)
  - artifacts/phase2_temperature_metrics.json (regenerated)
  - artifacts/phase2_data_dictionary.csv (regenerated)
  - artifacts/phase2_raw_row_results.csv (regenerated)
- Behavior change:
  - Phase 2 now uses the all-devices average and all-devices p90 threshold as the strict policy source.

1. Record every implemented code or documentation change in this file.
2. Add entries in chronological order.
3. Include affected files and a short rationale.
4. Note output/schema changes when artifacts are affected.

## 2026-07-12 to 2026-07-15

### 1. Added per-sensor local deviation outputs in Phase 2
- Summary:
  - Added per-sensor local deviation columns to Phase 2 output.
  - Initial formula was aligned to synchronized reference usage in the active state-machine implementation.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - artifacts/phase2_temperature_sensors.csv (regenerated)

### 2. Standardized Phase 2 numeric output precision
- Summary:
  - Applied 4-decimal output formatting for Phase 2 exported values.
  - Updated metrics JSON formatting to 4-decimal reporting where applicable.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - artifacts/phase2_temperature_sensors.csv (regenerated)
  - artifacts/phase2_temperature_metrics.json (regenerated)

### 3. Reworked Project Plan to prioritize Distributed_Data_Streams alignment
- Summary:
  - Added explicit precedence rule: if conflicts exist, Distributed_Data_Streams takes precedence.
  - Updated locked decisions and Phase 2 semantics toward local-deviation/margin framing.
  - Added category-level communication accounting requirements.
  - Clarified canonical boundary semantics and d=1 bridge to multivariate formulation.
- Affected files:
  - Distributed_Monitoring_POC_Project_Plan.md

### 4. Rebuilt active Phase 2 notebook state machine to match revised plan
- Summary:
  - Implemented explicit synchronized per-sensor reference state.
  - Added scheduled next-row re-sync behavior for negative delta.
  - Added communication-category fields (trigger/request/response/broadcast/total).
  - Added richer event/state fields and diagnostics metadata.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - artifacts/phase2_temperature_sensors.csv (regenerated)
  - artifacts/phase2_temperature_metrics.json (regenerated)

### 5. Updated script documentation for new Phase 2 behavior
- Summary:
  - Documented new state machine, policy definitions, and output schema highlights.
- Affected files:
  - scripts/README.md

### 6. Changed local trigger policy to warming-only
- Summary:
  - Updated trigger semantics from absolute-deviation style to warming-only:
    - local_deviation >= local_margin
  - Cooling deviations no longer trigger local re-sync requests.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - scripts/README.md
  - Distributed_Monitoring_POC_Project_Plan.md
  - Writing/Markdowns/distributed_monitoring_notebook_required_changes.md
  - artifacts/phase2_temperature_sensors.csv (regenerated)
  - artifacts/phase2_temperature_metrics.json (regenerated)

### 7. Removed duplicate/legacy state columns and renamed margin fields
- Summary:
  - Consolidated duplicate global state fields by keeping preferred names:
    - kept: prior_xbar_t0, prior_delta_global
    - removed from output: reference_global_average_before, global_delta_before
  - Renamed per-sensor margin columns:
    - from: {sensor}_local_delta
    - to: {sensor}_local_margin
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - scripts/README.md
  - Distributed_Monitoring_POC_Project_Plan.md
  - Writing/Markdowns/distributed_monitoring_notebook_required_changes.md
  - artifacts/phase2_temperature_sensors.csv (regenerated)

### 8. Removed actual_positive_global output field
- Summary:
  - Removed actual_positive_global from Phase 2 row output.
  - Metrics now use global_violation as the canonical actual label.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - artifacts/phase2_temperature_sensors.csv (regenerated)
  - artifacts/phase2_temperature_metrics.json (regenerated)

### 9. Consolidated predicted/count aliases to keep re-sync naming
- Summary:
  - Consolidated predicted_positive_any_sensor into resync_requested_any.
  - Consolidated triggering_sensor_count into resync_requested_count.
  - Updated metrics logic to use resync_requested_any as predicted signal.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - artifacts/phase2_temperature_sensors.csv (regenerated)
  - artifacts/phase2_temperature_metrics.json (regenerated)

### 10. Restored sensor request semantics on scheduled re-sync rows
- Summary:
  - Scheduled re-sync rows now still compute local deviation and per-sensor request flags.
  - resync_requested_any now reflects sensor-request activity rather than any system-performed re-sync.
  - This preserves the distinction between sensor requests and scheduled/system resync actions.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - artifacts/phase2_temperature_sensors.csv (regenerated)
  - artifacts/phase2_temperature_metrics.json (regenerated)

### 11. Keep local evaluation active during negative-delta scheduled rows
- Summary:
  - Scheduled re-sync rows now evaluate local deviations and re-sync request flags instead of blanking them.
  - Sensor requests and system-performed re-syncs remain separate concepts in the output schema.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - artifacts/phase2_temperature_sensors.csv (regenerated)
  - artifacts/phase2_temperature_metrics.json (regenerated)

## 2026-07-31

### 12. Enforced changelog-first workflow for all future changes
- Summary:
  - Added a repository-level agent policy that requires `CHANGELOG.md` updates for every implemented change.
  - Added a validation script to check that changelog entries include a required date token and optional text tokens.
  - Added VS Code tasks to run changelog checks quickly during workflow.
- Affected files:
  - AGENTS.md
  - scripts/check_changelog_entry.py
  - .vscode/tasks.json
  - CHANGELOG.md

## 2026-08-05

### 13. Renamed Phase 2 row fields to explicit timing scopes and added transition summary
- Summary:
  - Renamed the Phase 2 row schema to use explicit `entry_*`, `observed_*`, `event_*`, and `exit_*` timing semantics.
  - Added `transition_summary` near the front of each Phase 2 row for compact audit readability.
  - Split overloaded re-sync fields into distinct event-consumption, event-trigger, event-performed, and exit-scheduling fields while preserving the underlying state-machine behavior.
  - Hardened notebook path resolution so direct notebook execution falls back from `Path.cwd()` to the repository root when run from the `scripts` directory.
  - Updated the notebook metrics bindings and repository documentation to match the renamed schema and row invariants.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - scripts/README.md
  - Distributed_Monitoring_POC_Project_Plan.md
  - instructions/distributed_monitoring_notebook_required_changes.md
  - artifacts/phase2_temperature_sensors.csv (regenerated)
  - artifacts/phase2_temperature_metrics.json (regenerated)
  - CHANGELOG.md
- Rationale and impact:
  - Makes each minute row easier to audit in isolation without changing trigger timing or re-sync timing semantics.
  - Introduces a deliberate breaking schema change by replacing the old Phase 2 column names immediately rather than emitting compatibility aliases.

### 14. Prepared the repository for source-only GitHub publication
- Summary:
  - Added a root `.gitignore` for local environments, raw data, generated artifacts, archives, and temporary files.
  - Replaced machine-specific interpreter paths in VS Code task and launch configurations with interpreter-selection variables.
  - Rewrote setup and repository documentation so GitHub-facing guidance no longer depends on a personal Dropbox path or committed generated outputs.
  - Cleared saved outputs and execution counts from the active Phase 2 notebook and normalized its publish-facing kernel metadata.
- Affected files:
  - .gitignore
  - .vscode/tasks.json
  - .vscode/launch.json
  - instructions/PYTHON_ENV_SETUP_GUIDE.md
  - README.md
  - scripts/README.md
  - artifacts/README.md
  - scripts/build_phase2_temperature_sensors.ipynb
  - CHANGELOG.md
- Rationale and impact:
  - Removes the main machine-specific publication leaks while keeping the executable workflow and documentation intact.
  - Establishes a clear source-only repository boundary so collaborators regenerate raw outputs locally rather than pulling them from Git history.

### 15. Corrected forced re-sync row semantics to prevent false local trigger traffic
- Summary:
  - Refactored the Phase 2 state-machine row loop so rows that consume a scheduled re-sync from the prior row are treated as forced synchronization events.
  - Forced rows now skip local trigger evaluation against prior entry margins, set all per-sensor `event_{sensor}_resync_requested` values to `0`, and keep `trigger_message_count = 0`.
  - Preserved forced re-sync fanout counting (`request/response/broadcast`) and added invariant assertions to guard forced-row semantics.
  - Removed same-row forced+local dual-cause labeling behavior for the current model.
  - Updated Phase 2 documentation and implementation guidance to reflect the corrected forced-row policy and acceptance checks.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - scripts/README.md
  - instructions/distributed_monitoring_notebook_required_changes.md
  - CHANGELOG.md
- Rationale and impact:
  - Prevents negative-margin forced rows from generating spurious local trigger messages.
  - Makes communication totals and classification-style diagnostics reflect distinct forced synchronization vs local-trigger events.

### 16. Fixed phase2-smoke-check task quoting for PowerShell execution
- Summary:
  - Replaced the inline `python -c` smoke-check command with a script-backed task that executes `scripts/phase2_smoke_check.py`.
  - Removed shell-dependent quoting complexity that caused inline command parsing failures in PowerShell.
- Affected files:
  - .vscode/tasks.json
  - scripts/phase2_smoke_check.py
  - CHANGELOG.md
- Rationale and impact:
  - Restores one-command smoke validation in VS Code tasks for Windows PowerShell environments.
  - Makes the smoke check easier to maintain and portable across shells.

### 17. Added Phase 2 multi-tab Excel report export
- Summary:
  - Added a dedicated Phase 2 report exporter that writes a three-tab Excel workbook for inclusion-ready reporting.
  - Implemented `Data Dictionary`, `Sensor Reduction Analysis`, and `Raw Row Results` sheets in a fixed order.
  - Defined analysis tab calculations for baseline every-minute communication, actual POC communication, absolute difference, and primary reduction ratio/percent.
  - Added a VS Code task for one-command workbook generation and updated repository documentation.
- Affected files:
  - scripts/export_phase2_to_excel.py
  - .vscode/tasks.json
  - scripts/README.md
  - README.md
  - requirements.txt
  - CHANGELOG.md
- Rationale and impact:
  - Provides a shareable Excel deliverable without changing Phase 2 state-machine behavior.
  - Improves stakeholder communication by combining metric interpretation and raw traceability in one workbook.

### 18. Switched reporting workflow to CSV-first Phase 2 exports
- Summary:
  - Added a dedicated CSV-first exporter that generates three report artifacts: data dictionary, sensor reduction analysis, and raw row results.
  - Updated the VS Code task to run CSV export directly and removed the Excel dependency from required packages.
  - Updated repository and script documentation to describe CSV outputs and defer workbook stitching to a later step.
- Affected files:
  - scripts/export_phase2_report_csvs.py
  - .vscode/tasks.json
  - scripts/README.md
  - README.md
  - requirements.txt
  - CHANGELOG.md
- Rationale and impact:
  - Reduces failure risk from large workbook writes while preserving the full reporting content.
  - Keeps outputs easy to validate, diff, and package later into workbook tabs when needed.

## 2026-08-06

### 19. Added Phase 2 correctness observability fields and alias metrics (non-gating)
- Summary:
  - Added row-level centralized-vs-distributed observability fields to Phase 2 output: `centralized_constraint_state`, `distributed_constraint_state`, `distributed_alert`, `false_safe`, `false_alert`, and `violation_detection_delay_buckets`.
  - Added explicit run-level alias counters in metrics: `false_negative_count`, `false_positive_count`, `false_safe_count`, and `false_alert_count`.
  - Updated CSV report export logic and script documentation to include the new observability schema.
  - Kept behavior observational only: no fail-run gate was introduced for false-safe or false-alert rows.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - scripts/export_phase2_report_csvs.py
  - scripts/README.md
  - CHANGELOG.md
- Rationale and impact:
  - Makes row-level correctness behavior directly inspectable alongside communication metrics.
  - Preserves current experimentation workflow by reporting contradictions without blocking execution.

### 20. Simplified reduction analysis metrics for CSV report consumption
- Summary:
  - Removed `reduction_ratio_primary` from `phase2_sensor_reduction_analysis.csv` output.
  - Rounded `reduction_percent_primary` values to two decimal places.
  - Removed `reduction_ratio_primary_from_metrics` from `phase2_sensor_reduction_analysis.csv` output.
- Affected files:
  - scripts/export_phase2_report_csvs.py
  - CHANGELOG.md
- Rationale and impact:
  - Aligns the analysis artifact with requested reporting format and reduces redundant ratio fields.

### 21. Redefined correctness metrics around implemented re-synchronization
- Summary:
  - Changed Phase 2 row-level correctness fields so `distributed_alert`, `false_safe`, and `false_alert` are based on `event_resync_performed` rather than request-generation bits.
  - Changed confusion-matrix diagnostics so predicted-positive means an implemented re-synchronization occurred on the current row.
  - Updated report/dictionary text and README documentation to distinguish request generation from implemented mitigation.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - scripts/export_phase2_report_csvs.py
  - scripts/README.md
  - CHANGELOG.md
- Rationale and impact:
  - Prevents forced re-sync rows from being misclassified as missed violations solely because local warning evaluation was intentionally skipped.
  - Aligns false-safe/false-negative reporting with the user-requested operational question: whether a violating minute lacked an implemented re-synchronization.

### 22. Removed selected correctness metrics from reduction analysis CSV
- Summary:
  - Removed `ratio_delta_computed_minus_metrics` from `phase2_sensor_reduction_analysis.csv` output.
  - Removed `false_negative_count` from `phase2_sensor_reduction_analysis.csv` output.
  - Removed `false_positive_count` from `phase2_sensor_reduction_analysis.csv` output.
- Affected files:
  - scripts/export_phase2_report_csvs.py
  - artifacts/phase2_sensor_reduction_analysis.csv
  - CHANGELOG.md
- Rationale and impact:
  - Keeps the reduction analysis artifact focused on communication and selected observability counters.
  - Avoids duplicating confusion-matrix-oriented fields in this report output.

## Notes

- Archive files were intentionally not modified unless explicitly requested.
- This changelog is now the canonical running record for implemented changes in this repository.
