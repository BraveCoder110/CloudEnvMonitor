"""
E1 Final Analysis
=================

Combines all formal baseline and optimized latency sessions.

Outputs:
- combined formal dataset
- overall statistics
- session statistics
- comparison summary

Pilot data are intentionally excluded.

python -m experiments.formal.analyze_e1
"""

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path.home() / "azure-iot-environment"

INPUT_DIR = (
        PROJECT_ROOT
        / "experiments"
        / "results"
        / "formal"
)

OUTPUT_DIR = (
        PROJECT_ROOT
        / "experiments"
        / "results"
        / "e1"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


def load_condition(
        condition: str,
) -> pd.DataFrame:

    frames = []

    for session in (1, 2, 3):

        path = (
                INPUT_DIR
                / f"{condition}_session_{session}.csv"
        )

        if not path.exists():
            raise FileNotFoundError(path)

        frame = pd.read_csv(path)

        frames.append(frame)

    return pd.concat(
        frames,
        ignore_index=True,
    )


def calculate_statistics(
        values: pd.Series,
) -> dict:

    values = values.astype(float)

    n = len(values)

    mean = values.mean()
    sd = values.std(ddof=1)

    sem = sd / np.sqrt(n)

    # t≈1.987 for df=89.
    # For this engineering summary we use 1.987.
    ci_margin = 1.987 * sem

    return {
        "n": n,
        "mean_ms": mean,
        "median_ms": values.median(),
        "sd_ms": sd,
        "min_ms": values.min(),
        "max_ms": values.max(),
        "p95_ms": np.percentile(
            values,
            95,
        ),
        "cv_percent": (
                sd / mean * 100
        ),
        "ci95_lower_ms": (
                mean - ci_margin
        ),
        "ci95_upper_ms": (
                mean + ci_margin
        ),
    }


def main() -> None:

    baseline = load_condition(
        "baseline"
    )

    optimized = load_condition(
        "optimized"
    )

    combined = pd.concat(
        [
            baseline,
            optimized,
        ],
        ignore_index=True,
    )

    combined.to_csv(
        OUTPUT_DIR
        / "edge_latency_formal_all.csv",
        index=False,
        )

    # ------------------------------------------------------
    # Overall statistics
    # ------------------------------------------------------

    rows = []

    for (
            condition,
            dataframe,
    ) in (
            ("baseline", baseline),
            ("optimized", optimized),
    ):

        stats = calculate_statistics(
            dataframe[
                "total_control_latency_ms"
            ]
        )

        stats["condition"] = condition

        success_series = (
            dataframe["success"]
            .astype(str)
            .str.lower()
        )

        success_count = (
                success_series
                == "true"
        ).sum()

        stats[
            "software_success_count"
        ] = int(success_count)

        stats[
            "software_success_rate_percent"
        ] = (
                success_count
                / len(dataframe)
                * 100
        )

        rows.append(stats)

    overall = pd.DataFrame(rows)

    columns = [
        "condition",
        "n",
        "mean_ms",
        "median_ms",
        "sd_ms",
        "min_ms",
        "max_ms",
        "p95_ms",
        "cv_percent",
        "ci95_lower_ms",
        "ci95_upper_ms",
        "software_success_count",
        "software_success_rate_percent",
    ]

    overall = overall[columns]

    overall.to_csv(
        OUTPUT_DIR
        / "overall_statistics.csv",
        index=False,
        )

    # ------------------------------------------------------
    # Session statistics
    # ------------------------------------------------------

    session_rows = []

    for condition in (
            "baseline",
            "optimized",
    ):

        subset = combined[
            combined["condition"]
            == condition
            ]

        for session in (1, 2, 3):

            session_df = subset[
                subset["session"]
                == session
                ]

            stats = calculate_statistics(
                session_df[
                    "total_control_latency_ms"
                ]
            )

            stats[
                "condition"
            ] = condition

            stats[
                "session"
            ] = session

            session_rows.append(
                stats
            )

    session_statistics = pd.DataFrame(
        session_rows
    )

    session_statistics.to_csv(
        OUTPUT_DIR
        / "session_statistics.csv",
        index=False,
        )

    # ------------------------------------------------------
    # Overall improvement
    # ------------------------------------------------------

    baseline_mean = baseline[
        "total_control_latency_ms"
    ].mean()

    optimized_mean = optimized[
        "total_control_latency_ms"
    ].mean()

    absolute_reduction = (
            baseline_mean
            - optimized_mean
    )

    relative_reduction = (
            absolute_reduction
            / baseline_mean
            * 100
    )

    baseline_p95 = np.percentile(
        baseline[
            "total_control_latency_ms"
        ],
        95,
    )

    optimized_p95 = np.percentile(
        optimized[
            "total_control_latency_ms"
        ],
        95,
    )

    comparison = pd.DataFrame(
        [
            {
                "baseline_mean_ms":
                    baseline_mean,

                "optimized_mean_ms":
                    optimized_mean,

                "absolute_reduction_ms":
                    absolute_reduction,

                "relative_reduction_percent":
                    relative_reduction,

                "baseline_p95_ms":
                    baseline_p95,

                "optimized_p95_ms":
                    optimized_p95,
            }
        ]
    )

    comparison.to_csv(
        OUTPUT_DIR
        / "comparison_summary.csv",
        index=False,
        )

    # ------------------------------------------------------
    # Console summary
    # ------------------------------------------------------

    print("=" * 72)
    print("E1 FINAL ANALYSIS")
    print("=" * 72)

    print(
        f"Baseline N           : "
        f"{len(baseline)}"
    )

    print(
        f"Optimized N          : "
        f"{len(optimized)}"
    )

    print()

    print(
        f"Baseline mean        : "
        f"{baseline_mean:.3f} ms"
    )

    print(
        f"Optimized mean       : "
        f"{optimized_mean:.3f} ms"
    )

    print(
        f"Absolute reduction   : "
        f"{absolute_reduction:.3f} ms"
    )

    print(
        f"Relative reduction   : "
        f"{relative_reduction:.2f} %"
    )

    print()

    print(
        f"Baseline P95         : "
        f"{baseline_p95:.3f} ms"
    )

    print(
        f"Optimized P95        : "
        f"{optimized_p95:.3f} ms"
    )

    print()

    print(
        f"Results saved to:\n"
        f"{OUTPUT_DIR}"
    )


if __name__ == "__main__":
    main()