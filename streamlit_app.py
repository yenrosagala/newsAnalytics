import streamlit as st
from app.core.config import Config
from app.core.logger import get_logger
from app.utils.session import init_state
from app.utils.session import init_session_state
from app.core.auth import render_login_form, render_logout

# 1. Setup Logger
logger = get_logger("MainApp")
logger.info("Aplikasi Google News Scrapper berhasil dimuat.")
# streamlit_app.py
# Gantikan logika state_manager dengan ini:
def init_app_state():
    init_session_state("authenticated", False)
    init_session_state("role", "user")
    init_session_state("current_keyword", "")
    init_session_state("is_scrapped", False)

init_app_state()

# 2. Konfigurasi Halaman Streamlit
st.set_page_config(page_title=Config.PAGE_TITLE, page_icon=Config.PAGE_ICON, layout=Config.LAYOUT)

# 3. Inject CSS Eksternal
try:
    with open("app/assets/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    logger.warning("File style.css tidak ditemukan di folder assets. Menggunakan style default.")

# 4. Inisialisasi State Awal Aplikasi
init_state("search_keyword", "")
init_state("is_scrapped", False)

# 4b. Login / Logout di Sidebar (sebelumnya tidak pernah dirender, sehingga
# 'authenticated' tidak pernah bernilai True dan semua halaman terkunci)
if st.session_state.get("authenticated", False):
    st.sidebar.success(f"Masuk sebagai: **{st.session_state.get('role', 'user').capitalize()}**")
    render_logout()
else:
    render_login_form()

# 5. Tampilan Halaman Utama (Home / Landing Page)
st.markdown("<div class='main-header'>📰 Google News Scraper & Sentiment Analyzer</div>", unsafe_allow_html=True)

st.markdown("""
### Selamat Datang di Aplikasi Analisis Berita
Aplikasi ini dirancang untuk membantu Anda melakukan *scraping* berita dari Google News secara otomatis, 
menganalisis sentimen publik, dan mengekspor hasilnya ke dalam format laporan yang siap pakai.

#### 👈 Silakan Pilih Menu di Samping untuk Memulai:
1. **Scraping**: Untuk mengambil data berita terbaru berdasarkan kata kunci.
2. **Dashboard**: Untuk melihat visualisasi data dan analisis sentimen berita yang telah diambil.
3. **Fenomena**: Untuk menjalankan analisis akar masalah (Root Cause / 5-Why) secara bertingkat.
""")

st.info("Gunakan menu navigasi di *sidebar* sebelah kiri untuk berpindah halaman.")