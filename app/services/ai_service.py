import os
from google import genai
import streamlit as st
from app.core.logger import get_logger

logger = get_logger("AIService")

class AIService:
    def __init__(self):
        # 1. Ambil data mentah dari secrets
        raw_keys = st.secrets.get("GEMINI_API_KEYS")
        
        # 2. Ekstrak menjadi list string yang bersih (Apapun format asli di toml-nya)
        self.api_keys = []
        if isinstance(raw_keys, list):
            # Jika di toml formatnya array: ["key1", "key2"]
            self.api_keys = [str(k).strip() for k in raw_keys if k and str(k).strip()]
        elif isinstance(raw_keys, str):
            # Jika di toml formatnya string koma: "key1, key2" atau cuma 1 "key1"
            self.api_keys = [k.strip() for k in raw_keys.split(",") if k.strip()]
            
        # 3. Eksekusi Klien AI
        if self.api_keys:
            # ✅ KUNCI PERBAIKAN: Kita HANYA mengambil elemen PERTAMA (index 0) 
            # dari list untuk dimasukkan ke Client, BUKAN memasukkan list-nya!
            kunci_aktif = self.api_keys[0] 
            
            self.client = genai.Client(api_key=kunci_aktif)
            self.model_name = 'gemini-2.5-flash'
            logger.info("AI Service berhasil diinisialisasi.")
        else:
            self.client = None
            logger.error("GAGAL: GEMINI_API_KEYS kosong atau format salah di secrets.toml!")

    def _init_client(self):
        """Membuat instance client dengan validasi strict"""
        if not self.api_keys:
            logger.error("Daftar API Key kosong. Klien AI tidak dijalankan.")
            self.client = None
            return

        current_key = self.api_keys[self.active_index]
        
        # VALIDASI FINAL: Pastikan key benar-benar string dan tidak kosong
        if current_key is None or not isinstance(current_key, str) or current_key.strip() == "":
            logger.error(f"API Key pada index {self.active_index} tidak valid (None/Kosong).")
            self.client = None
            return
            
        try:
            # Hanya jalankan jika kita yakin itu adalah string
            self.client = genai.Client(api_key=current_key.strip())
            logger.info(f"AI Service siap menggunakan API Key index ke-{self.active_index}")
        except Exception as e:
            logger.error(f"Gagal inisialisasi Gemini Client: {e}")
            self.client = None

    def rotate_key(self) -> bool:
        """Menggeser ke API key cadangan berikutnya (Round-Robin)"""
        if len(self.api_keys) <= 1:
            logger.error("Hanya ada 1 API key. Tidak bisa rotasi!")
            return False
            
        # Geser index, jika sudah di ujung, kembali ke 0
        self.active_index = (self.active_index + 1) % len(self.api_keys)
        self._init_client()
        logger.warning(f"🔄 Rotasi API Key! Beralih ke index {self.active_index}")
        return True

    def analyze_article(self, full_text: str) -> dict:
        """Satu kali request API untuk mendapatkan Rangkuman & Sentimen sekaligus."""
        if not self.client:
            return {"summary": "Gagal: API Key tidak ada", "sentiment": "Neutral"}
            
        if not full_text or len(full_text.strip()) < 150:
            return {"summary": "Konten berita terlalu pendek untuk dirangkum.", "sentiment": "Neutral"}
            
        prompt = (
            "Bertindaklah sebagai analis media profesional. Analisis berita berikut:\n\n"
            f"{full_text}\n\n"
            "Berikan hasil persis dalam format berikut (tanpa basa-basi):\n"
            "SENTIMEN: [Isi dengan Positif, Negatif, atau Netral]\n"
            "RANGKUMAN:\n- [Poin 1]\n- [Poin 2]\n- [Poin 3]"
        )
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            text_res = response.text
            
            # Parsing sederhana untuk memisahkan Sentimen dan Rangkuman
            sentiment_label = "Neutral"
            if "SENTIMEN: Positif" in text_res or "SENTIMEN: POSITIF" in text_res: 
                sentiment_label = "Positive"
            elif "SENTIMEN: Negatif" in text_res or "SENTIMEN: NEGATIF" in text_res: 
                sentiment_label = "Negative"
                
            return {
                "summary": text_res,
                "sentiment": sentiment_label
            }
        except Exception as e:
            logger.error(f"Gagal memproses AI: {str(e)}")
            return {"summary": f"Gagal memproses rangkuman AI: {str(e)}", "sentiment": "Neutral"}

# Singleton instance
ai_service = AIService()
