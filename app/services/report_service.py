from fpdf import FPDF
import datetime
import os
from typing import List, Dict


# fpdf2 core fonts (Helvetica/Arial/Times/Courier) render using LATIN-1,
# bukan cp1252 (lihat FPDF.core_fonts_encoding). Perbedaan ini penting karena
# karakter tipografi umum dari hasil AI/scraping -- kutip pintar "" ' ',
# en/em-dash (–, —), elipsis, bullet -- ADA di cp1252 tapi TIDAK ADA di latin-1.
# Encode ke cp1252 dulu (seperti sebelumnya) membuat sanitasi "lolos" tanpa
# error, tapi fpdf2 lalu gagal total saat benar-benar menggambar glyph-nya:
#   FPDFException: Character "–" ... is outside the range of characters
#   supported by the font used: "helvetica"
# Solusi: petakan dulu karakter tipografi umum ke padanan ASCII-nya, baru
# encode ke latin-1 (dengan 'replace' sebagai jaring pengaman terakhir untuk
# karakter langka lain seperti emoji/CJK).
_PDF_TYPOGRAPHIC_CHAR_MAP = {
    "\u201c": '"', "\u201d": '"',   # " "
    "\u2018": "'", "\u2019": "'",   # ' '
    "\u2013": "-", "\u2014": "-",   # en dash (–), em dash (—)
    "\u2026": "...",                 # elipsis
    "\u2022": "-",                   # bullet
    "\u00a0": " ",                   # non-breaking space
}


def _sanitize_pdf_text(text: str) -> str:
    """Bersihkan teks agar aman dirender font core fpdf2 (encoding latin-1),
    TANPA menghapus karakter tipografi umum (kutip miring "", en/em-dash, elipsis,
    bullet) seperti pendekatan encode('ascii','ignore') lama yang merusak teks
    hasil AI (mis. "kata—kata" jadi "katakata").
    Karakter tipografi umum dipetakan ke padanan ASCII (mis. "" -> "), sisanya
    yang benar-benar di luar latin-1 (mis. emoji, CJK) diganti '?'.
    """
    if not text:
        return ""
    for src, dst in _PDF_TYPOGRAPHIC_CHAR_MAP.items():
        text = text.replace(src, dst)
    return text.encode("latin-1", "replace").decode("latin-1")


