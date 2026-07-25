import re
from pathlib import Path

import streamlit as st


def _cari_repositori_sentimen():
    candidates = [
        Path("/tmp/sentimen-bahasa"),
        Path("/workspaces/sentimen-bahasa"),
        Path(__file__).resolve().parents[1] / "sentimen-bahasa",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _baca_kamus_leksikon(path):
    kamus = {}
    if not path:
        return kamus

    for nama_file, pemisah in [
        ("sentiwords_id.txt", ":"),
        ("emoticon_id.txt", " | "),
        ("idioms_id.txt", ":"),
        ("boosterwords_id.txt", ":"),
    ]:
        file_path = path / "leksikon" / "sentistrength_id" / nama_file
        if not file_path.exists():
            continue
        with file_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if pemisah in line:
                    parts = line.split(pemisah, 1)
                else:
                    parts = line.split()
                if len(parts) >= 2:
                    key = parts[0].strip().lower()
                    try:
                        value = int(parts[1].strip())
                    except ValueError:
                        continue
                    kamus[key] = value

    return kamus


def _baca_daftar_negasi(path):
    file_path = path / "leksikon" / "sentistrength_id" / "negatingword.txt"
    if not file_path.exists():
        return []
    with file_path.open("r", encoding="utf-8") as handle:
        return [line.strip().lower() for line in handle if line.strip() and not line.startswith("#")]


def _baca_daftar_tanya(path):
    file_path = path / "leksikon" / "sentistrength_id" / "questionword.txt"
    if not file_path.exists():
        return []
    with file_path.open("r", encoding="utf-8") as handle:
        return [line.strip().lower() for line in handle if line.strip() and not line.startswith("#")]


@st.cache_resource
def muat_model_sentimen_repo():
    repo_dir = _cari_repositori_sentimen()
    if repo_dir:
        kamus = _baca_kamus_leksikon(repo_dir)
        negasi = _baca_daftar_negasi(repo_dir)
        tanya = _baca_daftar_tanya(repo_dir)
        if kamus:
            return {
                "kamus": kamus,
                "negasi": negasi,
                "tanya": tanya,
            }

    return {
        "kamus": {
            "sukses": 5, "berhasil": 5, "untung": 4, "surplus": 5, "tumbuh": 3, "meningkat": 3,
            "naik": 2, "pulih": 4, "optimal": 4, "bagus": 3, "baik": 3, "aman": 4, "stabil": 4,
            "prestasi": 5, "juara": 5, "hebat": 4, "unggul": 4, "maju": 3, "berkembang": 3,
            "efektif": 4, "efisien": 4, "inovasi": 4, "apresiasi": 4, "mendukung": 3, "setuju": 3,
            "puas": 4, "senang": 3, "bahagia": 4, "investasi": 2, "bantuan": 3, "membaik": 4,
            "gagal": -5, "rugi": -4, "krisis": -5, "anjlok": -4, "turun": -2, "merosot": -4,
            "korupsi": -5, "suap": -5, "pungli": -4, "tewas": -5, "korban": -4, "inflasi": -3,
            "defisit": -4, "sanksi": -4, "buruk": -4, "bahaya": -4, "ancaman": -4, "hancur": -5,
            "kecewa": -4, "marah": -4, "protes": -3, "ditangkap": -3, "tersangka": -4, "lemah": -3,
        },
        "negasi": ["tidak", "tak", "bukan", "jangan", "tanpa", "kurang"],
        "tanya": ["apa", "siapa", "kapan", "mengapa", "bagaimana"],
    }


def hitung_sentimen_leksikon(teks):
    if not teks or not str(teks).strip() or "[Gagal Ekstrak]" in str(teks):
        return "Netral"

    model = muat_model_sentimen_repo()
    kamus = model["kamus"]
    negasi = set(model.get("negasi", []))
    pertanyaan = set(model.get("tanya", []))

    teks_bersih = re.sub(r"http\S+|www\.\S+", " ", str(teks).lower())
    teks_bersih = re.sub(r"[^a-z0-9\s]", " ", teks_bersih)
    teks_bersih = re.sub(r"\s+", " ", teks_bersih).strip()

    if not teks_bersih:
        return "Netral"

    total_skor = 0
    kata_kata = teks_bersih.split()
    for idx, kata in enumerate(kata_kata):
        kata_plain = re.sub(r"([a-z])\1{2,}", r"\1", kata)
        if kata_plain in kamus:
            skor = kamus[kata_plain]
            if idx > 0 and kata_kata[idx - 1] in negasi:
                skor = -abs(skor)
            total_skor += skor
        elif kata_plain in pertanyaan:
            total_skor += 0

    if total_skor > 1:
        return "Positif"
    if total_skor < -1:
        return "Negatif"
    return "Netral"
