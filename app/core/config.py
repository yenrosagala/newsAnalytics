import os
from pathlib import Path
import streamlit as st

# UBAH 'config' MENJADI 'Config'
class Config:
    # --------------------------------------------------------------
    # KREDENSIAL LOGIN ADMIN
    # Aplikasi ini terbuka bebas untuk pengguna umum (tidak perlu login).
    # Login HANYA dipakai untuk mengakses fitur manajemen database (admin).
    # HANYA dibaca dari st.secrets (atau env var sebagai fallback untuk
    # dev lokal non-Streamlit). TIDAK ADA default password tertanam di
    # kode -- jika secret ini kosong, login admin dinonaktifkan
    # (fail-closed), bukan diam-diam pakai password lemah yang sudah
    # terpublikasi di GitHub.
    # --------------------------------------------------------------
    ADMIN_USERNAME = st.secrets.get("ADMIN_USERNAME", os.getenv("ADMIN_USERNAME", "admin"))
    ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", os.getenv("ADMIN_PASSWORD", ""))

    # Base Directory Proyek
    DEFAULT_NUM_RESULTS = 20
    MAX_ARTICLES_IN_MEMORY = 1000
    GEMINI_CONTEXT_LIMIT = 120000
    MODEL_FALLBACKS = [
        "gemini-2.5-flash", 
        "gemini-3.1-flash-lite",
        "gemini-3-flash-preview"
    ]
    # Konfigurasi UI
    DATE_FORMAT = "%Y-%m-%d"
    PAGE_TITLE = "Google News Scraper & Sentiment Analyzer"
    PAGE_ICON = "📰"
    LAYOUT = "wide"
    
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    DB_NAME = os.getenv("DATABASE_URL", str(BASE_DIR / "berita_google_news.db"))
    
    @property
    def DB_PATH(self):
        return self.DB_NAME