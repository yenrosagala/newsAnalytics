import streamlit as st
import pandas as pd
from datetime import datetime
import os

from app.services.scraper_service import scraper_service
from app.services.database_service import db_service 
from app.services.ai_service import ai_service
from app.services.clustering_service import clustering_service
from app.core.config import Config   
from app.core.logger import setup_logger
from app.generate_pdf import generate_pdf_report
from app.prompts.executive_summary import get_executive_summary_prompt
from app.core.auth import render_auth_sidebar

# Konfigurasi Halaman (Wajib dipanggil pertama kali)
st.set_page_config(page_title="AI News Understanding", layout="wide", page_icon="📥")

# Inisialisasi konfigurasi
config = Config()
logger = setup_logger("AI Understanding")

# Memuat File CSS Kustom (jika tersedia)
css_path = "app/assets/style.css"
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
else:
    logger.warning("File style.css tidak ditemukan di folder assets.")

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

# Render autentikasi sidebar
render_auth_sidebar()

# Header Halaman Utama dengan UI/UX Modern
st.markdown("# 📥 AI Understanding")
st.caption("Understanding the News")
st.markdown("Masukkan kata kunci untuk mengambil data berita terbaru dan kelola database executive summary.")
st.markdown("---")

# Variabel status admin
is_admin = st.session_state.get("role") == "admin"

# --- HELPER PDF FUNCTION ---
def process_and_get_pdf(target_keyword):
    df_all = db_service.get_latest_scraped_data(limit=1000)
    if df_all.empty:
        return None, "Data berita kosong."
    
    filtered_data = df_all[df_all['kata_kunci'].astype(str).str.contains(target_keyword, case=False, na=False, regex=False)]
    if filtered_data.empty:
        return None, f"Tidak ada data untuk keyword '{target_keyword}'."
        
    date_min = filtered_data['waktu_tampilan'].min() if 'waktu_tampilan' in filtered_data.columns else "-"
    date_max = filtered_data['waktu_tampilan'].max() if 'waktu_tampilan' in filtered_data.columns else "-"
    date_range_str = f"{date_min} sampai {date_max}"
    
    t_media = filtered_data['media'].value_counts().head(3) if 'media' in filtered_data.columns else {}
    t_media_str = ", ".join([f"{m} ({c} artikel)" for m, c in t_media.items()]) if not t_media.empty else "Berbagai Media"
    
    cached_summary = db_service.get_cached_executive_summary(target_keyword)
    if cached_summary:
        summary_text_result = cached_summary
    else:
        formatted_articles = [
            f"--- ARTIKEL REFERENSI ---\nMedia: {row.get('media', '-')}\nTanggal: {row.get('waktu_tampilan', '-')}\nJudul: {row.get('judul', '-')}\nIsi:\n{row.get('isi_konten', '-')}" 
            for _, row in filtered_data.iterrows()
        ]
        concatenated_content = "\n\n".join(formatted_articles)
        prompt = get_executive_summary_prompt(
            data_context="Analisis berita komprehensif 2026",
            display_title_keyword=target_keyword,
            date_range_str=date_range_str,
            t_media_str=t_media_str,
            concatenated_content=concatenated_content,
            catatan_regenerate=""
        )
        try:
            summary_text_result = ai_service.generate(prompt)
            db_service.save_executive_summary_to_db(kata_kunci=target_keyword, rentang_waktu=date_range_str, hasil_summary=summary_text_result)
        except Exception as ai_err:
            return None, f"Gagal menghasilkan ringkasan via AI: {ai_err}"
            
    insights_list = [f"Total keseluruhan artikel: {len(filtered_data)} berita."]
    pdf_bytes = generate_pdf_report(filtered_df=filtered_data, insights=insights_list, target_keyword=target_keyword, date_range_str=date_range_str, t_media_str=t_media_str, summary_text=summary_text_result)
    return pdf_bytes, None

# --- MEMBUAT TABS AGAR HALAMAN LEBIH BERSIH & TIDAK PADAT ---
tab_scrape, tab_database, tab_cluster = st.tabs(["🚀 Scraper & Summary", "🗄️ Database Arsip", "🧩 Story Clustering & Timeline"])

