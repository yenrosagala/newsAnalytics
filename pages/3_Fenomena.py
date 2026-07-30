import asyncio
from datetime import datetime
import json
import os
import re

from app.core.auth import render_auth_sidebar
from app.core.config import Config
from app.core.logger import setup_logger
from app.prompts.executive_summary import get_recursive_executive_summary_prompt
from app.recursive_engine import (
    run_recursive_5why_pipeline_with_progress,
    consolidate_bibliography,
    format_bibliography_for_prompt,
    format_level_breakdown_for_prompt,
    validate_citation_diversity,
)
from app.services.ai_service import ai_service
from app.services.database_service import db_service
from app.services.report_service import report_service
import streamlit as st

config = Config()
logger = setup_logger("page_fenomena")

# Memuat File CSS Kustom (jika tersedia)
css_path = "app/assets/style.css"
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Konfigurasi Halaman (Wajib dipanggil pertama kali)
st.set_page_config(page_title="Fenomena & Root Cause", layout="wide", page_icon="🔍")

# Sidebar Navigasi & Informasi Konsisten dengan Halaman Lain
with st.sidebar:
    st.markdown("### ⚡ NewsAnalytics AI")
    st.markdown("---")
    st.page_link("streamlit_app.py", label="Home", icon="🏠")
    st.page_link("pages/1_Scraping.py", label="News Scraper", icon="📥")
    st.page_link("pages/2_Dashboard.py", label="Analytics Dashboard", icon="📊")
    st.page_link("pages/3_Fenomena.py", label="Root Cause Analysis", icon="🔍")
    st.markdown("---")
    st.markdown("### ℹ️ Informasi")
    st.caption(
        "Fitur Recursive 5 Why mengeksplorasi berita secara berlapis guna mengidentifikasi akar permasalahan di balik suatu fenomena."
    )

# Render autentikasi sidebar
render_auth_sidebar()

# Header Halaman Utama dengan UI/UX Modern
st.markdown("# 🔍 Root Cause Analysis")
st.caption("Fenomena & Recursive 5-Why Analysis")
st.markdown(
    "Identifikasi akar masalah secara mendalam berdasarkan temuan berita dan anomali data."
)
st.markdown("---")


def _parse_title_summary_json(raw_text: str, fallback_query: str) -> dict:
    """Parsing defensif untuk output JSON {title, executive_summary} dari AI."""
    if not raw_text:
        return {
            "title": f"Analisis Akar Masalah: {fallback_query}",
            "executive_summary": "",
        }

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
        logger.warning(
            f"Gagal parsing JSON judul+ringkasan dari AI, dipakai sebagai teks polos: {e}"
        )
        return {
            "title": f"Analisis Akar Masalah: {fallback_query}",
            "executive_summary": text,
        }


def _render_level_details(
    level_info: dict, depth: int, url_to_global_number: dict | None = None
):
    """Helper render satu blok level dengan container kartu fitur modern.

    Catatan: sebelumnya kartu ini dibuat dari sepasang st.markdown('<div>')
    ... st.markdown('</div>') terpisah -- pola ini TIDAK benar-benar
    membungkus widget Streamlit asli di antaranya (lihat catatan di CSS),
    sehingga ringkasan/penyebab/bibliografi/keyword level tampil polos DI
    LUAR kartu, dan tag <div> pembuka/penutup sendiri muncul sebagai kotak
    kosong mengambang. Diganti dengan st.container(key=...) yang benar-benar
    membungkus di DOM.
    """
    is_root_cause = depth == 5

    with st.container(key=f"level_card_{depth}"):
        if is_root_cause:
            st.markdown('<span class="root-cause-badge">🎯 Root Cause Level</span>', unsafe_allow_html=True)

        st.markdown(f"#### 📍 Level {depth}: {', '.join(level_info.get('queries_used', []))}")
        st.markdown(f"<p style='color: #94a3b8; margin-bottom: 8px;'><b>Artikel Diekstrak:</b> {level_info.get('articles_found', 0)} artikel</p>", unsafe_allow_html=True)

        if level_info.get("summary"):
            st.markdown(
                f"<p style='color: #cbd5e1;'><b>📝 Ringkasan Level:</b> {level_info['summary']}</p>",
                unsafe_allow_html=True,
            )

        if level_info.get("causes_extracted"):
            st.markdown("<b>🔍 Penyebab Teridentifikasi:</b>", unsafe_allow_html=True)
            for c in level_info["causes_extracted"]:
                st.markdown(f"- 🔴 {c}")

        if level_info.get("bibliography"):
            with st.expander(f"📚 Daftar Pustaka Level {depth}"):
                url_to_global_number_local = url_to_global_number or {}
                for local_idx, bib in enumerate(level_info["bibliography"], 1):
                    num = url_to_global_number_local.get(bib.get("url"), local_idx)
                    st.markdown(
                        f"[{num}] {bib.get('author', 'Tidak diketahui')}. {bib.get('media', '-')}. {bib.get('date', '-')}. **{bib.get('title', 'Tanpa Judul')}**. [Link]({bib.get('url', '#')})"
                    )

        if level_info.get("next_keywords"):
            st.markdown("**➡️ Keyword Turunan:**")
            st.info(" | ".join([f"`{kw}`" for kw in level_info["next_keywords"]]))


