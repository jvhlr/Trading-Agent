"""
Dataset Builder Module for XAUUSD Trading System.

Prepares datasets for model training with strict chronological splits.
CRITICAL INVARIANTS:
1. No shuffling across time boundaries.
2. StandardScalers fit ONLY on training data.
3. Warmup NaNs and future-target NaNs dropped explicitly.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler


@dataclass
class DatasetSplit:
    """Dataclass holding chronologically split datasets."""

    X_train: np.ndarray
    y_train: np.ndarray
    returns_train: np.ndarray
    timestamps_train: pd.Series

    X_val: np.ndarray
    y_val: np.ndarray
    returns_val: np.ndarray
    timestamps_val: pd.Series

    X_test: np.ndarray
    y_test: np.ndarray
    returns_test: np.ndarray
    timestamps_test: pd.Series

    feature_names: List[str]
    scaler: Optional[StandardScaler]
    raw_df_cleaned: pd.DataFrame


def build_dataset(
    df: pd.DataFrame,
    feature_cols: List[str],
    target_col: str = "target_direction",
    return_col: Optional[str] = "return_1",
    timestamp_col: str = "timestamp",
    train_ratio: float = 0.6,
    val_ratio: float = 0.2,
    test_ratio: float = 0.2,
    scale: bool = True,
) -> DatasetSplit:
    """
    Cleans DataFrame, performs strict chronological train/validation/test split,
    and scales features using a scaler fit exclusively on training data.

    Args:
        df: DataFrame containing features, target, return, and timestamp.
        feature_cols: List of column names to use as input features.
        target_col: Name of target column (e.g. 'target_direction').
        return_col: Name of price return column (for backtest metrics).
        timestamp_col: Name of timestamp column.
        train_ratio: Fraction of dataset for training (default: 0.6).
        val_ratio: Fraction of dataset for validation (default: 0.2).
        test_ratio: Fraction of dataset for testing (default: 0.2).
        scale: Whether to scale features using StandardScaler (default: True).

    Returns:
        DatasetSplit object.
    """
    if abs(train_ratio + val_ratio + test_ratio - 1.0) > 1e-5:
        raise ValueError(
            f"Ratios must sum to 1.0, got {train_ratio}+{val_ratio}+{test_ratio} = {train_ratio+val_ratio+test_ratio}"
        )

    # Required columns check
    missing_cols = [c for c in list(feature_cols) + [target_col] if c not in df.columns]
    if missing_cols:
        raise KeyError(f"Missing required columns in DataFrame: {missing_cols}")

    # Determine return column for financial calculations
    actual_return_col = None
    for candidate in [return_col, "return_1", "target_return", "returns"]:
        if candidate and candidate in df.columns:
            actual_return_col = candidate
            break

    # Ensure chronological order
    out = df.copy()
    if timestamp_col in out.columns:
        out = out.sort_values(timestamp_col).reset_index(drop=True)

    # Drop rows where target or features contain NaN (warmup / end of dataset)
    clean_df = out.dropna(subset=feature_cols + [target_col]).reset_index(drop=True)
    n_samples = len(clean_df)

    if n_samples < 50:
        raise ValueError(
            f"Dataset has only {n_samples} samples after dropping NaNs. Minimum 50 required."
        )

    # Calculate split boundary indices
    train_end = int(n_samples * train_ratio)
    val_end = train_end + int(n_samples * val_ratio)

    # Extract raw feature matrix & target arrays
    X_raw = clean_df[feature_cols].values
    y_all = clean_df[target_col].values.astype(int)
    returns_all = (
        clean_df[actual_return_col].values if actual_return_col else np.zeros(n_samples)
    )
    timestamps_all = (
        clean_df[timestamp_col] if timestamp_col in clean_df.columns else clean_df.index.to_series()
    )

    # Split raw arrays
    X_train_raw = X_raw[:train_end]
    X_val_raw = X_raw[train_end:val_end]
    X_test_raw = X_raw[val_end:]

    y_train = y_all[:train_end]
    y_val = y_all[train_end:val_end]
    y_test = y_all[val_end:]

    returns_train = returns_all[:train_end]
    returns_val = returns_all[train_end:val_end]
    returns_test = returns_all[val_end:]

    timestamps_train = timestamps_all.iloc[:train_end].reset_index(drop=True)
    timestamps_val = timestamps_all.iloc[train_end:val_end].reset_index(drop=True)
    timestamps_test = timestamps_all.iloc[val_end:].reset_index(drop=True)

    # Scale features: fit ONLY on training set!
    scaler = None
    if scale:
        scaler = StandardScaler()
        # Replace any residual Inf with NaN and then fill with 0
        X_train_raw = np.nan_to_num(X_train_raw, nan=0.0, posinf=0.0, neginf=0.0)
        X_val_raw = np.nan_to_num(X_val_raw, nan=0.0, posinf=0.0, neginf=0.0)
        X_test_raw = np.nan_to_num(X_test_raw, nan=0.0, posinf=0.0, neginf=0.0)

        scaler.fit(X_train_raw)
        X_train = scaler.transform(X_train_raw)
        X_val = scaler.transform(X_val_raw)
        X_test = scaler.transform(X_test_raw)
    else:
        X_train, X_val, X_test = X_train_raw, X_val_raw, X_test_raw

    return DatasetSplit(
        X_train=X_train,
        y_train=y_train,
        returns_train=returns_train,
        timestamps_train=timestamps_train,
        X_val=X_val,
        y_val=y_val,
        returns_val=returns_val,
        timestamps_val=timestamps_val,
        X_test=X_test,
        y_test=y_test,
        returns_test=returns_test,
        timestamps_test=timestamps_test,
        feature_names=feature_cols,
        scaler=scaler,
        raw_df_cleaned=clean_df,
    )
