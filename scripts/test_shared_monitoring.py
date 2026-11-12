"""Independently test shared preparation, Phase 2 behavior, and Phase 3 dependencies.

The shared monitoring engine owns stable-cohort preparation, threshold
provenance, Phase 2 state decisions, and artifact freshness contracts consumed
by Phase 3. These tests use small synthetic rows and isolated temporary
repositories; they do not represent the full Phase 3 production dataset.
Membership/departure cases exercise general Phase 2 behavior, whereas Phase 3A
uses a complete fixed six-sensor cohort.

The suite checks full-precision six-sensor means/P90, complete observations,
entry-state transitions, two-sided root-state correctness, independent oracle
isolation, publication receipts, and compact exports. Corrupted fixtures are
deliberate negative controls. Temporary files, mocks, and subprocesses are
confined to test-owned locations; the oracle diagnoses state but never controls
monitoring messages.
"""

import csv
import datetime as dt
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from unittest.mock import patch

import numpy as np
import pandas as pd
import yaml

from scripts import shared_monitoring_engine as contract
from scripts.shared_monitoring_engine import (
    PROJECT_CONFIG_PATH,
    build_phase2_trace,
    build_phase3a_average_statistics_row,
    build_phase3a_average_values,
    check_membership_invariants,
    check_trace_invariants,
    evaluate_root_states,
    load_phase1_definitions,
    normalize_phase2_readings,
    prepare_monitoring,
    root_correctness_summary,
    run_phase3a_two_sided,
    validate_monitoring_preparation,
    validate_preparation_policy,
)


SENSOR_IDS = ("A", "C", "D", "E", "F", "G")


def make_config(bucket_count):
    """Build a minimal inclusive one-minute config for a synthetic trace."""
    start = dt.datetime(2022, 1, 1, tzinfo=dt.timezone.utc)
    end = start + dt.timedelta(minutes=bucket_count - 1)
    return {
        "selected_sensor_ids": list(SENSOR_IDS),
        "selected_sensor_temperature_columns": [
            f"{sensor}_temperature" for sensor in SENSOR_IDS
        ],
        "start_timestamp_utc": start.isoformat(),
        "end_timestamp_utc": end.isoformat(),
        "endpoint_convention": "inclusive",
        "expected_bucket_count": bucket_count,
        "expected_elapsed_minutes": bucket_count - 1,
        "sampling_interval_seconds": 60,
    }


def make_rows(sensor_values):
    """Convert row-major sensor values into timestamped six-sensor records."""
    start = dt.datetime(2022, 1, 1, tzinfo=dt.timezone.utc)
    rows = []
    for offset, readings in enumerate(sensor_values):
        timestamp = start + dt.timedelta(minutes=offset)
        row = {
            "bucket_epoch": int(timestamp.timestamp()),
            "bucket_time_utc": timestamp.isoformat(),
        }
        row.update(
            {
                f"{sensor}_temperature": value
                for sensor, value in zip(SENSOR_IDS, readings)
            }
        )
        rows.append(row)
    return rows


