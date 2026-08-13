"""
python -m experiments.formal.analyze_e4
E4 Final Analysis
=================

Experiment:
Offline Backlog Scalability of Dual-Cloud Recovery

Formal workload levels:
    10 records
    30 records
    60 records

Formal repetitions:
    3 sessions per workload level

Total formal trials:
    9

Outputs
-------
1. E4_ALL_RUNS.csv
2. E4_SUMMARY.csv
3. E4_ANALYSIS.md
4. E4_RECOVERY_TIME.png
5. E4_THROUGHPUT.png

Primary research question
-------------------------
How does offline telemetry backlog size affect dual-cloud
recovery time and effective historical backfill throughput
after network restoration?

Important interpretation
------------------------
Effective throughput is defined as:

    historical backlog size / full historical recovery time

It is a system-level metric and is NOT raw network throughput.
"""

from __future__ import annotations

import csv
import math
import statistics
from pathlib import Path

import matplotlib.pyplot as plt


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = (
        Path.home()
        / "azure-iot-environment"
)

RESULT_DIR = (
        PROJECT_ROOT
        / "experiments"
        / "results"
        / "e4"
)

ALL_RUNS_PATH = (
        RESULT_DIR
        / "E4_ALL_RUNS.csv"
)

SUMMARY_PATH = (
        RESULT_DIR
        / "E4_SUMMARY.csv"
)

ANALYSIS_PATH = (
        RESULT_DIR
        / "E4_ANALYSIS.md"
)

RECOVERY_PLOT_PATH = (
        RESULT_DIR
        / "E4_RECOVERY_TIME.png"
)

THROUGHPUT_PLOT_PATH = (
        RESULT_DIR
        / "E4_THROUGHPUT.png"
)


BACKLOG_LEVELS = [
    10,
    30,
    60,
]

SESSIONS = [
    1,
    2,
    3,
]


# ============================================================
# Helpers
# ============================================================

def mean(values):
    return statistics.mean(values)


def sample_sd(values):
    if len(values) < 2:
        return 0.0

    return statistics.stdev(values)


def cv_percent(values):
    m = mean(values)

    if math.isclose(
            m,
            0.0,
    ):
        return 0.0

    return (
            sample_sd(values)
            / m
            * 100.0
    )


def linear_regression(
        x_values,
        y_values,
):
    """
    Simple ordinary least squares regression:

        y = intercept + slope * x

    Returns:
        intercept
        slope
        R^2
    """

    x_mean = mean(
        x_values
    )

    y_mean = mean(
        y_values
    )

    numerator = sum(
        (
                x - x_mean
        )
        * (
                y - y_mean
        )
        for x, y
        in zip(
            x_values,
            y_values,
        )
    )

    denominator = sum(
        (
                x - x_mean
        ) ** 2
        for x
        in x_values
    )

    slope = (
            numerator
            / denominator
    )

    intercept = (
            y_mean
            - slope
            * x_mean
    )

    predictions = [
        intercept
        + slope * x
        for x
        in x_values
    ]

    ss_res = sum(
        (
                observed
                - predicted
        ) ** 2
        for observed, predicted
        in zip(
            y_values,
            predictions,
        )
    )

    ss_tot = sum(
        (
                observed
                - y_mean
        ) ** 2
        for observed
        in y_values
    )

    if math.isclose(
            ss_tot,
            0.0,
    ):
        r_squared = 1.0

    else:
        r_squared = (
                1.0
                - ss_res
                / ss_tot
        )

    return {
        "intercept":
            intercept,

        "slope":
            slope,

        "r_squared":
            r_squared,
    }


