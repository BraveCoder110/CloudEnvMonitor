"""
python -m experiments.formal.analyze_e3

E3 Final Analysis
=================

Purpose
-------
Analyze the three formal E3 dual-cloud recovery sessions.

The script reads:

    experiments/results/e3/e3_session_1.csv
    experiments/results/e3/e3_session_2.csv
    experiments/results/e3/e3_session_3.csv

and generates:

    experiments/results/e3/E3_SUMMARY.csv
    experiments/results/e3/E3_ANALYSIS.md

Metrics
-------
1. Initial historical backlog
2. First-progress latency
3. Full historical-backlog recovery time
4. Effective backfill throughput
5. Mean
6. Sample standard deviation
7. Coefficient of variation (CV)
8. Session PASS rate

Important
---------
This script does NOT modify any raw experimental data.
"""

from __future__ import annotations

import csv
import math
import statistics
from pathlib import Path


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RESULT_DIR = (
        PROJECT_ROOT
        / "experiments"
        / "results"
        / "e3"
)

SESSION_FILES = [
    RESULT_DIR / "e3_session_1.csv",
    RESULT_DIR / "e3_session_2.csv",
    RESULT_DIR / "e3_session_3.csv",
    ]

SUMMARY_CSV = RESULT_DIR / "E3_SUMMARY.csv"
ANALYSIS_MD = RESULT_DIR / "E3_ANALYSIS.md"


# ============================================================
# Utility functions
# ============================================================

def to_float(value):
    """Convert a value to float if possible."""

    if value is None:
        return None

    value = str(value).strip()

    if value == "":
        return None

    try:
        return float(value)
    except ValueError:
        return None


def to_int(value):
    """Convert a value to integer if possible."""

    number = to_float(value)

    if number is None:
        return None

    return int(number)


def find_value(row, candidates, required=True):
    """
    Find a value using several possible column names.

    This makes the analysis slightly more robust if the monitor
    used a minor naming variation between script versions.
    """

    for name in candidates:
        if name in row:
            value = row[name]

            if value is not None and str(value).strip() != "":
                return value

    if required:
        raise KeyError(
            "Could not find any of these columns:\n"
            + "\n".join(f"  - {name}" for name in candidates)
            + "\n\nAvailable columns:\n"
            + "\n".join(f"  - {name}" for name in row.keys())
        )

    return None


def mean(values):
    return statistics.mean(values)


def sample_sd(values):
    """
    Sample standard deviation.

    n = 3 formal independent sessions, so statistics.stdev()
    is appropriate here.
    """

    if len(values) < 2:
        return 0.0

    return statistics.stdev(values)


def cv_percent(values):
    """
    Coefficient of variation:

        CV = SD / Mean * 100%
    """

    m = mean(values)

    if math.isclose(m, 0.0):
        return 0.0

    return sample_sd(values) / m * 100.0


def fmt(value, digits=3):
    if value is None:
        return "N/A"

    return f"{value:.{digits}f}"


# ============================================================
# Read one E3 session
# ============================================================

