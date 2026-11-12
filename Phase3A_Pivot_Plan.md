# Phase 3A Pivot Plan
## Distributed Monitoring POC — Stable-Cohort FMIC/SMIC Experiment

**Status:** Sponsor-approved project pivot  
**Date:** 2026-11-01  
**Purpose:** Simplify Phase 3 so that the primary FMIC/SMIC experiment is methodologically defensible, computationally manageable, and understandable by a part-time product manager using AI-assisted coding.

**Implementation record updated:** 2026-11-03 — completed work through US-3.22 is documented in Section 22.

**Policy follow-up (2026-11-10):** US-3.23 revised Phase 2 to the two-sided
equal-allowance policy. Its separately named baseline and validation are recorded
in Section 22.12; US-3.22 results and denominators remain unchanged historical evidence.

---

## 1. Why This Pivot Is Being Made

The original Phase 3 implementation became substantially more complex than necessary for the core research question. The implementation added dynamic sensor availability, re-entry handling, changing eligible sets, extensive audit traces, exhaustive clustering-search records, and other state-management requirements before FMIC or SMIC had been implemented end-to-end.

This complexity produced artifacts that were difficult to inspect and manage. In particular, Phase 3 output grew to multiple gigabytes even though the validated Phase 2 output was less than 100 MB.

The project will therefore simplify the primary Phase 3 experiment while preserving the source-defined clustering methodology.

The primary research question remains:

> **Can source-aligned FMIC and SMIC clustering reduce communication relative to the Phase 2 distributed-monitoring approach while preserving correct monitoring of the global temperature threshold?**

The pivot is intended to keep implementation effort focused on that question.

---

## 2. Governing Rule During the Pivot

This document records the approved Phase 3A design decisions.

For the **primary Phase 3A experiment**, if this document conflicts with the existing `Phase_3_User_Stories.md` or the current `Distributed_Monitoring_POC_Project_Plan.md`, this pivot plan governs until those documents are updated.

The original Phase 3 user stories remain part of the project history and should not be rewritten retroactively. New user stories will be added to implement the approved pivot.

The definitive methodology source remains:

`140516editor Book Chapter (Last Version).pdf`  
*Clustering for Monitoring Distributed Data Streams*

The source chapter continues to govern the mathematical definitions for history, normalization, partition quality, greedy clustering, FMIC, SMIC, and source-comparable communication accounting.

---

## 3. Phase 3A and Phase 3B

Phase 3 is now divided into two conceptual tracks.

### Phase 3A — Primary Experiment

Phase 3A is the required project path.

It evaluates Phase 2, FMIC, and SMIC using a fixed set of continuously observed sensors over a continuous time interval with no missing selected-sensor observations.

This is the experiment that must be completed before any optional robustness work is considered.

### Phase 3B — Optional Availability Robustness Extension

Phase 3B is optional and is not part of the Phase 3A critical path.

It may later evaluate the algorithms using the broader dataset with sensors going online and offline, changing observed contributors, re-entry synchronization, changing coordinator assignments, and other availability-related behaviors.

The availability-aware work already implemented is not considered wasted, but it is no longer required before FMIC and SMIC can be implemented and evaluated.

---

## 4. Locked Phase 3A Experimental Cohort

The primary Phase 3A experiment will use the following six sensors:

- A
- C
- D
- E
- F
- G

Sensors B and H are excluded from the primary Phase 3A cohort.

The selected interval is:

- **Start:** `2022-02-24T18:50:00+00:00`
- **End:** `2022-03-10T15:53:00+00:00`
- **Expected one-minute buckets:** `19,984`

Every selected sensor has a valid observation in every included bucket.

The interval is strictly continuous at one-minute resolution: both endpoints are inclusive, and every adjacent timestamp must differ by exactly 60 seconds. With inclusive endpoints, 19,984 buckets span 19,983 elapsed minutes.

No sensor-value imputation is permitted.

The Phase 3A implementation must validate these conditions before running. Validation must include the expected cohort, inclusive interval endpoints, exact 19,984-bucket row count, complete selected-sensor observations, and exact 60-second spacing between every adjacent timestamp. If any requirement is not satisfied, the run should fail rather than fall back to dynamic availability handling.

---

## 5. Phase 1 Changes

The existing Phase 1 transformation logic remains unchanged.

Phase 1 will continue to produce the full aligned temperature dataset.

A small addition will be made to the Phase 1 statistics output so that `phase1_average_statistics.csv` includes a row representing the Phase 3A stable cohort and interval.

The Phase 3A threshold will be calculated from the six-sensor average over the approved Phase 3A interval.

The approximate p90 value identified during planning is:

`22.42866665 °C`

The implementation should calculate and record the value programmatically rather than rely on a manually entered approximation.

The new statistics row should have a clear series identifier such as:

`phase3a_stable_cohort`

The existing full-data Phase 1 statistics must be preserved.

---

## 6. Phase 2 Baseline for Phase 3A

The current Phase 2 monitoring implementation will be reused rather than rewritten.

A new matched Phase 2 run will be produced using exactly:

- sensors A, C, D, E, F, and G;
- the approved Phase 3A time interval;
- the Phase 3A-specific p90 threshold;
- the existing Phase 2 boundary and synchronization conventions.

