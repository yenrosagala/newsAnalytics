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

st.set_page_config(page_title="FlashNews: Database Management", layout="wide", page_icon="📊")

# Halaman ini terbuka untuk pengguna umum -- tidak perlu login.
# Panel admin (hapus data) di bagian bawah halaman ini tetap tergerbang
# terpisah lewat pengecekan role admin (lihat bagian "PANEL ADMINISTRATOR").
render_auth_sidebar()

try:
    with open("app/assets/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

st.title("📊 FlashNews: Database Management Dashboard")
st.write("Panel Administrator untuk melihat, menganalisis, dan mengelola basis data berita yang tersimpan.")

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

# NOTE: db_service.get_latest_scraped_data() me-rename kolom mentah Supabase
# ("keyword", "sentiment", dst) menjadi "kata_kunci", "Sentimen", dst.
# Fallback disediakan agar dashboard tetap jalan walau mapping berubah.
col_keyword = "kata_kunci" if "kata_kunci" in df_raw.columns else "keyword"
col_media = "media" if "media" in df_raw.columns else "source"
col_content = "isi_konten" if "isi_konten" in df_raw.columns else "content"
col_title = "judul" if "judul" in df_raw.columns else "title"
col_sentiment = "Sentimen" if "Sentimen" in df_raw.columns else ("sentiment" if "sentiment" in df_raw.columns else None)

with st.sidebar:
    st.markdown("---")
    st.title("🎛️ Control Panel Data")
    
    available_options = list(df_raw[col_keyword].dropna().unique()) if col_keyword in df_raw.columns else []
    selected_keyword = st.multiselect("Filter Keyword", options=available_options, default=None)
    
    opsi_sentimen = list(df_raw[col_sentiment].dropna().unique()) if col_sentiment else ["POSITIVE", "NEGATIVE", "NEUTRAL"]
    selected_sentimen = st.multiselect("Filter Sentimen", options=opsi_sentimen, default=opsi_sentimen)
    
    opsi_media = list(df_raw[col_media].dropna().unique()) if col_media in df_raw.columns else []
    selected_media = st.multiselect("Filter Media", options=opsi_media, default=None)

filtered_df = df_raw.copy()
if selected_keyword:
    filtered_df = filtered_df[filtered_df[col_keyword].isin(selected_keyword)]
if selected_media:
    filtered_df = filtered_df[filtered_df[col_media].isin(selected_media)]
if col_sentiment and selected_sentimen:
    filtered_df = filtered_df[filtered_df[col_sentiment].isin(selected_sentimen)]

st.markdown("## Insights Utama")
if filtered_df.empty:
    st.info("💡 Tidak ada data yang sesuai dengan kriteria filter Anda.")
else:
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Total Berita Terfilter", len(filtered_df))
    kpi2.metric("Portal Media Unik", filtered_df[col_media].nunique() if col_media in filtered_df.columns else 0)
    kpi3.metric("Keyword Aktif", filtered_df[col_keyword].nunique() if col_keyword in filtered_df.columns else 0)

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

st.markdown("### Grafik Analitik")
col_chart1, col_chart2 = st.columns(2)
with col_chart1:
    if col_sentiment and col_sentiment in filtered_df.columns:
        fig_pie = px.pie(filtered_df, names=col_sentiment, title="Distribusi Sentimen Berita", hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)
with col_chart2:
    if col_media in filtered_df.columns:
        top_media_chart = filtered_df[col_media].value_counts().reset_index()
        top_media_chart.columns = ['Media', 'Jumlah']
        fig_bar = px.bar(top_media_chart.head(10), x='Media', y='Jumlah', title="Top 10 Portal Media", color='Jumlah')
        st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("### Daftar Berita Tersimpan")
@st.dialog("Detail Berita", width="large")
def show_news_detail(row):
    st.subheader(row[col_title])
    st.caption(f"📅 {row[date_col]} | 📰 {row[col_media]} | 🏷️ {row[col_sentiment]}")
    st.markdown("---")
    st.write(row[col_content])
    if st.button("Tutup"):
        st.rerun()

event = st.dataframe(filtered_df, use_container_width=True, selection_mode="single-row", on_select="rerun", key="data_editor")

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

    if st.button("🚨 EKSEKUSI HAPUS MASAL TANGGAL INI", type="primary", use_container_width=True):
        deleted = db_service.delete_articles_by_date(date_str=target_date.strftime("%Y-%m-%d"), admin_password=admin_password)
        if deleted:
            st.success(f"Berhasil menghapus {deleted} artikel pada tanggal {target_date}.")
            st.cache_data.clear()
            st.rerun()
        else:
            st.error("Password PostgreSQL salah atau proses penghapusan gagal.")