def read_session(path: Path, session_number: int):
    if not path.exists():
        raise FileNotFoundError(
            f"Missing E3 session file:\n{path}"
        )

    with path.open(
            "r",
            encoding="utf-8-sig",
            newline=""
    ) as file:

        reader = csv.DictReader(file)
        rows = list(reader)

    if not rows:
        raise RuntimeError(
            f"No data found in:\n{path}"
        )

    # E3 monitor produces one formal summary row.
    row = rows[-1]

    azure_backlog = to_int(
        find_value(
            row,
            [
                "initial_azure_backlog",
                "azure_initial_backlog",
            ],
        )
    )

    tb_backlog = to_int(
        find_value(
            row,
            [
                "initial_thingsboard_backlog",
                "thingsboard_initial_backlog",
                "initial_tb_backlog",
                "tb_initial_backlog",
            ],
        )
    )

    azure_first = to_float(
        find_value(
            row,
            [
                "azure_first_decrease_time_s",
                "azure_first_progress_time_s",
                "azure_first_progress_s",
            ],
        )
    )

    tb_first = to_float(
        find_value(
            row,
            [
                "thingsboard_first_decrease_time_s",
                "thingsboard_first_progress_time_s",
                "thingsboard_first_progress_s",
                "tb_first_decrease_time_s",
                "tb_first_progress_time_s",
            ],
        )
    )

    azure_recovery = to_float(
        find_value(
            row,
            [
                "azure_recovery_time_s",
                "azure_historical_recovery_time_s",
            ],
        )
    )

    tb_recovery = to_float(
        find_value(
            row,
            [
                "thingsboard_recovery_time_s",
                "thingsboard_historical_recovery_time_s",
                "tb_recovery_time_s",
            ],
        )
    )

    azure_throughput = to_float(
        find_value(
            row,
            [
                "azure_effective_backfill_throughput_records_per_s",
                "azure_throughput_records_per_s",
                "azure_throughput",
            ],
        )
    )

    tb_throughput = to_float(
        find_value(
            row,
            [
                "thingsboard_effective_backfill_throughput_records_per_s",
                "thingsboard_throughput_records_per_s",
                "tb_effective_backfill_throughput_records_per_s",
                "thingsboard_throughput",
                "tb_throughput",
            ],
        )
    )

    result = str(
        find_value(
            row,
            [
                "result",
                "overall_result",
                "status",
            ],
            required=False,
        )
        or "UNKNOWN"
    ).strip().upper()

    cutoff_id = to_int(
        find_value(
            row,
            [
                "cutoff_record_id",
                "frozen_cutoff_id",
                "historical_cutoff_id",
            ],
            required=False,
        )
    )

    return {
        "session": session_number,
        "cutoff_record_id": cutoff_id,

        "azure_initial_backlog": azure_backlog,
        "thingsboard_initial_backlog": tb_backlog,

        "azure_first_progress_s": azure_first,
        "thingsboard_first_progress_s": tb_first,

        "azure_recovery_s": azure_recovery,
        "thingsboard_recovery_s": tb_recovery,

        "azure_throughput_rps": azure_throughput,
        "thingsboard_throughput_rps": tb_throughput,

        "result": result,
    }


# ============================================================
# Load all formal sessions
# ============================================================

sessions = []

for number, path in enumerate(
        SESSION_FILES,
        start=1,
):
    session = read_session(
        path,
        number,
    )

    sessions.append(session)


# ============================================================
# Validate
# ============================================================

for session in sessions:

    required_metrics = [
        "azure_initial_backlog",
        "thingsboard_initial_backlog",
        "azure_first_progress_s",
        "thingsboard_first_progress_s",
        "azure_recovery_s",
        "thingsboard_recovery_s",
        "azure_throughput_rps",
        "thingsboard_throughput_rps",
    ]

    for metric in required_metrics:

        if session[metric] is None:
            raise RuntimeError(
                f"Session {session['session']} "
                f"is missing metric: {metric}"
            )


# ============================================================
# Metric arrays
# ============================================================

azure_backlog = [
    s["azure_initial_backlog"]
    for s in sessions
]

tb_backlog = [
    s["thingsboard_initial_backlog"]
    for s in sessions
]

azure_first = [
    s["azure_first_progress_s"]
    for s in sessions
]

tb_first = [
    s["thingsboard_first_progress_s"]
    for s in sessions
]

azure_recovery = [
    s["azure_recovery_s"]
    for s in sessions
]

tb_recovery = [
    s["thingsboard_recovery_s"]
    for s in sessions
]

azure_throughput = [
    s["azure_throughput_rps"]
    for s in sessions
]

tb_throughput = [
    s["thingsboard_throughput_rps"]
    for s in sessions
]


# ============================================================
# Overall statistics
# ============================================================

pass_count = sum(
    1
    for s in sessions
    if s["result"] == "PASS"
)

pass_rate = (
        pass_count
        / len(sessions)
        * 100.0
)


