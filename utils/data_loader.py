from io import BytesIO
from typing import Optional, Tuple

import pandas as pd
import streamlit as st

LARGE_DATASET_THRESHOLD = 100_000
VIZ_SAMPLE_SIZE = 100_000


def validate_csv(uploaded_file) -> Tuple[bool, Optional[str]]:
    if uploaded_file is None:
        return False, "No file uploaded."
    if not uploaded_file.name.lower().endswith(".csv"):
        return False, "Only .csv files are supported."
    return True, None


@st.cache_data(show_spinner=False)
def load_csv(file_bytes: bytes, file_name: str) -> pd.DataFrame:
    """Parse CSV bytes into a DataFrame. Tries the faster pyarrow engine first,
    falling back to the default engine for CSVs it can't handle (e.g. irregular
    quoting or mixed-type columns)."""
    try:
        return pd.read_csv(BytesIO(file_bytes), engine="pyarrow")
    except Exception:
        pass
    try:
        return pd.read_csv(BytesIO(file_bytes))
    except Exception as e:
        raise ValueError(f"Failed to parse CSV: {e}")


def get_viz_dataframe(df: pd.DataFrame, max_rows: int = VIZ_SAMPLE_SIZE) -> Tuple[pd.DataFrame, bool]:
    """Return a dataframe safe to plot. Sampling only ever affects charts,
    never the working dataset used for cleaning, filtering, stats, or export."""
    if len(df) > max_rows:
        return df.sample(n=max_rows, random_state=42).sort_index(), True
    return df, False