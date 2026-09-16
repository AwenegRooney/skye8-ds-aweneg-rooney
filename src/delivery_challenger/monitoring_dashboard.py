import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from typing import Any


def parse_logs(log_file: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Parse JSON logs from file.
    Returns (routing_logs, ground_truth_logs).
    """
    routing_logs = []
    ground_truth_logs = []

    try:
        with open(log_file, "r") as f:
            for line in f:
                if "ROUTING_DECISION:" in line:
                    try:
                        json_str = line.split("ROUTING_DECISION: ", 1)[1]
                        routing_logs.append(json.loads(json_str))
                    except (json.JSONDecodeError, IndexError):
                        pass
                elif "GROUND_TRUTH:" in line:
                    try:
                        json_str = line.split("GROUND_TRUTH: ", 1)[1]
                        ground_truth_logs.append(json.loads(json_str))
                    except (json.JSONDecodeError, IndexError):
                        pass
    except FileNotFoundError:
        print(f"Error: Log file '{log_file}' not found.")
        sys.exit(1)

    return routing_logs, ground_truth_logs


def calculate_metrics(
    routing_logs: list[dict[str, Any]],
    ground_truth_logs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Calculate aggregated metrics for monitoring."""
    metrics: dict[str, Any] = {
        "total_predictions": len(routing_logs),
        "total_ground_truths": len(ground_truth_logs),
        "error_by_model": defaultdict(list),
        "latency_ms_by_model": defaultdict(list),
        "traffic_split": defaultdict(int),
        "prediction_distribution": defaultdict(int),
    }

    # Process routing decisions (traffic split, latency)
    for log in routing_logs:
        model = log.get("model_version", "unknown")
        metrics["traffic_split"][model] += 1

        latency = log.get("latency_ms", 0)
        metrics["latency_ms_by_model"][model].append(latency)

        pred = log.get("prediction_minutes", 0)
        bucket = int(pred // 5) * 5  # Bucket by 5-minute intervals
        metrics["prediction_distribution"][f"{bucket}-{bucket+5}"] += 1

    # Process ground truth (error)
    for log in ground_truth_logs:
        model = log.get("model_version", "unknown")
        error = log.get("absolute_error", 0)
        metrics["error_by_model"][model].append(error)

    return metrics


def calculate_percentiles(values: list[float]) -> dict[str, float]:
    """Calculate latency/error percentiles."""
    if not values:
        return {"p50": 0, "p95": 0, "p99": 0, "mean": 0}

    sorted_vals = sorted(values)
    n = len(sorted_vals)

    return {
        "mean": sum(sorted_vals) / n,
        "p50": sorted_vals[int(n * 0.50)] if n > 0 else 0,
        "p95": sorted_vals[int(n * 0.95)] if n > 0 else 0,
        "p99": sorted_vals[int(n * 0.99)] if n > 0 else 0,
        "min": sorted_vals[0],
        "max": sorted_vals[-1],
    }


def format_report(metrics: dict[str, Any]) -> str:
    """Format metrics into a readable text report."""
    report = []
    report.append("=" * 80)
    report.append("DELIVERY CHALLENGER CANARY ROLLOUT MONITORING REPORT")
    report.append("=" * 80)
    report.append(
        f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"  # noqa: DTZ005
    )

    # Summary
    report.append("\n" + "-" * 80)
    report.append("SUMMARY")
    report.append("-" * 80)
    report.append(f"Total Predictions: {metrics['total_predictions']}")
    report.append(f"Ground Truths Recorded: {metrics['total_ground_truths']}")

    # Traffic Split
    report.append("\n" + "-" * 80)
    report.append("TRAFFIC SPLIT")
    report.append("-" * 80)
    total = metrics["total_predictions"]
    for model, count in sorted(metrics["traffic_split"].items()):
        pct = (count / total * 100) if total > 0 else 0
        report.append(f"  {model:<30} {count:>6} requests ({pct:>5.1f}%)")

    # Error by Model Version
    report.append("\n" + "-" * 80)
    report.append("ERROR ANALYSIS (Mean Absolute Error in Minutes)")
    report.append("-" * 80)
    for model in sorted(metrics["error_by_model"].keys()):
        errors = metrics["error_by_model"][model]
        if errors:
            percentiles = calculate_percentiles(errors)
            report.append(f"\n  {model}")
            report.append(f"    Mean:  {percentiles['mean']:.2f} min")
            report.append(f"    Median (p50): {percentiles['p50']:.2f} min")
            report.append(f"    p95:   {percentiles['p95']:.2f} min")
            report.append(f"    p99:   {percentiles['p99']:.2f} min")
            report.append(
                f"    Range: {percentiles['min']:.2f} - {percentiles['max']:.2f} min"
            )
            report.append(f"    Observations: {len(errors)}")

    # Latency by Model Version
    report.append("\n" + "-" * 80)
    report.append("LATENCY ANALYSIS (in milliseconds)")
    report.append("-" * 80)
    for model in sorted(metrics["latency_ms_by_model"].keys()):
        latencies = metrics["latency_ms_by_model"][model]
        if latencies:
            percentiles = calculate_percentiles(latencies)
            report.append(f"\n  {model}")
            report.append(f"    Mean:  {percentiles['mean']:.1f} ms")
            report.append(f"    Median (p50): {percentiles['p50']:.1f} ms")
            report.append(f"    p95:   {percentiles['p95']:.1f} ms")
            report.append(f"    p99:   {percentiles['p99']:.1f} ms")
            report.append(f"    Max:   {percentiles['max']:.1f} ms")

    # Prediction Distribution
    report.append("\n" + "-" * 80)
    report.append("PREDICTION DISTRIBUTION (Minutes)")
    report.append("-" * 80)
    for bucket in sorted(metrics["prediction_distribution"].keys()):
        count = metrics["prediction_distribution"][bucket]
        pct = (count / total * 100) if total > 0 else 0
        report.append(f"  {bucket:<10} {count:>6} predictions ({pct:>5.1f}%)")

    # Rollback Criteria Check
    report.append("\n" + "-" * 80)
    report.append("AUTOMATIC ROLLBACK CRITERIA CHECK")
    report.append("-" * 80)
    challenger_errors = metrics["error_by_model"].get("challenger_lgbm_v1", [])
    if len(challenger_errors) >= 100:
        recent_100_mae = sum(challenger_errors[-100:]) / 100
        threshold = 9.5
        status = "? ROLLBACK TRIGGERED" if recent_100_mae >= threshold else "? PASS"
        report.append(f"  Status: {status}")
        report.append(f"  Challenger MAE (last 100): {recent_100_mae:.2f} min")
        report.append(f"  Threshold: {threshold:.2f} min")
        report.append(f"  Observations: {len(challenger_errors[-100:])}")
    else:
        report.append("  Status: ? INSUFFICIENT DATA")
        report.append(f"  Observations: {len(challenger_errors)}/100 required")

    report.append("\n" + "=" * 80)
    return "\n".join(report)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse and aggregate delivery prediction logs for monitoring."
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default="predictions.log",
        help="Path to log file (default: predictions.log)",
    )
    parser.add_argument(
        "--output",
        type=str,
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    args = parser.parse_args()

    print(f"Reading logs from: {args.log_file}")
    routing_logs, ground_truth_logs = parse_logs(args.log_file)
    print(
        f"Parsed {len(routing_logs)} routing decisions, {len(ground_truth_logs)} ground truths"
    )

    metrics = calculate_metrics(routing_logs, ground_truth_logs)

    if args.output == "json":
        # Convert defaultdicts to regular dicts for JSON serialization
        metrics_json = {
            "total_predictions": metrics["total_predictions"],
            "total_ground_truths": metrics["total_ground_truths"],
            "traffic_split": dict(metrics["traffic_split"]),
            "prediction_distribution": dict(metrics["prediction_distribution"]),
            "error_by_model": {
                model: calculate_percentiles(errors)
                for model, errors in metrics["error_by_model"].items()
            },
            "latency_by_model": {
                model: calculate_percentiles(latencies)
                for model, latencies in metrics["latency_ms_by_model"].items()
            },
        }
        print(json.dumps(metrics_json, indent=2))
    else:
        print(format_report(metrics))


if __name__ == "__main__":
    main()