def read_single_result(
        backlog,
        session,
):
    """
    Read one formal E4 CSV.
    """

    path = (
            RESULT_DIR
            / (
                f"e4_backlog_{backlog}"
                f"_session_{session}.csv"
            )
    )

    if not path.exists():
        raise FileNotFoundError(
            f"Missing formal E4 file:\n"
            f"{path}"
        )

    with path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
    ) as file:

        reader = csv.DictReader(
            file
        )

        rows = list(
            reader
        )

    if len(rows) != 1:
        raise RuntimeError(
            f"Expected exactly one row in:\n"
            f"{path}\n"
            f"Found: {len(rows)}"
        )

    row = rows[0]

    result = {
        "target_backlog":
            int(
                row[
                    "target_backlog"
                ]
            ),

        "session":
            int(
                row[
                    "session"
                ]
            ),

        "cutoff_record_id":
            int(
                row[
                    "cutoff_record_id"
                ]
            ),

        "initial_azure_backlog":
            int(
                row[
                    "initial_azure_backlog"
                ]
            ),

        "initial_thingsboard_backlog":
            int(
                row[
                    "initial_thingsboard_backlog"
                ]
            ),

        "azure_first_progress_s":
            float(
                row[
                    "azure_first_progress_s"
                ]
            ),

        "thingsboard_first_progress_s":
            float(
                row[
                    "thingsboard_first_progress_s"
                ]
            ),

        "azure_recovery_s":
            float(
                row[
                    "azure_recovery_s"
                ]
            ),

        "thingsboard_recovery_s":
            float(
                row[
                    "thingsboard_recovery_s"
                ]
            ),

        "azure_effective_throughput_rps":
            float(
                row[
                    "azure_effective_throughput_rps"
                ]
            ),

        "thingsboard_effective_throughput_rps":
            float(
                row[
                    "thingsboard_effective_throughput_rps"
                ]
            ),

        "result":
            row[
                "result"
            ].strip().upper(),
    }

    if (
            result[
                "target_backlog"
            ]
            != backlog
    ):
        raise RuntimeError(
            f"Backlog mismatch in {path}"
        )

    if (
            result["session"]
            != session
    ):
        raise RuntimeError(
            f"Session mismatch in {path}"
        )

    return result


# ============================================================
# Load all nine formal trials
# ============================================================

runs = []

for backlog in BACKLOG_LEVELS:

    for session in SESSIONS:

        runs.append(
            read_single_result(
                backlog,
                session,
            )
        )


# ============================================================
# Validate formal experiment
# ============================================================

if len(runs) != 9:
    raise RuntimeError(
        "E4 requires exactly "
        "9 formal trials."
    )


for run in runs:

    if (
            run["result"]
            != "PASS"
    ):
        raise RuntimeError(
            "One or more formal E4 "
            "runs did not PASS:\n"
            f"{run}"
        )

    if (
            run[
                "initial_azure_backlog"
            ]
            < run[
        "target_backlog"
    ]
    ):
        raise RuntimeError(
            "Azure initial backlog "
            "is below target."
        )

    if (
            run[
                "initial_thingsboard_backlog"
            ]
            < run[
        "target_backlog"
    ]
    ):
        raise RuntimeError(
            "ThingsBoard initial backlog "
            "is below target."
        )


# ============================================================
# Save E4_ALL_RUNS.csv
# ============================================================

all_run_fields = list(
    runs[0].keys()
)

with ALL_RUNS_PATH.open(
        "w",
        encoding="utf-8",
        newline="",
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=all_run_fields,
    )

    writer.writeheader()

    writer.writerows(
        runs
    )


# ============================================================
# Workload-level statistics
# ============================================================

summary_rows = []