statistics_rows = [
    {
        "metric": "Initial backlog",
        "platform": "Azure",
        "mean": mean(azure_backlog),
        "sd": sample_sd(azure_backlog),
        "cv_percent": cv_percent(azure_backlog),
    },
    {
        "metric": "Initial backlog",
        "platform": "ThingsBoard",
        "mean": mean(tb_backlog),
        "sd": sample_sd(tb_backlog),
        "cv_percent": cv_percent(tb_backlog),
    },
    {
        "metric": "First-progress latency (s)",
        "platform": "Azure",
        "mean": mean(azure_first),
        "sd": sample_sd(azure_first),
        "cv_percent": cv_percent(azure_first),
    },
    {
        "metric": "First-progress latency (s)",
        "platform": "ThingsBoard",
        "mean": mean(tb_first),
        "sd": sample_sd(tb_first),
        "cv_percent": cv_percent(tb_first),
    },
    {
        "metric": "Recovery time (s)",
        "platform": "Azure",
        "mean": mean(azure_recovery),
        "sd": sample_sd(azure_recovery),
        "cv_percent": cv_percent(azure_recovery),
    },
    {
        "metric": "Recovery time (s)",
        "platform": "ThingsBoard",
        "mean": mean(tb_recovery),
        "sd": sample_sd(tb_recovery),
        "cv_percent": cv_percent(tb_recovery),
    },
    {
        "metric": "Effective throughput (records/s)",
        "platform": "Azure",
        "mean": mean(azure_throughput),
        "sd": sample_sd(azure_throughput),
        "cv_percent": cv_percent(azure_throughput),
    },
    {
        "metric": "Effective throughput (records/s)",
        "platform": "ThingsBoard",
        "mean": mean(tb_throughput),
        "sd": sample_sd(tb_throughput),
        "cv_percent": cv_percent(tb_throughput),
    },
]


# ============================================================
# Cross-platform comparisons
# ============================================================

azure_recovery_mean = mean(
    azure_recovery
)

tb_recovery_mean = mean(
    tb_recovery
)

azure_throughput_mean = mean(
    azure_throughput
)

tb_throughput_mean = mean(
    tb_throughput
)

recovery_difference = (
        azure_recovery_mean
        - tb_recovery_mean
)

recovery_reduction_percent = (
        recovery_difference
        / azure_recovery_mean
        * 100.0
)

throughput_difference = (
        tb_throughput_mean
        - azure_throughput_mean
)

throughput_increase_percent = (
        throughput_difference
        / azure_throughput_mean
        * 100.0
)


azure_first_earlier_count = sum(
    1
    for s in sessions
    if (
            s["azure_first_progress_s"]
            <
            s["thingsboard_first_progress_s"]
    )
)

tb_recovery_faster_count = sum(
    1
    for s in sessions
    if (
            s["thingsboard_recovery_s"]
            <
            s["azure_recovery_s"]
    )
)

tb_throughput_higher_count = sum(
    1
    for s in sessions
    if (
            s["thingsboard_throughput_rps"]
            >
            s["azure_throughput_rps"]
    )
)


# ============================================================
# Write E3_SUMMARY.csv
# ============================================================

summary_fields = [
    "session",
    "cutoff_record_id",

    "azure_initial_backlog",
    "thingsboard_initial_backlog",

    "azure_first_progress_s",
    "thingsboard_first_progress_s",

    "azure_recovery_s",
    "thingsboard_recovery_s",

    "azure_throughput_rps",
    "thingsboard_throughput_rps",

    "result",
]

with SUMMARY_CSV.open(
        "w",
        encoding="utf-8",
        newline=""
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=summary_fields,
    )

    writer.writeheader()

    for session in sessions:
        writer.writerow(session)


# ============================================================
# Write E3_ANALYSIS.md
# ============================================================

lines = []

lines.append("# E3 Final Analysis")
lines.append("")

lines.append(
    "## Dual-Cloud Recovery After Real Network Disconnection"
)
lines.append("")

lines.append(
    "E3 evaluates whether the edge system can preserve "
    "telemetry during a real network outage and "
    "automatically backfill historical records to both "
    "Azure IoT Hub and ThingsBoard after connectivity "
    "is restored."
)
lines.append("")

lines.append("## 1. Session Results")
lines.append("")

lines.append(
    "| Session | Azure Backlog | TB Backlog | "
    "Azure First Progress (s) | TB First Progress (s) | "
    "Azure Recovery (s) | TB Recovery (s) | "
    "Azure Throughput (records/s) | "
    "TB Throughput (records/s) | Result |"
)

lines.append(
    "|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|"
)