Because every selected sensor is present on every included row, membership-change behavior should never activate in this run.

If membership-change behavior occurs, the stable-cohort input or filtering logic should be treated as incorrect.

The existing full-data Phase 2 output remains a valid historical artifact, but it will not be used as the primary comparator for Phase 3A.

The required primary comparison is:

**Stable-cohort Phase 2 vs. Stable-cohort FMIC vs. Stable-cohort SMIC**

All three must use the same observations, timestamps, cohort, threshold, boundary convention, and communication-counting definitions.

---

## 7. Existing Phase 3 Work to Preserve

The project will pivot from the existing Phase 3 implementation rather than start over.

The source-aligned mathematical work already implemented through the current clustering foundation should be preserved unless testing shows that it is incorrect.

The following core behavior remains required:

1. persistent per-sensor history;
2. signed deviation from the active synchronization reference;
3. history retained across synchronization rather than reset;
4. signed normalization using the maximum history magnitude;
5. deterministic handling of the initial all-zero-history condition;
6. source-aligned cluster quality and partition quality;
7. signed cancellation within clusters;
8. source-aligned greedy merging and partition selection.

The mathematical core should not be simplified merely to reduce coding effort.

The implementation and output infrastructure surrounding that core may be simplified substantially.

---

## 8. Phase 3A Complexity to Remove

Phase 3A should remove implementation logic that exists only to support changing sensor availability.

The primary Phase 3A execution path does not need:

- sensor departure handling;
- sensor return or re-entry handling;
- changing eligible-sensor sets;
- offline-sensor history suspension;
- stale pre-return reference protection;
- zero-observation global states;
- changing observed denominators;
- membership-triggered synchronization;
- membership-related cause attribution;
- coordinator changes caused by sensor availability;
- deferred synchronization waiting for sensors to return.

These behaviors may remain relevant to optional Phase 3B, but they should not complicate the Phase 3A implementation.

A new user story will explicitly govern removal of unnecessary Phase 3A complexity rather than merely leaving unused branches in place.

---

## 9. History and Normalization Under Phase 3A

Phase 3A keeps the source-defined history rule.

For sensor `i`, with active synchronization reference `v_i(t_j)`, history is updated from valid observations as:

`h_i <- 0.5 * h_i + [v_i(t) - v_i(t_j)]`

The deviation remains signed.

History persists across synchronization events. Synchronization changes the reference used for future updates but does not reset accumulated history.

Because the Phase 3A cohort is stable, every clustering event uses the same six sensors.

For scalar temperature histories:

`H = max_i |h_i|`

and, when `H > 0`:

`a_i = h_i / H`

Normalization must preserve sign and must not overwrite raw accumulated history.

The initial all-zero-history condition remains a valid edge case and should use the previously agreed deterministic fallback.

---

## 10. Clustering Logic to Preserve

The current source-aligned clustering mathematics remains in scope.

For cluster `pi`:

`q(pi) = (1 / |pi|) * |sum(a_i)| + alpha * |pi|`

For partition `Pi`:

`Q(Pi) = max q(pi)`

The implementation must preserve signed cancellation by summing signed normalized histories before taking the absolute value.

The greedy merge procedure remains source-aligned:

1. begin with singleton clusters;
2. identify the current worst-quality cluster;
3. merge it with the partner producing the smallest merged-cluster quality;
4. retain candidate partitions;
5. stop at two clusters when applicable;
6. select the retained partition having minimum partition quality.

Existing deterministic project tie rules may remain unless a simpler source-consistent rule is explicitly approved later.

---

## 11. Production Output Simplification

Phase 3A production outputs should contain only information required to understand and reproduce the experiment.

The project will no longer require persistence of every deterministic intermediate calculation.

### Remove from normal full-data output

Do not persist:

- one sensor-history row for every sensor for every minute;
- every rejected merge candidate;
- every merge-partner score;
- every intermediate partition quality for every candidate;
- exhaustive JSON representations of the full clustering search path for every synchronization and alpha;
- detailed availability audit fields that cannot occur in Phase 3A.

### Retain at clustering events

At a minimum, retain:

- event/synchronization identifier;
- timestamp;
- algorithm;
- alpha;
- raw sensor histories used for clustering;
- normalized histories;
- selected partition;
- selected partition quality;
- cluster count;
- coordinator assignments.

Detailed traces may be generated in an explicit debug mode for synthetic tests or small samples, but they are not normal project deliverables.

---

## 12. FMIC and SMIC Implementation Strategy

FMIC will be implemented first as the first complete Phase 3A clustering-monitoring algorithm.

FMIC must use the source-defined first-moment weighting and allowance calculations.

After FMIC is validated end-to-end, SMIC will be added using the same monitoring architecture.

FMIC and SMIC must not become separate implementations of the monitoring lifecycle.

They should share:

- source observations;
- history handling;
- normalization;
- clustering;
- synchronization timing;
- coordinator behavior;
- communication accounting;
- output generation;
- correctness tests where the behavior is common.

The main algorithm-specific difference should be the weighting/allowance calculation.

