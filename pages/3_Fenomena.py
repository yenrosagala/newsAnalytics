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
    build_evidence_graph_data,
)
from app.services.ai_service import ai_service
from app.services.database_service import db_service
from app.services.report_service import report_service
from app.services.evidence_graph import build_evidence_graph_fig
import streamlit as st

config = Config()
logger = setup_logger("page_fenomena")

# Memuat File CSS Kustom (jika tersedia)
css_path = "app/assets/style.css"
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Konfigurasi Halaman (Wajib dipanggil pertama kali)
st.set_page_config(page_title="AI Investigator", layout="wide", page_icon="🕵️")

# Sidebar Navigasi & Informasi Konsisten dengan Halaman Lain
with st.sidebar:
    st.markdown("### ⚡ NewsAnalytics AI")
    st.markdown("---")
    st.page_link("streamlit_app.py", label="Home", icon="🏠")
    st.page_link("pages/1_Scraping.py", label="AI Understanding", icon="📥")
    st.page_link("pages/2_Dashboard.py", label="Analytics Dashboard", icon="📊")
    st.page_link("pages/3_Fenomena.py", label="AI Investigator", icon="🕵️")
    st.markdown("---")
    st.markdown("### ℹ️ Informasi")
    st.caption(
        "AI Investigator menelusuri berita secara berlapis (Recursive 5-Why) untuk "
        "mengidentifikasi akar permasalahan, lengkap dengan evidence graph & skor keyakinan."
    )

# Render autentikasi sidebar
render_auth_sidebar()

# Header Halaman Utama dengan UI/UX Modern
st.markdown("# 🕵️ AI Investigator")
st.caption("Recursive Root Cause Analysis · Evidence Graph · Confidence Scoring")
st.markdown(
    "Telusuri akar masalah secara mendalam berdasarkan temuan berita, lengkap dengan "
    "peta bukti (evidence graph) dan skor keyakinan per penyebab, lalu ringkas hasilnya "
    "menjadi Executive Intelligence Brief siap-pakai."
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
    level_info: dict,
    depth: int,
    total_levels: int,
    url_to_global_number: dict | None = None,
):
    """Helper render satu blok level sebagai expander yang bisa dilipat,
    supaya banyak level tidak membuat halaman jadi panjang & padat.
    Level pertama dibuka otomatis; level lainnya terlipat sampai diklik.
    """
    is_root_cause = depth == total_levels
    root_badge = "🎯 " if is_root_cause else ""
    expander_label = f"{root_badge}Level {depth}: {', '.join(level_info.get('queries_used', []))}"

    with st.expander(expander_label, expanded=(depth == 1)):
        if is_root_cause:
            st.markdown('<span class="root-cause-badge">🎯 Root Cause Level</span>', unsafe_allow_html=True)

        st.markdown(f"<p style='color: #94a3b8; margin-bottom: 8px;'><b>Artikel Diekstrak:</b> {level_info.get('articles_found', 0)} artikel</p>", unsafe_allow_html=True)

        if level_info.get("summary"):
            st.markdown(
                f"<p style='color: #cbd5e1;'><b>📝 Ringkasan Level:</b> {level_info['summary']}</p>",
                unsafe_allow_html=True,
            )

        if level_info.get("causes_extracted"):
            st.markdown("<b>🔍 Penyebab Teridentifikasi (dengan Skor Keyakinan):</b>", unsafe_allow_html=True)
            _tier_colors = {"Tinggi": "#10B981", "Sedang": "#F59E0B", "Rendah": "#EF4444"}
            for c in level_info["causes_extracted"]:
                if isinstance(c, dict):
                    detail = c.get("confidence_detail") or {}
                    composite = detail.get("composite")
                    tier = detail.get("tier", "Rendah")
                    color = _tier_colors.get(tier, "#94a3b8")
                    badge = (
                        f"<span style='background:{color}22; color:{color}; border:1px solid {color}66; "
                        f"border-radius:6px; padding:1px 8px; font-size:0.72rem; font-weight:700; margin-left:6px;'>"
                        f"{composite}% · {tier}</span>"
                        if composite is not None else ""
                    )
                    st.markdown(f"- {c.get('cause', '')} {badge}", unsafe_allow_html=True)
                    if c.get("rationale"):
                        st.markdown(
                            f"<p style='color:#94a3b8; font-size:0.82rem; margin:0 0 6px 16px;'>↳ {c['rationale']}</p>",
                            unsafe_allow_html=True,
                        )
                else:
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


