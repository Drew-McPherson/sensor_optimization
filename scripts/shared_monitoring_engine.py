"""Shared two-sided monitoring engine and Phase 2 artifact contract."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import statistics
from types import ModuleType
from typing import Any, Dict, List, Optional
import hashlib
import io
import json
import math
import os
from pathlib import Path
import tempfile
import unittest

import pandas as pd
import yaml


PHASE3A_APPROVED_SENSOR_IDS = ("A", "C", "D", "E", "F", "G")
PROJECT_CONFIG_PATH = Path("config/project_config.yaml")
PHASE3A_CONFIG_SECTION = "phase3a_experiment"


def load_project_config(root: Path) -> dict[str, Any]:
    """Load the single canonical project configuration."""
    config_path = root.resolve() / PROJECT_CONFIG_PATH
    with config_path.open(encoding="utf-8") as stream:
        config = yaml.safe_load(stream)
    if not isinstance(config, dict):
        raise ValueError(f"Project configuration must be a YAML mapping: {config_path}")
    return config


def load_phase3a_config(root: Path) -> dict[str, Any]:
    """Load the Phase 3A experiment section from the canonical configuration."""
    config = load_project_config(root)
    experiment = config.get(PHASE3A_CONFIG_SECTION)
    if not isinstance(experiment, dict):
        raise ValueError(
            f"Project configuration is missing its {PHASE3A_CONFIG_SECTION!r} mapping."
        )
    return experiment


def _safe_numeric(v: Any) -> Optional[float]:
    """Best-effort numeric conversion for mixed row values."""
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _percentile_linear(sorted_values: List[float], p: int) -> Optional[float]:
    """
    Compute percentile using linear interpolation between nearest ranks.
    p is expected in [0, 100].
    """
    if not sorted_values:
        return None
    if p <= 0:
        return sorted_values[0]
    if p >= 100:
        return sorted_values[-1]

    n = len(sorted_values)
    pos = (p / 100.0) * (n - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))

    if lo == hi:
        return sorted_values[lo]

    weight = pos - lo
    return sorted_values[lo] * (1.0 - weight) + sorted_values[hi] * weight


def build_phase3a_average_values(
    aligned_rows: List[Dict[str, Any]],
    experiment_config: Dict[str, Any],
) -> List[float]:
    """Validate the interval and compute its fixed six-sensor means."""
    sensor_ids = tuple(experiment_config.get("selected_sensor_ids", ()))
    if sensor_ids != PHASE3A_APPROVED_SENSOR_IDS:
        raise ValueError("Phase 3A cohort must remain exactly A, C, D, E, F, and G.")

    sensor_columns = [f"{sensor_id}_temperature" for sensor_id in sensor_ids]
    configured_columns = experiment_config.get("selected_sensor_temperature_columns")
    if configured_columns != sensor_columns:
        raise ValueError("Phase 3A sensor columns do not match the approved cohort.")
    if experiment_config.get("endpoint_convention") != "inclusive":
        raise ValueError("Phase 3A interval endpoints must both be inclusive.")

    interval_seconds = experiment_config.get("sampling_interval_seconds")
    expected_count = experiment_config.get("expected_bucket_count")
    if (
        interval_seconds != 60
        or isinstance(expected_count, bool)
        or not isinstance(expected_count, int)
    ):
        raise ValueError(
            "Phase 3A requires an integer bucket count and 60-second interval."
        )

    start = dt.datetime.fromisoformat(experiment_config["start_timestamp_utc"])
    end = dt.datetime.fromisoformat(experiment_config["end_timestamp_utc"])
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("Phase 3A interval endpoints must be timezone-aware.")
    start = start.astimezone(dt.timezone.utc)
    end = end.astimezone(dt.timezone.utc)
    elapsed_seconds = (end - start).total_seconds()
    if elapsed_seconds <= 0 or elapsed_seconds % interval_seconds:
        raise ValueError(
            "Phase 3A endpoints must define a positive one-minute interval."
        )
    elapsed_minutes = int(elapsed_seconds // interval_seconds)
    if expected_count != elapsed_minutes + 1:
        raise ValueError("Phase 3A bucket count must include both interval endpoints.")
    if experiment_config.get("expected_elapsed_minutes") != elapsed_minutes:
        raise ValueError(
            "Phase 3A expected elapsed minutes do not match its endpoints."
        )

    selected_rows = []
    for row in aligned_rows:
        timestamp = dt.datetime.fromisoformat(str(row["bucket_time_utc"]))
        if timestamp.tzinfo is None:
            raise ValueError("Phase 1 bucket timestamps must be timezone-aware.")
        timestamp = timestamp.astimezone(dt.timezone.utc)
        if start <= timestamp <= end:
            selected_rows.append((row, timestamp))

    if len(selected_rows) != expected_count:
        raise ValueError(
            f"Phase 3A requires {expected_count} aligned buckets; "
            f"found {len(selected_rows)}."
        )
    timestamps = [timestamp for _, timestamp in selected_rows]
    if len(set(timestamps)) != len(timestamps):
        raise ValueError("Phase 3A aligned input contains duplicate timestamps.")
    if any(left >= right for left, right in zip(timestamps, timestamps[1:])):
        raise ValueError("Phase 3A aligned timestamps must be strictly increasing.")
    if timestamps[0] != start or timestamps[-1] != end:
        raise ValueError("Phase 3A aligned input does not include the exact endpoints.")

    average_values = []
    for index, (row, timestamp) in enumerate(selected_rows):
        epoch = _safe_numeric(row.get("bucket_epoch"))
        if epoch is None or not math.isfinite(epoch) or int(epoch) != epoch:
            raise ValueError(
                f"Phase 3A bucket_epoch is invalid at {timestamp.isoformat()}."
            )
        if int(epoch) != int(timestamp.timestamp()):
            raise ValueError(
                "Phase 3A bucket_epoch does not match " f"{timestamp.isoformat()}."
            )
        if (
            index
            and (timestamp - timestamps[index - 1]).total_seconds() != interval_seconds
        ):
            raise ValueError(
                f"Phase 3A timestamp gap before {timestamp.isoformat()}; "
                "expected exactly 60 seconds."
            )

        readings = []
        for column in sensor_columns:
            value = _safe_numeric(row.get(column))
            if value is None or not math.isfinite(value):
                raise ValueError(
                    f"Phase 3A requires a finite {column} value at "
                    f"{timestamp.isoformat()}."
                )
            readings.append(value)
        average_values.append(sum(readings) / len(sensor_ids))

    return average_values


def build_phase3a_average_statistics_row(
    average_values: List[float],
    percentiles: List[int],
) -> Dict[str, Any]:
    """Build the Phase 3A statistics row, retaining full precision for P90."""
    if not average_values or 90 not in percentiles:
        raise ValueError("Phase 3A statistics require values and configured P90.")
    if any(not math.isfinite(value) for value in average_values):
        raise ValueError("Phase 3A average values must all be finite.")

    sorted_values = sorted(average_values)
    row: Dict[str, Any] = {
        "series_name": "phase3a_stable_cohort",
        "source_column": "phase3a_six_sensor_average",
        "confidence_filter": "all_valid_phase3a_interval_buckets",
        "filtered_snapshot_count": len(sorted_values),
        "non_null_value_count": len(sorted_values),
        "mean": round(statistics.mean(sorted_values), 6),
        "std_dev": (
            round(statistics.stdev(sorted_values), 6) if len(sorted_values) > 1 else 0.0
        ),
    }
    for percentile in percentiles:
        value = _percentile_linear(sorted_values, percentile)
        if value is None:
            row[f"p{percentile:02d}"] = ""
        elif percentile == 90:
            row[f"p{percentile:02d}"] = value
        else:
            row[f"p{percentile:02d}"] = round(value, 6)
    return row



def load_phase1_definitions(root: Path, *, audit: bool = False) -> ModuleType:
    """Load only explicitly tagged definitions, never notebook execution cells."""
    path = root.resolve() / "scripts" / "phase1_implement.ipynb"
    notebook = json.loads(path.read_text(encoding="utf-8"))
    tag = "phase1-audit" if audit else "phase1-core"
    cells = [cell for cell in notebook["cells"] if tag in cell.get("metadata", {}).get("tags", [])]
    if len(cells) != 1 or cells[0]["cell_type"] != "code":
        raise ValueError(f"Expected exactly one {tag} definition cell in {path}.")
    module = ModuleType(tag.replace("-", "_"))
    module.__file__ = str(path)
    exec(compile("".join(cells[0]["source"]), str(path), "exec"), module.__dict__)
    if audit:
        module.discover_csv_files = module.discover_audit_csv_files
    return module


def validate_preparation_policy(config: dict) -> None:
    threshold = config.get("threshold")
    if not isinstance(threshold, dict) or any(threshold.get(key) != value for key, value in {
        "source_series": "phase3a_stable_cohort", "statistic": "p90",
        "production_script": "scripts/shared_monitoring_engine.py",
        "status": "derived_from_aligned_input",
    }.items()):
        raise ValueError("Monitoring threshold policy must identify shared-engine cohort P90 preparation.")
    if "p90_value" in threshold or "statistics_artifact" in threshold:
        raise ValueError("Derived threshold values/statistics must be run evidence, not configuration.")


def historical_input_matches(root: Path, historical: str, current: str) -> bool:
    """Recognize the unchanged pre-cutover reference only for identical input bytes."""
    if historical == current:
        return True
    return (
        historical == "artifacts/aligned_phase1_temperature.csv"
        and current == "artifacts/phase1_operational/phase1_aligned_temperature.csv"
        and _hash(root / current) == "07f4eb49687e7f50e8d9179914e1f7b8a93ef83cef99b43cf9f073881051cb9b"
    )


def prepare_monitoring(root: Path) -> dict:
    """Derive cohort statistics without writing configuration or artifacts."""
    root = root.resolve()
    config_path = root / PROJECT_CONFIG_PATH
    config = load_phase3a_config(root)
    validate_preparation_policy(config)
    input_path = root / config["input_source"]
    before = {"input_sha256": _hash(input_path), "config_sha256": _hash(config_path)}
    status_path = root / "artifacts" / "phase1_operational" / "phase1_run.json"
    if not status_path.is_file():
        raise FileNotFoundError(f"Required Phase 1 publication status is missing: {status_path}")
    publication = json.loads(status_path.read_text(encoding="utf-8"))
    if (
        publication.get("schema_version") != 1
        or publication.get("limited_run") is not False
        or publication.get("status") != "passed"
        or publication.get("hashes", {}).get("phase1_aligned_sha256") != before["input_sha256"]
        or publication.get("implementation_sha256") != _hash(root / "scripts" / "phase1_implement.ipynb")
        or publication.get("config_sha256") != _hash(config_path)
    ):
        raise ValueError("Phase 1 publication is failed, incomplete, or stale for the aligned input.")
    with input_path.open(encoding="utf-8", newline="") as stream:
        values = build_phase3a_average_values(list(csv.DictReader(stream)), config)
    statistics_row = build_phase3a_average_statistics_row(values, list(range(5, 100, 5)))
    if before != {"input_sha256": _hash(input_path), "config_sha256": _hash(config_path)}:
        raise RuntimeError("Monitoring preparation inputs changed during execution.")
    return {
        "schema_version": 1, "source_series": "phase3a_stable_cohort",
        "statistic": "p90", "p90_value": statistics_row["p90"],
        "statistics": statistics_row,
        "population": {key: config[key] for key in (
            "input_source", "selected_sensor_ids", "selected_sensor_temperature_columns",
            "start_timestamp_utc", "end_timestamp_utc", "endpoint_convention",
            "expected_bucket_count", "expected_elapsed_minutes", "sampling_interval_seconds",
        )},
        "provenance": {**before, "producer_sha256": _hash(Path(__file__)),
                       "publication_sha256": _hash(status_path)},
    }


def preparation_fingerprint(preparation: dict) -> str:
    return hashlib.sha256(json.dumps(preparation, sort_keys=True, allow_nan=False, separators=(",", ":")).encode()).hexdigest()


def validate_monitoring_preparation(root: Path, saved: dict) -> None:
    if saved != prepare_monitoring(root):
        raise ValueError("Saved monitoring preparation is stale or inconsistent with current inputs/code.")


POLICY_ID = "two_sided_absolute_distance_equal_allowances"


def evaluate_root_states(
    rows: pd.DataFrame,
    observations: pd.DataFrame,
    sensor_columns: list[str],
    threshold: float,
) -> pd.DataFrame:
    """Offline oracle; never supplies state or decisions to the monitor."""
    if len(rows) != len(observations):
        raise ValueError("Oracle trace length does not match observations.")
    truth = []
    for values in observations[sensor_columns].itertuples(index=False, name=None):
        usable = [float(value) for value in values if pd.notna(value)]
        truth.append(
            "UNDEFINED" if not usable else
            "VIOLATED" if sum(usable) / len(usable) >= threshold else "SAFE"
        )
    result = pd.DataFrame(index=rows.index)
    result["oracle_global_state"] = truth
    defined = result["oracle_global_state"].ne("UNDEFINED")
    known = rows["root_known_state"]
    if not known.isin(["UNDEFINED", "SAFE", "VIOLATED"]).all():
        raise ValueError("Unknown root-known threshold state.")
    result["false_safe"] = (defined & known.eq("SAFE") & result["oracle_global_state"].eq("VIOLATED")).astype(int)
    result["false_violated"] = (defined & known.eq("VIOLATED") & result["oracle_global_state"].eq("SAFE")).astype(int)
    result["root_state_not_evaluable"] = (defined & known.eq("UNDEFINED")).astype(int)
    result.loc[~defined, ["false_safe", "false_violated", "root_state_not_evaluable"]] = float("nan")
    return result


def root_correctness_summary(rows: pd.DataFrame) -> dict:
    false_safe = int(rows["false_safe"].sum())
    false_violated = int(rows["false_violated"].sum())
    unknown = int(rows["root_state_not_evaluable"].sum())
    evaluated = int(rows["oracle_global_state"].ne("UNDEFINED").sum())
    return {
        "false_safe_count": false_safe,
        "false_violated_count": false_violated,
        "root_state_not_evaluable_count": unknown,
        "root_state_evaluation_count": evaluated,
        "correctness_status": "passed" if evaluated and not (false_safe or false_violated or unknown) else "failed",
    }


def normalize_phase2_readings(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Preserve missing observations, rejecting malformed/non-finite readings."""
    normalized = frame.copy()
    for column in columns:
        values = frame[column]
        numeric = pd.to_numeric(values, errors="coerce")
        invalid = values.notna() & (numeric.isna() | numeric.isin([float("inf"), -float("inf")]))
        if invalid.any():
            index = invalid[invalid].index[0]
            raise ValueError(
                f"Invalid Phase 2 reading in {column} at bucket "
                f"{frame.loc[index, 'bucket_epoch']}: {values.loc[index]!r}; "
                "expected a finite number or a missing observation."
            )
        normalized[column] = numeric
    return normalized