SMIC adds the source-defined conservative second-moment component to the first-moment approach.

---

## 13. Alpha Policy

Alpha is treated as a clustering tuning parameter for this dataset, not as a primary research question or a generally transferable scientific result.

Initial implementation and correctness testing should use a single baseline value, such as:

`alpha = 0.10`

The full alpha sweep should occur only after FMIC and SMIC each operate correctly end-to-end.

A coarse sweep of:

`0.05, 0.10, 0.15, ..., 0.95`

may then be used to identify a reasonable dataset-specific setting.

The alpha tuning output should remain small. At minimum it needs:

- algorithm;
- alpha;
- total communication;
- correctness-pass status.

Additional compact metrics such as root synchronizations or cluster count may be retained if useful.

The project does not need to preserve the complete internal clustering search path for every alpha.

The selected alpha should not be presented as a universal optimum.

---

## 14. Communication Accounting

Transparent communication accounting remains required.

Phase 3A should separately count genuine transmission types needed to compare the methods, including as applicable:

- node/local-trigger messages;
- cluster collection/check requests;
- cluster collection/check responses;
- coordinator-to-root escalation messages;
- root synchronization requests;
- synchronization responses;
- synchronization broadcasts/constraint updates;
- total messages.

Requests and responses remain separate transmissions.

Message categories must reconcile to total communication.

Phase 3A does not require membership-change communication categories because membership does not change during the primary experiment.

---

## 15. Correctness Testing Philosophy

Correctness will be demonstrated primarily through focused synthetic and hand-calculated tests rather than by retaining every full-run intermediate state.

The required test suite should include, at minimum:

### History Test

Verify the history recurrence against hand calculations across multiple observations and synchronization intervals.

**Purpose:** confirm that history uses the active synchronization reference, preserves sign, discounts older history correctly, survives synchronization, and uses the new reference afterward.

### Normalization Test

Verify signed normalization against hand-calculated histories, including positive values, negative values, zeros, and the all-zero case.

**Purpose:** confirm that normalization scales histories without destroying direction or modifying raw history.

### Clustering Test

Use a small hand-calculated set of normalized histories and verify cluster quality, partition quality, greedy merge choices, retained candidates, and final selected partition.

**Purpose:** confirm that implementation matches the source clustering algorithm rather than merely producing plausible clusters.

### FMIC Weight and Allowance Test

Hand-calculate first-moment weights, node allowances, and coordinator allowances.

**Purpose:** establish formula-level agreement before communication results are interpreted.

### SMIC Weight and Allowance Test

Hand-calculate the required first moment, second moment, conservative second-moment component, and resulting allowances.

**Purpose:** prove that SMIC differs from FMIC only in the intended source-defined calculation.

### Safe Cancellation Test

Construct a case where one node warms and another cools enough that cluster cancellation keeps the monitored global condition safe.

**Expected behavior:** the local event is recognized, but unnecessary root escalation may be avoided.

### Unsafe Partial-Cancellation Test

Construct a case where cooling does not offset warming enough to preserve the global condition.

**Expected behavior:** coordinator/root escalation occurs and the global violation is not concealed.

### Boundary Test

Test values immediately below, exactly at, and immediately above node, coordinator, and global boundaries.

**Purpose:** prove consistent application of the declared `<` versus `>=` convention.

### Communication Accounting Test

Use a small 2–4 sensor example and manually count every expected transmission.

**Purpose:** prove that requests, responses, triggers, escalations, and broadcasts are neither omitted nor double-counted.

Availability/offline tests are not required for Phase 3A and may be retained for optional Phase 3B.

---

## 16. Reproducibility Standard

Phase 3A replaces exhaustive audit retention with a reproducibility requirement.

A researcher should be able to reproduce the reported results using:

- the original Phase 1 aligned data;
- the Phase 3A experiment configuration;
- the Phase 3A threshold statistics row;
- the implementation notebooks/code;
- the deterministic algorithm definitions;
- the focused correctness tests;
- the compact clustering-event and results artifacts.

The project does not need to permanently store every intermediate state that can be deterministically recomputed.

---

## 17. Target Phase 3A Artifacts

The normal Phase 3A deliverable set should remain small.

Target artifacts are:

1. `phase3a_experiment_config.json`
2. `phase3a_cluster_events.csv`
3. `phase3a_results.csv`
4. Phase 3A synthetic/unit-test results

The exact filenames may change during implementation if a simpler organization is justified, but the project should avoid unnecessary duplicate outputs.

`phase3a_results.csv` should be capable of supporting the primary Phase 2/FM​IC/SMIC comparison and compact alpha tuning results.

Detailed debug traces are optional and should not be produced by default.

---

## 18. Primary Final Comparison

The primary Phase 3A result will compare:

1. Stable-cohort Phase 2
2. Stable-cohort FMIC
3. Stable-cohort SMIC

All three must use:

- sensors A, C, D, E, F, and G;
- the approved 19,984-bucket continuous interval;
- the same Phase 3A p90 threshold;
- identical input observations;
- identical boundary conventions;
- consistent synchronization timing;
- consistent communication-counting rules.

The primary outcome is whether clustering reduces communication while preserving correct monitoring behavior.

