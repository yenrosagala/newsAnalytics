import io
from datetime import datetime
from fpdf import FPDF
import matplotlib.pyplot as plt
import seaborn as sns


def clean_text(text):
    """Fungsi helper untuk membersihkan karakter non-ASCII/Unicode yang tidak didukung Helvetica"""
    if not isinstance(text, str):
        return str(text)
    # Ganti tanda kutip miring/unik dengan tanda kutip biasa, lalu hapus karakter non-ASCII lainnya
    text = text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    return text.encode('ascii', 'ignore').decode('ascii')


def generate_pdf_report(filtered_df, insights, target_keyword, date_range_str, t_media_str, summary_text):
    """
    Fungsi utilitas murni untuk membuat file PDF berdasarkan data yang dikirim dari UI.
    Grafik dibuat menggunakan Matplotlib/Seaborn agar tidak ketergantungan pada Chrome/Kaleido.
    """
    # Set style global untuk grafik biar rapi
    plt.style.use('ggplot')
    
    # 1. BIKIN GRAFIK SENTIMEN (Pie Chart)
    img_sentimen_bytes = io.BytesIO()
    if not filtered_df.empty and "Sentimen" in filtered_df.columns:
        sentimen_counts = filtered_df["Sentimen"].value_counts()
        
        fig, ax = plt.subplots(figsize=(5, 4))
        colors = {"Positif": "#4CAF50", "Negatif": "#F44336", "Netral": "#9E9E9E"}
        current_colors = [colors.get(x, "#9E9E9E") for x in sentimen_counts.index]
        
        ax.pie(
            sentimen_counts.values, 
            labels=sentimen_counts.index, 
            autopct='%1.1f%%', 
            startangle=90, 
            colors=current_colors,
            wedgeprops=dict(width=0.4, edgecolor='w')
        )
        ax.set_title("Distribusi Sentimen", fontsize=12, fontweight='bold', pad=10)
        plt.tight_layout()
        plt.savefig(img_sentimen_bytes, format='png', dpi=200)
        plt.close()
        img_sentimen_bytes.seek(0)

    # 2. BIKIN GRAFIK TOP 10 MEDIA (Horizontal Bar Chart)
    img_media_bytes = io.BytesIO()
    if not filtered_df.empty and "media" in filtered_df.columns:
        top_10_m = filtered_df["media"].value_counts().head(10)
        
        fig, ax = plt.subplots(figsize=(6, 4))
        sns.barplot(x=top_10_m.values, y=top_10_m.index, ax=ax, hue=top_10_m.index, palette="Blues_r", legend=False)
        ax.set_title("Top 10 Media Kontributor", fontsize=12, fontweight='bold', pad=10)
        ax.set_xlabel("Jumlah Berita")
        plt.tight_layout()
        plt.savefig(img_media_bytes, format='png', dpi=200)
        plt.close()
        img_media_bytes.seek(0)

    # 3. PARSING TEKS SUMMATION UNTUK MEMISAHKAN ESAI DAN REFERENSI
    parsed_body = summary_text
    parsed_references = ""
    
    if "Isi Analisis" in summary_text:
        parts = summary_text.split("Isi Analisis")
        rest = parts[1]
        if "Daftar Pustaka" in rest:
            rest_parts = rest.split("Daftar Pustaka")
            parsed_body = rest_parts[0].strip()
            parsed_references = rest_parts[1].strip()
        else:
            parsed_body = rest.strip()
    elif "Daftar Pustaka" in summary_text:
        rest_parts = summary_text.split("Daftar Pustaka")
        parsed_body = rest_parts[0].strip()
        parsed_references = rest_parts[1].strip()

    # 4. INISIALISASI DOKUMEN FPDF
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(left=20, top=20, right=20) 
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    
    # --- HEADER LAPORAN ---
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(0, 120, 212) 
    pdf.cell(170, 10, "LAPORAN EXECUTIVE NEWS INTELLIGENCE", align="C", new_x="LMARGIN", new_y="NEXT")
    
      
    # MENAMPILKAN JUDUL UTAMA ANALISIS HASIL AI SECARA DINAMIS
    clean_keyword_title = target_keyword.replace("Judul Analisis", "").replace("**", "").replace(":", "").strip()
    clean_keyword_title = clean_keyword_title.replace("•", "-").replace("·", "-")
    clean_keyword_title = clean_text(clean_keyword_title)
    
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(40, 40, 40)
    pdf.multi_cell(170, 6, f"{clean_keyword_title}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(170, 6, f"Dibuat secara otomatis pada: {datetime.now().strftime('%d %B %Y, %H:%M')}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)


    # Garis Pembatas Utama
    pdf.set_draw_color(0, 120, 212)
    pdf.set_line_width(0.6)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(8)
    
    # --- METADATA ANALISIS ---
    pdf.set_font("Helvetica", "B", 10.5)
    pdf.set_text_color(60, 60, 60)
       
    pdf.set_font("Helvetica", "B", 10.5)
    pdf.cell(40, 6, "Rentang Waktu", border=0)
    pdf.set_font("Helvetica", "", 10.5)
    pdf.cell(130, 6, f": {clean_text(date_range_str)}", border=0, new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("Helvetica", "B", 10.5)
    pdf.cell(40, 6, "Top Media", border=0)
    pdf.set_font("Helvetica", "", 10.5)
    pdf.multi_cell(130, 6, f": {clean_text(t_media_str)}", border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    # Garis Pembatas Utama
    pdf.set_draw_color(0, 120, 212)
    pdf.set_line_width(0.6)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(8)
    
    # --- SEKSI 1: VISUALISASI GRAFIK ---
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(0, 100, 180)
    pdf.cell(170, 8, "1. Grafik & Visualisasi Analisis", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    
    y_pos = pdf.get_y()
    if img_sentimen_bytes.getvalue():
        pdf.image(img_sentimen_bytes, x=20, y=y_pos, w=80)
    if img_media_bytes.getvalue():
        pdf.image(img_media_bytes, x=105, y=y_pos, w=85)
    pdf.set_y(y_pos + 62) 
    pdf.ln(4)
    
    # --- SEKSI 2: INSIGHTS UTAMA ---
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(0, 100, 180)
    pdf.cell(170, 8, "2. Ringkasan Temuan Utama (Insights)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10.5)
    pdf.set_text_color(50, 50, 50)
    pdf.ln(2)
    for insight in insights[:-1]:
        clean_insight = clean_text(insight)
        clean_insight = clean_insight.replace("•", "-").replace("·", "-")
        pdf.multi_cell(170, 6, f"  - {clean_insight}", new_x="LMARGIN", new_y="NEXT", align="JUSTIFY")
    pdf.ln(6)
    
    # --- SEKSI 3: EXECUTIVE SUMMARY BY AI ---
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(0, 100, 180)
    pdf.cell(170, 8, "3. Analisis Naratif Eksekutif", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(40, 40, 40)
    
    clean_body = parsed_body.replace("**", "")
    clean_body = clean_text(clean_body)
    clean_body = clean_body.replace("•", "-").replace("·", "-")
    paragraf_list = [p.strip() for p in clean_body.split("\n") if p.strip()]
    
    for paragraf in paragraf_list:
        # 🟢 REVISI UTAMA: Menggantikan first_line_indent dengan penambahan spasi manual di awal paragraf
        paragraf_terindentasi = "        " + paragraf
        pdf.multi_cell(170, 6.5, paragraf_terindentasi, new_x="LMARGIN", new_y="NEXT", align="JUSTIFY")
        pdf.ln(3)
    
    # --- SEKSI 4: DAFTAR PUSTAKA NUMERIK DI HALAMAN AKHIR ---
    if parsed_references:
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(0, 100, 180)
        pdf.cell(170, 8, "4. Daftar Pustaka", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(50, 50, 50)
        
        clean_refs = parsed_references.replace("**", "")
        clean_refs = clean_text(clean_refs)
        clean_refs = clean_refs.replace("•", "-").replace("·", "-")
        ref_lines = [r.strip() for r in clean_refs.split("\n") if r.strip()]
        
        for line in ref_lines:
            pdf.multi_cell(170, 5.5, line, new_x="LMARGIN", new_y="NEXT", align="JUSTIFY")
            pdf.ln(1)

    # --- FOOTER LAPORAN ---
    if pdf.get_y() > 245:
        pdf.add_page()
        
    pdf.ln(5)
    pdf.set_draw_color(200, 200, 200)
    pdf.set_line_width(0.3)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(4)
    
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(140, 140, 140)
    teks_footer_1 = "Laporan resmi ini dihasilkan secara otomatis oleh sistem News Intelligence Dashboard."
    teks_footer_2 = "Aplikasi: newscrapper.streamlit.app | Pengembang: Yenro P. Sagala - BPS Provinsi Papua"
    
    pdf.cell(170, 4, teks_footer_1, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(170, 4, teks_footer_2, align="C", new_x="LMARGIN", new_y="NEXT")
    
    return pdf.output()