# --- STRUKTUR TAB UTAMA ---
tab_recursive, tab_pdf_recursive = st.tabs(
    ["🚀 Jalankan Analisis 5 Why", "📄 Download PDF Laporan Recursive"]
)

with tab_recursive:
    with st.container(key="fenomena_config_card"):
        st.subheader("⚙️ Konfigurasi Analisis Fenomena")
        initial_problem_query = st.text_area(
            "Deskripsi Fenomena / Masalah Utama",
            value=st.session_state.get(
                "last_recursive_query", "Sensus Ekonomi 2026 Papua kendala"
            ),
            key="input_query_tab1",
        )
        depth = st.slider(
            "Kedalaman Analisis (Recursive Level)",
            3,
            7,
            5,
            key="slider_depth_analysis",
        )
        run_analysis = st.button(
            "🚀 Jalankan Recursive 5 Why Analysis",
            type="primary",
            key="btn_run_recursive",
            width="stretch",
        )

    st.markdown("---")

    if run_analysis:
        prog_bar = st.progress(0.0)
        status_container = st.empty()

        try:
            result_tree = asyncio.run(
                run_recursive_5why_pipeline_with_progress(
                    initial_query=initial_problem_query,
                    max_depth=depth,
                    progress_bar=prog_bar,
                    status_text=status_container,
                )
            )

            if not result_tree or not isinstance(result_tree, list):
                status_container.empty()
                prog_bar.empty()
                st.warning(
                    f"⚠️ Analisis dihentikan. Tidak ada artikel yang berhasil diekstrak atau struktur data kosong untuk keyword '{initial_problem_query}'."
                )
            else:
                status_container.text(
                    "Menyusun judul & ringkasan eksekutif komprehensif via AI Service..."
                )

                consolidated_bib = consolidate_bibliography(result_tree)

                prompt_exec = get_recursive_executive_summary_prompt(
                    initial_query=initial_problem_query,
                    level_breakdown=format_level_breakdown_for_prompt(result_tree),
                    numbered_bibliography=format_bibliography_for_prompt(
                        consolidated_bib
                    ),
                )

                ai_title = f"Analisis Akar Masalah: {initial_problem_query}"
                final_executive_summary = ""
                try:
                    raw_response = ai_service.generate(prompt_exec)
                    parsed = _parse_title_summary_json(
                        raw_response, initial_problem_query
                    )
                    ai_title = parsed["title"]
                    final_executive_summary = parsed["executive_summary"]
                except Exception as llm_err:
                    logger.error(
                        f"Gagal menyusun ringkasan eksekutif: {llm_err}"
                    )
                    st.warning(
                        f"⚠️ Gagal menyusun ringkasan eksekutif via AI ({llm_err})."
                    )

                citation_warning = validate_citation_diversity(
                    final_executive_summary, consolidated_bib
                )
                st.session_state["last_citation_warning"] = citation_warning

                st.session_state["last_recursive_result"] = result_tree
                st.session_state["last_recursive_query"] = initial_problem_query
                st.session_state["last_executive_summary"] = (
                    final_executive_summary
                )
                st.session_state["last_report_title"] = ai_title
                st.session_state["last_consolidated_bibliography"] = (
                    consolidated_bib
                )

                try:
                    db_service.save_root_cause_analysis(
                        initial_query=initial_problem_query,
                        result_tree=result_tree,
                        executive_summary=final_executive_summary,
                    )
                except Exception as db_err:
                    logger.warning(
                        f"Gagal menyimpan ke database riwayat: {db_err}"
                    )

                status_container.empty()
                prog_bar.empty()
                st.success(
                    "✅ Analisis Akar Masalah (5 Why) & Penyusunan Laporan Eksekutif Selesai!"
                )

                st.markdown(f"## {ai_title}")
                if final_executive_summary:
                    st.markdown("### 📋 Ringkasan Eksekutif")
                    st.markdown(final_executive_summary)
                    if citation_warning:
                        st.warning(citation_warning)
                    st.divider()

                st.markdown("### 🌳 Hasil Pohon Akar Masalah (Root Cause Tree)")
                url_to_global_number = {
                    b.get("url"): b.get("number") for b in consolidated_bib
                }
                for level_info in result_tree:
                    _render_level_details(
                        level_info, level_info["depth"], url_to_global_number
                    )

        except Exception as e:
            status_container.empty()
            prog_bar.empty()
            st.error(f"Terjadi kesalahan sistem pada pipeline recursive: {e}")
    else:
        stored_result_history = st.session_state.get(
            "last_recursive_result", None
        )

        if not stored_result_history:
            st.markdown(
                """
            <div class="feature-card" style="text-align: center; padding: 48px 24px; border: 2px dashed rgba(0, 240, 255, 0.25);">
                <div style="font-size: 3rem; margin-bottom: 12px;">🔍</div>
                <h3 style="color: #00f0ff;">Belum Ada Analisis yang Dijalankan</h3>
                <p style="color: #94a3b8; max-width: 600px; margin: 0 auto 20px auto;">
                    Masukkan deskripsi fenomena di atas dan klik tombol <b>Jalankan Recursive 5 Why Analysis</b>. 
                </p>
            </div>
            """,
                unsafe_allow_html=True,
            )
        else:
            stored_query_history = st.session_state.get(
                "last_recursive_query", ""
            )
            stored_title_history = st.session_state.get("last_report_title", "")
            stored_exec_summary = st.session_state.get(
                "last_executive_summary", ""
            )

            st.markdown(f"## {stored_title_history or stored_query_history}")
            if stored_exec_summary:
                st.markdown("### 📋 Ringkasan Eksekutif")
                st.markdown(stored_exec_summary)
                stored_citation_warning = st.session_state.get(
                    "last_citation_warning"
                )
                if stored_citation_warning:
                    st.warning(stored_citation_warning)
                st.divider()

            st.markdown(
                "### 🌳 Hasil Pohon Akar Masalah Terakhir (Root Cause Tree)"
            )
            stored_bib_for_render = st.session_state.get(
                "last_consolidated_bibliography", []
            )
            url_to_global_number = {
                b.get("url"): b.get("number") for b in stored_bib_for_render
            }
            for level_info in stored_result_history:
                _render_level_details(
                    level_info, level_info["depth"], url_to_global_number
                )

with tab_pdf_recursive:
    st.subheader("📄 Cetak & Download PDF Laporan Recursive 5-Why")
    stored_result = st.session_state.get("last_recursive_result", None)
    stored_query = st.session_state.get(
        "last_recursive_query", "Analisis Fenomena"
    )
    stored_exec_summary = st.session_state.get("last_executive_summary", "")
    stored_title = st.session_state.get(
        "last_report_title", f"Analisis Akar Masalah: {stored_query}"
    )
    stored_bibliography = st.session_state.get(
        "last_consolidated_bibliography", []
    )

    if not stored_result:
        st.warning(
            "⚠️ Belum ada hasil analisis rekursif yang tersedia. Silakan jalankan analisis di tab sebelumnya."
        )
    else:
        st.info(f"💡 Laporan komprehensif **'{stored_title}'** siap dicetak.")

        if st.button(
            "📥 Proses File PDF Recursive",
            type="primary",
            key="btn_gen_pdf_recursive",
            width="stretch",
        ):
            with st.spinner(
                "Menyiapkan dokumen PDF laporan eksekutif lengkap..."
            ):
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
                            width="stretch",
                        )
                except Exception as pdf_err:
                    st.error(f"Gagal memproses file PDF: {pdf_err}")