---

## 19. Phase 3A Scope Limitation

Phase 3A evaluates FMIC and SMIC under stable node participation.

It does not establish how the algorithms perform when sensors repeatedly disappear and return.

That question is reserved for optional Phase 3B.

Final reporting should state this limitation explicitly rather than implying that Phase 3A represents all operational sensor-network conditions.

---

## 20. Documentation and User-Story Strategy

The project will not retroactively rewrite the existing Phase 3 user stories that drove the current implementation.

Instead:

1. this pivot plan records the approved redesign;
2. `Distributed_Monitoring_POC_Project_Plan.md` will be updated to incorporate Phase 3A and optional Phase 3B;
3. new user stories will be added after the existing sequence to implement the pivot;
4. those new stories will explicitly supersede conflicting prior requirements for the Phase 3A path.

The next planned implementation stories are expected to address, in sequence:

- simplifying the existing Phase 3 implementation for stable-cohort operation;
- establishing and validating the Phase 3A input contract;
- producing the matched stable-cohort Phase 2 baseline;
- implementing FMIC end-to-end;
- implementing SMIC through shared monitoring logic;
- validating Phase 3A with focused synthetic tests;
- tuning alpha and producing the final Phase 3A comparison.

The exact story numbering and acceptance criteria will be defined separately so that each coding task remains limited in scope and manageable for AI-assisted implementation.

---

## 21. Definition of Success for the Pivot

The Phase 3A pivot is successful when:

1. the primary experiment operates on the approved six-sensor stable interval;
2. the Phase 3A-specific p90 is reproducibly calculated and documented;
3. the matched Phase 2 baseline is rerun on the same experimental population;
4. unnecessary availability-related complexity is removed from the Phase 3A implementation path;
5. Phase 3 production outputs are small enough to inspect and manage directly;
6. source-aligned history, normalization, clustering, FMIC, and SMIC formulas pass focused correctness tests;
7. FMIC and SMIC use one shared monitoring architecture;
8. alpha is treated as dataset-specific tuning rather than the central research question;
9. communication accounting remains transparent and reconciled;
10. the final Phase 2/FM​IC/SMIC comparison is understandable without reconstructing gigabytes of intermediate state.

---

## 22. Implementation Record — Decisions and Completed Milestones Through US-3.22

**Recorded as of:** 2026-11-03  
**Status:** Work through US-3.22 has been implemented and reviewed. The US-3.21 correctness gate passed before the full alpha sweep; the sweep and final comparison passed validation.

This section describes what the project actually did after the original pivot was approved. Sections 1–21 above remain the approved plan and describe the intended approach. This section is the implementation history; where a later, documented implementation decision is more specific than the original plan, it explains the difference.

### 22.1 Main decisions made during implementation

**Focus the required experiment on six continuously reporting sensors.** We kept sensors **A, C, D, E, F, and G** and excluded B and H from Phase 3A. The selected period runs from **2022-02-24 18:50 UTC** through **2022-03-10 15:53 UTC**, inclusive. It contains exactly **19,984 one-minute observations** per selected sensor. This removes missing-data and sensor-return decisions from the main comparison. Testing changing sensor availability remains a possible Phase 3B activity, not a prerequisite.

**Keep the source mathematics while reducing software and output complexity.** We reused the existing history, normalization, and greedy clustering approach. We removed availability-driven paths from the normal Phase 3A work and stopped treating detailed per-minute histories and exhaustive merge records as required production outputs. Short synthetic tests and compact event records provide the evidence needed to understand the results.

**Use one matched set of experimental conditions.** Phase 2, FMIC, and SMIC use the same six sensors, timestamps, temperature readings, threshold, and global decision boundary: **safe when the mean is below p90; violated when the mean is at or above p90**. The p90 value is calculated from the selected cohort rather than borrowed from the broader eight-sensor data.

**Use consistent, explicit message counts.** For the primary comparison, the simulation uses **six sensor nodes and a separate root component**. Cluster coordinators are selected from the sensors. Messages to oneself cost zero; a request and its response count as two transmissions. We count local triggers, cluster requests, cluster responses, coordinator escalations, root requests, root responses, and root state updates separately. This network arrangement is a **documented project adaptation**: the chapter's own broadcast examples sometimes use a sensor as the root. A chapter-style count must not be substituted for the project's actual-transmission total.

**Monitor the threshold from both sides.** At each root synchronization, the root stores whether the global mean is currently safe or violated. The next monitoring allowance is based on the **absolute distance from that mean to the threshold**. A mean above p90 is not automatically a reason to synchronize again. The nodes and coordinators must detect changes that could cross the threshold in either direction and bring them to the root. At exactly p90, the state is violated and the allowance is zero. We did not copy Phase 2's negative-margin forced-synchronization schedule into FMIC or SMIC.

**Implement FMIC before SMIC, using one shared engine.** FMIC first established a working local-trigger, coordinator-check, root-update, and clustering lifecycle. SMIC then added the second-moment calculation and selected a different weight formula in that same engine. It did not introduce a separate coordinator or synchronization implementation.

