from typing import Any

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.power import TTestPower


def evaluate_paired_difference(
    abs_error_incumbent: pd.Series, abs_error_challenger: pd.Series, alpha: float = 0.05
) -> dict[str, Any]:
    diff = abs_error_incumbent - abs_error_challenger
    n = len(diff)

    mean_imp = diff.mean()

    if n <= 1:
        return {
            "mean_improvement_minutes": float(mean_imp) if n == 1 else np.nan,
            "ci_lower": np.nan,
            "ci_upper": np.nan,
            "p_value": np.nan,
            "std_dev_diff": np.nan,
            "sample_size": int(n),
        }

    std_dev = diff.std(ddof=1)

    if std_dev == 0 or np.isnan(std_dev):
        return {
            "mean_improvement_minutes": float(mean_imp),
            "ci_lower": np.nan,
            "ci_upper": np.nan,
            "p_value": np.nan,
            "std_dev_diff": 0.0,
            "sample_size": int(n),
        }

    se = std_dev / np.sqrt(n)
    _, p_val = stats.ttest_rel(abs_error_incumbent, abs_error_challenger)

    ci_lower, ci_upper = stats.t.interval(
        confidence=1 - alpha, df=n - 1, loc=mean_imp, scale=se
    )

    return {
        "mean_improvement_minutes": float(mean_imp),
        "ci_lower": float(ci_lower),
        "ci_upper": float(ci_upper),
        "p_value": float(p_val),
        "std_dev_diff": float(std_dev),
        "sample_size": int(n),
    }


def apply_benjamini_hochberg(
    p_values: list[float], alpha: float = 0.05
) -> tuple[np.ndarray, np.ndarray]:
    p_vals_arr = np.array(p_values, dtype=float)
    valid_mask = ~np.isnan(p_vals_arr)

    reject = np.zeros(len(p_vals_arr), dtype=bool)
    pvals_corrected = np.full(len(p_vals_arr), np.nan)

    if np.any(valid_mask):
        rej_valid, p_corr_valid, _, _ = multipletests(
            p_vals_arr[valid_mask], alpha=alpha, method="fdr_bh"
        )
        reject[valid_mask] = rej_valid
        pvals_corrected[valid_mask] = p_corr_valid

    return reject, pvals_corrected


def calculate_required_sample_size(
    std_dev_diff: float,
    target_diff: float = 1.0,
    alpha: float = 0.05,
    power: float = 0.80,
) -> float:
    if np.isnan(std_dev_diff) or std_dev_diff == 0:
        return np.nan

    effect_size = target_diff / std_dev_diff
    analysis = TTestPower()

    try:
        required_n = analysis.solve_power(
            effect_size=effect_size, power=power, alpha=alpha, alternative="two-sided"
        )
        return float(np.ceil(required_n))
    except Exception:  # noqa: BLE001
        return np.nan


def run_segment_statistical_analysis(
    holdout_df: pd.DataFrame,
    challenger_preds: pd.Series,
    incumbent_col: str = "predicted_minutes_v1",
    actual_col: str = "actual_minutes",
    alpha: float = 0.05,
    operational_threshold: float = 1.0,
) -> pd.DataFrame:
    df = holdout_df.copy()
    df["abs_err_incumbent"] = (df[actual_col] - df[incumbent_col]).abs()
    df["abs_err_challenger"] = (df[actual_col] - challenger_preds).abs()

    segment_cols = [
        "distance_bucket",
        "hour_of_day",
        "package_type",
        "raining",
        "pickup_zone",
    ]
    results = []

    for col in segment_cols:
        for group_val, group_data in df.groupby(col):
            stats_dict = evaluate_paired_difference(
                group_data["abs_err_incumbent"],
                group_data["abs_err_challenger"],
                alpha=alpha,
            )
            stats_dict["dimension"] = col
            stats_dict["segment_value"] = str(group_val)
            results.append(stats_dict)

    results_df = pd.DataFrame(results)

    reject, pvals_corrected = apply_benjamini_hochberg(
        results_df["p_value"].tolist(), alpha=alpha
    )
    results_df["p_value_corrected"] = pvals_corrected
    results_df["is_stat_significant"] = reject

    required_samples = []
    statuses = []

    for _, row in results_df.iterrows():
        is_sig = row["is_stat_significant"]
        mean_imp = row["mean_improvement_minutes"]

        if is_sig:
            required_samples.append(np.nan)
            if mean_imp < 0:
                statuses.append("Regressed (Worse)")
            elif mean_imp >= operational_threshold:
                statuses.append("Operationally Improved")
            else:
                statuses.append("Statistically Sig / Operationally Trivial")
        else:
            statuses.append("Inconclusive (Underpowered)")
            n_req = calculate_required_sample_size(
                row["std_dev_diff"], target_diff=1.0, alpha=alpha
            )
            required_samples.append(n_req)

    results_df["status"] = statuses
    results_df["required_n_for_1min_diff"] = required_samples

    return results_df