for backlog in BACKLOG_LEVELS:

    group = [
        run
        for run
        in runs
        if (
                run[
                    "target_backlog"
                ]
                == backlog
        )
    ]

    azure_first = [
        r[
            "azure_first_progress_s"
        ]
        for r
        in group
    ]

    tb_first = [
        r[
            "thingsboard_first_progress_s"
        ]
        for r
        in group
    ]

    azure_recovery = [
        r[
            "azure_recovery_s"
        ]
        for r
        in group
    ]

    tb_recovery = [
        r[
            "thingsboard_recovery_s"
        ]
        for r
        in group
    ]

    azure_throughput = [
        r[
            "azure_effective_throughput_rps"
        ]
        for r
        in group
    ]

    tb_throughput = [
        r[
            "thingsboard_effective_throughput_rps"
        ]
        for r
        in group
    ]

    summary_rows.append(
        {
            "backlog":
                backlog,

            "n":
                len(group),

            "success_count":
                sum(
                    r["result"]
                    == "PASS"
                    for r
                    in group
                ),

            "azure_first_mean_s":
                mean(
                    azure_first
                ),

            "azure_first_sd_s":
                sample_sd(
                    azure_first
                ),

            "azure_first_cv_percent":
                cv_percent(
                    azure_first
                ),

            "thingsboard_first_mean_s":
                mean(
                    tb_first
                ),

            "thingsboard_first_sd_s":
                sample_sd(
                    tb_first
                ),

            "thingsboard_first_cv_percent":
                cv_percent(
                    tb_first
                ),

            "azure_recovery_mean_s":
                mean(
                    azure_recovery
                ),

            "azure_recovery_sd_s":
                sample_sd(
                    azure_recovery
                ),

            "azure_recovery_cv_percent":
                cv_percent(
                    azure_recovery
                ),

            "thingsboard_recovery_mean_s":
                mean(
                    tb_recovery
                ),

            "thingsboard_recovery_sd_s":
                sample_sd(
                    tb_recovery
                ),

            "thingsboard_recovery_cv_percent":
                cv_percent(
                    tb_recovery
                ),

            "azure_throughput_mean_rps":
                mean(
                    azure_throughput
                ),

            "azure_throughput_sd_rps":
                sample_sd(
                    azure_throughput
                ),

            "azure_throughput_cv_percent":
                cv_percent(
                    azure_throughput
                ),

            "thingsboard_throughput_mean_rps":
                mean(
                    tb_throughput
                ),

            "thingsboard_throughput_sd_rps":
                sample_sd(
                    tb_throughput
                ),

            "thingsboard_throughput_cv_percent":
                cv_percent(
                    tb_throughput
                ),
        }
    )


# ============================================================
# Save E4_SUMMARY.csv
# ============================================================

summary_fields = list(
    summary_rows[0].keys()
)

with SUMMARY_PATH.open(
        "w",
        encoding="utf-8",
        newline="",
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=summary_fields,
    )

    writer.writeheader()

    writer.writerows(
        summary_rows
    )


# ============================================================
# Scaling regression
#
# Use workload-level means rather than treating all nine
# observations as independent workload values.
# ============================================================

x = [
    row["backlog"]
    for row
    in summary_rows
]

azure_recovery_means = [
    row[
        "azure_recovery_mean_s"
    ]
    for row
    in summary_rows
]

tb_recovery_means = [
    row[
        "thingsboard_recovery_mean_s"
    ]
    for row
    in summary_rows
]

azure_tp_means = [
    row[
        "azure_throughput_mean_rps"
    ]
    for row
    in summary_rows
]

tb_tp_means = [
    row[
        "thingsboard_throughput_mean_rps"
    ]
    for row
    in summary_rows
]


azure_recovery_model = (
    linear_regression(
        x,
        azure_recovery_means,
    )
)

tb_recovery_model = (
    linear_regression(
        x,
        tb_recovery_means,
    )
)

azure_tp_model = (
    linear_regression(
        x,
        azure_tp_means,
    )
)

tb_tp_model = (
    linear_regression(
        x,
        tb_tp_means,
    )
)


# ============================================================
# Cross-platform consistency
# ============================================================

azure_first_earlier = sum(
    run[
        "azure_first_progress_s"
    ]
    <
    run[
        "thingsboard_first_progress_s"
    ]
    for run
    in runs
)

tb_recovery_faster = sum(
    run[
        "thingsboard_recovery_s"
    ]
    <
    run[
        "azure_recovery_s"
    ]
    for run
    in runs
)

tb_throughput_higher = sum(
    run[
        "thingsboard_effective_throughput_rps"
    ]
    >
    run[
        "azure_effective_throughput_rps"
    ]
    for run
    in runs
)


# ============================================================
# Plot 1: Recovery Time vs Backlog
# ============================================================

