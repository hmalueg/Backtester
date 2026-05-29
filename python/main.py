from data_loading import load, split
import atr


# Add more modules here as they are ported. Each must expose a
# `process(df, windows)` that returns {validation_year: (param, val_mse)}.
PROCESSORS = [atr]


if __name__ == "__main__":
    data = load("corn")
    print(f"Loaded {len(data)} rows spanning "
          f"{data['TradeDate'].min().date()} to {data['TradeDate'].max().date()}")

    windows = split(data)
    '''
    for i, w in enumerate(windows):
        print(f"Window {i}: train years {w.train_years} ({len(w.train)} rows) "
              f"-> validation {w.validation_year} ({len(w.validation)} rows)")
    '''
    for module in PROCESSORS:
        print(f"\n=== {module.__name__} ===")
        result, test_mse = module.process(data, windows)
        for year, (param, mse, train_mse_by_param) in sorted(result.items()):
            train_str = ", ".join(
                f"{p}={m:.4f}" for p, m in sorted(train_mse_by_param.items())
            )
            print(f"{year}: best={param}, val MSE={mse:.4f} | train MSE [{train_str}]")
        print(f"Test MSE (2026, using 2025-best lambda): {test_mse:.4f}")

    print(f"\n=== plain ATR (SMA) ===")
    plain_result, plain_test_mse = atr.process_plain_atr(data, windows)
    for year, (best_n, mse, train_mse_by_n) in sorted(plain_result.items()):
        train_str = ", ".join(
            f"N={n}:{m:.4f}" for n, m in sorted(train_mse_by_n.items())
        )
        print(f"{year}: best N={best_n}, val MSE={mse:.4f} | train MSE [{train_str}]")
    print(f"Test MSE (2026, using 2025-best N): {plain_test_mse:.4f}")
