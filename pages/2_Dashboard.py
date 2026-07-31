import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
from app.services.database_service import db_service
from app.core.config import Config
from app.core.logger import setup_logger
from app.core.auth import render_auth_sidebar

config = Config()
logger = setup_logger("page_dashboard")


try:
    with open("app/assets/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

with st.sidebar:
    st.markdown("### ⚡ NewsAnalytics AI")
    st.markdown("---")
    st.page_link("streamlit_app.py", label="Home", icon="🏠")
    st.page_link("pages/1_Scraping.py", label="AI Understanding", icon="📥")
    st.page_link("pages/2_Dashboard.py", label="Analytics Dashboard", icon="📊")
    st.page_link("pages/3_Fenomena.py", label="AI Investigator", icon="🔍")
    st.markdown("---")
    st.markdown("### ℹ️ Informasi")
    st.caption("Fitur mengeksplorasi berita dan memberikan insight secara menyeluruh.")

# Konfigurasi Halaman dengan layout wide
st.set_page_config(page_title="Analytics", layout="wide", page_icon="📊")

# Render autentikasi sidebar
render_auth_sidebar()

# Header Halaman Utama
st.markdown("# 📊 Analytics Dashboard")
st.caption("Dashboard and Admin Management")
st.markdown("Panel Administrator untuk melihat, menganalisis, dan mengelola basis data berita yang tersimpan.")
st.markdown("---")

# Variabel penentu apakah panel admin (manajemen destruktif) ditampilkan
is_admin = st.session_state.get("role") == "admin"

@st.cache_data(ttl=60)
def load_dashboard_data():
    return db_service.get_latest_scraped_data(limit=1000)

df_raw = load_dashboard_data()

date_col = "published_date" if "published_date" in df_raw.columns else ("waktu_tampilan" if "waktu_tampilan" in df_raw.columns else None)
if not df_raw.empty and date_col:
    df_raw[date_col] = pd.to_datetime(df_raw[date_col], errors="coerce")
    if df_raw[date_col].dt.tz is not None:
        df_raw[date_col] = df_raw[date_col].dt.tz_localize(None)
    df_raw["tanggal_saja"] = df_raw[date_col].dt.date

if df_raw.empty:
    st.warning("Basis data kosong. Belum ada data berita yang tersimpan di sistem.")
    st.stop()

col_keyword = "kata_kunci" if "kata_kunci" in df_raw.columns else "keyword"
col_media = "media" if "media" in df_raw.columns else "source"
col_content = "isi_konten" if "isi_konten" in df_raw.columns else "content"
col_title = "judul" if "judul" in df_raw.columns else "title"
col_sentiment = "Sentimen" if "Sentimen" in df_raw.columns else ("sentiment" if "sentiment" in df_raw.columns else None)

# UI/UX Pembaruan: Peningkatan Kontrol Panel Filter Horizontal di Bagian Atas
with st.container(key="dashboard_filter_bar"):
    st.markdown("#### ⚙️ Control Panel Data (Filter Global)")
    f_col1, f_col2, f_col3 = st.columns(3)

    with f_col1:
        available_options = list(df_raw[col_keyword].dropna().unique()) if col_keyword in df_raw.columns else []
        selected_keyword = st.multiselect("Filter Keyword", options=available_options, default=None)

    with f_col2:
        opsi_sentimen = list(df_raw[col_sentiment].dropna().unique()) if col_sentiment else ["POSITIVE", "NEGATIVE", "NEUTRAL"]
        selected_sentimen = st.multiselect("Filter Sentimen", options=opsi_sentimen, default=opsi_sentimen)

    with f_col3:
        opsi_media = list(df_raw[col_media].dropna().unique()) if col_media in df_raw.columns else []
        selected_media = st.multiselect("Filter Media", options=opsi_media, default=None)

filtered_df = df_raw.copy()
if selected_keyword:
    filtered_df = filtered_df[filtered_df[col_keyword].isin(selected_keyword)]
if selected_media:
    filtered_df = filtered_df[filtered_df[col_media].isin(selected_media)]
if col_sentiment and selected_sentimen:
    filtered_df = filtered_df[filtered_df[col_sentiment].isin(selected_sentimen)]

# Insights Utama & Metrik
st.markdown("## 📈 Insights Utama")
if filtered_df.empty:
    st.info("💡 Tidak ada data yang sesuai dengan kriteria filter Anda.")
else:
    def _metric_card(col, icon, color_class, value, label):
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-icon-badge {color_class}">{icon}</div>
                <div>
                    <div class="metric-text-value">{value}</div>
                    <div class="metric-text-label">{label}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    kpi1, kpi2, kpi3 = st.columns(3)
    _metric_card(kpi1, "📰", "metric-icon-blue", f"{len(filtered_df):,}", "Total Berita Terfilter")
    _metric_card(kpi2, "🏢", "metric-icon-amber", f"{filtered_df[col_media].nunique() if col_media in filtered_df.columns else 0:,}", "Portal Media Unik")
    _metric_card(kpi3, "🔖", "metric-icon-purple", f"{filtered_df[col_keyword].nunique() if col_keyword in filtered_df.columns else 0:,}", "Keyword Aktif")
    st.write("")

    insights = []
    top_media = filtered_df[col_media].value_counts() if col_media in filtered_df.columns else []
    if col_sentiment and not filtered_df[col_sentiment].empty:
        total_sentimen = len(filtered_df[col_sentiment].dropna())
        if total_sentimen > 0:
            sentimen_counts = filtered_df[col_sentiment].value_counts()
            jml_positif = sentimen_counts.get('POSITIVE', 0) + sentimen_counts.get('Positive', 0)
            jml_negatif = sentimen_counts.get('NEGATIVE', 0) + sentimen_counts.get('Negative', 0)
            persen_positif = (jml_positif / total_sentimen) * 100
            persen_negatif = (jml_negatif / total_sentimen) * 100
            
            if persen_positif > persen_negatif:
                insights.append(f"📈 Sentimen cenderung positif ({persen_positif:.1f}%)")
            elif persen_negatif > persen_positif:
                insights.append(f"📉 Sentimen cenderung negatif ({persen_negatif:.1f}%)")
            
    if len(top_media) > 0:
        insights.append(f"📰 Media dominan: {top_media.index[0]} ({top_media.values[0]} artikel)")
    
    for insight in insights:
        st.write(f"- {insight}")
    st.divider()

# Grafik Analitik Berdampingan
st.markdown("### 📊 Grafik Analitik")

def _sentiment_color_map(series):
    """Petakan tiap nilai sentimen unik ke warna semantik (hijau/merah/abu-abu),
    case-insensitive supaya cocok baik untuk 'POSITIVE' maupun 'Positive'."""
    palette = {}
    for val in series.dropna().unique():
        v = str(val).strip().lower()
        if v.startswith("pos"):
            palette[val] = "#10B981"   # hijau
        elif v.startswith("neg"):
            palette[val] = "#EF4444"   # merah
        else:
            palette[val] = "#94A3B8"   # netral / abu-abu
    return palette

_dark_chart_layout = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color="#E2E8F0",
    title_font_color="#FFFFFF",
    margin=dict(t=48, b=10, l=10, r=10),
)

