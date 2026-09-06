from io import BytesIO

import pandas as pd
import streamlit as st

from utils.cleaning import convert_dtype, fill_categorical, fill_numeric, get_missing_summary, remove_duplicates
from utils.data_loader import LARGE_DATASET_THRESHOLD, get_viz_dataframe, load_csv, validate_csv
from utils.filtering import (
    DATETIME_OPS,
    NUMERIC_OPS,
    TEXT_OPS,
    apply_datetime_filter,
    apply_numeric_filter,
    apply_text_filter,
)
from utils.profiling import (
    detect_column_types,
    get_column_profile,
    get_numeric_summary,
    get_overview_metrics,
    try_parse_datetime_candidates,
)
from utils.visualization import AGG_FUNCS, build_chart, check_pie_categories, recommend_charts, validate_config

st.set_page_config(page_title="CSV Analytics Workspace", layout="wide")
st.title("CSV Analytics Workspace")


def optional_selectbox(label: str, options: list, key: str = None):
    """Selectbox that supports a 'no selection' choice, returning None for it."""
    choice = st.selectbox(label, ["(none)"] + options, key=key)
    return None if choice == "(none)" else choice


# --- SESSION STATE INIT ---
for key in ("original_df", "working_df", "uploaded_file_name"):
    if key not in st.session_state:
        st.session_state[key] = None

# --- FILE UPLOAD ---
uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

if uploaded_file is not None:
    is_valid, error = validate_csv(uploaded_file)
    if not is_valid:
        st.error(error)
        st.stop()

    if st.session_state.uploaded_file_name != uploaded_file.name:
        file_bytes = uploaded_file.getvalue()
        try:
            df = load_csv(file_bytes, uploaded_file.name)
        except ValueError as e:
            st.error(str(e))
            st.stop()

        if len(df) > LARGE_DATASET_THRESHOLD:
            st.warning(
                f"This dataset has {len(df):,} rows, above the {LARGE_DATASET_THRESHOLD:,}-row comfort "
                "limit for this MVP. The full dataset is still used for cleaning, filtering, statistics, "
                "and export — only chart rendering will use a random sample for responsiveness."
            )

        st.session_state.original_df = df
        st.session_state.working_df = df.copy()
        st.session_state.uploaded_file_name = uploaded_file.name

if st.session_state.working_df is None:
    st.info("Upload a CSV file to get started.")
    st.stop()

working_df = st.session_state.working_df
numeric_cols, categorical_cols, datetime_cols = detect_column_types(working_df)

with st.sidebar:
    st.header("Dataset")
    st.caption(st.session_state.uploaded_file_name)
    st.caption(f"Working dataset: {len(working_df):,} rows")
    if st.button("Reset to original dataset", use_container_width=True):
        st.session_state.working_df = st.session_state.original_df.copy()
        st.rerun()

tab_overview, tab_preview, tab_clean, tab_filter, tab_stats, tab_viz = st.tabs(
    ["Overview", "Data Preview", "Data Cleaning", "Filtering", "Statistics", "Visualization"]
)

# ---------------- OVERVIEW ----------------
with tab_overview:
    metrics = get_overview_metrics(working_df, numeric_cols, categorical_cols, datetime_cols)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows", f"{metrics['rows']:,}")
    c2.metric("Columns", metrics["columns"])
    c3.metric("Missing Values", f"{metrics['missing_values']:,}")
    c4.metric("Duplicate Rows", f"{metrics['duplicate_rows']:,}")

    c5, c6, c7 = st.columns(3)
    c5.metric("Numeric Columns", metrics["numeric_columns"])
    c6.metric("Categorical Columns", metrics["categorical_columns"])
    c7.metric("Datetime Columns", metrics["datetime_columns"])

    datetime_candidates = try_parse_datetime_candidates(working_df)
    if datetime_candidates:
        st.info(
            "These columns look like they might be dates: "
            f"{', '.join(datetime_candidates)}. Convert them in the Data Cleaning tab if needed."
        )

