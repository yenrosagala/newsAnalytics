import os
from pathlib import Path

# UBAH 'config' MENJADI 'Config'
class Config:
    # Base Directory Proyek
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
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

  