col_chart1, col_chart2 = st.columns(2)
with col_chart1:
    if col_sentiment and col_sentiment in filtered_df.columns:
        fig_pie = px.pie(
            filtered_df, names=col_sentiment, title="Distribusi Sentimen Berita", hole=0.4,
            color=col_sentiment, color_discrete_map=_sentiment_color_map(filtered_df[col_sentiment]),
        )
        fig_pie.update_layout(**_dark_chart_layout)
        st.plotly_chart(fig_pie, width='stretch')
with col_chart2:
    if col_media in filtered_df.columns:
        top_media_chart = filtered_df[col_media].value_counts().reset_index()
        top_media_chart.columns = ['Media', 'Jumlah']
        fig_bar = px.bar(
            top_media_chart.head(10), x='Media', y='Jumlah', title="Top 10 Portal Media",
            color='Jumlah', color_continuous_scale=["#0B2A4A", "#38BDF8"],
        )
        fig_bar.update_layout(**_dark_chart_layout)
        st.plotly_chart(fig_bar, width='stretch')

st.markdown("### 📋 Daftar Berita Tersimpan")
@st.dialog("Detail Berita", width="large")
def show_news_detail(row):
    st.subheader(row[col_title])
    st.caption(f"📅 {row[date_col]} | 📰 {row[col_media]} | 🏷️ {row[col_sentiment]}")
    st.markdown("---")
    st.write(row[col_content])
    if st.button("Tutup"):
        st.rerun()

event = st.dataframe(filtered_df, width='stretch', selection_mode="single-row", on_select="rerun", key="data_editor")

if is_admin:
    selection = st.session_state.get("data_editor", None)
    if selection and "selection" in selection and len(selection["selection"]["rows"]) > 0:
        idx = selection["selection"]["rows"][0]
        selected_row_data = filtered_df.iloc[idx]
        show_news_detail(selected_row_data)
else:
    if st.session_state.get("data_editor", {}).get("selection", {}).get("rows"):
        st.info("Fitur detail berita hanya tersedia untuk akun Admin.")

st.divider()

# AREA DESTRUKTIF (HANYA ADMIN)
if is_admin:
    st.error("⚠️ PANEL ADMINISTRATOR: Manajemen Destruksi Basis Data")
    target_date = st.date_input("Pilih Tanggal Target", key="date_hapus_massal")
    admin_password = st.text_input("PostgreSQL Admin Password", type="password", key="pg_admin_password")

    if st.button("🚨 EKSEKUSI HAPUS MASAL TANGGAL INI", type="primary", width='stretch'):
        deleted = db_service.delete_articles_by_date(date_str=target_date.strftime("%Y-%m-%d"), admin_password=admin_password)
        if deleted:
            st.success(f"Berhasil menghapus {deleted} artikel pada tanggal {target_date}.")
            st.cache_data.clear()
            st.rerun()
        else:
            st.error("Password PostgreSQL salah atau proses penghapusan gagal.")