# ---------------- DATA PREVIEW ----------------
with tab_preview:
    st.subheader("Data Preview")
    preview_rows = st.slider("Rows to preview", min_value=10, max_value=500, value=50, step=10)
    st.dataframe(working_df.head(preview_rows), use_container_width=True)

    st.subheader("Column Profile")
    st.dataframe(get_column_profile(working_df), use_container_width=True)

    if numeric_cols:
        st.subheader("Numeric Column Summary")
        st.dataframe(get_numeric_summary(working_df, numeric_cols), use_container_width=True)

# ---------------- CLEANING ----------------
with tab_clean:
    st.subheader("Missing Values")
    missing_summary = get_missing_summary(working_df)
    if missing_summary.empty:
        st.success("No missing values in the working dataset.")
    else:
        st.dataframe(missing_summary, use_container_width=True)
        col_to_clean = st.selectbox("Column to handle", options=missing_summary["Column"].tolist())

        if col_to_clean in numeric_cols:
            strategy = st.selectbox("Strategy", ["Drop rows", "Fill mean", "Fill median"])
            if st.button("Apply missing value strategy"):
                st.session_state.working_df = fill_numeric(working_df, col_to_clean, strategy)
                st.rerun()
        else:
            strategy = st.selectbox("Strategy", ["Drop rows", "Fill mode", "Fill custom value"])
            custom_value = None
            if strategy == "Fill custom value":
                custom_value = st.text_input("Custom value", value="")
            if st.button("Apply missing value strategy"):
                st.session_state.working_df = fill_categorical(working_df, col_to_clean, strategy, custom_value)
                st.rerun()

    st.divider()
    st.subheader("Duplicate Rows")
    dup_count = int(working_df.duplicated().sum())
    st.write(f"Duplicate Rows: {dup_count}")
    if dup_count > 0 and st.button("Remove duplicates"):
        st.session_state.working_df = remove_duplicates(working_df)
        st.rerun()

    st.divider()
    st.subheader("Data Type Conversion")
    conv_col = st.selectbox("Column to convert", options=working_df.columns.tolist(), key="conv_col")
    target_type = st.selectbox("Convert to", ["numeric", "datetime", "string"])
    if st.button("Convert column"):
        new_df, conv_err = convert_dtype(working_df, conv_col, target_type)
        if conv_err:
            st.error(f"Conversion failed: {conv_err}")
        else:
            st.session_state.working_df = new_df
            st.success(f"Converted '{conv_col}' to {target_type}.")
            st.rerun()

# ---------------- FILTERING ----------------
with tab_filter:
    st.subheader("Filter Working Dataset")
    filter_col = st.selectbox("Column to filter", options=working_df.columns.tolist(), key="filter_col")

    if filter_col in numeric_cols:
        op = st.selectbox("Operator", NUMERIC_OPS)
        default_value = float(working_df[filter_col].dropna().median()) if working_df[filter_col].notna().any() else 0.0
        value = st.number_input("Value", value=default_value)
        if st.button("Apply filter"):
            st.session_state.working_df = apply_numeric_filter(working_df, filter_col, op, value)
            st.rerun()
    elif filter_col in datetime_cols:
        op = st.selectbox("Operator", DATETIME_OPS)
        value = st.date_input("Date")
        value2 = st.date_input("End date", key="filter_date_end") if op == "between" else None
        if st.button("Apply filter"):
            st.session_state.working_df = apply_datetime_filter(
                working_df, filter_col, op, pd.to_datetime(value), pd.to_datetime(value2) if value2 else None
            )
            st.rerun()
    else:
        op = st.selectbox("Operator", TEXT_OPS)
        value = st.text_input("Value")
        if st.button("Apply filter"):
            st.session_state.working_df = apply_text_filter(working_df, filter_col, op, value)
            st.rerun()

    if working_df.empty:
        st.warning("No data matches the current filter.")