def _render_evidence_graph_section(result_tree: list):
    """Render peta visual investigasi + penyebab berwarna berdasarkan tier
    keyakinan, dengan akar masalah ditandai."""
    st.caption(
        "Peta bukti interaktif: kotak biru adalah level investigasi, lingkaran berwarna adalah "
        "penyebab yang teridentifikasi (hijau = keyakinan tinggi, kuning = sedang, merah = rendah). "
        "Lingkaran bergaris cyan menandai akar masalah paling dalam yang ditemukan."
    )
    graph_data = build_evidence_graph_data(result_tree)
    fig = build_evidence_graph_fig(graph_data)
    if fig is not None:
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("Belum cukup data untuk membangun evidence graph.")


def _render_investigation_results(
    title: str,
    exec_summary: str,
    citation_warning: str | None,
    result_tree: list,
    consolidated_bib: list,
):
    """Susun hasil investigasi (brief, evidence graph, root cause tree) ke
    dalam sub-tab terpisah, supaya tidak semua konten menumpuk di satu
    halaman panjang. Dipakai baik untuk hasil baru maupun riwayat tersimpan.
    """
    st.markdown(f"## {title}")

    sub_tab_brief, sub_tab_graph, sub_tab_tree = st.tabs(
        ["📋 Executive Brief", "🕸️ Evidence Graph", "🌳 Root Cause Tree"]
    )

    with sub_tab_brief:
        if exec_summary:
            st.markdown(exec_summary)
            if citation_warning:
                st.warning(citation_warning)
        else:
            st.info("Ringkasan eksekutif belum tersedia untuk investigasi ini.")

    with sub_tab_graph:
        _render_evidence_graph_section(result_tree)

    with sub_tab_tree:
        total_levels = max((lvl["depth"] for lvl in result_tree), default=1)
        url_to_global_number = {
            b.get("url"): b.get("number") for b in consolidated_bib
        }
        for level_info in result_tree:
            _render_level_details(
                level_info, level_info["depth"], total_levels, url_to_global_number
            )


# --- STRUKTUR TAB UTAMA ---
tab_recursive, tab_pdf_recursive = st.tabs(
    ["🕵️ Jalankan AI Investigator", "📄 Download Executive Intelligence Brief"]
)

with tab_recursive:
    with st.container(key="fenomena_config_card"):
        st.subheader("⚙️ Konfigurasi Investigasi")
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
            "🕵️ Jalankan AI Investigator",
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

                _render_investigation_results(
                    ai_title,
                    final_executive_summary,
                    citation_warning,
                    result_tree,
                    consolidated_bib,
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
                <div style="font-size: 3rem; margin-bottom: 12px;">🕵️</div>
                <h3 style="color: #00f0ff;">Belum Ada Investigasi yang Dijalankan</h3>
                <p style="color: #94a3b8; max-width: 600px; margin: 0 auto 20px auto;">
                    Masukkan deskripsi fenomena di atas dan klik tombol <b>Jalankan AI Investigator</b>. 
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

            stored_bib_for_render = st.session_state.get(
                "last_consolidated_bibliography", []
            )
            _render_investigation_results(
                stored_title_history or stored_query_history,
                stored_exec_summary,
                st.session_state.get("last_citation_warning"),
                stored_result_history,
                stored_bib_for_render,
            )

with tab_pdf_recursive:
    st.subheader("📄 Cetak & Download Executive Intelligence Brief (PDF)")
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
            "⚠️ Belum ada hasil investigasi yang tersedia. Silakan jalankan AI Investigator di tab sebelumnya."
        )
    else:
        st.info(f"💡 Executive Intelligence Brief **'{stored_title}'** siap dicetak.")

        if st.button(
            "📥 Proses Executive Intelligence Brief (PDF)",
            type="primary",
            key="btn_gen_pdf_recursive",
            width="stretch",
        ):
            with st.spinner(
                "Menyiapkan dokumen PDF Executive Intelligence Brief..."
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
                        st.success("Dokumen PDF Executive Intelligence Brief berhasil dibuat!")
                        st.download_button(
                            label=f"📄 Download PDF: {stored_title[:60]}",
                            data=pdf_bytes,
                            file_name=f"AI_Investigator_Brief_{stored_query.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf",
                            mime="application/pdf",
                            width="stretch",
                        )
                except Exception as pdf_err:
                    st.error(f"Gagal memproses file PDF: {pdf_err}")
