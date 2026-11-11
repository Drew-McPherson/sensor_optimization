"""Canonical Phase 3A algorithms and revised controlled experiment.

Importing this module does not load inputs or execute experiments.
Run regression tests separately and supply their current validation record.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Iterable, Mapping, Sequence
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from numbers import Real
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import MappingProxyType
from typing import Any

import numpy as np
import pandas as pd

from scripts.shared_monitoring_engine import (
    EVENTS as PHASE2_EVENTS,
    RECEIPT as PHASE2_RECEIPT,
    SUMMARY as PHASE2_SUMMARY,
    build_phase2_trace,
    load_validated as load_validated_phase2,
    root_correctness_summary,
)


@dataclass(frozen=True)
class HistoryNormalizationSnapshot:
    """One event-level normalization result shared by alpha candidates."""

    eligible_sensor_ids: tuple[str, ...]
    raw_histories: Mapping[str, float]
    history_magnitudes: Mapping[str, float]
    maximum_history_magnitude: float | None
    normalized_histories: Mapping[str, float] | None
    normalization_status: str
    partition_basis: str
    zero_history_fallback: bool
    fallback_reason: str | None
    fallback_partition: tuple[tuple[str, ...], ...] | None
    deferred_reason: str | None


@dataclass(frozen=True)
class AlphaClusteringInput:
    """Per-alpha handoff referencing the shared normalization snapshot."""

    clustering_event_id: int
    synchronization_id: int
    alpha: float
    normalization_snapshot: HistoryNormalizationSnapshot


PHASE3_ALPHA_VALUES = tuple(value / 100 for value in range(5, 100, 5))
PHASE3A_DEFAULT_ALPHA_VALUES = (0.10,)


def normalize_sensor_histories(
    raw_histories: Mapping[str, Real],
    eligible_sensor_ids: Iterable[str],
) -> HistoryNormalizationSnapshot:
    """Normalize eligible scalar histories without mutating persistent state."""
    if isinstance(eligible_sensor_ids, str):
        raise ValueError("Provide eligible sensor IDs as an iterable, not a string.")
    eligible_ids = tuple(eligible_sensor_ids)
    if any(not isinstance(sensor_id, str) or not sensor_id for sensor_id in eligible_ids):
        raise ValueError("Eligible sensor IDs must be non-empty strings.")
    if len(set(eligible_ids)) != len(eligible_ids):
        raise ValueError("Eligible sensor IDs must be unique.")

    if not eligible_ids:
        return HistoryNormalizationSnapshot(
            eligible_sensor_ids=(),
            raw_histories=MappingProxyType({}),
            history_magnitudes=MappingProxyType({}),
            maximum_history_magnitude=None,
            normalized_histories=None,
            normalization_status="deferred",
            partition_basis="not_applicable",
            zero_history_fallback=False,
            fallback_reason=None,
            fallback_partition=None,
            deferred_reason="no_eligible_sensors",
        )

    missing = sorted(set(eligible_ids) - set(raw_histories))
    if missing:
        raise ValueError(f"Raw history is missing eligible sensors: {missing}.")

    eligible_histories: dict[str, float] = {}
    for sensor_id in sorted(eligible_ids):
        value = raw_histories[sensor_id]
        if isinstance(value, bool) or not isinstance(value, Real):
            raise ValueError(f"History for {sensor_id} must be a finite number.")
        numeric_value = float(value)
        if not math.isfinite(numeric_value):
            raise ValueError(f"History for {sensor_id} must be finite.")
        eligible_histories[sensor_id] = numeric_value

    magnitudes = {
        sensor_id: abs(history)
        for sensor_id, history in eligible_histories.items()
    }
    maximum_magnitude = max(magnitudes.values())
    if maximum_magnitude == 0:
        return HistoryNormalizationSnapshot(
            eligible_sensor_ids=tuple(sorted(eligible_histories)),
            raw_histories=MappingProxyType(eligible_histories),
            history_magnitudes=MappingProxyType(magnitudes),
            maximum_history_magnitude=0.0,
            normalized_histories=None,
            normalization_status="all_zero_history_fallback",
            partition_basis="all_zero_history_fallback",
            zero_history_fallback=True,
            fallback_reason="all_eligible_histories_are_zero",
            fallback_partition=tuple(
                (sensor_id,) for sensor_id in sorted(eligible_histories)
            ),
            deferred_reason=None,
        )

    normalized = {
        sensor_id: history / maximum_magnitude
        for sensor_id, history in eligible_histories.items()
    }
    return HistoryNormalizationSnapshot(
        eligible_sensor_ids=tuple(sorted(eligible_histories)),
        raw_histories=MappingProxyType(eligible_histories),
        history_magnitudes=MappingProxyType(magnitudes),
        maximum_history_magnitude=maximum_magnitude,
        normalized_histories=MappingProxyType(normalized),
        normalization_status="normalized",
        partition_basis="normalized_history",
        zero_history_fallback=False,
        fallback_reason=None,
        fallback_partition=None,
        deferred_reason=None,
    )


def build_alpha_clustering_inputs(
    synchronization_id: int,
    normalization_snapshot: HistoryNormalizationSnapshot,
    alpha_values: Iterable[Real] = PHASE3A_DEFAULT_ALPHA_VALUES,
) -> tuple[AlphaClusteringInput, ...]:
    """Build selected alpha inputs, sharing one event normalization result."""
    if synchronization_id < 1:
        raise ValueError("Synchronization ID must be positive.")
    if normalization_snapshot.deferred_reason is not None:
        return ()
    return tuple(
        AlphaClusteringInput(
            clustering_event_id=synchronization_id,
            synchronization_id=synchronization_id,
            alpha=float(alpha),
            normalization_snapshot=normalization_snapshot,
        )
        for alpha in alpha_values
    )


Cluster = tuple[str, ...]
Partition = tuple[Cluster, ...]


def _validated_clustering_values(
    normalized_histories: Mapping[str, Real], alpha: Real,
) -> dict[str, float]:
    if isinstance(alpha, bool) or not isinstance(alpha, Real):
        raise ValueError("Alpha must be a finite number in [0, 1].")
    if not math.isfinite(float(alpha)) or not 0 <= alpha <= 1:
        raise ValueError("Alpha must be a finite number in [0, 1].")
    values: dict[str, float] = {}
    for sensor_id, value in normalized_histories.items():
        if not isinstance(sensor_id, str) or not sensor_id:
            raise ValueError("Clustering sensor IDs must be non-empty strings.")
        if isinstance(value, bool) or not isinstance(value, Real):
            raise ValueError(f"Normalized history for {sensor_id} must be finite.")
        numeric_value = float(value)
        if not math.isfinite(numeric_value) or abs(numeric_value) > 1:
            raise ValueError(f"Normalized history for {sensor_id} must be in [-1, 1].")
        values[sensor_id] = numeric_value
    return values


def _canonical_cluster(cluster: Iterable[str]) -> Cluster:
    if isinstance(cluster, str):
        raise ValueError("A cluster must be an iterable of sensor IDs, not a string.")
    members = tuple(cluster)
    if not members or any(not isinstance(member, str) or not member for member in members):
        raise ValueError("Clusters must contain non-empty string sensor IDs.")
    if len(set(members)) != len(members):
        raise ValueError("A cluster must not contain duplicate sensor IDs.")
    return tuple(sorted(members))


def _cluster_quality(cluster: Cluster, values: Mapping[str, float], alpha: float) -> float:
    return abs(math.fsum(values[sensor_id] for sensor_id in cluster)) / len(cluster) + alpha * len(cluster)


def cluster_quality(
    cluster: Iterable[str], normalized_histories: Mapping[str, Real], alpha: Real,
) -> float:
    """Score signed cancellation before applying the scalar absolute value."""
    values = _validated_clustering_values(normalized_histories, alpha)
    members = _canonical_cluster(cluster)
    unknown = sorted(set(members) - set(values))
    if unknown:
        raise ValueError(f"Cluster contains sensors without normalized histories: {unknown}.")
    return _cluster_quality(members, values, float(alpha))


def partition_quality(
    partition: Iterable[Iterable[str]], normalized_histories: Mapping[str, Real], alpha: Real,
) -> float:
    """Score a disjoint partition containing exactly the supplied sensors."""
    values = _validated_clustering_values(normalized_histories, alpha)
    clusters = tuple(sorted(_canonical_cluster(cluster) for cluster in partition))
    members = tuple(member for cluster in clusters for member in cluster)
    if not clusters or len(set(members)) != len(members) or set(members) != set(values):
        raise ValueError("Partition must cover every eligible sensor exactly once.")
    return max(_cluster_quality(cluster, values, float(alpha)) for cluster in clusters)


def evaluate_alpha_clustering(clustering_input: AlphaClusteringInput) -> dict[str, object] | None:
    """Retain the greedy candidate sequence and choose its earliest minimum."""
    snapshot = clustering_input.normalization_snapshot
    if snapshot.deferred_reason is not None:
        return None
    eligible = snapshot.eligible_sensor_ids
    if not eligible:
        raise ValueError("A completed clustering input must have eligible sensors.")
    if snapshot.zero_history_fallback:
        if any(snapshot.raw_histories[sensor_id] != 0 for sensor_id in eligible):
            raise ValueError("All-zero fallback requires zero raw eligible histories.")
        # Zero raw histories allow fallback scoring without fabricating normalization.
        source_values = snapshot.raw_histories
    else:
        if snapshot.normalized_histories is None:
            raise ValueError("Nonzero history clustering requires normalized histories.")
        source_values = snapshot.normalized_histories
    values = _validated_clustering_values(source_values, clustering_input.alpha)
    if len(set(eligible)) != len(eligible) or set(values) != set(eligible):
        raise ValueError("Clustering values must cover exactly the eligible sensor set.")
    alpha = float(clustering_input.alpha)
    partition: Partition = tuple((sensor_id,) for sensor_id in sorted(eligible))
    candidates: list[dict[str, object]] = []
    candidate_qualities: list[float] = []
    candidate_partitions: list[Partition] = []
    merges: list[dict[str, object]] = []

    while True:
        qualities = {cluster: _cluster_quality(cluster, values, alpha) for cluster in partition}
        quality = max(qualities.values())
        candidates.append({
            "candidate_index": len(candidates),
            "partition": partition,
            "cluster_count": len(partition),
            "cluster_qualities": [
                {"members": cluster, "quality": qualities[cluster]} for cluster in partition
            ],
            "partition_quality": quality,
        })
        candidate_qualities.append(quality)
        candidate_partitions.append(partition)
        if snapshot.zero_history_fallback or len(partition) <= 2:
            break

        worst = min(partition, key=lambda cluster: (-qualities[cluster], cluster))
        partners = []
        for partner in partition:
            if partner != worst:
                merged = tuple(sorted(worst + partner))
                partners.append((partner, merged, _cluster_quality(merged, values, alpha)))
        partner, merged, merged_quality = min(partners, key=lambda item: (item[2], item[0]))
        merges.append({
            "from_candidate_index": len(candidates) - 1,
            "worst_cluster": worst,
            "worst_cluster_quality": qualities[worst],
            "partner_scores": [
                {"partner": item[0], "merged_cluster": item[1], "merged_quality": item[2]}
                for item in partners
            ],
            "selected_partner": partner,
            "merged_cluster": merged,
            "merged_quality": merged_quality,
        })
        partition = tuple(sorted(
            tuple(cluster for cluster in partition if cluster not in (worst, partner)) + (merged,)
        ))

    selected_index = min(range(len(candidates)), key=lambda index: candidate_qualities[index])
    selected_partition = candidate_partitions[selected_index]
    return {
        "clustering_event_id": clustering_input.clustering_event_id,
        "synchronization_id": clustering_input.synchronization_id,
        "normalization_snapshot_id": clustering_input.synchronization_id,
        "alpha": alpha,
        "partition_basis": snapshot.partition_basis,
        "zero_history_fallback": snapshot.zero_history_fallback,
        "fallback_reason": snapshot.fallback_reason,
        "candidate_partitions": candidates,
        "merge_steps": merges,
        "selected_candidate_index": selected_index,
        "selected_partition": selected_partition,
        "partition_quality": candidate_qualities[selected_index],
        "cluster_count": len(selected_partition),
        "cluster_assignments": {
            sensor_id: cluster_index
            for cluster_index, cluster in enumerate(selected_partition)
            for sensor_id in cluster
        },
    }

PHASE3A_APPROVED_SENSOR_IDS = ("A", "C", "D", "E", "F", "G")
PHASE3A_BUCKET_SECONDS = 60


def validate_phase3a_config(config):
    """Reject configuration drift from the approved stable-cohort contract."""
    if not isinstance(config, dict):
        raise ValueError("Phase 3A experiment configuration must be a JSON object.")
    if config.get("input_source") != "artifacts/aligned_phase1_temperature.csv":
        raise ValueError("Phase 3A input must use the aligned Phase 1 artifact.")

    sensor_ids = tuple(config.get("selected_sensor_ids", ()))
    if sensor_ids != PHASE3A_APPROVED_SENSOR_IDS:
        raise ValueError(
            "Phase 3A cohort must remain exactly A, C, D, E, F, and G."
        )
    expected_columns = [f"{sensor_id}_temperature" for sensor_id in sensor_ids]
    if config.get("selected_sensor_temperature_columns") != expected_columns:
        raise ValueError(
            "Phase 3A temperature columns must match the approved sensor cohort."
        )
    if config.get("endpoint_convention") != "inclusive":
        raise ValueError("Phase 3A interval endpoints must both be inclusive.")
    if config.get("sampling_interval_seconds") != PHASE3A_BUCKET_SECONDS:
        raise ValueError("Phase 3A sampling interval must be exactly 60 seconds.")
    if config.get("stable_cohort_required") is not True:
        raise ValueError("Phase 3A must require the fixed stable cohort.")
    if config.get("missing_value_policy") != "fail":
        raise ValueError("Phase 3A missing observations must fail validation.")
    if config.get("imputation_policy") != "none":
        raise ValueError("Phase 3A input must not use imputed sensor values.")
    if config.get("baseline_alpha") != 0.10:
        raise ValueError("The Phase 3A baseline alpha must be 0.10.")
    if config.get("boundary_convention") != {
        "safe_when": "metric < threshold",
        "violated_when": "metric >= threshold",
    }:
        raise ValueError("Phase 3A boundary convention does not match the approved policy.")

    threshold_config = config.get("threshold")
    if not isinstance(threshold_config, dict):
        raise ValueError("Phase 3A threshold configuration must be an object.")
    if threshold_config.get("source_series") != "phase3a_stable_cohort":
        raise ValueError("The Phase 3A threshold source must be phase3a_stable_cohort.")
    if threshold_config.get("statistic") != "p90":
        raise ValueError("The authoritative Phase 3A threshold statistic must be p90.")
    threshold_value = threshold_config.get("p90_value")
    if isinstance(threshold_value, bool) or not isinstance(
        threshold_value, (int, float)
    ) or not np.isfinite(threshold_value):
        raise ValueError("The authoritative Phase 3A P90 must be a finite number.")
    if threshold_config.get("status") != "authoritative":
        raise ValueError("The Phase 3A P90 must be marked authoritative.")
    if threshold_config.get("statistics_artifact") != "artifacts/phase1_average_statistics.csv":
        raise ValueError("Phase 3A P90 provenance must name the Phase 1 statistics artifact.")
    if threshold_config.get("production_script") != "scripts/build_phase1_temperature.py":
        raise ValueError("Phase 3A P90 provenance must name the Phase 1 production script.")

    start_time = pd.Timestamp(config.get("start_timestamp_utc"))
    end_time = pd.Timestamp(config.get("end_timestamp_utc"))
    if start_time.tz is None or end_time.tz is None:
        raise ValueError("Phase 3A interval timestamps must be timezone-aware.")
    start_time = start_time.tz_convert("UTC")
    end_time = end_time.tz_convert("UTC")
    if end_time <= start_time:
        raise ValueError("Phase 3A end timestamp must follow its start timestamp.")

    elapsed_seconds = (end_time - start_time).total_seconds()
    if elapsed_seconds % PHASE3A_BUCKET_SECONDS:
        raise ValueError("Phase 3A endpoints must align to one-minute buckets.")
    expected_elapsed_minutes = int(elapsed_seconds // 60)
    expected_bucket_count = config.get("expected_bucket_count")
    if isinstance(expected_bucket_count, bool) or not isinstance(
        expected_bucket_count, int
    ):
        raise ValueError("Phase 3A expected_bucket_count must be an integer.")
    if expected_bucket_count != expected_elapsed_minutes + 1:
        raise ValueError("Phase 3A bucket count must include both interval endpoints.")
    if config.get("expected_elapsed_minutes") != expected_elapsed_minutes:
        raise ValueError("Phase 3A expected elapsed minutes do not match its endpoints.")

    return sensor_ids, expected_columns, start_time, end_time, expected_bucket_count


def prepare_phase3a_input(source_frame, experiment_config):
    """Select and validate the approved complete one-minute Phase 3A input."""
    sensor_ids, sensor_columns, start_time, end_time, expected_bucket_count = (
        validate_phase3a_config(experiment_config)
    )
    required_columns = ["bucket_epoch", "bucket_time_utc", *sensor_columns]
    missing_columns = sorted(set(required_columns) - set(source_frame.columns))
    if missing_columns:
        raise ValueError(f"Phase 3A input is missing required columns: {missing_columns}")

    timestamps = pd.to_datetime(
        source_frame["bucket_time_utc"], utc=True, errors="coerce"
    )
    if timestamps.isna().any():
        raise ValueError("Phase 1 input contains an invalid bucket_time_utc timestamp.")
    in_interval = timestamps.between(start_time, end_time, inclusive="both")
    selected = source_frame.loc[in_interval, required_columns].copy()
    selected["bucket_time_utc"] = pd.to_datetime(
        selected["bucket_time_utc"], utc=True, errors="raise"
    )

    if len(selected) != expected_bucket_count:
        raise ValueError(
            f"Phase 3A interval requires {expected_bucket_count} buckets; "
            f"found {len(selected)}."
        )
    selected_times = selected["bucket_time_utc"]
    if not selected_times.is_unique:
        raise ValueError("Phase 3A input contains duplicate timestamps.")
    if not selected_times.is_monotonic_increasing:
        raise ValueError("Phase 3A timestamps must be in strictly increasing order.")
    if selected_times.iloc[0] != start_time:
        raise ValueError("Phase 3A first timestamp does not match the approved start.")
    if selected_times.iloc[-1] != end_time:
        raise ValueError("Phase 3A final timestamp does not match the approved end.")

    time_deltas = selected_times.diff().dt.total_seconds().iloc[1:]
    if not time_deltas.eq(PHASE3A_BUCKET_SECONDS).all():
        bad_position = int(
            np.flatnonzero(
                ~time_deltas.eq(PHASE3A_BUCKET_SECONDS).to_numpy()
            )[0]
        ) + 1
        raise ValueError(
            f"Phase 3A timestamp gap at selected row {bad_position}; "
            "expected exactly 60 seconds."
        )

    epochs = pd.to_numeric(selected["bucket_epoch"], errors="coerce")
    epoch_values = epochs.to_numpy(dtype=float)
    if not np.isfinite(epoch_values).all() or not np.equal(
        epoch_values, np.floor(epoch_values)
    ).all():
        raise ValueError("Phase 3A bucket_epoch values must be finite whole seconds.")
    expected_epochs = np.fromiter(
        (int(timestamp.timestamp()) for timestamp in selected_times),
        dtype=np.int64,
        count=len(selected_times),
    )
    if not np.array_equal(epochs.to_numpy(dtype=np.int64), expected_epochs):
        raise ValueError("Phase 3A bucket_epoch values do not match timestamps.")
    if not epochs.diff().iloc[1:].eq(PHASE3A_BUCKET_SECONDS).all():
        raise ValueError("Phase 3A bucket_epoch values must be consecutive 60-second steps.")
    selected["bucket_epoch"] = epochs.astype("int64")

    for column in sensor_columns:
        numeric = pd.to_numeric(selected[column], errors="coerce")
        invalid = numeric.isna() | ~np.isfinite(numeric.to_numpy(dtype=float))
        if invalid.any():
            row_number = int(np.flatnonzero(invalid.to_numpy())[0])
            raise ValueError(
                f"Phase 3A requires a finite {column} value in every bucket; "
                f"missing or invalid value at {selected_times.iloc[row_number]}."
            )
        selected[column] = numeric.astype(float)
    return selected.reset_index(drop=True)


class Phase3AHistoryTracker:
    """Track signed accumulated history for an always-present fixed cohort."""

    DISCOUNT = 0.5

    def __init__(self, sensor_ids):
        self.sensor_ids = tuple(sensor_ids)
        if not self.sensor_ids or len(set(self.sensor_ids)) != len(self.sensor_ids):
            raise ValueError("Phase 3A sensor IDs must be non-empty and unique.")
        self.histories = {sensor_id: 0.0 for sensor_id in self.sensor_ids}
        self.references = {sensor_id: None for sensor_id in self.sensor_ids}
        self.synchronization_id = 0
        self.row_number = 0

    def step(self, readings, synchronization_causes=()):
        if set(readings) != set(self.sensor_ids):
            raise ValueError("Phase 3A readings must contain exactly the fixed cohort.")
        values = {}
        for sensor_id in self.sensor_ids:
            value = readings[sensor_id]
            if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, float, np.number)):
                raise ValueError(f"Phase 3A reading for {sensor_id} must be finite and numeric.")
            value = float(value)
            if not np.isfinite(value):
                raise ValueError(f"Phase 3A reading for {sensor_id} must be finite and numeric.")
            values[sensor_id] = value

        if isinstance(synchronization_causes, str):
            raise ValueError("Synchronization causes must be an iterable, not a string.")
        causes = tuple(sorted(set(synchronization_causes)))
        if self.synchronization_id == 0 and not causes:
            raise ValueError("The first Phase 3A row must complete initialization synchronization.")
        if self.synchronization_id:
            for sensor_id in self.sensor_ids:
                self.histories[sensor_id] = (
                    self.DISCOUNT * self.histories[sensor_id]
                    + values[sensor_id] - self.references[sensor_id]
                )
        clustering_histories = None
        if causes:
            self.synchronization_id += 1
            clustering_histories = dict(self.histories)
            self.references = dict(values)
        self.row_number += 1
        return clustering_histories, causes


"""Shared FMIC/SMIC monitoring for the fixed Phase 3A experiment.