def build_phase2_trace(
    frame: pd.DataFrame,
    sensor_columns: list[str],
    threshold: float,
    *,
    round_output: bool = True,
) -> pd.DataFrame:
    if not isinstance(round_output, bool):
        raise ValueError("round_output must be a boolean.")
    if frame.empty or not sensor_columns:
        raise ValueError("Phase 2 requires rows and at least one sensor column.")
    if not math.isfinite(threshold):
        raise ValueError("Phase 2 threshold must be finite.")
    required = ["bucket_epoch", "bucket_time_utc", *sensor_columns]
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing Phase 2 input columns: {sorted(missing)}")
    if frame["bucket_epoch"].duplicated().any():
        raise ValueError("Phase 2 requires one row per bucket_epoch.")
    if not frame["bucket_epoch"].is_monotonic_increasing:
        raise ValueError("Phase 2 input must be ordered by bucket_epoch.")
    for column in sensor_columns:
        for value in frame[column].dropna():
            if not math.isfinite(float(value)):
                raise ValueError(f"Non-finite sensor reading in {column}.")

    def reported(value: float) -> float:
        return value if math.isfinite(value) else float("nan")

    def names(columns: set[str]) -> str:
        return "|".join(sorted(column.removesuffix("_temperature") for column in columns))

    reference_mean = float("nan")
    references = {column: float("nan") for column in sensor_columns}
    margins = dict(references)
    previous_online: set[str] | None = None
    initialized = False
    root_state = "UNDEFINED"
    pending_causes: set[str] = set()
    records = []
    priority = (
        "initialization",
        "sensor_membership_changed",
        "local_constraint_violation",
    )

    for values in frame[required].itertuples(index=False, name=None):
        row = dict(zip(required, values))
        online = {column for column in sensor_columns if pd.notna(row[column])}
        departed = set() if previous_online is None else previous_online - online
        returned = set() if previous_online is None else online - previous_online
        changed = bool(departed or returned)
        count = len(online)
        mean = sum(float(row[column]) for column in sorted(online)) / count if count else float("nan")
        if count and not math.isfinite(mean):
            raise ValueError(f"Non-finite Phase 2 mean at bucket {row['bucket_epoch']}.")
        entry_mean = reference_mean
        entry_delta = abs(threshold - entry_mean)
        causes = set(pending_causes)
        if not initialized:
            causes.add("initialization")
        if changed:
            causes.add("sensor_membership_changed")
        forced = bool(causes)
        triggering = set()
        sensor_fields = {}
        compared_count = 0
        local_violation_count = 0

        for column in sensor_columns:
            sensor = column.removesuffix("_temperature")
            value = float(row[column]) if column in online else float("nan")
            reference = references[column]
            margin = margins[column]
            deviation = value - reference
            comparable = column in online and math.isfinite(reference) and math.isfinite(margin)
            local_violation = comparable and abs(deviation) >= margin
            compared_count += int(comparable)
            local_violation_count += int(local_violation)
            triggered = (
                not forced and local_violation
            )
            if triggered:
                triggering.add(column)
            sensor_fields.update({
                f"observed_{sensor}_temperature": reported(value),
                f"entry_{sensor}_reference_value": reported(reference),
                f"entry_{sensor}_local_allowance": reported(margin),
                f"event_{sensor}_local_deviation": reported(deviation),
                f"event_{sensor}_allowance_remaining": reported(entry_delta - abs(deviation)),
                f"event_{sensor}_resync_requested": int(triggered),
            })

        if triggering:
            causes.add("local_constraint_violation")
        ordered_causes = [cause for cause in priority if cause in causes]
        primary_reason = ordered_causes[0] if ordered_causes else ""
        performed = bool(causes) and count > 0
        initialization = performed and "initialization" in causes
        membership_sync = performed and "sensor_membership_changed" in causes
        local_sync = performed and "local_constraint_violation" in causes
        if performed:
            reference_mean = mean
            if not math.isfinite(abs(threshold - mean)):
                raise ValueError(f"Non-finite root allowance at bucket {row['bucket_epoch']}.")
            root_state = "VIOLATED" if mean >= threshold else "SAFE"
            references = {
                column: float(row[column]) if column in online else float("nan")
                for column in sensor_columns
            }
            margins = {
                column: abs(threshold - mean) if column in online else float("nan")
                for column in sensor_columns
            }
            initialized = True
            pending_causes = set()
        else:
            pending_causes = set(causes)
        exit_delta = abs(threshold - reference_mean)
        fanout = count if performed else 0
        total = len(triggering) + 3 * fanout
        violation = int(mean >= threshold) if count else float("nan")
        pending = bool(pending_causes)

        out = {
            "bucket_epoch": int(row["bucket_epoch"]),
            "bucket_time_utc": row["bucket_time_utc"],
            "transition_summary": (
                ("resync:" if performed else "pending:") + "|".join(ordered_causes)
                if ordered_causes else "steady_state"
            ),
            "p90_threshold_used": reported(threshold),
            "observed_global_average": reported(mean),
            "entry_xbar_t0": reported(entry_mean),
            "exit_xbar_t0_if_resync": reported(reference_mean) if performed else float("nan"),
            "entry_root_allowance": reported(entry_delta),
            "exit_root_allowance_if_resync": reported(exit_delta) if performed else float("nan"),
            "threshold_policy": POLICY_ID,
            "root_known_state": root_state if count else "UNDEFINED",
            "observed_online_sensor_names": names(online),
            "observed_online_sensor_count": count,
            "event_departing_sensor_names": names(departed),
            "event_returning_sensor_names": names(returned),
            "event_membership_changed": int(changed),
            "global_state_evaluable": int(count > 0),
            "global_violation": violation,
            "event_triggering_sensor_names": names(triggering),
            "event_resync_request_count": len(triggering),
            "event_any_sensor_requested_resync": int(bool(triggering)),
            "event_resync_triggered_by_local_violation": int(local_sync),
            "event_resync_triggered_by_membership_change": int(membership_sync),
            "event_initialization_performed": int(initialization),
            "event_resync_performed": int(performed),
            "event_resync_reason": primary_reason,
            "event_resync_causes": "|".join(ordered_causes),
            "exit_resync_scheduled_next_row": int(pending),
            "exit_resync_pending": int(pending),
            "exit_resync_pending_causes": "|".join(cause for cause in priority if cause in pending_causes),
            "trigger_message_count": len(triggering),
            "request_message_count": fanout,
            "response_message_count": fanout,
            "broadcast_message_count": fanout,
            "total_message_count": total,
            # Attribution counters overlap when a single sync has several causes.
            "membership_resync_message_count": 3 * fanout if membership_sync else 0,
            "initialization_message_count": 3 * fanout if initialization else 0,
            "centralized_constraint_state": (
                "UNDEFINED" if not count else "VIOLATING" if violation == 1 else "FEASIBLE"
            ),
            "distributed_constraint_state": (
                "UNDEFINED" if not count else
                "VIOLATING" if local_violation_count else
                "FEASIBLE" if compared_count == count else "NOT_EVALUABLE"
            ),
            "legacy_event_false_negative": int(violation == 1 and not performed) if count else float("nan"),
            "legacy_event_false_alert": int(violation == 0 and performed) if count else float("nan"),
            "legacy_event_sync_delay_buckets": float("nan"),
        }
        out.update(sensor_fields)
        records.append(out)
        previous_online = online

    trace = pd.DataFrame.from_records(records)
    oracle = evaluate_root_states(trace, frame, sensor_columns, threshold)
    trace[oracle.columns] = oracle
    errors = check_trace_invariants(trace, frame, sensor_columns, threshold, rounded=False)
    if errors:
        raise ValueError("Phase 2 unrounded trace validation failed: " + "; ".join(errors))
    return trace.round(4) if round_output else trace