class Phase3AStatisticsTests(unittest.TestCase):
    """Check stable-cohort mean/P90 preparation and its evidence boundaries."""

    def test_round_trip_csv_parser_preserves_full_precision_p90(self):
        """Retain the exact decimal P90 through round-trip CSV parsing."""
        csv_text = "series_name,p90\n" "phase3a_stable_cohort,22.428666649999997\n"
        parsed = pd.read_csv(io.StringIO(csv_text), float_precision="round_trip")
        self.assertEqual(float(parsed.iloc[0]["p90"]), 22.428666649999997)

    def test_six_sensor_average_and_linear_p90_keep_full_precision(self):
        """Derive six-sensor means and linear P90 without display rounding."""
        rows = make_rows(
            [
                (0.0, 1.0, 2.0, 3.0, 4.0, 5.0),
                (1.0, 2.0, 3.0, 4.0, 5.0, 6.0),
                (5.0, 6.0, 7.0, 8.0, 9.0, 10.0),
            ]
        )
        averages = build_phase3a_average_values(rows, make_config(3))
        statistics_row = build_phase3a_average_statistics_row(averages, [5, 10, 90, 95])

        self.assertEqual(averages, [2.5, 3.5, 7.5])
        self.assertTrue(math.isclose(statistics_row["p90"], 6.7))
        self.assertEqual(statistics_row["series_name"], "phase3a_stable_cohort")
        self.assertEqual(statistics_row["filtered_snapshot_count"], 3)
        self.assertEqual(statistics_row["non_null_value_count"], 3)

    def test_phase3a_averages_require_complete_finite_contiguous_input(self):
        """Reject gaps, missing readings, and non-finite cohort values."""
        rows = make_rows([(1.0,) * 6, (2.0,) * 6, (3.0,) * 6])
        config = make_config(3)
        self.assertEqual(build_phase3a_average_values(rows, config), [1.0, 2.0, 3.0])

        gap_rows = make_rows([(1.0,) * 6, (2.0,) * 6, (3.0,) * 6])
        gap_rows[1]["bucket_epoch"] += 30
        gap_rows[1]["bucket_time_utc"] = (
            dt.datetime.fromisoformat(gap_rows[1]["bucket_time_utc"])
            + dt.timedelta(seconds=30)
        ).isoformat()
        with self.assertRaisesRegex(ValueError, "timestamp gap"):
            build_phase3a_average_values(gap_rows, config)

        missing_rows = make_rows([(1.0,) * 6, (2.0,) * 6, (3.0,) * 6])
        missing_rows[1]["D_temperature"] = ""
        with self.assertRaisesRegex(ValueError, "D_temperature"):
            build_phase3a_average_values(missing_rows, config)

        nonfinite_rows = make_rows([(1.0,) * 6, (2.0,) * 6, (3.0,) * 6])
        nonfinite_rows[1]["E_temperature"] = float("inf")
        with self.assertRaisesRegex(ValueError, "E_temperature"):
            build_phase3a_average_values(nonfinite_rows, config)

    def test_authoritative_threshold_provenance(self):
        """Require a derived threshold policy rather than a stored numeric override."""
        config = {
            "threshold": {
                "source_series": "phase3a_stable_cohort", "statistic": "p90",
                "production_script": "scripts/shared_monitoring_engine.py",
                "status": "derived_from_aligned_input",
            }
        }
        validate_preparation_policy(config)
        config["threshold"]["p90_value"] = 22.4
        with self.assertRaisesRegex(ValueError, "run evidence"):
            validate_preparation_policy(config)

    def test_preparation_is_read_only_and_rejects_stale_evidence(self):
        """Keep shared preparation read-only and fail on stale input identity."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "config").mkdir()
            (root / "artifacts" / "phase1_operational").mkdir(parents=True)
            config = make_config(3)
            config.update(input_source="artifacts/aligned.csv", threshold={
                "source_series": "phase3a_stable_cohort", "statistic": "p90",
                "production_script": "scripts/shared_monitoring_engine.py",
                "status": "derived_from_aligned_input",
            })
            config_path = root / PROJECT_CONFIG_PATH
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(yaml.safe_dump({"phase3a_experiment": config}))
            rows = make_rows([(1.0,) * 6, (2.0,) * 6, (3.0,) * 6])
            input_path = root / config["input_source"]
            with input_path.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            status = root / "artifacts" / "phase1_operational" / "phase1_run.json"
            repository = Path(__file__).resolve().parents[1]
            (root / "scripts").mkdir()
            for relative in ("scripts/phase1_implement.ipynb",):
                (root / relative).write_bytes((repository / relative).read_bytes())
            status.write_text(json.dumps({
                "schema_version": 1, "limited_run": False, "status": "passed",
                "hashes": {"phase1_aligned_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest()},
                "implementation_sha256": hashlib.sha256((root / "scripts" / "phase1_implement.ipynb").read_bytes()).hexdigest(),
                "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
            }))
            before = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
            prepared = prepare_monitoring(root)
            self.assertEqual(prepared["p90_value"], 2.8000000000000003)
            validate_monitoring_preparation(root, prepared)
            self.assertEqual(before, {path: path.read_bytes() for path in root.rglob("*") if path.is_file()})
            prepared["p90_value"] = 999
            with self.assertRaisesRegex(ValueError, "stale"):
                validate_monitoring_preparation(root, prepared)
            status.write_text('{"status":"failed"}')
            with self.assertRaisesRegex(ValueError, "failed"):
                prepare_monitoring(root)
            status.unlink()
            with self.assertRaises(FileNotFoundError):
                prepare_monitoring(root)

    def test_definition_loading_does_not_run_or_require_raw_inputs(self):
        """Load reusable Phase 1 definitions without executing its pipeline."""
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            isolated = Path(temporary)
            (isolated / "scripts").mkdir()
            notebook = root / "scripts" / "phase1_implement.ipynb"
            (isolated / "scripts" / notebook.name).write_bytes(notebook.read_bytes())
            before = list(isolated.rglob("*"))
            core = load_phase1_definitions(isolated)
            audit = load_phase1_definitions(isolated, audit=True)
            self.assertTrue(callable(core.run_phase1))
            self.assertTrue(callable(audit.run_qc))
            self.assertEqual(before, list(isolated.rglob("*")))
            with self.assertRaisesRegex(ValueError, "explicit output"):
                core.run_phase1(root, limit_files=1)


class ArtifactContractTests(unittest.TestCase):
    """Verify publication receipts, source identity, and import-safe behavior."""

    def setUp(self):
        """Create an isolated synthetic repository for artifact-contract checks."""
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        for name in contract.SOURCES:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(name.encode())
        self.summary = {
            "schema_version": 1,
            "events_artifact": "../phase2_operational/phase2_events.csv",
            "validation_artifact": "../phase2_operational/phase2_validation.json",
            "monitoring_preparation": {"fixture": "independent contract test"},
        }
        preparation_mock = mock.patch.object(
            contract, "prepare_monitoring", return_value=self.summary["monitoring_preparation"],
        )
        preparation_mock.start()
        self.addCleanup(preparation_mock.stop)
        self.events = b"event\n1\n"
        import hashlib
        self.summary["events_sha256"] = hashlib.sha256(self.events).hexdigest()
        with mock.patch.object(contract, "_generate", return_value=(self.summary, self.events)):
            contract.publish(self.root)
        self.receipt = {
            "schema_version": 1, "status": "passed",
            "checks": ["unit_tests", "isolated_reproduction"], "test_count": 1,
            "skipped": [], "failures": [], "errors": [],
            "summary_sha256": contract._hash(self.root / contract.SUMMARY),
            "events_sha256": contract._hash(self.root / contract.EVENTS),
            "source_sha256": contract._source_hashes(self.root),
        }
        self.write_receipt()

    def write_receipt(self):
        """Write a passing fixture receipt bound to current synthetic hashes."""
        (self.root / contract.RECEIPT).write_text(json.dumps(self.receipt), encoding="utf-8")

    def test_receipt_is_required_and_must_pass(self):
        """Reject absent, failed, or incomplete independent validation evidence."""
        self.assertEqual(contract.load_validated(self.root), self.summary)
        (self.root / contract.RECEIPT).unlink()
        with self.assertRaises(FileNotFoundError):
            contract.load_validated(self.root)
        for status in ("failed", "in_progress"):
            self.receipt["status"] = status
            self.write_receipt()
            with self.assertRaises(ValueError):
                contract.load_validated(self.root)

    def test_changed_evidence_is_rejected(self):
        """Detect changed source or artifact bytes after receipt creation."""
        for relative in (contract.SUMMARY, contract.EVENTS, *map(Path, contract.SOURCES)):
            path = self.root / relative
            original = path.read_bytes()
            with self.subTest(path=relative):
                path.write_bytes(original + b" ")
                with self.assertRaises((ValueError, json.JSONDecodeError)):
                    contract.load_validated(self.root)
                path.write_bytes(original)

    def test_partial_or_mixed_runs_are_rejected(self):
        """Reject incomplete evidence bundles and artifacts from mixed run IDs."""
        self.summary["events_sha256"] = "0" * 64
        (self.root / contract.SUMMARY).write_bytes(contract._json_bytes(self.summary))
        self.receipt["summary_sha256"] = contract._hash(self.root / contract.SUMMARY)
        self.write_receipt()
        with self.assertRaises(ValueError):
            contract.load_validated(self.root)

    def test_import_does_not_run_or_write_artifacts(self):
        """Verify importing the shared engine does not publish or execute work."""
        repository = Path(__file__).resolve().parents[1]
        before = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        code = (
            "from pathlib import Path; import sys; "
            f"sys.path.insert(0, {str(repository)!r}); "
            "import scripts.shared_monitoring_engine"
        )
        subprocess.run(
            [sys.executable, "-B", "-c", code],
            cwd=self.root, capture_output=True, text=True, check=True,
        )
        after = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        self.assertEqual(before, after)


class MembershipTests(unittest.TestCase):
    """Exercise general Phase 2 membership changes and observed-only transitions."""

    def trace(self, values, threshold=20.0):
        """Build a synthetic Phase 2 trace for the supplied changing membership."""
        frame = pd.DataFrame(values, columns=["A_temperature", "B_temperature"])
        frame["bucket_epoch"] = np.arange(len(frame)) * 60
        frame["bucket_time_utc"] = [f"t{i}" for i in range(len(frame))]
        result = build_phase2_trace(frame, ["A_temperature", "B_temperature"], threshold)
        self.assertEqual(check_membership_invariants(result), [])
        self.assertEqual(check_trace_invariants(
            result, frame, ["A_temperature", "B_temperature"], threshold
        ), [])
        return result

    def test_startup_departure_and_return(self):
        """Check startup, departure, and return effects on member state."""
        rows = self.trace([[10, 10], [10, None], [10, 10]])
        self.assertEqual(rows.total_message_count.tolist(), [6, 3, 6])
        self.assertEqual(rows.event_resync_performed.tolist(), [1, 1, 1])
        self.assertEqual(rows.event_departing_sensor_names.tolist(), ["", "B", ""])
        self.assertEqual(rows.event_returning_sensor_names.tolist(), ["", "", "B"])
        self.assertEqual(rows.event_membership_changed.tolist(), [0, 1, 1])
        self.assertTrue(pd.isna(rows.loc[2, "entry_B_reference_value"]))

    def test_stable_membership_and_local_trigger(self):
        """Keep stable membership silent until a local deviation triggers."""
        rows = self.trace([[10, 10], [10, 10], [20, 10], [20, 10]])
        self.assertEqual(rows.event_resync_performed.tolist(), [1, 0, 1, 0])
        self.assertEqual(rows.total_message_count.tolist(), [6, 0, 7, 0])
        self.assertEqual(rows.loc[2, "entry_xbar_t0"], 10)
        self.assertEqual(rows.loc[2, "exit_xbar_t0_if_resync"], 15)
        self.assertEqual(rows.loc[3, "entry_xbar_t0"], 15)
        self.assertEqual(rows.loc[3, "entry_A_reference_value"], 20)

    def test_simultaneous_departure_and_return(self):
        """Resolve simultaneous membership changes from current observations only."""
        rows = self.trace([[10, None], [None, 12]])
        self.assertEqual(rows.total_message_count.tolist(), [3, 3])
        self.assertEqual(rows.loc[1, "event_departing_sensor_names"], "A")
        self.assertEqual(rows.loc[1, "event_returning_sensor_names"], "B")
        self.assertEqual(rows.loc[1, "observed_global_average"], 12)

    def test_membership_sync_above_threshold(self):
        """Synchronize on membership change even when the global mean is violated."""
        rows = self.trace([[21, 21], [22, None]])
        self.assertEqual(rows.total_message_count.tolist(), [6, 3])
        self.assertEqual(rows.loc[1, "event_resync_reason"], "sensor_membership_changed")
        self.assertEqual(rows.loc[1, "event_resync_causes"], "sensor_membership_changed")
        self.assertEqual(rows.loc[1, "trigger_message_count"], 0)

    def test_all_offline_pending_then_return(self):
        """Carry pending membership work across empty buckets until a sensor returns."""
        rows = self.trace([[10, 10], [None, None], [None, None], [12, None]])
        self.assertEqual(rows.total_message_count.tolist(), [6, 0, 0, 3])
        self.assertEqual(rows.exit_resync_pending.tolist(), [0, 1, 1, 0])
        self.assertTrue(rows.loc[1:2, "global_violation"].isna().all())
        self.assertTrue(rows.loc[1:2, "observed_global_average"].isna().all())
        self.assertTrue(rows.loc[1:2, "legacy_event_false_alert"].isna().all())
        self.assertTrue(rows.loc[1:2, "exit_xbar_t0_if_resync"].isna().all())
        self.assertEqual(rows.loc[3, "entry_xbar_t0"], 10)
        self.assertEqual(rows.loc[3, "exit_xbar_t0_if_resync"], 12)

    def test_leading_empty_rows_do_not_look_ahead(self):
        """Avoid using future sensor availability to decide earlier empty rows."""
        rows = self.trace([[None, None], [None, None], [12, None], [12, None]])
        self.assertTrue(rows.loc[:2, "entry_xbar_t0"].isna().all())
        self.assertEqual(rows.event_initialization_performed.tolist(), [0, 0, 1, 0])
        self.assertEqual(rows.total_message_count.tolist(), [0, 0, 3, 0])
        self.assertEqual(rows.loc[3, "entry_xbar_t0"], 12)

    def test_entirely_empty_run(self):
        """Handle a trace with no observed sensors without inventing state."""
        rows = self.trace([[None, None], [None, None]])
        self.assertEqual(rows.total_message_count.sum(), 0)
        self.assertTrue(rows.global_violation.isna().all())
        self.assertEqual(rows.exit_resync_pending.tolist(), [1, 1])

    def test_zero_allowance_then_stable_violated_state(self):
        """Preserve zero-allowance checks while retaining a known violated state."""
        rows = self.trace([[20, 20], [20, 20], [21, 21], [21, 21]])
        self.assertEqual(rows.global_violation.tolist(), [1, 1, 1, 1])
        self.assertEqual(rows.loc[1, "event_resync_reason"], "local_constraint_violation")
        self.assertEqual(rows.loc[3, "event_resync_reason"], "")
        self.assertEqual(rows.loc[3, "root_known_state"], "VIOLATED")
        self.assertEqual(rows.loc[3, "trigger_message_count"], 0)

    def test_nonfinite_reading_is_explicit_error(self):
        """Reject non-finite observed values instead of silently excluding them."""
        with self.assertRaisesRegex(ValueError, "Non-finite sensor reading"):
            self.trace([[10, float("inf")]])

    def test_threshold_decisions_use_unrounded_values(self):
        """Apply threshold comparisons to source precision rather than rounded text."""
        rows = self.trace([[19.99999, 19.99999], [20.00001, 20.00001]])
        self.assertEqual(rows.observed_global_average.tolist(), [20, 20])
        self.assertEqual(rows.global_violation.tolist(), [0, 1])

    def test_trace_can_preserve_full_precision_for_protocol_comparison(self):
        """Keep full precision available for exact Phase 2/C0 protocol comparison."""
        frame = pd.DataFrame(
            [[10.123456789, 11.987654321], [10.123456789, 11.987654321]],
            columns=["A_temperature", "B_temperature"],
        )
        frame["bucket_epoch"] = [0, 60]
        frame["bucket_time_utc"] = ["t0", "t1"]
        rounded = build_phase2_trace(
            frame, ["A_temperature", "B_temperature"], 20.0
        )
        full_precision = build_phase2_trace(
            frame, ["A_temperature", "B_temperature"], 20.0,
            round_output=False,
        )
        self.assertEqual(rounded.loc[0, "observed_A_temperature"], 10.1235)
        self.assertEqual(full_precision.loc[0, "observed_A_temperature"], 10.123456789)
        self.assertEqual(
            full_precision.loc[1, "entry_A_local_allowance"],
            abs(20.0 - (10.123456789 + 11.987654321) / 2),
        )

    def test_membership_pending_survives_empty_buckets_above_threshold(self):
        """Retain unresolved membership changes across empty violated buckets."""
        rows = self.trace([[21, 21], [None, None], [None, None], [19, None]])
        self.assertEqual(rows.total_message_count.tolist(), [6, 0, 0, 3])
        self.assertEqual(rows.loc[3, "event_resync_reason"], "sensor_membership_changed")
        self.assertEqual(rows.loc[3, "event_resync_causes"], "sensor_membership_changed")
        self.assertEqual(rows.loc[3, "exit_resync_pending"], 0)

    def test_normalization_preserves_missing_and_numeric_strings(self):
        """Normalize numeric text while preserving explicit missing observations."""
        frame = pd.DataFrame({
            "bucket_epoch": [0, 60, 120],
            "A_temperature": ["12.5", None, np.nan],
        })
        normalized = normalize_phase2_readings(frame, ["A_temperature"])
        self.assertEqual(normalized.loc[0, "A_temperature"], 12.5)
        self.assertTrue(normalized.loc[1:, "A_temperature"].isna().all())
        self.assertEqual(frame.loc[0, "A_temperature"], "12.5")

    def test_normalization_rejects_malformed_and_nonfinite_readings(self):
        """Reject malformed or non-finite readings during trace normalization."""
        for value in ("bad", "NA", "NaN", " ", float("inf"), -float("inf")):
            with self.subTest(value=value):
                frame = pd.DataFrame({
                    "bucket_epoch": [0, 60],
                    "A_temperature": [10, value],
                })
                with self.assertRaisesRegex(ValueError, "A_temperature at bucket 60"):
                    normalize_phase2_readings(frame, ["A_temperature"])


class CorrectnessTests(unittest.TestCase):
    """Verify two-sided root-state correctness and isolation of the offline oracle."""

    def trace(self, values, threshold=20.0):
        """Build a compact correctness trace from synthetic sensor values."""
        sensors = [f"{name}_temperature" for name in "ABCD"[:len(values[0])]]
        frame = pd.DataFrame(values, columns=sensors, dtype=float)
        frame["bucket_epoch"] = np.arange(len(frame)) * 60
        frame["bucket_time_utc"] = [f"t{i}" for i in range(len(frame))]
        rows = build_phase2_trace(frame, sensors, threshold)
        self.assertEqual(check_trace_invariants(rows, frame, sensors, threshold), [])
        return rows, frame, sensors

    def test_warming_local_violation_global_safe(self):
        """Distinguish a local trigger from a global threshold violation."""
        rows, _, _ = self.trace([[10, 10], [20, 10]])
        self.assertEqual(rows.distributed_constraint_state.tolist(), ["NOT_EVALUABLE", "VIOLATING"])
        self.assertEqual(rows.centralized_constraint_state.tolist(), ["FEASIBLE", "FEASIBLE"])
        self.assertEqual(rows.loc[1, "event_resync_request_count"], 1)
        self.assertEqual(rows.loc[1, "legacy_event_false_alert"], 1)

    def test_constant_above_threshold_stays_known_without_messages(self):
        """Keep root-known VIOLATED state during silent unchanged observations."""
        rows, _, _ = self.trace([[21, 21]] * 5)
        self.assertEqual(rows.total_message_count.tolist(), [6, 0, 0, 0, 0])
        self.assertEqual(rows.root_known_state.tolist(), ["VIOLATED"] * 5)
        self.assertEqual(rows.entry_root_allowance.iloc[1:].tolist(), [1] * 4)
        self.assertEqual(rows.exit_resync_pending.tolist(), [0] * 5)
        self.assertEqual(rows.legacy_event_false_negative.tolist(), [0, 1, 1, 1, 1])
        self.assertEqual(root_correctness_summary(rows)["correctness_status"], "passed")
        self.assertNotIn("event_exit_delta_negative", rows.columns)
        self.assertNotIn("entry_delta_global", rows.columns)
        self.assertNotIn("negative_delta_from_prior_row", "|".join(rows.event_resync_causes))

    def test_cooling_within_allowance_then_crossing(self):
        """Retain the known state until cooling crosses the permitted boundary."""
        rows, _, _ = self.trace([[22, 22], [21, 21], [19, 19], [19, 19]])
        self.assertEqual(rows.root_known_state.tolist(), ["VIOLATED", "VIOLATED", "SAFE", "SAFE"])
        self.assertEqual(rows.event_resync_performed.tolist(), [1, 0, 1, 0])
        self.assertEqual(rows.loc[2, "event_A_local_deviation"], -3)
        self.assertEqual(rows.loc[2, "trigger_message_count"], 2)
        self.assertEqual(rows.loc[3, "entry_A_reference_value"], 19)
        self.assertEqual(rows.false_violated.sum(), 0)

    def test_opposite_deviations_strictly_inside_equal_allowances(self):
        """Allow opposite sub-boundary deviations without unnecessary collection."""
        rows, _, _ = self.trace([[10, 10], [19, 1], [1, 19]])
        self.assertEqual(rows.total_message_count.tolist(), [6, 0, 0])
        self.assertEqual(rows.root_known_state.tolist(), ["SAFE"] * 3)
        self.assertEqual(rows.loc[1, "event_B_local_deviation"], -9)
        self.assertEqual(rows.loc[1, "event_B_allowance_remaining"], 1)

    def test_negative_deviation_boundary(self):
        """Apply the absolute local-deviation boundary to a negative change."""
        for epsilon, triggered in ((0.000001, 0), (0, 1), (-0.000001, 1)):
            with self.subTest(epsilon=epsilon):
                rows, _, _ = self.trace([[22, 22], [20 + epsilon, 22]])
                self.assertEqual(rows.loc[1, "event_resync_performed"], triggered)
                self.assertEqual(rows.loc[1, "trigger_message_count"], triggered)
                self.assertEqual(rows.false_violated.sum(), 0)

    def test_zero_allowance_unchanged_then_cooling_one_collection_per_bucket(self):
        """Preserve zero-allowance triggers while limiting collection per bucket."""
        rows, _, _ = self.trace([[20, 20], [20, 20], [19, 19], [19, 19]])
        self.assertEqual(rows.root_known_state.tolist(), ["VIOLATED", "VIOLATED", "SAFE", "SAFE"])
        self.assertEqual(rows.total_message_count.tolist(), [6, 8, 8, 0])
        self.assertEqual(rows.event_resync_performed.tolist(), [1, 1, 1, 0])
        self.assertEqual(rows.request_message_count.tolist(), [2, 2, 2, 0])
        self.assertEqual(rows.response_message_count.tolist(), [2, 2, 2, 0])
        self.assertEqual(rows.broadcast_message_count.tolist(), [2, 2, 2, 0])
        self.assertEqual(rows.trigger_message_count.tolist(), [0, 2, 2, 0])
        self.assertEqual(rows.loc[2, "entry_root_allowance"], 0)
        self.assertEqual(rows.loc[3, "entry_root_allowance"], 1)

    def test_oracle_detects_both_injected_root_state_defects(self):
        """Detect independently injected false-safe and false-violated root states."""
        rows, observations, sensors = self.trace([[10, 10], [21, 21]])
        broken = rows.copy()
        broken.loc[0, "root_known_state"] = "VIOLATED"
        broken.loc[1, "root_known_state"] = "SAFE"
        oracle = evaluate_root_states(broken, observations, sensors, 20.0)
        self.assertEqual(oracle.false_safe.tolist(), [0, 1])
        self.assertEqual(oracle.false_violated.tolist(), [1, 0])
        broken[oracle.columns] = oracle
        summary = root_correctness_summary(broken)
        self.assertEqual(summary["correctness_status"], "failed")
        self.assertEqual(summary["false_safe_count"], 1)
        self.assertEqual(summary["false_violated_count"], 1)
        for index, field in ((0, "root_known_state"), (1, "root_known_state")):
            corrupted = rows.copy()
            corrupted.loc[index, field] = broken.loc[index, field]
            self.assertTrue(any(field in error for error in
                                check_trace_invariants(corrupted, observations, sensors, 20.0)))

    def test_offline_checker_changes_cannot_control_communication(self):
        """Prove changing the offline checker does not alter protocol messages."""
        rows, observations, sensors = self.trace([[22, 22], [21, 21], [19, 19]])
        captured = []

        def faulty_oracle(trace, inputs, columns, threshold):
            """Return deliberately wrong truth solely for this negative control."""
            captured.append(trace.copy())
            result = evaluate_root_states(trace, inputs, columns, threshold)
            result["false_safe"] = 1
            return result

        with patch("scripts.shared_monitoring_engine.evaluate_root_states", side_effect=faulty_oracle):
            with self.assertRaisesRegex(ValueError, "false_safe"):
                build_phase2_trace(observations, sensors, 20.0)
        for column in (
            "event_resync_performed", "event_resync_causes", "trigger_message_count",
            "request_message_count", "response_message_count", "broadcast_message_count",
        ):
            self.assertEqual(captured[0][column].tolist(), rows[column].tolist())

    def test_nonfinite_mean_or_allowance_is_an_explicit_failure(self):
        """Fail explicitly when means or allowances become non-finite."""
        with self.assertRaisesRegex(ValueError, "Non-finite Phase 2 mean"):
            self.trace([[1e308, 1e308]])
        with self.assertRaisesRegex(ValueError, "Non-finite root allowance"):
            MembershipTests().trace([[-1e308, -1]], threshold=1.5e308)

    def test_safe_signed_cancellation(self):
        """Confirm opposite signed changes cancel under the cluster/global checks."""
        rows, _, _ = self.trace([[10, 10], [21, -1]])
        self.assertEqual(rows.loc[1, "observed_global_average"], 10)
        self.assertEqual(rows.loc[1, "distributed_constraint_state"], "VIOLATING")
        self.assertEqual(rows.loc[1, "centralized_constraint_state"], "FEASIBLE")
        self.assertEqual(rows.loc[1, "total_message_count"], 8)

    def test_partial_cancellation_crosses_global_threshold(self):
        """Require root escalation when residual signed change crosses the threshold."""
        rows, _, _ = self.trace([[10, 10], [33, 9]])
        self.assertEqual(rows.loc[1, "observed_global_average"], 21)
        self.assertEqual(rows.loc[1, "global_violation"], 1)
        self.assertEqual(rows.loc[1, "event_resync_performed"], 1)
        self.assertEqual(rows.loc[1, "exit_xbar_t0_if_resync"], 21)

    def test_multiple_triggers_one_sync_unequal_initial_temperatures(self):
        """Use unequal sensor references to verify one collection for multiple triggers."""
        rows, _, _ = self.trace([[8, 10, 12], [18, 20, 22]])
        self.assertEqual(rows.loc[1, "event_resync_request_count"], 3)
        self.assertEqual(rows.loc[1, "event_resync_performed"], 1)
        self.assertEqual(rows.loc[1, "total_message_count"], 12)
        self.assertEqual(rows.loc[1, "entry_A_reference_value"], 8)
        self.assertEqual(rows.loc[1, "entry_C_reference_value"], 12)

    def test_local_and_global_boundaries_use_unrounded_values(self):
        """Check exact local/global boundary behavior at full numeric precision."""
        for epsilon, state in ((-0.000001, "FEASIBLE"), (0, "VIOLATING"), (0.000001, "VIOLATING")):
            with self.subTest(epsilon=epsilon):
                rows, _, _ = self.trace([[10, 10], [20 + epsilon, 10]])
                self.assertEqual(rows.loc[1, "distributed_constraint_state"], state)
                self.assertEqual(rows.loc[1, "event_resync_performed"], int(epsilon >= 0))
                rows, _, _ = self.trace([[10, 10], [20 + epsilon, 20 + epsilon]])
                self.assertEqual(rows.loc[1, "global_violation"], int(epsilon >= 0))
                corrupted = rows.copy()
                corrupted.loc[1, "global_violation"] = int(epsilon < 0)
                sensors = ["A_temperature", "B_temperature"]
                source = pd.DataFrame([[10, 10], [20 + epsilon, 20 + epsilon]], columns=sensors)
                source["bucket_epoch"] = [0, 60]
                self.assertTrue(any("global_violation" in error for error in
                                    check_trace_invariants(corrupted, source, sensors, 20.0)))

    def test_forced_rows_report_violations_without_trigger_messages(self):
        """Separate forced correctness rows from protocol-trigger transmissions."""
        rows, _, _ = self.trace([[21, 21], [22, None]])
        self.assertEqual(rows.loc[1, "distributed_constraint_state"], "VIOLATING")
        self.assertEqual(rows.loc[1, "event_A_local_deviation"], 1)
        self.assertEqual(rows.loc[1, "event_A_resync_requested"], 0)
        self.assertEqual(rows.loc[1, "trigger_message_count"], 0)
        self.assertEqual(rows.loc[1, "event_resync_causes"], "sensor_membership_changed")

    def test_cooling_clears_global_and_local_state(self):
        """Refresh root-known and local state when a cooling crossing synchronizes."""
        rows, _, _ = self.trace([[21, 21], [19, 19], [19, 19]])
        self.assertEqual(rows.centralized_constraint_state.tolist(),
                         ["VIOLATING", "FEASIBLE", "FEASIBLE"])
        self.assertEqual(rows.distributed_constraint_state.tolist(),
                         ["NOT_EVALUABLE", "VIOLATING", "FEASIBLE"])
        self.assertEqual(rows.loc[1, "exit_root_allowance_if_resync"], 1)
        self.assertEqual(rows.loc[2, "event_resync_performed"], 0)

    def test_partial_comparison_cannot_claim_feasible(self):
        """Prevent an incomplete comparison from receiving a passing status."""
        rows, _, _ = self.trace([[10, None], [10, 10], [10, 10]])
        self.assertEqual(rows.distributed_constraint_state.tolist(),
                         ["NOT_EVALUABLE", "NOT_EVALUABLE", "FEASIBLE"])
        rows, _, _ = self.trace([[10, None], [20, 10]])
        self.assertEqual(rows.loc[1, "distributed_constraint_state"], "VIOLATING")
        rows, _, _ = self.trace([[None, None], [10, None]])
        self.assertEqual(rows.distributed_constraint_state.tolist(), ["UNDEFINED", "NOT_EVALUABLE"])

    def test_four_sensor_membership_reference_refresh(self):
        """Refresh references using only currently observed Phase 2 members."""
        rows, _, _ = self.trace([[5, 10, 15, 10], [5, None, 15, 10], [5, 11, 15, 10], [5, 11, 15, 10]])
        self.assertEqual(rows.observed_online_sensor_count.tolist(), [4, 3, 4, 4])
        self.assertEqual(rows.total_message_count.tolist(), [12, 9, 12, 0])
        self.assertTrue(pd.isna(rows.loc[2, "entry_B_reference_value"]))
        self.assertEqual(rows.loc[3, "entry_B_reference_value"], 11)
        self.assertEqual(rows.loc[3, "entry_root_allowance"], 9.75)

    def test_departure_raises_mean_without_remaining_sensor_warming(self):
        """Attribute a changed global mean to departure rather than warming."""
        rows, _, _ = self.trace([[10, 25], [None, 25]])
        self.assertEqual(rows.observed_global_average.tolist(), [17.5, 25])
        self.assertEqual(rows.global_violation.tolist(), [0, 1])
        self.assertEqual(rows.loc[1, "event_B_local_deviation"], 0)
        self.assertEqual(rows.loc[1, "distributed_constraint_state"], "FEASIBLE")
        self.assertEqual(rows.loc[1, "event_resync_reason"], "sensor_membership_changed")
        self.assertEqual(rows.loc[1, "event_resync_performed"], 1)
        self.assertEqual(rows.loc[1, "false_safe"], 0)
        self.assertEqual(rows.loc[1, "trigger_message_count"], 0)
        self.assertEqual(rows.loc[1, "total_message_count"], 3)

    def test_return_changes_denominator_and_establishes_next_row_reference(self):
        """Recompute membership mean and references when an offline sensor returns."""
        rows, _, _ = self.trace([[25, None], [25, 10], [25, 10]])
        self.assertEqual(rows.observed_online_sensor_count.tolist(), [1, 2, 2])
        self.assertEqual(rows.observed_global_average.tolist(), [25, 17.5, 17.5])
        self.assertEqual(rows.global_violation.tolist(), [1, 0, 0])
        self.assertEqual(rows.loc[1, "event_returning_sensor_names"], "B")
        self.assertEqual(rows.loc[1, "event_resync_causes"], "sensor_membership_changed")
        self.assertEqual(rows.loc[1, "trigger_message_count"], 0)
        self.assertEqual(rows.total_message_count.tolist(), [3, 6, 0])
        self.assertTrue(pd.isna(rows.loc[1, "entry_B_reference_value"]))
        self.assertEqual(rows.loc[2, "entry_B_reference_value"], 10)
        self.assertEqual(rows.loc[2, "entry_root_allowance"], 2.5)

    def test_trace_validator_detects_corruption_with_bucket_and_field(self):
        """Identify corrupted trace fields with their bucket-level diagnostics."""
        rows, frame, sensors = self.trace([[10, 10], [20, 10], [20, None], [None, None], [19, 19]])
        mutations = [
            (1, "distributed_constraint_state", "FEASIBLE"),
            (1, "event_A_resync_requested", 0),
            (1, "observed_global_average", 16),
            (1, "exit_xbar_t0_if_resync", 17),
            (1, "exit_root_allowance_if_resync", 99),
            (2, "entry_xbar_t0", 99),
            (2, "entry_A_reference_value", 99),
            (2, "entry_A_local_allowance", 99),
            (2, "event_departing_sensor_names", "A"),
            (3, "exit_resync_pending", 0),
            (4, "event_resync_causes", ""),
            (4, "entry_B_reference_value", 12),
        ]
        for index, field, value in mutations:
            with self.subTest(field=field):
                corrupted = rows.copy()
                corrupted.loc[index, field] = value
                errors = check_trace_invariants(corrupted, frame, sensors, 20.0)
                self.assertTrue(any(f"bucket {index * 60}: {field}" in error for error in errors), errors)
        corrupted = rows.copy()
        corrupted.loc[1, "total_message_count"] += 1
        errors = check_trace_invariants(corrupted, frame, sensors, 20.0)
        self.assertTrue(
            any("bucket 60: total_message_count" in error for error in errors),
            errors,
        )
        corrupted = rows.assign(distributed_alert=0)
        self.assertTrue(any("distributed_alert" in error for error in
                            check_trace_invariants(corrupted, frame, sensors, 20.0)))
        corrupted = rows.copy()
        corrupted.loc[1, "event_A_local_deviation"] += 0.000001
        self.assertEqual(check_trace_invariants(corrupted, frame, sensors, 20.0), [])
        self.assertTrue(any("event_A_local_deviation" in error for error in
                            check_trace_invariants(corrupted, frame, sensors, 20.0, rounded=False)))

    def test_csv_export_corruption_has_bucket_field_diagnostic(self):
        """Report the exact bucket and field for a corrupted exported row."""
        rows, frame, sensors = self.trace([[10, 10], [20, 10], [20, None]])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "phase2_trace.csv"
            rows.to_csv(path, index=False)
            exported = pd.read_csv(path)
            exported.loc[1, "observed_global_average"] += 1
            exported.to_csv(path, index=False)

            corrupted_export = pd.read_csv(path)
            errors = check_trace_invariants(corrupted_export, frame, sensors, 20.0)

        self.assertTrue(
            any("bucket 60: observed_global_average" in error for error in errors),
            errors,
        )

    def test_reference_calculation_over_random_stream(self):
        """Compare the online trace with an independent deterministic calculation."""
        rng = np.random.default_rng(108)
        values = rng.uniform(5, 35, size=(120, 4))
        values[rng.random(values.shape) < 0.15] = np.nan
        rows, frame, sensors = self.trace(values.tolist())
        # A small independent oracle advances references after hand-defined events.
        reference = None
        old_online = None
        margin = None
        scheduled = False
        for index, readings in enumerate(values):
            online = np.isfinite(readings)
            current = readings[online]
            mean = float(current.mean()) if len(current) else np.nan
            forcing = reference is None or scheduled or (
                old_online is not None and not np.array_equal(online, old_online)
            )
            if reference is None:
                violations = np.zeros(4, dtype=bool)
                comparable = np.zeros(4, dtype=bool)
            else:
                comparable = online & np.isfinite(reference)
                violations = comparable & (np.abs(readings - reference) >= margin)
            expected_state = (
                "UNDEFINED" if not online.any() else "VIOLATING" if violations.any() else
                "FEASIBLE" if comparable.sum() == online.sum() else "NOT_EVALUABLE"
            )
            self.assertEqual(rows.loc[index, "distributed_constraint_state"], expected_state)
            triggered = 0 if forcing else int(violations.sum())
            synced = len(current) > 0 and (forcing or triggered > 0)
            self.assertEqual(rows.loc[index, "event_resync_performed"], int(synced))
            self.assertEqual(rows.loc[index, "total_message_count"], triggered + (3 * len(current) if synced else 0))
            if synced:
                reference = readings.copy()
                margin = abs(20.0 - mean)
                scheduled = False
            elif not online.any():
                scheduled = True
            old_online = online
        self.assertEqual(check_trace_invariants(rows, frame, sensors, 20.0), [])


class MatchedProductionTests(unittest.TestCase):
    """Validate locked-cohort reproduction, isolated outputs, and fail-closed inputs."""

    def create_matched_fixture(self, root):
        """Create a temporary matched Phase 1/2/3 fixture and prerequisite records."""
        repository = Path(__file__).resolve().parents[1]
        project_config = yaml.safe_load(
            (repository / PROJECT_CONFIG_PATH).read_text(encoding="utf-8")
        )
        config = project_config["phase3a_experiment"]
        artifacts = root / "artifacts"
        artifacts.mkdir()
        references = artifacts / "phase3_operational" / "references"
        references.mkdir(parents=True)
        (root / "scripts").mkdir()
        (root / "config").mkdir()
        phase3_path = root / "scripts" / "phase3_implement.py"
        phase3_path.write_text("protected Phase 3 fixture")
        config_path = root / PROJECT_CONFIG_PATH
        project_config["phase3a_experiment"] = config
        config_path.write_text(yaml.safe_dump(project_config))
        times = pd.date_range(config["start_timestamp_utc"], periods=19984, freq="min")
        frame = pd.DataFrame({
            "bucket_time_utc": [time.isoformat() for time in times],
            "bucket_epoch": [int(time.timestamp()) for time in times],
            **{f"{sensor}_temperature": [21.0] * 1999 + [19.0] * 17985 for sensor in "ACDEFG"},
        })
        input_path = artifacts / "phase1_operational" / "phase1_aligned_temperature.csv"
        input_path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(input_path, index=False)
        publication_path = artifacts / "phase1_operational" / "phase1_run.json"
        publication_path.parent.mkdir(parents=True, exist_ok=True)
        for relative in ("scripts/phase1_implement.ipynb",):
            (root / relative).write_bytes((repository / relative).read_bytes())
        publication_path.write_text(json.dumps({
            "schema_version": 1, "limited_run": False, "status": "passed",
            "hashes": {"phase1_aligned_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest()},
            "implementation_sha256": hashlib.sha256((root / "scripts" / "phase1_implement.ipynb").read_bytes()).hexdigest(),
            "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        }))
        historical = {
            key: config[key] for key in (
                "experiment_name", "input_source", "selected_sensor_ids",
                "start_timestamp_utc", "end_timestamp_utc", "endpoint_convention",
                "boundary_convention",
            )
        }
        historical.update({
            "algorithm": "phase2", "bucket_count": 19984,
            "threshold_value": 19.0 * (1 - (0.9 * 19983 % 1)) + 21.0 * (0.9 * 19983 % 1),
            "threshold_source_series": "phase3a_stable_cohort",
            "total_messages": 38087, "resynchronization_count": 2107,
            "message_category_totals": {
                "trigger_message_count": 161, "request_message_count": 12642,
                "response_message_count": 12642, "broadcast_message_count": 12642,
            },
        })
        history = references / "phase3a_phase2_baseline.json"
        history.write_text(json.dumps(historical))
        historical_rows = artifacts / "phase2_temperature_sensors.csv"
        historical_rows.write_text("protected historical trace")
        old_alpha = references / "phase3a_alpha_results.csv"
        old_alpha.write_text("protected published alpha results")
        protected = {
            path: path.read_bytes() for path in
            (config_path, phase3_path, input_path, history, historical_rows, old_alpha)
        }
        return config, frame, protected

    def test_fresh_process_reproducibility_and_lf_events(self):
        """Reproduce compact events in a fresh process with stable line endings."""
        repository = Path(__file__).resolve().parents[1]
        outputs = []
        with tempfile.TemporaryDirectory() as directory:
            for name in ("first", "second"):
                with self.subTest(run=name):
                    root = Path(directory) / name
                    root.mkdir()
                    _, _, protected = self.create_matched_fixture(root)
                    completed = subprocess.run(
                        [sys.executable, "-B", "-m", "scripts.shared_monitoring_engine", "--root", str(root),
                         "--output-dir", str(root / "isolated")],
                        cwd=repository, capture_output=True, text=True, timeout=120, check=True,
                    )
                    artifacts = root / "isolated"
                    summary_bytes = (artifacts / "phase3a_phase2_two_sided_baseline.json").read_bytes()
                    summary = json.loads(summary_bytes)
                    self.assertEqual(json.loads(completed.stdout), summary)
                    event_bytes = (artifacts / "phase3a_phase2_two_sided_events.csv").read_bytes()
                    self.assertNotIn(b"\r", event_bytes)
                    self.assertTrue(event_bytes.endswith(b"\n"))
                    self.assertEqual(event_bytes.count(b"\n"), summary["resynchronization_count"] + 1)
                    self.assertEqual(
                        event_bytes.split(b"\n", 1)[0].decode("utf-8").split(","),
                        [
                            "bucket_epoch", "bucket_time_utc", "event_resync_causes",
                            "event_triggering_sensor_names", "entry_xbar_t0", "exit_xbar_t0_if_resync",
                            "entry_root_allowance", "exit_root_allowance_if_resync", "root_known_state",
                            "oracle_global_state", "trigger_message_count", "request_message_count",
                            "response_message_count", "broadcast_message_count", "total_message_count",
                        ],
                    )
                    digest = hashlib.sha256(event_bytes).hexdigest()
                    self.assertEqual(summary["events_sha256"], digest)
                    self.assertEqual(summary["bucket_count"], 19984)
                    self.assertEqual(summary["selected_sensor_ids"], list("ACDEFG"))
                    self.assertEqual(
                        summary["threshold_value"],
                        19.0 * (1 - (0.9 * 19983 % 1)) + 21.0 * (0.9 * 19983 % 1),
                    )
                    self.assertEqual(summary["global_threshold_violation_count"], 1999)
                    self.assertEqual(summary["root_state_evaluation_count"], 19984)
                    self.assertEqual(summary["correctness_status"], "passed")
                    for field in (
                        "false_safe_count", "false_violated_count", "root_state_not_evaluable_count",
                        "membership_change_event_count", "membership_triggered_synchronization_count",
                    ):
                        self.assertEqual(summary[field], 0)
                    self.assertEqual(summary["resynchronization_count"], 2)
                    self.assertEqual(summary["monitoring_triggered_synchronization_count"], 1)
                    self.assertEqual(summary["initialization_count"], 1)
                    self.assertEqual(summary["total_messages"], 42)
                    self.assertEqual(summary["local_trigger_transmission_count"], 6)
                    self.assertEqual(summary["message_category_totals"], {
                        "trigger_message_count": 6, "request_message_count": 12,
                        "response_message_count": 12, "broadcast_message_count": 12,
                    })
                    self.assertTrue(summary["message_counts_reconcile"])
                    for path, content in protected.items():
                        self.assertEqual(path.read_bytes(), content)
                        self.assertEqual(
                            summary["provenance"]["protected_artifact_sha256_before_and_after"][
                                str(path.relative_to(root))
                            ],
                            hashlib.sha256(content).hexdigest(),
                        )
                    outputs.append((summary_bytes, summary, event_bytes, digest))
            self.assertEqual(outputs[0], outputs[1])

    def test_separate_current_outputs_preserve_originals_without_a_phase3_notebook(self):
        """Write revised outputs separately and preserve historical files."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, _, protected = self.create_matched_fixture(root)
            original = root / "artifacts" / "phase3a_phase2_two_sided_baseline.json"
            original.write_text("protected original baseline")
            output = root / "artifacts" / "phase2_current"
            summary = run_phase3a_two_sided(root, output)
            self.assertEqual(summary["correctness_status"], "passed")
            self.assertEqual(original.read_text(), "protected original baseline")
            self.assertEqual(json.loads((output / original.name).read_text()), summary)
            for path, content in protected.items():
                self.assertEqual(path.read_bytes(), content)
            self.assertFalse(any((root / "scripts").glob("phase3*.ipynb")))
            for invalid in (
                root, root.parent, root / "artifacts", root / "scripts" / "generated",
                root / "artifacts" / "phase3_baseline_us327" / "generated",
                *(root / "artifacts" / name / "generated" for name in (
                    "phase2_outputs", "phase2_operational", "phase2_archive",
                    "phase3_outputs", "phase3_operational", "phase3_archive",
                )),
            ):
                with self.subTest(path=invalid), self.assertRaises(ValueError):
                    run_phase3a_two_sided(root, invalid)

    def test_locked_runner_preserves_history_and_writes_validated_compact_outputs(self):
        """Run the stable-cohort workflow and reject altered or stale prerequisites."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, frame, protected = self.create_matched_fixture(root)
            artifacts = root / "artifacts"
            input_path = artifacts / "phase1_operational" / "phase1_aligned_temperature.csv"
            config_path = root / PROJECT_CONFIG_PATH
            summary = run_phase3a_two_sided(root)
            self.assertEqual(summary["bucket_count"], 19984)
            self.assertEqual(
                summary["threshold_value"],
                19.0 * (1 - (0.9 * 19983 % 1)) + 21.0 * (0.9 * 19983 % 1),
            )
            self.assertEqual(summary["global_threshold_violation_count"], 1999)
            self.assertEqual(summary["correctness_status"], "passed")
            self.assertEqual(summary["false_safe_count"], 0)
            self.assertEqual(summary["false_violated_count"], 0)
            self.assertEqual(summary["resynchronization_count"], 2)
            self.assertEqual(summary["total_messages"], 42)
            self.assertEqual(summary["message_category_totals"], {
                "trigger_message_count": 6, "request_message_count": 12,
                "response_message_count": 12, "broadcast_message_count": 12,
            })
            self.assertEqual(summary["centralized_sensor_transmission_reference"], 119904)
            self.assertEqual(summary["historical_comparison"]["total_messages"], 38087)
            self.assertEqual(set(path.name for path in artifacts.iterdir()) - {
                "phase1_operational",
                "phase2_temperature_sensors.csv", "phase3_operational",
            }, {"phase3a_phase2_two_sided_events.csv", "phase3a_phase2_two_sided_baseline.json"})
            events = pd.read_csv(artifacts / "phase3a_phase2_two_sided_events.csv")
            self.assertEqual(len(events), 2)
            self.assertEqual(events.root_known_state.tolist(), ["VIOLATED", "SAFE"])
            for path, content in protected.items():
                self.assertEqual(path.read_bytes(), content)
            frame.loc[1, "A_temperature"] = np.nan
            frame.to_csv(input_path, index=False)
            with self.assertRaisesRegex(ValueError, "stale"):
                run_phase3a_two_sided(root)
            publication_path = artifacts / "phase1_operational" / "phase1_run.json"
            publication = json.loads(publication_path.read_text())
            publication["hashes"]["phase1_aligned_sha256"] = hashlib.sha256(input_path.read_bytes()).hexdigest()
            publication_path.write_text(json.dumps(publication))
            with self.assertRaisesRegex(ValueError, "finite A_temperature"):
                run_phase3a_two_sided(root)
            frame.loc[1, "A_temperature"] = 21.0
            frame.loc[1, "bucket_epoch"] += 1
            frame.to_csv(input_path, index=False)
            publication["hashes"]["phase1_aligned_sha256"] = hashlib.sha256(input_path.read_bytes()).hexdigest()
            publication_path.write_text(json.dumps(publication))
            with self.assertRaisesRegex(ValueError, "bucket_epoch"):
                run_phase3a_two_sided(root)
            config["selected_sensor_ids"] = list("ABCDEF")
            project_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            project_config["phase3a_experiment"] = config
            config_path.write_text(yaml.safe_dump(project_config))
            publication["config_sha256"] = hashlib.sha256(config_path.read_bytes()).hexdigest()
            publication_path.write_text(json.dumps(publication))
            with self.assertRaisesRegex(ValueError, "selected_sensor_ids"):
                run_phase3a_two_sided(root)


if __name__ == "__main__":
    unittest.main()