Chapter section 1.4, printed p.10 (PDF p.14): mu is the arithmetic
mean of the discounted vectors {v(t_m), v(t_(m-1))/2, ...}.
FMIC keeps only |mu| in the general moment weight (section 1.5.2).
Clustering history and the first moment are deliberately separate states.
"""


MESSAGE_CATEGORIES = (
    "node_trigger_messages",
    "cluster_check_requests",
    "cluster_check_responses",
    "coordinator_root_escalations",
    "root_sync_requests",
    "root_sync_responses",
    "root_state_updates",
)


def fmic_allocation(
    moments: Mapping[str, float],
    partition: Sequence[Sequence[str]],
    root_allowance: float,
) -> dict:
    if not moments or any(
        isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value)
        for value in moments.values()
    ):
        raise ValueError("FMIC moments must be nonempty and finite.")
    weights = {sensor: abs(value) for sensor, value in moments.items()}
    return {
        "first_moments": dict(moments),
        **allocate_moment_weights(weights, partition, root_allowance, "source_first_moment"),
    }


def allocate_moment_weights(
    weights: Mapping[str, float],
    partition: Sequence[Sequence[str]],
    root_allowance: float,
    weight_status: str,
) -> dict:
    if not weights or any(not math.isfinite(value) or value < 0 for value in weights.values()):
        raise ValueError("Raw moment weights must be nonempty, finite, and nonnegative.")
    if not math.isfinite(root_allowance) or root_allowance < 0:
        raise ValueError("Root allowance must be finite and nonnegative.")
    members = [sensor for cluster in partition for sensor in cluster]
    if any(not cluster for cluster in partition) or sorted(members) != sorted(weights):
        raise ValueError("Partition must cover every sensor exactly once.")
    total = math.fsum(weights.values())
    if not math.isfinite(total):
        raise ValueError("Total moment weight overflowed.")
    fallback = total == 0
    scaled = {
        sensor: 1.0 if fallback else len(weights) * (value / total)
        for sensor, value in weights.items()
    }
    node = {sensor: value * root_allowance for sensor, value in scaled.items()}
    if any(not math.isfinite(value) for value in node.values()):
        raise ValueError("Moment node allowances overflowed.")
    coordinator = {
        max(cluster): math.fsum(node[sensor] for sensor in cluster) / len(cluster)
        for cluster in partition
    }
    return {
        "raw_weights": dict(weights),
        "scaled_weights": scaled,
        "node_allowances": node,
        "coordinator_allowances": coordinator,
        "weight_status": "project_all_zero_equal_weight_fallback" if fallback else weight_status,
    }


class DiscountedFirstMoment:
    """Implement the source discounted vector-set mean (section 1.4, p.10/PDF 14).

    S(m) = sum(2**(-(m-i)) * raw_reading(i), i=1..m), mu(m) = S(m)/m.
    Updating S by 0.5*S + reading is algebraically equivalent to that set.
    Count every post-t0 observation, not sync events; neither state resets.
    This is not a weight-normalized EMA or the reference-relative history.
    See the preceding provenance cell and FirstMomentTests' hand calculation.
    """

    def __init__(self, sensors: Sequence[str]):
        self.sums = dict.fromkeys(sensors, 0.0)
        self.count = 0

    def update(self, readings: Mapping[str, float]) -> None:
        if set(readings) != set(self.sums):
            raise ValueError("First moments require the fixed sensor cohort.")
        if any(
            isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value)
            for value in readings.values()
        ):
            raise ValueError("First-moment observations must be finite.")
        self.count += 1
        self.sums = {
            sensor: 0.5 * self.sums[sensor] + readings[sensor]
            for sensor in self.sums
        }
        if any(not math.isfinite(value) for value in self.sums.values()):
            raise ValueError("Discounted first-moment sums overflowed.")

    def means(self) -> dict[str, float]:
        return {
            sensor: value / self.count if self.count else 0.0
            for sensor, value in self.sums.items()
        }


class DiscountedSecondMoment(DiscountedFirstMoment):
    """Source sum of squared deviations, NOT population/sample variance.

    Appendix 1, printed p.22/PDF 26: sigma^2 = sum((x_i-mu)^2), i=1..m.
    This resolves section 1.4's i=0 indexing typo; there is no divisor.
    Appendix 1, printed p.24/PDF 28, supplies the stable recurrence below.
    Scaling prior vectors by 1/2 scales their squared deviations by 1/4.
    All update terms are nonnegative: no cancellation clamp is needed.
    """

    def __init__(self, sensors: Sequence[str]):
        super().__init__(sensors)
        self.second_moments = dict.fromkeys(self.sums, 0.0)

    def update(self, readings: Mapping[str, float]) -> None:
        old_means = self.means()
        old_count = self.count
        super().update(readings)
        updated = {}
        for sensor, prior in self.second_moments.items():
            delta = readings[sensor] - 0.5 * old_means[sensor]
            updated[sensor] = 0.25 * prior + (old_count / self.count) * delta * delta
        if any(not math.isfinite(value) or value < 0 for value in updated.values()):
            raise ValueError("Discounted second moments must remain finite and nonnegative.")
        self.second_moments = updated


def smic_allocation(
    moments: Mapping[str, float],
    second_moments: Mapping[str, float],
    count: int,
    partition: Sequence[Sequence[str]],
    root_allowance: float,
) -> dict:
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise ValueError("SMIC observation count must be a nonnegative integer.")
    if not moments or set(moments) != set(second_moments):
        raise ValueError("SMIC first and second moments must cover the same fixed cohort.")
    if any(
        isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value)
        for value in (*moments.values(), *second_moments.values())
    ) or any(value < 0 for value in second_moments.values()):
        raise ValueError("SMIC moments must be finite; second moments must be nonnegative.")
    if count == 0 and any(value != 0 for value in moments.values()):
        raise ValueError("No observations must give zero first moments.")
    if count <= 1 and any(value != 0 for value in second_moments.values()):
        raise ValueError("Zero or one observation must give zero central second moments.")
    factor = (count - 1) / count if count else 0.0
    terms = {sensor: math.sqrt(factor * value) for sensor, value in second_moments.items()}
    weights = {sensor: abs(value) + terms[sensor] for sensor, value in moments.items()}
    return {
        "first_moments": dict(moments),
        "second_moments": dict(second_moments),
        "conservative_terms": terms,
        **allocate_moment_weights(weights, partition, root_allowance, "source_first_plus_second_moment"),
    }


class FMICMonitor:
    """Shared FMIC/SMIC lifecycle; compatibility name, no imported sync schedule.

    allocation_strategy(moment, partition, root_allowance) optionally injects
    allocation values for protocol tests; otherwise weight_method selects them.
    """

    def __init__(
        self,
        sensor_ids: Sequence[str],
        threshold: float,
        alpha: float = 0.10,
        *,
        clustering: Callable = evaluate_alpha_clustering,
        weight_method: str = "FMIC",
        allocation_strategy: Callable | None = None,
        raise_on_false_safe: bool = True,
        capture_decisions: bool = False,
    ):
        if weight_method not in ("FMIC", "SMIC"):
            raise ValueError("weight_method must be FMIC or SMIC.")
        self.weight_method = weight_method
        self.allocation_strategy = allocation_strategy
        self.raise_on_false_safe = raise_on_false_safe
        if not isinstance(capture_decisions, bool):
            raise ValueError("capture_decisions must be a boolean.")
        self.capture_decisions = capture_decisions
        self.sensors = tuple(sensor_ids)
        if not self.sensors or len(set(self.sensors)) != len(self.sensors):
            raise ValueError("Sensors must be nonempty and unique.")
        if not math.isfinite(threshold) or not math.isfinite(alpha) or not 0 <= alpha <= 1:
            raise ValueError("Threshold and alpha must be finite; alpha must be in [0, 1].")
        self.threshold = threshold
        self.alpha = alpha
        self.clustering = clustering
        self.history = Phase3AHistoryTracker(self.sensors)
        self.moment = (
            DiscountedSecondMoment(self.sensors) if weight_method == "SMIC"
            else DiscountedFirstMoment(self.sensors)
        )
        self.references: dict[str, float] = {}
        self.partition: tuple[tuple[str, ...], ...] = ()
        self.allocation: dict = {}
        self.known_violated = False
        self.events: list[dict] = []
        self.decision_trace: list[dict] = []
        self.messages = dict.fromkeys(MESSAGE_CATEGORIES, 0)
        self.rows = 0
        self.node_triggers = 0
        self.checks = 0
        self.escalations = 0
        self.truth_violations = 0
        self.false_safe = 0
        self.false_violated = 0

    def step(self, readings: Mapping[str, float], timestamp: str, epoch: int) -> dict:
        if set(readings) != set(self.sensors):
            raise ValueError(f"{self.weight_method} readings must contain exactly the fixed cohort.")
        if any(isinstance(value, bool) or not isinstance(value, Real) for value in readings.values()):
            raise ValueError(f"{self.weight_method} observations must be numeric, not booleans or text.")
        values = {sensor: float(readings[sensor]) for sensor in self.sensors}
        if any(not math.isfinite(value) for value in values.values()):
            raise ValueError(f"{self.weight_method} observations must be finite.")
        counts = dict.fromkeys(MESSAGE_CATEGORIES, 0)
        entry_references = dict(self.references)
        entry_node_allowances = dict(self.allocation.get("node_allowances", {}))
        entry_coordinator_allowances = dict(self.allocation.get("coordinator_allowances", {}))
        entry_partition = self.partition
        entry_known_state = (
            None if not self.references else "VIOLATED" if self.known_violated else "SAFE"
        )
        initialization = not self.references
        triggering_sensor_ids = set()
        check_count = escalation_count = trigger_count = 0
        if not initialization:
            self.moment.update(values)
            for cluster in self.partition:
                coordinator = max(cluster)
                deviations = {
                    sensor: values[sensor] - self.references[sensor] for sensor in cluster
                }
                triggers = {
                    sensor for sensor in cluster
                    if abs(deviations[sensor]) >= self.allocation["node_allowances"][sensor]
                }
                if not triggers:
                    continue
                triggering_sensor_ids.update(triggers)
                trigger_count += len(triggers)
                check_count += 1
                # All triggering non-coordinators send their current reading.
                # The coordinator requests only peers not already reporting.
                counts["node_trigger_messages"] += len(triggers - {coordinator})
                requested = set(cluster) - triggers - {coordinator}
                counts["cluster_check_requests"] += len(requested)
                counts["cluster_check_responses"] += len(requested)
                cluster_change = abs(math.fsum(deviations.values()) / len(cluster))
                if cluster_change >= self.allocation["coordinator_allowances"][coordinator]:
                    escalation_count += 1
                    counts["coordinator_root_escalations"] += 1
        synchronize = initialization or escalation_count > 0
        causes = ("initialization",) if initialization else (
            ("coordinator_violation",) if synchronize else ()
        )
        histories, _ = self.history.step(values, synchronization_causes=causes)
        actual_mean = math.fsum(values.values()) / len(values)
        actual_violated = actual_mean >= self.threshold
        if synchronize:
            # The separate root has no sensor readings. Alerts carry no raw
            # readings; one collection obtains every sensor's state directly.
            counts["root_sync_requests"] = len(self.sensors)
            counts["root_sync_responses"] = len(self.sensors)
            counts["root_state_updates"] = len(self.sensors)
            if histories is None:
                raise RuntimeError("Synchronization did not produce a history snapshot.")
            snapshot = normalize_sensor_histories(histories, self.sensors)
            evaluation = self.clustering(
                AlphaClusteringInput(
                    self.history.synchronization_id,
                    self.history.synchronization_id, self.alpha, snapshot,
                )
            )
            if evaluation is None:
                raise RuntimeError(f"{self.weight_method} synchronization unexpectedly deferred clustering.")
            self.partition = tuple(tuple(cluster) for cluster in evaluation["selected_partition"])
            root_allowance = abs(self.threshold - actual_mean)
            if self.allocation_strategy is not None:
                self.allocation = self.allocation_strategy(self.moment, self.partition, root_allowance)
            elif isinstance(self.moment, DiscountedSecondMoment):
                self.allocation = smic_allocation(
                    self.moment.means(), self.moment.second_moments, self.moment.count,
                    self.partition, root_allowance,
                )
            else:
                self.allocation = fmic_allocation(self.moment.means(), self.partition, root_allowance)
            self.references = dict(values)
            self.known_violated = actual_violated
            event = {
                "clustering_event_id": self.history.synchronization_id,
                "synchronization_id": self.history.synchronization_id,
                "bucket_epoch": epoch, "bucket_time_utc": timestamp,
                "algorithm": self.weight_method, "alpha": self.alpha,
                "synchronization_causes": "|".join(causes),
                "raw_sensor_histories": json.dumps(histories, sort_keys=True),
                "normalized_histories": json.dumps(
                    dict(snapshot.normalized_histories)
                    if snapshot.normalized_histories is not None else None, sort_keys=True,
                ),
                "normalization_status": snapshot.normalization_status,
                "selected_partition": json.dumps(self.partition),
                "selected_partition_quality": evaluation["partition_quality"],
                "cluster_count": len(self.partition),
                "coordinator_assignments": json.dumps(
                    {str(i): max(cluster) for i, cluster in enumerate(self.partition)}
                ),
                "coordinator_rule": "lexicographically_highest_member",
                "global_average": actual_mean, "global_violated": int(actual_violated),
                "p90_threshold": self.threshold, "root_allowance": root_allowance,
                "moment_observation_count": self.moment.count,
                "weight_status": self.allocation["weight_status"],
            }
            for field in (
                "first_moments", "raw_weights", "scaled_weights",
                "node_allowances", "coordinator_allowances",
            ):
                event[field] = json.dumps(self.allocation[field], sort_keys=True)
            if self.weight_method == "SMIC":
                for field in ("second_moments", "conservative_terms"):
                    event[field] = json.dumps(self.allocation[field], sort_keys=True)
            self.events.append(event)
        false_safe = actual_violated and not self.known_violated
        self.rows += 1
        self.truth_violations += int(actual_violated)
        self.false_safe += int(false_safe)
        self.false_violated += int(not actual_violated and self.known_violated)
        self.node_triggers += trigger_count
        self.checks += check_count
        self.escalations += escalation_count
        for category in counts:
            self.messages[category] += counts[category]
        if self.capture_decisions:
            self.decision_trace.append({
                "bucket_epoch": epoch,
                "bucket_time_utc": timestamp,
                "entry_references": entry_references,
                "entry_node_allowances": entry_node_allowances,
                "entry_coordinator_allowances": entry_coordinator_allowances,
                "entry_partition": entry_partition,
                "entry_known_state": entry_known_state,
                "triggering_sensor_ids": tuple(sorted(triggering_sensor_ids)),
                "synchronized": synchronize,
                "observed_global_average": actual_mean,
                "global_violated": actual_violated,
                "root_known_state": "VIOLATED" if self.known_violated else "SAFE",
                "post_references": dict(self.references),
                "post_partition": self.partition,
                "post_node_allowances": dict(self.allocation.get("node_allowances", {})),
                "post_coordinator_allowances": dict(
                    self.allocation.get("coordinator_allowances", {})
                ),
                "messages": dict(counts),
                "total_messages": sum(counts.values()),
            })
        if false_safe and self.raise_on_false_safe:
            raise RuntimeError(f"Blocking {self.weight_method} false-safe at {timestamp}.")
        return {
            "synchronized": synchronize, "global_violated": actual_violated,
            "known_violated": self.known_violated, "false_safe": false_safe,
            "node_triggers": trigger_count, "coordinator_checks": check_count,
            "coordinator_escalations": escalation_count, "messages": counts,
            "total_messages": sum(counts.values()),
        }

    def summary(self) -> dict:
        if not self.rows:
            raise ValueError(f"Cannot summarize an uninitialized {self.weight_method} monitor.")
        cluster_sizes = [
            len(cluster) for event in self.events
            for cluster in json.loads(event["selected_partition"])
        ]
        return {
            "algorithm": self.weight_method, "alpha": self.alpha,
            "bucket_count": self.rows,
            "total_messages": sum(self.messages.values()),
            "message_category_totals": dict(self.messages),
            "root_synchronization_count": len(self.events),
            "initialization_count": 1,
            "monitoring_triggered_synchronization_count": len(self.events) - 1,
            "node_trigger_count": self.node_triggers,
            "coordinator_check_count": self.checks,
            "coordinator_to_root_escalation_count": self.escalations,
            "global_threshold_violation_count": self.truth_violations,
            "false_safe_count": self.false_safe,
            "false_violated_count": self.false_violated,
            "correctness_status": "passed" if self.false_safe == 0 and self.false_violated == 0 else "failed",
            "message_counts_reconcile": True,
            "cluster_count_min": min(event["cluster_count"] for event in self.events),
            "cluster_count_max": max(event["cluster_count"] for event in self.events),
            "cluster_size_min": min(cluster_sizes),
            "cluster_size_max": max(cluster_sizes),
            "cluster_size_mean_across_sync_clusters": math.fsum(cluster_sizes) / len(cluster_sizes),
            "root_model": "separate_root_component",
            "monitoring_policy": "absolute distance to threshold; root-known state retained until sync",
            "moment_policy": "all post-initialization raw readings; discounted_sum = 0.5 * prior_sum + reading; mu = discounted_sum / sample_count; never reset at sync",
            "weight_zero_policy": "project fallback: all W_n=0 gives w_n=1; individual zero weights remain zero",
            "protocol": "all clusters checked once per bucket; all triggering peers report; collect remaining peers; alerts carry no raw readings; one root collection per bucket; updates take effect next bucket",
            "correctness_policy": "centralized truth is validation-only and never triggers communication",
            "source": "Clustering for Monitoring Distributed Data Streams, section 1.4 p.10-11, section 1.5.2; separate root and >= boundary are project conventions",
        }


def run_phase3a_fmic(
    root: Path,
    alpha: float | None = None,
    output_dir: Path | None = None,
    *,
    prepared_inputs: dict | None = None,
    raise_on_false_safe: bool = True,
) -> dict:
    return run_phase3a_monitoring(
        root, "FMIC", alpha, output_dir, prepared_inputs=prepared_inputs,
        raise_on_false_safe=raise_on_false_safe,
    )


def run_phase3a_smic(
    root: Path,
    alpha: float | None = None,
    output_dir: Path | None = None,
    *,
    prepared_inputs: dict | None = None,
    raise_on_false_safe: bool = True,
) -> dict:
    return run_phase3a_monitoring(
        root, "SMIC", alpha, output_dir, prepared_inputs=prepared_inputs,
        raise_on_false_safe=raise_on_false_safe,
    )


def load_phase3a_monitoring_inputs(root: Path) -> dict:
    config_path = root / "config" / "phase3a_experiment_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    sensors, _, _, _, _ = validate_phase3a_config(config)
    threshold_config = config["threshold"]
    threshold = float(threshold_config["p90_value"])
    statistics_path = root / threshold_config["statistics_artifact"]
    statistics = pd.read_csv(statistics_path, float_precision="round_trip")
    threshold_rows = statistics.loc[
        statistics["series_name"] == threshold_config["source_series"], "p90"
    ]
    if len(threshold_rows) != 1 or float(threshold_rows.iloc[0]) != threshold:
        raise ValueError("Phase 3A threshold does not match the authoritative statistics artifact.")
    input_path = root / config["input_source"]
    selected = prepare_phase3a_input(
        pd.read_csv(input_path, float_precision="round_trip"), config
    )
    baseline_path = _phase3_reference_directory(root) / "phase3a_phase2_baseline.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    for key in (
        "experiment_name", "input_source", "selected_sensor_ids", "start_timestamp_utc",
        "end_timestamp_utc", "endpoint_convention", "boundary_convention",
    ):
        if baseline[key] != config[key]:
            raise ValueError(f"Phase 2 baseline does not match {key}.")
    if (
        baseline["bucket_count"] != len(selected)
        or baseline["threshold_value"] != threshold
        or baseline["threshold_source_series"] != threshold_config["source_series"]
        or baseline["correctness_status"] != "passed"
        or baseline["algorithm"] != "phase2"
        or sum(baseline["message_category_totals"].values()) != baseline["total_messages"]
    ):
        raise ValueError("Invalid matched Phase 2 baseline for Phase 3A comparison.")
    return {
        "root": root.resolve(), "config": config, "sensors": sensors,
        "threshold": threshold, "threshold_config": threshold_config,
        "selected": selected, "baseline": baseline,
        "config_path": config_path, "input_path": input_path,
        "statistics_path": statistics_path,
        "baseline_path": baseline_path,
    }


def run_phase3a_monitoring(
    root: Path,
    weight_method: str,
    alpha: float | None = None,
    output_dir: Path | None = None,
    *,
    prepared_inputs: dict | None = None,
    raise_on_false_safe: bool = True,
) -> dict:
    if weight_method not in ("FMIC", "SMIC"):
        raise ValueError("weight_method must be FMIC or SMIC.")
    inputs = prepared_inputs or load_phase3a_monitoring_inputs(root)
    if inputs["root"] != root.resolve():
        raise ValueError("Prepared Phase 3A inputs belong to a different repository root.")
    config = inputs["config"]
    sensors = inputs["sensors"]
    threshold = inputs["threshold"]
    threshold_config = inputs["threshold_config"]
    selected = inputs["selected"]
    baseline = inputs["baseline"]
    alpha = float(config["baseline_alpha"] if alpha is None else alpha)
    if not math.isfinite(alpha) or not 0 <= alpha <= 1:
        raise ValueError("Production alpha must be finite and in [0, 1].")
    if output_dir is None and alpha != float(config["baseline_alpha"]):
        raise ValueError("A non-baseline alpha requires an explicit output directory to preserve baseline artifacts.")

    monitor = FMICMonitor(
        sensors, threshold, alpha, weight_method=weight_method,
        raise_on_false_safe=raise_on_false_safe,
    )
    for row in selected.to_dict("records"):
        monitor.step(
            {sensor: row[f"{sensor}_temperature"] for sensor in sensors},
            row["bucket_time_utc"].isoformat(), int(row["bucket_epoch"]),
        )
    summary = monitor.summary()
    if summary["global_threshold_violation_count"] != baseline["global_violation_count"]:
        raise ValueError(f"{weight_method} centralized truth does not match the Phase 2 baseline.")
    summary.update({
        key: config[key] for key in (
            "experiment_name", "input_source", "selected_sensor_ids",
            "start_timestamp_utc", "end_timestamp_utc", "endpoint_convention",
            "boundary_convention",
        )
    })
    summary.update({
        "threshold_source_series": threshold_config["source_series"],
        "threshold_value": threshold,
        "threshold_statistic": threshold_config["statistic"],
        "threshold_statistics_artifact": threshold_config["statistics_artifact"],
        "phase2_total_messages": baseline["total_messages"],
        "phase2_resynchronizations": baseline["resynchronization_count"],
        "centralized_sensor_transmission_reference": len(selected) * len(sensors),
        "message_reduction_vs_phase2_percent": (
            100 * (1 - summary["total_messages"] / baseline["total_messages"])
        ),
        "message_reduction_vs_centralized_percent": (
            100 * (1 - summary["total_messages"] / (len(selected) * len(sensors)))
        ),
        "input_sha256": hashlib.sha256(inputs["input_path"].read_bytes()).hexdigest(),
        "config_sha256": hashlib.sha256(inputs["config_path"].read_bytes()).hexdigest(),
        "phase2_baseline_sha256": hashlib.sha256(inputs["baseline_path"].read_bytes()).hexdigest(),
    })
    if weight_method == "SMIC":
        summary.update({
            "second_moment_policy": "source unnormalized sum of squared deviations; no m or m-1 divisor; persistent; 0.25*prior + k/(k+1)*(reading - 0.5*old_mu)^2",
            "second_moment_source": "Appendix 1 printed p.22/PDF 26 defines i=1..m, resolving section 1.4's i=0 typo; recurrence printed p.24/PDF 28",
            "second_moment_numerics": "nonnegative stable update; no negative-variance clamp or tolerance",
            "moment_payload_policy": "sensor moments/weights piggyback on existing root-sync responses; allowances on existing state updates; no additional transmissions",
            "comparison_status": "fixed-alpha comparison with matched Phase 2; not a universal algorithm ranking",
        })
    target_dir = _resolve_legacy_output_dir(root, output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    events_path = target_dir / f"phase3a_{weight_method.lower()}_events.csv"
    summary_path = target_dir / f"phase3a_{weight_method.lower()}_summary.json"
    events = pd.DataFrame.from_records(monitor.events)
    events["threshold_source_series"] = threshold_config["source_series"]
    events.to_csv(events_path, index=False)
    summary["events_sha256"] = hashlib.sha256(events_path.read_bytes()).hexdigest()
    summary_path.write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return summary


def _phase3a_cluster_metrics(events: pd.DataFrame, sensor_count: int) -> dict:
    if events.empty:
        raise ValueError("A monitoring run must include its initialization clustering event.")
    cluster_counts = [len(json.loads(value)) for value in events["selected_partition"]]
    cluster_sizes = [
        len(cluster)
        for partition_value in events["selected_partition"]
        for cluster in json.loads(partition_value)
    ]
    memberships = sum(cluster_sizes)
    if memberships != len(events) * sensor_count:
        raise ValueError("Synchronization partitions must cover each sensor exactly once.")
    return {
        "cluster_count_min": min(cluster_counts),
        "cluster_count_max": max(cluster_counts),
        "cluster_count_mean_per_sync_event": math.fsum(cluster_counts) / len(events),
        "cluster_size_min": min(cluster_sizes),
        "cluster_size_max": max(cluster_sizes),
        "cluster_size_mean_across_sync_clusters": memberships / len(cluster_sizes),
    }


def _phase3a_validate_us321(root: Path) -> dict:
    path = _phase3_reference_directory(root) / "phase3a_validation_summary.json"
    if not path.exists():
        raise FileNotFoundError(f"US-3.21 validation record not found: {path}")
    validation = json.loads(path.read_text(encoding="utf-8"))
    runs = validation.get("production_replays", [])
    if (
        validation.get("story") != "US-3.21"
        or validation.get("test_result", {}).get("status") != "passed"
        or len(runs) != 2
        or any(run.get("correctness_status") != "passed" for run in runs)
        or any(run.get("message_counts_reconcile") is not True for run in runs)
    ):
        raise ValueError("US-3.21 validation gate is not recorded as passed for both algorithms.")
    return validation


def _phase3a_alpha_plots(results_path: Path, output_dir: Path, phase2_messages: int) -> list[str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    results = pd.read_csv(results_path)
    if len(results) != 38 or results[["algorithm", "alpha_label"]].duplicated().any():
        raise ValueError("Saved alpha results must contain 38 unique algorithm/alpha rows.")
    passing = results.loc[results["correctness_status"] == "passed"]
    plots = (
        ("total_messages", "Actual transmissions", "phase3a_messages_vs_alpha.png"),
        ("root_synchronization_count", "Root synchronizations (including initialization)", "phase3a_synchronizations_vs_alpha.png"),
        ("cluster_count_mean_per_sync_event", "Mean clusters per synchronization event", "phase3a_clustering_vs_alpha.png"),
    )
    for metric, ylabel, filename in plots:
        figure, axis = plt.subplots(figsize=(8, 5), constrained_layout=True)
        for algorithm, color in (("FMIC", "#1f77b4"), ("SMIC", "#d62728")):
            subset = passing.loc[passing["algorithm"] == algorithm].sort_values("alpha")
            axis.plot(subset["alpha"], subset[metric], marker="o", color=color, label=f"{algorithm} (correctness passed)")
        if metric == "total_messages":
            axis.axhline(phase2_messages, color="#444444", linestyle="--", label="Matched Phase 2 (fixed benchmark)")
        axis.set_xlabel("Alpha (tested grid: 0.05 to 0.95 by 0.05)")
        axis.set_ylabel(ylabel)
        axis.set_title(f"Phase 3A fixed A/C/D/E/F/G cohort: {ylabel} vs alpha")
        axis.set_xticks([step / 20 for step in range(1, 20)])
        axis.grid(True, alpha=0.25)
        axis.legend()
        figure.savefig(output_dir / filename, dpi=160)
        plt.close(figure)
    return [filename for _, _, filename in plots]


def run_phase3a_alpha_sweep(root: Path) -> dict:
    validation = _phase3a_validate_us321(root)
    inputs = load_phase3a_monitoring_inputs(root)
    alpha_steps = tuple(range(1, 20))
    alpha_grid = tuple(step / 20 for step in alpha_steps)
    alpha_labels = tuple(f"{step / 20:.2f}" for step in alpha_steps)
    if len(set(alpha_grid)) != 19 or alpha_labels[1] != "0.10":
        raise RuntimeError("The approved alpha grid is not unique or lacks the baseline alpha.")

    artifacts_dir = _phase3_operational_directory(root) / "legacy_runs"
    reference_dir = _phase3_reference_directory(root)
    implementation_path = Path(__file__).resolve()
    protected_paths = [
        inputs["input_path"], inputs["statistics_path"], inputs["config_path"], inputs["baseline_path"],
        reference_dir / "phase3a_fmic_events.csv",
        reference_dir / "phase3a_fmic_summary.json",
        reference_dir / "phase3a_smic_events.csv",
        reference_dir / "phase3a_smic_summary.json",
    ]
    protected_hashes = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in protected_paths
    }
    baseline_summaries = {
        method: json.loads((reference_dir / f"phase3a_{method.lower()}_summary.json").read_text(encoding="utf-8"))
        for method in ("FMIC", "SMIC")
    }
    output_rows = []
    event_frames = []
    category_names = tuple(MESSAGE_CATEGORIES)
    with tempfile.TemporaryDirectory(prefix="phase3a-alpha-sweep-") as temporary:
        temporary_dir = Path(temporary)
        for method, runner in (("FMIC", run_phase3a_fmic), ("SMIC", run_phase3a_smic)):
            for step, alpha, alpha_label in zip(alpha_steps, alpha_grid, alpha_labels):
                summary = runner(
                    root, alpha, temporary_dir, prepared_inputs=inputs,
                    raise_on_false_safe=False,
                )
                events_path = temporary_dir / f"phase3a_{method.lower()}_events.csv"
                events = pd.read_csv(events_path, float_precision="round_trip")
                if (
                    len(events) != summary["root_synchronization_count"]
                    or summary["total_messages"] != sum(summary["message_category_totals"].values())
                    or summary["message_counts_reconcile"] is not True
                ):
                    raise ValueError(f"{method} alpha {alpha_label} event or message totals do not reconcile.")
                cluster_metrics = _phase3a_cluster_metrics(
                    events, len(inputs["sensors"])
                )
                if alpha_label == "0.10":
                    expected = baseline_summaries[method]
                    for key in (
                        "total_messages", "message_category_totals",
                        "root_synchronization_count", "false_safe_count",
                        "false_violated_count", "correctness_status",
                    ):
                        if summary[key] != expected[key]:
                            raise RuntimeError(f"{method} alpha=0.10 regression in {key}.")
                    if summary["events_sha256"] != expected["events_sha256"]:
                        raise RuntimeError(f"{method} alpha=0.10 event fingerprint changed.")
                row = {
                    "algorithm": method,
                    "alpha": alpha,
                    "alpha_label": alpha_label,
                    "selected_sensor_ids": json.dumps(inputs["sensors"], separators=(",", ":")),
                    "start_timestamp_utc": inputs["config"]["start_timestamp_utc"],
                    "end_timestamp_utc": inputs["config"]["end_timestamp_utc"],
                    "endpoint_convention": inputs["config"]["endpoint_convention"],
                    "boundary_convention": json.dumps(inputs["config"]["boundary_convention"], sort_keys=True, separators=(",", ":")),
                    "bucket_count": summary["bucket_count"],
                    "threshold_value": summary["threshold_value"],
                    "correctness_status": summary["correctness_status"],
                    "false_safe_count": summary["false_safe_count"],
                    "false_violated_count": summary["false_violated_count"],
                    "global_threshold_violation_count": summary["global_threshold_violation_count"],
                    "total_messages": summary["total_messages"],
                    "initialization_count": summary["initialization_count"],
                    "monitoring_triggered_synchronization_count": summary["monitoring_triggered_synchronization_count"],
                    "root_synchronization_count": summary["root_synchronization_count"],
                    "node_trigger_count": summary["node_trigger_count"],
                    "coordinator_check_count": summary["coordinator_check_count"],
                    "coordinator_to_root_escalation_count": summary["coordinator_to_root_escalation_count"],
                    "message_counts_reconcile": summary["message_counts_reconcile"],
                    "phase2_total_messages": inputs["baseline"]["total_messages"],
                    "reduction_vs_phase2_percent": summary["message_reduction_vs_phase2_percent"],
                    "centralized_sensor_transmission_reference": summary["centralized_sensor_transmission_reference"],
                    "reduction_vs_centralized_percent": summary["message_reduction_vs_centralized_percent"],
                    **cluster_metrics,
                    "input_sha256": summary["input_sha256"],
                    "config_sha256": summary["config_sha256"],
                    "phase2_baseline_sha256": summary["phase2_baseline_sha256"],
                    "events_sha256": summary["events_sha256"],
                    "implementation_sha256": hashlib.sha256(implementation_path.read_bytes()).hexdigest(),
                    "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    "failure_reason": "" if summary["correctness_status"] == "passed" else "Correctness gate failed.",
                }
                row.update(summary["message_category_totals"])
                output_rows.append(row)
                events["alpha_label"] = alpha_label
                event_frames.append(events)

    results = pd.DataFrame.from_records(output_rows).sort_values(
        ["algorithm", "alpha"], kind="stable"
    ).reset_index(drop=True)
    expected_pairs = {(method, label) for method in ("FMIC", "SMIC") for label in alpha_labels}
    actual_pairs = set(zip(results["algorithm"], results["alpha_label"]))
    if len(results) != 38 or actual_pairs != expected_pairs or results.duplicated(["algorithm", "alpha_label"]).any():
        raise ValueError("Alpha sweep did not produce exactly 38 unique approved algorithm/alpha results.")
    if any(results[category].lt(0).any() for category in category_names):
        raise ValueError("Message category totals cannot be negative.")
    results["reconciled_total_messages"] = results[list(category_names)].sum(axis=1)
    if not results["reconciled_total_messages"].eq(results["total_messages"]).all():
        raise ValueError("At least one alpha result does not reconcile to transmission categories.")

    output_dir = artifacts_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    results_path = output_dir / "phase3a_alpha_results.csv"
    events_path = output_dir / "phase3a_alpha_events.csv"
    results.to_csv(results_path, index=False, float_format="%.17g")
    pd.concat(event_frames, ignore_index=True).to_csv(events_path, index=False)
    plots = _phase3a_alpha_plots(
        results_path, output_dir, inputs["baseline"]["total_messages"]
    )

    minima = {}
    for method in ("FMIC", "SMIC"):
        eligible = results.loc[
            (results["algorithm"] == method) & (results["correctness_status"] == "passed")
        ]
        if eligible.empty:
            minima[method] = {"status": "no correctness-passing alpha", "alphas": []}
        else:
            minimum = int(eligible["total_messages"].min())
            tied = eligible.loc[eligible["total_messages"] == minimum]
            minima[method] = {
                "status": "minimum observed on this dataset and tested grid",
                "minimum_total_messages": minimum,
                "alphas": tied["alpha_label"].tolist(),
                "representative_alpha_if_needed": tied["alpha_label"].min(),
                "results": tied.to_dict("records"),
            }
    paired = []
    for label in alpha_labels:
        fmic = results.loc[(results["algorithm"] == "FMIC") & (results["alpha_label"] == label)].iloc[0]
        smic = results.loc[(results["algorithm"] == "SMIC") & (results["alpha_label"] == label)].iloc[0]
        paired.append({
            "alpha": label,
            "fmic_minus_smic_total_messages": int(fmic["total_messages"] - smic["total_messages"]),
            "fmic_minus_smic_root_synchronizations": int(fmic["root_synchronization_count"] - smic["root_synchronization_count"]),
            "fmic_minus_smic_node_triggers": int(fmic["node_trigger_count"] - smic["node_trigger_count"]),
            "fmic_minus_smic_coordinator_checks": int(fmic["coordinator_check_count"] - smic["coordinator_check_count"]),
            "message_category_differences_fmic_minus_smic": {
                category: int(fmic[category] - smic[category]) for category in category_names
            },
        })
    trends = {}
    for method in ("FMIC", "SMIC"):
        values = results.loc[results["algorithm"] == method].sort_values("alpha")["total_messages"].tolist()
        if all(left <= right for left, right in zip(values, values[1:])):
            trend = "monotonic nondecreasing"
        elif all(left >= right for left, right in zip(values, values[1:])):
            trend = "monotonic nonincreasing"
        else:
            trend = "irregular across the tested grid"
        trends[method] = trend
    protected_after = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in protected_paths
    }
    if protected_after != protected_hashes:
        raise RuntimeError("The alpha sweep modified a protected baseline or input artifact.")
    summary = {
        "story": "US-3.22",
        "experiment_name": inputs["config"]["experiment_name"],
        "alpha_grid": list(alpha_labels),
        "run_count": len(results),
        "cohort": inputs["sensors"],
        "start_timestamp_utc": inputs["config"]["start_timestamp_utc"],
        "end_timestamp_utc": inputs["config"]["end_timestamp_utc"],
        "endpoint_convention": inputs["config"]["endpoint_convention"],
        "bucket_count": len(inputs["selected"]),
        "threshold_source_series": inputs["threshold_config"]["source_series"],
        "threshold_value": inputs["threshold"],
        "boundary_convention": inputs["config"]["boundary_convention"],
        "phase2_baseline": inputs["baseline"],
        "centralized_sensor_transmission_reference": len(inputs["selected"]) * len(inputs["sensors"]),
        "baseline_alpha_results": results.loc[results["alpha_label"] == "0.10"].to_dict("records"),
        "minimum_observed_by_algorithm": minima,
        "paired_fmic_smic_differences": paired,
        "message_sensitivity_trend": trends,
        "cluster_size_aggregation": "Include the initialization partition; mean cluster size is total sensor memberships across all selected partitions at synchronization events divided by total clusters across those events.",
        "mean_cluster_count_aggregation": "Arithmetic mean of cluster counts, one count per synchronization event including initialization.",
        "correctness_status_by_algorithm": {
            method: "passed" if results.loc[results["algorithm"] == method, "correctness_status"].eq("passed").all() else "failed"
            for method in ("FMIC", "SMIC")
        },
        "message_accounting_status": "passed" if results["message_counts_reconcile"].all() else "failed",
        "us321_validation": {
            "status": validation["test_result"]["status"],
            "tests": validation["test_result"]["tests"],
        },
        "provenance": {
            "input_sha256": output_rows[0]["input_sha256"],
            "config_sha256": output_rows[0]["config_sha256"],
            "phase2_baseline_sha256": output_rows[0]["phase2_baseline_sha256"],
            "implementation_sha256": output_rows[0]["implementation_sha256"],
            "implementation_sha256": output_rows[0]["implementation_sha256"],
            "protected_artifact_sha256_before_and_after": protected_hashes,
        },
        "outputs": {
            "results_csv": results_path.name,
            "events_csv": events_path.name,
            "plots": plots,
        },
        "limitations": [
            "One deterministic six-sensor temperature dataset and one threshold; results do not imply statistical significance or generalization.",
            "Minimum observed alpha is an in-sample descriptive result on this dataset and tested grid, not a universal or theoretically optimal setting.",
            "No intermittent sensor availability or Phase 3B behavior was evaluated.",
        ],
    }
    summary_path = output_dir / "phase3a_comparison_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return summary


def build_phase3a_history_events(
    source_frame,
    threshold,
    *,
    experiment_config,
    alpha_values=None,
    phase2_builder=build_phase2_trace,
):
    """Build compact event rows using the validated experiment configuration."""
    sensor_ids, sensor_columns, _, _, _ = validate_phase3a_config(experiment_config)
    authoritative_threshold = float(experiment_config["threshold"]["p90_value"])
    if float(threshold) != authoritative_threshold:
        raise ValueError("Supplied Phase 3A threshold does not match the authoritative config P90.")
    selected = prepare_phase3a_input(source_frame, experiment_config)
    if alpha_values is None:
        alpha_values = (float(experiment_config["baseline_alpha"]),)
    else:
        alpha_values = tuple(alpha_values)
    if not alpha_values:
        raise ValueError("At least one alpha value is required.")

    selected_times = selected["bucket_time_utc"]
    validation_summary = {
        "row_count": len(selected),
        "first_timestamp": selected_times.iloc[0].isoformat(),
        "last_timestamp": selected_times.iloc[-1].isoformat(),
        "selected_sensor_ids": list(sensor_ids),
        "missing_value_count": int(selected[sensor_columns].isna().sum().sum()),
        "timestamp_gap_count": int(
            selected_times.diff().dt.total_seconds().iloc[1:].ne(
                experiment_config["sampling_interval_seconds"]
            ).sum()
        ),
    }
    print("Phase 3A input validation: " + json.dumps(validation_summary, sort_keys=True))

    # The existing Phase 2 monitor supplies synchronization timing only; this is
    # not a separate Phase 2 comparison run or output artifact.
    baseline = phase2_builder(selected, sensor_columns, threshold)
    if len(baseline) != len(selected):
        raise ValueError("Phase 2 synchronization trace does not match Phase 3A input rows.")
    if not baseline["global_state_evaluable"].astype(bool).all():
        raise ValueError("Phase 3A fixed-cohort input unexpectedly has an undefined global state.")
    if baseline["observed_online_sensor_count"].ne(len(sensor_ids)).any():
        raise ValueError("Phase 3A input violated the fixed six-sensor cohort assumption.")
    if baseline["event_membership_changed"].astype(bool).any():
        raise ValueError("Phase 3A input unexpectedly changed sensor membership.")

    tracker = Phase3AHistoryTracker(sensor_ids)
    event_rows = []
    for row_index, input_row in selected.iterrows():
        baseline_row = baseline.iloc[row_index]
        if int(input_row["bucket_epoch"]) != int(baseline_row["bucket_epoch"]):
            raise ValueError(f"Phase 2/Phase 3A bucket mismatch at row {row_index}.")
        causes = ()
        if int(baseline_row["event_resync_performed"]) == 1:
            causes = tuple(
                cause for cause in str(baseline_row["event_resync_causes"]).split("|") if cause
            )
        histories, causes = tracker.step(
            {
                sensor_id: input_row[f"{sensor_id}_temperature"]
                for sensor_id in sensor_ids
            },
            synchronization_causes=causes,
        )
        if (histories is not None) != (int(baseline_row["event_resync_performed"]) == 1):
            raise ValueError(f"Phase 3A history synchronization mismatch at row {row_index}.")
        if histories is None:
            continue

        normalization = normalize_sensor_histories(histories, sensor_ids)
        alpha_inputs = build_alpha_clustering_inputs(
            tracker.synchronization_id, normalization, alpha_values
        )
        for alpha_input in alpha_inputs:
            evaluation = evaluate_alpha_clustering(alpha_input)
            if evaluation is None:
                raise RuntimeError("A completed stable-cohort event was unexpectedly deferred.")
            partition = evaluation["selected_partition"]
            coordinators = {
                str(cluster_index): max(cluster)
                for cluster_index, cluster in enumerate(partition)
            }
            event_rows.append({
                "clustering_event_id": tracker.synchronization_id,
                "synchronization_id": tracker.synchronization_id,
                "bucket_epoch": int(input_row["bucket_epoch"]),
                "bucket_time_utc": input_row["bucket_time_utc"].isoformat(),
                "synchronization_causes": "|".join(causes),
                "alpha": alpha_input.alpha,
                "raw_sensor_histories": json.dumps(dict(normalization.raw_histories), sort_keys=True),
                "normalized_histories": json.dumps(
                    dict(normalization.normalized_histories)
                    if normalization.normalized_histories is not None else None,
                    sort_keys=True,
                ),
                "normalization_status": normalization.normalization_status,
                "partition_basis": normalization.partition_basis,
                "zero_history_fallback": int(normalization.zero_history_fallback),
                "selected_partition": json.dumps(partition),
                "selected_partition_quality": evaluation["partition_quality"],
                "cluster_count": evaluation["cluster_count"],
                "coordinator_assignments": json.dumps(coordinators, sort_keys=True),
                "coordinator_rule": "lexicographically_highest_member",
                "p90_threshold": authoritative_threshold,
                "threshold_source_series": experiment_config["threshold"]["source_series"],
                "threshold_status": experiment_config["threshold"]["status"],
            })
    return pd.DataFrame.from_records(event_rows), baseline


def build_phase3a_phase2_baseline_summary(trace, experiment_config):
    """Summarize and validate the matched Phase 2 trace for Phase 3A."""
    expected_count = experiment_config["expected_bucket_count"]
    if len(trace) != expected_count:
        raise ValueError("Matched Phase 2 trace has the wrong Phase 3A bucket count.")

    sensor_count = len(experiment_config["selected_sensor_ids"])
    observed_counts = trace["observed_online_sensor_count"]
    if not observed_counts.eq(sensor_count).all():
        raise ValueError("Matched Phase 2 sensor count changed during the stable run.")
    membership_changes = int(trace["event_membership_changed"].sum())
    membership_syncs = int(trace["event_resync_triggered_by_membership_change"].sum())
    if membership_changes or membership_syncs:
        raise ValueError("Matched Phase 2 run unexpectedly reported membership changes.")

    category_columns = (
        "trigger_message_count",
        "request_message_count",
        "response_message_count",
        "broadcast_message_count",
    )
    category_totals = {
        column: int(trace[column].sum()) for column in category_columns
    }
    total_messages = int(trace["total_message_count"].sum())
    if sum(category_totals.values()) != total_messages:
        raise ValueError("Matched Phase 2 communication categories do not reconcile.")

    global_evaluation_count = int(trace["global_state_evaluable"].sum())
    if global_evaluation_count != expected_count:
        raise ValueError("Matched Phase 2 did not evaluate every Phase 3A bucket.")

    threshold = experiment_config["threshold"]
    return {
        "experiment_name": experiment_config["experiment_name"],
        "input_source": experiment_config["input_source"],
        "algorithm": "phase2",
        "selected_sensor_ids": experiment_config["selected_sensor_ids"],
        "start_timestamp_utc": experiment_config["start_timestamp_utc"],
        "end_timestamp_utc": experiment_config["end_timestamp_utc"],
        "endpoint_convention": experiment_config["endpoint_convention"],
        "boundary_convention": experiment_config["boundary_convention"],
        "bucket_count": expected_count,
        "global_evaluation_count": global_evaluation_count,
        "threshold_source_series": threshold["source_series"],
        "threshold_statistic": threshold["statistic"],
        "threshold_value": float(threshold["p90_value"]),
        "total_messages": total_messages,
        "message_category_totals": category_totals,
        "resynchronization_count": int(trace["event_resync_performed"].sum()),
        "membership_change_event_count": membership_changes,
        "membership_triggered_synchronization_count": membership_syncs,
        "observed_sensor_count_min": int(observed_counts.min()),
        "observed_sensor_count_max": int(observed_counts.max()),
        "global_violation_count": int(trace["global_violation"].sum()),
        "centralized_sensor_transmission_reference": expected_count * sensor_count,
        "message_counts_reconcile": True,
        "correctness_status": "passed",
    }




EXPERIMENT_NAME = "phase3a_stable_cohort"


CONTROL_MODE = "fixed_singletons_equal_allowances"


SENSORS = tuple("ACDEFG")


PHASE2_CATEGORIES = (
    "trigger_message_count",
    "request_message_count",
    "response_message_count",
    "broadcast_message_count",
)


PHASE3_CATEGORY_MAP = {
    "trigger_message_count": "coordinator_root_escalations",
    "request_message_count": "root_sync_requests",
    "response_message_count": "root_sync_responses",
    "broadcast_message_count": "root_state_updates",
}


PHASE3_PEER_CATEGORIES = (
    "node_trigger_messages",
    "cluster_check_requests",
    "cluster_check_responses",
)


def _sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load_phase3_monitor():
    return FMICMonitor, MESSAGE_CATEGORIES


def fixed_singleton_hooks(sensor_ids: tuple[str, ...]):
    partition = tuple((sensor,) for sensor in sensor_ids)

    def clustering(_: Any) -> dict[str, Any]:
        return {"selected_partition": partition, "partition_quality": 0.0}

    def allocation_strategy(
        _moment: Any, selected: tuple[tuple[str, ...], ...], allowance: float
    ):
        del _moment
        if selected != partition:
            raise ValueError(
                f"Fixed singleton partition changed: expected {partition}, got {selected}."
            )
        if not math.isfinite(allowance) or allowance < 0:
            raise ValueError("Fixed singleton root allowance must be finite and nonnegative.")
        return {
            "first_moments": {},
            "raw_weights": dict.fromkeys(sensor_ids, 1.0),
            "scaled_weights": dict.fromkeys(sensor_ids, 1.0),
            "node_allowances": dict.fromkeys(sensor_ids, allowance),
            "coordinator_allowances": dict.fromkeys(sensor_ids, allowance),
            "weight_status": CONTROL_MODE,
        }

    return clustering, allocation_strategy


def run_phase3_control(
    frame: pd.DataFrame,
    sensor_columns: list[str],
    threshold: float,
    monitor_class: Any,
):
    sensor_ids = tuple(column.removesuffix("_temperature") for column in sensor_columns)
    if not sensor_ids or len(set(sensor_ids)) != len(sensor_ids):
        raise ValueError("Phase 3 control requires a nonempty, unique sensor cohort.")
    clustering, allocation_strategy = fixed_singleton_hooks(sensor_ids)
    monitor = monitor_class(
        sensor_ids,
        threshold,
        alpha=0.1,
        clustering=clustering,
        weight_method="FMIC",
        allocation_strategy=allocation_strategy,
        raise_on_false_safe=False,
        capture_decisions=True,
    )
    for row in frame[["bucket_epoch", "bucket_time_utc", *sensor_columns]].itertuples(
        index=False, name=None
    ):
        epoch, timestamp, *readings = row
        monitor.step(
            dict(zip(sensor_ids, map(float, readings))),
            str(timestamp),
            int(epoch),
        )
    return monitor


def _phase2_snapshot(row: pd.Series, sensor_columns: list[str]) -> tuple[dict, dict]:
    references = {}
    allowances = {}
    for column in sensor_columns:
        sensor = column.removesuffix("_temperature")
        reference = float(row[f"entry_{sensor}_reference_value"])
        allowance = float(row[f"entry_{sensor}_local_allowance"])
        if math.isfinite(reference):
            references[sensor] = reference
        if math.isfinite(allowance):
            allowances[sensor] = allowance
    return references, allowances


def compare_decisions(
    phase2_trace: pd.DataFrame,
    phase3_trace: list[dict],
    sensor_columns: list[str],
    phase3_events: list[dict],
) -> dict[str, Any]:
    check_names = (
        "timestamps",
        "synchronization_flags",
        "trigger_sensor_sets",
        "entry_references",
        "entry_allowances",
        "entry_coordinator_allowances",
        "entry_root_known_state",
        "post_root_known_state",
        "observed_global_mean",
        "message_categories",
        "message_totals",
    )
    passed_counts = dict.fromkeys(check_names, 0)
    mismatch_counts = dict.fromkeys(check_names, 0)
    phase2_length = len(phase2_trace)
    phase3_length = len(phase3_trace)
    trace_length_mismatch = phase2_length != phase3_length
    diagnostics = []

    def add_diagnostic(
        mismatch_type: str,
        index: int,
        field: str,
        expected: Any,
        observed: Any,
        phase2_value: Any = None,
        phase3_value: Any = None,
    ) -> None:
        if index < phase2_length:
            row = phase2_trace.iloc[index]
            bucket_epoch = int(row["bucket_epoch"])
            bucket_time = str(row["bucket_time_utc"])
        elif index < phase3_length:
            row = phase3_trace[index]
            bucket_epoch = int(row["bucket_epoch"])
            bucket_time = str(row["bucket_time_utc"])
        else:
            bucket_epoch = None
            bucket_time = None
        diagnostic = {
            "mismatch_type": mismatch_type,
            "bucket_index": index,
            "bucket_epoch": bucket_epoch,
            "bucket_time_utc": bucket_time,
            "field": field,
            "expected": expected,
            "observed": observed,
        }
        if phase2_value is not None or phase3_value is not None:
            diagnostic["phase2"] = phase2_value
            diagnostic["phase3"] = phase3_value
        diagnostics.append(diagnostic)

    if trace_length_mismatch:
        add_diagnostic(
            "trace_length",
            min(phase2_length, phase3_length),
            "decision_trace_length",
            phase2_length,
            phase3_length,
        )

    def numeric_maps_equal(expected: dict, observed: dict) -> bool:
        if expected.keys() != observed.keys():
            return False
        return all(
            math.isclose(
                float(expected[key]),
                float(observed[key]),
                rel_tol=0.0,
                abs_tol=1e-12,
            )
            for key in expected
        )

    prior_phase2_state = None

    def record(index: int, field: str, phase2_value: Any, phase3_value: Any, equal: bool):
        if equal:
            passed_counts[field] += 1
            return
        mismatch_counts[field] += 1
        add_diagnostic(
            "bucket_comparison",
            index,
            field,
            phase2_value,
            phase3_value,
            phase2_value,
            phase3_value,
        )

    for index, (phase2_row, phase3_row) in enumerate(
        zip((row for _, row in phase2_trace.iterrows()), phase3_trace)
    ):
        p2_timestamp = (
            int(phase2_row["bucket_epoch"]),
            str(phase2_row["bucket_time_utc"]),
        )
        p3_timestamp = (
            int(phase3_row["bucket_epoch"]),
            str(phase3_row["bucket_time_utc"]),
        )
        record(index, "timestamps", p2_timestamp, p3_timestamp, p2_timestamp == p3_timestamp)

        p2_sync = bool(phase2_row["event_resync_performed"])
        p3_sync = bool(phase3_row["synchronized"])
        record(index, "synchronization_flags", p2_sync, p3_sync, p2_sync == p3_sync)

        p2_triggers = tuple(
            name for name in str(phase2_row["event_triggering_sensor_names"]).split("|") if name
        )
        p3_triggers = tuple(phase3_row["triggering_sensor_ids"])
        record(
            index, "trigger_sensor_sets", p2_triggers, p3_triggers,
            p2_triggers == p3_triggers,
        )

        p2_references, p2_allowances = _phase2_snapshot(phase2_row, sensor_columns)
        p3_references = phase3_row["entry_references"]
        p3_allowances = phase3_row["entry_node_allowances"]
        record(
            index, "entry_references", p2_references, p3_references,
            numeric_maps_equal(p2_references, p3_references),
        )
        record(
            index, "entry_allowances", p2_allowances, p3_allowances,
            numeric_maps_equal(p2_allowances, p3_allowances),
        )
        p3_coordinator_allowances = phase3_row["entry_coordinator_allowances"]
        record(
            index, "entry_coordinator_allowances", p2_allowances,
            p3_coordinator_allowances,
            numeric_maps_equal(p2_allowances, p3_coordinator_allowances),
        )
        record(
            index, "entry_root_known_state", prior_phase2_state,
            phase3_row["entry_known_state"],
            prior_phase2_state == phase3_row["entry_known_state"],
        )
        p2_root_state = str(phase2_row["root_known_state"])
        p3_root_state = str(phase3_row["root_known_state"])
        record(
            index, "post_root_known_state", p2_root_state, p3_root_state,
            p2_root_state == p3_root_state,
        )
        p2_mean = float(phase2_row["observed_global_average"])
        p3_mean = float(phase3_row["observed_global_average"])
        record(
            index,
            "observed_global_mean",
            p2_mean,
            p3_mean,
            math.isclose(p2_mean, p3_mean, rel_tol=0.0, abs_tol=1e-12),
        )

        p2_messages = {
            category: int(phase2_row[category]) for category in PHASE2_CATEGORIES
        }
        p3_messages = phase3_row["messages"]
        mapped_p3_messages = {
            phase2_category: int(p3_messages[phase3_category])
            for phase2_category, phase3_category in PHASE3_CATEGORY_MAP.items()
        }
        record(
            index, "message_categories", p2_messages, mapped_p3_messages,
            p2_messages == mapped_p3_messages,
        )
        p2_total = int(phase2_row["total_message_count"])
        p3_total = int(phase3_row["total_messages"])
        record(index, "message_totals", p2_total, p3_total, p2_total == p3_total)
        prior_phase2_state = p2_root_state

    expected_partition = tuple(
        (column.removesuffix("_temperature"),) for column in sensor_columns
    )
    synchronized_rows = [row for row in phase3_trace if row["synchronized"]]
    expected_event_times = [
        (int(row["bucket_epoch"]), str(row["bucket_time_utc"]))
        for row in synchronized_rows
    ]
    trace_index_by_time = {
        (int(row["bucket_epoch"]), str(row["bucket_time_utc"])): index
        for index, row in enumerate(phase3_trace)
    }

    def event_time(event: dict) -> tuple[int, str] | None:
        try:
            return int(event["bucket_epoch"]), str(event["bucket_time_utc"])
        except (KeyError, TypeError, ValueError):
            return None

    event_diagnostics = []

    def add_event_diagnostic(
        event_index: int,
        field: str,
        expected: Any,
        observed: Any,
    ) -> None:
        if event_index < len(synchronized_rows):
            row = synchronized_rows[event_index]
            bucket_index = trace_index_by_time[
                (int(row["bucket_epoch"]), str(row["bucket_time_utc"]))
            ]
        elif event_index < len(phase3_events):
            bucket_index = trace_index_by_time.get(
                event_time(phase3_events[event_index]), phase3_length
            )
        else:
            bucket_index = phase3_length
        add_diagnostic(
            "sync_event_configuration",
            bucket_index,
            field,
            expected,
            observed,
        )
        event_diagnostics.append(diagnostics[-1])

    for event_index in range(max(len(expected_event_times), len(phase3_events))):
        expected_time = (
            expected_event_times[event_index]
            if event_index < len(expected_event_times)
            else None
        )
        observed_time = (
            event_time(phase3_events[event_index])
            if event_index < len(phase3_events)
            else None
        )
        if expected_time != observed_time:
            add_event_diagnostic(
                event_index,
                "phase3_sync_event_timeline",
                expected_time,
                observed_time,
            )
    if not expected_event_times and not phase3_events:
        add_event_diagnostic(
            0,
            "phase3_sync_event_timeline",
            "at least one initialization synchronization",
            [],
        )

    expected_allowance_sensors = tuple(
        column.removesuffix("_temperature") for column in sensor_columns
    )
    expected_partition_json = [list(cluster) for cluster in expected_partition]
    for event_index, event in enumerate(phase3_events):
        try:
            observed_partition = json.loads(event["selected_partition"])
        except (KeyError, TypeError, json.JSONDecodeError):
            observed_partition = event.get("selected_partition")
        if observed_partition != expected_partition_json:
            add_event_diagnostic(
                event_index,
                "selected_partition",
                expected_partition_json,
                observed_partition,
            )

        try:
            expected_root_allowance = abs(
                float(event["p90_threshold"]) - float(event["global_average"])
            )
        except (KeyError, TypeError, ValueError):
            expected_root_allowance = None
        try:
            observed_root_allowance = float(event["root_allowance"])
        except (KeyError, TypeError, ValueError):
            observed_root_allowance = event.get("root_allowance")
        try:
            root_allowance_matches = (
                expected_root_allowance is not None
                and math.isclose(
                    float(expected_root_allowance),
                    float(observed_root_allowance),
                    rel_tol=0.0,
                    abs_tol=1e-12,
                )
            )
        except (TypeError, ValueError):
            root_allowance_matches = False
        if not root_allowance_matches:
            add_event_diagnostic(
                event_index,
                "root_allowance",
                expected_root_allowance,
                observed_root_allowance,
            )

        expected_allowances = (
            dict.fromkeys(expected_allowance_sensors, expected_root_allowance)
            if expected_root_allowance is not None
            else {}
        )
        for field in ("node_allowances", "coordinator_allowances"):
            try:
                observed_allowances = json.loads(event[field])
            except (KeyError, TypeError, json.JSONDecodeError):
                observed_allowances = event.get(field)
            try:
                allowances_match = (
                    expected_root_allowance is not None
                    and numeric_maps_equal(expected_allowances, observed_allowances)
                )
            except (AttributeError, TypeError, ValueError):
                allowances_match = False
            if not allowances_match:
                add_event_diagnostic(
                    event_index,
                    field,
                    expected_allowances,
                    observed_allowances,
                )

    event_config_valid = (
        len(phase3_events) > 0
        and len(phase3_events) == len(synchronized_rows)
        and not event_diagnostics
    )
    peer_diagnostics = []
    for index, row in enumerate(phase3_trace):
        for category in PHASE3_PEER_CATEGORIES:
            observed_count = int(row["messages"][category])
            if observed_count != 0:
                add_diagnostic(
                    "peer_traffic",
                    index,
                    f"messages.{category}",
                    0,
                    observed_count,
                )
                peer_diagnostics.append(diagnostics[-1])
    peer_traffic_zero = not peer_diagnostics
    diagnostics.sort(
        key=lambda diagnostic: (
            diagnostic["bucket_index"],
            diagnostic["field"],
        )
    )
    first_mismatch = diagnostics[0] if diagnostics else None
    passed = not diagnostics and event_config_valid and peer_traffic_zero
    return {
        "passed": passed,
        "bucket_count": phase2_length,
        "expected_trace_length": phase2_length,
        "actual_trace_length": phase3_length,
        "trace_length_mismatch": trace_length_mismatch,
        "compared_bucket_count": min(phase2_length, phase3_length),
        "mismatch_type": first_mismatch["mismatch_type"] if first_mismatch else None,
        "per_bucket_checks": {
            name: {
                "passed_buckets": passed_counts[name],
                "mismatched_buckets": mismatch_counts[name],
            }
            for name in check_names
        },
        "fixed_singleton_partition_and_allowances_at_every_sync": event_config_valid,
        "phase3_peer_traffic_zero": peer_traffic_zero,
        "first_mismatch": first_mismatch,
        "diagnostics": diagnostics,
    }


def _phase2_reference_directory(root: Path) -> Path:
    current = root / "artifacts" / "phase2_outputs"
    if not current.is_dir():
        raise FileNotFoundError(
            "Current Phase 2 prerequisites are required; historical root-level fallbacks are disabled."
        )
    return current


def _phase3_operational_directory(root: Path) -> Path:
    return root / "artifacts" / "phase3_operational"


def _phase3_reference_directory(root: Path) -> Path:
    return _phase3_operational_directory(root) / "references"


def _resolve_legacy_output_dir(root: Path, output_dir: Path | None) -> Path:
    root = root.resolve()
    target = (
        output_dir.resolve()
        if output_dir is not None
        else (_phase3_operational_directory(root) / "legacy_runs").resolve()
    )
    protected = (
        root / "artifacts" / "phase3_outputs",
        _phase3_reference_directory(root),
        root / "artifacts" / "phase3_archive",
        *(root / "artifacts" / name for name in ("phase2_current", "phase2_outputs", "phase2_operational", "phase2_archive")),
        *(root / name for name in ("scripts", "config", "Data", ".git")),
    )
    if (
        target == root or root.is_relative_to(target)
        or target == root / "artifacts"
        or any(target == path or target.is_relative_to(path) for path in protected)
    ):
        raise ValueError("Phase 3A outputs cannot overlap user results, operational references, archive or source.")
    if target.is_relative_to(root / "artifacts") and not target.is_relative_to(
        _phase3_operational_directory(root) / "legacy_runs"
    ):
        raise ValueError("Legacy Phase 3A output under artifacts must use phase3_operational/legacy_runs.")
    return target


def _resolve_operational_dir(output_dir: Path) -> Path:
    """Resolve the run-specific operational directory paired with selected outputs."""
    output_dir = output_dir.resolve()
    if output_dir.name == "phase3_outputs":
        return output_dir.with_name("phase3_operational")
    return output_dir / "phase3_operational"


def _phase3_layout(output_dir: Path, operational_dir: Path) -> dict[str, str]:
    return {
        "outputs_directory": output_dir.name,
        "operational_directory": operational_dir.name,
        "pairing": "sibling" if operational_dir.parent == output_dir.parent else "contained",
    }


def _relative_artifact_path(source_directory: Path, target: Path) -> str:
    return Path(os.path.relpath(target, source_directory)).as_posix()


def _validate_contract(root: Path):
    artifacts = root / "artifacts"
    reference_directory = _phase3_reference_directory(root)
    config_path = root / "config" / "phase3a_experiment_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    expected = {
        "experiment_name": EXPERIMENT_NAME,
        "selected_sensor_ids": list(SENSORS),
        "start_timestamp_utc": "2022-02-24T18:50:00+00:00",
        "end_timestamp_utc": "2022-03-10T15:53:00+00:00",
        "expected_bucket_count": 19984,
        "sampling_interval_seconds": 60,
        "endpoint_convention": "inclusive",
        "boundary_convention": {
            "safe_when": "metric < threshold",
            "violated_when": "metric >= threshold",
        },
        "input_source": "artifacts/aligned_phase1_temperature.csv",
    }
    for key, value in expected.items():
        if config.get(key) != value:
            raise ValueError(f"Phase 3A configuration does not match approved {key}.")
    threshold_config = config["threshold"]
    if (
        threshold_config.get("source_series") != EXPERIMENT_NAME
        or threshold_config.get("statistic") != "p90"
        or threshold_config.get("statistics_artifact")
        != "artifacts/phase1_average_statistics.csv"
    ):
        raise ValueError("Phase 3A threshold provenance is not the authoritative cohort p90.")

    input_path = root / expected["input_source"]
    stats_path = root / threshold_config["statistics_artifact"]
    revised_path = root / PHASE2_SUMMARY
    revised_events_path = root / PHASE2_EVENTS
    historical_path = reference_directory / "phase3a_phase2_baseline.json"
    implementation_path = root / "scripts" / "phase3_implement.py"
    if implementation_path.resolve() != Path(__file__).resolve():
        raise ValueError("Phase 3 implementation must be imported from the selected root.")
    phase2_path = root / "scripts" / "shared_monitoring_engine.py"
    runner_path = Path(__file__).resolve()
    for path in (input_path, stats_path, revised_path, revised_events_path, historical_path):
        if not path.is_file():
            raise FileNotFoundError(f"Required US-3.24 input is missing: {path}")

    stats = pd.read_csv(stats_path, float_precision="round_trip")
    p90 = stats.loc[stats["series_name"].eq(EXPERIMENT_NAME), "p90"]
    if len(p90) != 1:
        raise ValueError("Expected exactly one authoritative phase3a_stable_cohort p90.")
    threshold = float(p90.iloc[0])
    if not math.isfinite(threshold) or threshold != float(threshold_config["p90_value"]):
        raise ValueError("Authoritative p90 differs from the locked config value.")

    revised = load_validated_phase2(root)
    if (
        revised.get("story") != "US-3.23"
        or revised.get("algorithm") != "phase2"
        or revised.get("threshold_policy") != "two_sided_absolute_distance_equal_allowances"
        or revised.get("correctness_status") != "passed"
        or revised.get("false_safe_count") != 0
        or revised.get("false_violated_count") != 0
        or revised.get("bucket_count") != expected["expected_bucket_count"]
        or revised.get("threshold_value") != threshold
        or revised.get("selected_sensor_ids") != list(SENSORS)
        or revised.get("message_counts_reconcile") is not True
    ):
        raise ValueError("Revised US-3.23 Phase 2 baseline has not passed its required gate.")
    if revised.get("global_threshold_violation_count") != 1999:
        raise ValueError("Revised Phase 2 baseline has an unexpected threshold violation count.")
    baseline_provenance = revised.get("provenance", {})
    expected_baseline_hashes = {
        "input_sha256": _sha256(input_path),
        "statistics_sha256": _sha256(stats_path),
        "config_sha256": _sha256(config_path),
        "historical_baseline_sha256": _sha256(historical_path),
    }
    if any(
        baseline_provenance.get(key) != value
        for key, value in expected_baseline_hashes.items()
    ) or baseline_provenance.get("code_sha256") != _sha256(phase2_path):
        raise ValueError(
            "Revised Phase 2 baseline inputs or current producer identity are incompatible."
        )
    if _sha256(revised_events_path) != revised.get("events_sha256"):
        raise ValueError("Revised Phase 2 event file does not match its saved hash.")
    historical = json.loads(historical_path.read_text(encoding="utf-8"))
    if historical.get("total_messages") != 38087 or historical.get("resynchronization_count") != 2107:
        raise ValueError("Historical signed-margin Phase 2 artifact is not the expected preserved baseline.")
    protected = {
        path: _sha256(path)
        for path in reference_directory.iterdir()
        if path.is_file()
    }
    protected.update({
        path: _sha256(path)
        for path in artifacts.glob("phase2_*")
        if path.is_file()
    })
    protected[revised_path] = _sha256(revised_path)
    protected[revised_events_path] = _sha256(revised_events_path)
    protected[input_path] = _sha256(input_path)
    protected[stats_path] = _sha256(stats_path)
    protected[config_path] = _sha256(config_path)
    protected[implementation_path] = _sha256(implementation_path)
    protected[revised_path] = _sha256(revised_path)
    protected[revised_events_path] = _sha256(revised_events_path)
    return {
        "config": config,
        "threshold": threshold,
        "input_path": input_path,
        "stats_path": stats_path,
        "phase2_path": phase2_path,
        "implementation_path": implementation_path,
        "runner_path": runner_path,
        "revised_path": revised_path,
        "revised_events_path": revised_events_path,
        "historical_path": historical_path,
        "revised": revised,
        "protected": protected,
    }


def _read_locked_observations(contract: dict[str, Any]) -> tuple[pd.DataFrame, list[str]]:
    config = contract["config"]
    frame = pd.read_csv(
        contract["input_path"],
        keep_default_na=False,
        na_values=[""],
        float_precision="round_trip",
    )
    timestamps = pd.to_datetime(frame["bucket_time_utc"], utc=True, errors="raise")
    selected_mask = timestamps.between(
        config["start_timestamp_utc"], config["end_timestamp_utc"]
    )
    selected = frame.loc[selected_mask].copy()
    timestamps = timestamps.loc[selected.index]
    if (
        len(selected) != config["expected_bucket_count"]
        or not timestamps.is_monotonic_increasing
        or timestamps.duplicated().any()
        or timestamps.iloc[0] != pd.Timestamp(config["start_timestamp_utc"])
        or timestamps.iloc[-1] != pd.Timestamp(config["end_timestamp_utc"])
        or not timestamps.diff().iloc[1:].eq(pd.Timedelta(seconds=60)).all()
    ):
        raise ValueError("Phase 3A observations fail the locked timestamp/count/cadence contract.")
    epochs = pd.to_numeric(selected["bucket_epoch"], errors="raise")
    if not all(epoch == timestamp.timestamp() for epoch, timestamp in zip(epochs, timestamps)):
        raise ValueError("Bucket epochs do not match their UTC timestamps.")
    sensor_columns = [f"{sensor}_temperature" for sensor in SENSORS]
    missing = set(sensor_columns) - set(selected.columns)
    if missing:
        raise ValueError(f"Missing approved sensor columns: {sorted(missing)}")
    selected = selected[["bucket_epoch", "bucket_time_utc", *sensor_columns]].copy()
    selected = selected.reset_index(drop=True)
    for column in sensor_columns:
        selected[column] = pd.to_numeric(selected[column], errors="raise")
    if selected[sensor_columns].isna().any().any():
        raise ValueError("Locked Phase 3A cohort must have six complete, non-imputed readings.")
    if not selected[sensor_columns].map(lambda value: math.isfinite(float(value))).all().all():
        raise ValueError("Locked Phase 3A readings must be finite.")
    return selected, sensor_columns


def _write_events(
    output_path: Path,
    phase2_trace: pd.DataFrame,
    phase3_trace: list[dict],
    sensor_columns: list[str],
) -> None:
    records = []
    for phase2_row, phase3_row in zip(
        (row for _, row in phase2_trace.iterrows()), phase3_trace
    ):
        if not phase2_row["event_resync_performed"] and not phase3_row["triggering_sensor_ids"]:
            continue
        entry_references, entry_allowances = _phase2_snapshot(phase2_row, sensor_columns)
        records.append({
            "bucket_epoch": int(phase2_row["bucket_epoch"]),
            "bucket_time_utc": str(phase2_row["bucket_time_utc"]),
            "initialization": bool(phase2_row["event_initialization_performed"]),
            "triggering_sensor_ids": json.dumps(
                list(phase3_row["triggering_sensor_ids"]), separators=(",", ":")
            ),
            "phase2_triggering_sensor_ids": json.dumps(
                [name for name in str(phase2_row["event_triggering_sensor_names"]).split("|") if name],
                separators=(",", ":"),
            ),
            "entry_root_known_state": phase3_row["entry_known_state"] or "",
            "root_known_state": str(phase2_row["root_known_state"]),
            "entry_references": json.dumps(entry_references, sort_keys=True, separators=(",", ":")),
            "entry_allowances": json.dumps(entry_allowances, sort_keys=True, separators=(",", ":")),
            "post_references": json.dumps(phase3_row["post_references"], sort_keys=True, separators=(",", ":")),
            "post_allowances": json.dumps(phase3_row["post_node_allowances"], sort_keys=True, separators=(",", ":")),
            "phase2_messages": int(phase2_row["total_message_count"]),
            "phase3_messages": int(phase3_row["total_messages"]),
            "phase2_trigger_messages": int(phase2_row["trigger_message_count"]),
            "phase3_root_escalations": int(
                phase3_row["messages"]["coordinator_root_escalations"]
            ),
        })
    pd.DataFrame.from_records(records).to_csv(output_path, index=False, lineterminator="\n")


def run_phase3a_protocol_equivalence(
    root: Path,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    contract = _validate_contract(root)
    output_dir = (
        output_dir.resolve()
        if output_dir is not None
        else _phase3_operational_directory(root)
    )
    reference_directory = _phase3_reference_directory(root).resolve()
    if (
        output_dir == root or root.is_relative_to(output_dir)
        or output_dir.is_relative_to(reference_directory)
        or output_dir.is_relative_to(root / "artifacts" / "phase3_archive")
        or any(output_dir.is_relative_to(root / name) for name in ("scripts", "config", "Data", ".git"))
    ):
        raise ValueError("Runtime equivalence output overlaps source, protected references or the removal archive.")
    if output_dir == _phase3_operational_directory(root):
        run_path = output_dir / RUN_PATH
        existing = _read_json(run_path) if run_path.is_file() else {}
        if existing.get("kind") != "production" or existing.get("status") != "in_progress":
            raise ValueError("Runtime equivalence must use an isolated candidate directory outside the active operational run.")
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / RUN_PATH
    events_path = output_dir / EQUIVALENCE_EVENTS_PATH
    frame, sensor_columns = _read_locked_observations(contract)
    phase2_trace = build_phase2_trace(
        frame, sensor_columns, contract["threshold"], round_output=False
    )

    monitor_class, phase3_categories = load_phase3_monitor()
    monitor = run_phase3_control(
        frame, sensor_columns, contract["threshold"], monitor_class
    )
    phase3_trace = monitor.decision_trace
    comparison = compare_decisions(
        phase2_trace, phase3_trace, sensor_columns, monitor.events
    )

    phase2_correctness = root_correctness_summary(phase2_trace)
    oracle_states = phase2_trace["oracle_global_state"].tolist()
    phase3_false_safe = sum(
        truth == "VIOLATED" and row["root_known_state"] == "SAFE"
        for truth, row in zip(oracle_states, phase3_trace)
    )
    phase3_false_violated = sum(
        truth == "SAFE" and row["root_known_state"] == "VIOLATED"
        for truth, row in zip(oracle_states, phase3_trace)
    )
    phase3_oracle = {
        "false_safe_count": int(phase3_false_safe),
        "false_violated_count": int(phase3_false_violated),
        "true_violation_count": int(sum(state == "VIOLATED" for state in oracle_states)),
        "correctness_status": (
            "passed" if not phase3_false_safe and not phase3_false_violated else "failed"
        ),
    }
    phase2_totals = {
        category: int(phase2_trace[category].sum()) for category in PHASE2_CATEGORIES
    }
    phase3_summary = monitor.summary()
    phase3_totals = {
        category: int(phase3_summary["message_category_totals"][category])
        for category in phase3_categories
    }
    synchronizations = int(phase2_trace["event_resync_performed"].sum())
    trigger_count = int(phase2_trace["trigger_message_count"].sum())
    phase2_triggers_by_sensor = {
        sensor: sum(
            sensor in tuple(
                name for name in str(value).split("|") if name
            )
            for value in phase2_trace["event_triggering_sensor_names"]
        )
        for sensor in SENSORS
    }
    phase3_triggers_by_sensor = {
        sensor: sum(
            sensor in row["triggering_sensor_ids"] for row in phase3_trace
        )
        for sensor in SENSORS
    }
    mapped_phase3_totals = {
        phase2_category: phase3_totals[phase3_category]
        for phase2_category, phase3_category in PHASE3_CATEGORY_MAP.items()
    }
    formula_total = 18 * synchronizations + trigger_count
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    _write_events(events_path, phase2_trace, phase3_trace, sensor_columns)

    protected_after = {
        str(path): _sha256(path) for path in contract["protected"]
    }
    protected_unchanged = all(
        protected_after[str(path)] == digest
        for path, digest in contract["protected"].items()
    )
    checks = {
        "phase2_prerequisite_correctness": phase2_correctness["correctness_status"] == "passed",
        "phase3_oracle_correctness": phase3_oracle["correctness_status"] == "passed",
        "phase3_monitor_oracle_counters_match": (
            phase3_summary["false_safe_count"] == phase3_oracle["false_safe_count"]
            and phase3_summary["false_violated_count"] == phase3_oracle["false_violated_count"]
            and phase3_summary["global_threshold_violation_count"]
            == phase3_oracle["true_violation_count"]
        ),
        "locked_bucket_count": len(frame) == 19984,
        "locked_true_violation_count": phase3_oracle["true_violation_count"] == 1999,
        "per_bucket_equivalence": comparison["passed"],
        "mapped_message_categories": phase2_totals == mapped_phase3_totals,
        "message_totals_equal": (
            int(phase2_trace["total_message_count"].sum()) == phase3_summary["total_messages"]
        ),
        "six_sensor_message_formula": phase3_summary["total_messages"] == formula_total,
        "per_sensor_trigger_counts": phase2_triggers_by_sensor == phase3_triggers_by_sensor,
        "phase3_peer_categories_zero": comparison["phase3_peer_traffic_zero"],
        "message_categories_reconcile": (
            int(phase2_trace["total_message_count"].sum()) == sum(phase2_totals.values())
            and phase3_summary["total_messages"] == sum(phase3_totals.values())
        ),
        "no_membership_changes": int(phase2_trace["event_membership_changed"].sum()) == 0,
        "protected_artifacts_unchanged": protected_unchanged,
        "revised_baseline_events_hash_valid": (
            _sha256(contract["revised_events_path"])
            == contract["revised"].get("events_sha256")
        ),
    }
    result = {
        "experiment_name": EXPERIMENT_NAME,
        "story": "US-3.24",
        "mode": CONTROL_MODE,
        "alpha": "not_applicable",
        "threshold_policy": "two_sided_absolute_distance_equal_allowances",
        "protocol": {
            "sensors": list(SENSORS),
            "root": "separate_component",
            "boundary": "safe iff mean < threshold; violated iff mean >= threshold",
            "trigger": "abs(current - entry_reference) >= entry_allowance",
            "allowance": "abs(threshold - synchronized_mean) for every singleton",
            "activation": "synchronization references and allowances apply to the next bucket",
            "message_unit": "one actual transmission between distinct components",
        },
        "contract": {
            "input": "artifacts/aligned_phase1_temperature.csv",
            "statistics": "artifacts/phase1_average_statistics.csv",
            "threshold_statistic": "phase3a_stable_cohort p90",
            "threshold_value": contract["threshold"],
            "start_timestamp_utc": contract["config"]["start_timestamp_utc"],
            "end_timestamp_utc": contract["config"]["end_timestamp_utc"],
            "endpoint_convention": "inclusive",
            "bucket_count": len(frame),
            "sampling_interval_seconds": 60,
            "centralized_sensor_transmission_reference": len(frame) * len(SENSORS),
        },
        "phase2_reference": {
            "artifact": contract["revised_path"].relative_to(root).as_posix(),
            "artifact_sha256": _sha256(contract["revised_path"]),
            "event_artifact_sha256": _sha256(contract["revised_events_path"]),
            "baseline_recorded_code_sha256": contract["revised"]["provenance"]["code_sha256"],
            "current_code_sha256": _sha256(contract["phase2_path"]),
            "correctness": phase2_correctness,
        },
        "phase3_control": {
            "mode": CONTROL_MODE,
            "internal_alpha_for_ignored_callback": 0.1,
            "reported_alpha": "not_applicable",
            "partition": [list(cluster) for cluster in tuple((sensor,) for sensor in SENSORS)],
            "allocation": "equal root-distance allowance; moment values ignored",
            "correctness": phase3_oracle,
        },
        "comparison": comparison,
        "checks": checks,
        "status": "passed" if all(checks.values()) else "failed",
        "message_mapping": {
            "phase2_categories": phase2_totals,
            "phase3_categories": phase3_totals,
            "mapped_phase3_categories": mapped_phase3_totals,
            "phase2_triggers_by_sensor": phase2_triggers_by_sensor,
            "phase3_triggers_by_sensor": phase3_triggers_by_sensor,
            "phase2_total_messages": int(phase2_trace["total_message_count"].sum()),
            "phase3_total_messages": int(phase3_summary["total_messages"]),
            "root_synchronizations_including_initialization": synchronizations,
            "genuine_trigger_notifications": trigger_count,
            "six_sensor_formula": "18*S + L",
            "formula_total": formula_total,
            "phase3_peer_categories": {
                category: phase3_totals[category] for category in PHASE3_PEER_CATEGORIES
            },
        },
        "outputs": {
            "summary": summary_path.name,
            "events": events_path.name,
            "events_sha256": _sha256(events_path),
        },
        "interpretation": (
            "Non-clustered, equal-allowance protocol-equivalence validation only; "
            "not an alpha experiment and not evidence of FMIC/SMIC clustering savings."
        ),
        "provenance": {
            "input_sha256": _sha256(contract["input_path"]),
            "statistics_sha256": _sha256(contract["stats_path"]),
            "config_sha256": _sha256(root / "config" / "phase3a_experiment_config.json"),
            "phase2_monitoring_sha256": _sha256(contract["phase2_path"]),
            "phase3_implementation_sha256": _sha256(contract["implementation_path"]),
            "runner_sha256": _sha256(contract["runner_path"]),
            "test_sha256": {
                name: _sha256(root / "scripts" / name)
                for name in VALIDATION_TEST_MODULES
            },
            "revised_phase2_baseline_sha256": _sha256(contract["revised_path"]),
            "historical_phase2_baseline_sha256": _sha256(contract["historical_path"]),
            "protected_artifact_sha256_before_and_after": {
                str(path.relative_to(root)): {
                    "before": digest,
                    "after": protected_after[str(path)],
                }
                for path, digest in contract["protected"].items()
            },
        },
        "validation_commands": [
            "python -B -m scripts.phase3_test --checks behavior replay",
            "python -B -m scripts.shared_monitoring_engine",
            "python -B -m scripts.phase3_implement --equivalence --output-dir artifacts/phase3_equivalence",
        ],
        "validation": {
            "fresh_process_reproducibility_test": "scripts.phase3_test.ProductionReproducibilityTests.test_fresh_process_reproduction",
            "test_suite_status": "not_run",
            "test_suite_result": "not_run",
            "test_count": None,
        },
    }
    _write_json_atomic(summary_path, {
        "schema_version": 2, "kind": "equivalence", "status": result["status"],
        "equivalence": result,
    })
    return result


ALPHA_LABELS = tuple(f"{step / 20:.2f}" for step in range(1, 20))


WITHIN_CATEGORIES = MESSAGE_CATEGORIES[:3]


ROOT_WIDE_CATEGORIES = MESSAGE_CATEGORIES[4:]


OUTPUT_PREFIX = "phase3a_us325_"


RUN_PATH = "phase3_run.json"
RESULTS_PATH = "phase3_results.csv"
CLUSTER_SIZES_PATH = "phase3_cluster_sizes.csv"
SNAPSHOTS_PATH = "phase3_snapshots.csv"
SUMMARY_PATH = "phase3_summary.json"
EQUIVALENCE_EVENTS_PATH = "phase3_equivalence_events.csv"
VALIDATION_PATH = "phase3_validation.json"
OUTPUT_FILES = (RESULTS_PATH, CLUSTER_SIZES_PATH, SNAPSHOTS_PATH, SUMMARY_PATH)
OPERATIONAL_RUN_FILES = (RUN_PATH, EQUIVALENCE_EVENTS_PATH, VALIDATION_PATH)
BUNDLE_FILES = OUTPUT_FILES + OPERATIONAL_RUN_FILES


def _json_fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()


def _write_csv_records(path: Path, rows: list[dict[str, Any]]) -> None:
    columns = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _artifact_inventory(directory: Path, operational_dir: Path) -> dict[str, Any]:
    inventory = {}
    keys = {
        RESULTS_PATH: ["config_id", "alpha_label"],
        CLUSTER_SIZES_PATH: ["config_id", "alpha_label", "cluster_size"],
        SNAPSHOTS_PATH: ["config_id", "alpha_label", "synchronization_id"],
        EQUIVALENCE_EVENTS_PATH: ["bucket_epoch"],
    }
    for location, name in (
        *(("outputs", name) for name in OUTPUT_FILES),
        ("operational", EQUIVALENCE_EVENTS_PATH),
    ):
        base = directory if location == "outputs" else operational_dir
        path = base / name
        metadata: dict[str, Any] = {"sha256": _sha256(path)}
        if path.suffix == ".csv":
            with path.open(encoding="utf-8", newline="") as stream:
                reader = csv.reader(stream)
                metadata.update(columns=next(reader), row_count=sum(1 for _ in reader), key=keys[name])
        inventory[f"{location}/{name}"] = metadata
    return inventory


def _bundle_semantics() -> dict[str, Any]:
    return {
        "layout": "Four user-readable files in phase3_outputs; run manifest, C0 event file and receipt in its paired phase3_operational directory.",
        "counts": "Integer actual transmissions, checks, buckets or events; never bytes/latency.",
        "percentages": "Fields ending in percent are percentages, not fractions.",
        "alpha": "Dimensionless; controls use null alpha and alpha_label=not_applicable.",
        "nulls": "Empty CSV cells mean unavailable/not applicable, never zero; no imputation.",
        "time": "UTC ISO timestamps and Unix epoch seconds; inclusive endpoints.",
        "temperature": "Degrees Celsius; allowances and first moments use temperature units.",
        "second_moments": "Unnormalized discounted central squared deviations (degrees Celsius squared); not variance.",
        "initialization": "Included in synchronization/event counts; not a moment observation.",
        "precision": "Round-trip numerical precision; original observation order retained.",
        "snapshots": "All C1/C2 syncs; FMIC/SMIC alpha 0.10 and every tied tested-grid minimum only. No C0 snapshots.",
        "equivalence_events": "All C0 initialization/root-sync events, not all per-bucket decisions.",
        "comparators": {
            "primary": "Revised two-sided Phase 2/C0; identified by baseline source hash.",
            "historical": "Preserved signed-margin Phase 2; never relabeled as the primary.",
            "centralized": "One actual sensor transmission per cohort member per bucket.",
        },
    }


def load_phase3_run(root: Path, directory: Path) -> dict[str, Any]:
    """Validate a paired outputs/operational run and resolve its receipt in memory."""
    root = root.resolve()
    directory = directory.resolve()
    operational_dir = _resolve_operational_dir(directory)
    for name in OUTPUT_FILES:
        if not (directory / name).is_file():
            raise FileNotFoundError(f"Required saved Phase 3 output is missing: {directory / name}")
    for name in OPERATIONAL_RUN_FILES:
        if not (operational_dir / name).is_file():
            raise FileNotFoundError(f"Required Phase 3 operational evidence is missing: {operational_dir / name}")
    if {path.name for path in directory.iterdir() if path.is_file()} != set(OUTPUT_FILES):
        raise ValueError("Phase 3 outputs directory contains unexpected files.")
    if {path.name for path in operational_dir.iterdir() if path.is_file()} != set(OPERATIONAL_RUN_FILES):
        raise ValueError("Phase 3 operational run directory contains unexpected root-level files.")
    run = _read_json(operational_dir / RUN_PATH)
    expected_layout = _phase3_layout(directory, operational_dir)
    if (
        run.get("schema_version") != 2 or run.get("kind") != "production"
        or run.get("status") != "passed" or not run.get("run_id")
        or run.get("semantics") != _bundle_semantics()
        or run.get("layout") != expected_layout
    ):
        raise ValueError("Saved Phase 3 bundle is incomplete, incompatible or failed.")
    if run.get("artifacts") != _artifact_inventory(directory, operational_dir):
        raise ValueError("Saved Phase 3 artifact hashes, schemas or row counts differ from the run inventory.")
    for section in ("completion", "failures"):
        record = run.get(section, {})
        if record.get("status") != "passed" or record.get("run_id") != run["run_id"]:
            raise ValueError("Saved Phase 3 reports do not identify the same successful current run.")
    if run["failures"].get("failure_count") != 0 or run["failures"].get("failures") != []:
        raise ValueError("Saved Phase 3 bundle contains failures.")
    summary = _read_json(directory / SUMMARY_PATH)
    summary_reference = run.get("summary")
    if (
        summary.get("schema_version") != 1 or summary.get("kind") != "summary"
        or summary.get("status") != "passed" or summary.get("run_id") != run["run_id"]
        or not isinstance(summary_reference, dict)
        or summary_reference != {"artifact": SUMMARY_PATH, "sha256": _sha256(directory / SUMMARY_PATH)}
    ):
        raise ValueError("Saved Phase 3 summary is stale, incompatible or belongs to another run.")
    report = dict(summary["comparison"])
    if report.get("status") != "passed" or report.get("run_id") != run["run_id"]:
        raise ValueError("Saved Phase 3 summary is failed or belongs to another run.")
    reference = report["validation"]
    receipt_path = operational_dir / VALIDATION_PATH
    receipt = _read_validation_record(root, receipt_path)
    if reference != {
        "artifact": _relative_artifact_path(directory, receipt_path),
        "sha256": receipt["record_sha256"],
    }:
        raise ValueError("Saved Phase 3 independent validation receipt reference differs.")
    report["validation"] = receipt
    if report["provenance"].get("equivalence_sha256") != _json_fingerprint(run["equivalence"]):
        raise ValueError("Saved Phase 3 equivalence section hash differs.")
    return {**run, "comparison": report}


def _read_result_frames(directory: Path) -> dict[str, pd.DataFrame]:
    results = pd.read_csv(
        directory / RESULTS_PATH,
        dtype={
            "alpha_label": str, "revised_phase2_message_difference": "Int64",
            "matched_singleton_message_difference": "Int64",
            "matched_singleton_root_synchronization_difference": "Int64",
        },
        float_precision="round_trip",
    )
    if "configuration_kind" not in results or not results["configuration_kind"].isin(["control", "clustered"]).all():
        raise ValueError("Saved Phase 3 results require explicit control/clustered configuration_kind.")
    control = results["configuration_kind"].eq("control")
    if not results.loc[control, "config_id"].isin(["C0", "C1", "C2"]).all() or results.loc[~control, "config_id"].isin(["C0", "C1", "C2"]).any():
        raise ValueError("Saved Phase 3 configuration_kind does not match configuration identity.")
    contrasts = [
        "reduction_vs_revised_phase2_percent", "revised_phase2_message_difference",
        "matched_singleton_message_difference", "matched_singleton_reduction_percent",
        "matched_singleton_root_synchronization_difference",
    ]
    if not results.loc[control, ["alpha", *contrasts]].isna().all().all():
        raise ValueError("Control alpha and clustered-only contrast fields must be null.")
    sizes = pd.read_csv(directory / CLUSTER_SIZES_PATH, dtype={"alpha_label": str}, float_precision="round_trip")
    control_sizes = sizes["config_id"].isin(["C0", "C1", "C2"])
    if not sizes.loc[control_sizes, "alpha_label"].eq("not_applicable").all():
        raise ValueError("Control cluster-size alpha labels must be not_applicable.")
    return {
        "controls": results.loc[control].drop(columns=["configuration_kind", *contrasts]).reset_index(drop=True),
        "alphas": results.loc[~control].drop(columns="configuration_kind").reset_index(drop=True),
        "control_cluster_sizes": sizes.loc[control_sizes].drop(columns="alpha_label").reset_index(drop=True),
        "cluster_sizes": sizes.loc[~control_sizes].reset_index(drop=True),
        "snapshots": pd.read_csv(directory / SNAPSHOTS_PATH, dtype={"alpha_label": str}, float_precision="round_trip"),
    }


VALIDATION_TEST_MODULES = (
    "phase3_test.py",
    "test_phase2_monitoring.py",
)


REGRESSION_REFERENCES = {
    ("C0", "not_applicable"): (9159, 467),
    ("C1", "not_applicable"): (8964, 457),
    ("C2", "not_applicable"): (8962, 457),
    ("FMIC", "0.10"): (11922, 293),
    ("SMIC", "0.10"): (11902, 293),
    ("FMIC", "0.65"): (8722, 436),
    ("SMIC", "0.65"): (8720, 436),
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            json.dump(payload, stream, indent=2, allow_nan=False)
            stream.write("\n")
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _integrity_differences(
    before: dict[str, str], after: dict[str, str]
) -> list[dict[str, str | None]]:
    differences = []
    for path in sorted(set(before) | set(after)):
        if before.get(path) != after.get(path):
            differences.append({
                "path": path,
                "before_sha256": before.get(path),
                "after_sha256": after.get(path),
            })
    return differences


def _failure_provenance(root: Path) -> dict[str, Any]:
    candidates = {
        "runner_sha256": Path(__file__).resolve(),
        "config_sha256": root / "config" / "phase3a_experiment_config.json",
        "input_sha256": root / "artifacts" / "aligned_phase1_temperature.csv",
        "statistics_sha256": root / "artifacts" / "phase1_average_statistics.csv",
        "historical_phase2_baseline_sha256": (
            _phase3_reference_directory(root) / "phase3a_phase2_baseline.json"
        ),
        "phase2_monitoring_sha256": root / "scripts" / "shared_monitoring_engine.py",
        "phase3_implementation_sha256": root / "scripts" / "phase3_implement.py",
    }
    hashes: dict[str, Any] = {
        key: _sha256(path)
        for key, path in candidates.items()
        if path.is_file()
    }
    hashes["test_sha256"] = {
        name: _sha256(root / "scripts" / name)
        for name in VALIDATION_TEST_MODULES
        if (root / "scripts" / name).is_file()
    }
    return hashes


def _persist_failure(
    root: Path,
    run_id: str,
    state: dict[str, Any],
    error: Exception,
    integrity: dict[str, Any],
    output_dir: Path,
    operational_dir: Path,
) -> None:
    failure: dict[str, Any] = {
        "stage": state.get("stage", "unknown"),
        "failure_reason": f"{type(error).__name__}: {error}",
    }
    configuration = state.get("configuration")
    if configuration is not None:
        failure["configuration"] = configuration
        if "algorithm" in configuration:
            failure["algorithm"] = configuration["algorithm"]
        if "alpha" in configuration:
            failure["alpha"] = configuration["alpha"]
    metrics = state.get("metrics")
    if metrics is not None:
        failure.update(metrics)
    record = {
        "story": "US-3.26",
        "run_id": run_id,
        "status": "failed",
        "failure_count": 1,
        "failures": [failure],
        "provenance": _failure_provenance(root),
        "protected_artifact_integrity": integrity,
    }
    _write_json_atomic(
        operational_dir / RUN_PATH,
        {
            "schema_version": 2, "kind": "production", "run_id": run_id, "status": "failed",
            "layout": _phase3_layout(output_dir, operational_dir),
            "failures": record,
            "completion": {"story": "US-3.26", "run_id": run_id, "status": "failed", "failure": failure},
        },
    )


def _load_engine():
    return sys.modules[__name__]


def _fixed_singletons(sensor_ids: tuple[str, ...]):
    partition = tuple((sensor,) for sensor in sensor_ids)

    def clustering(_clustering_input: Any) -> dict[str, Any]:
        return {"selected_partition": partition, "partition_quality": 0.0}

    return clustering


def _resolve_output_dir(root: Path, output_dir: Path | None) -> Path:
    output = (output_dir or (root / "artifacts" / "phase3_outputs")).resolve()
    protected_directories = [
        root / name for name in ("scripts", "config", "Data", ".git")
    ]
    protected_directories.extend((
        root / "artifacts" / "phase3_operational",
        root / "artifacts" / "phase3_archive",
        *(root / "artifacts" / name for name in ("phase2_current", "phase2_outputs", "phase2_operational", "phase2_archive")),
    ))
    if output == root or output == root / "artifacts" or root.is_relative_to(output):
        raise ValueError("Phase 3 outputs require a separate directory, not the source/artifacts root.")
    if output.name == "phase3_current":
        raise ValueError("The retired phase3_current output directory is not supported.")
    if output.is_relative_to(root / "artifacts") and any(
        part.startswith(("phase3_baseline_", "phase3_extraction_"))
        for part in output.relative_to(root / "artifacts").parts
    ):
        raise ValueError("Phase 3 output directory overlaps protected checkpoint files.")
    if any(output == path or output.is_relative_to(path) for path in protected_directories):
        raise ValueError("Phase 3 output directory overlaps protected source or checkpoint files.")
    return output


def validation_provenance(root: Path) -> dict[str, str]:
    """Files covered by an externally executed regression validation."""
    relative_paths = [
        "scripts/phase3_implement.py", "scripts/shared_monitoring_engine.py",
        "scripts/build_phase1_temperature.py",
        "config/phase3a_experiment_config.json",
        "artifacts/aligned_phase1_temperature.csv",
        "artifacts/phase1_average_statistics.csv",
        "artifacts/phase3_operational/references/phase3a_phase2_baseline.json",
        "artifacts/phase3_operational/references/phase3a_validation_summary.json",
        "artifacts/phase3_operational/references/phase3a_fmic_events.csv",
        "artifacts/phase3_operational/references/phase3a_fmic_summary.json",
        "artifacts/phase3_operational/references/phase3a_smic_events.csv",
        "artifacts/phase3_operational/references/phase3a_smic_summary.json",
        "artifacts/phase3_operational/references/phase3a_protocol_equivalence_events.csv",
        "artifacts/phase3_operational/references/phase3a_us325_control_results.csv",
        "artifacts/phase3_operational/references/phase3a_us325_alpha_results.csv",
        "artifacts/phase3_operational/references/phase3a_us325_control_cluster_size_summary.csv",
        "artifacts/phase3_operational/references/phase3a_us325_cluster_size_summary.csv",
        "artifacts/phase3_operational/references/phase3a_us325_event_snapshots.csv",
        "artifacts/phase3_operational/references/phase3a_alpha_results.csv",
        "artifacts/phase3_operational/references/phase3a_comparison_summary.json",
    ]
    relative_paths.extend(f"scripts/{name}" for name in VALIDATION_TEST_MODULES)
    relative_paths.append("scripts/test_phase1_phase3a_statistics.py")
    relative_paths.extend(path.as_posix() for path in (PHASE2_SUMMARY, PHASE2_EVENTS, PHASE2_RECEIPT))
    return {name: _sha256(root / name) for name in relative_paths}


def _read_validation_record(root: Path, path: Path | None) -> dict[str, Any]:
    if path is None:
        raise ValueError("A current --validation-record from separately executed tests is required.")
    record = _read_json(path)
    _validate_validation_record(root, record)
    return {
        **record, "record_path": str(path.resolve()),
        "record_sha256": _sha256(path),
    }


def _validate_validation_record(root: Path, record: dict[str, Any]) -> None:
    count = record.get("test_count")
    if (
        record.get("schema_version") != 2
        or record.get("status") != "passed"
        or record.get("returncode") != 0
        or record.get("inputs_and_code_unchanged") is not True
        or record.get("protected_files_unchanged") is not True
        or record.get("skipped") != []
        or record.get("failures") != []
        or record.get("errors") != []
        or record.get("checks") != ["behavior", "replay"]
        or record.get("cross_phase_modules") != [
            "scripts.test_phase2_monitoring", "scripts.test_phase1_phase3a_statistics"
        ]
        or not isinstance(count, int) or isinstance(count, bool) or count <= 0
        or not isinstance(record.get("test_ids"), list)
        or len(record["test_ids"]) != count
        or record.get("modules") != [
            f"scripts.{Path(name).stem}" for name in VALIDATION_TEST_MODULES
        ] + ["scripts.test_phase1_phase3a_statistics"]
        or record.get("provenance") != validation_provenance(root)
        or not record.get("command")
    ):
        raise ValueError("Regression validation record is failed, incomplete, or stale for current inputs/code.")


def _equivalence_provenance(root: Path, contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "input_sha256": _sha256(contract["input_path"]),
        "statistics_sha256": _sha256(contract["stats_path"]),
        "config_sha256": _sha256(root / "config" / "phase3a_experiment_config.json"),
        "phase2_monitoring_sha256": _sha256(contract["phase2_path"]),
        "phase3_implementation_sha256": _sha256(contract["implementation_path"]),
        "runner_sha256": _sha256(Path(__file__)),
        "revised_phase2_baseline_sha256": _sha256(contract["revised_path"]),
        "historical_phase2_baseline_sha256": _sha256(contract["historical_path"]),
        "test_sha256": {
            name: _sha256(root / "scripts" / name) for name in VALIDATION_TEST_MODULES
        },
    }


def _equivalence_is_current(
    report: dict[str, Any], events_path: Path, expected: dict[str, Any],
) -> bool:
    return (
        events_path.is_file()
        and report.get("status") == "passed"
        and bool(report.get("checks"))
        and all(value is True for value in report["checks"].values())
        and report.get("comparison", {}).get("passed") is True
        and all(report.get("provenance", {}).get(key) == value for key, value in expected.items())
        and report.get("outputs", {}).get("events_sha256") == _sha256(events_path)
    )


def _validate_prerequisites(
    root: Path, contract: dict[str, Any], output_dir: Path,
    validation: dict[str, Any],
) -> dict[str, Any]:
    us321 = _phase3a_validate_us321(root)
    expected = _equivalence_provenance(root, contract)
    events_name = EQUIVALENCE_EVENTS_PATH
    source = None
    for candidate in (output_dir,):
        summary_path, events_path = candidate / RUN_PATH, candidate / events_name
        if summary_path.is_file():
            saved = _read_json(summary_path).get("equivalence", {})
            if _equivalence_is_current(saved, events_path, expected):
                source = candidate
                break
    reused = source is not None
    if source is None:
        saved = run_phase3a_protocol_equivalence(root, output_dir)
        if not _equivalence_is_current(saved, output_dir / events_name, expected):
            raise ValueError("Fresh C0 equivalence failed; weighted controls and alpha runs remain blocked.")
    return {
        "us321": us321, "us324": saved, "revised_phase2": contract["revised"],
        "us324_events_path": output_dir / events_name,
        "C0_reused": reused,
        "external_record_sha256": validation["record_sha256"],
    }


def _protected_hashes(root: Path) -> dict[str, str]:
    artifacts = root / "artifacts"
    protected_paths = {
        path.resolve() for path in artifacts.iterdir()
        if path.is_file()
    }
    for folder in (
        artifacts / "phase2_outputs",
        artifacts / "phase2_operational",
        _phase3_reference_directory(root),
    ):
        if folder.is_dir():
            protected_paths.update(path.resolve() for path in folder.rglob("*") if path.is_file())
    protected_paths.update(
        path.resolve() for folder in ("scripts", "config")
        if (root / folder).is_dir()
        for path in (root / folder).rglob("*")
        if path.is_file() and path.suffix in (".py", ".ipynb", ".json", ".yaml")
    )
    return {str(path.relative_to(root)): _sha256(path) for path in sorted(protected_paths)}


def _validate_partition(
    partition: tuple[tuple[str, ...], ...], sensor_ids: tuple[str, ...]
) -> None:
    members = tuple(sensor for cluster in partition for sensor in cluster)
    if (
        not partition
        or any(not cluster for cluster in partition)
        or len(members) != len(set(members))
        or set(members) != set(sensor_ids)
    ):
        raise ValueError("Every synchronization partition must cover the cohort exactly once.")


def _event_snapshot(
    event: dict[str, Any], config_id: str, alpha_label: str
) -> dict[str, Any]:
    fields = (
        "synchronization_id",
        "bucket_epoch",
        "bucket_time_utc",
        "algorithm",
        "selected_partition",
        "selected_partition_quality",
        "cluster_count",
        "coordinator_assignments",
        "raw_sensor_histories",
        "normalized_histories",
        "global_average",
        "global_violated",
        "p90_threshold",
        "root_allowance",
        "moment_observation_count",
        "weight_status",
        "first_moments",
        "second_moments",
        "conservative_terms",
        "raw_weights",
        "scaled_weights",
        "node_allowances",
        "coordinator_allowances",
    )
    result = {
        "config_id": config_id,
        "alpha_label": alpha_label,
        "snapshot_type": "synchronization",
    }
    result.update({field: event.get(field) for field in fields})
    return result


def _composition(category_totals: dict[str, int]) -> dict[str, Any]:
    if set(category_totals) != set(MESSAGE_CATEGORIES):
        raise ValueError("Transmission categories do not match the seven-category contract.")
    if any(value < 0 for value in category_totals.values()):
        raise ValueError("Transmission categories cannot be negative.")
    total = sum(category_totals.values())
    groups = {
        "within_cluster_messages": sum(category_totals[name] for name in WITHIN_CATEGORIES),
        "coordinator_to_root_messages": category_totals["coordinator_root_escalations"],
        "root_wide_messages": sum(category_totals[name] for name in ROOT_WIDE_CATEGORIES),
    }
    if sum(groups.values()) != total:
        raise ValueError("Communication pathways do not reconcile to total transmissions.")
    shares = {
        f"{name}_share_percent": (100 * value / total if total else None)
        for name, value in groups.items()
    }
    if total and not math.isclose(sum(shares.values()), 100.0, abs_tol=1e-10):
        raise ValueError("Communication pathway shares do not sum to 100 percent.")
    return {
        "total_messages": total,
        **groups,
        **shares,
        "zero_message_share_convention": "not_applicable" if total == 0 else None,
    }


def _run_monitor(
    monitor_class: Any,
    frame: pd.DataFrame,
    sensor_columns: list[str],
    threshold: float,
    weight_method: str,
    *,
    alpha: float,
    fixed_singletons: bool,
    clustering: Any = None,
    allocation_strategy: Any = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    sensor_ids = tuple(column.removesuffix("_temperature") for column in sensor_columns)
    kwargs = {}
    if fixed_singletons:
        kwargs["clustering"] = _fixed_singletons(sensor_ids)
    elif clustering is not None:
        kwargs["clustering"] = clustering
    if allocation_strategy is not None:
        kwargs["allocation_strategy"] = allocation_strategy
    monitor = monitor_class(
        sensor_ids,
        threshold,
        alpha,
        weight_method=weight_method,
        raise_on_false_safe=False,
        **kwargs,
    )
    size_counts = {
        size: {
            "cluster_size": size,
            "coordinator_check_count": 0,
            "checks_resolved_without_escalation": 0,
            "checks_escalated": 0,
            "repeated_coordinator_check_count": 0,
            "repeated_checks_resolved_without_escalation": 0,
            "node_trigger_messages": 0,
            "cluster_check_requests": 0,
            "cluster_check_responses": 0,
            "triggered_sensor_count": 0,
        }
        for size in range(1, len(sensor_ids) + 1)
    }
    previous_checked_memberships: set[tuple[str, ...]] = set()
    previous_epoch: int | None = None
    category_totals = dict.fromkeys(MESSAGE_CATEGORIES, 0)
    repeated_checks = repeated_local = 0

    for row in frame[["bucket_epoch", "bucket_time_utc", *sensor_columns]].itertuples(
        index=False, name=None
    ):
        epoch, timestamp, *readings = row
        values = dict(zip(sensor_ids, map(float, readings)))
        checks = []
        if monitor.references:
            for cluster in monitor.partition:
                coordinator = max(cluster)
                deviations = {
                    sensor: values[sensor] - monitor.references[sensor]
                    for sensor in cluster
                }
                triggers = {
                    sensor
                    for sensor in cluster
                    if abs(deviations[sensor])
                    >= monitor.allocation["node_allowances"][sensor]
                }
                if not triggers:
                    continue
                escalates = (
                    abs(math.fsum(deviations.values()) / len(cluster))
                    >= monitor.allocation["coordinator_allowances"][coordinator]
                )
                checks.append({
                    "members": tuple(sorted(cluster)),
                    "size": len(cluster),
                    "triggers": triggers,
                    "escalates": escalates,
                    "node_trigger_messages": len(triggers - {coordinator}),
                    "peer_messages": len(set(cluster) - triggers - {coordinator}),
                })

        result = monitor.step(values, str(timestamp), int(epoch))
        if (
            len(checks) != result["coordinator_checks"]
            or sum(item["escalates"] for item in checks)
            != result["coordinator_escalations"]
        ):
            raise RuntimeError("Independent check instrumentation disagrees with FMICMonitor.")
        expected_peer_categories = {
            "node_trigger_messages": sum(
                item["node_trigger_messages"] for item in checks
            ),
            "cluster_check_requests": sum(item["peer_messages"] for item in checks),
            "cluster_check_responses": sum(item["peer_messages"] for item in checks),
            "coordinator_root_escalations": sum(
                item["escalates"] for item in checks
            ),
        }
        if any(result["messages"][key] != value for key, value in expected_peer_categories.items()):
            raise RuntimeError("Per-cluster communication does not reconcile to monitor messages.")

        checked_memberships = {item["members"] for item in checks}
        is_consecutive = (
            previous_epoch is not None and int(epoch) - previous_epoch == 60
        )
        for item in checks:
            size = size_counts[item["size"]]
            repeated = (
                is_consecutive
                and item["members"] in previous_checked_memberships
            )
            size["coordinator_check_count"] += 1
            size["triggered_sensor_count"] += len(item["triggers"])
            size["checks_escalated"] += int(item["escalates"])
            size["checks_resolved_without_escalation"] += int(not item["escalates"])
            size["repeated_coordinator_check_count"] += int(repeated)
            size["repeated_checks_resolved_without_escalation"] += int(
                repeated and not item["escalates"]
            )
            size["node_trigger_messages"] += item["node_trigger_messages"]
            size["cluster_check_requests"] += item["peer_messages"]
            size["cluster_check_responses"] += item["peer_messages"]
            repeated_checks += int(repeated)
            repeated_local += int(repeated and not item["escalates"])

        for category, count in result["messages"].items():
            category_totals[category] += int(count)
        if result["synchronized"]:
            previous_checked_memberships = set()
            previous_epoch = None
        else:
            previous_checked_memberships = checked_memberships
            previous_epoch = int(epoch)

    summary = monitor.summary()
    summary["events_fingerprint"] = hashlib.sha256(
        json.dumps(
            monitor.events, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    if summary["message_category_totals"] != category_totals:
        raise RuntimeError("Per-bucket messages do not reconcile to the monitor summary.")
    if sum(size["coordinator_check_count"] for size in size_counts.values()) != summary[
        "coordinator_check_count"
    ]:
        raise RuntimeError("Cluster-size check counts do not reconcile.")
    if sum(size["checks_escalated"] for size in size_counts.values()) != summary[
        "coordinator_to_root_escalation_count"
    ]:
        raise RuntimeError("Cluster-size escalation counts do not reconcile.")
    if sum(size["repeated_coordinator_check_count"] for size in size_counts.values()) != repeated_checks:
        raise RuntimeError("Cluster-size repeated check counts do not reconcile.")
    if summary["coordinator_check_count"] != (
        summary["coordinator_to_root_escalation_count"]
        + sum(size["checks_resolved_without_escalation"] for size in size_counts.values())
    ):
        raise RuntimeError("Coordinator check outcomes do not reconcile.")
    composition = _composition(category_totals)
    summary.update(composition)
    summary.update({
        "checks_escalated": summary["coordinator_to_root_escalation_count"],
        "checks_resolved_without_escalation": sum(
            size["checks_resolved_without_escalation"] for size in size_counts.values()
        ),
        "repeated_coordinator_check_count": repeated_checks,
        "repeated_checks_resolved_without_escalation": repeated_local,
        "repeated_check_share_percent": (
            100 * repeated_checks / summary["coordinator_check_count"]
            if summary["coordinator_check_count"] else None
        ),
    })
    return summary, list(size_counts.values()), monitor.events


def _configuration_row(
    config_id: str,
    method: str,
    alpha_label: str,
    summary: dict[str, Any],
    *,
    source: str,
) -> dict[str, Any]:
    row = {
        "config_id": config_id,
        "algorithm": method,
        "allowance_method": method,
        "alpha": None if alpha_label == "not_applicable" else float(alpha_label),
        "alpha_label": alpha_label,
        "alpha_status": "not_applicable" if alpha_label == "not_applicable" else "tested",
        "result_source": source,
        "correctness_status": summary["correctness_status"],
        "false_safe_count": int(summary["false_safe_count"]),
        "false_violated_count": int(summary["false_violated_count"]),
        "global_threshold_violation_count": int(
            summary["global_threshold_violation_count"]
        ),
        "bucket_count": int(summary["bucket_count"]),
        "total_messages": int(summary["total_messages"]),
        "root_synchronization_count": int(summary["root_synchronization_count"]),
        "coordinator_check_count": int(summary["coordinator_check_count"]),
        "checks_resolved_without_escalation": int(
            summary["checks_resolved_without_escalation"]
        ),
        "checks_escalated": int(summary["checks_escalated"]),
        "node_trigger_count": int(summary["node_trigger_count"]),
        "coordinator_to_root_escalation_count": int(
            summary["coordinator_to_root_escalation_count"]
        ),
        "repeated_coordinator_check_count": int(
            summary["repeated_coordinator_check_count"]
        ),
        "repeated_checks_resolved_without_escalation": int(
            summary["repeated_checks_resolved_without_escalation"]
        ),
        "repeated_check_share_percent": summary["repeated_check_share_percent"],
        "message_counts_reconcile": summary["message_counts_reconcile"],
        "cluster_count_min": int(summary["cluster_count_min"]),
        "cluster_count_max": int(summary["cluster_count_max"]),
        "cluster_count_mean_per_sync_event": summary[
            "cluster_count_mean_per_sync_event"
        ],
        "singleton_partition_event_count": summary["singleton_partition_event_count"],
        "singleton_partition_event_share_percent": summary[
            "singleton_partition_event_share_percent"
        ],
        "events_fingerprint": summary.get("events_fingerprint"),
    }
    row.update({name: int(summary["message_category_totals"][name]) for name in MESSAGE_CATEGORIES})
    row.update({
        key: value
        for key, value in summary.items()
        if key in (
            "within_cluster_messages",
            "coordinator_to_root_messages",
            "root_wide_messages",
            "within_cluster_messages_share_percent",
            "coordinator_to_root_messages_share_percent",
            "root_wide_messages_share_percent",
            "zero_message_share_convention",
        )
    })
    return row


def _validate_alpha_grid(alpha_rows: list[dict[str, Any]]) -> None:
    frame = pd.DataFrame(alpha_rows)
    if len(frame) != 38 or frame[["algorithm", "alpha_label"]].duplicated().any():
        raise ValueError("The alpha grid must contain 38 unique method/alpha pairs.")
    if set(frame["algorithm"]) != {"FMIC", "SMIC"}:
        raise ValueError("The alpha grid must contain only FMIC and SMIC.")
    for method in ("FMIC", "SMIC"):
        method_rows = frame.loc[frame["algorithm"] == method]
        if set(method_rows["alpha_label"]) != set(ALPHA_LABELS) or len(method_rows) != 19:
            raise ValueError(f"{method} must contain each of the 19 approved alpha values.")
    if (
        not frame["correctness_status"].eq("passed").all()
        or not frame["message_counts_reconcile"].eq(True).all()
        or not frame["false_safe_count"].eq(0).all()
        or not frame["false_violated_count"].eq(0).all()
        or any(
            row["total_messages"] != sum(row[name] for name in MESSAGE_CATEGORIES)
            for row in alpha_rows
        )
    ):
        raise ValueError("Failed or unreconciled configurations cannot enter alpha ranking.")


def _validate_regression_references(
    controls: list[dict[str, Any]], alpha_rows: list[dict[str, Any]]
) -> None:
    rows = controls + alpha_rows
    by_config = {
        (row["config_id"], row["alpha_label"]): row
        for row in rows
    }
    for key, (messages, synchronizations) in REGRESSION_REFERENCES.items():
        row = by_config.get(key)
        if row is None:
            raise ValueError(f"Missing regression configuration {key}.")
        if (
            row["total_messages"] != messages
            or row["root_synchronization_count"] != synchronizations
            or row["global_threshold_violation_count"] != 1999
            or row["false_safe_count"] != 0
            or row["false_violated_count"] != 0
            or row["correctness_status"] != "passed"
            or row["message_counts_reconcile"] is not True
        ):
            raise ValueError(
                f"US-3.25 regression fingerprint changed for {key}; stop for scientific review."
            )


def _validate_saved_regression_outputs(
    artifacts: Path,
    controls: list[dict[str, Any]],
    alpha_rows: list[dict[str, Any]],
) -> None:
    checks = (
        "correctness_status",
        "false_safe_count",
        "false_violated_count",
        "global_threshold_violation_count",
        "bucket_count",
        "total_messages",
        "root_synchronization_count",
        "message_counts_reconcile",
        "events_fingerprint",
        *MESSAGE_CATEGORIES,
    )
    saved_files = (
        (f"{OUTPUT_PREFIX}control_results.csv", controls, "config_id", None),
        (
            f"{OUTPUT_PREFIX}alpha_results.csv",
            alpha_rows,
            "algorithm",
            "alpha_label",
        ),
    )
    for filename, rows, id_column, alpha_column in saved_files:
        path = artifacts / filename
        if not path.is_file():
            raise FileNotFoundError(f"Independent Phase 3 regression reference is missing: {path}")
        saved = pd.read_csv(path, dtype={"alpha_label": str})
        saved_by_key = {}
        for item in saved.to_dict(orient="records"):
            key = (item[id_column], item[alpha_column]) if alpha_column else (item[id_column],)
            saved_by_key[key] = item
        for row in rows:
            key = (row[id_column], row[alpha_column]) if alpha_column else (row[id_column],)
            old = saved_by_key.get(key)
            if old is None:
                raise ValueError(f"Existing US-3.25 output is missing configuration {key}.")
            for name in checks:
                old_value = old.get(name)
                new_value = row.get(name)
                if pd.isna(old_value) and new_value is None:
                    continue
                if name in (
                    "false_safe_count",
                    "false_violated_count",
                    "global_threshold_violation_count",
                    "bucket_count",
                    "total_messages",
                    "root_synchronization_count",
                    *MESSAGE_CATEGORIES,
                ):
                    if int(old_value) != int(new_value):
                        raise ValueError(
                            f"US-3.25 regression output changed at {key}, field {name}."
                        )
                elif name == "events_fingerprint":
                    if str(old_value) != str(new_value):
                        raise ValueError(
                            f"US-3.25 event fingerprint changed at {key}; stop for review."
                        )
                elif old_value != new_value:
                    raise ValueError(
                        f"US-3.25 regression output changed at {key}, field {name}."
                    )


def _from_existing_c0(
    root: Path,
    gates: dict[str, Any],
    sensor_ids: tuple[str, ...],
) -> dict[str, Any]:
    report = gates["us324"]
    comparison = report["comparison"]
    mapping = report["message_mapping"]
    revised = gates["revised_phase2"]
    expected_categories = {
        "node_trigger_messages": 0,
        "cluster_check_requests": 0,
        "cluster_check_responses": 0,
        "coordinator_root_escalations": revised["message_category_totals"][
            "trigger_message_count"
        ],
        "root_sync_requests": revised["message_category_totals"]["request_message_count"],
        "root_sync_responses": revised["message_category_totals"]["response_message_count"],
        "root_state_updates": revised["message_category_totals"]["broadcast_message_count"],
    }
    partition = [list((sensor,)) for sensor in sensor_ids]
    c0_events = pd.read_csv(
        gates["us324_events_path"],
        keep_default_na=False,
    )
    if not comparison["passed"] or not all(
        counts["mismatched_buckets"] == 0
        for counts in comparison["per_bucket_checks"].values()
    ):
        raise ValueError("Reused US-3.24 C0 does not pass its per-bucket equivalence gate.")
    if mapping["phase3_categories"] != expected_categories:
        raise ValueError("Reused C0 message categories do not match revised Phase 2.")
    if not c0_events.empty:
        if not {"phase2_triggering_sensor_ids", "triggering_sensor_ids"}.issubset(
            c0_events.columns
        ):
            raise ValueError("US-3.24 event snapshots cannot verify C0 trigger equivalence.")
        for row in c0_events.itertuples(index=False):
            if json.loads(row.phase2_triggering_sensor_ids) != json.loads(
                row.triggering_sensor_ids
            ):
                raise ValueError("Reused C0 trigger sets differ from revised Phase 2.")
    summary = {
        "algorithm": "C0",
        "alpha": "not_applicable",
        "bucket_count": revised["bucket_count"],
        "total_messages": revised["total_messages"],
        "message_category_totals": expected_categories,
        "root_synchronization_count": revised["resynchronization_count"],
        "coordinator_check_count": revised["message_category_totals"]["trigger_message_count"],
        "coordinator_to_root_escalation_count": revised["message_category_totals"][
            "trigger_message_count"
        ],
        "node_trigger_count": revised["message_category_totals"]["trigger_message_count"],
        "global_threshold_violation_count": revised["global_threshold_violation_count"],
        "false_safe_count": revised["false_safe_count"],
        "false_violated_count": revised["false_violated_count"],
        "correctness_status": revised["correctness_status"],
        "message_counts_reconcile": revised["message_counts_reconcile"],
        "cluster_count_min": len(sensor_ids),
        "cluster_count_max": len(sensor_ids),
        "cluster_count_mean_per_sync_event": float(len(sensor_ids)),
        "singleton_partition_event_count": revised["resynchronization_count"],
        "singleton_partition_event_share_percent": 100.0,
        "checks_resolved_without_escalation": 0,
        "checks_escalated": revised["message_category_totals"]["trigger_message_count"],
        "repeated_coordinator_check_count": 0,
        "repeated_checks_resolved_without_escalation": 0,
        "repeated_check_share_percent": 0.0,
    }
    summary.update(_composition(expected_categories))
    for field in (
        "root_synchronization_count",
        "coordinator_check_count",
        "coordinator_to_root_escalation_count",
    ):
        if summary[field] != {
            "root_synchronization_count": mapping[
                "root_synchronizations_including_initialization"
            ],
            "coordinator_check_count": mapping["genuine_trigger_notifications"],
            "coordinator_to_root_escalation_count": mapping[
                "genuine_trigger_notifications"
            ],
        }[field]:
            raise ValueError(f"Reused US-3.24 C0 {field} differs from its summary.")
    return _configuration_row(
        "C0", "equal_allowance", "not_applicable", summary, source="reused_US-3.24"
    )


def _validate_control(summary: dict[str, Any]) -> None:
    if (
        summary["bucket_count"] != 19984
        or summary["global_threshold_violation_count"] != 1999
        or summary["false_safe_count"] != 0
        or summary["false_violated_count"] != 0
        or summary["correctness_status"] != "passed"
        or summary["total_messages"]
        != sum(summary["message_category_totals"].values())
        or sum(summary["message_category_totals"][name] for name in WITHIN_CATEGORIES) != 0
        or summary["coordinator_check_count"]
        != summary["coordinator_to_root_escalation_count"]
    ):
        raise ValueError("A US-3.25 singleton control failed correctness or accounting.")


def _run_control(
    engine: Any,
    frame: pd.DataFrame,
    columns: list[str],
    threshold: float,
    method: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    monitor_class = engine.FMICMonitor
    summary, by_size, events = _run_monitor(
        monitor_class,
        frame,
        columns,
        threshold,
        method,
        alpha=0.1,
        fixed_singletons=True,
    )
    sensor_ids = tuple(column.removesuffix("_temperature") for column in columns)
    for event in events:
        selected = tuple(tuple(cluster) for cluster in json.loads(event["selected_partition"]))
        _validate_partition(selected, sensor_ids)
        if selected != tuple((sensor,) for sensor in sensor_ids):
            raise ValueError(f"{method} singleton control changed its partition.")
        root_allowance = float(event["root_allowance"])
        node = json.loads(event["node_allowances"])
        coordinator = json.loads(event["coordinator_allowances"])
        if not math.isclose(
            math.fsum(map(float, node.values())),
            len(sensor_ids) * root_allowance,
            rel_tol=0.0,
            abs_tol=1e-10,
        ):
            raise ValueError(f"{method} singleton allowances do not sum to N*delta.")
        if any(
            not math.isclose(float(node[sensor]), float(coordinator[sensor]), abs_tol=1e-12)
            for sensor in sensor_ids
        ):
            raise ValueError(f"{method} singleton coordinator/node allowances differ.")
    summary["cluster_count_mean_per_sync_event"] = float(len(sensor_ids))
    summary["singleton_partition_event_count"] = len(events)
    summary["singleton_partition_event_share_percent"] = 100.0
    _validate_control(summary)
    row = _configuration_row(
        "C1" if method == "FMIC" else "C2",
        method,
        "not_applicable",
        summary,
        source="fresh_run",
    )
    snapshots = [
        _event_snapshot(event, row["config_id"], "not_applicable")
        for event in events
    ]
    return row, by_size, snapshots


def _run_alpha(
    engine: Any,
    frame: pd.DataFrame,
    columns: list[str],
    threshold: float,
    method: str,
    alpha_label: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    summary, by_size, events = _run_monitor(
        engine.FMICMonitor,
        frame,
        columns,
        threshold,
        method,
        alpha=float(alpha_label),
        fixed_singletons=False,
    )
    sensor_ids = tuple(column.removesuffix("_temperature") for column in columns)
    cluster_counts = []
    singleton_events = 0
    for event in events:
        partition = tuple(tuple(cluster) for cluster in json.loads(event["selected_partition"]))
        _validate_partition(partition, sensor_ids)
        cluster_counts.append(len(partition))
        singleton_events += int(
            partition == tuple((sensor,) for sensor in sensor_ids)
        )
        node = json.loads(event["node_allowances"])
        coordinator = json.loads(event["coordinator_allowances"])
        root_allowance = float(event["root_allowance"])
        if not math.isclose(
            math.fsum(map(float, node.values())),
            len(sensor_ids) * root_allowance,
            rel_tol=0.0,
            abs_tol=1e-10,
        ):
            raise ValueError(f"{method} allowances do not sum to N*root allowance.")
        if any(
            not math.isclose(
                float(coordinator[max(cluster)]),
                math.fsum(float(node[sensor]) for sensor in cluster) / len(cluster),
                rel_tol=0.0,
                abs_tol=1e-12,
            )
            for cluster in partition
        ):
            raise ValueError(f"{method} coordinator allowance is not the cluster mean.")
    summary["cluster_count_mean_per_sync_event"] = math.fsum(cluster_counts) / len(
        cluster_counts
    )
    summary["singleton_partition_event_count"] = singleton_events
    summary["singleton_partition_event_share_percent"] = (
        100 * singleton_events / len(events)
    )
    if (
        summary["bucket_count"] != 19984
        or summary["global_threshold_violation_count"] != 1999
        or summary["false_safe_count"] != 0
        or summary["false_violated_count"] != 0
        or summary["correctness_status"] != "passed"
        or summary["total_messages"] != sum(summary["message_category_totals"].values())
        or not summary["message_counts_reconcile"]
    ):
        raise ValueError(f"{method} alpha={alpha_label} failed correctness/accounting.")
    row = _configuration_row(
        method,
        method,
        alpha_label,
        summary,
        source="fresh_run",
    )
    summary["events_fingerprint"] = hashlib.sha256(
        json.dumps(events, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    row["events_fingerprint"] = summary["events_fingerprint"]
    snapshots = [
        _event_snapshot(event, method, alpha_label) for event in events
    ]
    return row, by_size, snapshots


def _contrast(source: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    return {
        "message_difference": source["total_messages"] - target["total_messages"],
        "percent_relative_to_source": (
            100 * (source["total_messages"] - target["total_messages"])
            / source["total_messages"] if source["total_messages"] else None
        ),
        "root_synchronization_difference": (
            source["root_synchronization_count"]
            - target["root_synchronization_count"]
        ),
        "coordinator_check_difference": (
            source["coordinator_check_count"] - target["coordinator_check_count"]
        ),
        "locally_resolved_check_difference": (
            source["checks_resolved_without_escalation"]
            - target["checks_resolved_without_escalation"]
        ),
        "escalated_check_difference": (
            source["checks_escalated"] - target["checks_escalated"]
        ),
        "message_category_differences": {
            category: source[category] - target[category]
            for category in MESSAGE_CATEGORIES
        },
        "pathway_message_differences": {
            name: source[name] - target[name]
            for name in (
                "within_cluster_messages",
                "coordinator_to_root_messages",
                "root_wide_messages",
            )
        },
        "pathway_share_differences_percentage_points": {
            name: source[name] - target[name]
            for name in (
                "within_cluster_messages_share_percent",
                "coordinator_to_root_messages_share_percent",
                "root_wide_messages_share_percent",
            )
        },
    }


def _configuration_table(
    controls: list[dict[str, Any]],
    alphas: list[dict[str, Any]],
    revised: dict[str, Any],
    minima: dict[str, Any],
    centralized_messages: int,
) -> list[dict[str, Any]]:
    table = [{
        "config_id": "revised_phase2",
        "algorithm": "Phase 2 revised",
        "alpha_label": "not_applicable",
        "comparison_scope": "matched_primary_comparator",
        "correctness_status": revised["correctness_status"],
        "total_messages": revised["total_messages"],
        "root_synchronization_count": revised["resynchronization_count"],
        "coordinator_check_count": revised["message_category_totals"][
            "trigger_message_count"
        ],
        "checks_resolved_without_escalation": 0,
        "checks_escalated": revised["message_category_totals"][
            "trigger_message_count"
        ],
        "centralized_reduction_percent": 100 * (
            1 - revised["total_messages"] / centralized_messages
        ),
        "message_categories": revised["message_category_totals"],
    }]
    table.extend({
        **row,
        "comparison_scope": "singleton_control",
        "reduction_vs_revised_phase2_percent": (
            100 * (1 - row["total_messages"] / revised["total_messages"])
            if revised["total_messages"] else None
        ),
        "centralized_reduction_percent": 100 * (
            1 - row["total_messages"] / centralized_messages
        ),
    } for row in controls)
    for row in alphas:
        if row["alpha_label"] == "0.10":
            table.append({
                **row,
                "comparison_scope": "prespecified_alpha_0.10",
                "centralized_reduction_percent": 100 * (
                    1 - row["total_messages"] / centralized_messages
                ),
            })
    for method, result in minima.items():
        for alpha_label in result["alpha_labels"]:
            row = next(
                item for item in alphas
                if item["algorithm"] == method
                and item["alpha_label"] == alpha_label
            )
            table.append({
                **row,
                "comparison_scope": "exploratory_in_sample_tested_grid_minimum",
                "centralized_reduction_percent": 100 * (
                    1 - row["total_messages"] / centralized_messages
                ),
            })
    return table



def load_phase3_analysis_results(
    root: Path, output_dir: Path, *, include_historical: bool = False,
) -> dict[str, Any]:
    """Load compatible saved analysis inputs without experiments, tests or writes."""
    root, output_dir = root.resolve(), output_dir.resolve()
    contract = _validate_contract(root)
    historical = _read_json(contract["historical_path"])
    run = load_phase3_run(root, output_dir)
    operational_dir = _resolve_operational_dir(output_dir)
    paths = {name: output_dir / name for name in OUTPUT_FILES}
    paths["run"] = operational_dir / RUN_PATH
    paths["equivalence_events"] = operational_dir / EQUIVALENCE_EVENTS_PATH
    paths["validation"] = operational_dir / VALIDATION_PATH
    if include_historical:
        paths["historical_alphas"] = _phase3_reference_directory(root) / "phase3a_alpha_results.csv"
        paths["historical_summary"] = _phase3_reference_directory(root) / "phase3a_comparison_summary.json"
    for path in paths.values():
        if not path.is_file():
            raise FileNotFoundError(f"Required saved Phase 3 analysis input is missing: {path}")
    input_hashes = {str(path): _sha256(path) for path in paths.values()}
    for relative, digest in validation_provenance(root).items():
        input_hashes[str(root / relative)] = digest
    report, completion, failure, equivalence = (
        run[key] for key in ("comparison", "completion", "failures", "equivalence")
    )
    if (
        report.get("status") != "passed"
        or not report.get("run_id")
        or any(record.get("status") != "passed" or record.get("run_id") != report["run_id"]
               for record in (completion, failure))
        or failure.get("failure_count") != 0 or failure.get("failures") != []
    ):
        raise ValueError("Saved Phase 3 reports do not identify the same successful current run.")
    validation = report["validation"]
    _validate_validation_record(root, validation)
    expected = _equivalence_provenance(root, contract)
    provenance = report["provenance"]
    if any(provenance.get(key) != expected[key] for key in (
        "input_sha256", "statistics_sha256", "config_sha256", "phase2_monitoring_sha256",
        "phase3_implementation_sha256", "runner_sha256",
        "revised_phase2_baseline_sha256", "test_sha256",
    )):
        raise ValueError("Saved Phase 3 production provenance is stale.")
    if (
        provenance.get("equivalence_sha256") != _json_fingerprint(equivalence)
        or not _equivalence_is_current(equivalence, paths["equivalence_events"], expected)
    ):
        raise ValueError("Saved Phase 3 C0 provenance/events are incompatible.")
    experiment = report["experiment"]
    config = contract["config"]
    if (
        experiment.get("name") != config["experiment_name"]
        or experiment.get("sensor_ids") != list(SENSORS)
        or experiment.get("bucket_count") != 19984
        or experiment.get("threshold") != contract["threshold"]
        or experiment.get("boundary_convention") != config["boundary_convention"]
        or experiment.get("alpha_grid") != list(ALPHA_LABELS)
    ):
        raise ValueError("Saved Phase 3 experiment differs from the locked configuration.")

    frames = _read_result_frames(output_dir)
    required_result_fields = {
        "config_id", "algorithm", "allowance_method", "alpha", "alpha_label", "alpha_status",
        "correctness_status", "false_safe_count", "false_violated_count",
        "global_threshold_violation_count", "bucket_count", "total_messages",
        "root_synchronization_count", "coordinator_check_count", "checks_escalated",
        "node_trigger_count",
        "checks_resolved_without_escalation", "repeated_coordinator_check_count",
        "repeated_checks_resolved_without_escalation", "repeated_check_share_percent",
        "message_counts_reconcile", "cluster_count_mean_per_sync_event",
        "singleton_partition_event_share_percent", *MESSAGE_CATEGORIES,
        "within_cluster_messages", "coordinator_to_root_messages", "root_wide_messages",
        "within_cluster_messages_share_percent", "coordinator_to_root_messages_share_percent",
        "root_wide_messages_share_percent",
    }
    size_fields = {
        "config_id", "cluster_size", "coordinator_check_count", "checks_escalated",
        "checks_resolved_without_escalation", "repeated_coordinator_check_count",
        "repeated_checks_resolved_without_escalation", "node_trigger_messages",
        "cluster_check_requests", "cluster_check_responses", "triggered_sensor_count",
    }
    schemas = {
        "controls": required_result_fields,
        "alphas": required_result_fields | {
            "reduction_vs_revised_phase2_percent", "matched_singleton_message_difference",
            "matched_singleton_reduction_percent", "matched_singleton_root_synchronization_difference",
        },
        "control_cluster_sizes": size_fields,
        "cluster_sizes": size_fields | {"alpha_label"},
        "snapshots": {
            "config_id", "alpha_label", "synchronization_id", "bucket_time_utc", "bucket_epoch",
            "selected_partition", "global_average", "p90_threshold", "root_allowance",
            "moment_observation_count",
        },
    }
    for key, required in schemas.items():
        frame = frames[key]
        if frame.empty or not required.issubset(frame.columns):
            raise ValueError(f"Saved Phase 3 {key} has an empty or incompatible schema.")
        frames[key] = frame
    controls, alphas = (
        frames[key].to_dict(orient="records") for key in ("controls", "alphas")
    )
    if (
        len(controls) != 3 or {row["config_id"] for row in controls} != {"C0", "C1", "C2"}
        or any(row["alpha_label"] != "not_applicable" or not pd.isna(row["alpha"])
               for row in controls)
    ):
        raise ValueError("Saved Phase 3 singleton controls are incomplete or alpha-dependent.")
    _validate_alpha_grid(alphas)
    for row in controls + alphas:
        method = {"C0": "equal_allowance", "C1": "FMIC", "C2": "SMIC"}.get(
            row["config_id"], row["config_id"]
        )
        if (
            row["algorithm"] != method or row["allowance_method"] != method
            or row["alpha_status"] != ("not_applicable" if row["config_id"].startswith("C") else "tested")
            or (row["config_id"] in ("FMIC", "SMIC") and row["alpha"] != float(row["alpha_label"]))
        ):
            raise ValueError("Saved Phase 3 method/alpha semantics are incompatible.")
        if (
            row["bucket_count"] != 19984 or row["global_threshold_violation_count"] != 1999
            or row["correctness_status"] != "passed"
            or row["false_safe_count"] != 0 or row["false_violated_count"] != 0
            or not row["message_counts_reconcile"]
        ):
            raise ValueError("Saved Phase 3 correctness/accounting gate failed.")
        counts = {key: row[key] for key in MESSAGE_CATEGORIES}
        if any(not math.isfinite(value) or value < 0 or int(value) != value
               for value in counts.values()):
            raise ValueError("Saved Phase 3 message categories must be finite nonnegative integers.")
        composition = _composition(counts)
        for field, value in composition.items():
            if field == "zero_message_share_convention":
                continue
            if value is None or not math.isclose(float(row[field]), value, rel_tol=1e-12, abs_tol=1e-10):
                raise ValueError(f"Saved Phase 3 {field} does not reconcile.")
        for field in (
            "root_synchronization_count", "coordinator_check_count", "checks_escalated",
            "checks_resolved_without_escalation", "repeated_coordinator_check_count",
            "repeated_checks_resolved_without_escalation", "repeated_check_share_percent",
            "cluster_count_mean_per_sync_event", "singleton_partition_event_share_percent",
        ):
            if not math.isfinite(row[field]) or row[field] < 0:
                raise ValueError(f"Saved Phase 3 {field} must be finite and nonnegative.")
        if row["coordinator_check_count"] != row["checks_escalated"] + row["checks_resolved_without_escalation"]:
            raise ValueError("Saved Phase 3 coordinator check outcomes do not reconcile.")
        if row["coordinator_check_count"] <= 0 or not math.isclose(
            row["repeated_check_share_percent"],
            100 * row["repeated_coordinator_check_count"] / row["coordinator_check_count"],
            rel_tol=1e-12, abs_tol=1e-10,
        ):
            raise ValueError("Saved Phase 3 repeated-check shares do not reconcile.")
    _validate_regression_references(controls, alphas)
    if report["alpha_results_count"] != 38 or len(report["controls"]) != 3:
        raise ValueError("Saved Phase 3 summary grid is incomplete.")
    for saved in report["controls"]:
        actual = next(row for row in controls if row["config_id"] == saved["config_id"])
        if any(saved[field] != actual[field] for field in MESSAGE_CATEGORIES + (
            "total_messages", "root_synchronization_count", "coordinator_check_count",
        )):
            raise ValueError("Saved Phase 3 control table differs from its summary.")
    for method in ("FMIC", "SMIC"):
        series = [row for row in alphas if row["algorithm"] == method]
        minimum = min(row["total_messages"] for row in series)
        labels = sorted(row["alpha_label"] for row in series if row["total_messages"] == minimum)
        if (
            report["alpha_minima"][method]["minimum_total_messages"] != minimum
            or report["alpha_minima"][method]["alpha_labels"] != labels
        ):
            raise ValueError("Saved Phase 3 exploratory minima do not match the saved alpha rows.")
    expected_table = _configuration_table(
        controls, alphas, contract["revised"], report["alpha_minima"], 19984 * 6,
    )
    saved_table = report["configuration_comparison_table"]
    if len(saved_table) != len(expected_table):
        raise ValueError("Saved Phase 3 comparison table has an incompatible row count.")
    for actual, saved in zip(expected_table, saved_table):
        for field in (
            "config_id", "alpha_label", "comparison_scope", "total_messages",
            "root_synchronization_count", "coordinator_check_count",
            "checks_resolved_without_escalation", "checks_escalated",
            "centralized_reduction_percent",
        ):
            if actual[field] != saved[field]:
                raise ValueError(f"Saved Phase 3 comparison table mismatch: {field}.")
    if report["comparisons"] != _build_comparisons(controls, alphas, contract["revised"]["total_messages"], 19984 * 6):
        raise ValueError("Saved Phase 3 matched comparisons disagree with their source tables.")
    indexed = {(row["config_id"], row["alpha_label"]): row for row in controls + alphas}
    for key, control_table in (("control_cluster_sizes", True), ("cluster_sizes", False)):
        sizes = frames[key]
        key_fields = ["config_id"] if control_table else ["config_id", "alpha_label"]
        counts = sizes[list(size_fields - {"config_id", "cluster_size"})].to_numpy(dtype=float)
        if (
            sizes.duplicated(key_fields + ["cluster_size"]).any()
            or not np.isfinite(counts).all() or (counts < 0).any()
            or (counts != np.floor(counts)).any()
        ):
            raise ValueError("Saved Phase 3 cluster-size diagnostics are malformed.")
        expected_keys = set(row["config_id"] for row in controls) if control_table else set(indexed) - {
            (row["config_id"], row["alpha_label"]) for row in controls
        }
        groups = dict(tuple(sizes.groupby(key_fields[0] if control_table else key_fields)))
        if set(groups) != expected_keys:
            raise ValueError("Saved Phase 3 cluster-size configurations are incomplete.")
        for group_key, group in groups.items():
            row = indexed[(group_key, "not_applicable") if control_table else group_key]
            if len(group) != 6 or set(group["cluster_size"]) != set(range(1, 7)):
                raise ValueError("Saved Phase 3 cluster-size grid is incomplete.")
            for field in size_fields - {"config_id", "cluster_size"}:
                target = "node_trigger_count" if field == "triggered_sensor_count" else field
                if group[field].sum() != row[target]:
                    raise ValueError(f"Saved Phase 3 cluster-size {field} does not reconcile.")
    snapshot_frame = frames["snapshots"]
    expected_snapshots = {("C1", "not_applicable"), ("C2", "not_applicable")}
    for method in ("FMIC", "SMIC"):
        expected_snapshots.update((method, label) for label in {"0.10", *report["alpha_minima"][method]["alpha_labels"]})
    groups = dict(tuple(snapshot_frame.groupby(["config_id", "alpha_label"])))
    if set(groups) != expected_snapshots or snapshot_frame.duplicated(
        ["config_id", "alpha_label", "synchronization_id"]
    ).any():
        raise ValueError("Saved Phase 3 snapshot configurations are incomplete or duplicated.")
    observations, columns = _read_locked_observations(contract)
    source_averages = {
        int(row[0]): math.fsum(map(float, row[1:])) / len(columns)
        for row in observations[["bucket_epoch", *columns]].itertuples(index=False, name=None)
    }
    first_epoch = min(source_averages)
    for key, group in groups.items():
        if group["synchronization_id"].tolist() != list(range(1, indexed[key]["root_synchronization_count"] + 1)):
            raise ValueError("Saved Phase 3 snapshot synchronization history is incomplete.")
    for row in snapshot_frame.to_dict(orient="records"):
        numeric = [row[field] for field in ("global_average", "p90_threshold", "root_allowance", "moment_observation_count")]
        if not all(math.isfinite(value) for value in numeric):
            raise ValueError("Saved Phase 3 snapshots contain nonfinite values.")
        partition = tuple(tuple(cluster) for cluster in json.loads(row["selected_partition"]))
        _validate_partition(partition, SENSORS)
        epoch = row["bucket_epoch"]
        if (
            epoch not in source_averages or row["p90_threshold"] != contract["threshold"]
            or int(pd.Timestamp(row["bucket_time_utc"]).timestamp()) != epoch
            or row["global_average"] != source_averages[epoch]
            or row["root_allowance"] != abs(source_averages[epoch] - contract["threshold"])
            or row["moment_observation_count"] != (epoch - first_epoch) // 60
        ):
            raise ValueError("Saved Phase 3 snapshot differs from its source observations.")
    if include_historical:
        historical_rows = pd.read_csv(paths["historical_alphas"], dtype={"alpha_label": str}, float_precision="round_trip")
        historical_summary = _read_json(paths["historical_summary"])
        _validate_alpha_grid(historical_rows.to_dict(orient="records"))
        if (
            not {"algorithm", "alpha", "alpha_label", "total_messages",
                 "root_synchronization_count", "cluster_count_mean_per_sync_event"}.issubset(historical_rows.columns)
            or historical_summary.get("correctness_status_by_algorithm") != {"FMIC": "passed", "SMIC": "passed"}
            or historical_summary.get("message_accounting_status") != "passed"
            or not historical_rows["phase2_total_messages"].eq(historical["total_messages"]).all()
            or historical_summary.get("phase2_baseline") != historical
        ):
            raise ValueError("Saved historical Phase 3 sweep is incomplete or failed.")
        if any(historical_summary.get("provenance", {}).get(key) != value for key, value in (
            ("input_sha256", expected["input_sha256"]),
            ("config_sha256", expected["config_sha256"]),
            ("phase2_baseline_sha256", expected["historical_phase2_baseline_sha256"]),
        )):
            raise ValueError("Historical Phase 3 input/baseline identities differ from this cohort.")
        frames["historical_alphas"] = historical_rows
    if any(_sha256(Path(path)) != digest for path, digest in input_hashes.items()):
        raise RuntimeError("Saved Phase 3 inputs changed while loading analysis.")
    return {
        **frames, "report": report, "equivalence": equivalence,
        "revised": contract["revised"], "historical": historical,
        "config": config, "input_hashes": input_hashes,
    }


def _build_comparisons(
    controls: list[dict[str, Any]],
    alphas: list[dict[str, Any]],
    revised_phase2_messages: int,
    centralized_messages: int,
) -> dict[str, Any]:
    by_id = {row["config_id"]: row for row in controls}
    c0, c1, c2 = (by_id[name] for name in ("C0", "C1", "C2"))
    comparisons: dict[str, Any] = {
        "revised_phase2": {"total_messages": revised_phase2_messages},
        "centralized_reference": {"total_messages": centralized_messages},
        "weighting_effects_without_clustering": {
            "C0_minus_C1_messages": c0["total_messages"] - c1["total_messages"],
            "C0_relative_C1_percent": (
                100 * (c0["total_messages"] - c1["total_messages"])
                / c0["total_messages"] if c0["total_messages"] else None
            ),
            "C0_minus_C2_messages": c0["total_messages"] - c2["total_messages"],
            "C0_relative_C2_percent": (
                100 * (c0["total_messages"] - c2["total_messages"])
                / c0["total_messages"] if c0["total_messages"] else None
            ),
            "C1_minus_C2_messages": c1["total_messages"] - c2["total_messages"],
            "matched_pathway_and_check_contrasts": {
                "C0_minus_C1": _contrast(c0, c1),
                "C0_minus_C2": _contrast(c0, c2),
                "C1_minus_C2": _contrast(c1, c2),
            },
        },
        "clustering_effects_conditional_on_weighting": {},
        "full_algorithm_vs_revised_phase2": {},
        "full_fmic_minus_smic_at_same_alpha": {},
    }
    for method, control in (("FMIC", c1), ("SMIC", c2)):
        comparisons["clustering_effects_conditional_on_weighting"][method] = {}
        comparisons["full_algorithm_vs_revised_phase2"][method] = {}
    grouped = {}
    for row in alphas:
        alpha = row["alpha_label"]
        grouped.setdefault(alpha, {})[row["algorithm"]] = row
        control = c1 if row["algorithm"] == "FMIC" else c2
        comparisons["clustering_effects_conditional_on_weighting"][
            row["algorithm"]
        ][alpha] = {
            **_contrast(control, row),
            "control_minus_clustered_messages": control["total_messages"]
            - row["total_messages"],
            "percent_relative_to_weighted_singleton_control": (
                100 * (control["total_messages"] - row["total_messages"])
                / control["total_messages"] if control["total_messages"] else None
            ),
            "singleton_root_synchronizations": control["root_synchronization_count"],
            "clustered_root_synchronizations": row["root_synchronization_count"],
            "root_synchronizations_avoided_vs_matched_control": (
                control["root_synchronization_count"]
                - row["root_synchronization_count"]
            ),
        }
        comparisons["full_algorithm_vs_revised_phase2"][row["algorithm"]][alpha] = {
            "total_messages": row["total_messages"],
            "reduction_percent": (
                100 * (1 - row["total_messages"] / revised_phase2_messages)
                if revised_phase2_messages else None
            ),
            "centralized_reduction_percent": (
                100 * (1 - row["total_messages"] / centralized_messages)
                if centralized_messages else None
            ),
        }
    for alpha, methods in grouped.items():
        fmic, smic = methods["FMIC"], methods["SMIC"]
        comparisons["full_fmic_minus_smic_at_same_alpha"][alpha] = {
            "message_difference": fmic["total_messages"] - smic["total_messages"],
            "root_synchronization_difference": (
                fmic["root_synchronization_count"]
                - smic["root_synchronization_count"]
            ),
            "category_differences_fmic_minus_smic": {
                category: fmic[category] - smic[category]
                for category in MESSAGE_CATEGORIES
            },
            "pathway_message_differences_fmic_minus_smic": {
                name: fmic[name] - smic[name]
                for name in (
                    "within_cluster_messages",
                    "coordinator_to_root_messages",
                    "root_wide_messages",
                )
            },
            "pathway_share_differences_percentage_points_fmic_minus_smic": {
                name: fmic[name] - smic[name]
                for name in (
                    "within_cluster_messages_share_percent",
                    "coordinator_to_root_messages_share_percent",
                    "root_wide_messages_share_percent",
                )
            },
            "partition_singleton_event_share_difference_percentage_points": (
                fmic["singleton_partition_event_share_percent"]
                - smic["singleton_partition_event_share_percent"]
            ),
            "coordinator_check_difference": (
                fmic["coordinator_check_count"] - smic["coordinator_check_count"]
            ),
            "locally_resolved_check_difference": (
                fmic["checks_resolved_without_escalation"]
                - smic["checks_resolved_without_escalation"]
            ),
            "repeated_check_difference": (
                fmic["repeated_coordinator_check_count"]
                - smic["repeated_coordinator_check_count"]
            ),
            "repeated_locally_resolved_check_difference": (
                fmic["repeated_checks_resolved_without_escalation"]
                - smic["repeated_checks_resolved_without_escalation"]
            ),
            "mean_cluster_count_difference": (
                fmic["cluster_count_mean_per_sync_event"]
                - smic["cluster_count_mean_per_sync_event"]
            ),
        }
    return comparisons



def _run_fresh_process_replay(
    root: Path,
    method: str,
    alpha_label: str,
    expected: dict[str, Any],
) -> dict[str, Any]:
    command = [
        sys.executable,
        "-B",
        "-m",
        "scripts.phase3_implement",
        "--replay",
        "--root",
        str(root),
        "--method",
        method,
        "--alpha",
        alpha_label,
    ]
    completed = subprocess.run(
        command, cwd=root, text=True, capture_output=True, check=False
    )
    if completed.returncode:
        raise RuntimeError(
            "Fresh-process US-3.25 replay failed:\n"
            + completed.stdout
            + completed.stderr
        )
    replay = json.loads(completed.stdout)
    for key in (
        "correctness_status",
        "bucket_count",
        "global_threshold_violation_count",
        "total_messages",
        "root_synchronization_count",
        "message_category_totals",
        "false_safe_count",
        "false_violated_count",
        "message_counts_reconcile",
        "events_fingerprint",
    ):
        if key == "message_category_totals":
            expected_value = (
                expected[key]
                if key in expected and isinstance(expected[key], dict)
                else {category: int(expected[category]) for category in MESSAGE_CATEGORIES}
            )
        else:
            expected_value = expected[key]
        if replay[key] != expected_value:
            raise ValueError(
                f"Fresh-process {method} alpha={alpha_label} differs at {key}."
            )
    return {"command": command, "status": "passed", **replay}


def _replay(root: Path, method: str, alpha_label: str) -> dict[str, Any]:
    is_control = method in ("C1", "C2")
    if is_control:
        if alpha_label != "not_applicable":
            raise ValueError("Singleton-control replays require alpha=not_applicable.")
        algorithm = "FMIC" if method == "C1" else "SMIC"
    else:
        if method not in ("FMIC", "SMIC") or alpha_label not in ALPHA_LABELS:
            raise ValueError("Replay requires C1/C2 or FMIC/SMIC and an approved alpha.")
        algorithm = method
    contract = _validate_contract(root)
    frame, columns = _read_locked_observations(contract)
    monitor_class, _ = load_phase3_monitor()
    engine = _load_engine()
    summary, _, events = _run_monitor(
        monitor_class,
        frame,
        columns,
        contract["threshold"],
        algorithm,
        alpha=0.1 if is_control else float(alpha_label),
        fixed_singletons=is_control,
    )
    return {
        "config_id": method if is_control else algorithm,
        "algorithm": algorithm,
        "alpha_label": alpha_label,
        "correctness_status": summary["correctness_status"],
        "bucket_count": summary["bucket_count"],
        "global_threshold_violation_count": summary["global_threshold_violation_count"],
        "total_messages": summary["total_messages"],
        "root_synchronization_count": summary["root_synchronization_count"],
        "message_category_totals": summary["message_category_totals"],
        "false_safe_count": summary["false_safe_count"],
        "false_violated_count": summary["false_violated_count"],
        "message_counts_reconcile": summary["message_counts_reconcile"],
        "events_fingerprint": hashlib.sha256(json.dumps(
            events, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")).hexdigest(),
    }


def run_us325(
    root: Path, output_dir: Path | None = None,
    validation_record: Path | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    output_dir = _resolve_output_dir(root, output_dir)
    operational_dir = _resolve_operational_dir(output_dir)
    if output_dir.exists() and any(
        path.is_file() and path.name not in OUTPUT_FILES
        for path in output_dir.iterdir()
    ):
        raise ValueError("Phase 3 production requires a clean phase3_outputs directory; preserve unrelated files separately.")
    if operational_dir.exists() and any(
        path.is_file() and path.name not in OPERATIONAL_RUN_FILES
        for path in operational_dir.iterdir()
    ):
        raise ValueError("Phase 3 production requires a clean paired operational run directory.")
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).isoformat()
    state: dict[str, Any] = {
        "stage": "initial_protected_artifact_inventory",
        "configuration": None,
        "metrics": None,
    }
    protected_before: dict[str, str] = {}
    try:
        previous = _read_json(operational_dir / RUN_PATH) if (operational_dir / RUN_PATH).is_file() else {}
        _write_json_atomic(operational_dir / RUN_PATH, {
            "schema_version": 2, "kind": "production", "run_id": run_id, "status": "in_progress",
            "equivalence": previous.get("equivalence", {}),
        })
        protected_before = _protected_hashes(root)
        state["stage"] = "contract_validation"
        return _run_us325(
            root, protected_before, state, run_id, output_dir, operational_dir,
            validation_record,
        )
    except Exception as error:
        try:
            protected_after = _protected_hashes(root)
            differences = _integrity_differences(protected_before, protected_after)
            integrity = {
                "status": "unchanged" if not differences else "changed",
                "differences": differences,
                "before_sha256": protected_before,
                "after_sha256": protected_after,
            }
        except Exception as integrity_error:
            integrity = {
                "status": "check_failed",
                "differences": [],
                "before_sha256": protected_before,
                "check_error": f"{type(integrity_error).__name__}: {integrity_error}",
            }
        try:
            _persist_failure(
                root, run_id, state, error, integrity, output_dir, operational_dir,
            )
        except Exception as diagnostic_error:
            print(
                "Failed to persist US-3.26 failure diagnostics: "
                f"{type(diagnostic_error).__name__}: {diagnostic_error}",
                file=sys.stderr,
            )
        raise


def _run_us325(
    root: Path,
    protected_before: dict[str, str],
    state: dict[str, Any],
    run_id: str,
    output_dir: Path,
    operational_dir: Path,
    validation_record: Path | None,
) -> dict[str, Any]:
    artifacts = output_dir
    state["stage"] = "contract_validation"
    contract = _validate_contract(root)
    state["stage"] = "external_regression_validation"
    test_validation = _read_validation_record(root, validation_record)
    validation_record = Path(test_validation["record_path"])
    if validation_record.parent == operational_dir and validation_record.name != VALIDATION_PATH:
        raise ValueError("Validation record must not use a reserved production artifact filename.")
    validation_hash = _sha256(validation_record)
    if validation_record != operational_dir / VALIDATION_PATH:
        operational_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(validation_record, operational_dir / VALIDATION_PATH)
    if _sha256(operational_dir / VALIDATION_PATH) != validation_hash:
        raise ValueError("Copied independent validation receipt bytes differ.")
    state["stage"] = "prerequisite_validation"
    gates = _validate_prerequisites(root, contract, operational_dir, test_validation)
    state["stage"] = "input_loading"
    frame, columns = _read_locked_observations(contract)
    sensor_ids = tuple(column.removesuffix("_temperature") for column in columns)
    engine = _load_engine()

    state["stage"] = "singleton_controls"
    controls = [_from_existing_c0(root, gates, sensor_ids)]
    revised_checks = controls[0]["coordinator_check_count"]
    control_sizes = [
        {
            "config_id": "C0",
            "cluster_size": size,
            "coordinator_check_count": (
                revised_checks if size == 1 else 0
            ),
            "checks_resolved_without_escalation": 0,
            "checks_escalated": revised_checks if size == 1 else 0,
            "repeated_coordinator_check_count": 0,
            "repeated_checks_resolved_without_escalation": 0,
            "node_trigger_messages": 0,
            "cluster_check_requests": 0,
            "cluster_check_responses": 0,
            "triggered_sensor_count": (
                revised_checks if size == 1 else 0
            ),
        }
        for size in range(1, len(sensor_ids) + 1)
    ]
    control_snapshots = []
    for method in ("FMIC", "SMIC"):
        state["configuration"] = {
            "config_id": "C1" if method == "FMIC" else "C2",
            "algorithm": method,
            "alpha": "not_applicable",
        }
        state["stage"] = "singleton_control_execution"
        state["metrics"] = None
        row, by_size, snapshots = _run_control(
            engine, frame, columns, contract["threshold"], method
        )
        state["metrics"] = {
            "evaluated_bucket_count": row["bucket_count"],
            "false_safe_count": row["false_safe_count"],
            "false_violated_count": row["false_violated_count"],
            "total_messages": row["total_messages"],
            "message_category_totals": {
                name: row[name] for name in MESSAGE_CATEGORIES
            },
            "message_counts_reconcile": row["message_counts_reconcile"],
        }
        controls.append(row)
        control_sizes.extend({**item, "config_id": row["config_id"]} for item in by_size)
        control_snapshots.extend(snapshots)
    if any(row["correctness_status"] != "passed" for row in controls):
        raise ValueError("C0/C1/C2 correctness gates must pass before any alpha runs.")
    state["configuration"] = None
    state["metrics"] = None

    c0 = next(row for row in controls if row["config_id"] == "C0")
    for row in controls[1:]:
        if row["total_messages"] < 0:
            raise ValueError(f"{row['config_id']} has a negative message total.")

    # C0 remains the saved US-3.24 run; C1/C2 are validated before the alpha grid.
    alpha_rows = []
    alpha_sizes = []
    event_snapshots = list(control_snapshots)
    state["stage"] = "alpha_grid"
    for method in ("FMIC", "SMIC"):
        for alpha_label in ALPHA_LABELS:
            state["configuration"] = {
                "config_id": method,
                "algorithm": method,
                "alpha": alpha_label,
            }
            state["stage"] = "alpha_configuration_execution"
            state["metrics"] = None
            row, by_size, snapshots = _run_alpha(
                engine,
                frame,
                columns,
                contract["threshold"],
                method,
                alpha_label,
            )
            state["metrics"] = {
                "evaluated_bucket_count": row["bucket_count"],
                "false_safe_count": row["false_safe_count"],
                "false_violated_count": row["false_violated_count"],
                "total_messages": row["total_messages"],
                "message_category_totals": {
                    name: row[name] for name in MESSAGE_CATEGORIES
                },
                "message_counts_reconcile": row["message_counts_reconcile"],
            }
            matched_control = next(
                item for item in controls
                if item["config_id"] == ("C1" if method == "FMIC" else "C2")
            )
            row["reduction_vs_revised_phase2_percent"] = (
                100 * (1 - row["total_messages"] / gates["revised_phase2"]["total_messages"])
            )
            row["revised_phase2_message_difference"] = (
                gates["revised_phase2"]["total_messages"] - row["total_messages"]
            )
            row["matched_singleton_message_difference"] = (
                matched_control["total_messages"] - row["total_messages"]
            )
            row["matched_singleton_reduction_percent"] = (
                100 * (matched_control["total_messages"] - row["total_messages"])
                / matched_control["total_messages"]
                if matched_control["total_messages"] else None
            )
            row["matched_singleton_root_synchronization_difference"] = (
                matched_control["root_synchronization_count"]
                - row["root_synchronization_count"]
            )
            alpha_rows.append(row)
            alpha_sizes.extend({
                **item,
                "config_id": method,
                "alpha_label": alpha_label,
            } for item in by_size)
            if alpha_label == "0.10":
                event_snapshots.extend(snapshots)

    _validate_alpha_grid(alpha_rows)
    _validate_regression_references(controls, alpha_rows)
    state["configuration"] = None
    state["metrics"] = None
    alpha_frame = pd.DataFrame(alpha_rows)
    minima = {}
    for method in ("FMIC", "SMIC"):
        method_rows = alpha_frame.loc[alpha_frame["algorithm"] == method]
        minimum = int(method_rows["total_messages"].min())
        minima[method] = {
            "minimum_total_messages": minimum,
            "alpha_labels": sorted(
                method_rows.loc[
                    method_rows["total_messages"] == minimum, "alpha_label"
                ].tolist()
            ),
            "scope": "exploratory_in_sample_tested_grid",
        }
        # Re-run each selected minimum from fresh state for event snapshots.
        for alpha_label in minima[method]["alpha_labels"]:
            state["configuration"] = {
                "config_id": method,
                "algorithm": method,
                "alpha": alpha_label,
            }
            state["stage"] = "minimum_configuration_replay"
            state["metrics"] = None
            _, _, events = _run_alpha(
                engine,
                frame,
                columns,
                contract["threshold"],
                method,
                alpha_label,
            )
            event_snapshots.extend(events)

    _validate_saved_regression_outputs(_phase3_reference_directory(root), controls, alpha_rows)
    state["configuration"] = None
    state["metrics"] = None
    results_path = artifacts / RESULTS_PATH
    result_rows = [
        {**row, "configuration_kind": kind}
        for kind, rows in (("control", controls), ("clustered", alpha_rows))
        for row in rows
    ]
    _write_csv_records(results_path, result_rows)
    size_path = artifacts / CLUSTER_SIZES_PATH
    _write_csv_records(size_path, [
        {**row, "alpha_label": "not_applicable"} for row in control_sizes
    ] + alpha_sizes)
    snapshot_path = artifacts / SNAPSHOTS_PATH
    # Alpha 0.10 and every tied minimum are retained; controls retain all sync snapshots.
    pd.DataFrame(event_snapshots).drop_duplicates(
        subset=["config_id", "alpha_label", "synchronization_id"], keep="first"
    ).to_csv(snapshot_path, index=False, lineterminator="\n")

    revised = gates["revised_phase2"]
    comparisons = _build_comparisons(
        controls,
        alpha_rows,
        revised["total_messages"],
        len(frame) * len(sensor_ids),
    )
    presentation = {
        "schema_version": 1,
        "analysis_notebook": "scripts/phase3_analyze.ipynb",
        "plots_and_interpretation": "saved_results_only_notebook",
        "automatic_png_exports": False,
    }

    replay_specs = [
        (control["config_id"], "not_applicable", control)
        for control in controls
        if control["config_id"] in ("C1", "C2")
    ]
    replay_specs.extend(
        (method, alpha_label, next(
            row for row in alpha_rows
            if row["algorithm"] == method and row["alpha_label"] == alpha_label
        ))
        for method, alpha_label in (
            ("FMIC", "0.10"),
            ("SMIC", "0.10"),
            ("FMIC", "0.65"),
            ("SMIC", "0.65"),
        )
    )
    replay_results = {}
    for method, alpha_label, expected in replay_specs:
        state["configuration"] = {
            "config_id": method,
            "algorithm": expected["algorithm"],
            "alpha": alpha_label,
        }
        state["stage"] = "fresh_process_replay"
        state["metrics"] = None
        replay_results[f"{method}:{alpha_label}"] = _run_fresh_process_replay(
            root, method, alpha_label, expected
        )

    state["configuration"] = None
    state["metrics"] = None
    state["stage"] = "final_protected_artifact_integrity"
    protected_after = _protected_hashes(root)
    protected_differences = _integrity_differences(protected_before, protected_after)
    protected_unchanged = not protected_differences
    if not protected_unchanged:
        raise RuntimeError(
            "US-3.26 modified protected artifacts: "
            + json.dumps(protected_differences, sort_keys=True)
        )
    if _sha256(validation_record) != validation_hash or _sha256(operational_dir / VALIDATION_PATH) != validation_hash:
        raise RuntimeError("External validation record changed during production execution.")
    if test_validation["provenance"] != validation_provenance(root):
        raise RuntimeError("Validated inputs or code changed during production execution.")
    state["stage"] = "completion_report"
    report = {
        "story": "US-3.25",
        "run_id": run_id,
        "status": "passed",
        "experiment": {
            "name": contract["config"]["experiment_name"],
            "sensor_ids": list(sensor_ids),
            "bucket_count": len(frame),
            "threshold": contract["threshold"],
            "boundary_convention": contract["config"]["boundary_convention"],
            "alpha_grid": list(ALPHA_LABELS),
            "singleton_controls_alpha": "not_applicable",
        },
        "prerequisite_gates": {
            "US-3.21": "passed",
            "US-3.23": "passed",
            "US-3.24": "passed",
            "C0_reused_from_US-3.24": gates["C0_reused"],
            "C0_per_bucket_equivalence": gates["us324"]["comparison"]["passed"],
        },
        "phase2_revised_comparator": {
            "total_messages": revised["total_messages"],
            "root_synchronizations": revised["resynchronization_count"],
            "false_safe_count": revised["false_safe_count"],
            "false_violated_count": revised["false_violated_count"],
            "threshold_source": "US-3.23 revised Phase 2",
            "baseline_sha256": _sha256(contract["revised_path"]),
        },
        "controls": controls,
        "alpha_results_count": len(alpha_rows),
        "alpha_minima": minima,
        "comparisons": comparisons,
        "configuration_comparison_table": _configuration_table(
            controls,
            alpha_rows,
            revised,
            minima,
            len(frame) * len(sensor_ids),
        ),
        "presentation": presentation,
        "zero_allowance_policy": {
            "comparison": "abs(deviation) >= allowance",
            "unchanged_reading_at_zero_allowance_triggers": True,
            "behavior_changed": False,
            "diagnostic_tests": "scripts.phase3_test",
            "synthetic_boundary_diagnostic": {
                "fixture": "test_zero_allowance_unchanged_and_both_crossing_directions",
                "root_synchronizations_including_initialization": 4,
                "coordinator_checks": 6,
                "coordinator_escalations": 6,
                "actual_messages": 30,
                "true_global_violations": 3,
                "false_safe_count": 0,
                "false_violated_count": 0,
            },
        },
        "outputs": {
            "results": results_path.name,
            "cluster_size_summary": size_path.name,
            "event_snapshots": snapshot_path.name,
            "summary": SUMMARY_PATH,
            "reused_C0_event_source": _relative_artifact_path(
                artifacts, operational_dir / EQUIVALENCE_EVENTS_PATH,
            ),
            "plots": [],
            "analysis_notebook": presentation["analysis_notebook"],
        },
        "reproducibility": {
            "fresh_process_replays": replay_results,
            "protected_artifacts_unchanged": protected_unchanged,
            "protected_artifact_count": len(protected_before),
            "protected_artifact_differences": protected_differences,
            "protected_artifact_sha256": {
                name: {
                    "before": protected_before.get(name),
                    "after": protected_after.get(name),
                }
                for name in sorted(set(protected_before) | set(protected_after))
            },
        },
        "validation": {
            "artifact": _relative_artifact_path(
                artifacts, operational_dir / VALIDATION_PATH,
            ),
            "sha256": validation_hash,
        },
        "provenance": {
            "input_sha256": _sha256(contract["input_path"]),
            "statistics_sha256": _sha256(contract["stats_path"]),
            "config_sha256": _sha256(root / "config" / "phase3a_experiment_config.json"),
            "phase2_monitoring_sha256": _sha256(contract["phase2_path"]),
            "phase3_implementation_sha256": _sha256(contract["implementation_path"]),
            "revised_phase2_baseline_sha256": _sha256(contract["revised_path"]),
            "equivalence_sha256": _json_fingerprint(gates["us324"]),
            "runner_sha256": _sha256(Path(__file__).resolve()),
            "test_sha256": {
                name: _sha256(root / "scripts" / name)
                for name in VALIDATION_TEST_MODULES
            },
        },
        "interpretation_limits": [
            "Controlled within-dataset contrasts, not general causal estimates.",
            "Local check resolutions are not root synchronizations avoided.",
            "Message counts do not measure bytes, latency, or bandwidth.",
            "The tested-grid minimum is exploratory and in-sample, not a universal optimum.",
            "This is a fixed six-sensor temperature-only cohort; no availability robustness is inferred.",
        ],
    }
    completion = {
        "story": "US-3.26",
        "run_id": run_id,
        "status": "passed",
        "validation_hardening": {
            "protected_artifact_integrity": {
                "status": "unchanged",
                "count": len(protected_before),
                "hashes": report["reproducibility"]["protected_artifact_sha256"],
            },
            "regression_test_suite": {
                "status": test_validation["status"],
                "test_count": test_validation["test_count"],
                "command": test_validation["command"],
                "test_sha256": report["provenance"]["test_sha256"],
            },
            "fresh_process_replays": replay_results,
            "regression_results": {
                "controls": {
                    row["config_id"]: {
                        "total_messages": row["total_messages"],
                        "root_synchronization_count": row[
                            "root_synchronization_count"
                        ],
                    }
                    for row in controls
                },
                "prespecified_alpha_0.10": {
                    method: {
                        "total_messages": next(
                            row["total_messages"]
                            for row in alpha_rows
                            if row["algorithm"] == method
                            and row["alpha_label"] == "0.10"
                        ),
                        "root_synchronization_count": next(
                            row["root_synchronization_count"]
                            for row in alpha_rows
                            if row["algorithm"] == method
                            and row["alpha_label"] == "0.10"
                        ),
                    }
                    for method in ("FMIC", "SMIC")
                },
                "exploratory_grid_minima": minima,
                "all_38_alpha_configurations": {
                    "status": "passed",
                    "configuration_count": len(alpha_rows),
                    "false_safe_count": sum(
                        row["false_safe_count"] for row in alpha_rows
                    ),
                    "false_violated_count": sum(
                        row["false_violated_count"] for row in alpha_rows
                    ),
                    "distinct_global_threshold_violation_counts": sorted({
                        row["global_threshold_violation_count"] for row in alpha_rows
                    }),
                    "message_counts_reconcile": all(
                        row["message_counts_reconcile"] for row in alpha_rows
                    ),
                },
                "C0_per_bucket_equivalence": gates["us324"]["comparison"]["passed"],
            },
            "grid": {
                "FMIC_alpha_count": 19,
                "SMIC_alpha_count": 19,
                "unique_method_alpha_pairs": 38,
            },
            "failure_policy": {
                "status": "no_failures",
                "diagnostic_path": (
                    f"{_relative_artifact_path(artifacts, operational_dir / RUN_PATH)}#/failures"
                ),
            },
            "visualization": presentation,
            "unresolved_issues": [],
        },
        "scientific_interpretation": (
            "No new scientific conclusion was evaluated. US-3.25 regression "
            "fingerprints and historical outputs were preserved."
        ),
    }
    summary_path = artifacts / SUMMARY_PATH
    _write_json_atomic(summary_path, {
        "schema_version": 1, "kind": "summary", "run_id": run_id,
        "status": "passed", "comparison": report,
    })
    _write_json_atomic(
        operational_dir / RUN_PATH,
        {
            "schema_version": 2, "kind": "production", "run_id": run_id, "status": "passed",
            "layout": _phase3_layout(artifacts, operational_dir),
            "summary": {"artifact": SUMMARY_PATH, "sha256": _sha256(summary_path)},
            "completion": completion, "equivalence": gates["us324"],
            "failures": {
                "story": "US-3.26", "run_id": run_id, "status": "passed",
                "failure_count": 0, "failures": [],
                "provenance": {
                    "runner_sha256": _sha256(Path(__file__).resolve()),
                    "test_sha256": report["provenance"]["test_sha256"],
                },
            },
            "semantics": _bundle_semantics(),
            "artifacts": _artifact_inventory(artifacts, operational_dir),
        },
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--equivalence", action="store_true",
        help="Run the non-clustered Phase 2/C0 runtime equivalence check only.",
    )
    parser.add_argument(
        "--validation-record", type=Path,
        help="Passing independently executed regression record for these exact inputs/code.",
    )
    parser.add_argument(
        "--historical-sweep", action="store_true",
        help="Explicit legacy US-3.22 workflow; writes its original historical outputs.",
    )
    parser.add_argument("--replay", action="store_true")
    parser.add_argument("--method", choices=("C1", "C2", "FMIC", "SMIC"))
    parser.add_argument("--alpha", choices=(*ALPHA_LABELS, "not_applicable"))
    args = parser.parse_args(argv)
    if args.equivalence:
        if args.replay or args.historical_sweep or args.validation_record or args.method or args.alpha:
            parser.error("--equivalence accepts only --root and --output-dir.")
        if args.output_dir is None:
            parser.error("--equivalence requires a separate --output-dir.")
        selected_output = _resolve_output_dir(args.root.resolve(), args.output_dir)
        result = run_phase3a_protocol_equivalence(
            args.root, _resolve_operational_dir(selected_output)
        )
        print(json.dumps({
            "status": result["status"],
            "bucket_count": result["contract"]["bucket_count"],
            "phase2_messages": result["message_mapping"]["phase2_total_messages"],
            "phase3_messages": result["message_mapping"]["phase3_total_messages"],
            "first_mismatch": result["comparison"]["first_mismatch"],
        }, indent=2))
        return 0 if result["status"] == "passed" else 1
    if args.historical_sweep:
        if args.replay or args.output_dir or args.validation_record:
            parser.error("--historical-sweep cannot be combined with revised-run options.")
        print(json.dumps(run_phase3a_alpha_sweep(args.root.resolve()), indent=2))
        return 0
    if args.replay:
        if args.method is None or args.alpha is None:
            parser.error("--replay requires --method and --alpha.")
        if args.output_dir or args.validation_record:
            parser.error("--replay is read-only and cannot accept production output/validation options.")
        print(json.dumps(_replay(args.root.resolve(), args.method, args.alpha), sort_keys=True))
        return 0
    report = run_us325(args.root, args.output_dir, args.validation_record)
    print(json.dumps({
        "status": report["status"],
        "control_messages": {
            row["config_id"]: row["total_messages"] for row in report["controls"]
        },
        "alpha_results_count": report["alpha_results_count"],
        "alpha_minima": report["alpha_minima"],
        "outputs": report["outputs"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