# ================= TAB 1: SCRAPER =================
with tab_scrape:
    st.subheader("⚙️ Parameter Pencarian Berita")
    with st.form("scraping_form"):
        keyword = st.text_input("Kata Kunci (Keyword):", st.session_state.get("current_keyword", "Transformasi Digital Indonesia"))
        col_a, col_b = st.columns(2)
        with col_a:
            num_results = st.number_input("Jumlah Maksimal Artikel:", min_value=5, max_value=50, value=config.DEFAULT_NUM_RESULTS, step=5)
        with col_b:
            sentiment_filter = st.selectbox("Filter Sentimen", ["Semua", "Positif", "Netral", "Negatif"])
            
        submit_scraping = st.form_submit_button("🚀 Jalankan Scraping", use_container_width=True, type="primary")

    if submit_scraping:
        if not keyword.strip():
            st.error("Keyword tidak boleh kosong!")
        else:
            st.session_state["current_keyword"] = keyword
            progress_bar = st.progress(0.0)
            status_container = st.empty()
            
            saved_count = scraper_service.execute_scraping_workflow(
                keyword=keyword, limit=num_results, region="ID", status_container=status_container, progress_bar=progress_bar
            )
            
            if saved_count > 0:
                status_container.success(f"✅ Berhasil menyimpan {saved_count} artikel baru!")
                progress_bar.empty()
                st.session_state["trigger_auto_summary"] = keyword
            else:
                status_container.warning("Tidak ada berita baru ditemukan.")
                progress_bar.empty()

    active_keyword_to_summarize = st.session_state.get("trigger_auto_summary")
    if active_keyword_to_summarize:
        st.info(f"📄 Laporan untuk '{active_keyword_to_summarize}' siap diunduh.")
        if st.button("📥 Download PDF Laporan Terbaru", use_container_width=True):
            pdf_data, err_msg = process_and_get_pdf(active_keyword_to_summarize)
            if pdf_data:
                st.download_button("Klik untuk Simpan PDF", data=bytes(pdf_data), file_name=f"Laporan_{active_keyword_to_summarize}.pdf", mime="application/pdf", use_container_width=True)
            else:
                st.error(err_msg)

# ================= TAB 2: DATABASE ARSIP =================
with tab_database:
    st.subheader("🗄️ Daftar Executive Summary Tersimpan")
    df_latest = db_service.get_latest_scraped_data(limit=5)

    if not df_latest.empty:
        for kw in df_latest['kata_kunci'].dropna().unique():
            df_kw = df_latest[df_latest['kata_kunci'] == kw]
            with st.expander(f"🔑 Topik: {kw} ({len(df_kw)} Artikel)"):
                pdf_cache_key = f"pdf_bytes_{kw}"
                if st.button(f"⚙️ Generate/Siapkan PDF", key=f"btn_prep_{kw}", use_container_width=True):
                    pdf_data, err_msg = process_and_get_pdf(kw)
                    if pdf_data:
                        st.session_state[pdf_cache_key] = pdf_data
                        st.success("PDF siap!")
                    else:
                        st.error(err_msg)
                
                if pdf_cache_key in st.session_state:
                    st.download_button(f"📥 Unduh '{kw}'", data=bytes(st.session_state[pdf_cache_key]), file_name=f"Laporan_{kw}.pdf", mime="application/pdf", key=f"dl_{kw}", use_container_width=True)
    else:
        st.info("Belum ada data tersimpan.")

# ================= TAB 3: CLUSTERING & TIMELINE =================
with tab_cluster:
    st.subheader("🧩 Pengelompokan Cerita & Timeline")
    df_for_cluster = db_service.get_latest_scraped_data(limit=500)

    if df_for_cluster.empty:
        st.info("Belum ada data berita untuk clustering.")
    else:
        cluster_keyword_options = list(df_for_cluster["kata_kunci"].dropna().unique())
        selected_cluster_keywords = st.multiselect("Pilih Keyword", options=cluster_keyword_options, default=cluster_keyword_options[:1])
        
        df_to_cluster = df_for_cluster[df_for_cluster["kata_kunci"].isin(selected_cluster_keywords)] if selected_cluster_keywords else df_for_cluster

        if not df_to_cluster.empty:
            clustered_df = clustering_service.cluster(df_to_cluster)
            cluster_summary = clustering_service.build_cluster_summary(clustered_df)
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Artikel", len(clustered_df))
            m2.metric("Cerita Unik", clustered_df["cluster_id"].nunique())
            m3.metric("Multi-Sumber", int((cluster_summary["jumlah_artikel"] > 1).sum()) if not cluster_summary.empty else 0)

            timeline_fig = clustering_service.build_timeline_fig(clustered_df)
            if timeline_fig:
                st.plotly_chart(timeline_fig, use_container_width=True)
