import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

# --- CONFIGURASI DASAR ---
st.set_page_config(page_title="Optimized CSV Dashboard", layout="wide")
st.title("⚡ Fast & Interactive CSV Dashboard with Download Feature")

# --- FUNGSI LOAD DATA DENGAN CACHE ---
@st.cache_data(show_spinner=True)
def load_data(file):
    df = pd.read_csv(file)
    return df

# --- UPLOAD FILE CSV ---
uploaded_file = st.file_uploader("📂 Upload file CSV kamu di sini", type=["csv"])

if uploaded_file is not None:
    with st.spinner("📥 Sedang memuat data... tunggu sebentar..."):
        df = load_data(uploaded_file)

    # --- BATASI JUMLAH DATA (JIKA TERLALU BESAR) ---
    max_rows = 100000
    if len(df) > max_rows:
        st.warning(f"Dataset terlalu besar ({len(df):,} baris). "f"Hanya menampilkan {max_rows:,} baris pertama untuk efisiensi.")
        df = df.head(max_rows)

    # --- TAMPILKAN DATA ---
    st.success(f"✅ Data berhasil dimuat! Total {len(df):,} baris dan {len(df.columns)} kolom.")
    with st.expander("📋 Lihat data (klik untuk buka)"):
        st.dataframe(df.head(50), use_container_width=True)

    # --- SIDEBAR PENGATURAN ---
    st.sidebar.header("⚙️ Pengaturan Visualisasi")
    all_cols = df.columns.tolist()
    numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns.tolist()

    x_axis = st.sidebar.selectbox("Pilih kolom X-Axis", options=all_cols)
    y_axis = st.sidebar.selectbox("Pilih kolom Y-Axis (numerik)", options=numeric_cols)
    chart_type = st.sidebar.selectbox("Pilih jenis grafik", ["Bar", "Line", "Scatter", "Pie"])

    # --- FILTER OPSIONAL ---
    st.sidebar.header("🔍 Filter Data (opsional)")
    filter_cols = st.sidebar.multiselect("Pilih kolom untuk difilter", options=all_cols)
    filtered_df = df.copy()
    for col in filter_cols:
        vals = df[col].unique().tolist()
        chosen = st.sidebar.multiselect(f"Nilai untuk '{col}'", vals)
        if chosen:
            filtered_df = filtered_df[filtered_df[col].isin(chosen)]

    # --- TOMBOL UNTUK VISUALISASI ---
    run_viz = st.sidebar.button("🚀 Tampilkan Visualisasi")

    # --- BAGIAN TAB ---
    tab1, tab2 = st.tabs(["📈 Visualisasi Data", "📊 Statistik Dataset"])

    with tab1:
        if run_viz:
            st.subheader("📈 Hasil Visualisasi")

            # --- PILIHAN GRAFIK ---
            if chart_type == "Bar":
                fig = px.bar(filtered_df, x=x_axis, y=y_axis, color=x_axis)
            elif chart_type == "Line":
                fig = px.line(filtered_df, x=x_axis, y=y_axis)
            elif chart_type == "Scatter":
                fig = px.scatter(filtered_df, x=x_axis, y=y_axis, color=x_axis)
            elif chart_type == "Pie":
                fig = px.pie(filtered_df, names=x_axis, values=y_axis)

            st.plotly_chart(fig, use_container_width=True)

            # --- FITUR DOWNLOAD GAMBAR ---
            # Simpan grafik ke buffer PNG
            img_bytes = BytesIO()
            fig.write_image(img_bytes, format="png")
            img_bytes.seek(0)

            st.download_button(
                label="📸 Download Grafik (.png)",
                data=img_bytes,
                file_name=f"visualisasi_{chart_type.lower()}.png",
                mime="image/png"
            )
        else:
            st.info("Klik tombol **🚀 Tampilkan Visualisasi** di sidebar untuk menampilkan grafik.")

    with tab2:
        st.subheader("📊 Statistik Dasar")
        st.dataframe(df.describe().T.style.highlight_max(axis=0), use_container_width=True)

else:
    st.info("Silakan upload file CSV terlebih dahulu untuk memulai 📁")