azure_recovery_sd = [
    row[
        "azure_recovery_sd_s"
    ]
    for row
    in summary_rows
]

tb_recovery_sd = [
    row[
        "thingsboard_recovery_sd_s"
    ]
    for row
    in summary_rows
]


plt.figure(
    figsize=(8, 5)
)

plt.errorbar(
    x,
    azure_recovery_means,
    yerr=azure_recovery_sd,
    marker="o",
    capsize=5,
    label="Azure IoT Hub",
)

plt.errorbar(
    x,
    tb_recovery_means,
    yerr=tb_recovery_sd,
    marker="o",
    capsize=5,
    label="ThingsBoard",
)

plt.xlabel(
    "Historical Backlog Size (records)"
)

plt.ylabel(
    "Full Recovery Time (s)"
)

plt.title(
    "E4: Historical Backlog Size vs Recovery Time"
)

plt.xticks(
    BACKLOG_LEVELS
)

plt.legend()

plt.tight_layout()

plt.savefig(
    RECOVERY_PLOT_PATH,
    dpi=300,
)

plt.close()


# ============================================================
# Plot 2: Throughput vs Backlog
# ============================================================

azure_tp_sd = [
    row[
        "azure_throughput_sd_rps"
    ]
    for row
    in summary_rows
]

tb_tp_sd = [
    row[
        "thingsboard_throughput_sd_rps"
    ]
    for row
    in summary_rows
]


plt.figure(
    figsize=(8, 5)
)

plt.errorbar(
    x,
    azure_tp_means,
    yerr=azure_tp_sd,
    marker="o",
    capsize=5,
    label="Azure IoT Hub",
)

plt.errorbar(
    x,
    tb_tp_means,
    yerr=tb_tp_sd,
    marker="o",
    capsize=5,
    label="ThingsBoard",
)

plt.xlabel(
    "Historical Backlog Size (records)"
)

plt.ylabel(
    "Effective Historical Backfill Throughput "
    "(records/s)"
)

plt.title(
    "E4: Backlog Size vs Effective Backfill Throughput"
)

plt.xticks(
    BACKLOG_LEVELS
)

plt.legend()

plt.tight_layout()

plt.savefig(
    THROUGHPUT_PLOT_PATH,
    dpi=300,
)

plt.close()


# ============================================================
# Markdown report
# ============================================================

lines = []

lines.append(
    "# E4 Final Analysis"
)

lines.append("")

lines.append(
    "## Offline Backlog Scalability of "
    "Dual-Cloud Recovery"
)

lines.append("")

lines.append(
    "E4 evaluated the effect of historical offline "
    "telemetry backlog size on recovery behaviour "
    "after real network restoration."
)

lines.append("")

lines.append(
    "Three backlog levels were evaluated: "
    "**10, 30, and 60 records**, with three formal "
    "independent sessions per workload level."
)

lines.append("")

lines.append(
    "A total of **9 formal trials** were therefore "
    "included in the analysis."
)

lines.append("")


lines.append(
    "## 1. Workload-Level Results"
)

lines.append("")

lines.append(
    "| Backlog | Azure Recovery (s) | "
    "ThingsBoard Recovery (s) | "
    "Azure Throughput (records/s) | "
    "ThingsBoard Throughput (records/s) |"
)

lines.append(
    "|---:|---:|---:|---:|---:|"
)

for row in summary_rows:

    lines.append(
        f"| {row['backlog']} "
        f"| {row['azure_recovery_mean_s']:.3f} "
        f"± {row['azure_recovery_sd_s']:.3f} "
        f"| {row['thingsboard_recovery_mean_s']:.3f} "
        f"± {row['thingsboard_recovery_sd_s']:.3f} "
        f"| {row['azure_throughput_mean_rps']:.4f} "
        f"± {row['azure_throughput_sd_rps']:.4f} "
        f"| {row['thingsboard_throughput_mean_rps']:.4f} "
        f"± {row['thingsboard_throughput_sd_rps']:.4f} |"
    )

lines.append("")


