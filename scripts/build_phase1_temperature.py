#!/usr/bin/env python3
"""
Phase 1 transformation runner for the Distributed Monitoring POC.

What this script does:
1. Reads raw CSV telemetry files from Data/files_csv.
2. Applies a transparent Phase 1 transformation (Temperature only).
3. Produces reviewable artifacts with explicit audit/QC information.
4. Enforces configurable quality gates from config/transformation_defaults.yaml.

Why this script exists:
- The project requires data preparation to be traceable and reviewable.
- Every major transformation step records counts and decisions.
- Output artifacts are deterministic for reproducibility.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import re
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# -----------------------------------------------------------------------------
# Utility helpers
# -----------------------------------------------------------------------------


def _now_utc_iso() -> str:
    """Return current UTC time in ISO format for logs and decisions metadata."""
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def _sha256_file(path: Path) -> str:
    """Hash a file for reproducibility checks."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _parse_filename_timestamp(name: str) -> Optional[dt.datetime]:
    """
    Parse timestamps embedded in filenames like:
      2022_02_11_13-45-52_data.csv
      2022_06_13_00-00-19.csv

    Returns timezone-aware UTC datetime when parseable, else None.
    """
    m = re.search(r"(\d{4}_\d{2}_\d{2}_\d{2}-\d{2}-\d{2})", name)
    if not m:
        return None
    try:
        ts = dt.datetime.strptime(m.group(1), "%Y_%m_%d_%H-%M-%S")
        return ts.replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return None


def _bucket_epoch(ts_epoch: int, bucket_size_seconds: int) -> int:
    """Map a unix-epoch second to a fixed bucket boundary."""
    return ts_epoch - (ts_epoch % bucket_size_seconds)