def check_membership_invariants(rows: pd.DataFrame) -> list[str]:
    """Validate both in-memory and CSV-loaded traces without relying on assertions."""
    errors = []
    required = [
        "bucket_epoch",
        "observed_online_sensor_count",
        "event_resync_performed",
        "global_state_evaluable",
        "event_membership_changed",
        "request_message_count",
        "response_message_count",
        "broadcast_message_count",
        "trigger_message_count",
        "total_message_count",
        "global_violation",
        "centralized_constraint_state",
        "event_resync_causes",
    ]
    missing = [column for column in required if column not in rows.columns]
    if missing:
        return [f"Trace is missing required field {column}" for column in missing]

    count = rows["observed_online_sensor_count"]
    performed = rows["event_resync_performed"].eq(1)
    evaluable = rows["global_state_evaluable"].eq(1)
    changed = rows["event_membership_changed"].eq(1)

    def report_rows(mask: pd.Series, field: str, message: str) -> None:
        for index in rows.index[mask.fillna(True)]:
            bucket = rows.at[index, "bucket_epoch"]
            errors.append(f"bucket {bucket}: {field} {message}")

    for column in ("request_message_count", "response_message_count", "broadcast_message_count"):
        report_rows(
            ~rows[column].eq(count * performed),
            column,
            "must equal the online sensor count on completed synchronizations",
        )
    categories = ["trigger_message_count", "request_message_count", "response_message_count", "broadcast_message_count"]
    report_rows(
        ~rows[categories].sum(axis=1).eq(rows["total_message_count"]),
        "total_message_count",
        "does not reconcile with the communication category counts",
    )
    report_rows(
        changed & evaluable & ~performed,
        "event_resync_performed",
        "must be 1 when observed sensor membership changes",
    )
    empty = ~evaluable
    report_rows(
        empty & rows["global_violation"].notna(),
        "global_violation",
        "must be undefined when no sensors are observed",
    )
    report_rows(
        empty & rows["total_message_count"].ne(0),
        "total_message_count",
        "must be 0 when no sensors are observed",
    )
    report_rows(
        empty & performed,
        "event_resync_performed",
        "must be 0 when no sensors are observed",
    )
    report_rows(
        empty & rows["centralized_constraint_state"].ne("UNDEFINED"),
        "centralized_constraint_state",
        "must be UNDEFINED when no sensors are observed",
    )
    forced = rows["event_resync_causes"].fillna("").str.contains(
        "initialization|sensor_membership_changed"
    )
    report_rows(
        forced & rows["trigger_message_count"].ne(0),
        "trigger_message_count",
        "must be 0 on forced synchronization rows",
    )
    return errors