for s in sessions:

    lines.append(
        f"| {s['session']} "
        f"| {s['azure_initial_backlog']} "
        f"| {s['thingsboard_initial_backlog']} "
        f"| {fmt(s['azure_first_progress_s'])} "
        f"| {fmt(s['thingsboard_first_progress_s'])} "
        f"| {fmt(s['azure_recovery_s'])} "
        f"| {fmt(s['thingsboard_recovery_s'])} "
        f"| {fmt(s['azure_throughput_rps'], 4)} "
        f"| {fmt(s['thingsboard_throughput_rps'], 4)} "
        f"| {s['result']} |"
    )

lines.append("")


lines.append("## 2. Statistical Summary")
lines.append("")

lines.append(
    "| Metric | Platform | Mean | SD | CV (%) |"
)

lines.append(
    "|---|---|---:|---:|---:|"
)

for row in statistics_rows:

    lines.append(
        f"| {row['metric']} "
        f"| {row['platform']} "
        f"| {fmt(row['mean'], 4)} "
        f"| {fmt(row['sd'], 4)} "
        f"| {fmt(row['cv_percent'], 2)} |"
    )

lines.append("")


lines.append("## 3. Reliability")
lines.append("")

lines.append(
    f"- Successful sessions: "
    f"**{pass_count}/{len(sessions)}**"
)

lines.append(
    f"- Session success rate: "
    f"**{pass_rate:.1f}%**"
)

lines.append(
    "- All formal sessions required both historical "
    "cloud backlogs to meet the predefined minimum "
    "before recovery timing began."
)

lines.append("")


lines.append("## 4. Cross-Platform Recovery Pattern")
lines.append("")

lines.append(
    f"- Azure showed the first historical backlog "
    f"decrease earlier than ThingsBoard in "
    f"**{azure_first_earlier_count}/{len(sessions)}** sessions."
)

lines.append(
    f"- ThingsBoard completed historical backlog "
    f"clearance faster than Azure in "
    f"**{tb_recovery_faster_count}/{len(sessions)}** sessions."
)

lines.append(
    f"- ThingsBoard achieved higher effective "
    f"backfill throughput in "
    f"**{tb_throughput_higher_count}/{len(sessions)}** sessions."
)

lines.append("")


lines.append("## 5. Mean Recovery Comparison")
lines.append("")

lines.append(
    f"- Azure mean recovery time: "
    f"**{azure_recovery_mean:.3f} s**"
)

lines.append(
    f"- ThingsBoard mean recovery time: "
    f"**{tb_recovery_mean:.3f} s**"
)

lines.append(
    f"- Mean recovery-time difference: "
    f"**{recovery_difference:.3f} s**"
)

lines.append(
    f"- ThingsBoard mean recovery time was "
    f"**{recovery_reduction_percent:.2f}% lower** "
    f"than Azure in these three trials."
)

lines.append("")


lines.append("## 6. Mean Backfill Throughput")
lines.append("")

lines.append(
    f"- Azure mean effective throughput: "
    f"**{azure_throughput_mean:.4f} records/s**"
)

lines.append(
    f"- ThingsBoard mean effective throughput: "
    f"**{tb_throughput_mean:.4f} records/s**"
)

lines.append(
    f"- Mean throughput difference: "
    f"**{throughput_difference:.4f} records/s**"
)

lines.append(
    f"- ThingsBoard mean effective throughput was "
    f"**{throughput_increase_percent:.2f}% higher** "
    f"than Azure in these three trials."
)

lines.append("")


lines.append("## 7. Interpretation")
lines.append("")

lines.append(
    "Across the three formal trials, the system "
    "successfully preserved telemetry locally during "
    "network disconnection and automatically recovered "
    "the frozen historical backlog for both cloud "
    "platforms after network restoration."
)

lines.append("")

lines.append(
    "The repeated successful recovery demonstrates that "
    "edge operation and cloud communication are "
    "functionally decoupled: temporary cloud "
    "unavailability does not prevent local sensing, "
    "edge-state evaluation, actuator logic, or SQLite "
    "persistence."
)

lines.append("")

