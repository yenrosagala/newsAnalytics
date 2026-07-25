# app/scraper.py
"""
DEPRECATED: File ini dipertahankan sementara sebagai jembatan (bridge) 
agar UI lama tidak break. Migrasikan pemanggilan ke app.services langsung.
"""
from app.services.scraper_service import scraper_service

def scrape_google_news(keyword, jumlah_berita):
    # Mengarahkan fungsi scraper lama ke Service Layer yang baru
    return scraper_service.execute_scraping_workflow(keyword, num_results=jumlah_berita)