**Run alpha sensitivity only after validation.** The initial production comparison used **alpha = 0.10**. After the US-3.21 validation gate passed, US-3.22 completed the 19-value end-to-end sweep for both methods. Any minimum is reported only as a dataset- and grid-specific observation, not as a universal optimum.

### 22.2 US-3.16 — Simplify Phase 3 for stable-cohort operation

**What was done**

1. We retained the existing Phase 3 clustering foundation rather than starting over. The same notebook now contains stable-cohort input preparation, persistent sensor histories, signed normalization, and deterministic cluster selection.
2. We narrowed the normal execution path to the fixed six-sensor set. Sensor departures, returns, changing denominators, and membership-based resynchronizations are not part of the Phase 3A simulation.
3. We preserved the signed history update: each minute contributes the difference between the current reading and that sensor's active synchronization reference, while earlier history is discounted by a factor of 0.5. History is **not reset** when a root synchronization occurs; the synchronization only changes the reference for later minutes.
4. We kept normalization by the largest absolute sensor history while preserving each history's sign, including a deterministic fallback for an all-zero history vector.
5. We kept the greedy clustering procedure: start with individual sensors, merge according to cluster quality, evaluate retained candidate partitions, and select the partition with the lowest maximum cluster quality. We retained deterministic rules so the same inputs produce the same clusters.
6. We reduced normal output to compact synchronization/clustering records instead of writing the full internal clustering search and every sensor's history on every minute. Detailed checks remain appropriate for short synthetic examples.

**Milestone achieved:** A simpler Phase 3A foundation that can be reused by both monitoring algorithms without changing the source-based clustering rules. This foundation is exercised by the subsequent FMIC and SMIC runs.

### 22.3 US-3.17 — Establish and validate the fixed experiment input

**What was done**

1. We locked the cohort to **A, C, D, E, F, G** and the inclusive time interval **2022-02-24 18:50 UTC–2022-03-10 15:53 UTC**.
2. We established a Phase 3A configuration file to record the selected sensors, input dataset, timestamps, expected row count, one-minute sampling interval, alpha, threshold source, and decision boundary.
3. We added input checks that reject missing or unexpected sensor columns, missing/nonfinite readings, duplicate or out-of-order timestamps, incorrect endpoints, and any gap other than exactly 60 seconds.
4. We made invalid input stop the run instead of quietly filling gaps or switching back to the changing-availability logic.
5. We fixed **alpha = 0.10** for initial implementation. The threshold was identified by its authoritative Phase 1 statistics row, rather than treating an approximate manually entered p90 as final.

**Milestone achieved:** A repeatable, validated input contract for **19,984 complete one-minute buckets** with no imputation. FMIC and SMIC use this same contract.

### 22.4 US-3.18 — Calculate the cohort-specific p90 and matched Phase 2 baseline

**What was done**

1. We extended the **production Phase 1 statistics calculation** to compute the average temperature of the six selected sensors at each of the 19,984 timestamps and then calculate that series' 90th percentile.
2. We added a separate `phase3a_stable_cohort` row to `phase1_average_statistics.csv`, preserving the preexisting full-data statistics. The authoritative threshold is **22.428666649999997 °C**. The original full-data p90, about **24.343381 °C**, is **not** the Phase 3A cutoff.
3. We linked the experiment configuration to this exact statistics row and made subsequent monitoring runs check that the configured threshold matches the recorded value.
4. We reused the existing Phase 2 monitoring method on the same six sensors, interval, and new p90. This is a new matched comparator, not a comparison to the earlier full-data/eight-sensor Phase 2 run.
5. We recorded the matched baseline in `phase3a_phase2_baseline.json`, including message totals, synchronization counts, global threshold violations, and the no-membership-change result.
6. During related Phase 1 quality-control work, we found that an aggregate file named `temperature_raw.csv` was being read along with source CSV files. The source-file discovery rule was changed to exclude this aggregate. The recorded duplicate-key rate then fell from **50.050912%** to **0.101823%**, below the **0.5%** quality gate. This was a data-input correction, **not a change to the FMIC or SMIC monitoring formulas**.

**Observed matched Phase 2 result**

| Measure | Value |
|---|---:|
| One-minute buckets evaluated | 19,984 |
| Total messages | 38,087 |
| Local trigger messages | 161 |
| Root requests | 12,642 |
| Root responses | 12,642 |
| Root updates/broadcasts | 12,642 |
| Resynchronizations | 2,107 |
| Minutes with global mean at or above p90 | 1,999 |
| Membership-change events | 0 |
| Centralized reference: 6 sensor messages each minute | 119,904 |

The message categories add up to **38,087**. The baseline reports a passed correctness check. The p90 and 19,984-row cohort are now the common basis for all subsequent Phase 3A comparisons.

**Milestone achieved:** A defensible, like-for-like Phase 2 comparison point with documented data and threshold provenance.

### 22.5 US-3.19 — Implement and review FMIC end to end

**What was done**

