import streamlit as st
from app.core.config import Config
from app.core.logger import get_logger
from app.utils.session import init_state
from app.utils.session import init_session_state
from app.core.auth import render_login_form, render_logout, is_authenticated

# 1. Setup Logger
logger = get_logger("MainApp")
logger.info("Aplikasi Google News Scrapper berhasil dimuat.")


# 2. Inisialisasi Session State Terpusat
# 'authenticated' disimpan di st.session_state, yang otomatis dibagikan ke
# SEMUA halaman (Scraping/Dashboard/Fenomena) selama tab browser yang sama
# masih terbuka -- jadi login cukup sekali per sesi, tidak perlu login ulang
# setiap pindah halaman.
def init_app_state():
    init_session_state("authenticated", False)
    init_session_state("role", "user")
    init_session_state("current_keyword", "")
    init_session_state("is_scrapped", False)

init_app_state()

# 3. Konfigurasi Halaman Streamlit
st.set_page_config(page_title=Config.PAGE_TITLE, page_icon=Config.PAGE_ICON, layout=Config.LAYOUT)

# 4. Inject CSS Eksternal
try:
    with open("app/assets/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    logger.warning("File style.css tidak ditemukan di folder assets. Menggunakan style default.")

# 5. Inisialisasi State Awal Aplikasi
init_state("search_keyword", "")
init_state("is_scrapped", False)

# 6. Login / Logout di Sidebar
if is_authenticated():
    st.sidebar.success(f"Masuk sebagai: **{st.session_state.get('role', 'user').capitalize()}**")
    render_logout()
else:
    render_login_form()

# 7. Header Halaman Utama
st.markdown("<div class='main-header'>📰 Google News Scraper & Sentiment Analyzer</div>", unsafe_allow_html=True)

st.markdown("""
### Selamat Datang di Aplikasi Analisis Berita
Aplikasi ini dirancang untuk membantu Anda melakukan *scraping* berita dari Google News secara otomatis,
menganalisis sentimen publik, dan mengekspor hasilnya ke dalam format laporan yang siap pakai.
""")

st.divider()

# 8. Menu Utama di Halaman Tengah (bukan hanya di sidebar)
if is_authenticated():
    st.markdown("#### 🚀 Pilih Menu untuk Memulai")
else:
    st.info("🔒 Silakan login terlebih dahulu melalui sidebar di sebelah kiri untuk mengakses menu di bawah ini.")
    st.markdown("#### 🚀 Menu Aplikasi (login untuk mengakses)")

menu_items = [
    {
        "icon": "📰",
        "title": "Scraping",
        "desc": "Ambil berita terbaru dari Google News berdasarkan kata kunci, lalu hasilkan ringkasan eksekutif otomatis.",
        "page": "pages/1_Scraping.py",
    },
    {
        "icon": "📊",
        "title": "Dashboard",
        "desc": "Visualisasikan data berita yang sudah tersimpan: distribusi sentimen, media kontributor, dan detail artikel.",
        "page": "pages/2_Dashboard.py",
    },
    {
        "icon": "🧠",
        "title": "Fenomena",
        "desc": "Jalankan analisis akar masalah (Root Cause / 5-Why) secara bertingkat terhadap sebuah topik/fenomena.",
        "page": "pages/3_Fenomena.py",
    },
]

cols = st.columns(3)
for col, item in zip(cols, menu_items):
    with col:
        with st.container(border=True):
            st.markdown(f"### {item['icon']} {item['title']}")
            st.caption(item["desc"])
            st.page_link(item["page"], label=f"Buka {item['title']}", icon="➡️", use_container_width=True)

st.divider()
st.info("💡 Anda juga bisa berpindah halaman kapan saja lewat menu navigasi di *sidebar* sebelah kiri.")
