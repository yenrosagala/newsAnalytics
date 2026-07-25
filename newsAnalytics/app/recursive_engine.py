"""
Recursive 5-Why Engine
======================
Menjalankan analisis akar-masalah (root cause) secara bertingkat terhadap
sebuah topik berita, dengan pola pikir "5 Why":

  Level 1: cari berita untuk query awal -> AI merangkum & mengekstrak
           penyebab (causes) + kata kunci turunan (next_keywords)
  Level 2..N: ulangi proses di atas menggunakan kata kunci turunan dari
              level sebelumnya, sampai max_depth tercapai atau tidak ada
              lagi artikel/kata kunci baru yang ditemukan.

Dipakai oleh pages/3_Fenomena.py melalui:
    run_recursive_5why_pipeline_with_progress(initial_query, max_depth, progress_bar, status_text)
"""
import json
import re
from typing import Dict, List

from app.core.logger import get_logger
from app.services.ai_service import ai_service
from app.services.scraper_service import scraper_service

logger = get_logger("RecursiveEngine")

ARTICLES_PER_LEVEL = 10
MAX_ARTICLES_IN_PROMPT = 15
MAX_CONTENT_CHARS_PER_ARTICLE = 1500


def _build_analysis_prompt(current_queries: List[str], depth: int, articles: List[Dict]) -> str:
    corpus_parts = []
    for art in articles[:MAX_ARTICLES_IN_PROMPT]:
        content = (art.get("content") or "")[:MAX_CONTENT_CHARS_PER_ARTICLE]
        corpus_parts.append(
            f"Judul: {art.get('title', '-')}\n"
            f"Media: {art.get('source', '-')}\n"
            f"Tanggal: {art.get('published_date', '-')}\n"
            f"Isi: {content}"
        )
    corpus = "\n\n---\n\n".join(corpus_parts) if corpus_parts else "Tidak ada artikel relevan yang ditemukan."

    return f"""Anda adalah analis root-cause profesional yang menjalankan metode "5 Why" secara bertingkat terhadap berita.

Level analisis saat ini: {depth}
Query pencarian yang digunakan: {", ".join(current_queries)}

Berikut kumpulan artikel berita yang relevan:
{corpus}

Tugas Anda:
1. Buat RINGKASAN singkat (3-5 kalimat) mengenai apa yang terjadi berdasarkan artikel di atas.
2. Identifikasi 2-5 PENYEBAB (causes) spesifik yang terungkap dari artikel di atas yang menjelaskan MENGAPA fenomena ini terjadi.
3. Dari penyebab-penyebab tersebut, turunkan 1-3 KATA KUNCI PENCARIAN baru (next_keywords) yang lebih spesifik untuk level "why" berikutnya, guna menggali lebih dalam akar masalahnya.

Jawab HANYA dalam format JSON valid persis seperti ini, tanpa teks lain, tanpa markdown code fence:
{{
  "summary": "...",
  "causes": ["...", "..."],
  "next_keywords": ["...", "..."]
}}"""


def _parse_ai_json(raw_text: str) -> Dict:
    if not raw_text:
        return {"summary": "", "causes": [], "next_keywords": []}

    text = raw_text.strip()
    text = re.sub(r"^```(json)?", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text).strip()

    try:
        data = json.loads(text)
        return {
            "summary": data.get("summary", "") or "",
            "causes": data.get("causes") or [],
            "next_keywords": data.get("next_keywords") or [],
        }
    except Exception as e:
        logger.warning(f"Gagal parsing JSON dari AI, fallback ke ringkasan teks polos: {e}")
        return {"summary": text[:800], "causes": [], "next_keywords": []}


def _articles_to_bibliography(articles: List[Dict]) -> List[Dict]:
    return [
        {
            "media": art.get("source") or "Media Nasional",
            "date": art.get("published_date") or "-",
            "title": art.get("title") or "Tanpa Judul",
            "url": art.get("url") or "#",
        }
        for art in articles
    ]


async def run_recursive_5why_pipeline_with_progress(
    initial_query: str,
    max_depth: int = 5,
    progress_bar=None,
    status_text=None,
) -> List[Dict]:
    """
    Menjalankan pipeline root-cause 5-Why secara bertingkat dan mengembalikan
    list of dict, satu entri per level, berisi:
        depth, queries_used, articles_found, summary,
        causes_extracted, bibliography, next_keywords
    """
    result_tree: List[Dict] = []
    current_queries = [initial_query]

    for depth in range(1, max_depth + 1):
        if status_text:
            status_text.text(f"Level {depth}/{max_depth}: mencari berita untuk '{', '.join(current_queries)}'...")
        if progress_bar:
            progress_bar.progress(min(depth / (max_depth + 1), 0.95))

        all_articles: List[Dict] = []
        for q in current_queries:
            arts = scraper_service.fetch_articles_for_analysis(q, limit=ARTICLES_PER_LEVEL)
            all_articles.extend(arts)

        if not all_articles:
            logger.info(f"Level {depth}: tidak ada artikel untuk {current_queries}, pipeline dihentikan.")
            break

        if status_text:
            status_text.text(f"Level {depth}/{max_depth}: menganalisis {len(all_articles)} artikel via AI...")

        ai_parsed = {"summary": "", "causes": [], "next_keywords": []}
        if ai_service.client:
            try:
                prompt = _build_analysis_prompt(current_queries, depth, all_articles)
                response = ai_service.client.models.generate_content(
                    model=ai_service.model_name,
                    contents=prompt,
                )
                ai_parsed = _parse_ai_json(response.text)
            except Exception as e:
                logger.error(f"Level {depth}: gagal memanggil AI service: {e}")
        else:
            logger.warning("AI Service belum terkonfigurasi, melewati ekstraksi otomatis penyebab.")

        result_tree.append({
            "depth": depth,
            "queries_used": current_queries,
            "articles_found": len(all_articles),
            "summary": ai_parsed.get("summary", ""),
            "causes_extracted": ai_parsed.get("causes", []),
            "bibliography": _articles_to_bibliography(all_articles),
            "next_keywords": ai_parsed.get("next_keywords", []),
        })

        next_keywords = ai_parsed.get("next_keywords") or []
        if not next_keywords:
            logger.info(f"Level {depth}: tidak ada kata kunci turunan, pipeline dihentikan lebih awal.")
            break
        current_queries = next_keywords[:3]

    if progress_bar:
        progress_bar.progress(1.0)
    if status_text:
        status_text.text("Analisis Recursive 5-Why selesai.")

    return result_tree