lines.append(
    "## 2. Recovery-Time Variability"
)

lines.append("")

for row in summary_rows:

    lines.append(
        f"- Backlog {row['backlog']}: "
        f"Azure recovery CV = "
        f"**{row['azure_recovery_cv_percent']:.2f}%**, "
        f"ThingsBoard recovery CV = "
        f"**{row['thingsboard_recovery_cv_percent']:.2f}%**."
    )

lines.append("")


lines.append(
    "## 3. Reliability"
)

lines.append("")

lines.append(
    "- Formal E4 trials completed: **9**"
)

lines.append(
    "- Successful historical-backlog recoveries: "
    "**9/9**"
)

lines.append(
    "- Observed recovery success rate: **100%**"
)

lines.append("")


lines.append(
    "## 4. Scaling Behaviour"
)

lines.append("")

lines.append(
    "Mean historical-backlog recovery time increased "
    "as workload size increased from 10 to 30 and "
    "then 60 records."
)

lines.append("")

lines.append(
    "However, recovery time increased substantially "
    "less than proportionally to the six-fold growth "
    "in backlog size from 10 to 60 records."
)

lines.append("")

lines.append(
    "At the same time, effective historical backfill "
    "throughput increased with backlog size. "
    "This behaviour is consistent with the presence "
    "of fixed network-reconnection and synchronization "
    "overheads that are amortized across larger "
    "historical workloads."
)

lines.append("")


lines.append(
    "## 5. Descriptive Linear Models"
)

lines.append("")

lines.append(
    "The following models are descriptive workload-level "
    "fits and should not be interpreted as proof of "
    "general linear scalability."
)

lines.append("")

lines.append(
    "### Azure Recovery"
)

lines.append("")

lines.append(
    f"T(N) = "
    f"{azure_recovery_model['intercept']:.4f} "
    f"+ "
    f"{azure_recovery_model['slope']:.4f} N"
)

lines.append("")

lines.append(
    f"R² = "
    f"{azure_recovery_model['r_squared']:.4f}"
)

lines.append("")


lines.append(
    "### ThingsBoard Recovery"
)

lines.append("")

lines.append(
    f"T(N) = "
    f"{tb_recovery_model['intercept']:.4f} "
    f"+ "
    f"{tb_recovery_model['slope']:.4f} N"
)

lines.append("")

lines.append(
    f"R² = "
    f"{tb_recovery_model['r_squared']:.4f}"
)

lines.append("")


lines.append(
    "## 6. Cross-Platform Pattern"
)

lines.append("")

lines.append(
    f"- Azure showed earlier first recovery progress "
    f"in **{azure_first_earlier}/9** formal trials."
)

lines.append(
    f"- ThingsBoard completed full historical recovery "
    f"faster in **{tb_recovery_faster}/9** formal trials."
)

lines.append(
    f"- ThingsBoard achieved higher effective "
    f"backfill throughput in "
    f"**{tb_throughput_higher}/9** formal trials."
)

lines.append("")


lines.append(
    "## 7. Interpretation"
)

lines.append("")

lines.append(
    "The E4 results provide evidence that the proposed "
    "SQLite-based store-and-forward architecture can "
    "recover historical telemetry across the tested "
    "10-, 30-, and 60-record workload levels while "
    "the edge application continues operating."
)

lines.append("")

lines.append(
    "The observed increase in recovery time with workload "
    "size indicates a measurable backlog-dependent cost. "
    "However, effective throughput also increased as "
    "the backlog became larger, suggesting that fixed "
    "reconnection and synchronization overhead represents "
    "a substantial fraction of total recovery time for "
    "small workloads."
)

lines.append("")

lines.append(
    "Across the tested prototype configuration, Azure "
    "generally initiated historical recovery slightly "
    "earlier, whereas ThingsBoard completed the frozen "
    "historical backlog sooner and achieved higher "
    "effective backfill throughput."
)

lines.append("")


lines.append(
    "## 8. Limitations"
)

lines.append("")

lines.append(
    "Only three backlog levels were evaluated, and each "
    "level contained three formal repetitions."
)

