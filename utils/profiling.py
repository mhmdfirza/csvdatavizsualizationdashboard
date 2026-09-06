from typing import List, Tuple

import numpy as np
import pandas as pd


def detect_column_types(df: pd.DataFrame) -> Tuple[List[str], List[str], List[str]]:
    """Split columns into numeric, categorical, and datetime groups.
    Every column falls into exactly one group, so the three lists always
    partition df.columns."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    datetime_cols = df.select_dtypes(include=["datetime64"]).columns.tolist()
    categorical_cols = [c for c in df.columns if c not in numeric_cols and c not in datetime_cols]
    return numeric_cols, categorical_cols, datetime_cols


def try_parse_datetime_candidates(df: pd.DataFrame, threshold: float = 0.9, sample_size: int = 200) -> List[str]:
    """Suggest object columns that look like dates, without converting them.
    Conversion only happens when the user explicitly asks for it in Data Cleaning."""
    candidates = []
    for col in df.select_dtypes(include=["object"]).columns:
        sample = df[col].dropna().head(sample_size)
        if sample.empty:
            continue
        parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
        if parsed.notna().mean() >= threshold:
            candidates.append(col)
    return candidates


def get_column_profile(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in df.columns:
        series = df[col]
        rows.append({
            "Column": col,
            "Data Type": str(series.dtype),
            "Non-null Count": int(series.notna().sum()),
            "Missing Count": int(series.isna().sum()),
            "Missing %": round(series.isna().mean() * 100, 2),
            "Unique Count": int(series.nunique(dropna=True)),
        })
    return pd.DataFrame(rows)


def get_numeric_summary(df: pd.DataFrame, numeric_cols: List[str]) -> pd.DataFrame:
    if not numeric_cols:
        return pd.DataFrame()
    summary = df[numeric_cols].agg(["mean", "median", "min", "max", "std"]).T
    summary.columns = ["Mean", "Median", "Min", "Max", "Std"]
    return summary.round(3)


def get_overview_metrics(
    df: pd.DataFrame, numeric_cols: List[str], categorical_cols: List[str], datetime_cols: List[str]
) -> dict:
    return {
        "rows": len(df),
        "columns": len(df.columns),
        "numeric_columns": len(numeric_cols),
        "categorical_columns": len(categorical_cols),
        "datetime_columns": len(datetime_cols),
        "missing_values": int(df.isna().sum().sum()),
        "duplicate_rows": int(df.duplicated().sum()),
    }