1. We implemented the **first-moment method** in the Phase 3 notebook and traced its mathematical definition to the original chapter PDF after discovering that some formulas were damaged in the extracted text.
2. For each sensor, we maintain a discounted sum of its post-initialization readings. A new reading is added to half of the previous discounted sum. The sum is divided by the number of processed post-initialization readings to get that sensor's first moment. This state is separate from the signed history used for clustering and is not reset at synchronization.
3. The FMIC weight for each scalar temperature sensor is the **absolute value of its first moment**. We scale weights so their total equals the number of sensors, then multiply each scaled weight by the current root allowance to obtain the sensor's allowance. A coordinator's allowance is the average of its cluster members' allowances.
4. We made the all-zero-weight case explicit. When every weight is zero, every sensor receives equal scaled weight **1**. This is a **project-defined fallback**, not a formula claimed to come directly from the chapter. An individual zero weight remains zero if other weights are nonzero.
5. We implemented the full monitoring sequence: sensors check their local allowance; triggered sensors report to the cluster coordinator; the coordinator evaluates the cluster and collects additional sensor values as needed; an unresolved cluster check escalates to the root; the root collects the current sensor readings, records the global threshold state, recalculates constraints, and reclusters.
6. The root uses the two-sided threshold policy described in Section 22.1. A root synchronization is driven by FMIC's own monitoring events, **not by replaying Phase 2's synchronization times**. Updated references and allowances apply to subsequent observations.
7. We recorded each message category separately, including the root collection and state-update messages. Communication between a coordinator and itself is not counted as a network transmission.
8. We added hand-calculated tests for first moments, node and coordinator allowances, zero weights, signed cancellation, root escalation, threshold boundaries, persistent history, and message counting. During review, the correctness summary was tightened to require **both** zero false-safe and zero false-violated states. Source references and a hand-calculated example were added to explain the first-moment recurrence.
9. We wrote a compact synchronization-event file and summary rather than an all-minute sensor-history dump. The FMIC file has **293 events**, one per root synchronization.

**Observed FMIC result at alpha = 0.10**

| Measure | Value |
|---|---:|
| Total messages | 11,922 |
| Root synchronizations, including initialization | 293 |
| Monitoring-triggered root synchronizations | 292 |
| Node triggers (events, not transmitted messages) | 3,689 |
| Coordinator checks | 3,522 |
| Coordinator-to-root escalations | 420 |
| Minutes with global mean at or above p90 | 1,999 |
| False-safe / false-violated minutes | 0 / 0 |
| Reported reduction relative to matched Phase 2 | 68.70% |

The **11,922** messages consist of **2,564 node-trigger transmissions; 1,832 cluster requests; 1,832 cluster responses; 420 coordinator-to-root escalations; 1,758 root requests; 1,758 root responses; and 1,758 root state updates**. The categories reconcile and the summary reports correctness `passed`.

**Milestone achieved:** A complete, independently scheduled FMIC simulation with compact event output and an initial, successful comparison against matched Phase 2. The reported results were reviewed for internal consistency; a later comprehensive validation stage remains planned.

### 22.6 US-3.20 — Add SMIC to the shared FMIC monitoring engine

**What was done**

1. We implemented the source-based **second-moment** calculation while preserving FMIC's first-moment calculation. The original chapter and its appendix were used to clarify the mathematical symbols, including the fact that the second moment is an **unnormalized sum of squared deviations** of the discounted observations, not an ordinary sample variance.
2. We used the running calculation documented by the implementation: if `S2` is the stored second moment, a new observation updates it using `0.25 * old_S2 + (m-1)/m * (reading - 0.5 * previous_first_moment)^2`, with `m` representing the number of observations after the new reading. The implementation includes handling for the first observation, invalid values, and all-zero weights.
3. We calculated SMIC's scalar sensor weights as **absolute first moment plus the conservative second-moment term**, `sqrt((m-1)/m * S2)`. The same shared weight-scaling, node-allowance, and coordinator-allowance calculations are then applied.
4. We **reused the FMIC monitoring class** (`FMICMonitor`) with a method setting of `FMIC` or `SMIC`. The two methods share the same sensors, history and clustering code, threshold policy, coordinator/root behavior, communication categories, and output conventions. The chosen moment/weight calculation is the intended difference.
5. We retained the project fallback of equal scaled weights when the total calculated weight is zero. Information about moments and weights travels with existing root synchronization responses and state updates; the simulation does not invent extra transmissions just because SMIC has more numerical fields.
6. We extended the synthetic tests with hand-calculated second moments, direct comparisons with explicit discounted observation sets, early-observation cases, zero/nonzero weights, allowance reconciliation, persistent moment states, exact message counts, threshold-crossing tests, and checks that identical allowances lead to identical monitoring decisions. Regression tests were added to guard against changing FMIC behavior.
7. We generated SMIC's own event and summary files. As with FMIC, these are compact root synchronization records rather than one detailed history row per sensor per minute.

**Observed SMIC result at alpha = 0.10**

| Measure | Value |
|---|---:|
| Total messages | 11,902 |
| Root synchronizations, including initialization | 293 |
| Monitoring-triggered root synchronizations | 292 |
| Node triggers | 3,680 |
| Coordinator checks | 3,514 |
| Coordinator-to-root escalations | 420 |
| Minutes with global mean at or above p90 | 1,999 |
| False-safe / false-violated minutes | 0 / 0 |
| Reported reduction relative to matched Phase 2 | 68.75% |

