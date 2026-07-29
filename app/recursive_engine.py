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

ARTICLES_PER_LEVEL = 3
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
            "author": art.get("authors") or "Tidak diketahui",
        }
        for art in articles
    ]


def consolidate_bibliography(result_tree: List[Dict]) -> List[Dict]:
    """Menggabungkan daftar pustaka SEMUA level menjadi satu daftar bernomor global.

    - Deduplikasi berdasarkan URL (kalau artikel yang sama muncul lagi di
      level lain, nomornya tidak diulang -- tapi level asalnya dicatat di
      `levels` supaya tetap tertelusur ia relevan di level mana saja).
    - Penomoran mengikuti urutan kemunculan pertama (Level 1 duluan, dst),
      dan nomor ini adalah yang WAJIB dipakai AI saat sitasi di ringkasan
      eksekutif (lihat get_recursive_executive_summary_prompt).
    """
    consolidated: List[Dict] = []
    seen_urls: Dict[str, int] = {}  # url -> index di `consolidated`

    for lvl in result_tree:
        depth = lvl.get("depth")
        for bib in lvl.get("bibliography", []):
            url = bib.get("url") or "#"
            key = url if url != "#" else f"{bib.get('title')}|{bib.get('media')}"
            if key in seen_urls:
                idx = seen_urls[key]
                if depth not in consolidated[idx]["levels"]:
                    consolidated[idx]["levels"].append(depth)
                continue
            entry = dict(bib)
            entry["levels"] = [depth]
            seen_urls[key] = len(consolidated)
            consolidated.append(entry)

    for i, entry in enumerate(consolidated, 1):
        entry["number"] = i

    return consolidated


def format_bibliography_for_prompt(consolidated_bibliography: List[Dict]) -> str:
    """Format daftar pustaka konsolidasi jadi teks bernomor untuk dikirim ke AI."""
    lines = []
    for entry in consolidated_bibliography:
        levels_str = ", ".join(f"L{d}" for d in entry.get("levels", []))
        lines.append(
            f"[{entry['number']}] {entry.get('author', 'Tidak diketahui')}. "
            f"{entry.get('media', '-')}. {entry.get('date', '-')}. "
            f"{entry.get('title', 'Tanpa Judul')}. (Ditemukan di: {levels_str})"
        )
    return "\n".join(lines) if lines else "Tidak ada sumber."


def format_level_breakdown_for_prompt(result_tree: List[Dict]) -> str:
    """Format ringkasan + penyebab tiap level jadi teks untuk dikirim ke AI."""
    parts = []
    for lvl in result_tree:
        parts.append(f"--- LEVEL {lvl['depth']} (Query: {', '.join(lvl['queries_used'])}) ---")
        parts.append(f"Ringkasan: {lvl.get('summary', '-')}")
        causes = lvl.get("causes_extracted") or []
        if causes:
            parts.append("Penyebab teridentifikasi di level ini:")
            for c in causes:
                parts.append(f"- {c}")
        parts.append("")
    return "\n".join(parts)


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
                raw_response_text = ai_service.generate(prompt)
                ai_parsed = _parse_ai_json(raw_response_text)
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