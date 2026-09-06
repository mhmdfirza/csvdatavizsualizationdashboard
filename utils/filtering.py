from typing import Optional

import pandas as pd

NUMERIC_OPS = ["=", "!=", ">", ">=", "<", "<="]
TEXT_OPS = ["equals", "not equals", "contains"]
DATETIME_OPS = ["after", "before", "between"]


def apply_numeric_filter(df: pd.DataFrame, col: str, op: str, value: float) -> pd.DataFrame:
    if op == "=":
        return df[df[col] == value]
    if op == "!=":
        return df[df[col] != value]
    if op == ">":
        return df[df[col] > value]
    if op == ">=":
        return df[df[col] >= value]
    if op == "<":
        return df[df[col] < value]
    if op == "<=":
        return df[df[col] <= value]
    return df


def apply_text_filter(df: pd.DataFrame, col: str, op: str, value: str) -> pd.DataFrame:
    series = df[col].astype(str)
    if op == "equals":
        return df[series == value]
    if op == "not equals":
        return df[series != value]
    if op == "contains":
        return df[series.str.contains(value, case=False, na=False)]
    return df


def apply_datetime_filter(
    df: pd.DataFrame, col: str, op: str, value: pd.Timestamp, value2: Optional[pd.Timestamp] = None
) -> pd.DataFrame:
    series = pd.to_datetime(df[col], errors="coerce")
    if op == "after":
        return df[series > value]
    if op == "before":
        return df[series < value]
    if op == "between" and value2 is not None:
        return df[(series >= value) & (series <= value2)]
    return df