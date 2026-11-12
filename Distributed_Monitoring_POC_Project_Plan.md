# Distributed Monitoring POC Project Plan

This plan is the current project specification. The approved stable-cohort
redesign and its subsequent comparability corrections are incorporated here.
The [project history](project_history.md) preserves the original discussions,
pivot, implementation milestones, and point-in-time decisions; it does not
govern current requirements.

## Implementation and Evidence Status (verified 2026-11-12)

- **Phase 1 transformation and shared monitoring preparation:** implemented.
  The current Phase 1 receipt records 77 passing tests; shared preparation
  derives the stable-cohort P90 from aligned data rather than storing it in
  Phase 1 statistics or configuration.
- **Matched Phase 2 and Phase 2/C0 equivalence:** implemented. The current
  matched summary reports 9,159 messages, 467 synchronizations, and passing
  sampled-state correctness. Its independent receipt records 49 passing tests.
- **C0/C1/C2 controls and FMIC/SMIC:** implemented. The current Phase 3 run
  (`2026-11-12T13:31:38.792440+00:00`) contains three controls and 38 clustered
  configurations. Its independent receipt records 170 passing tests and is
  hash-referenced by the summary. The read-only saved-results loader passed
  against this run and its current inputs, configuration, outputs, and receipt.
- **Current reporting:** `scripts/phase3_analyze.ipynb` reads and analyzes saved
  outputs only; the governing current interpretation is in §7.4. No production
  rerun was performed for this documentation update.
- **Not demonstrated / deferred:** the original eight-device multivariate POC,
  a separately measured event-level detection-delay distribution,
  out-of-sample threshold or alpha performance, intermittent-availability
  robustness, and physical network latency, energy, bandwidth, or fault
  tolerance. Their status is not upgraded by the current receipts.

## 1) How To Read This Plan

**Phase 1 ownership update (2026-11-11, US-1.16):**
[`scripts/phase1_implement.ipynb`](scripts/phase1_implement.ipynb) is the
canonical general transformation and optional duplicate-audit implementation.
[`scripts/shared_monitoring_engine.py`](scripts/shared_monitoring_engine.py)
now owns stable-cohort validation, mean/P90 preparation, and shared downstream
freshness checks. Phase 1 neither requires nor mutates the monitoring
configuration. The cohort P90 is derived run evidence embedded in Phase 2/3
records, not a row written by Phase 1 or a numerical value stored in the
experiment configuration. Experimental populations, full precision, and
scientific algorithms remain unchanged. US-1.19 places current Phase 1
data and run/validation records in `artifacts/phase1_operational/`; analysis
remains saved/read-only. Historical artifact paths below are not current
dependencies.

