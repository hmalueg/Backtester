"""Load corn historical data and produce walk-forward train/validation windows.

Mirrors the C# DataProcessing.Split: each window has TRAIN_YEARS calendar years
of training data followed by the next calendar year as validation, sliding
forward one year at a time for WINDOW_COUNT windows.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

import pandas as pd


DATA_DIR = Path(__file__).resolve().parent.parent / "data"

TRAIN_YEARS = 2
WINDOW_COUNT = 8


@dataclass
class Window:
    train: pd.DataFrame
    validation: pd.DataFrame
    train_years: List[int]
    validation_year: int


def load(market: str) -> pd.DataFrame:
    """Read `{market}_historical_data.csv` from the data dir, parse TradeDate, and sort."""
    path = DATA_DIR / f"{market}_historical_data.csv"
    df = pd.read_csv(path, parse_dates=["TradeDate"])
    df = df.sort_values("TradeDate").reset_index(drop=True)
    df["Year"] = df["TradeDate"].dt.year
    return df


def split(df: pd.DataFrame, train_years: int = TRAIN_YEARS,
          window_count: int = WINDOW_COUNT) -> List[Window]:
    """Walk-forward split into `window_count` windows.

    The earliest calendar year in the dataframe is excluded from both
    training and validation (it remains in the dataframe so callers can
    still reference it, e.g. for prior-day settlements).
    """
    all_years = sorted(df["Year"].unique())
    years = all_years[1:]  # drop the first year from train/validation
    needed = train_years + window_count
    if len(years) < needed:
        raise ValueError(
            f"Need {needed} distinct calendar years for {window_count} windows "
            f"with {train_years}yr train; got {len(years)}."
        )

    windows: List[Window] = []
    for i in range(window_count):
        train_yrs = years[i:i + train_years]
        val_yr = years[i + train_years]

        train_df = df[df["Year"].isin(train_yrs)].reset_index(drop=True)
        val_df = df[df["Year"] == val_yr].reset_index(drop=True)

        windows.append(Window(
            train=train_df,
            validation=val_df,
            train_years=train_yrs,
            validation_year=val_yr,
        ))

    return windows
