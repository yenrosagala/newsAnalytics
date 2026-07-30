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


def get_recursive_executive_summary_prompt(
    initial_query: str,
    level_breakdown: str,
    numbered_bibliography: str,
) -> str:
    """Prompt untuk laporan Root Cause Analysis (5-Why) bertingkat.

    Berbeda dari get_executive_summary_prompt (yang dirancang untuk satu
    korpus keyword tunggal dan memaksakan konteks institusi/wilayah tetap),
    prompt ini:
    - Generik untuk topik APAPUN, tidak hardcode entitas/wilayah tertentu.
    - Meminta OUTPUT JSON ketat {"title": ..., "executive_summary": ...}
      supaya judul & isi bisa dipisah secara reliable tanpa parsing string
      yang rapuh.
    - Diberi daftar pustaka yang SUDAH DINOMORI SECARA OTORITATIF oleh
      sistem (bukan oleh AI), dan AI diwajibkan memakai nomor tsb persis
      saat melakukan sitasi -- supaya [1][2][3] di esai benar-benar cocok
      dengan Daftar Pustaka final di PDF.
    """
    return f"""Anda adalah analis riset senior yang menyusun laporan Root Cause Analysis (metode "5 Why") bertingkat untuk kalangan eksekutif/pengambil kebijakan.

TOPIK/FENOMENA AWAL YANG DITELUSURI:
{initial_query}

Berikut adalah hasil penelusuran bertingkat (Level 1 = permukaan masalah, Level berikutnya = penyebab yang semakin mendalam):
{level_breakdown}

Berikut adalah DAFTAR PUSTAKA yang SUDAH DINOMORI SECARA RESMI oleh sistem (gunakan PERSIS nomor-nomor ini saat melakukan sitasi, jangan membuat nomor sendiri):
{numbered_bibliography}

## Tugas Anda

1. **Judul**: Buat SATU judul laporan yang tajam, spesifik, dan mencerminkan alur sebab-akibat yang ditemukan lintas seluruh level (bukan sekadar mengulang topik awal, bukan generik, bukan clickbait, bukan berupa pertanyaan). Panjang 10-20 kata, bahasa Indonesia formal-analitis.

2. **Ringkasan Eksekutif**: Tulis esai naratif formal (5-9 paragraf) yang mensintesis TEMUAN DARI SELURUH LEVEL menjadi satu narasi akar-masalah yang koheren -- jelaskan bagaimana penyebab di level permukaan mengarah ke penyebab yang lebih dalam di level berikutnya, sampai ke akar masalah yang paling mendasar yang teridentifikasi. Integrasikan unsur 5W+1H secara alami ke dalam paragraf, JANGAN gunakan bullet point atau subjudul yang memecah esai. Tutup dengan implikasi/rekomendasi tingkat tinggi berdasarkan akar masalah yang ditemukan.
   - WAJIB memakai sitasi numerik [n] pada setiap klaim faktual, sesuai PERSIS nomor di Daftar Pustaka Resmi di atas.
   - Satu kalimat boleh memiliki lebih dari satu sitasi, misalnya [2][5].
   - **DILARANG KERAS mengulang nomor sitasi yang sama untuk klaim yang berasal dari sumber berbeda.** Setiap nomor sitasi HARUS merujuk ke sumber spesifik yang memang menyatakan klaim tersebut -- periksa Daftar Pustaka Resmi untuk memastikan nomornya cocok sebelum menuliskannya.
     - BENAR (contoh): "Harga beras naik 12% di Jayapura [1], sementara Bulog menyatakan stok masih aman untuk tiga bulan ke depan [4]." (dua klaim berbeda, dua nomor berbeda)
     - SALAH (jangan lakukan ini): "Harga beras naik 12% di Jayapura [1], sementara Bulog menyatakan stok masih aman [1]." (dua klaim berbeda tapi nomor sitasi disamakan -- ini instruksi yang dilanggar)
   - Kalau esai memakai lebih dari satu sitasi, hasil akhirnya HARUS memuat sitasi dengan nomor yang bervariasi (bukan cuma satu nomor diulang-ulang di seluruh esai), karena Daftar Pustaka Resmi berisi banyak sumber berbeda yang masing-masing punya kontribusi klaim yang berbeda.
   - JANGAN mencantumkan ulang daftar pustaka di dalam field ini -- itu akan disusun terpisah oleh sistem.
   - Gunakan bahasa Indonesia formal, objektif, analitis, dan profesional. Bold pada angka/istilah/kebijakan penting boleh memakai **teks**.
   - JANGAN mengasumsikan topik ini selalu tentang institusi atau wilayah tertentu -- analisis harus murni mengikuti fakta yang ada di korpus berita di atas, apapun topiknya.

## Format Output (WAJIB)
Jawab HANYA dengan JSON valid, tanpa markdown code fence, tanpa teks lain di luar JSON, persis struktur berikut:
{{
  "title": "...",
  "executive_summary": "..."
}}"""
