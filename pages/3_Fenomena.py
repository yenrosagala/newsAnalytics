import streamlit as st
import asyncio
import json
import re
from datetime import datetime

from app.services.database_service import db_service
from app.services.ai_service import ai_service
from app.services.report_service import report_service
from app.core.config import Config
from app.core.logger import setup_logger
from app.prompts.executive_summary import get_recursive_executive_summary_prompt
from app.core.auth import render_auth_sidebar
from app.recursive_engine import (
    run_recursive_5why_pipeline_with_progress,
    consolidate_bibliography,
    format_bibliography_for_prompt,
    format_level_breakdown_for_prompt,
)

config = Config()
logger = setup_logger("page_fenomena")

st.set_page_config(page_title="FlashNews: Root Cause Analysis", layout="wide", page_icon="🧠")

# Halaman ini terbuka untuk pengguna umum -- tidak perlu login.
render_auth_sidebar()

try:
    with open("app/assets/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

st.title("🧠 FlashNews: Root Cause Analysis")
st.write("Eksplorasi mendalam mengenai akar masalah dan tren fenomena berita menggunakan pendekatan rekursif 5-Why cerdas.")

st.sidebar.markdown("### ℹ️ Informasi")
st.sidebar.caption("Fitur Recursive 5 Why mengeksplorasi berita secara berlapis guna mengidentifikasi akar permasalahan di balik suatu fenomena.")


def _parse_title_summary_json(raw_text: str, fallback_query: str) -> dict:
    """Parsing defensif untuk output JSON {title, executive_summary} dari AI.

    Kalau AI gagal mengembalikan JSON valid (mis. karena error API atau
    format tak terduga), sistem tetap menghasilkan judul & ringkasan yang
    masuk akal alih-alih menampilkan JSON mentah/kosong ke pengguna.
    """
    if not raw_text:
        return {"title": f"Analisis Akar Masalah: {fallback_query}", "executive_summary": ""}

    text = raw_text.strip()
    text = re.sub(r"^```(json)?", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text).strip()

    try:
        data = json.loads(text)
        title = (data.get("title") or "").strip()
        summary = (data.get("executive_summary") or "").strip()
        if not title:
            title = f"Analisis Akar Masalah: {fallback_query}"
        return {"title": title, "executive_summary": summary}
    except Exception as e:
        logger.warning(f"Gagal parsing JSON judul+ringkasan dari AI, dipakai sebagai teks polos: {e}")
        return {"title": f"Analisis Akar Masalah: {fallback_query}", "executive_summary": text}


def _render_level_details(level_info: dict, depth: int):
    """Helper render satu blok level (dipakai di tab hasil baru & di riwayat,
    supaya tidak ada logic tampilan yang terduplikasi)."""
    st.markdown(f"### 📍 Level {depth}")
    st.write(f"**Query Pencarian:** `{', '.join(level_info['queries_used'])}`")
    st.write(f"**Artikel Diekstrak:** {level_info['articles_found']} artikel")

    if level_info.get("summary"):
        st.markdown("**📝 Ringkasan Level:**")
        st.write(level_info["summary"])
    if level_info.get("causes_extracted"):
        st.markdown("**🔍 Penyebab Teridentifikasi:**")
        for c in level_info["causes_extracted"]:
            st.markdown(f"- 🔴 {c}")
    if level_info.get("bibliography"):
        with st.expander(f"📚 Daftar Pustaka Level {depth}"):
            for idx, bib in enumerate(level_info["bibliography"], 1):
                st.markdown(f"[{idx}] {bib.get('author', 'Tidak diketahui')}. {bib.get('media', '-')}. {bib.get('date', '-')}. **{bib.get('title', 'Tanpa Judul')}**. [Link]({bib.get('url', '#')})")
    if level_info.get("next_keywords"):
        st.markdown("**➡️ Keyword Turunan:**")
        st.info(" | ".join([f"`{kw}`" for kw in level_info["next_keywords"]]))
    st.divider()


tab_recursive, tab_pdf_recursive = st.tabs(["🚀 Jalankan Analisis 5 Why", "📄 Download PDF Laporan Recursive"])

with tab_recursive:
    st.caption("Sistem akan melakukan pencarian dan penelusuran berita bertingkat secara otomatis hingga 5 level untuk menemukan akar masalah.")
    initial_problem_query = st.text_input("Masukkan Masalah Utama / Topik Awal:", value="Sensus Ekonomi 2026 Papua kendala", key="input_query_tab1")

    if st.button("🚀 Jalankan Recursive 5 Why Analysis", type="primary", key="btn_run_recursive"):
        prog_bar = st.progress(0.0)
        status_container = st.empty()

        try:
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
                status_container.text("Menyusun judul & ringkasan eksekutif komprehensif via AI Service...")

                # Daftar pustaka dikonsolidasi & DINOMORI SISTEM (bukan oleh AI) --
                # supaya sitasi [n] di ringkasan eksekutif pasti cocok dengan
                # Daftar Pustaka final di PDF.
                consolidated_bib = consolidate_bibliography(result_tree)

                prompt_exec = get_recursive_executive_summary_prompt(
                    initial_query=initial_problem_query,
                    level_breakdown=format_level_breakdown_for_prompt(result_tree),
                    numbered_bibliography=format_bibliography_for_prompt(consolidated_bib),
                )

                ai_title = f"Analisis Akar Masalah: {initial_problem_query}"
                final_executive_summary = ""
                if ai_service.client:
                    try:
                        raw_response = ai_service.generate(prompt_exec)
                        parsed = _parse_title_summary_json(raw_response, initial_problem_query)
                        ai_title = parsed["title"]
                        final_executive_summary = parsed["executive_summary"]
                    except Exception as llm_err:
                        logger.error(f"Gagal menyusun ringkasan eksekutif: {llm_err}")
                        st.warning(f"⚠️ Gagal menyusun ringkasan eksekutif via AI ({llm_err}). Analisis per-level tetap tersedia di bawah.")
                else:
                    st.warning("⚠️ AI Service belum terkonfigurasi -- ringkasan eksekutif tidak dapat dibuat, tapi analisis per-level tetap tersedia di bawah.")

                st.session_state["last_recursive_result"] = result_tree
                st.session_state["last_recursive_query"] = initial_problem_query
                st.session_state["last_executive_summary"] = final_executive_summary
                st.session_state["last_report_title"] = ai_title
                st.session_state["last_consolidated_bibliography"] = consolidated_bib

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

                st.markdown(f"## {ai_title}")
                if final_executive_summary:
                    st.markdown("### 📋 Ringkasan Eksekutif")
                    st.markdown(final_executive_summary)
                    st.divider()

                st.markdown("### 🔬 Analisis Bertingkat per Level")
                for level_info in result_tree:
                    _render_level_details(level_info, level_info["depth"])

        except Exception as e:
            status_container.empty()
            prog_bar.empty()
            st.error(f"Terjadi kesalahan sistem pada pipeline recursive: {e}")

with tab_pdf_recursive:
    st.subheader("📄 Cetak & Download PDF Laporan Recursive 5-Why")
    stored_result = st.session_state.get("last_recursive_result", None)
    stored_query = st.session_state.get("last_recursive_query", "Analisis Fenomena")
    stored_exec_summary = st.session_state.get("last_executive_summary", "")
    stored_title = st.session_state.get("last_report_title", f"Analisis Akar Masalah: {stored_query}")
    stored_bibliography = st.session_state.get("last_consolidated_bibliography", [])

    if not stored_result:
        st.warning("⚠️ Belum ada hasil analisis rekursif yang tersedia. Silakan jalankan analisis di tab sebelumnya.")
    else:
        st.info(f"💡 Laporan komprehensif **'{stored_title}'** siap dicetak.")
        st.caption(
            f"Kedalaman: {len(stored_result)} level  |  "
            f"Total artikel: {sum(lvl['articles_found'] for lvl in stored_result)}  |  "
            f"Total sumber pustaka: {len(stored_bibliography)}"
        )

        if st.button("📥 Proses File PDF Recursive", type="primary", key="btn_gen_pdf_recursive"):
            with st.spinner("Menyiapkan dokumen PDF laporan eksekutif lengkap..."):
                try:
                    pdf_bytes = report_service.generate_recursive_pdf(
                        title=stored_title,
                        executive_summary=stored_exec_summary,
                        initial_query=stored_query,
                        result_tree=stored_result,
                        consolidated_bibliography=stored_bibliography,
                    )

                    if pdf_bytes:
                        st.success("Dokumen PDF laporan berhasil dibuat!")
                        st.download_button(
                            label=f"📄 Download PDF: {stored_title[:60]}",
                            data=pdf_bytes,
                            file_name=f"Laporan_RootCause_5Why_{stored_query.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                except Exception as pdf_err:
                    st.error(f"Gagal memproses file PDF: {pdf_err}")

# --- TAMPILKAN RIWAYAT / ROOT CAUSE ANALISIS SEBELUMNYA ---
stored_result_history = st.session_state.get("last_recursive_result", None)
stored_query_history = st.session_state.get("last_recursive_query", "")
stored_title_history = st.session_state.get("last_report_title", "")

if stored_result_history:
    with st.expander(f"📂 Riwayat Analisis Sebelumnya: '{stored_title_history or stored_query_history}'", expanded=False):
        st.info(f"Menampilkan hasil investigasi rekursif terakhir untuk topik: **{stored_query_history}**")
        for level_info in stored_result_history:
            _render_level_details(level_info, level_info["depth"])