def _sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run_phase3a_two_sided(root: Path, output_dir: Path | None = None) -> dict:
    """Run only the locked matched experiment, writing separate compact outputs."""
    root = root.resolve()
    artifacts = root / "artifacts"
    config_path = root / PROJECT_CONFIG_PATH
    config = load_phase3a_config(root)
    locked = {
        "experiment_name": "phase3a_stable_cohort",
        "selected_sensor_ids": list("ACDEFG"),
        "start_timestamp_utc": "2022-02-24T18:50:00+00:00",
        "end_timestamp_utc": "2022-03-10T15:53:00+00:00",
        "expected_bucket_count": 19984,
        "sampling_interval_seconds": 60,
        "endpoint_convention": "inclusive",
        "boundary_convention": {
            "safe_when": "metric < threshold",
            "violated_when": "metric >= threshold",
        },
        "input_source": "artifacts/phase1_operational/phase1_aligned_temperature.csv",
    }
    for key, value in locked.items():
        if config.get(key) != value:
            raise ValueError(f"Phase 3A configuration does not match the approved {key}.")
    preparation = prepare_monitoring(root)
    threshold_config = config["threshold"]
    input_path = root / config["input_source"]
    historical_path = (
        artifacts / "phase3_operational" / "references" / "phase3a_phase2_baseline.json"
    )
    destination = output_dir.resolve() if output_dir is not None else artifacts
    if output_dir is not None:
        if destination == root or root.is_relative_to(destination) or destination == artifacts:
            raise ValueError("An explicit Phase 2 output directory must be separate from source and historical artifacts.")
        if any(destination.is_relative_to(root / name) for name in ("scripts", "config", "instructions")):
            raise ValueError("Phase 2 output directory overlaps protected sources.")
        if any(destination.is_relative_to(artifacts / name) for name in (
            "phase2_outputs", "phase2_operational", "phase2_archive",
            "phase3_outputs", "phase3_operational", "phase3_archive",
        )):
            raise ValueError("Phase 2 isolated output directory overlaps owned artifacts.")
        if destination.is_relative_to(artifacts) and any(
            part.startswith(("phase3_baseline_", "phase3_extraction_"))
            for part in destination.relative_to(artifacts).parts
        ):
            raise ValueError("Phase 2 output directory overlaps protected checkpoint evidence.")
    output_path = destination / "phase3a_phase2_two_sided_baseline.json"
    events_path = destination / "phase3a_phase2_two_sided_events.csv"
    protected = {input_path, config_path}
    protected.add(historical_path)
    protected.update(path for path in artifacts.glob("phase2_*") if path.is_file())
    references = artifacts / "phase3_operational" / "references"
    if references.is_dir():
        protected.update(path for path in references.rglob("*") if path.is_file())
    protected.update(
        path for path in (root / "scripts").iterdir()
        if path.is_file() and path.suffix in (".py", ".ipynb")
    )
    protected_hashes = {
        str(path.relative_to(root)): _sha256(path)
        for path in sorted(protected)
    }
    threshold = preparation["p90_value"]
    historical = json.loads(historical_path.read_text(encoding="utf-8"))
    for key in (
        "experiment_name", "input_source", "selected_sensor_ids",
        "start_timestamp_utc", "end_timestamp_utc", "endpoint_convention", "boundary_convention",
    ):
        matches = (
            historical_input_matches(root, historical[key], config[key])
            if key == "input_source" else historical[key] == config[key]
        )
        if not matches:
            raise ValueError(f"Historical Phase 2 baseline does not match {key}.")
    if (
        historical["algorithm"] != "phase2"
        or historical["bucket_count"] != config["expected_bucket_count"]
        or historical["threshold_value"] != threshold
        or historical["threshold_source_series"] != threshold_config["source_series"]
        or sum(historical["message_category_totals"].values()) != historical["total_messages"]
    ):
        raise ValueError("Historical Phase 2 baseline metadata or messages do not reconcile.")

    frame = pd.read_csv(
        input_path, keep_default_na=False, na_values=[""], float_precision="round_trip"
    )
    times = pd.to_datetime(frame["bucket_time_utc"], utc=True, errors="raise")
    selected = frame.loc[
        times.between(config["start_timestamp_utc"], config["end_timestamp_utc"])
    ].copy()
    times = times.loc[selected.index]
    if (
        len(selected) != config["expected_bucket_count"]
        or not times.is_monotonic_increasing or times.duplicated().any()
        or times.iloc[0] != pd.Timestamp(config["start_timestamp_utc"])
        or times.iloc[-1] != pd.Timestamp(config["end_timestamp_utc"])
        or not times.diff().iloc[1:].eq(pd.Timedelta(seconds=60)).all()
    ):
        raise ValueError("Matched Phase 3A timestamps/count/cadence do not match the locked interval.")
    epochs = pd.to_numeric(selected["bucket_epoch"], errors="raise")
    if not all(
        epoch == timestamp.timestamp() for epoch, timestamp in zip(epochs, times)
    ):
        raise ValueError("Matched bucket epochs do not agree with the UTC timestamps.")
    sensors = [f"{sensor}_temperature" for sensor in config["selected_sensor_ids"]]
    selected = normalize_phase2_readings(selected, sensors)
    if selected[sensors].isna().any().any():
        raise ValueError("Matched Phase 3A sensor observations must be complete; no imputation.")
    selected = selected.reset_index(drop=True)
    trace = build_phase2_trace(selected, sensors, threshold)
    correctness = root_correctness_summary(trace)
    if correctness["correctness_status"] != "passed":
        raise ValueError(f"Two-sided Phase 2 correctness gate failed: {correctness}")
    if (
        correctness["root_state_evaluation_count"] != len(selected)
        or int(trace["global_violation"].sum()) != 1999
        or int(trace["event_membership_changed"].sum()) != 0
        or int(trace["event_resync_triggered_by_membership_change"].sum()) != 0
    ):
        raise ValueError("Matched Phase 3A truth/evaluation/membership gate failed.")
    categories = (
        "trigger_message_count", "request_message_count",
        "response_message_count", "broadcast_message_count",
    )
    totals = {column: int(trace[column].sum()) for column in categories}
    total = int(trace["total_message_count"].sum())
    if total != sum(totals.values()):
        raise ValueError("Two-sided Phase 2 transmission categories do not reconcile.")
    event_columns = [
        "bucket_epoch", "bucket_time_utc", "event_resync_causes",
        "event_triggering_sensor_names", "entry_xbar_t0", "exit_xbar_t0_if_resync",
        "entry_root_allowance", "exit_root_allowance_if_resync", "root_known_state",
        "oracle_global_state", *categories, "total_message_count",
    ]
    events = trace.loc[trace["event_resync_performed"].eq(1), event_columns]
    destination.mkdir(parents=True, exist_ok=True)
    events.to_csv(events_path, index=False, lineterminator="\n")
    synchronizations = int(trace["event_resync_performed"].sum())
    summary = {
        key: config[key] for key in (
            "experiment_name", "input_source", "selected_sensor_ids", "start_timestamp_utc",
            "end_timestamp_utc", "endpoint_convention", "boundary_convention",
        )
    }
    summary.update({
        "story": "US-3.23",
        "algorithm": "phase2",
        "threshold_policy": POLICY_ID,
        "threshold_source_series": threshold_config["source_series"],
        "monitoring_preparation": preparation,
        "threshold_statistic": "p90",
        "threshold_value": threshold,
        "bucket_count": len(trace),
        "global_threshold_violation_count": int(trace["global_violation"].sum()),
        **correctness,
        "message_category_totals": totals,
        "total_messages": total,
        "message_counts_reconcile": True,
        "resynchronization_count": synchronizations,
        "initialization_count": int(trace["event_initialization_performed"].sum()),
        "monitoring_triggered_synchronization_count": int(trace["event_resync_triggered_by_local_violation"].sum()),
        "local_trigger_transmission_count": totals["trigger_message_count"],
        "membership_change_event_count": int(trace["event_membership_changed"].sum()),
        "membership_triggered_synchronization_count": int(trace["event_resync_triggered_by_membership_change"].sum()),
        "centralized_sensor_transmission_reference": len(trace) * len(sensors),
        "events_artifact": events_path.name,
        "events_sha256": _sha256(events_path),
        "historical_comparison": {
            "artifact": historical_path.name,
            "policy": "historical_signed_margin_one_sided_trigger_negative_margin_scheduling",
            "total_messages": historical["total_messages"],
            "resynchronization_count": historical["resynchronization_count"],
            "message_category_totals": historical["message_category_totals"],
            "revised_minus_historical_messages": total - historical["total_messages"],
            "revised_minus_historical_synchronizations": synchronizations - historical["resynchronization_count"],
            "interpretation": "Policy-change comparison only. Synchronization schedules and absolute triggers both change; no causal split is inferred from aggregate differences.",
        },
        "provenance": {
            "input_sha256": protected_hashes[str(input_path.relative_to(root))],
            "preparation_sha256": preparation_fingerprint(preparation),
            "config_sha256": protected_hashes[str(config_path.relative_to(root))],
            "code_sha256": _sha256(Path(__file__)),
            "historical_baseline_sha256": _sha256(historical_path),
            "protected_artifact_sha256_before_and_after": protected_hashes,
        },
        "validation_commands": [
            "python -B -m scripts.phase3_test --checks behavior replay",
            "python -B -m scripts.shared_monitoring_engine publish",
        ],
        "limitations": [
            "Sampled-bucket root-known-state correctness; no between-bucket or individual-sensor guarantee.",
            "Single fixed six-sensor dataset; faithful message delivery and complete usable observations assumed.",
            "Any comparison with existing FMIC/SMIC results is preliminary: moment weighting and coordinator/cluster protocol effects remain uncontrolled.",
            "Historical Phase 2 and published US-3.22 results are not updated or relabeled.",
        ],
    })
    for relative, digest in protected_hashes.items():
        if _sha256(root / relative) != digest:
            raise RuntimeError(f"Protected input or historical output changed during execution: {relative}")
    output_path.write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return summary


