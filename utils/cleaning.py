from typing import Optional, Tuple

import pandas as pd


def get_missing_summary(df: pd.DataFrame) -> pd.DataFrame:
    missing = df.isna().sum()
    missing = missing[missing > 0]
    pct = (missing.values / len(df) * 100).round(2) if len(df) else missing.values
    return pd.DataFrame({"Column": missing.index, "Missing Count": missing.values, "Missing %": pct})


def fill_numeric(df: pd.DataFrame, col: str, strategy: str) -> pd.DataFrame:
    df = df.copy()
    if strategy == "Drop rows":
        return df.dropna(subset=[col])
    if strategy == "Fill mean":
        df[col] = df[col].fillna(df[col].mean())
    elif strategy == "Fill median":
        df[col] = df[col].fillna(df[col].median())
    return df


def fill_categorical(df: pd.DataFrame, col: str, strategy: str, custom_value: Optional[str] = None) -> pd.DataFrame:
    df = df.copy()
    if strategy == "Drop rows":
        return df.dropna(subset=[col])
    if strategy == "Fill mode":
        mode = df[col].mode(dropna=True)
        if not mode.empty:
            df[col] = df[col].fillna(mode.iloc[0])
    elif strategy == "Fill custom value":
        df[col] = df[col].fillna(custom_value)
    return df


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop_duplicates(keep="first").reset_index(drop=True)


def convert_dtype(df: pd.DataFrame, col: str, target_type: str) -> Tuple[pd.DataFrame, Optional[str]]:
    """Convert a column's dtype. Never raises: a failed conversion returns the
    original dataframe untouched plus an error message for the UI to show."""
    df = df.copy()
    try:
        if target_type == "numeric":
            df[col] = pd.to_numeric(df[col], errors="coerce")
        elif target_type == "datetime":
            df[col] = pd.to_datetime(df[col], errors="coerce", format="mixed")
        elif target_type == "string":
            df[col] = df[col].astype(str)
        else:
            return df, f"Unknown target type: {target_type}"
        return df, None
    except Exception as e:
        return df, str(e)