def _safe_float(v: str) -> Optional[float]:
    """Best-effort conversion to float. Returns None on invalid values."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _safe_int_epoch(v: str) -> Optional[int]:
    """
    Parse epoch time that may be integer-like or float-like text.
    Example: "1644587153" or "1644587153.0".
    """
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


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


# -----------------------------------------------------------------------------
# Config loading
# -----------------------------------------------------------------------------


def load_yaml_config(path: Path) -> Dict[str, Any]:
    """
    Load the transformation config.

    PyYAML is used when available, but the script also includes a small
    standard-library fallback so it can run on a plain Windows Python install
    without any extra packages.
    """
    try:
        import yaml  # type: ignore
    except ImportError:
        yaml = None

    if yaml is not None:
        with path.open("r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
    else:
        cfg = _load_yaml_subset(path)

    if not isinstance(cfg, dict):
        raise ValueError(f"Config at {path} is not a mapping/object.")
    return cfg


def _load_yaml_subset(path: Path) -> Dict[str, Any]:
    """
    Parse the small YAML subset used by the project config.

    Supported forms:
    - top-level and nested mappings
    - list items introduced by '-'
    - strings, integers, floats, booleans, and quoted strings

    This keeps the script dependency-free while still reading the existing
    config file format.
    """

    def parse_scalar(text: str) -> Any:
        value = text.strip()
        if value == "":
            return ""
        if value.startswith('"') and value.endswith('"') and len(value) >= 2:
            return value[1:-1]
        if value.startswith("'") and value.endswith("'") and len(value) >= 2:
            return value[1:-1]
        lowered = value.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        if lowered in {"null", "none", "~"}:
            return None
        if re.fullmatch(r"[-+]?\d+", value):
            try:
                return int(value)
            except ValueError:
                pass
        if re.fullmatch(r"[-+]?\d*\.\d+", value):
            try:
                return float(value)
            except ValueError:
                pass
        return value

    def leading_spaces(line: str) -> int:
        return len(line) - len(line.lstrip(" "))

    lines: List[Tuple[int, str]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "#" in raw_line:
            hash_index = raw_line.find("#")
            if hash_index > 0 and raw_line[:hash_index].rstrip().endswith(("'", '"')):
                pass
            else:
                raw_line = raw_line[:hash_index]
        lines.append((leading_spaces(raw_line), raw_line.rstrip()))

    if not lines:
        return {}

    def parse_block(index: int, indent: int) -> Tuple[Any, int]:
        result: Any = None
        while index < len(lines):
            current_indent, raw_line = lines[index]
            stripped = raw_line.strip()
            if current_indent < indent:
                break
            if stripped.startswith("-") and current_indent == indent:
                if result is None:
                    result = []
                elif not isinstance(result, list):
                    raise ValueError(f"Mixed mapping/list structure near: {raw_line}")
                item_text = stripped[1:].strip()
                index += 1
                if item_text == "":
                    if index < len(lines) and lines[index][0] > current_indent:
                        item_value, index = parse_block(index, lines[index][0])
                    else:
                        item_value = {}
                else:
                    item_value = parse_scalar(item_text)
                    if index < len(lines) and lines[index][0] > current_indent:
                        nested_value, index = parse_block(index, lines[index][0])
                        if isinstance(item_value, dict):
                            if isinstance(nested_value, dict):
                                item_value.update(nested_value)
                            else:
                                raise ValueError(f"List item mapping expected near: {raw_line}")
                        else:
                            if isinstance(nested_value, dict):
                                item_value = {"value": item_value, **nested_value}
                            else:
                                item_value = nested_value
                result.append(item_value)
                continue

            if ":" not in stripped:
                raise ValueError(f"Unsupported config line: {raw_line}")

            if result is None:
                result = {}
            elif not isinstance(result, dict):
                raise ValueError(f"Mixed mapping/list structure near: {raw_line}")

            key, value_text = stripped.split(":", 1)
            key = key.strip()
            value_text = value_text.strip()
            index += 1

            if value_text == "":
                if index < len(lines) and lines[index][0] > current_indent:
                    nested_value, index = parse_block(index, lines[index][0])
                    result[key] = nested_value
                else:
                    result[key] = {}
            else:
                result[key] = parse_scalar(value_text)
                if index < len(lines) and lines[index][0] > current_indent:
                    nested_value, index = parse_block(index, lines[index][0])
                    if isinstance(result[key], dict):
                        if isinstance(nested_value, dict):
                            result[key].update(nested_value)
                        else:
                            raise ValueError(f"Mapping expected near: {raw_line}")
                    else:
                        result[key] = nested_value

        if result is None:
            result = {}
        return result, index

    parsed, final_index = parse_block(0, lines[0][0])
    if final_index != len(lines):
        raise ValueError(f"Could not fully parse config file {path}")
    if not isinstance(parsed, dict):
        raise ValueError(f"Config at {path} is not a mapping/object.")
    return parsed


# -----------------------------------------------------------------------------
# Core transformation
# -----------------------------------------------------------------------------


def discover_csv_files(data_dir: Path, limit_files: Optional[int]) -> List[Path]:
    """
    Discover CSV files under data directory and sort by timestamp-in-filename
    when present, fallback to lexical name order.
    """
    files = [
        p
        for p in data_dir.glob("*.csv")
        if p.is_file() and p.name.lower().endswith(".csv")
    ]

    files.sort(key=lambda p: ((_parse_filename_timestamp(p.name) or dt.datetime.min.replace(tzinfo=dt.timezone.utc)), p.name))

    if limit_files is not None:
        files = files[:limit_files]
    return files


def build_phase1_temperature(
    files: List[Path],
    bucket_size_seconds: int,
    max_forward_fill_buckets: int,
    stale_threshold_seconds: int,
    min_devices_per_snapshot: int,
    drop_snapshot_if_stale_over_threshold: bool,
    completeness_weight: float,
    freshness_weight: float,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """
    Execute full Phase 1 transformation and return:
    1) raw_index_rows: per-file coverage and parsing audit
    2) aligned_rows: final aligned snapshot rows for output CSV
    3) qc: summarized quality metrics for gates and review

    Design notes:
    - We keep full trace counters for auditability.
    - Deduplication is performed for temperature stream keys used in Phase 1.
    - Alignment uses bucketed timeline and bounded forward-fill.
        - Per-bucket average columns are emitted from final per-device row values:
            one includes imputed values, one excludes imputed values.
    """

    # Track file-level audit and global counters.
    raw_index_rows: List[Dict[str, Any]] = []
    counters = {
        "files_processed": 0,
        "rows_total": 0,
        "rows_schema_valid": 0,
        "rows_schema_invalid": 0,
        "rows_temperature": 0,
        "rows_temperature_valid": 0,
        "rows_temperature_invalid": 0,
        "rows_temperature_duplicate": 0,
    }

    # Temperature data keyed by (bucket_epoch, device_id): list of raw values.
    # We store list to support median aggregation exactly as specified.
    values_by_bucket_device: Dict[Tuple[int, str], List[float]] = defaultdict(list)

    # Keep seen temperature keys for deterministic de-duplication in Phase 1.
    # Key is (time_epoch, device, sensor).
    seen_temp_keys: set[Tuple[int, str, str]] = set()

    device_ids_seen: set[str] = set()

    for file_path in files:
        counters["files_processed"] += 1

        row_count = 0
        schema_valid = 0
        schema_invalid = 0
        ts_min: Optional[int] = None
        ts_max: Optional[int] = None

        with file_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)

            # Basic schema check at reader level.
            expected = {"Time", "DeviceId", "Sensor", "Value"}
            fieldnames = set(reader.fieldnames or [])
            schema_ok = expected.issubset(fieldnames)

            if not schema_ok:
                # Entire file is counted but invalid for transformation.
                for _ in reader:
                    row_count += 1
                    schema_invalid += 1
                    counters["rows_total"] += 1
                    counters["rows_schema_invalid"] += 1

                raw_index_rows.append(
                    {
                        "file_name": file_path.name,
                        "file_path": str(file_path),
                        "file_timestamp_utc": (_parse_filename_timestamp(file_path.name) or ""),
                        "row_count": row_count,
                        "schema_valid_rows": 0,
                        "schema_invalid_rows": schema_invalid,
                        "min_time_epoch": "",
                        "max_time_epoch": "",
                        "status": "invalid_schema",
                    }
                )
                continue

            for row in reader:
                row_count += 1
                counters["rows_total"] += 1

                t = row.get("Time", "")
                d = row.get("DeviceId", "")
                s = row.get("Sensor", "")
                v = row.get("Value", "")

                ts_epoch = _safe_int_epoch(t)
                val = _safe_float(v)

                # Row-level schema validity includes parseability of critical fields.
                if ts_epoch is None or not d or not s or val is None:
                    schema_invalid += 1
                    counters["rows_schema_invalid"] += 1
                    continue

                schema_valid += 1
                counters["rows_schema_valid"] += 1

                ts_min = ts_epoch if ts_min is None else min(ts_min, ts_epoch)
                ts_max = ts_epoch if ts_max is None else max(ts_max, ts_epoch)

                if s != "Temperature":
                    continue

                counters["rows_temperature"] += 1

                temp_key = (ts_epoch, d, s)
                if temp_key in seen_temp_keys:
                    counters["rows_temperature_duplicate"] += 1
                    continue
                seen_temp_keys.add(temp_key)

                counters["rows_temperature_valid"] += 1
                device_ids_seen.add(d)

                bucket = _bucket_epoch(ts_epoch, bucket_size_seconds)
                values_by_bucket_device[(bucket, d)].append(val)

        raw_index_rows.append(
            {
                "file_name": file_path.name,
                "file_path": str(file_path),
                "file_timestamp_utc": (_parse_filename_timestamp(file_path.name) or ""),
                "row_count": row_count,
                "schema_valid_rows": schema_valid,
                "schema_invalid_rows": schema_invalid,
                "min_time_epoch": "" if ts_min is None else ts_min,
                "max_time_epoch": "" if ts_max is None else ts_max,
                "status": "ok",
            }
        )

    # Build aggregated per (bucket, device) temperature value.
    agg_value_by_bucket_device: Dict[Tuple[int, str], float] = {}
    for key, vals in values_by_bucket_device.items():
        # Use median for robustness to spikes, as specified in plan/config.
        agg_value_by_bucket_device[key] = float(statistics.median(vals))

    buckets_sorted = sorted({b for (b, _) in agg_value_by_bucket_device.keys()})
    devices_sorted = sorted(device_ids_seen)

    # Align series by bucket across devices with bounded carry-forward.
    # For each device, track last observed value and age in buckets.
    aligned_rows: List[Dict[str, Any]] = []
    imputed_cell_count = 0
    total_cell_count = 0
    stale_cell_count = 0

    # last_real[(device)] = (bucket_epoch, value)
    last_real: Dict[str, Tuple[int, float]] = {}

    for bucket in buckets_sorted:
        row: Dict[str, Any] = {
            "bucket_epoch": bucket,
            "bucket_time_utc": dt.datetime.fromtimestamp(bucket, tz=dt.timezone.utc).isoformat(),
        }

        available_devices = 0
        non_imputed_fields = 0
        imputed_fields = 0
        max_age_seconds = 0
        avg_candidates_all_devices: List[float] = []
        avg_candidates_non_imputed: List[float] = []

        for device in devices_sorted:
            total_cell_count += 1

            direct_key = (bucket, device)
            value: Optional[float] = None
            imputed = False
            age_seconds = 0

            if direct_key in agg_value_by_bucket_device:
                # Fresh measurement for this bucket/device.
                value = agg_value_by_bucket_device[direct_key]
                last_real[device] = (bucket, value)
            else:
                # Attempt bounded carry-forward from latest real observation.
                if device in last_real:
                    last_bucket, last_value = last_real[device]
                    gap_buckets = (bucket - last_bucket) // bucket_size_seconds
                    if gap_buckets <= max_forward_fill_buckets:
                        value = last_value
                        imputed = True
                        age_seconds = int(gap_buckets * bucket_size_seconds)

            # Optional stale-drop behavior.
            if (
                value is not None
                and drop_snapshot_if_stale_over_threshold
                and age_seconds > stale_threshold_seconds
            ):
                stale_cell_count += 1
                value = None
                imputed = False
                age_seconds = 0

            # Record per-device fields to keep reviewability explicit.
            row[f"{device}_temperature"] = "" if value is None else round(value, 6)
            row[f"{device}_is_imputed"] = int(imputed) if value is not None else ""
            row[f"{device}_age_seconds"] = age_seconds if value is not None else ""

            if value is not None:
                avg_candidates_all_devices.append(value)
                available_devices += 1
                max_age_seconds = max(max_age_seconds, age_seconds)
                if imputed:
                    imputed_fields += 1
                    imputed_cell_count += 1
                else:
                    avg_candidates_non_imputed.append(value)
                    non_imputed_fields += 1

        # Calculate snapshot confidence from plan formula.
        total_fields = len(devices_sorted) if devices_sorted else 1
        completeness_component = non_imputed_fields / total_fields
        freshness_component = 1.0 - min(1.0, max_age_seconds / max(1, stale_threshold_seconds))
        confidence = (
            completeness_weight * completeness_component
            + freshness_weight * freshness_component
        )

        row["available_devices"] = available_devices
        row["imputed_fields"] = imputed_fields
        row["max_age_seconds"] = max_age_seconds
        row["snapshot_confidence"] = round(confidence, 6)
        row["meets_min_device_coverage"] = int(available_devices >= min_devices_per_snapshot)
        row["average_temperature_all_devices"] = (
            ""
            if not avg_candidates_all_devices
            else round(sum(avg_candidates_all_devices) / len(avg_candidates_all_devices), 6)
        )
        row["average_temperature_all_devices_count"] = len(avg_candidates_all_devices)
        row["average_temperature_non_imputed_devices"] = (
            ""
            if not avg_candidates_non_imputed
            else round(sum(avg_candidates_non_imputed) / len(avg_candidates_non_imputed), 6)
        )

        aligned_rows.append(row)

    # Summarize QC metrics for quality-gate checks and reporting.
    schema_validity_percent = (
        100.0 * counters["rows_schema_valid"] / max(1, counters["rows_total"])
    )
    duplicate_key_rate_percent = (
        100.0 * counters["rows_temperature_duplicate"] / max(1, counters["rows_temperature"])
    )
    imputation_rate_percent = (
        100.0 * imputed_cell_count / max(1, total_cell_count)
    )
    stale_snapshot_rate_percent = (
        100.0 * stale_cell_count / max(1, total_cell_count)
    )
    coverage_ok_count = sum(1 for r in aligned_rows if r["meets_min_device_coverage"] == 1)
    device_coverage_percent = (
        100.0 * coverage_ok_count / max(1, len(aligned_rows))
    )

    qc = {
        **counters,
        "devices_seen_count": len(devices_sorted),
        "snapshot_count": len(aligned_rows),
        "schema_validity_percent": round(schema_validity_percent, 6),
        "duplicate_key_rate_percent": round(duplicate_key_rate_percent, 6),
        "imputation_rate_percent": round(imputation_rate_percent, 6),
        "stale_snapshot_rate_percent": round(stale_snapshot_rate_percent, 6),
        "device_coverage_percent": round(device_coverage_percent, 6),
    }

    return raw_index_rows, aligned_rows, qc


# -----------------------------------------------------------------------------
# Artifact writers and quality gate checks
# -----------------------------------------------------------------------------


def write_csv_rows(path: Path, rows: List[Dict[str, Any]]) -> None:
    """Write list-of-dict rows to CSV with deterministic field ordering."""
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        # Write an empty file with no header if no rows exist.
        path.write_text("", encoding="utf-8")
        return

    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_qc_report(path: Path, qc: Dict[str, Any]) -> None:
    """Write single-row QC report as CSV for easy downstream review."""
    write_csv_rows(path, [qc])


def build_phase1_average_statistics_rows(
    aligned_rows: List[Dict[str, Any]],
    confidence_threshold: float,
    percentiles: List[int],
) -> List[Dict[str, Any]]:
    """
    Build summary statistics for phase1 average columns using only rows with
    snapshot_confidence greater than the configured threshold.
    """
    filtered_rows = [
        r
        for r in aligned_rows
        if (_safe_numeric(r.get("snapshot_confidence")) is not None)
        and (_safe_numeric(r.get("snapshot_confidence")) > confidence_threshold)
    ]

    percentile_fields = [f"p{p:02d}" for p in percentiles]

    series_specs = [
        ("average_temperature_all_devices", "all_devices_including_imputed"),
        ("average_temperature_non_imputed_devices", "non_imputed_devices_only"),
    ]

    rows: List[Dict[str, Any]] = []
    confidence_label = f"snapshot_confidence_gt_{confidence_threshold:.2f}"

    for column_name, series_name in series_specs:
        values: List[float] = []
        for r in filtered_rows:
            val = _safe_numeric(r.get(column_name))
            if val is not None:
                values.append(val)

        out: Dict[str, Any] = {
            "series_name": series_name,
            "source_column": column_name,
            "confidence_filter": confidence_label,
            "filtered_snapshot_count": len(filtered_rows),
            "non_null_value_count": len(values),
            "mean": "",
            "std_dev": "",
        }
        for f in percentile_fields:
            out[f] = ""

        if values:
            values_sorted = sorted(values)
            out["mean"] = round(statistics.mean(values_sorted), 6)
            out["std_dev"] = round(statistics.stdev(values_sorted), 6) if len(values_sorted) > 1 else 0.0
            for p in percentiles:
                pv = _percentile_linear(values_sorted, p)
                out[f"p{p:02d}"] = "" if pv is None else round(pv, 6)

        rows.append(out)

    # Add a diagnostic delta series to quantify imputation impact.
    delta_values: List[float] = []
    for r in filtered_rows:
        all_val = _safe_numeric(r.get("average_temperature_all_devices"))
        non_imp_val = _safe_numeric(r.get("average_temperature_non_imputed_devices"))
        if all_val is not None and non_imp_val is not None:
            delta_values.append(all_val - non_imp_val)

    delta_row: Dict[str, Any] = {
        "series_name": "imputation_delta_all_minus_non_imputed",
        "source_column": "average_temperature_all_devices - average_temperature_non_imputed_devices",
        "confidence_filter": confidence_label,
        "filtered_snapshot_count": len(filtered_rows),
        "non_null_value_count": len(delta_values),
        "mean": "",
        "std_dev": "",
    }
    for f in percentile_fields:
        delta_row[f] = ""

    if delta_values:
        delta_sorted = sorted(delta_values)
        delta_row["mean"] = round(statistics.mean(delta_sorted), 6)
        delta_row["std_dev"] = round(statistics.stdev(delta_sorted), 6) if len(delta_sorted) > 1 else 0.0
        for p in percentiles:
            pv = _percentile_linear(delta_sorted, p)
            delta_row[f"p{p:02d}"] = "" if pv is None else round(pv, 6)

    rows.append(delta_row)
    return rows


def evaluate_quality_gates(qc: Dict[str, Any], gates: Dict[str, Any]) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Compare computed QC metrics against gate thresholds from config.
    Returns overall pass/fail and a list of per-gate results.
    """
    checks = [
        {
            "gate": "schema_validity_min_percent",
            "metric": "schema_validity_percent",
            "operator": ">=",
            "actual": float(qc["schema_validity_percent"]),
            "threshold": float(gates["schema_validity_min_percent"]),
        },
        {
            "gate": "duplicate_key_rate_max_percent",
            "metric": "duplicate_key_rate_percent",
            "operator": "<=",
            "actual": float(qc["duplicate_key_rate_percent"]),
            "threshold": float(gates["duplicate_key_rate_max_percent"]),
        },
        {
            "gate": "imputation_rate_max_percent",
            "metric": "imputation_rate_percent",
            "operator": "<=",
            "actual": float(qc["imputation_rate_percent"]),
            "threshold": float(gates["imputation_rate_max_percent"]),
        },
        {
            "gate": "stale_snapshot_rate_max_percent",
            "metric": "stale_snapshot_rate_percent",
            "operator": "<=",
            "actual": float(qc["stale_snapshot_rate_percent"]),
            "threshold": float(gates["stale_snapshot_rate_max_percent"]),
        },
        {
            "gate": "device_coverage_min_percent",
            "metric": "device_coverage_percent",
            "operator": ">=",
            "actual": float(qc["device_coverage_percent"]),
            "threshold": float(gates["device_coverage_min_percent"]),
        },
    ]

    all_pass = True
    for check in checks:
        if check["operator"] == ">=":
            passed = check["actual"] >= check["threshold"]
        else:
            passed = check["actual"] <= check["threshold"]
        check["passed"] = passed
        all_pass = all_pass and passed

    return all_pass, checks


