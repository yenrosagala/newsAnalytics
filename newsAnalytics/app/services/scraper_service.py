import xml.etree.ElementTree as ET
import requests
import concurrent.futures
from typing import Optional, List, Dict
import cloudscraper
from app.core.logger import get_logger
from app.services.ai_service import ai_service
from app.services.sentiment_service import sentiment_service
from app.services.database_service import db_service

try:
    from googlenewsdecoder import gnewsdecoder
except ImportError:  # pragma: no cover - dependency guard
    gnewsdecoder = None

try:
    from newspaper import Article
except ImportError:  # pragma: no cover - dependency guard
    Article = None

logger = get_logger("ScraperService")

REGION_MAP = {
    "ID": ("id", "ID", "ID:id"),
    "US": ("en", "US", "US:en"),
}


class ScraperService:
    """Service untuk menangani scraping berita dan alur kerja integrasi AI/DB."""

    def __init__(self) -> None:
        self.scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
        )

    def fetch_google_news_rss(self, keyword: str, region: str = "ID") -> str:
        """Mengambil data RSS feed dari Google News."""
        encoded_keyword = requests.utils.quote(keyword)
        hl, gl, ceid = REGION_MAP.get(region, REGION_MAP["ID"])
        url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl={hl}&gl={gl}&ceid={ceid}"
        try:
            response = self.scraper.get(url, timeout=15)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Gagal fetch RSS untuk {keyword}: {str(e)}")
            return ""

    def _resolve_real_url(self, google_url: str) -> str:
        """Menerjemahkan URL redirect Google News menjadi URL artikel asli."""
        if not gnewsdecoder or not google_url:
            return google_url
        try:
            result = gnewsdecoder(google_url, interval=0)
            if result and result.get("status") and result.get("decoded_url"):
                return result["decoded_url"]
        except Exception as e:
            logger.warning(f"Gagal decode URL Google News: {e}")
        return google_url

    def _extract_full_text(self, url: str, fallback_text: str = "") -> str:
        """Mengambil isi lengkap artikel. Jika gagal, jatuh kembali ke deskripsi RSS."""
        if Article and url:
            try:
                article = Article(url)
                article.download()
                article.parse()
                if article.text and len(article.text.strip()) > 100:
                    return article.text.strip()
            except Exception as e:
                logger.warning(f"Gagal ekstrak isi artikel dari {url}: {e}")
        return fallback_text

    def _process_single_article(self, item: ET.Element, keyword: str) -> Optional[Dict]:
        """Memproses satu artikel: resolve URL, ekstrak isi, dan analisis sentimen."""
        try:
            link = item.findtext('link')
            title = item.findtext('title') or ""
            if not link:
                return None

            description = item.findtext('description') or ""
            real_url = self._resolve_real_url(link)
            full_text = self._extract_full_text(real_url, fallback_text=description)

            sentiment_label = sentiment_service.analyze_text(full_text) if full_text else "NEUTRAL"

            return {
                "title": title,
                "url": real_url or link,
                "source": item.findtext('source') or "",
                "published_date": item.findtext('pubDate') or "",
                "keyword": keyword,
                "content": full_text,
                "sentiment": sentiment_label,
            }
        except Exception as e:
            logger.warning(f"Gagal memproses artikel {item.findtext('title')}: {str(e)}")
            return None

    def _fetch_and_process(self, keyword: str, limit: int, region: str) -> List[Dict]:
        xml_data = self.fetch_google_news_rss(keyword, region=region)
        if not xml_data:
            return []
        try:
            root = ET.fromstring(xml_data)
            items = root.findall('.//item')[:limit]
        except ET.ParseError as e:
            logger.error(f"Gagal parsing XML RSS: {str(e)}")
            return []

        articles: List[Dict] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(self._process_single_article, item, keyword): item for item in items}
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    articles.append(result)
        return articles

    def fetch_articles_for_analysis(self, keyword: str, limit: int = 10, region: str = "ID") -> List[Dict]:
        """
        Mengambil & memproses artikel TANPA menyimpan ke database.
        Dipakai oleh recursive engine (Root Cause Analysis / 5-Why).
        """
        return self._fetch_and_process(keyword, limit, region)

    def execute_scraping_workflow(
        self,
        keyword: str,
        limit: int = 10,
        region: str = "ID",
        status_container=None,
        progress_bar=None,
    ) -> int:
        """
        Orchestrator utama scraping:
        1. Fetch RSS -> 2. Proses paralel (resolve URL + ekstrak isi + sentimen) -> 3. Simpan ke DB
        """
        if status_container:
            status_container.info(f"Mengambil daftar berita untuk '{keyword}'...")
        if progress_bar:
            progress_bar.progress(0.1)

        xml_data = self.fetch_google_news_rss(keyword, region=region)
        if not xml_data:
            if status_container:
                status_container.warning("Tidak ada respons dari Google News RSS.")
            return 0

        try:
            root = ET.fromstring(xml_data)
            items = root.findall('.//item')[:limit]
        except ET.ParseError as e:
            logger.error(f"Gagal parsing XML RSS: {str(e)}")
            if status_container:
                status_container.error("Gagal membaca format RSS dari Google News.")
            return 0

        total = len(items) or 1
        articles: List[Dict] = []
        done = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(self._process_single_article, item, keyword): item for item in items}
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                done += 1
                if progress_bar:
                    progress_bar.progress(min(0.1 + 0.8 * (done / total), 0.9))
                if result:
                    articles.append(result)
                    if status_container:
                        status_container.text(f"Memproses ({done}/{total}): {result['title'][:70]}...")

        if not articles:
            if status_container:
                status_container.warning("Tidak ada artikel yang berhasil diproses.")
            return 0

        saved_count = db_service.save_articles(articles)
        if progress_bar:
            progress_bar.progress(1.0)
        return saved_count


scraper_service = ScraperService()
