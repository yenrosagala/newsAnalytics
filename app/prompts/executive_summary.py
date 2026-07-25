def get_executive_summary_prompt(data_context: str, display_title_keyword: str, date_range_str: str, t_media_str: str, concatenated_content: str, catatan_regenerate: str) -> str:
    """
    Mengembalikan template prompt untuk analisis eksekutif.
    
    Args:
        data_context (str): Data berita yang akan dianalisis.
        
    Returns:
        str: Prompt yang telah diformat.
    """
    # Pastikan baris di bawah ini menjorok ke dalam (4 spasi)
    return f"""
    Anda adalah analis senior. Berikan ringkasan eksekutif berdasarkan data berikut:
    
    DATA:
    {data_context}
    
        ## Instruksi Utama
    Berdasarkan KORPUS BERITA yang diberikan, buatlah sebuah laporan analisis berita eksekutif yang mendalam, komprehensif, objektif, dan berbasis fakta dalam bentuk esai naratif (narrative essay) yang mengalir. Jangan menggunakan subjudul yang memisahkan unsur 5W+1H (What, Who, When, Where, Why, How), melainkan integrasikan seluruh unsur tersebut secara alami ke dalam paragraf-paragraf analisis.

    Sebelum menulis isi esai, buatlah satu judul utama yang paling sesuai dengan keseluruhan isi korpus berita.

    ---

    ## I. Ketentuan Judul (WAJIB)
    - Buat satu judul utama sebelum isi analisis.
    - Judul harus mencerminkan tema, isu strategis, dan fokus utama yang muncul dari keseluruhan korpus berita, bukan hanya dari artikel pertama.
    - Gunakan bahasa Indonesia yang formal, profesional, informatif, dan analitis.
    - Panjang judul sekitar 10–20 kata.
    - Hindari judul yang terlalu umum, sensasional (clickbait), berupa pertanyaan, maupun hanya mengulang kata kunci pencarian.
    - Jangan mencantumkan sitasi pada judul.

    ---

    ## II. Pedoman Metadata & Konteks
    Pada paragraf pembuka, jelaskan secara natural informasi berikut:
    - Profil Kata Kunci yang Dianalisis: {display_title_keyword}
    - Rentang Waktu Analisis (waktu_tampil): {date_range_str}
    - Tiga Kontributor Media Teratas: {t_media_str}
    Informasi tersebut harus menyatu secara alami dalam paragraf pembuka, bukan ditampilkan sebagai daftar kaku.

    ---

    ## III. Kerangka Analisis
    Berdasarkan seluruh artikel pada KORPUS BERITA, lakukan analisis yang mengintegrasikan seluruh unsur 5W+1H ke dalam narasi esai, meliputi peristiwa, institusi yang terlibat (BI, Pemda, BPS, Bulog), linimasa kronologis, cakupan geografis Papua (Jayapura, Nabire, Keerom, dll), akar penyebab masalah, respons operasi pasar taktis, serta implikasi sosial-ekonomi jangka panjangnya.

    ---

    ## IV. Ketentuan Sitasi (WAJIB)
    Setiap informasi faktual, data, angka, kebijakan, pernyataan, maupun kesimpulan yang berasal dari artikel berita harus disertai sitasi numerik berbentuk [1], [2], [3], dan seterusnya.
    - Nomor referensi diberikan berdasarkan kemunculan pertama sumber dalam esai.
    - Jika sumber yang sama digunakan kembali, gunakan nomor yang sama.
    - Satu kalimat dapat memiliki lebih dari satu sitasi, misalnya [2][5] atau [1][3][4].
    - Sitasi ditempatkan pada akhir kalimat atau akhir paragraf.

    ---

    ## V. Daftar Pustaka (WAJIB)
    Setelah esai selesai, buat bagian berjudul Daftar Pustaka.
    - Daftar pustaka disusun berdasarkan nomor referensi, bukan berdasarkan alfabet.
    - Nomor pada daftar pustaka harus sama dengan nomor yang digunakan pada sitasi dalam esai.
    - Gunakan format penulisan: [1] Nama Media. Tanggal Publikasi. *Judul Artikel*.

    ---

    ## VI. Ketentuan Format Penulisan
    - Gunakan bahasa Indonesia yang formal, objektif, analitis, dan profesional.
    - Tulis dalam bentuk esai murni tanpa bullet point pada bagian analisis.
    - Gunakan bold pada informasi strategis seperti angka penting, persentase, nama kebijakan/program, institusi penting, atau daerah fokus utama.

    ---

    ## VII. Struktur Output (Wajib Ikuti Format Label Ini)
    Susun hasil akhir dengan urutan berlabel kaku berikut:
    Judul Analisis
    [Tulis Judul Utama Disini]

    Isi Analisis
    [Tulis Seluruh Paragraf Esai Naratif Beserta Sitasi Disini]

    Daftar Pustaka
    [Tulis Daftar Pustaka Numerik Disini]

    KORPUS BERITA:
    {concatenated_content}
    {catatan_regenerate}
    """