class ReportService:
    @staticmethod
    def export_articles_to_pdf(articles: list, output_filename: str = "Laporan_Monitoring_Berita.pdf") -> str:
        # FPDF2 akan digunakan. Pastikan di requirements.txt tertulis fpdf2, bukan fpdf.
        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        
        pdf.set_font("Arial", "B", 18)
        pdf.set_text_color(43, 108, 176)
        pdf.cell(0, 10, "Laporan Hasil Analisis Media Berita", ln=True, align="L")
        
        pdf.set_font("Arial", "", 9)
        pdf.set_text_color(113, 128, 150)
        waktu_cetak = datetime.datetime.now().strftime('%d-%m-%Y %H:%M')
        pdf.cell(0, 5, f"Dicetak Otomatis Sistem pada: {waktu_cetak}", ln=True, align="L")
        
        pdf.ln(5)
        
        S = _sanitize_pdf_text

        for idx, item in enumerate(articles, 1):
            # Membuang latin-1 encode yang merusak karakter
            judul = S(f"{idx}. {item.get('title', 'Tanpa Judul')}")
            
            pdf.set_font("Arial", "B", 11)
            pdf.set_text_color(45, 55, 72)
            pdf.multi_cell(0, 6, text=judul)
            
            pdf.set_font("Arial", "I", 8.5)
            pdf.set_text_color(113, 128, 150)
            meta = S(f"Waktu: {item.get('published_date', '-')} | Kata Kunci: {item.get('keyword', '-')}")
            pdf.cell(0, 5, text=meta, ln=True)
            
            pdf.ln(2)
            pdf.set_font("Arial", "", 9.5)
            pdf.set_text_color(45, 55, 72)
            
            # Langsung berikan text asli dari string Python, FPDF2 mendukung UTF-8
            summary_text = S(f"Analisis AI:\n{item.get('summary', 'Rangkuman belum dibuat.')}")
            
            pdf.set_fill_color(247, 250, 252)
            pdf.multi_cell(0, 5, text=summary_text, border="L", fill=True)
            pdf.ln(6)
            
        pdf.output(output_filename)
        return output_filename

    @staticmethod
    def generate_recursive_pdf(
        title: str,
        brief: Dict,
        initial_query: str,
        result_tree: List[Dict],
        consolidated_bibliography: List[Dict],
    ) -> bytes:
        """Menyusun laporan PDF formal Root Cause Analysis (5-Why) bertingkat.

        Struktur:
          1. Sampul: judul hasil AI (bukan generik) + metadata topik
          2. Executive Brief (Situation / Risks / Impact / Recommendations)
             -- dict terstruktur dari app.services.decision_brief
          3. Analisis Bertingkat: per level -- query, ringkasan, penyebab
          4. Grafik jumlah artikel per level (data asli, bukan data acak)
          5. Daftar Pustaka Konsolidasi -- gabungan SEMUA level, bernomor
             global, masing-masing entri menandai level asalnya
        """
        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.set_margins(left=20, top=20, right=20)
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()

        S = _sanitize_pdf_text
        brief = brief or {}
        SEVERITY_RGB = {"Tinggi": (200, 40, 40), "Sedang": (180, 120, 0), "Rendah": (30, 140, 90)}

        # --- SAMPUL ---
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(170, 6, "AI INVESTIGATOR -- EXECUTIVE INTELLIGENCE BRIEF (RECURSIVE ROOT CAUSE ANALYSIS)", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        pdf.set_font("Helvetica", "B", 17)
        pdf.set_text_color(0, 90, 160)
        pdf.multi_cell(170, 8, S(title.strip() or f"Analisis Akar Masalah: {initial_query}"), align="L", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(90, 90, 90)
        pdf.multi_cell(170, 5.5, S(f"Topik awal investigasi: {initial_query}"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(120, 120, 120)
        total_articles = sum(lvl.get("articles_found", 0) for lvl in result_tree)
        meta_line = (
            f"Dibuat otomatis: {datetime.datetime.now().strftime('%d %B %Y, %H:%M')}  |  "
            f"Kedalaman analisis: {len(result_tree)} level  |  "
            f"Total artikel dianalisis: {total_articles}  |  "
            f"Total sumber pustaka: {len(consolidated_bibliography)}"
        )
        pdf.multi_cell(170, 5, S(meta_line), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

        pdf.set_draw_color(0, 120, 212)
        pdf.set_line_width(0.6)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(8)

        # --- EXECUTIVE INTELLIGENCE BRIEF (Situation / Risks / Impact / Recommendations) ---
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(0, 100, 180)
        pdf.cell(170, 8, "Executive Intelligence Brief", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        def _brief_subheading(text):
            pdf.set_font("Helvetica", "B", 11.5)
            pdf.set_text_color(0, 100, 180)
            pdf.cell(170, 7, S(text), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)

        def _brief_paragraphs(text):
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(30, 30, 30)
            for para in [p.strip() for p in (text or "").split("\n") if p.strip()]:
                pdf.multi_cell(170, 6.3, S(para), align="J", markdown=True, new_x="LMARGIN", new_y="NEXT")
                pdf.ln(3)

        if brief.get("situation"):
            _brief_subheading("Situation")
            _brief_paragraphs(brief["situation"])

        if brief.get("risks"):
            _brief_subheading("Risks")
            pdf.set_font("Helvetica", "", 10.5)
            for r in brief["risks"]:
                severity = r.get("severity", "Sedang")
                rgb = SEVERITY_RGB.get(severity, (80, 80, 80))
                pdf.set_text_color(30, 30, 30)
                pdf.write(5.6, S(f"- {r.get('risk', '')} "))
                pdf.set_font("Helvetica", "B", 9.5)
                pdf.set_text_color(*rgb)
                pdf.write(5.6, f"[{severity}]")
                pdf.ln(6)
                pdf.set_font("Helvetica", "", 10.5)
                if r.get("rationale"):
                    pdf.set_text_color(110, 110, 110)
                    pdf.set_font("Helvetica", "I", 9)
                    pdf.multi_cell(170, 5, S(f"  Dasar: {r['rationale']}"), new_x="LMARGIN", new_y="NEXT")
                    pdf.set_font("Helvetica", "", 10.5)
            pdf.ln(3)

        if brief.get("impact"):
            _brief_subheading("Impact")
            _brief_paragraphs(brief["impact"])

        if brief.get("recommendations"):
            _brief_subheading("Recommendations")
            pdf.set_font("Helvetica", "", 10.5)
            pdf.set_text_color(30, 30, 30)
            for i, rec in enumerate(brief["recommendations"], 1):
                pdf.multi_cell(170, 6, S(f"{i}. {rec}"), new_x="LMARGIN", new_y="NEXT", align="JUSTIFY")
            pdf.ln(3)

        if not any([brief.get("situation"), brief.get("risks"), brief.get("impact"), brief.get("recommendations")]):
            pdf.set_font("Helvetica", "I", 10)
            pdf.set_text_color(120, 120, 120)
            pdf.multi_cell(170, 6, "Executive brief tidak tersedia untuk laporan ini.", new_x="LMARGIN", new_y="NEXT")

        pdf.ln(2)
        pdf.set_draw_color(200, 200, 200)
        pdf.set_line_width(0.3)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(8)

        # --- ANALISIS BERTINGKAT PER LEVEL ---
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(0, 100, 180)
        pdf.cell(170, 8, "Analisis Bertingkat per Level (5-Why)", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

        for lvl in result_tree:
            if pdf.get_y() > 250:
                pdf.add_page()

            depth = lvl.get("depth")
            pdf.set_fill_color(235, 244, 252)
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(0, 80, 140)
            pdf.cell(170, 8, S(f"Level {depth}"), fill=True, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)

            pdf.set_font("Helvetica", "B", 9.5)
            pdf.set_text_color(80, 80, 80)
            pdf.cell(35, 5.5, "Query Pencarian", border=0)
            pdf.set_font("Helvetica", "", 9.5)
            pdf.multi_cell(135, 5.5, S(", ".join(lvl.get("queries_used", []))), new_x="LMARGIN", new_y="NEXT")

            pdf.set_font("Helvetica", "B", 9.5)
            pdf.cell(35, 5.5, "Artikel Ditemukan", border=0)
            pdf.set_font("Helvetica", "", 9.5)
            pdf.cell(135, 5.5, S(f"{lvl.get('articles_found', 0)} artikel"), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)

            if lvl.get("summary"):
                pdf.set_font("Helvetica", "B", 9.5)
                pdf.set_text_color(40, 40, 40)
                pdf.cell(170, 5.5, "Ringkasan Level:", new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", "", 9.5)
                pdf.multi_cell(170, 5.3, S(lvl["summary"]), align="J", new_x="LMARGIN", new_y="NEXT")
                pdf.ln(1)

            causes = lvl.get("causes_extracted") or []
            if causes:
                pdf.set_font("Helvetica", "B", 9.5)
                pdf.set_text_color(180, 40, 40)
                pdf.cell(170, 5.5, "Penyebab Teridentifikasi (dengan Skor Keyakinan):", new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", "", 9.5)
                pdf.set_text_color(40, 40, 40)
                for c in causes:
                    if isinstance(c, dict):
                        detail = c.get("confidence_detail") or {}
                        composite = detail.get("composite")
                        tier = detail.get("tier")
                        conf_str = f" [Keyakinan: {composite}% - {tier}]" if composite is not None else ""
                        line = f"- {c.get('cause', '')}{conf_str}"
                        pdf.multi_cell(170, 5.3, S(line), new_x="LMARGIN", new_y="NEXT")
                        if c.get("rationale"):
                            pdf.set_font("Helvetica", "I", 8.5)
                            pdf.set_text_color(110, 110, 110)
                            pdf.multi_cell(170, 4.8, S(f"  Dasar: {c['rationale']}"), new_x="LMARGIN", new_y="NEXT")
                            pdf.set_font("Helvetica", "", 9.5)
                            pdf.set_text_color(40, 40, 40)
                    else:
                        pdf.multi_cell(170, 5.3, S(f"- {c}"), new_x="LMARGIN", new_y="NEXT")

            pdf.ln(5)

        # --- GRAFIK JUMLAH ARTIKEL PER LEVEL (data asli) ---
        try:
            import io
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            levels_lbl = [f"L{lvl.get('depth')}" for lvl in result_tree]
            counts = [lvl.get("articles_found", 0) for lvl in result_tree]
            if any(counts):
                fig, ax = plt.subplots(figsize=(6, 2.6))
                ax.bar(levels_lbl, counts, color="#0078D4")
                ax.set_title("Jumlah Artikel Dianalisis per Level", fontsize=10, fontweight="bold")
                ax.set_ylabel("Jumlah Artikel")
                plt.tight_layout()
                img_buf = io.BytesIO()
                plt.savefig(img_buf, format="png", dpi=180)
                plt.close(fig)
                img_buf.seek(0)

                if pdf.get_y() > 220:
                    pdf.add_page()
                pdf.image(img_buf, x=35, w=140)
                pdf.ln(6)
        except Exception:
            pass  # Grafik bersifat pelengkap; laporan tetap valid tanpa grafik jika gagal

        # --- DAFTAR PUSTAKA KONSOLIDASI ---
        if pdf.get_y() > 230:
            pdf.add_page()

        pdf.set_draw_color(200, 200, 200)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(6)

        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(0, 100, 180)
        pdf.cell(170, 8, "Daftar Pustaka Konsolidasi (Seluruh Level)", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "I", 8.5)
        pdf.set_text_color(120, 120, 120)
        pdf.multi_cell(170, 5, "Memuat gabungan seluruh sumber dari setiap level pencarian; nomor sesuai sitasi [n] pada Ringkasan Eksekutif.", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(40, 40, 40)
        for entry in consolidated_bibliography:
            levels_str = ", ".join(f"L{d}" for d in entry.get("levels", []))
            line = (
                f"[{entry['number']}] {entry.get('author', 'Tidak diketahui')}. "
                f"{entry.get('media', '-')}. {entry.get('date', '-')}. "
                f"{entry.get('title', 'Tanpa Judul')}. {entry.get('url', '')} (Level: {levels_str})"
            )
            pdf.multi_cell(170, 5.2, S(line), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)

        # --- FOOTER ---
        if pdf.get_y() > 250:
            pdf.add_page()
        pdf.ln(5)
        pdf.set_draw_color(200, 200, 200)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(4)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(140, 140, 140)
        pdf.cell(170, 4, "Laporan ini dihasilkan otomatis oleh AI Investigator - AI Decision Intelligence Platform.", align="C", new_x="LMARGIN", new_y="NEXT")

        return bytes(pdf.output())


# Inisialisasi Singleton agar nama panggilannya di pages/2_Dashboard.py tetap sama
report_service = ReportService()
