import streamlit as st
import pandas as pd
from datetime import datetime
import os

from app.services.scraper_service import scraper_service
from app.services.database_service import db_service 
from app.services.ai_service import ai_service
from app.core.config import Config  
from app.core.logger import setup_logger
from app.generate_pdf import generate_pdf_report
from app.prompts.executive_summary import get_executive_summary_prompt
from app.core.auth import render_auth_sidebar

# Inisialisasi konfigurasi
config = Config()
logger = setup_logger("page_scraping")



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
    st.page_link("streamlit_app.py", label="Home Dashboard", icon="🏠")
    st.page_link("pages/1_Scraping.py", label="News Insight", icon="📥")
    st.page_link("pages/2_Dashboard.py", label="Analytics & Metrics", icon="📊")
    st.page_link("pages/3_Fenomena.py", label="Fenomena (5-Why)", icon="🔍")
    st.markdown("---")
    st.markdown("### ℹ️ Informasi")
    st.caption("Fitur mengeksplorasi berita dan memberikan insight secara menyeluruh.")

# Konfigurasi Halaman (Wajib dipanggil pertama kali)
st.set_page_config(page_title="Scraping & Database", layout="wide", page_icon="📥")

# Render autentikasi sidebar
render_auth_sidebar()

# Header Halaman Utama dengan UI/UX Modern
st.markdown("# 📥 Google News Scraping & Executive Summary")
st.markdown("Masukkan kata kunci untuk mengambil data berita terbaru dan kelola database executive summary.")
st.markdown("---")

# Variabel status admin
is_admin = st.session_state.get("role") == "admin"

# --- BAGIAN UTAMA: FORM PARAMETER SCRAPING BERITA ---
with st.container():
    st.markdown('<div class="feature-card">', unsafe_allow_html=True)
    st.subheader("⚙️ Parameter Pencarian Berita")
    st.write("Masukkan topik atau kata kunci berita (Pencarian otomatis difilter dari 1 Januari 2026).")
    
    with st.form("scraping_form"):
        keyword = st.text_input("Kata Kunci (Keyword):", st.session_state.get("current_keyword", "Transformasi Digital Indonesia"))
        
        col_a, col_b = st.columns(2)
        with col_a:
            num_results = st.number_input("Jumlah Maksimal Artikel:", min_value=5, max_value=50, value=config.DEFAULT_NUM_RESULTS, step=5)
        with col_b:
            sentiment_filter = st.selectbox("Filter Sentimen (Opsional Tampilan)", ["Semua", "Positif", "Netral", "Negatif"])
            
        submit_scraping = st.form_submit_button("🚀 Jalankan Scraping & Generate Summary", use_container_width=True, type="primary")
    
    st.markdown('</div>', unsafe_allow_html=True)

if submit_scraping:
    if not keyword.strip():
        st.error("Keyword tidak boleh kosong!")
    else:
        st.session_state["current_keyword"] = keyword
        
        st.write(f"**Proses Scraping Berjalan:** '{keyword}'")
        
        # Membuat penampung UI untuk Progress Bar dan URL Real-time
        progress_bar = st.progress(0.0)
        status_container = st.empty()
        
        # Meneruskan status_container dan progress_bar ke service (Region difokuskan murni ke ID)
        saved_count = scraper_service.execute_scraping_workflow(
            keyword=keyword, 
            limit=num_results, 
            region="ID",
            status_container=status_container,
            progress_bar=progress_bar
        )
        
        if saved_count > 0:
            status_container.success(f"✅ Berhasil mengekstrak dan menyimpan {saved_count} artikel baru!")
            progress_bar.empty() # Sembunyikan progress bar setelah selesai
            st.session_state["trigger_auto_summary"] = keyword
        else:
            status_container.warning("Tidak ada berita baru yang ditemukan atau gagal memproses data.")
            progress_bar.empty()
            st.session_state["trigger_auto_summary"] = None

st.divider()

