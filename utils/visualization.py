from typing import List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

AGG_FUNCS = {
    "Sum": "sum",
    "Mean": "mean",
    "Count": "count",
    "Min": "min",
    "Max": "max",
}


def validate_config(chart_type: str, df: pd.DataFrame, x: Optional[str], y: Optional[str], numeric_cols: List[str]) -> Optional[str]:
    """Return a human-readable error, or None if the configuration is safe to plot."""
    if df.empty:
        return "No data matches the current filter."

    if chart_type == "Scatter":
        if x is None or y is None or x not in numeric_cols or y not in numeric_cols:
            return "Scatter plot requires numeric X and Y columns."
    elif chart_type in ("Bar", "Line", "Pie"):
        if y is None or y not in numeric_cols:
            return f"{chart_type} chart requires a numeric Y-axis (value) column."
        if x is None:
            return f"{chart_type} chart requires an X-axis (category) column."
    elif chart_type == "Histogram":
        if x is None or x not in numeric_cols:
            return "Histogram requires a numeric column."
    elif chart_type == "Box Plot":
        if y is None or y not in numeric_cols:
            return "Box plot requires a numeric column."
    return None


def check_pie_categories(df: pd.DataFrame, x: Optional[str], max_slices: int = 12) -> Optional[str]:
    if x is None:
        return None
    n = df[x].nunique(dropna=True)
    if n > max_slices:
        return f"'{x}' has {n} unique values, too many for a readable pie chart. Consider using a Bar Chart instead."
    return None


def _grouped(df: pd.DataFrame, group_cols: List[str], value_col: str, agg_label: str) -> pd.DataFrame:
    func = AGG_FUNCS[agg_label]
    return df.groupby(group_cols, dropna=False, as_index=False)[value_col].agg(func)


def build_chart(
    chart_type: str,
    df: pd.DataFrame,
    x: Optional[str] = None,
    y: Optional[str] = None,
    agg_label: Optional[str] = None,
    color: Optional[str] = None,
    bins: Optional[int] = None,
) -> go.Figure:
    if chart_type == "Bar":
        group_cols = [x] + ([color] if color else [])
        plot_df = _grouped(df, group_cols, y, agg_label)
        return px.bar(plot_df, x=x, y=y, color=color)

    if chart_type == "Line":
        group_cols = [x] + ([color] if color else [])
        plot_df = _grouped(df, group_cols, y, agg_label).sort_values(x)
        return px.line(plot_df, x=x, y=y, color=color)

    if chart_type == "Scatter":
        return px.scatter(df, x=x, y=y, color=color)

    if chart_type == "Pie":
        plot_df = _grouped(df, [x], y, agg_label)
        return px.pie(plot_df, names=x, values=y)

    if chart_type == "Histogram":
        return px.histogram(df, x=x, nbins=bins)

    if chart_type == "Box Plot":
        return px.box(df, x=color, y=y)

    raise ValueError(f"Unknown chart type: {chart_type}")


def recommend_charts(numeric_cols: List[str], categorical_cols: List[str], datetime_cols: List[str]) -> List[tuple]:
    """Rule-based recommendations based on the dataset's actual structure."""
    recs = []
    if datetime_cols and numeric_cols:
        recs.append(("Line Chart", f"{numeric_cols[0]} over {datetime_cols[0]}"))
    if categorical_cols and numeric_cols:
        recs.append(("Bar Chart", f"{numeric_cols[0]} by {categorical_cols[0]}"))
    if len(numeric_cols) >= 2:
        recs.append(("Scatter Plot", f"{numeric_cols[0]} vs {numeric_cols[1]}"))
    if numeric_cols:
        recs.append(("Histogram", f"Distribution of {numeric_cols[0]}"))
        recs.append(("Box Plot", f"Spread of {numeric_cols[0]}"))
    if categorical_cols and not numeric_cols:
        recs.append(("Bar Chart", f"Count of {categorical_cols[0]}"))
    return recs[:4]