lines.append("")

lines.append(
    "The experiment therefore characterizes recovery "
    "behaviour only within the tested prototype and "
    "workload range. It does not establish general "
    "performance characteristics of Azure IoT Hub or "
    "ThingsBoard."
)

lines.append("")

lines.append(
    "The reported throughput is a system-level effective "
    "backfill metric and includes network reconnection, "
    "cloud communication, local worker scheduling, and "
    "SQLite state-update overhead."
)

lines.append("")


lines.append(
    "## 9. E4 Conclusion"
)

lines.append("")

lines.append(
    "**E4 RESULT: PASS**"
)

lines.append("")

lines.append(
    "All nine formal trials successfully recovered the "
    "complete frozen historical backlog after network "
    "restoration."
)

lines.append("")

lines.append(
    "Recovery time increased with backlog size over the "
    "tested range, while effective historical backfill "
    "throughput also increased, indicating that fixed "
    "recovery overhead is progressively amortized across "
    "larger queued workloads."
)


ANALYSIS_PATH.write_text(
    "\n".join(lines) + "\n",
    encoding="utf-8",
    )


# ============================================================
# Console output
# ============================================================

print("=" * 76)

print(
    "E4 FINAL ANALYSIS"
)

print("=" * 76)

print()

for row in summary_rows:

    print(
        f"Backlog = {row['backlog']}"
    )

    print(
        f"  Azure recovery : "
        f"{row['azure_recovery_mean_s']:.3f} "
        f"± {row['azure_recovery_sd_s']:.3f} s"
    )

    print(
        f"  TB recovery    : "
        f"{row['thingsboard_recovery_mean_s']:.3f} "
        f"± {row['thingsboard_recovery_sd_s']:.3f} s"
    )

    print(
        f"  Azure throughput: "
        f"{row['azure_throughput_mean_rps']:.4f} "
        f"± {row['azure_throughput_sd_rps']:.4f} records/s"
    )

    print(
        f"  TB throughput   : "
        f"{row['thingsboard_throughput_mean_rps']:.4f} "
        f"± {row['thingsboard_throughput_sd_rps']:.4f} records/s"
    )

    print()


print("-" * 76)

print(
    "DESCRIPTIVE RECOVERY MODELS"
)

print("-" * 76)

print(
    "Azure:"
)

print(
    f"T(N) = "
    f"{azure_recovery_model['intercept']:.4f} "
    f"+ "
    f"{azure_recovery_model['slope']:.4f}N"
)

print(
    f"R² = "
    f"{azure_recovery_model['r_squared']:.4f}"
)

print()

print(
    "ThingsBoard:"
)

print(
    f"T(N) = "
    f"{tb_recovery_model['intercept']:.4f} "
    f"+ "
    f"{tb_recovery_model['slope']:.4f}N"
)

print(
    f"R² = "
    f"{tb_recovery_model['r_squared']:.4f}"
)

print()

print("-" * 76)

print(
    "CROSS-PLATFORM CONSISTENCY"
)

print("-" * 76)

print(
    f"Azure first progress earlier : "
    f"{azure_first_earlier}/9"
)

print(
    f"TB full recovery faster      : "
    f"{tb_recovery_faster}/9"
)

print(
    f"TB throughput higher         : "
    f"{tb_throughput_higher}/9"
)

print()

print(
    "Formal E4 trials PASS        : "
    "9/9"
)

print(
    "Observed success rate        : "
    "100.0%"
)

print()

print("=" * 76)

print(
    f"ALL RUNS:\n{ALL_RUNS_PATH}"
)

print()

print(
    f"SUMMARY:\n{SUMMARY_PATH}"
)

print()

print(
    f"ANALYSIS:\n{ANALYSIS_PATH}"
)

print()

print(
    f"RECOVERY PLOT:\n"
    f"{RECOVERY_PLOT_PATH}"
)

print()

print(
    f"THROUGHPUT PLOT:\n"
    f"{THROUGHPUT_PLOT_PATH}"
)

print("=" * 76)