def check_trace_invariants(
    rows: pd.DataFrame,
    observations: pd.DataFrame,
    sensor_columns: list[str],
    threshold: float,
    *,
    rounded: bool = True,
) -> list[str]:
    """Consistency replay of trace fields and transitions from raw observations.

    Used before rounding and after CSV export. Replay does not call the production
    builder or trust its synchronization flags to advance the reference state.
    It reconstructs substantial monitoring logic, so it is not independent proof
    of algorithm correctness. The offline root-state oracle and independently
    specified synthetic fixtures provide complementary correctness checks.
    """
    errors = check_membership_invariants(rows)
    if "distributed_alert" in rows.columns:
        errors.append("Removed field distributed_alert is still present")
    if len(rows) != len(observations):
        return errors + ["Trace length does not match input observations"]
    tolerance = 0.000050001 if rounded else 1e-12
    previous: set[str] | None = None
    baseline = float("nan")
    references = {column: float("nan") for column in sensor_columns}
    allowances = dict(references)
    initialized = False
    due: set[str] = set()
    priority = (
        "initialization",
        "sensor_membership_changed", "local_constraint_violation",
    )
    input_columns = ["bucket_epoch", *sensor_columns]
    trace_columns = list(rows.columns)

    for input_values, trace_values in zip(
        observations[input_columns].itertuples(index=False, name=None),
        rows.itertuples(index=False, name=None),
    ):
        source = dict(zip(input_columns, input_values))
        actual = dict(zip(trace_columns, trace_values))
        bucket = source["bucket_epoch"]

        def expect(field: str, expected: str | int | float) -> None:
            if field not in actual:
                errors.append(f"bucket {bucket}: missing {field}")
                return
            value = actual[field]
            if isinstance(expected, str):
                matches = ("" if pd.isna(value) else str(value)) == expected
            elif pd.isna(expected):
                matches = pd.isna(value)
            elif pd.isna(value):
                matches = False
            elif isinstance(expected, int):
                matches = value == expected
            else:
                matches = math.isclose(float(value), expected, rel_tol=0, abs_tol=tolerance)
            if not matches:
                errors.append(f"bucket {bucket}: {field} expected {expected!r}, got {value!r}")

        def ids(columns: set[str]) -> str:
            return "|".join(sorted(column.removesuffix("_temperature") for column in columns))

        online = {column for column in sensor_columns if pd.notna(source[column])}
        left = set() if previous is None else previous - online
        joined = set() if previous is None else online - previous
        n = len(online)
        mean = sum(float(source[column]) for column in sorted(online)) / n if n else float("nan")
        delta = abs(threshold - baseline)
        causes = set(due)
        if not initialized:
            causes.add("initialization")
        if left or joined:
            causes.add("sensor_membership_changed")
        forced = bool(causes)
        violations = set()
        comparable = set()
        for column in sensor_columns:
            sensor = column.removesuffix("_temperature")
            value = float(source[column]) if column in online else float("nan")
            difference = value - references[column]
            if column in online and math.isfinite(references[column]) and math.isfinite(allowances[column]):
                comparable.add(column)
                if abs(difference) >= allowances[column]:
                    violations.add(column)
            expect(f"observed_{sensor}_temperature", value)
            expect(f"entry_{sensor}_reference_value", references[column])
            expect(f"entry_{sensor}_local_allowance", allowances[column])
            expect(f"event_{sensor}_local_deviation", difference)
            expect(f"event_{sensor}_allowance_remaining", delta - abs(difference))
            expect(f"event_{sensor}_resync_requested", int(not forced and column in violations))
        triggers = set() if forced else violations
        if triggers:
            causes.add("local_constraint_violation")
        completed = bool(causes) and n > 0
        ordered = [cause for cause in priority if cause in causes]
        local_state = (
            "UNDEFINED" if not n else "VIOLATING" if violations else
            "FEASIBLE" if comparable == online else "NOT_EVALUABLE"
        )
        global_label = int(mean >= threshold) if n else float("nan")
        expect("bucket_epoch", int(bucket))
        expect("p90_threshold_used", threshold)
        expect("entry_xbar_t0", baseline)
        expect("entry_root_allowance", delta)
        expect("threshold_policy", POLICY_ID)
        expect("observed_global_average", mean)
        expect("observed_online_sensor_names", ids(online))
        expect("observed_online_sensor_count", n)
        expect("event_departing_sensor_names", ids(left))
        expect("event_returning_sensor_names", ids(joined))
        expect("event_membership_changed", int(bool(left or joined)))
        expect("global_state_evaluable", int(n > 0))
        expect("global_violation", global_label)
        expect("distributed_constraint_state", local_state)
        expect("centralized_constraint_state", "UNDEFINED" if not n else "VIOLATING" if global_label == 1 else "FEASIBLE")
        expect("event_triggering_sensor_names", ids(triggers))
        expect("event_resync_request_count", len(triggers))
        expect("event_any_sensor_requested_resync", int(bool(triggers)))
        expect("event_resync_performed", int(completed))
        expect("event_resync_reason", ordered[0] if ordered else "")
        expect("event_resync_causes", "|".join(ordered))
        expect("event_initialization_performed", int(completed and "initialization" in causes))
        expect("event_resync_triggered_by_membership_change", int(completed and "sensor_membership_changed" in causes))
        for internal, cause in (
            ("event_resync_triggered_by_local_violation", "local_constraint_violation"),
        ):
            if internal in actual:
                expect(internal, int(completed and cause in causes))
        fanout = n if completed else 0
        expect("trigger_message_count", len(triggers))
        for field in ("request_message_count", "response_message_count", "broadcast_message_count"):
            expect(field, fanout)
        expect("total_message_count", len(triggers) + 3 * fanout)
        for field, cause in (
            ("membership_resync_message_count", "sensor_membership_changed"),
            ("initialization_message_count", "initialization"),
        ):
            expect(field, 3 * fanout if cause in causes else 0)
        expect("legacy_event_false_negative", int(global_label == 1 and not completed) if n else float("nan"))
        expect("legacy_event_false_alert", int(global_label == 0 and completed) if n else float("nan"))

        if completed:
            baseline = mean
            references = {
                column: float(source[column]) if column in online else float("nan")
                for column in sensor_columns
            }
            allowances = {
                column: abs(threshold - mean) if column in online else float("nan")
                for column in sensor_columns
            }
            initialized = True
            due = set()
        else:
            due = set(causes)
        exit_delta = abs(threshold - baseline)
        expect("exit_xbar_t0_if_resync", baseline if completed else float("nan"))
        expect("exit_root_allowance_if_resync", exit_delta if completed else float("nan"))
        expected_root = "UNDEFINED" if not n else "VIOLATED" if baseline >= threshold else "SAFE"
        expect("root_known_state", expected_root)
        expect("oracle_global_state", "UNDEFINED" if not n else "VIOLATED" if global_label == 1 else "SAFE")
        expect("false_safe", int(expected_root == "SAFE" and global_label == 1) if n else float("nan"))
        expect("false_violated", int(expected_root == "VIOLATED" and global_label == 0) if n else float("nan"))
        expect("root_state_not_evaluable", 0 if n else float("nan"))
        expect("exit_resync_pending", int(bool(due)))
        expect("exit_resync_scheduled_next_row", int(bool(due)))
        expect("exit_resync_pending_causes", "|".join(cause for cause in priority if cause in due))
        previous = online
        if len(errors) >= 20:
            return errors + ["Stopped trace validation after at least 20 errors"]
    return errors


