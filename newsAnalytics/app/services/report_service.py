from fpdf import FPDF
import datetime
import os


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
        
        for idx, item in enumerate(articles, 1):
            # Membuang latin-1 encode yang merusak karakter
            judul = f"{idx}. {item.get('title', 'Tanpa Judul')}"
            
            pdf.set_font("Arial", "B", 11)
            pdf.set_text_color(45, 55, 72)
            pdf.multi_cell(0, 6, text=judul)
            
            pdf.set_font("Arial", "I", 8.5)
            pdf.set_text_color(113, 128, 150)
            meta = f"Waktu: {item.get('published_date', '-')} | Kata Kunci: {item.get('keyword', '-')}"
            pdf.cell(0, 5, text=meta, ln=True)
            
            pdf.ln(2)
            pdf.set_font("Arial", "", 9.5)
            pdf.set_text_color(45, 55, 72)
            
            # Langsung berikan text asli dari string Python, FPDF2 mendukung UTF-8
            summary_text = f"Analisis AI:\n{item.get('summary', 'Rangkuman belum dibuat.')}"
            
            pdf.set_fill_color(247, 250, 252)
            pdf.multi_cell(0, 5, text=summary_text, border="L", fill=True)
            pdf.ln(6)
            
        pdf.output(output_filename)
        return output_filename

# Inisialisasi Singleton agar nama panggilannya di pages/2_Dashboard.py tetap sama
report_service = ReportService()