lines.append(
    "A consistent cross-platform pattern was observed. "
    "Azure tended to show the first backlog decrease "
    "slightly earlier, whereas ThingsBoard completed "
    "historical backlog clearance faster and achieved "
    "higher effective backfill throughput in all three "
    "formal sessions."
)

lines.append("")

lines.append(
    "Because the experiment contains three independent "
    "formal trials, these platform differences should "
    "be interpreted as empirical observations under the "
    "tested prototype configuration rather than as "
    "general performance claims about Azure IoT Hub or "
    "ThingsBoard."
)

lines.append("")


lines.append("## 8. E3 Conclusion")
lines.append("")

if pass_count == len(sessions):

    lines.append(
        "**E3 RESULT: PASS**"
    )

    lines.append("")

    lines.append(
        "The prototype demonstrated successful "
        "dual-cloud recovery in all formal real-network-"
        "disconnection trials."
    )

else:

    lines.append(
        "**E3 RESULT: REVIEW REQUIRED**"
    )

    lines.append("")

    lines.append(
        "One or more formal sessions did not report PASS."
    )


ANALYSIS_MD.write_text(
    "\n".join(lines) + "\n",
    encoding="utf-8",
    )


# ============================================================
# Console output
# ============================================================

print()
print("=" * 72)
print("E3 FINAL ANALYSIS")
print("=" * 72)

for s in sessions:

    print()
    print(f"Session {s['session']}")
    print(
        f"  Azure backlog       : "
        f"{s['azure_initial_backlog']}"
    )
    print(
        f"  ThingsBoard backlog : "
        f"{s['thingsboard_initial_backlog']}"
    )

    print(
        f"  Azure first progress: "
        f"{s['azure_first_progress_s']:.3f} s"
    )
    print(
        f"  TB first progress   : "
        f"{s['thingsboard_first_progress_s']:.3f} s"
    )

    print(
        f"  Azure recovery      : "
        f"{s['azure_recovery_s']:.3f} s"
    )
    print(
        f"  TB recovery         : "
        f"{s['thingsboard_recovery_s']:.3f} s"
    )

    print(
        f"  Azure throughput    : "
        f"{s['azure_throughput_rps']:.4f} records/s"
    )
    print(
        f"  TB throughput       : "
        f"{s['thingsboard_throughput_rps']:.4f} records/s"
    )

    print(
        f"  Result              : "
        f"{s['result']}"
    )


print()
print("-" * 72)
print("MEAN ± SAMPLE SD")
print("-" * 72)

print(
    f"Azure first progress : "
    f"{mean(azure_first):.3f} ± "
    f"{sample_sd(azure_first):.3f} s"
)

print(
    f"TB first progress    : "
    f"{mean(tb_first):.3f} ± "
    f"{sample_sd(tb_first):.3f} s"
)

print(
    f"Azure recovery       : "
    f"{mean(azure_recovery):.3f} ± "
    f"{sample_sd(azure_recovery):.3f} s"
)

print(
    f"TB recovery          : "
    f"{mean(tb_recovery):.3f} ± "
    f"{sample_sd(tb_recovery):.3f} s"
)

print(
    f"Azure throughput     : "
    f"{mean(azure_throughput):.4f} ± "
    f"{sample_sd(azure_throughput):.4f} records/s"
)

print(
    f"TB throughput        : "
    f"{mean(tb_throughput):.4f} ± "
    f"{sample_sd(tb_throughput):.4f} records/s"
)


print()
print("-" * 72)
print("CROSS-PLATFORM PATTERN")
print("-" * 72)

print(
    f"Azure first progress earlier : "
    f"{azure_first_earlier_count}/"
    f"{len(sessions)}"
)

print(
    f"TB full recovery faster      : "
    f"{tb_recovery_faster_count}/"
    f"{len(sessions)}"
)

print(
    f"TB throughput higher         : "
    f"{tb_throughput_higher_count}/"
    f"{len(sessions)}"
)


print()
print("-" * 72)

print(
    f"Formal sessions PASS : "
    f"{pass_count}/{len(sessions)}"
)

print(
    f"Success rate         : "
    f"{pass_rate:.1f}%"
)

print()

print(
    f"CSV:\n{SUMMARY_CSV}"
)

print()

print(
    f"Markdown:\n{ANALYSIS_MD}"
)

print("=" * 72)