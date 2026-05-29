"""EWMA-based ATR walk-forward evaluation.

Python port of ATR.cs. For each window, search a small grid of EWMA
smoothing factors (lambdas) on the training true-range series, pick the
lambda with the lowest training MSE (skipping the warm-up region of
3 * half-life observations), then evaluate the resulting ATR on the
validation set.
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from data_loading import Window
from data_utils import df_with_true_range
from data_utils import squared_error

LAMBDAS: Tuple[float, ...] = (0.77, 0.78, 0.79, 0.8, 0.81, 0.82, 0.83)

def process(df: pd.DataFrame, windows: List[Window]) -> Tuple[Dict[int, Tuple[float, float, Dict[float, float]]], float]: # (val year -> (best lambda, val mse, (lambda -> train mse)), 2026 mse)
    """For each window, return (best_lambda, validation_MSE, train_mse_by_lambda)
    keyed by validation year.

    The ATR is warmed up using every TrueRange in `df` that falls strictly
    before the window's training years. Once warmed, MSE is computed on
    every training point (no warmup skip).

    `df` must be the full dataframe from data_loading.load() so that
    previous-day settlements line up across year boundaries.
    """
    df = df_with_true_range(df)

    result: Dict[int, Tuple[float, float, Dict[float, float]]] = {}
    for window in windows:
        first_train_year = min(window.train_years)
        warmup_tr = df.loc[df["Year"] == first_train_year - 1, "TrueRange"].dropna().to_numpy()
        train_tr = df.loc[df["Year"].isin(window.train_years), "TrueRange"].dropna().to_numpy()
        val_tr = df.loc[df["Year"] == window.validation_year, "TrueRange"].dropna().to_numpy()

        train_mse_by_lambda = get_train_mse_by_lambda(warmup_tr, train_tr)
        best_lambda = min(train_mse_by_lambda, key=train_mse_by_lambda.get)
        atr = calc_atr_for_list(train_tr, best_lambda)
        val_mse = get_validation_mse(val_tr, best_lambda, atr)

        result[window.validation_year] = (best_lambda, val_mse, train_mse_by_lambda)

    return result, get_test_mse(df, result[2025][0])

def get_test_mse(df: pd.DataFrame, lam: float) -> float:
    warmup_tr = df.loc[df["Year"] == 2025, "TrueRange"].dropna().to_numpy()
    test_tr = df.loc[df["Year"] == 2026, "TrueRange"].dropna().to_numpy()

    atr = calc_atr_for_list(warmup_tr, lam)
    return get_validation_mse(test_tr, lam, atr)
    

def get_train_mse_by_lambda(warmup: np.ndarray, train: np.ndarray) -> Dict[float, float]:
    """Warm the ATR on `warmup`, then return the training MSE for each lambda."""
    mse_by_lambda: Dict[float, float] = {}

    for lam in LAMBDAS:
        atr = 0.0
        for tr in warmup:
            atr = calc_ewma_atr(atr, tr, lam)

        squared_errors: List[float] = []
        for tr in train:
            squared_errors.append(squared_error(atr, tr))
            atr = calc_ewma_atr(atr, tr, lam)

        mse_by_lambda[lam] = float(np.mean(squared_errors))

    return mse_by_lambda

def get_validation_mse(validation: np.ndarray, lam: float, atr: float) -> float:
    """Run the trained ATR forward through validation and return the MSE."""
    squared_errors: List[float] = []
    for tr in validation:
        squared_errors.append(squared_error(atr, tr))
        atr = calc_ewma_atr(atr, tr, lam)
    return float(np.mean(squared_errors))


def calc_atr_for_list(train: np.ndarray, lam: float) -> float:
    """Roll the EWMA through warmup then training and return the final ATR."""
    atr = 0.0
    for tr in train:
        atr = calc_ewma_atr(atr, tr, lam)
    return atr

def calc_ewma_atr(atr: float, true_range: float, lam: float) -> float:
    return (1.0 - lam) * true_range + lam * atr


def half_life(lam: float) -> float:
    return math.log(2.0) / -math.log(lam)


'''
Non-ewma ATR
'''

# Candidate lookback windows (in trading days) for plain (SMA) ATR.
PLAIN_ATR_NS: Tuple[int, ...] = (5, 10, 14, 20, 30, 50)


def process_plain_atr(
    df: pd.DataFrame, windows: List[Window]
) -> Tuple[Dict[int, Tuple[int, float, Dict[int, float]]], float]:
    """Plain (SMA-of-TrueRange) ATR with the same walk-forward structure
    as the EWMA process: for each window pick the N with the lowest
    training MSE, then report the validation MSE for that N. Returns
    (val_year -> (best_n, val_mse, train_mse_by_n)) plus the 2026 test
    MSE computed with the N chosen when 2025 was validation.

    Each day's prediction is the SMA of the previous N TrueRanges
    (`.rolling(N).mean().shift(1)`), so no current-day leakage.
    """
    df = df_with_true_range(df)

    # Precompute one (squared error vs predicted SMA) series per candidate N.
    sq_errs_by_n: Dict[int, pd.Series] = {}
    for n in PLAIN_ATR_NS:
        sma_pred = df["TrueRange"].rolling(n).mean().shift(1)
        sq_errs_by_n[n] = (sma_pred - df["TrueRange"]) ** 2

    result: Dict[int, Tuple[int, float, Dict[int, float]]] = {}
    for window in windows:
        train_mask = df["Year"].isin(window.train_years)
        val_mask = df["Year"] == window.validation_year

        train_mse_by_n: Dict[int, float] = {
            n: float(sq_errs_by_n[n][train_mask].dropna().mean())
            for n in PLAIN_ATR_NS
        }
        best_n = min(train_mse_by_n, key=train_mse_by_n.get)
        val_mse = float(sq_errs_by_n[best_n][val_mask].dropna().mean())

        result[window.validation_year] = (best_n, val_mse, train_mse_by_n)

    best_n_2025 = result[2025][0]
    test_mse = float(
        sq_errs_by_n[best_n_2025][df["Year"] == 2026].dropna().mean()
    )

    return result, test_mse