# --- FUNGSI HELPER UNTUK MENDAPATKAN ATAU MEN-GENERATE SUMMARY KE DB & PDF ---
def process_and_get_pdf(target_keyword):
    df_all = db_service.get_latest_scraped_data(limit=1000)
    if df_all.empty:
        return None, "Data berita kosong."
        
    filtered_data = df_all[df_all['kata_kunci'].astype(str).str.contains(target_keyword, case=False, na=False)]
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
        
        if ai_service.client:
            try:
                response = ai_service.client.models.generate_content(
                    model=ai_service.model_name,
                    contents=prompt
                )
                summary_text_result = response.text
                
                db_service.save_executive_summary_to_db(
                    kata_kunci=target_keyword,
                    rentang_waktu=date_range_str,
                    hasil_summary=summary_text_result
                )
            except Exception as ai_err:
                return None, f"Gagal menghasilkan ringkasan via AI: {ai_err}"
        else:
            return None, "AI Service / Gemini Client belum terkonfigurasi dengan benar."
            
    insights_list = []
    if "Sentimen" in filtered_data.columns:
        s_counts = filtered_data["Sentimen"].value_counts()
        total_s = len(filtered_data)
        pos_cnt = s_counts.get("POSITIVE", 0) + s_counts.get("Positif", 0) + s_counts.get("Positive", 0)
        neg_cnt = s_counts.get("NEGATIVE", 0) + s_counts.get("Negatif", 0) + s_counts.get("Negative", 0)
        p_pos = (pos_cnt / total_s * 100) if total_s > 0 else 0
        p_neg = (neg_cnt / total_s * 100) if total_s > 0 else 0
        insights_list.append(f"Sentimen Positif mendominasi sebesar {p_pos:.1f}%" if p_pos >= p_neg else f"Sentimen Negatif mendominasi sebesar {p_neg:.1f}%")
    
    if not t_media.empty:
        insights_list.append(f"Media kontributor terbanyak adalah {t_media.index[0]} dengan {t_media.values[0]} artikel.")
    insights_list.append(f"Total keseluruhan artikel yang dianalisis pada topik ini adalah {len(filtered_data)} berita.")
    
    pdf_bytes = generate_pdf_report(
        filtered_df=filtered_data,
        insights=insights_list,
        target_keyword=target_keyword,
        date_range_str=date_range_str,
        t_media_str=t_media_str,
        summary_text=summary_text_result
    )
    
    return pdf_bytes, None

# --- BAGIAN OTOMATIS DOWNLOAD SETELAH SCRAPING ---
active_keyword_to_summarize = st.session_state.get("trigger_auto_summary")

if active_keyword_to_summarize:
    st.subheader(f"📥 Laporan Executive Summary Siap: '{active_keyword_to_summarize}'")
    with st.spinner("Menyiapkan dokumen PDF laporan resmi..."):
        pdf_data, err_msg = process_and_get_pdf(active_keyword_to_summarize)
        if pdf_data:
            st.success("Laporan analisis berhasil disiapkan dari sistem.")
            st.download_button(
                label=f"📄 Download PDF Laporan '{active_keyword_to_summarize}'",
                data=bytes(pdf_data),
                file_name=f"Laporan_Executive_Summary_{active_keyword_to_summarize.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        else:
            st.error(err_msg)

st.divider()

# --- BAGIAN DAFTAR EXECUTIVE SUMMARY TERAKHIR (DENGAN LAYOUT BARIS RAPI) ---
st.subheader("🗄️ Daftar Executive Summary Tersimpan (Database)")
df_latest = db_service.get_latest_scraped_data(limit=5)

if not df_latest.empty:
    unique_keywords = df_latest['kata_kunci'].dropna().unique()
    
    for kw in unique_keywords:
        df_kw = df_latest[df_latest['kata_kunci'] == kw]
        total_art = len(df_kw)
        
        # Menggunakan struktur expander dengan tata letak kolom yang bersih ala UI/UX baru
        with st.expander(f"🔑 Topik / Kata Kunci: {kw} ({total_art} Artikel Terkait)"):
            col_info1, col_info2 = st.columns([3, 1])
            with col_info1:
                st.markdown(f"**Status Dokumen:** Siap Diunduh")
                st.markdown(f"**Total Artikel Terkumpul:** {total_art} entri")
            with col_info2:
                if st.button(f"📥 Unduh PDF", key=f"btn_dl_{kw.replace(' ', '_')}", use_container_width=True):
                    with st.spinner(f"Memproses file PDF untuk '{kw}'..."):
                        pdf_data, err_msg = process_and_get_pdf(kw)
                        if pdf_data:
                            st.download_button(
                                label=f"Klik Untuk Unduh File '{kw}'",
                                data=bytes(pdf_data),
                                file_name=f"Laporan_Executive_Summary_{kw.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf",
                                mime="application/pdf",
                                key=f"dl_action_{kw.replace(' ', '_')}",
                                use_container_width=True
                            )
                        else:
                            st.error(err_msg)
        st.markdown("<hr style='margin: 5px 0; border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
else:
    st.info("Belum ada data berita tersimpan di database.")