The **11,902** messages consist of **2,556 node-trigger transmissions; 1,826 cluster requests; 1,826 cluster responses; 420 coordinator-to-root escalations; 1,758 root requests; 1,758 root responses; and 1,758 root state updates**. The categories reconcile and the summary reports correctness `passed`.

**Milestone achieved:** SMIC now runs through the same monitoring architecture as FMIC and produces a matched, preliminary result for the approved cohort and alpha.

### 22.7 What the completed runs show so far

| Measure | Matched Phase 2 | FMIC | SMIC |
|---|---:|---:|---:|
| One-minute buckets | 19,984 | 19,984 | 19,984 |
| Threshold (°C) | 22.42866665 | 22.42866665 | 22.42866665 |
| Total messages | 38,087 | 11,922 | 11,902 |
| Root synchronizations | 2,107 | 293 | 293 |
| Minutes at or above threshold | 1,999 | 1,999 | 1,999 |
| Reported monitoring correctness | Passed | Passed | Passed |
| Reduction in messages vs Phase 2 | — | 68.70% | 68.75% |

FMIC and SMIC both use far fewer messages than the matched Phase 2 simulation at **alpha = 0.10**. SMIC sends only **20 fewer messages** than FMIC, a difference of about **0.17% of FMIC's message total**. The two event files contain the same selected cluster partitions at corresponding event positions. Their synchronization timestamps differ in only **two** corresponding event positions, by one minute each. Therefore, the second-moment calculation has made only a small difference in this first experiment; it should not be treated as a universal finding about SMIC.

The reported zero-error results mean the monitoring methods kept their last root-known safe/violated state consistent with the observed global state at each of the 19,984 minutes in these runs. The centralized global mean is used as an **offline correctness check**; it is not allowed to secretly trigger communication during monitoring.

These comparisons are **preliminary, fixed-alpha results**, not the final study. They establish that the algorithms have working implementations and comparable outputs. They do **not** yet establish that alpha 0.10 is optimal, that SMIC will always use fewer messages, or that either method performs the same way with sensors dropping offline.

### 22.8 US-3.21 — Comprehensive synthetic validation

**What was done**

1. Expanded shared FMIC/SMIC protocol tests with an explicit sender/recipient/purpose/category transmission ledger and a singleton-cluster case.
2. Confirmed the centralized correctness oracle detects injected false-safe and false-violated states, reports failure for either mismatch, and does not determine protocol communication.
3. Verified source-moment and weighting expectations against independent hand calculations and the rendered original PDF: Section 1.4, printed p.10/PDF p.14, and Appendix 1, printed p.22/PDF p.26.
4. Ran `python -B -m unittest scripts.phase3_test_monitoring scripts.phase3_test_history scripts.test_phase2_monitoring -q`; all **91 tests passed**.
5. Replayed both production methods from the current notebook implementation in an isolated temporary root using the approved 19,984-bucket input. FMIC passed with 11,922 messages and 293 synchronizations; SMIC passed with 11,902 messages and 293 synchronizations. Both had 1,999 violated buckets, zero false-safe/false-violated states, and reconciled message totals. The generated event and summary files matched the saved artifacts byte-for-byte.

**Milestone achieved:** Synthetic formula, protocol, correctness, and communication-accounting validation passed for FMIC and SMIC. The validation record is `artifacts/phase3a_validation_summary.json`.

### 22.9 US-3.22 — Alpha sensitivity and final comparison

**What was done**

1. Confirmed the US-3.21 validation record passed before starting the sweep.
2. Ran 19 fresh, full-length FMIC monitors and 19 fresh, full-length SMIC monitors over alpha **0.05–0.95 by 0.05**. Every run used sensors A, C, D, E, F, and G; the inclusive interval 2022-02-24 18:50 UTC–2022-03-10 15:53 UTC; 19,984 buckets; and the full-precision p90 **22.428666649999997 °C**.
3. All 38 runs had zero false-safe and false-violated states, passed correctness, and reconciled all seven message categories. The alpha=0.10 sweep runs matched the fixed-alpha baselines in total and category messages, root synchronization counts, correctness counts/status, and event fingerprints.
4. Protected input, configuration, matched Phase 2, and fixed-alpha production artifact hashes were unchanged during the final sweep execution. The notebook's normal execution path writes sweep artifacts without invoking the fixed-alpha output writers.
5. Wrote 38 result rows, 14,829 compact synchronization-event snapshots, a comparison summary, and three result-derived PNG plots. The event file preserves per-alpha partitions and monitor state without minute-by-minute traces.
6. Defined mean cluster size as total sensor memberships across all selected partitions at synchronization events, including initialization, divided by total clusters across those events. Mean cluster count is the arithmetic mean of per-event counts, also including initialization.
7. All 94 Phase 2/Phase 3 regression tests passed on the final implementation.

**Findings**

