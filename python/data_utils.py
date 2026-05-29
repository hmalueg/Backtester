import pandas as pd

# Tukey IQR multiplier for TrueRange outlier removal. 1.5 = mild, 3.0 = extreme.
OUTLIER_IQR_MULT: float = 5.0

#close_or_settle = "Settlement"
close_or_settle = "Close"

def df_with_true_range(df: pd.DataFrame) -> pd.DataFrame:
    """Add a TrueRange column = max(High, prev_settle) - min(Low, prev_settle).

    The first row has no prior settlement; its TrueRange is NaN and is
    naturally excluded once split() drops the first calendar year from
    train/validation.
    """
    df = df.copy()
    prev_settle = df[close_or_settle].shift(1)
    df["Previous" + close_or_settle] = prev_settle
    # skipna=False so a missing previous settlement yields NaN rather than
    # silently falling back to just High/Low.
    df["TrueRange"] = (
        pd.concat([df["High"], prev_settle], axis=1).max(axis=1, skipna=False)
        - pd.concat([df["Low"], prev_settle], axis=1).min(axis=1, skipna=False)
    )

    # Discard TrueRange outliers via Tukey IQR: anything outside
    # [Q1 - k*IQR, Q3 + k*IQR] is set to NaN so it gets dropped by the
    # downstream .dropna() in process(). Bounds are computed on the full
    # series so warmup/train/validation see a consistent filter.
    tr = df["TrueRange"]
    q1 = tr.quantile(0.25)
    q3 = tr.quantile(0.75)
    iqr = q3 - q1
    upper = q3 + OUTLIER_IQR_MULT * iqr
    outlier_mask = tr.notna() & (tr > upper)

    df["TrueRange"] = tr.where(~outlier_mask)

    return df

def squared_error(atr: float, true_range: float) -> float:
    diff = atr - true_range
    return diff * diff
