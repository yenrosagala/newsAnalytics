import streamlit as st
import asyncio
import pandas as pd
from datetime import datetime
from urllib.parse import urlparse
from app.services.database_service import db_service
from app.services.ai_service import ai_service
from app.core.config import Config
from app.core.logger import setup_logger
from app.generate_pdf import generate_pdf_report
from app.prompts.executive_summary import get_executive_summary_prompt
from app.core.auth import require_login


config = Config()
logger = setup_logger("page_fenomena")

st.set_page_config(page_title="FlashNews: Root Cause Analysis", layout="wide", page_icon="🧠")

# --- PROTEKSI HALAMAN ---
require_login()

try:
    with open("app/assets/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

st.title("🧠 FlashNews: Root Cause Analysis")
st.write("Eksplorasi mendalam mengenai akar masalah dan tren fenomena berita menggunakan pendekatan rekursif 5-Why cerdas.")

# Sidebar Status Pengguna
st.sidebar.header("🔑 Status Pengguna")
is_admin = st.session_state.get("role") == "admin"
if is_admin:
    st.sidebar.success("Masuk sebagai: **Admin**\n\n*(Ganti akun via Homepage)*")
else:
    st.sidebar.info("Masuk sebagai: **General User**\n\n*(Ganti akun via Homepage)*")

st.sidebar.markdown("---")
st.sidebar.markdown("### ℹ️ Informasi")
st.sidebar.caption("Fitur Recursive 5 Why mengeksplorasi berita secara berlapis guna mengidentifikasi akar permasalahan di balik suatu fenomena.")

tab_recursive, tab_pdf_recursive = st.tabs(["🚀 Jalankan Analisis 5 Why", "📄 Download PDF Laporan Recursive"])

with tab_recursive:
    st.caption("Sistem akan melakukan pencarian dan penelusuran berita bertingkat secara otomatis hingga 5 level untuk menemukan akar masalah.")
    initial_problem_query = st.text_input("Masukkan Masalah Utama / Topik Awal:", value="Sensus Ekonomi 2026 Papua kendala", key="input_query_tab1")

    if st.button("🚀 Jalankan Recursive 5 Why Analysis", type="primary", key="btn_run_recursive"):
        prog_bar = st.progress(0.0)
        status_container = st.empty()
        
        try:
            from app.recursive_engine import run_recursive_5why_pipeline_with_progress
            
            result_tree = asyncio.run(
                run_recursive_5why_pipeline_with_progress(
                    initial_query=initial_problem_query, max_depth=5, progress_bar=prog_bar, status_text=status_container
                )
            )
            
            if not result_tree or not isinstance(result_tree, list):
                status_container.empty()
                prog_bar.empty()
                st.warning(f"⚠️ Analisis dihentikan. Tidak ada artikel yang berhasil diekstrak atau struktur data kosong untuk keyword '{initial_problem_query}'. Silakan coba keyword lain yang lebih umum.")
            else:
                status_container.text("Menyusun ringkasan eksekutif komprehensif alur 5-Why via AI Service...")
                
                comprehensive_corpus = []
                for lvl in result_tree:
                    comprehensive_corpus.append(f"--- LEVEL {lvl['depth']} (Query: {', '.join(lvl['queries_used'])}) ---")
                    comprehensive_corpus.append(f"Ringkasan: {lvl.get('summary', '')}")
                    comprehensive_corpus.append("Penyebab Teridentifikasi:")
                    for c in lvl.get("causes_extracted", []):
                        comprehensive_corpus.append(f"- {c}")
                    comprehensive_corpus.append("-" * 30)
                
                concatenated_content = "\n".join(comprehensive_corpus)
                
                prompt_exec = get_executive_summary_prompt(
                    data_context=f"Analisis Akar Masalah (Root Cause 5-Why) Bertingkat untuk Topik: {initial_problem_query}",
                    display_title_keyword=initial_problem_query,
                    date_range_str=datetime.now().strftime('%d %B %Y'),
                    t_media_str="Multi-Source Recursive Engine",
                    concatenated_content=concatenated_content,
                    catatan_regenerate=""
                )
                
                final_executive_summary = ""
                if ai_service.client:
                    # 🔄 Mekanisme Rotasi Ganda (Model & API Key) dengan Retry Otomatis saat Terkena Limit (429)
                    max_attempts = (len(ai_service.api_keys) * len(ai_service.models_list)) if getattr(ai_service, 'api_keys', None) else 5
                    attempt = 0
                    success = False

                    while attempt < max_attempts and not success:
                        try:
                            response = ai_service.client.models.generate_content(
                                model=ai_service.model_name, 
                                contents=prompt_exec
                            )
                            final_executive_summary = response.text
                            success = True
                        except Exception as llm_err:
                            err_str = str(llm_err)
                            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                                logger.warning(f"⚠️ Limit tercapai pada Model {ai_service.model_name}. Mencoba rotasi otomatis...")
                                
                                # Rotasi model terlebih dahulu, jika habis putar kunci API
                                rotated_model = ai_service.rotate_model() if hasattr(ai_service, 'rotate_model') else False
                                if not rotated_model or getattr(ai_service, 'active_model_index', 0) == 0:
                                    if hasattr(ai_service, 'rotate_key_for_level'):
                                        ai_service.rotate_key_for_level(attempt + 1)
                                    elif hasattr(ai_service, 'rotate_key'):
                                        ai_service.rotate_key()
                                        
                                attempt += 1
                            else:
                                logger.error(f"Gagal menyusun ringkasan: {llm_err}")
                                break
                    
                    # Fallback darurat jika seluruh rotasi habis
                    if not final_executive_summary:
                        final_executive_summary = concatenated_content
                else:
                    final_executive_summary = concatenated_content

                st.session_state["last_recursive_result"] = result_tree
                st.session_state["last_recursive_query"] = initial_problem_query
                st.session_state["last_executive_summary"] = final_executive_summary
                
                try:
                    db_service.save_root_cause_analysis(
                        initial_query=initial_problem_query,
                        result_tree=result_tree,
                        executive_summary=final_executive_summary
                    )
                except Exception as db_err:
                    logger.warning(f"Gagal menyimpan ke database riwayat: {db_err}")
                
                status_container.empty()
                prog_bar.empty()
                st.success("✅ Analisis Akar Masalah (5 Why) & Penyusunan Laporan Eksekutif Selesai!")
                
                for level_info in result_tree:
                    depth = level_info["depth"]
                    st.markdown(f"### 📍 Level {depth} (Kedalaman {depth} dari 5)")
                    st.write(f"**Query Pencarian:** `{', '.join(level_info['queries_used'])}`")
                    st.write(f"**Artikel Diekstrak:** {level_info['articles_found']} artikel")
                    
                    if level_info.get("summary"):
                        st.markdown("**📝 Ringkasan Level:**")
                        st.write(level_info["summary"])
                    if level_info["causes_extracted"]:
                        st.markdown("**🔍 Penyebab Teridentifikasi:**")
                        for c in level_info["causes_extracted"]:
                            st.markdown(f"- 🔴 {c}")
                    if level_info.get("bibliography"):
                        with st.expander(f"📚 Daftar Pustaka Level {depth}"):
                            for idx, bib in enumerate(level_info["bibliography"], 1):
                                st.markdown(f"[{idx}] {bib.get('author', 'Tidak diketahui')}. {bib['media']}. {bib['date']}. **{bib['title']}**. [Link]({bib['url']})")
                    if level_info["next_keywords"]:
                        st.markdown("**➡️ Keyword Turunan:**")
                        st.info(" | ".join([f"`{kw}`" for kw in level_info["next_keywords"]]))
                    st.divider()

        except Exception as e:
            status_container.empty()
            prog_bar.empty()
            st.error(f"Terjadi kesalahan sistem pada pipeline recursive: {e}")

with tab_pdf_recursive:
    st.subheader("📄 Cetak & Download PDF Laporan Recursive 5-Why")
    stored_result = st.session_state.get("last_recursive_result", None)
    stored_query = st.session_state.get("last_recursive_query", "Analisis Fenomena")
    stored_exec_summary = st.session_state.get("last_executive_summary", "")

    if not stored_result:
        st.warning("⚠️ Belum ada hasil analisis rekursif yang tersedia. Silakan jalankan analisis di tab sebelumnya.")
    else:
        st.info(f"💡 Laporan komprehensif untuk topik: **'{stored_query}'** siap dicetak.")

        insights_list = []
        total_articles_all = sum([lvl["articles_found"] for lvl in stored_result])
        insights_list.append(f"Total keseluruhan artikel tervalidasi dari penelusuran berjenjang adalah {total_articles_all} berita.")
        insights_list.append(f"Topik utama investigasi: {stored_query}")
        insights_list.append(f"Kedalaman analisis (Levels): {len(stored_result)}")

        # --- PEMBENTUKAN KONTROL STRUKTUR LAPORAN PDF YANG LENGKAP & TERSTRUKTUR ---
        pdf_sections = []
        
        # 1. Ringkasan Eksekutif Komprehensif
        pdf_sections.append("## Ringkasan Eksekutif Komprehensif")
        pdf_sections.append(stored_exec_summary)
        pdf_sections.append("\n---\n")

        # 2. Analisis Setiap Level secara Mendalam
        pdf_sections.append("## Analisis Per Level 5-Why")
        for lvl in stored_result:
            depth = lvl["depth"]
            queries_str = ", ".join(lvl.get("queries_used", []))
            summary_lvl = lvl.get("summary", "Tidak ada ringkasan level.")
            causes_lvl = lvl.get("causes_extracted", [])
            
            pdf_sections.append(f"### Level {depth}")
            pdf_sections.append(f"**Query Pencarian:** `{queries_str}`")
            pdf_sections.append(f"**Artikel Tervalidasi:** {lvl.get('articles_found', 0)} artikel")
            pdf_sections.append(f"**Ringkasan Level:**\n{summary_lvl}")
            
            if causes_lvl:
                pdf_sections.append("**Penyebab Terindikasi:**")
                for c in causes_lvl:
                    pdf_sections.append(f"- {c}")
            pdf_sections.append("\n")

        # 3. Daftar Pustaka Komprehensif Menggabungkan Seluruh Pustaka Setiap Level
        pdf_sections.append("## Daftar Pustaka Komprehensif")
        bib_counter = 1
        for lvl in stored_result:
            if lvl.get("bibliography"):
                for bib in lvl["bibliography"]:
                    url_link = bib.get('url', '#')
                    media_name = bib.get('media', '')
                    if url_link and ("http://" in url_link or "https://" in url_link):
                        parsed = urlparse(url_link)
                        domain = parsed.netloc.lower()
                        if domain.startswith("www."):
                            domain = domain[4:]
                        media_domain = domain.split(":")[0].split("/")[0] if domain else media_name
                    else:
                        media_domain = str(media_name).split(",")[-1].strip().replace("www.", "") if media_name else "Media Nasional"

                    pub_date = str(bib.get('date', datetime.now().strftime('%Y-%m-%d')))
                    if len(pub_date) >= 10 and pub_date[:4].isdigit():
                        pub_date = pub_date[:10]

                    title = bib.get('title', 'Tanpa Judul')
                    author = bib.get('author', 'Tidak diketahui')

                    bib_entry = f"[{bib_counter}] {author}. {media_domain}. {pub_date}. {title}. {url_link}"
                    pdf_sections.append(bib_entry)
                    bib_counter += 1

        full_text_for_pdf = "\n".join(pdf_sections)
        df_dummy = db_service.get_latest_scraped_data(limit=10)

        if st.button("📥 Proses File PDF Recursive", type="primary", key="btn_gen_pdf_recursive"):
            with st.spinner("Menyiapkan dokumen PDF laporan eksekutif lengkap dengan analisis per level dan daftar pustaka gabungan..."):
                try:
                    pdf_bytes = generate_pdf_report(
                        filtered_df=df_dummy,
                        insights=insights_list,
                        target_keyword=f"Root Cause Analysis 5-Why: {stored_query}",
                        date_range_str=datetime.now().strftime('%d %B %Y'),
                        t_media_str="Multi-Source Recursive Engine",
                        summary_text=full_text_for_pdf
                    )
                    
                    if pdf_bytes:
                        st.success("Dokumen PDF laporan berhasil dibuat!")
                        st.download_button(
                            label=f"📄 Download PDF Laporan '{stored_query}'",
                            data=bytes(pdf_bytes),
                            file_name=f"Laporan_Executive_5Why_{stored_query.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                except Exception as pdf_err:
                    st.error(f"Gagal memproses file PDF: {pdf_err}")

# --- TAMPILKAN RIWAYAT / ROOT CAUSE ANALISIS SEBELUMNYA ---
stored_result_history = st.session_state.get("last_recursive_result", None)
stored_query_history = st.session_state.get("last_recursive_query", "")

if stored_result_history:
    with st.expander(f"📂 Riwayat Analisis Sebelumnya: '{stored_query_history}'", expanded=False):
        st.info(f"Menampilkan hasil investigasi rekursif terakhir untuk topik: **{stored_query_history}**")
        
        for level_info in stored_result_history:
            depth = level_info["depth"]
            st.markdown(f"### 📍 Level {depth}")
            st.write(f"**Query Pencarian:** `{', '.join(level_info['queries_used'])}`")
            st.write(f"**Artikel Diekstrak:** {level_info['articles_found']} artikel")
            
            if level_info.get("summary"):
                st.markdown("**📝 Ringkasan Level:**")
                st.write(level_info["summary"])
            if level_info["causes_extracted"]:
                st.markdown("**🔍 Penyebab Teridentifikasi:**")
                for c in level_info["causes_extracted"]:
                    st.markdown(f"- 🔴 {c}")
            if level_info.get("bibliography"):
                with st.expander(f"📚 Daftar Pustaka Level {depth}"):
                    for idx, bib in enumerate(level_info["bibliography"], 1):
                        url_link = bib.get('url', '#')
                        media_name = bib.get('media', '')
                        if url_link and ("http://" in url_link or "https://" in url_link):
                            parsed = urlparse(url_link)
                            domain = parsed.netloc.lower()
                            if domain.startswith("www."):
                                domain = domain[4:]
                            media_domain = domain.split(":")[0].split("/")[0] if domain else media_name
                        else:
                            media_domain = str(media_name).split(",")[-1].strip().replace("www.", "") if media_name else "Media Nasional"

                        pub_date = str(bib.get('date', '-'))
                        if len(pub_date) >= 10 and pub_date[:4].isdigit():
                            pub_date = pub_date[:10]
                            
                        title = bib.get('title', 'Tanpa Judul')
                        author = bib.get('author', 'Tidak diketahui')
                        st.markdown(f"[{idx}] {author}. {media_domain}. {pub_date}. **{title}**. {url_link}")
            st.divider()