- Both methods reached their minimum observed message total at **alpha=0.65** on this dataset and tested grid: FMIC **8,722** messages and SMIC **8,720**. Each had 436 root synchronizations, mean cluster count 5.8005, and mean cluster size 1.0344. The reductions versus matched Phase 2 were 77.10% and 77.11%, respectively; these are in-sample descriptive minima, not generalizable or theoretically optimal settings.
- Message totals were irregular across alpha for both algorithms. At the prespecified alpha=0.10, FMIC used 11,922 messages and SMIC 11,902, with 293 root synchronizations each. The 20-message difference came from 8 additional FMIC node-trigger messages, 6 additional cluster-check requests, and 6 additional responses; root message and escalation categories were equal.
- At alpha=0.65, SMIC used two fewer messages than FMIC, entirely from two fewer coordinator-to-root escalations. The methods remain closely matched on this fixed experiment; no general superiority or statistical-significance claim is made.

**Milestone achieved:** US-3.22 completes the required Phase 3A alpha sensitivity sweep and matched final comparison. Phase 3B remains optional and was not evaluated.

### 22.10 What remains after US-3.22

**Phase 3B — Optional.** Only if separately approved, return to intermittent sensor availability and changing membership. The current Phase 3A outcomes do not answer those questions.

### 22.11 Files and evidence available for this record

The implementation history can be checked against these project artifacts:

- `build_phase1_temperature.py` — Phase 1 transformation and Phase 3A p90 statistics.
- `phase1_average_statistics.csv` — full-data and `phase3a_stable_cohort` statistics rows.
- `transformation_decisions.md` — Phase 1 run records and the aggregate-input exclusion correction.
- `build_phase3_temperature_clustering.ipynb` — Phase 3A history, clustering, FMIC, and SMIC code (the latest reviewed upload was named `build_phase3_temperature_clustering(4).ipynb`).
- `test_phase3_history.py` and `test_phase3_monitoring.py` — synthetic and implementation tests (the latest reviewed monitoring-test upload was named `test_phase3_monitoring(1).py`).
- `phase3a_phase2_baseline.json` — matched Phase 2 metrics.
- `phase3a_fmic_events.csv` and `phase3a_fmic_summary.json` — FMIC event history and results.
- `phase3a_smic_events.csv` and `phase3a_smic_summary.json` — SMIC event history and results.
- `phase3a_validation_summary.json` — US-3.21 test command, scenarios, source references, and production replay outcomes.
- `phase3a_alpha_results.csv`, `phase3a_alpha_events.csv`, and `phase3a_comparison_summary.json` — US-3.22 results, event snapshots, provenance, comparisons, and limitations.
- `phase3a_messages_vs_alpha.png`, `phase3a_synchronizations_vs_alpha.png`, and `phase3a_clustering_vs_alpha.png` — plots derived from the saved results table.
- `US-3.16` through `US-3.22` Markdown user stories — the scoped development instructions used to make the changes.

The US-3.21 gate was confirmed before the sweep. The US-3.22 38-run production sweep was executed and checked against the fixed-alpha baselines; the final sweep preserved their event and summary files.

### 22.12 US-3.23 — Two-sided geometric Phase 2 policy (2026-11-10)

The shared Phase 2 engine now gives each participating sensor the same
nonnegative allowance `abs(threshold - synchronized_mean)` and tests absolute
local deviations against it with `>=`. The signed local deviation remains
available for audit. The root retains the last synchronized SAFE/VIOLATED state;
an already-violated state no longer schedules a repeated root collection.
At exact equality, zero allowance still conservatively triggers on the next
bucket, even for unchanged readings. Initialization, membership/deferred
synchronization, next-bucket activation, and actual-transmission counting are
preserved.

The independent offline oracle checks the root state after bucket actions and
never controls synchronization. The revised 19,984-bucket matched run passed
with **9,159 messages** (753 triggers and 2,802 each of requests, responses, and
updates), **467 synchronizations**, 1,999 violated buckets, and **zero false-safe
and false-violated states**. Membership changes remained zero.

Outputs are `phase3a_phase2_two_sided_baseline.json` and
`phase3a_phase2_two_sided_events.csv`, generated by
`python -B -m scripts.phase2_monitoring`. The original signed-margin baseline
remains 38,087 messages and 2,107 synchronizations. The aggregate reduction of
28,928 messages and 1,640 synchronizations cannot be split causally between
scheduling removal and consequential trigger/timeline changes from those
aggregates alone.

All **103 Phase 2/Phase 3 tests passed**, including both oracle negative
controls, exact boundaries, cooling/warming, batched triggers, availability,
notebook reports, and protected outputs. Two fresh-process production runs
produced byte-identical revised baseline and event files. Before/after SHA-256
checks verified that the original Phase 2 outputs/baseline, input/configuration,
Phase 3 notebook, FMIC/SMIC results, US-3.21 validation, and US-3.22
tables/summary/plots were unchanged.

The general full-data Phase 2 notebook uses separate `phase2_two_sided_*`
output names. Its field dictionary documents the renamed absolute allowances,
removed negative-margin fields, retained root state, and explicitly separated
`legacy_event_*` synchronization diagnostics.

This is a policy repair, not full isolation of clustering benefits. Moment-based
allowances and coordinator/cluster protocol effects remain uncontrolled; any
comparison with existing FMIC/SMIC results is preliminary. No Phase 3 experiment
was rerun or denominator changed by US-3.23.