**Execution architecture update (2026-11-11, US-3.32):** Phase 3 has exactly
three maintained executable files: [`scripts/phase3_implement.py`](scripts/phase3_implement.py),
[`scripts/phase3_test.py`](scripts/phase3_test.py), and
[`scripts/phase3_analyze.ipynb`](scripts/phase3_analyze.ipynb). The implementation
defaults to the revised C0/C1/C2 plus 38 clustered evaluations; tests are external
and analysis reads saved results only. Notebook-only execution/tagged-cell
loading requirements are superseded. The original notebook and compatibility
modules are retired after full-matrix equivalence; historical scientific findings
below remain historical. See [current commands and rollback](scripts/README_scripts.md#us-332-three-file-workflow-and-verified-cutover).

This document has two layers:
1. Discussion view for stakeholder alignment.
2. Implementation view with deterministic rules that can be coded directly.

The approved Phase 3A design uses fixed participation; changing contributors,
re-entry, and availability-triggered synchronization are not part of the
primary FMIC/SMIC experiment.

Maintained execution order for a new reproducible run:
1. Phase 1 publishes aligned temperature snapshots and general statistics.
2. Shared monitoring preparation validates the stable cohort and derives its
   full-precision P90 from the aligned Phase 1 output.
3. Phase 2 produces the matched, two-sided equal-allowance baseline and an
   independent validation receipt.
4. Phase 3 validates Phase 2/C0 singleton equivalence, then evaluates C0/C1/C2
   controls and FMIC/SMIC over the 19-value alpha grid. Independent tests and
   saved-results analysis remain separate; clustered algorithms determine their
   own synchronization times.
5. Phase 3B is an optional later robustness extension for the broader dataset
   with changing sensor availability; it is not on the Phase 3A critical path.
6. Multivariate monitoring remains deferred. The sponsor has not yet decided
   whether the overall POC objective should be formally revised to temperature-
   only or retained as a distinct later multivariate phase.

---

## 2) Conflict Resolution And Locked Decisions

Precedence rule for this repository:
1. The definitive methodology source is [`Writing/Motivation/140516editor Book Chapter (Last Version).pdf`](Writing/Motivation/140516editor%20Book%20Chapter%20%28Last%20Version%29.pdf), *Clustering for Monitoring Distributed Data Streams*. If this plan or another summary conflicts with the chapter on history, normalization, clustering mathematics, FMIC/SMIC calculations, or source-comparable broadcast accounting, the chapter takes precedence **for those source-defined methods**. Explicitly labeled project adaptations (separate root, exact threshold boundary, transmission accounting, and all-zero-weight fallback) govern this project’s experimental implementation and must not be presented as formulas supplied by the chapter.
2. This plan governs the current project design, population, project adaptations, and implementation requirements. The project history and completed user stories record prior decisions and do not override it.
3. Section 1.4 and Algorithms 1.4.1–1.4.2 of the definitive chapter define the clustering/monitoring method; the chapter appendices define moment calculations and source-comparable broadcast accounting.
4. Existing Phase 3 user stories remain historical implementation records; resolve superseded requirements using this plan and later approved decisions.

### 2.1 Scope Changes From Prior Version
1. Phase 1 remains the full temperature transformation core; its calculation and aggregation logic is unchanged. Source-file discovery was corrected to exclude the aggregate `temperature_raw.csv` from raw inputs (documented in §8.1).
2. Phase 2 remains the deterministic non-clustered monitoring implementation. The existing full-data Phase 2 run is preserved as a historical artifact.
3. The primary clustering experiment is now **Phase 3A**, a stable-cohort experiment using six continuously observed sensors over a locked interval.
4. The previous Phase 3 requirement to model departures, returns, changing observed contributors, re-entry synchronization, changing denominators, and availability-driven coordinator changes is removed from the Phase 3A critical path.
5. Those availability-aware requirements are reserved for optional **Phase 3B** robustness work.
6. Phase 3A production outputs are intentionally compact. Detailed deterministic intermediate states are validated through tests or optional debug traces rather than persisted for every row and alpha.
7. Alpha is treated as a dataset-specific tuning parameter rather than a primary research question.
8. Multivariate monitoring remains a possible later extension after FMIC/SMIC validation; it must not be mixed into the Phase 3A experiment.

### 2.2 Locked Decisions
1. The current Phase 2 primary input is `artifacts/phase1_operational/phase1_aligned_temperature.csv`, subject to Phase 1 publication and freshness checks.
2. The existing full-data Phase 2 run may continue to use its existing Phase 1 threshold source for historical comparability.
3. Phase 3A uses sensors **A, C, D, E, F, and G** only.
4. Phase 3A uses the continuous UTC interval from **2022-02-24T18:50:00+00:00** through **2022-03-10T15:53:00+00:00**, inclusive, with **19,984 one-minute buckets**. Both endpoints are inclusive, so the interval spans 19,983 elapsed minutes.
5. Every selected sensor must have a valid observation in every Phase 3A bucket. No sensor-value imputation is permitted. If cohort, interval, row count, or completeness validation fails, Phase 3A stops rather than falling back to dynamic availability handling.
6. Shared monitoring preparation computes the `phase3a_stable_cohort` mean series and P90 from the aligned input; Phase 1 does not publish a cohort statistics row.
7. The Phase 3A p90 is calculated programmatically from the approved experimental population. The recorded full-precision result is **22.428666649999997 °C**; derived, provenance-bound run evidence, not a hard-coded number, is authoritative.
8. The current Phase 2 monitoring code is reused rather than rewritten. A matched Phase 3A Phase 2 run is created by filtering to the approved cohort/interval and using the Phase 3A p90.
9. Membership-change behavior must never activate in the matched Phase 3A Phase 2 run. If it does, the input/filtering logic is incorrect.
10. The revised comparison uses matched Phase 2, C0/C1/C2 controls, and full FMIC/SMIC under identical observations, timestamps, threshold, boundary convention, and transmission definitions. Only Phase 2 and equal-allowance singleton C0 must match per bucket; clustered algorithms determine their own synchronization timing.
11. The local deviation definition remains `delta_v_i(t) = v_i(t) - v_i(t0_i)`, where `t0_i` is the most recent synchronization reference for sensor i.
12. The canonical boundary convention remains safe when metric `<` boundary and violated when metric `>=` boundary. Logic uses unrounded values.
13. Source-aligned history remains persistent across resynchronizations and uses signed change relative to the active synchronization reference, not prior-minute change.
14. Phase 3A normalization uses the same six sensors at every clustering event. For scalar history, `H = max_i |h_i|`; when `H > 0`, `a_i = h_i / H`, preserving sign and raw history.
15. The initial all-zero-history case remains a valid deterministic edge case and uses the previously agreed singleton fallback.
16. Cluster quality, partition quality, signed cancellation, greedy merging, stopping behavior, and final partition selection remain source-aligned and are not simplified away.
17. Phase 3A removes runtime logic used only for changing availability: departures, returns/re-entry, changing eligible sets, offline history suspension, changing denominators, membership-triggered synchronization, membership cause attribution, availability-driven coordinator changes, zero-observation states, and deferred synchronization waiting for return.
18. Detailed availability-aware logic may be retained for optional Phase 3B, but it must not complicate the primary Phase 3A execution path.
19. Full sensor-by-minute history traces and exhaustive clustering-search audits are not normal Phase 3A deliverables.
20. Phase 3A retains selected compact synchronization snapshots with event ID, timestamp, algorithm, alpha, raw histories, normalized histories, selected partition and quality, cluster count, and coordinator assignments; full per-event traces are not required.
21. Detailed traces may be generated only through explicit debug/test modes or small samples.
22. FMIC was implemented and reviewed end-to-end in US-3.19 before SMIC was implemented and reviewed in US-3.20. Their production reports show passing correctness at `alpha=0.10`; the US-3.21 synthetic formula, protocol, correctness, and communication-accounting validation gate has also passed.
23. FMIC and SMIC share one monitoring architecture; their main algorithm-specific difference is the source-defined weighting/allowance calculation.
24. Initial correctness work may use `alpha=0.10` as a baseline implementation value only.
25. The revised evaluation runs three alpha-independent controls and a 19-value alpha sweep (`0.05, 0.10, ..., 0.95`) for each of FMIC and SMIC, after correctness and Phase 2/C0 equivalence gates pass. Alpha remains dataset-specific; a lowest-message setting is not a universal optimum.
26. Phase 3A uses six sensors plus a **separate root component**. Coordinators are sensor members; communication with oneself costs zero. A request and its response are separate transmissions. Actual transmissions are counted by category and reconcile exactly; chapter-style broadcast estimates, if shown, are labeled separately and are not substituted for actual totals. Membership categories are not required because membership is fixed.
27. Correctness is demonstrated primarily with focused synthetic and hand-calculated tests rather than by retaining every deterministic full-run intermediate state.
28. Reproducibility uses the aligned input, experiment configuration, derived threshold evidence, implementation, independent tests, provenance, and compact results; no Phase 1 cohort statistics row is required.
29. Phase 3B is optional. Phase 3A must be completed and interpreted before any Phase 3B work is considered required.
30. Existing Phase 3 user stories are not rewritten retroactively; this plan records the current Phase 3A requirements.

### 2.3 Source-to-Implementation Crosswalk

The chapter is the authority for its methodology; the original work statement
defines the broader POC objective, not the chapter's mathematical rules. The
available work statement is
[`Writing/Motivation/Distributed_Data_Streams (1).pdf`](Writing/Motivation/Distributed_Data_Streams%20%281%29.pdf);
its title and six-page contents were checked against the source. The slides at
[`Writing/Motivation/Sample Slides (2).pdf`](Writing/Motivation/Sample%20Slides%20%282%29.pdf)
are supplementary only. The crosswalk below identifies each source location,
classification, project treatment, rationale, and verification method; it does
not claim that every source theorem was empirically established by this
temperature-only study.

1. **Global function and geometric constraints** — Chapter §§1.1 and 1.3 and
   work statement pp. 1–2. **Classification:** source-derived general problem;
   scalar temperature is a project instance. **Treatment:** Phase 3A monitors
   the mean of six scalar temperature streams against one threshold.
   **Rationale / verification:** the scalar instance does not empirically
   establish the chapter's multivariate or nonlinear guarantees; verify the
   selected columns and offline mean oracle in saved run evidence.
2. **Signed change and discounted history** — Chapter §1.4.
   **Classification:** source-derived. **Treatment:** retain signed history
   across ordinary synchronizations and update it from the active reference.
   **Rationale / verification:** this preserves cancellation information;
   verify with hand-calculated history and normalization tests.
3. **Normalization, clustering, size penalty, and greedy merging** — Chapter
   §1.4, Eqs. 1.8–1.10, Algorithm 1.4.1. **Classification:** source-derived
   for scalar histories. **Treatment:** normalize signed histories, sum before
   taking absolute values, apply alpha's cluster-size penalty, and follow the
   specified greedy candidate selection. **Rationale / verification:** this
   maintains the source mathematics while fixing project dimension and
   deterministic edge conventions; verify formula, partition, and synthetic
   clustering tests.
4. **Moments and node-dependent allowances** — Chapter §1.4, Algorithm 1.4.2,
   Appendix 1. **Classification:** source-derived formulas with
   project-tested conventions. **Treatment:** FMIC and SMIC use the shared
   monitoring lifecycle and their respective moment/allowance calculations
   in §6.9. **Rationale / verification:** this separates weighting from
   clustering; verify hand calculations and saved C1/C2 controls.
5. **Coordinator checks and broadcast accounting** — Chapter §1.4 and
   Appendix 2. **Classification:** source-derived concept; project transmission
   totals are an adaptation. **Treatment:** report actual transmissions in
   the six-sensor-plus-separate-root model; do not equate root-as-sensor
   broadcast estimates with project totals. **Rationale / verification:**
   topology and accounting units differ; verify all seven categories and three
   pathways reconcile.
6. **Separate root, sensor coordinators, self-messages, and actual requests,
   responses, and updates** — Locked decisions §§2.2 and 7.3.
   **Classification:** project adaptation. **Treatment:** use six sensors plus
   a distinct root, a participating sensor as coordinator, and zero-cost
   self-messages. **Rationale / verification:** this specifies topology and
   unit; verify category/pathway accounting and singleton controls.
7. **Two-sided SAFE/VIOLATED persistence and absolute local deviations** —
   Project §§5–7 and US-3.23. **Classification:** project monitoring-policy
   adaptation. **Treatment:** retain the last root-known state between
   synchronizations and use absolute distance to the threshold in both
   directions. **Rationale / verification:** do not attribute this policy to
   a chapter theorem; verify Phase 2/C0 per-bucket equivalence and bidirectional
   correctness.
8. **Global SAFE `<` / VIOLATED `>=` and local `>=` checks** — Locked
   decisions §§2.2 and 5–7. **Classification:** project boundary adaptation.
   **Treatment:** equality is globally VIOLATED and triggers a local check.
   **Rationale / verification:** this deterministic convention includes zero
   allowance; verify exact-boundary tests.
9. **All-zero fallbacks and deterministic coordinator/tie rules** — Locked
   decisions and §6.9. **Classification:** project edge-case and tie
   adaptations. **Treatment:** use the singleton all-zero-history fallback,
   equal all-zero-weight fallback, lexicographically highest coordinator, and
   specified tie rules. **Rationale / verification:** these are implementation
   choices, not source formulas; verify their named tests and saved conventions.
10. **Eight-device environmental-vector objective and detection delay** — Work
    statement pp. 4–6. **Classification:** original POC requirement, not
    demonstrated by Phase 3A. **Treatment:** retain the six-sensor
    temperature-only study as a bounded completed experiment; multivariate
    operation and event-level delay remain unfulfilled/not separately
    evaluated. **Rationale / verification:** verify source scope; no
    multivariate or physical latency experiment was run. See §§3, 7.2, and 12.
11. **Stable six-sensor cohort and availability robustness** — Project pivot
    and work statement pp. 4–6. **Classification:** project scope adaptation;
    broader work deferred. **Treatment:** Phase 3A uses A, C, D, E, F, and G
    continuously; Phase 3B is optional and separate. **Rationale /
    verification:** do not infer completion of the original broader objective;
    verify the locked cohort and report limits.

---

## 3) Executive Summary (Discussion View)

### What This Experiment Measures
The completed Phase 3A study is a deterministic offline simulation of a
distributed monitoring protocol, not a deployed sensor network. It compares
logical message transmissions under one fixed six-sensor temperature cohort,
one retrospective empirical threshold, and the saved control/alpha
configurations. Its sampled-state correctness results apply to the observed
60-second buckets and the modeled reliable-communication assumptions only.

The controlled weighting and conditional-clustering results are summarized in
§7.4. They are dataset-specific contrasts, not general causal effects or
statistically significant population estimates. The alpha grid is exploratory
in-sample; the P90 is derived retrospectively from the same interval used for
evaluation.

### Why This Design Is Deterministic
The workflow does not train a predictive model. It applies fixed rules over aligned minute-bucket data:
1. a locked experimental cohort and interval;
2. a programmatically derived Phase 3A p90 threshold from that experimental population;
3. fixed history, clustering, allowance, boundary, synchronization, and message-counting rules;
4. shared implementation logic for FMIC and SMIC except where the source defines different weight/allowance calculations.

### Original POC Scope Checkpoint
The original work statement specifies eight devices and global monitoring of
environmental vectors including temperature, humidity, pressure, gas/IAQ, and
light, and asks for “Detection delay compared to centralized monitoring.”
Phase 3A instead completes a temperature-only scalar threshold experiment over
six continuously observed sensors. It does not fulfill the multivariate,
eight-device, availability-robustness, or separately measured delay objectives.
Whether the overall POC is formally revised to temperature-only or retains the
original objective as a distinct later phase remains an unresolved sponsor
decision; this plan does not make that decision.

---

## 4) Experiment Scope And Phases

### Phase 0 - Setup And Lock Assumptions
Objective: freeze definitions, source precedence, metrics, and state-machine semantics.

### Phase 1 - Temperature Transformation Core
Objective: transform raw telemetry into aligned minute snapshots with quality metadata.

The aligned data, source inventory, producer run record, and independent
validation receipt are in `artifacts/phase1_operational/`. General reader-facing
statistics are in `artifacts/phase1_outputs/`. Shared monitoring preparation
derives the Phase 3A threshold from the aligned output.

### Phase 2 - Deterministic Temperature Sensor Monitoring
Implemented: the deterministic local-deviation monitor is maintained for the
matched stable-cohort run as well as the separate historical full-data workflow.

Two Phase 2 results are distinguished:
1. **Existing full-data Phase 2 result:** retained as historical evidence of the availability-aware implementation.
2. **Matched Phase 3A Phase 2 baseline:** the existing Phase 2 engine was run on the six approved sensors and locked 19,984-bucket continuous interval using the Phase 3A-specific P90. This is the current comparator used for FMIC/SMIC.

### Phase 3A - Stable-Cohort Temperature Clustering Extension
Objective: measure weighting and clustering effects separately while preserving monitoring correctness under matched inputs and accounting.

Implemented sequence and maintained requirements:
1. The Phase 3A input contract is validated and the P90 is derived by shared
   monitoring preparation.
2. The matched stable-cohort Phase 2 baseline is published with an independent
   validation receipt.
3. Availability-only branches and oversized production traces are excluded
   from the Phase 3A primary workflow.
4. Source-aligned history, normalization, partition quality, and greedy
   clustering are retained and independently tested.
5. FMIC and SMIC share the maintained monitoring architecture and have
   independent algorithm/correctness coverage.
6. Per-bucket Phase 2/C0 equivalence is validated before interpreting C0/C1/C2
   and clustered configurations.
7. The three controls and 38 clustered configurations are present in the
   current saved results; see §7.4.

**Recorded status:** US-3.23 revised Phase 2; US-3.24 established C0 equivalence; US-3.25/3.26 completed and hardened the controlled evaluation. Later workflow consolidation retained the scientific results. See §§7, 11, and 14.

### Phase 3B - Availability Robustness Extension (Optional)
Objective: if time and sponsor interest permit, evaluate the broader dataset with sensor departure/return, changing observed contributors, re-entry handling, changing coordinators, and availability-related communication attribution.

Phase 3B is not required for Phase 3A completion and must not delay FMIC/SMIC implementation for the stable cohort.

### Phase 4 - Validation And Packaging
Objective: consolidate compact metrics, selected cluster-event records, tuning results, correctness evidence, limitations, and stakeholder-ready outputs.

Interpretation rule: the completed clustering experiment remains
temperature-only. Multivariate monitoring is deferred so that clustering
effects are not confounded with a simultaneous change in dimensionality.

---

## 5) Phase 2 Monitoring Logic (Discussion View)

Per minute bucket:
1. Determine the online set from valid Phase 1 observations and compare it to the preceding bucket; availability detection costs no messages.
2. Compute the mean from current online readings, or record undefined global state when there are none.
3. Initialization and membership changes, including deferred causes, force synchronization and skip operational local-trigger evaluation.
4. Otherwise evaluate `abs(delta_v_i(t)) >= abs(threshold - synchronized_mean)` using entry references and equal allowances; any local trigger causes one synchronization.
5. Combine coinciding causes into at most one synchronization per bucket, preserving all causes with initialization then membership precedence.
6. A completed synchronization contacts only online sensors, counting N requests, N responses, and N threshold updates. Local-trigger messages are counted only when actually generated.
7. When all sensors are offline, send nothing, retain pending causes, and wait for observations to return; do not reuse a prior mean as the current observation.
8. Apply synchronized references/allowances starting next row. Retain the last verified root-known SAFE/VIOLATED state between synchronizations; being above threshold does not schedule another synchronization.

Consistency note:
1. Phase 2 uses local constraints as an operational sufficient-condition proxy for the DDS aggregate deviation bound.
2. The canonical production policy uses the fixed boundary convention defined in locked decisions.

Interpretation:
1. False alarms are acceptable trade-offs for safer coverage.
2. Communication naturally clusters near high-temperature periods.
3. Root-known-state correctness is checked against an independent offline oracle; same-minute synchronization-versus-violation metrics are separately labeled legacy diagnostics.

---

## 6) Implementation Specification

### 6.1 Required Phase 2 Inputs
1. `artifacts/phase1_operational/phase1_aligned_temperature.csv` and its successful, current Phase 1 producer evidence.
2. `config/project_config.yaml` and the derived monitoring preparation evidence.

Required columns in aligned Phase 1 input:
1. bucket_epoch.
2. bucket_time_utc.
3. per-sensor temperature columns (for example A_temperature through H_temperature).
4. For the Phase 3A matched population, use only A_temperature, C_temperature,
   D_temperature, E_temperature, F_temperature, and G_temperature to calculate
   the six-sensor mean used by monitoring preparation and the offline oracle.
5. `average_temperature_all_devices` is the separate Phase 1 general/full-data
   series, formed under Phase 1 availability rules. It is not the Phase 3A
   six-sensor mean or oracle.

### 6.2 Threshold Derivation
1. The existing full-data Phase 2 run retains its historical threshold provenance.
2. For Phase 3A, read `artifacts/phase1_operational/phase1_aligned_temperature.csv`
   and filter sensors A, C, D, E, F, and G over the locked interval.
3. Compute the six-sensor average for every one of the 19,984 complete,
   consecutive one-minute buckets. This is the Phase 3A observed global mean;
   do not substitute `average_temperature_all_devices`.
4. Compute the Phase 3A p90 programmatically from that experimental series.
5. The p90 is retrospective and dataset-specific: it is derived from the same
   six-sensor, 19,984-bucket population used for evaluation. It is an empirical
   experimental threshold, not an externally validated operating or equipment
   safety limit or independent calibration.
6. Shared monitoring preparation validates the cohort and records the derived
   threshold and provenance in downstream run evidence; it does not add a
   Phase 1 statistics row or hard-code the threshold in configuration.
7. The recorded full-precision result is `22.428666649999997 °C`; the run must
   use its computed full-precision value rather than a hard-coded approximation.
8. Matched Phase 2 and all Phase 3 configurations must use the same validated,
   full-precision derived P90.

### 6.3 State Initialization
1. Start with undefined global/per-sensor references and margins, no prior membership set, and initialization pending.
2. The first bucket's observed set establishes initial membership without fabricating departure/return events.
3. Leading buckets without readings remain undefined, pending, and message-free. Never borrow values from a later row.
4. At the first usable bucket, complete initialization: synchronize the observed mean and online per-sensor readings, with equal local allowances `abs(p90 - synchronized_mean)` and a verified root-known state (SAFE below p90, VIOLATED at or above).
5. Count N requests, N responses, and N threshold updates for the N online sensors, with zero local triggers. Record `event_initialization_performed` and `initialization_message_count`.
6. Newly synchronized references and margins become next-row entry state. Sensors absent from synchronization have undefined references/margins; returning sensors force synchronization before local evaluation.

### 6.4 Per-Row Deterministic State Machine
For each row t:
1. Read prior committed state into `entry_*`; determine current online sensors, departures, and returns from valid observations after Phase 1 freshness filtering.
2. Add membership changes and initialization to pending synchronization causes. A departure is the first missing bucket and a return is the first subsequent valid bucket.
3. If any forced cause is present, suppress operational local triggers and keep trigger bits/messages zero, but calculate local deviations and constraint comparisons against valid entry references for reporting. Complete synchronization only if at least one sensor is online; otherwise retain pending causes without traffic.
4. Without forced causes, compute signed deviations from entry references and trigger when `abs(deviation) >= allowance`. All triggering sensors produce their trigger messages and one synchronization.
5. At synchronization, set the exit global reference to the current observed mean, set online references/margins from current observations, and invalidate references/margins for excluded sensors.
6. Count request/response/update fanout using the online count, not the configured cohort size. All membership status detection is free.
7. Record all causes, primary reason, completed/pending status, and membership changes. Causes sharing one synchronization do not create duplicate traffic.
8. The actual label is `observed_global_average >= p90` for evaluable rows, otherwise undefined. Diagnostic predicted positive remains `event_resync_performed`, not a claim of threshold violation.
9. Carry new references/allowances into row t+1 without negative-margin scheduling. Zero allowance still triggers conservatively with `>=`, including unchanged readings in the next bucket. Root-known state is updated after this bucket's completed synchronization; the offline oracle never controls communication.

### 6.5 Row Invariants
For each exported row:
1. `entry_*` fields are the state used to evaluate the current row.
2. `observed_*` fields are the raw values for the current minute bucket.
3. `event_*` fields record outcomes produced during the current minute.
4. `exit_*` fields describe the state committed at the end of the row and carried into the next row.
5. `transition_summary` is an early-row audit field summarizing the row's event and exit-state transitions.
6. `distributed_constraint_state` is `VIOLATING` if any absolute observed sensor deviation meets/exceeds its entry local allowance, including reporting-only comparisons on forced rows. `FEASIBLE` requires complete comparison coverage with no violation; incomplete coverage is `NOT_EVALUABLE`, and no observations is `UNDEFINED`.
7. `centralized_constraint_state` remains the observed global p90 oracle; `event_resync_performed` records the independent operational synchronization action. The redundant `distributed_alert` alias is removed.
8. Validation checks the full unrounded trace and saved evidence against the original observations; decisions use unrounded inputs. The compact published event CSV is not the complete trace.

### 6.6 Required Phase 2 Output Schema
The current matched workflow publishes a full-precision per-bucket
`artifacts/phase2_outputs/phase2_matched_trace.csv`, compact synchronization
events in `artifacts/phase2_operational/phase2_events.csv`, a schema-versioned
`artifacts/phase2_outputs/phase2_summary.json`, and an independent receipt. The
summary links the trace by relative path, schema version, ordered columns, row
count, and SHA-256 of exact file bytes. The event CSV retains its existing
timestamps, causes, triggering sensors, entry and exit global references and
allowances, root/oracle states, and trigger, request, response, broadcast, and
total message counts. The trace records entry state used for the current minute,
its observed values and events, and exit state carried into the next minute;
the offline oracle is for evaluation and never influences distributed
decisions or traffic. The matched trace is not a Phase 3 input and is distinct
from the historical full-dataset signed-margin export. See
[Phase 2 output details](scripts/README_scripts.md#us-216-matched-phase-2-notebooks).

Implementation precedence rule for `event_resync_reason` when more than one cause is possible in the same row:
1. `initialization`
2. `sensor_membership_changed`
3. `local_constraint_violation`

Record every cause in `event_resync_causes`, including deferred membership events. Forced synchronization rows suppress local triggers. The legacy conditional `sensor_recovered_after_offline` path is replaced by detection of every departure/return.

### 6.7 Phase 2 Implementation Artifact
The current matched workflow uses `scripts/phase2_implement.ipynb` and the
import-safe `scripts/shared_monitoring_engine.py`. The former general-dataset
notebook is retained under `artifacts/phase2_archive/scripts/` for historical
reference. The list below records the earlier implementation layout:
1. scripts/build_phase2_temperature_sensors.ipynb (retired).
2. scripts/shared_monitoring_engine.py, the state machine used by the notebook and synthetic tests.
3. scripts/test_shared_monitoring.py, run with `python -m unittest scripts.test_shared_monitoring -v`.

The shared monitoring engine retains availability-aware behavior, but the
matched run validates the locked stable cohort and derives its P90. Run the
current implementation and independent test notebooks as described in
[Phase 2 usage](scripts/README_scripts.md#us-216-matched-phase-2-notebooks).
No alternate monitoring state machine is required.

The historical full-data `phase2_temperature_sensors.csv` and archived general-
dataset notebook are not the current matched Phase 2 evidence. The active
matched evidence is `artifacts/phase2_outputs/phase2_summary.json`,
`artifacts/phase2_outputs/phase2_matched_trace.csv`,
`artifacts/phase2_operational/phase2_events.csv`, and its independent
`artifacts/phase2_operational/phase2_validation.json` receipt.

### 6.8 Phase 3A Experiment Input Contract
Phase 3A uses the temperature streams as scalar node streams and preserves the same global temperature-threshold objective used by the matched Phase 2 run.

Before any Phase 3A monitoring or clustering occurs, validate:
1. selected sensors are exactly A, C, D, E, F, and G;
2. first bucket is `2022-02-24T18:50:00+00:00`;
3. last bucket is `2022-03-10T15:53:00+00:00`;
4. row count is exactly 19,984;
5. every selected sensor has a valid finite temperature in every bucket;
6. timestamps are unique, strictly increasing, and every adjacent timestamp differs by exactly 60 seconds;
7. shared monitoring preparation computes the full-precision Phase 3A P90 from this same cohort and interval and records its provenance.

Failure of any input-contract check stops the Phase 3A run. The implementation must not switch to dynamic availability handling as a fallback.

### 6.9 Phase 3A Source-Aligned Clustering Specification
Source-alignment checkpoints:
1. History initializes at zero and updates for each valid observation after the reference row using `h_i <- 0.5 * h_i + (v_i(t) - v_i(t_j))`. The synchronization-reference row does not create an artificial zero-deviation history update.
2. History uses signed change from the active synchronization reference, never prior-minute change.
3. On a synchronization row, update history against the reference active on row entry, use the resulting history for clustering, and then install the new reference for subsequent rows.
4. Histories persist across synchronization and are not reset.
5. Every Phase 3A clustering event contains the same six sensors. No online/offline eligibility logic is required in the primary path.
6. For scalar histories, normalize with `H = max_i |h_i|`; when `H > 0`, use `a_i = h_i / H`, preserving sign and leaving raw history unchanged.
7. If all six histories are zero, use the previously agreed singleton no-information fallback and mark it explicitly.
8. Cluster quality is `q(pi) = (1 / |pi|) * |sum(a_i)| + alpha * |pi|`; partition quality is `Q(Pi) = max q(pi)`.
9. Signed normalized histories are summed before the absolute value so cancellation remains possible.
10. Algorithm 1.4.1 remains the governing greedy procedure: begin with singleton clusters, select the current worst-quality cluster, merge with the partner producing minimum merged-cluster quality, retain candidate partitions, stop at two clusters for `n >= 2`, and choose the retained partition with minimum `Q`.
11. Existing deterministic project tie rules may remain unless a simpler source-consistent rule is explicitly approved later.
12. FMIC uses the absolute **first moment** of each sensor's post-initialization temperature readings: `W_i = |mu_i|`. The first moment is computed from the persistent discounted sum `S_i(m) = 0.5 * S_i(m-1) + v_i(m)` and `mu_i(m) = S_i(m) / m`, for `m >= 1`. The first synchronization row initializes references and is not counted as a post-initialization moment update. This moment state is distinct from the signed history used for clustering.
13. SMIC uses the source's conservative **second-moment** contribution: `W_i = |mu_i| + sqrt(((m-1)/m) * S2_i)`. Here `S2_i` is the **unnormalized** sum of squared deviations among the discounted observations, not sample or population variance. The implemented recurrence is `S2_i(m) = 0.25 * S2_i(m-1) + ((m-1)/m) * (v_i(m) - 0.5 * mu_i(m-1))^2` for `m >= 2`, with zero second moment after the first post-initialization reading. The source definition and recurrence are documented in Chapter §1.4 and Appendix 1 (printed pp. 22 and 24).
14. For six sensors, let `W = sum_i W_i`. When `W > 0`, normalized weight `w_i = 6 * W_i / W`, so `sum_i w_i = 6`. The node allowance is `delta(i) = w_i * delta(root)`; a cluster coordinator's allowance is the arithmetic mean of its member-node allowances. If **all** weights are zero, use `w_i = 1` for every sensor. This equal-weight fallback is an **explicit project policy**, not a claimed chapter formula. An individually zero-weight sensor retains zero weight when the total is positive.
15. Keep the first and second moments persistent across ordinary root synchronization; changing the sensor reference does not reset either moment. Formula-level tests must verify discounted moments, history, normalization, clustering, weights, node/coordinator allowances, and zero-weight behavior against hand calculations.

### 6.10 Phase 3A Monitoring Lifecycle And Simplification
1. Phase 3A has a fixed six-sensor cohort and complete observations on every row. Departure, return, changing eligible sets, zero-observation state, changing observed denominator, and membership-triggered synchronization do not exist in the primary execution path.
2. Re-clustering remains event-based: initialize at the first completed synchronization and re-cluster at later completed resynchronizations according to the monitoring algorithm, not on a timer.
3. Resulting partitions, coordinators, references, and allowances become active using the agreed next-row state timing.
4. Each cluster uses the existing deterministic coordinator-selection rule unless a later pivot story explicitly changes it. A singleton coordinates itself.
5. Cluster/coordinator information may travel with normal synchronization threshold updates; no duplicate standalone formation traffic is created unless the implementation actually transmits it.
6. Each completed root synchronization records the six-sensor global mean and its **root-known state**: safe if `mean < p90`, violated if `mean >= p90`. The root allowance is `abs(global_mean_at_sync - p90)`, so it is never negative. Equality with p90 is **violated** and gives zero allowance.
7. FMIC and SMIC use **two-sided threshold monitoring**. Their local and coordinator checks must ensure that a change from the last root-known safe/violated state cannot be missed. Node-level violations remain observable even if signed cluster cancellation makes a root check unnecessary. An already-violated mean does not by itself cause forced synchronization; do **not** import historical Phase 2's negative-margin forced-resynchronization rule (removed from Phase 2 by US-3.23).
8. If a coordinator check cannot establish that the root-known state remains valid, it escalates to the separate root component. A completed root synchronization recalculates the actual mean, records the state, recomputes moment-based allowances, and refreshes references and clusters for the next bucket. Cluster checks and root collections follow the shared FMIC/SMIC engine, but **their event times may differ** from Phase 2 and from each other.
9. The true global mean computed from all six readings is available for **offline evaluation only**, not for deciding whether online communication is triggered. Both false-safe and false-violated counts must be zero for the run to be marked `passed`; the correctness comparison is with the actual six-sensor threshold state, **not the Phase 2 synchronization schedule**.
10. Availability-aware branches already built may be retained for optional Phase 3B, but Phase 3A code should remove or isolate them so they do not complicate the primary path.

### 6.11 Phase 3A Production Output And Reproducibility
Normal Phase 3A output is compact and event-oriented.

Do not persist by default:
1. one sensor-history row per sensor per minute;
2. every rejected merge candidate;
3. every merge-partner score;
4. every intermediate partition and cluster quality for every synchronization and alpha;
5. exhaustive nested JSON for deterministic search paths;
6. availability fields that cannot occur in Phase 3A.

For selected clustering snapshots, retain at minimum:
1. event/synchronization identifier;
2. timestamp;
3. algorithm;
4. alpha;
5. raw histories used for clustering;
6. normalized histories;
7. selected partition;
8. selected partition quality;
9. cluster count;
10. coordinator assignments.

A detailed debug mode may emit deeper traces for synthetic cases or small samples, but it is off by default for full-data runs.

Reproducibility uses the aligned input, experiment configuration, derived threshold evidence, implementation, deterministic algorithms, independent tests, and compact outputs. Persisting every deterministic intermediate state is not required.

### 6.12 Phase 3A FMIC/SMIC Build Strategy
1. Implement FMIC first as the first complete Phase 3A clustering-monitoring algorithm.
2. Validate FMIC formula outputs and end-to-end behavior before SMIC results are interpreted.
3. Add SMIC through the same monitoring engine. Do not create a second monitoring architecture.
4. Shared behavior includes observations, history, normalization, clustering rules, synchronization **protocol and next-row timing convention** (but not necessarily identical synchronization event timestamps), coordinator behavior, communication counting, outputs, and common correctness tests.
5. The principal algorithm-specific difference is the source-defined weight/allowance calculation.

### 6.13 Phase 3A Alpha Policy
1. Alpha is a dataset-specific tuning parameter, not the primary research question.
2. Use `alpha=0.10` as an initial implementation value only.
3. Do not interpret the full alpha grid until synthetic validation and the revised Phase 2/C0 equivalence and control gates pass.
4. Evaluate the 19-value grid `0.05, 0.10, ..., 0.95` for both algorithms (38 runs), alongside the three alpha-independent controls.
5. Retain one compact result row per configuration with total and category-level messages, correctness in both directions, root synchronizations, and summary cluster metrics. Keep `alpha=0.10` as the prespecified reference; grid minima are exploratory in-sample results.
6. Do not persist the full internal merge-search path for every alpha.
7. Select or discuss a preferred alpha only among configurations that pass correctness tests.
8. Do not present the selected alpha as a universal optimum.

### 6.14 Phase 3A Synthetic Correctness Test Suite
The Phase 3A suite must document the setup, expected result, and failure interpretation for each case.

1. **History recurrence test:** hand-calculate history across multiple observations and synchronization intervals. Confirms signed deviation from the active reference, 0.5 discounting, persistence across synchronization, and reference replacement.
2. **Normalization test:** use positive, negative, zero, tied-maximum, and all-zero histories. Confirms signed scaling, raw-state preservation, and deterministic zero-history fallback.
3. **Clustering test:** hand-calculate `q`, `Q`, worst-cluster choice, partner choice, merge sequence, retained partitions, and final selected partition for a small sensor set.
4. **FMIC weight/allowance test:** hand-calculate first-moment weights, node allowances, and coordinator allowance.
5. **SMIC weight/allowance test:** hand-calculate first moment, second moment, conservative second-moment component, node allowances, and coordinator allowance.
6. **Safe cancellation test:** one node warms and another cools enough for the monitored global condition to remain safe. Local activity remains observable while unnecessary root escalation may be avoided.
7. **Unsafe partial-cancellation test:** cooling is insufficient; coordinator/root escalation must occur and a true global violation cannot be concealed.
8. **Boundary test:** values just below, exactly at, and just above every relevant node, coordinator, and global boundary follow the declared `<` versus `>=` convention.
9. **Communication accounting test:** a hand-counted 2–4 sensor example reproduces every trigger, request, response, coordinator escalation, synchronization request/response, and broadcast exactly.
10. Availability/offline tests are not Phase 3A gates. They may be retained for optional Phase 3B.

### 6.15 Phase 3B Optional Availability Robustness
Phase 3B may later exercise the broader availability-aware design using the full dataset. Candidate scope includes sensor departure/return, changing observed contributors, re-entry synchronization, retained history through outages, changing coordinators, zero-observation states, and availability-related traffic attribution.

No Phase 3B implementation, test, or output is required for Phase 3A completion. Existing availability-aware code and historical user stories may be reused if Phase 3B is approved later.

## 7) Metrics And Evaluation

### 7.1 Phase 2 Historical Metrics
Existing Phase 2 diagnostic definitions remain valid for the historical full-data run. Synchronization-based precision/recall remain operational diagnostics rather than measures of actual warning accuracy.

### 7.2 Phase 3A Correctness Outcome
For each Phase 3A algorithm/configuration:
1. actual global condition is evaluated from the six-sensor observed mean using the Phase 3A p90 and canonical boundary rule;
2. no selected-sensor observation is missing, so every Phase 3A bucket is globally evaluable;
3. cluster cancellation is acceptable only if it does not conceal a true global threshold violation;
4. correctness requires the **last root-known state after that bucket's
   protocol events** to agree with the actual global threshold state at every
   sampled bucket; count false-safe and false-violated states separately, and
   fail if either count is nonzero;
5. the actual six-sensor mean is evaluated offline for validation and must not silently trigger a communication event;
6. correctness test status is a gate for interpreting communication savings.

The original work statement (p. 6) also requests **“Detection delay compared to
centralized monitoring.”** A sampled transition is a SAFE-to-VIOLATED or
VIOLATED-to-SAFE change between consecutive oracle buckets. Root recognition is
the state after completing that bucket's protocol events, compared with a
centralized monitor receiving all six readings in that same bucket. Current
saved evidence establishes sampled-bucket root-known-state agreement; it does
not separately report an event-level delay distribution. Such a delay is
**not separately evaluated**. If separately derived from suitable replay
evidence in future work, define delay as
`max(0, root_recognition_bucket_index - oracle_transition_bucket_index)` for
each direction and report transition counts, bucket-edge/post-processing
convention, initialization, censoring, and non-detection. Zero sampled-bucket
mismatches are not a measurement of sub-minute latency. Physical/network
delivery delay is outside the present model.

### 7.3 Phase 3A Communication Metrics
Report actual transmission counts by category:
1. node/local-trigger messages;
2. cluster collection/check requests;
3. cluster collection/check responses;
4. coordinator-to-root escalation messages;
5. root synchronization requests;
6. synchronization responses;
7. synchronization broadcasts/constraint updates;
8. total messages.

Rules:
1. the **primary model** is six sensor nodes and a separate root component; coordinators are sensor members;
2. one message is one actual transmission between distinct nodes/components; **self-communication costs zero**;
3. requests and responses are separate messages, and an update delivered to each individual sensor counts as a separate transmission;
4. category totals reconcile exactly to total messages; bundles containing cluster membership or moment data do not create extra transmissions beyond their enclosing messages;
5. local computation and coordinator selection are not messages by themselves;
6. no membership-change message categories are required in Phase 3A because membership is fixed;
7. the chapter's alternative **root-as-sensor broadcast accounting** may be reported as a clearly labeled secondary comparison, never substituted for the primary actual-transmission total;
8. Phase 2, FMIC, and SMIC use the same transmission definition, even though their monitoring events and categories differ.

### 7.4 Phase 3A Comparison Metrics
For matched Phase 2, the controls, and FMIC/SMIC report at minimum:
1. total messages;
2. communication totals by relevant type;
3. communication reduction versus the matched Phase 2 baseline for FMIC/SMIC;
4. communication reduction versus a centralized six-sensor-every-minute baseline;
5. node/local violations;
6. coordinator checks and violations for clustered algorithms;
7. root/global synchronizations or escalations;
8. selected cluster count and cluster-size summary for FMIC/SMIC;
9. correctness-pass status.

The centralized Phase 3A sensor-message baseline is `19,984 * 6 = 119,904` one-way sensor transmissions if defined as one transmission per sensor per minute. Any alternative centralized counting convention must be named explicitly and applied consistently.

#### Current Phase 3A Controlled Results

The following saved-results comparison is the current primary result. The
matched Phase 2 and C0 totals and root synchronization count agree, and the
current C0 equivalence evidence is checked per bucket, not inferred from equal
totals alone. The read-only saved-results loader passed for the run recorded
2026-11-12; the Phase 3 independent receipt records 170 passing tests, and the
matched Phase 2 receipt records 49. The current Phase 3 result file contains
three controls and all 38 FMIC/SMIC alpha rows; all report passed sampled-state
correctness and zero false-safe/false-violated buckets. Each configuration
records 1,999 globally violated sampled buckets.

| Configuration | Messages | Root synchronizations (incl. initialization) | Change vs revised Phase 2/C0 (9,159) | Conditional change vs weighted singleton | Change vs centralized reference (119,904) |
|---|---:|---:|---:|---:|---:|
| Revised Phase 2 / C0, equal allowances | 9,159 | 467 | 0.00% | — | 92.36% fewer |
| C1, FMIC weighting only | 8,964 | 457 | 2.13% fewer | — | 92.52% fewer |
| C2, SMIC weighting only | 8,962 | 457 | 2.15% fewer | — | 92.53% fewer |
| Full FMIC, alpha 0.10 (prespecified) | 11,922 | 293 | 30.17% more | 33.00% more vs C1 | 90.06% fewer |
| Full SMIC, alpha 0.10 (prespecified) | 11,902 | 293 | 29.95% more | 32.81% more vs C2 | 90.07% fewer |
| Full FMIC, alpha 0.65 (exploratory grid minimum) | 8,722 | 436 | 4.77% fewer | 2.70% fewer vs C1 | 92.73% fewer |
| Full SMIC, alpha 0.65 (exploratory grid minimum) | 8,720 | 436 | 4.79% fewer | 2.70% fewer vs C2 | 92.73% fewer |

Percentages are recomputed from saved message totals using
`100 * (1 - M(configuration) / M(reference))`; positive values mean fewer
messages and negative values mean more. The centralized reference is only one
transmission per sensor per minute under the stated simplified convention, not
end-to-end deployed-network cost.

The controls show modest weighting-only differences under a shared singleton
protocol. At alpha 0.10, full FMIC/SMIC use more total messages than their
corresponding weighted singleton controls despite fewer root synchronizations.
At alpha 0.65, the additional reduction relative to C1/C2 is approximately
2.70% for each method. This is conditional on the tested weighting, data, and
grid; weighting and clustering effects may interact and are not additive or
generally causal.

At alpha 0.65, both methods use a full-singleton partition at 354 of 436
root-synchronization events, or **81.19266055045871%** (including
initialization). This is an event share, not a share of the 19,984 observation
buckets. The grid minimum is exploratory and in-sample, not a universal or
out-of-sample optimum. Alpha response is irregular; no statistical significance
or population-level superiority is established. FMIC/SMIC's small observed
differences do not establish general algorithmic superiority.

Actual transmitted-message categories for the seven displayed configurations
are:

| Configuration | Sensor trigger | Cluster-check requests | Cluster-check responses | Coordinator-to-root escalations | Root-sync requests | Root-sync responses | Root state updates | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| C0 | 0 | 0 | 0 | 753 | 2,802 | 2,802 | 2,802 | 9,159 |
| C1 | 0 | 0 | 0 | 738 | 2,742 | 2,742 | 2,742 | 8,964 |
| C2 | 0 | 0 | 0 | 736 | 2,742 | 2,742 | 2,742 | 8,962 |
| FMIC, alpha 0.10 | 2,564 | 1,832 | 1,832 | 420 | 1,758 | 1,758 | 1,758 | 11,922 |
| SMIC, alpha 0.10 | 2,556 | 1,826 | 1,826 | 420 | 1,758 | 1,758 | 1,758 | 11,902 |
| FMIC, alpha 0.65 | 70 | 61 | 61 | 682 | 2,616 | 2,616 | 2,616 | 8,722 |
| SMIC, alpha 0.65 | 70 | 61 | 61 | 680 | 2,616 | 2,616 | 2,616 | 8,720 |

In C0/C1/C2, a triggering sensor is the coordinator of its singleton cluster;
its direct alert is counted once as a coordinator-to-root transmission, not as
an additional sensor-trigger message. Operation counts are separate from
messages: coordinator checks are 753/738/736 for C0/C1/C2, 3,522/3,514 at
alpha 0.10, and 774/772 at alpha 0.65 (FMIC/SMIC). The alpha 0.10 runs include
2,889/2,880 consecutive repeated checks; alpha 0.65 includes 60 for each
method. A locally resolved check or repeated check is not automatically a
root synchronization avoided.

The same message totals reconcile by the three mutually exclusive pathways:

| Configuration | Within-cluster messages (share) | Coordinator-to-root messages (share) | Root-wide messages (share) |
|---|---:|---:|---:|
| C0 | 0 (0.00%) | 753 (8.22%) | 8,406 (91.78%) |
| C1 | 0 (0.00%) | 738 (8.23%) | 8,226 (91.77%) |
| C2 | 0 (0.00%) | 736 (8.21%) | 8,226 (91.79%) |
| FMIC, alpha 0.10 | 6,228 (52.24%) | 420 (3.52%) | 5,274 (44.24%) |
| SMIC, alpha 0.10 | 6,208 (52.16%) | 420 (3.53%) | 5,274 (44.31%) |
| FMIC, alpha 0.65 | 192 (2.20%) | 682 (7.82%) | 7,848 (89.98%) |
| SMIC, alpha 0.65 | 192 (2.20%) | 680 (7.80%) | 7,848 (90.00%) |

The protocol is an offline deterministic simulation assuming a complete stable
cohort, accurate readings and timestamps, fixed 60-second sampling, and
reliable message delivery. Counts do not measure bytes, physical hops,
bandwidth, queuing, latency, energy, device/network failure, or threshold
excursions between sampled buckets. The P90 is selected retrospectively from
the evaluation series. Conclusions apply only to this one dataset, cohort,
interval, empirical threshold, protocol model, and tested alpha grid.

#### Controlled comparison and equivalence

The revised two-sided Phase 2 baseline uses equal node allowances. C0 uses
equal allowances and six fixed singleton clusters; C1 and C2 use, respectively,
FMIC and SMIC weighting with the same singleton partition. Full FMIC and SMIC
use their respective weighting and alpha-selected clusters. Compare C0 to C1/C2
to assess weighting, and C1 to full FMIC or C2 to full SMIC to assess
clustering conditional on the weighting method. Effects can interact and
must not be represented as automatically additive.

Before interpreting controls or alpha results, independently execute Phase 2
and C0 and require per-bucket agreement of trigger sensors, synchronization
times, entry references and allowances, root-known states, and mapped message
counts. C0 must have no peer-check transmissions. With six sensors and a
separate root, both total `18 * synchronizations + genuine sensor alerts`,
including initialization. An unexplained mismatch fails the gate.

Report the seven transmission categories and their mutually exclusive
within-cluster, coordinator-to-root, and root-wide pathway counts and shares.
Report locally resolved and escalating checks as operations, with cluster-size
and adjacent-bucket repeated-check breakdowns. A locally resolved check is not
automatically an avoided root synchronization; use independently executed
singleton controls for comparisons. Do not silently suppress repeated checks
or alter zero-allowance `>=` behavior without a separately validated design.
The metric is transmission count, not bytes, energy, hops, or latency.

### 7.5 Alpha Tuning Metrics
The revised evaluation requires the 38 clustered method/alpha combinations
and three alpha-independent controls, after correctness and equivalence gates.
The clustered table contains:
- algorithm and alpha;
- total messages and separate transmission category totals;
- false-safe count, false-violated count, and correctness-pass status;
- root synchronizations and compact cluster count/size information;
- reduction against the revised matched Phase 2 baseline.

Use only a complete correctness-passing grid when describing minimum-message
alphas, acknowledge ties, and distinguish the prespecified 0.10 reference from
exploratory in-sample minima. This is dataset-specific, not a universal ranking.
Do not require full merge traces or per-alpha forensic state.

### 7.6 Phase 3B Metrics (Optional)
If Phase 3B is later approved, availability-specific metrics and cause attribution may be reintroduced. They are not Phase 3A acceptance requirements and must not be mixed into the stable-cohort primary result.

---

## 8) Quality Gates And Acceptance

### 8.1 Transformation Gates (Phase 1)
Existing Phase 1 **quality-gate thresholds and temperature aggregation rules** remain unchanged. Source-file discovery was corrected to exclude `temperature_raw.csv`, an aggregate CSV inadvertently mixed with raw files. The recorded duplicate-key rate changed from **50.050912%** (failing the 0.5% gate) to **0.101823%** (passing). This corrected the input list, not the monitoring formulas or gate. See the [historical run records](project_history.md#transformation-run-records).

### 8.2 Phase 3A Input And Threshold Gates
Before matched Phase 2 or clustered runs:
1. sensors are exactly A, C, D, E, F, and G;
2. approved timestamps match the locked interval;
3. exactly 19,984 buckets are present;
4. both interval endpoints are inclusive and every adjacent timestamp differs by exactly 60 seconds;
5. every selected sensor has a valid finite value in every bucket;
6. no imputation is present;
7. the Phase 3A p90 is computed programmatically from the six-sensor mean by shared preparation and recorded in downstream evidence;
8. all Phase 3A algorithms use the same validated full-precision threshold value.

### 8.3 Matched Phase 2 Baseline Gate
1. Reuse the existing Phase 2 engine.
2. Run only the approved cohort/interval with the Phase 3A p90.
3. Membership-change behavior must remain inactive for the entire run.
4. Communication totals reconcile.
5. Existing Phase 2 correctness checks relevant to stable operation pass.
6. This matched result, not the historical full-data Phase 2 total, is the comparator for FMIC/SMIC.

### 8.4 Phase 3A Clustering Gates
Phase 3A may proceed to final comparison only when:
1. source-aligned history and normalization tests pass;
2. partition-quality and greedy-merge tests match hand calculations;
3. FMIC passes formula-level and end-to-end correctness tests before SMIC is interpreted;
4. SMIC independently passes its formula-level and end-to-end correctness tests;
5. no synthetic cancellation test hides a crossing in **either** direction: false-safe and false-violated states are both disallowed;
6. tests cover below, exactly at, and above each relevant boundary, including the zero-allowance state;
7. communication categories reconcile exactly to total messages;
8. production output excludes unnecessary full-run audit traces and remains manageable;
9. FMIC and SMIC use the same monitoring architecture except for the intended moment and weight/allowance calculations; their root synchronization timestamps need not match;
10. both directions of monitoring correctness agree with offline six-sensor truth, never with an assumed Phase 2 event schedule;
11. independent validation, Phase 2/C0 per-bucket equivalence, and control correctness pass before interpreting the revised sweep; only a complete passing grid is eligible for exploratory minima.

### 8.5 Phase 3B Gate (Optional)
No Phase 3B gate blocks Phase 3A completion. Phase 3B begins only after separate approval and may reuse the earlier availability-aware requirements as a starting point.

---

## 9) Verification Checklist

### 9.1 Phase 2 Historical Implementation
1. Existing full-data Phase 2 artifacts remain preserved.
2. Existing state-machine and communication validation remain part of project history.
3. Historical availability-aware behavior is not used as the primary Phase 3A comparator.

### 9.2 Phase 3A Experiment Setup
1. Locked cohort is A, C, D, E, F, G.
2. Locked interval is `2022-02-24T18:50:00+00:00` through `2022-03-10T15:53:00+00:00`.
3. Row count is 19,984.
4. Complete observations are verified for all six sensors on every row.
5. Phase 3A p90 is calculated from this exact population and recorded in downstream preparation evidence.
6. The `phase3a_experiment` section of `config/project_config.yaml` records the locked cohort, interval, expected row count, and threshold source.

### 9.3 Matched Phase 2 Baseline
1. Existing Phase 2 code is reused.
2. It reads the Phase 3A cohort/interval and p90.
3. No membership transition occurs.
4. Stable-run communication totals reconcile.
5. The output is clearly identified as the Phase 3A matched Phase 2 comparator.

### 9.4 Phase 3A Clustering Foundation
1. History updates use the active synchronization reference and retain sign.
2. History survives synchronization and uses the new reference afterward.
3. Normalization is signed, non-destructive, and calculated over all six stable sensors.
4. Initial all-zero history uses the explicit deterministic fallback.
5. Cluster quality and partition quality match the source formulas.
6. Greedy merging matches hand-calculated examples and stops/selects partitions as specified.
7. Availability-specific branches do not complicate the Phase 3A primary path.

### 9.5 Phase 3A FMIC/SMIC
**Recorded implementation and validation:** FMIC and SMIC share the current implementation script; US-3.21 and later validation covered correctness and communication accounting. The historical US-3.22 sweep and the revised controlled evaluation are distinct.

1. FMIC weights and allowances match hand calculations.
2. FMIC passes end-to-end tests before SMIC comparison.
3. SMIC first/second-moment calculations and allowances match hand calculations.
4. SMIC uses the shared monitoring architecture rather than a parallel implementation.
5. Node activity, coordinator checks, and root escalation are distinguishable.
6. Safe cancellation can reduce escalation without hiding global violation.
7. Unsafe partial cancellation escalates correctly.
8. Node/coordinator/global boundary tests pass.
9. Communication accounting matches the hand-counted synthetic example.

### 9.6 Phase 3A Outputs And Reproducibility
1. No full sensor-by-minute production history trace is required.
2. No exhaustive per-alpha merge-search JSON is required.
3. Clustering-event output retains raw/normalized histories, selected partition, quality, cluster count, coordinator, algorithm, alpha, timestamp, and event ID.
4. Current outputs use the `phase3_outputs/` and `phase3_operational/` layouts listed in §11; older algorithm-specific and US-3.22 names identify historical evidence.
5. Debug traces are opt-in and small.
6. The run can be reproduced from source data, config, derived threshold evidence, implementation, tests, and compact outputs.

### 9.7 Phase 3B (Optional)
1. Phase 3B requirements are not evaluated as part of Phase 3A completion.
2. If later approved, the earlier availability-aware stories may be reviewed and revised before reuse rather than assumed to remain automatically authoritative.

---

## 10) Recorded Sensitivity And Revalidation Criteria

### 10.1 Phase 2 Sensitivity
The historical Phase 2 sensitivity work remains available for reference but is not a prerequisite for the Phase 3A matched comparison unless a specific issue requires rerunning it.

### 10.2 Recorded Phase 3A Alpha Sweep
The current saved evaluation contains the completed coarse grid for **both**
FMIC and SMIC (19 values each, 38 runs):

`0.05, 0.10, 0.15, ..., 0.95`

The saved results retain compact evidence for each algorithm/alpha:
1. algorithm and alpha;
2. total messages and message-category counts;
3. false-safe count, false-violated count, and correctness-pass status;
4. root synchronizations and selected cluster/size summary;
5. reduction against the revised matched Phase 2 baseline.

Do not rerun this grid as part of the current documentation reconciliation.
Repeat it only after an approved scientific change to the input population,
configuration, or algorithm, with fresh independent validation and provenance.

Interpretation:
1. alpha is a tuning parameter, not the primary research question;
2. `alpha=0.10` is an initial implementation value, not a claimed optimum;
3. only correctness-passing configurations may be considered;
4. do not require a finer sweep unless the team later decides it adds value;
5. do not preserve full internal search traces for every alpha.

### 10.3 Current Phase 3A Primary Comparison
The current matched comparison uses the same cohort, interval, threshold,
observations, boundary convention, and counting rules: revised Phase 2, the
C0/C1/C2 singleton controls, and full FMIC/SMIC. Apply the controlled contrasts
in §7.4 rather than attributing the entire Phase 2 difference to clustering.
The current table is the primary result; historical US-3.22 figures are kept
only in §14.

### 10.4 Phase 3B Availability Robustness (Optional)
No availability sensitivity or attribution run is required for Phase 3A. If Phase 3B is approved later, define its experiment separately rather than treating it as a hidden extension of Phase 3A.

---

## 11) Deliverables

### Code And Execution
1. `scripts/phase1_implement.ipynb`, `scripts/phase1_test.ipynb`, and `scripts/phase1_analyze.ipynb` — transformation, independent testing, and saved analysis.
2. `scripts/phase2_implement.ipynb`, `scripts/phase2_test.ipynb`, `scripts/phase2_analyze.ipynb`, and `scripts/shared_monitoring_engine.py` — matched Phase 2 production, independent testing, saved analysis, and shared preparation.
3. `scripts/phase3_implement.py` — import-safe Phase 3 algorithms, revised production, isolated runtime equivalence, and read-only replays.
4. `scripts/phase3_test.py` — independent behavioral, saved-output, and fresh-process verification; Phase 1/2 suites remain independently owned dependencies.
5. `scripts/phase3_analyze.ipynb` — existing saved-result analysis, inline charts, and Markdown interpretation, with no production execution.

### Data And Result Artifacts
Current artifacts are intentionally compact:
1. `artifacts/phase1_operational/phase1_aligned_temperature.csv`, its producer record and validation receipt;
2. the Phase 3A experiment settings in `config/project_config.yaml` and derived preparation evidence;
3. `artifacts/phase2_outputs/phase2_summary.json`, `artifacts/phase2_outputs/phase2_matched_trace.csv`, `artifacts/phase2_operational/phase2_events.csv`, and the separate Phase 2 validation receipt;
4. `artifacts/phase3_outputs/phase3_results.csv`, `phase3_cluster_sizes.csv`, `phase3_snapshots.csv`, and `phase3_summary.json`;
5. `artifacts/phase3_operational/phase3_run.json`, `phase3_equivalence_events.csv`, and the separate `phase3_validation.json`.

The [artifact inventory](artifacts/README_artifacts.md) describes provenance,
historical references, and the complete current layout.

Detailed debug traces are optional and are not produced by default. Avoid duplicate summary files unless they provide a clear human-use case.

### Documentation
1. This project plan for current requirements.
2. [Project history](project_history.md) for the sponsor-approved pivot, decisions, and milestone-by-milestone context.
3. Existing user stories retained as historical records rather than rewritten retroactively.
4. [Current run instructions](scripts/README_scripts.md) for preparation, the matched baseline, and FMIC/SMIC.
5. Metrics interpretation notes that clearly distinguish Phase 3A stable-node conclusions from optional Phase 3B availability robustness.
6. Source-alignment notes referencing the definitive chapter and documenting any explicit project adaptations.
7. Focused correctness-test results before communication-savings claims.

---

## 12) Limitations, Major Risks, And Optional Follow-On Research

1. **Risk: the stable cohort is accidentally filtered incorrectly.**  
Mitigation: enforce the Phase 3A input contract on sensor IDs, inclusive endpoints, exact 19,984-row count, exact 60-second timestamp spacing, and complete finite observations before any monitoring begins.

2. **Risk: the wrong threshold population is used.**  
Mitigation: compute the Phase 3A p90 programmatically from the approved six-sensor interval in shared monitoring preparation and require matched Phase 2 and Phase 3 configurations to use the same full-precision value.

3. **Risk: historical availability logic could be mistaken for Phase 3A behavior.**
Mitigation: the current Phase 3A path excludes those branches; availability robustness remains optional Phase 3B and is not inferred from the stable cohort.

4. **Risk: drift from the definitive chapter's mathematical methodology while simplifying.**  
Mitigation: simplify infrastructure and outputs, not the source-defined history, normalization, partition-quality, greedy-merge, FMIC, or SMIC mathematics; retain hand-calculated formula tests.

5. **Risk: signed cancellation hides a true global threshold violation.**  
Mitigation: require safe- and unsafe-cancellation synthetic tests, bidirectional crossing tests, and comparison to offline actual global state (not Phase 2 synchronization timestamps) before accepting communication savings.

6. **Risk: FMIC and SMIC become duplicate codebases.**  
Mitigation: require one shared monitoring architecture with algorithm-specific weight/allowance functions.

7. **Risk: alpha tuning expands back into a large research subproject.**  
Mitigation: keep the 19-value-per-algorithm grid compact and interpret it only after correctness, equivalence, and control gates pass; do not add an uncontrolled finer search.

8. **Risk: communication savings are overstated through incomplete counting.**  
Mitigation: count actual trigger, request, response, coordinator escalation, synchronization, and broadcast transmissions separately and reconcile exactly to totals.

9. **Risk: production artifacts again become too large to inspect.**  
Mitigation: prohibit full sensor-by-minute history traces and exhaustive merge-search records by default; retain compact event-level outputs and use debug traces only on small cases.

10. **Risk: reproducibility is confused with storing every intermediate state.**  
Mitigation: define reproducibility around source data, config, threshold provenance, deterministic code, tests, and compact outputs; recompute deterministic internals when needed.

11. **Risk: stable-cohort results are overgeneralized to intermittent sensors.**  
Mitigation: state explicitly that Phase 3A evaluates stable node participation; reserve online/offline robustness claims for optional Phase 3B.

12. **Risk: old and new user stories give AI-assisted coding contradictory instructions.**  
Mitigation: retain historical stories and point coding tasks to this current plan and the relevant later approved requirements.

### 12.1 Interpretation Limits

Phase 3A covers one deterministic dataset, cohort, interval, retrospective
threshold, fixed sampling cadence, and tested alpha grid. The full series is
used to select the empirical P90 and observed alpha minimum; neither is an
independent out-of-sample result. The work does not establish statistical
significance, multivariate correctness, availability robustness, physical
network performance, or correctness between sampled observations. The original
POC scope remains unresolved: the sponsor may formally revise it to
temperature-only or retain the eight-device multivariate objective as a
distinct later phase. No choice is made here.

### 12.2 Optional Follow-On Experiments (Not Phase 3A Acceptance)

The following are research questions and decision gates only. None authorizes
new code, runs, datasets, configuration, or numerical claims under this plan.
Each requires separate scope and approval before implementation.

| Follow-on question and purpose | Added assumptions | Key validation gate | Approval status |
|---|---|---|---|
| **Out-of-sample alpha validation:** select alpha on one contiguous calibration interval and evaluate it unchanged on a later non-overlapping interval. | A complete compatible cohort and enough observations exist; temporal leakage is prevented. If not, report the limitation. | Prespecified split, unchanged algorithms/alpha, fresh correctness oracle and comparable controls. | Not approved; not run. |
| **Threshold sensitivity:** compare this retrospective P90 with independently justified alternatives or a calibration/evaluation split. | Each alternative has an external rationale or independent calibration population. | Prespecify thresholds and rerun all comparators under identical population, message, and correctness rules. | Not approved; not run. |
| **Cohort/time-window robustness:** repeat on another complete cohort or stable interval. | Candidate population has complete observations and is declared a distinct research population. | Validate source freshness, cohort completeness, threshold provenance, controls, and result comparability before interpreting. | Not approved; not run. |
| **Phase 3B availability robustness:** assess departures, re-entry, denominator changes, coordinator changes, and related traffic. | Explicit online/offline and re-entry state, synchronization, coordinator, and accounting rules. | Independently validate state transitions, oracle correctness, and all message categories under the approved missingness policy. | Optional; not approved or run. |
| **Multivariate extension:** address the original eight-device environmental-vector objective. | Specify vector components/units, normalization, feasible-region function `f`, cohort/missingness policy, bound or norm, and an oracle before coding; do not stack unscaled variables or assume a Euclidean norm without justification. | Validate source applicability, dimensional assumptions, oracle labels, comparators, cancellation correctness, and full communication accounting. | Original objective remains unresolved and not demonstrated; extension not approved or run. |
| **Network realism:** consider physical message sizes, latency, hops, delivery faults, or energy only if separately needed. | Define a network model or measurement platform and its operating assumptions. | Validate the new physical measures independently; do not infer them from logical transmission counts. | Not approved; not run. |

Phase 3B availability work remains distinct from the multivariate objective.
Alternative thresholds, temporal validation, additional populations, and
network realism likewise remain separate from Phase 3A acceptance.

---

## 13) Implementation Status And Revalidation Checklist

### Phase 1 / Threshold Implementation
1. Full aligned Phase 1 artifact exists and remains unchanged by the pivot.
2. Stable cohort and interval are locked: A, C, D, E, F, G; 2022-02-24T18:50:00+00:00 through 2022-03-10T15:53:00+00:00.
3. Exactly 19,984 complete, consecutive one-minute Phase 3A buckets are verified, with both endpoints inclusive and no timestamp gaps.
4. Shared preparation computes the full-precision cohort P90 and records its input and producer provenance in downstream evidence.

### Matched Phase 2 Implementation
1. Existing Phase 2 implementation runs on the Phase 3A subset without code duplication.
2. It reads the Phase 3A p90.
3. Membership-change behavior never activates.
4. Communication totals reconcile.
5. Result is labeled as the matched Phase 3A Phase 2 baseline.

### Phase 3A Clustering Foundation
1. Existing history, normalization, cluster-quality, and greedy-merge logic is revalidated against hand calculations.
2. Availability-only complexity is removed or isolated from the Phase 3A execution path.
3. Production output no longer writes the full sensor-by-minute history trace or exhaustive merge-search records.
4. Compact clustering-event output is defined and manageable.
5. Debug tracing is opt-in.

### FMIC Implementation And Validation
1. First-moment weights and allowances have direct tests.
2. Coordinator allowance matches the source rule.
3. FMIC passes safe/unsafe cancellation, boundary, and communication tests.
4. FMIC runs end-to-end on the Phase 3A data at the baseline alpha.

### SMIC Implementation And Validation
1. First- and second-moment calculations have direct tests.
2. SMIC reuses the FMIC monitoring architecture.
3. SMIC passes the same end-to-end correctness gates with only intended algorithm-specific differences.

### Final Phase 3A Comparison Recorded
US-3.21 and the historical US-3.22 sweep are point-in-time records. The
revised current comparison and its independent gates are summarized in §7.4
and bound to the current receipt and run manifest.

1. FMIC and SMIC pass the US-3.21 comprehensive correctness gate.
2. Compact coarse alpha tuning is complete.
3. Preferred configurations are selected only from correctness-passing runs.
4. Matched Phase 2, FMIC, and SMIC use identical Phase 3A cohort, interval, threshold, observations, and counting conventions.
5. Communication totals and reduction calculations reconcile.
6. Final outputs are small enough for direct human review.
7. Reporting clearly states that Phase 3A does not test intermittent sensor availability.

### Phase 3B Status
Phase 3B is optional and not required for the above checklist. If approved later, define its scope and acceptance criteria separately before implementation.

---

## 14) Historical Implementation Status And Results

This section preserves point-in-time implementation evidence and results; it
does not define the current primary comparison. See current controlled results
in §7.4 and the [project history](project_history.md) for milestone context.
Work through US-3.22 was recorded on 2026-11-03; US-3.23 and later decisions
are described in their dated records below.

| User story | Historical story objective | Status at recorded checkpoint |
|---|---|---|
| US-3.16 | Simplify Phase 3 for the fixed six-sensor cohort; retain signed history and clustering | Implemented and reviewed |
| US-3.17 | Lock and validate the exact input cohort, interval, and 19,984 complete minute buckets | Implemented and reviewed |
| US-3.18 | Calculate the authoritative cohort-specific p90 and matched Phase 2 baseline | Implemented and reviewed |
| US-3.19 | Implement FMIC, including first-moment weights, two-sided threshold checks, and transparent messages | Implemented and reviewed |
| US-3.20 | Add SMIC's second moment to the shared monitoring engine and confirm FMIC regression behavior | Implemented and reviewed |
| US-3.21 | Comprehensive synthetic and mathematical validation across both algorithms | Implemented and passed; 91 tests |
| US-3.22 | Required 19-alpha sensitivity sweep for each algorithm and final matched evaluation | Implemented and passed; 38 full-length runs |
| US-3.23 | Two-sided equal-allowance Phase 2 policy and separately named matched baseline | Implemented and passed; 103 regression tests |

### 14.1 Historical US-3.22 comparison — different Phase 2 policy; not causal attribution

This historical comparison uses sensors A, C, D, E, F, G; the
**19,984-bucket** inclusive interval; full-precision p90 of
**22.428666649999997 °C**; the same global boundary convention; and
`alpha=0.10` for FMIC/SMIC. Its then-existing Phase 2 policy, weighting, and
protocol differed. The old 38,087-message denominator and reported percentages
are preserved as historical records only; they are not current reductions or
causal estimates of clustering.

| Metric | Historical Phase 2 policy | FMIC | SMIC |
|---|---:|---:|---:|
| Total messages | 38,087 | 11,922 | 11,902 |
| Root synchronizations | 2,107 | 293 | 293 |
| Actual globally violated minutes | 1,999 | 1,999 | 1,999 |
| Reported correctness status | Passed | Passed | Passed |
| Reported false-safe / false-violated states | See baseline correctness fields | 0 / 0 | 0 / 0 |
| Historical reported reduction vs then-existing Phase 2 | — | 68.70% | 68.75% |

At this one alpha, SMIC uses **20 fewer messages** than FMIC, about **0.17% of FMIC's total**. The difference is 8 node-trigger messages, 6 cluster-check requests, and 6 responses; root-message and coordinator-escalation totals are equal. This is a small dataset-specific difference, not evidence that one method is generally better. The centralized six-sensor-every-minute reference is **119,904** sensor transmissions. Phase 2, FMIC, and SMIC do **not** share identical root synchronization schedules.

### 14.2 Historical US-3.22 alpha sensitivity results

The 19 tested alpha values were run independently for each algorithm on the same approved cohort, interval, threshold, and 19,984 buckets. All 38 runs had zero false-safe and false-violated states, `correctness_status=passed`, and exactly reconciled category/message totals. Both message-count curves are irregular across the tested grid.

| Metric at minimum observed alpha | FMIC | SMIC |
|---|---:|---:|
| Minimum observed alpha | 0.65 | 0.65 |
| Total messages | 8,722 | 8,720 |
| Root synchronizations, including initialization | 436 | 436 |
| Mean clusters per synchronization event, including initialization | 5.8005 | 5.8005 |
| Mean cluster size across all synchronization clusters | 1.0344 | 1.0344 |
| Historical reported reduction vs then-existing Phase 2 policy | 77.10% | 77.11% |
| Reduction vs. 119,904 centralized transmissions | 92.73% | 92.73% |

The 0.65 values are minimum observed on this single dataset and tested grid, not theoretically optimal settings or out-of-sample results. At 0.65 SMIC's two-message advantage comes from two fewer coordinator-to-root escalations. Cluster-size mean is total sensor memberships across all selected partitions at synchronization events divided by total clusters; the initialization partition is included for every method and alpha. Mean cluster count is the arithmetic mean of per-event counts with initialization included.

### 14.3 Historical evidence at the US-3.22 checkpoint

- **Existing:** `phase1_average_statistics.csv` (`phase3a_stable_cohort` row), `phase3a_phase2_baseline.json`, `phase3a_fmic_events.csv`, `phase3a_fmic_summary.json`, `phase3a_smic_events.csv`, and `phase3a_smic_summary.json`. The FMIC and SMIC event files hold compact root synchronization and clustering records rather than full minute-by-minute sensor traces.
- **Existing:** Phase 3A notebook with a shared FMIC/SMIC monitoring engine and focused moment/protocol tests. Source chapter formulas and project-specific choices are distinguished in §§2, 6, and 7.
- **Completed:** `phase3a_validation_summary.json` records the test command, scenarios, source references, production replay results, and limitations for US-3.21.
- **Completed:** `phase3a_alpha_results.csv` (38 rows), `phase3a_alpha_events.csv` (14,829 synchronization snapshots), and `phase3a_comparison_summary.json`.
- **Completed:** `phase3a_messages_vs_alpha.png`, `phase3a_synchronizations_vs_alpha.png`, and `phase3a_clustering_vs_alpha.png`; all plots derive from the saved results table.
- **Optional, not part of Phase 3A acceptance:** Phase 3B intermittent-sensor experiments.

For the step-by-step explanation and subsequent corrections, see [project history](project_history.md).

### 14.4 US-3.23 revised Phase 2 baseline (2026-11-10)

The shared Phase 2 engine now uses `abs(threshold - synchronized_mean)` and
absolute local deviations, retaining a verified root-known SAFE/VIOLATED state.
Negative-margin scheduling is removed; membership, initialization, next-bucket
activation, and actual-transmission accounting are retained.

The approved 19,984-bucket matched run passed with **9,159 messages**:
753 triggers plus 2,802 requests, 2,802 responses, and 2,802 state updates.
There were **467 synchronizations**, zero membership changes, 1,999 truly
violated buckets, and **zero false-safe and false-violated states**.
The historical 38,087-message / 2,107-synchronization benchmark remains
unchanged. The aggregate policy difference is -28,928 messages and -1,640
synchronizations; no separate causal attribution is inferred from those totals.

The historical US-3.23 artifacts were `phase3a_phase2_two_sided_baseline.json` and
`phase3a_phase2_two_sided_events.csv`. The summary records the policy, commands,
input/config/code hashes, independent root-state correctness, historical
comparison, and before/after hashes for protected outputs. The notebook's
general full-data reports use the `phase2_two_sided_*` prefix.

Sections 14.1–14.2 retain the original Phase 2 denominator and its then-
reported percentages as historical experiment records only. US-3.23 did not
isolate weighting or coordinator/cluster
protocol differences; US-3.24–3.26 subsequently added the equivalence gate,
controlled comparisons, and validation described in §7.4. These results do not
evaluate intermittent availability or establish universal superiority.

### 14.5 Revised controlled evaluation

US-3.24 recorded per-bucket Phase 2/C0 equivalence across 19,984 buckets:
467 synchronizations, 753 alerts, 9,159 messages per implementation, zero
peer transmissions, and zero false-safe/false-violated states. US-3.25/3.26
recorded C0/C1/C2 totals of 9,159/8,964/8,962 messages and 467/457/457
synchronizations. All 38 clustered configurations and three controls passed
the recorded correctness and accounting checks. At the prespecified 0.10,
FMIC/SMIC used 11,922/11,902 messages; the exploratory grid minima were
8,722/8,720 at 0.65 on this dataset. The current primary interpretation is in
§7.4. Subsequent workflow consolidation preserved the scientific results. See
[changelog](CHANGELOG.md) and [current artifact documentation](artifacts/README_artifacts.md)
for provenance and validation.