# ---------------- STATISTICS ----------------
with tab_stats:
    if working_df.empty:
        st.warning("No data matches the current filter.")
    else:
        st.subheader("Descriptive Statistics (Numeric)")
        if numeric_cols:
            st.dataframe(working_df[numeric_cols].describe().T, use_container_width=True)
        else:
            st.info("No numeric columns available.")

        if categorical_cols:
            st.subheader("Descriptive Statistics (Categorical)")
            st.dataframe(working_df[categorical_cols].describe().T, use_container_width=True)

# ---------------- VISUALIZATION ----------------
with tab_viz:
    if working_df.empty:
        st.warning("No data matches the current filter.")
    else:
        viz_df, was_sampled = get_viz_dataframe(working_df)
        if was_sampled:
            st.info(f"Visualizing a random sample of {len(viz_df):,} rows out of {len(working_df):,} for responsiveness.")

        recs = recommend_charts(numeric_cols, categorical_cols, datetime_cols)
        if recs:
            st.subheader("Recommended Charts")
            rec_cols = st.columns(len(recs))
            for rc, (chart_name, desc) in zip(rec_cols, recs):
                rc.markdown(f"**{chart_name}**\n\n{desc}")

        st.subheader("Chart Builder")
        chart_type = st.selectbox("Chart type", ["Bar", "Line", "Scatter", "Pie", "Histogram", "Box Plot"])
        all_cols = viz_df.columns.tolist()

        x_axis = y_axis = agg_label = color_col = bins = None

        if chart_type in ("Bar", "Line"):
            x_axis = st.selectbox("X axis", options=all_cols)
            y_axis = st.selectbox("Y axis (numeric)", options=numeric_cols if numeric_cols else all_cols)
            agg_label = st.selectbox("Aggregation", list(AGG_FUNCS.keys()))
            color_col = optional_selectbox("Group/Color (optional)", categorical_cols)
        elif chart_type == "Pie":
            x_axis = st.selectbox("Category column", options=all_cols)
            y_axis = st.selectbox("Value column (numeric)", options=numeric_cols if numeric_cols else all_cols)
            agg_label = st.selectbox("Aggregation", list(AGG_FUNCS.keys()))
        elif chart_type == "Scatter":
            x_axis = st.selectbox("X axis (numeric)", options=numeric_cols if numeric_cols else all_cols)
            y_axis = st.selectbox("Y axis (numeric)", options=numeric_cols if numeric_cols else all_cols)
            color_col = optional_selectbox("Color (optional)", categorical_cols)
        elif chart_type == "Histogram":
            x_axis = st.selectbox("Column (numeric)", options=numeric_cols if numeric_cols else all_cols)
            bins = st.slider("Number of bins", min_value=5, max_value=100, value=30)
        elif chart_type == "Box Plot":
            y_axis = st.selectbox("Column (numeric)", options=numeric_cols if numeric_cols else all_cols)
            color_col = optional_selectbox("Group by (optional)", categorical_cols)

        config_error = validate_config(chart_type, viz_df, x_axis, y_axis, numeric_cols)
        if config_error:
            st.warning(config_error)
        else:
            if chart_type == "Pie":
                pie_warning = check_pie_categories(viz_df, x_axis)
                if pie_warning:
                    st.warning(pie_warning)

            fig = build_chart(chart_type, viz_df, x=x_axis, y=y_axis, agg_label=agg_label, color=color_col, bins=bins)
            st.plotly_chart(fig, use_container_width=True)

            try:
                img_bytes = BytesIO()
                fig.write_image(img_bytes, format="png")
                img_bytes.seek(0)
                st.download_button(
                    "Download chart (.png)",
                    data=img_bytes,
                    file_name=f"chart_{chart_type.lower().replace(' ', '_')}.png",
                    mime="image/png",
                )
            except Exception:
                st.caption("PNG export unavailable (kaleido not installed).")

# ---------------- EXPORT ----------------
st.divider()
st.subheader("Export")
csv_bytes = working_df.to_csv(index=False).encode("utf-8")
st.download_button("Download working dataset (.csv)", data=csv_bytes, file_name="working_dataset.csv", mime="text/csv")