SUMMARY = Path("artifacts/phase2_outputs/phase2_summary.json")
EVENTS = Path("artifacts/phase2_operational/phase2_events.csv")
RECEIPT = Path("artifacts/phase2_operational/phase2_validation.json")
SOURCES = (
    "scripts/shared_monitoring_engine.py",
    "scripts/test_shared_monitoring.py",
    "config/project_config.yaml",
    "artifacts/phase1_operational/phase1_aligned_temperature.csv",
    "scripts/phase1_implement.ipynb",
    "artifacts/phase1_operational/phase1_run.json",
    "artifacts/phase3_operational/references/phase3a_phase2_baseline.json",
)


def _hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _json_bytes(value: dict) -> bytes:
    return (json.dumps(value, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _source_hashes(root: Path) -> dict[str, str]:
    return {name: _hash(root / name) for name in SOURCES}


def _owned_path(root: Path, relative: Path) -> Path:
    path = root / relative
    if path.resolve() != path or path.parent.resolve() != path.parent:
        raise ValueError(f"Phase 2 artifact path must not use a symbolic link: {path}")
    return path


def _protected_hashes(root: Path) -> dict[str, str]:
    artifacts = root / "artifacts"
    files = set()
    for folder in ("phase3_outputs", "phase3_operational", "phase2_archive", "phase2_current"):
        directory = artifacts / folder
        if directory.is_dir():
            files.update(path for path in directory.rglob("*") if path.is_file())
    return {str(path.relative_to(root)): _hash(path) for path in sorted(files)}


def _generate(root: Path) -> tuple[dict, bytes]:
    with tempfile.TemporaryDirectory(prefix="phase2_candidate_") as temporary:
        directory = Path(temporary) / "run"
        summary = run_phase3a_two_sided(root, directory)
        events = (directory / "phase3a_phase2_two_sided_events.csv").read_bytes()
    summary["schema_version"] = 1
    summary["events_artifact"] = "../phase2_operational/phase2_events.csv"
    summary["validation_artifact"] = "../phase2_operational/phase2_validation.json"
    summary["provenance"].pop("protected_artifact_sha256_before_and_after")
    summary["provenance"]["artifact_writer_sha256"] = _hash(root / "scripts" / "shared_monitoring_engine.py")
    summary["validation_commands"] = [
        "python -B -m scripts.shared_monitoring_engine validate",
    ]
    return summary, events


def publish(root: Path) -> dict:
    """Run the matched experiment and publish events before the linked summary."""
    root = root.resolve()
    summary, events = _generate(root)
    _write_atomic(_owned_path(root, EVENTS), events)
    _write_atomic(_owned_path(root, SUMMARY), _json_bytes(summary))
    return summary


def load_validated(root: Path) -> dict:
    """Read the current contract and require a matching independent receipt."""
    root = root.resolve()
    summary_path, events_path, receipt_path = (_owned_path(root, p) for p in (SUMMARY, EVENTS, RECEIPT))
    for path in (summary_path, events_path, receipt_path):
        if not path.is_file():
            raise FileNotFoundError(f"Required current Phase 2 artifact is missing: {path}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if (
        summary.get("schema_version") != 1
        or summary.get("events_artifact") != "../phase2_operational/phase2_events.csv"
        or summary.get("validation_artifact") != "../phase2_operational/phase2_validation.json"
        or summary.get("events_sha256") != _hash(events_path)
    ):
        raise ValueError("Phase 2 summary schema, event link, or event hash is invalid.")
    if (
        receipt.get("schema_version") != 1
        or receipt.get("status") != "passed"
        or receipt.get("checks") != ["unit_tests", "isolated_reproduction"]
        or not isinstance(receipt.get("test_count"), int)
        or isinstance(receipt["test_count"], bool)
        or receipt["test_count"] <= 0
        or receipt.get("skipped") != []
        or receipt.get("failures") != []
        or receipt.get("errors") != []
        or receipt.get("summary_sha256") != _hash(summary_path)
        or receipt.get("events_sha256") != _hash(events_path)
        or receipt.get("source_sha256") != _source_hashes(root)
    ):
        raise ValueError("Phase 2 independent validation receipt is failed, incomplete, or stale.")
    validate_monitoring_preparation(root, summary.get("monitoring_preparation", {}))
    return summary


def validate(root: Path) -> dict:
    """Execute regressions and an isolated reproduction, then issue a receipt."""
    root = root.resolve()
    receipt_path = _owned_path(root, RECEIPT)
    _write_atomic(receipt_path, _json_bytes({"schema_version": 1, "status": "in_progress"}))
    before = _source_hashes(root)
    protected_before = _protected_hashes(root)
    summary_path, events_path = _owned_path(root, SUMMARY), _owned_path(root, EVENTS)
    summary_hash, events_hash = _hash(summary_path), _hash(events_path)
    suite = unittest.defaultTestLoader.loadTestsFromNames(
        ["scripts.test_shared_monitoring"]
    )
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    print(stream.getvalue(), end="")
    if not result.wasSuccessful() or result.skipped or result.testsRun <= 0:
        raise RuntimeError("Phase 2 regression suite failed, skipped tests, or ran no tests.")
    expected, fresh_events = _generate(root)
    saved = json.loads(summary_path.read_text(encoding="utf-8"))
    if saved != expected or fresh_events != events_path.read_bytes():
        raise ValueError("Saved Phase 2 result differs from the isolated reproduction.")
    if (
        before != _source_hashes(root) or protected_before != _protected_hashes(root)
        or summary_hash != _hash(summary_path) or events_hash != _hash(events_path)
    ):
        raise RuntimeError("Phase 2 inputs, source, or saved artifacts changed during validation.")
    receipt = {
        "schema_version": 1,
        "status": "passed",
        "checks": ["unit_tests", "isolated_reproduction"],
        "test_count": result.testsRun,
        "skipped": [],
        "failures": [],
        "errors": [],
        "summary_sha256": summary_hash,
        "events_sha256": events_hash,
        "source_sha256": before,
    }
    _write_atomic(receipt_path, _json_bytes(receipt))
    load_validated(root)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=("publish", "validate"), default="publish")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path)
    arguments = parser.parse_args()
    if arguments.output_dir is not None:
        if arguments.command != "publish":
            parser.error("--output-dir is only supported for an isolated publish run")
        result = run_phase3a_two_sided(arguments.root, arguments.output_dir)
    elif arguments.command == "validate":
        result = validate(arguments.root)
    else:
        result = publish(arguments.root)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