def append_decisions_log(
    path: Path,
    run_meta: Dict[str, Any],
    gate_checks: List[Dict[str, Any]],
    qc: Dict[str, Any],
) -> None:
    """
    Append a structured markdown section to decisions log.
    This keeps a historical trail of settings and outcomes.
    """
    lines = []
    lines.append("\n## Automated Run")
    lines.append(f"- Date: {run_meta['date_utc']}")
    lines.append(f"- Script: {run_meta['script_name']}")
    lines.append(f"- Config file: {run_meta['config_path']}")
    lines.append(f"- Data directory: {run_meta['data_dir']}")
    lines.append(f"- Files processed: {qc['files_processed']}")
    lines.append("")
    lines.append("### Locked Defaults Used")
    lines.append(f"- bucket_size_seconds: {run_meta['bucket_size_seconds']}")
    lines.append(f"- max_forward_fill_buckets: {run_meta['max_forward_fill_buckets']}")
    lines.append(f"- min_devices_per_snapshot: {run_meta['min_devices_per_snapshot']}")
    lines.append(f"- stale_threshold_seconds: {run_meta['stale_threshold_seconds']}")
    lines.append("")
    lines.append("### Gate Checks")
    for g in gate_checks:
        lines.append(
            f"- {g['gate']}: actual={g['actual']}, threshold {g['operator']} {g['threshold']}, passed={g['passed']}"
        )
    lines.append("")
    lines.append("### QC Snapshot")
    lines.append(f"- schema_validity_percent: {qc['schema_validity_percent']}")
    lines.append(f"- duplicate_key_rate_percent: {qc['duplicate_key_rate_percent']}")
    lines.append(f"- imputation_rate_percent: {qc['imputation_rate_percent']}")
    lines.append(f"- stale_snapshot_rate_percent: {qc['stale_snapshot_rate_percent']}")
    lines.append(f"- device_coverage_percent: {qc['device_coverage_percent']}")

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build Phase 1 (temperature-only) aligned dataset with full audit trail."
    )
    parser.add_argument(
        "--config",
        default="config/transformation_defaults.yaml",
        help="Path to YAML config file.",
    )
    parser.add_argument(
        "--data-dir",
        default="Data/files_csv",
        help="Directory containing source CSV files.",
    )
    parser.add_argument(
        "--limit-files",
        type=int,
        default=None,
        help="Optional limit for quick smoke tests.",
    )
    parser.add_argument(
        "--enforce-gates",
        action="store_true",
        help="Return non-zero exit code when quality gates fail.",
    )

    args = parser.parse_args(argv)

    script_path = Path(__file__).resolve()
    repo_root = script_path.parent.parent

    config_path = (repo_root / args.config).resolve()
    data_dir = (repo_root / args.data_dir).resolve()

    cfg = load_yaml_config(config_path)

    global_cfg = cfg.get("global", {})
    phase1_cfg = cfg.get("phase1", {})
    gates_cfg = cfg.get("quality_gates", {})
    conf_cfg = cfg.get("confidence_scoring", {})
    stats_cfg = cfg.get("summary_statistics", {})
    artifacts_cfg = cfg.get("artifacts", {})

    files = discover_csv_files(data_dir, args.limit_files)
    if not files:
        print(f"No CSV files found in {data_dir}")
        return 1

    raw_index_rows, aligned_rows, qc = build_phase1_temperature(
        files=files,
        bucket_size_seconds=int(global_cfg["bucket_size_seconds"]),
        max_forward_fill_buckets=int(global_cfg["max_forward_fill_buckets"]),
        stale_threshold_seconds=int(phase1_cfg["stale_threshold_seconds"]),
        min_devices_per_snapshot=int(global_cfg["min_devices_per_snapshot"]),
        drop_snapshot_if_stale_over_threshold=bool(global_cfg["drop_snapshot_if_stale_over_threshold"]),
        completeness_weight=float(conf_cfg["completeness_weight"]),
        freshness_weight=float(conf_cfg["freshness_weight"]),
    )

    raw_index_path = (repo_root / artifacts_cfg["raw_index"]).resolve()
    phase1_out_path = (repo_root / artifacts_cfg["phase1_aligned"]).resolve()
    qc_path = (repo_root / artifacts_cfg["qc_report"]).resolve()
    decisions_path = (repo_root / artifacts_cfg["decisions_log"]).resolve()
    phase1_stats_path = (repo_root / artifacts_cfg["phase1_average_statistics"]).resolve()

    percentiles = [int(p) for p in stats_cfg.get("percentiles", list(range(5, 100, 5)))]
    percentiles = sorted({p for p in percentiles if 0 < p < 100})
    confidence_threshold = float(stats_cfg.get("confidence_threshold", 0.75))

    write_csv_rows(raw_index_path, raw_index_rows)
    write_csv_rows(phase1_out_path, aligned_rows)
    write_qc_report(qc_path, qc)
    phase1_stats_rows = build_phase1_average_statistics_rows(
        aligned_rows=aligned_rows,
        confidence_threshold=confidence_threshold,
        percentiles=percentiles,
    )
    write_csv_rows(phase1_stats_path, phase1_stats_rows)

    pass_gates, gate_checks = evaluate_quality_gates(qc, gates_cfg)

    run_meta = {
        "date_utc": _now_utc_iso(),
        "script_name": script_path.name,
        "config_path": str(config_path),
        "data_dir": str(data_dir),
        "bucket_size_seconds": global_cfg["bucket_size_seconds"],
        "max_forward_fill_buckets": global_cfg["max_forward_fill_buckets"],
        "min_devices_per_snapshot": global_cfg["min_devices_per_snapshot"],
        "stale_threshold_seconds": phase1_cfg["stale_threshold_seconds"],
    }
    append_decisions_log(decisions_path, run_meta, gate_checks, qc)

    # Emit machine-readable run summary for easy CI / agent parsing.
    summary = {
        "artifacts": {
            "raw_index": str(raw_index_path),
            "phase1_aligned": str(phase1_out_path),
            "phase1_average_statistics": str(phase1_stats_path),
            "qc_report": str(qc_path),
            "decisions_log": str(decisions_path),
        },
        "hashes": {
            "raw_index_sha256": _sha256_file(raw_index_path),
            "phase1_aligned_sha256": _sha256_file(phase1_out_path),
            "phase1_average_statistics_sha256": _sha256_file(phase1_stats_path),
            "qc_report_sha256": _sha256_file(qc_path),
        },
        "quality_gates_passed": pass_gates,
        "qc": qc,
        "gate_checks": gate_checks,
    }
    print(json.dumps(summary, indent=2))

    if args.enforce_gates and not pass_gates:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
