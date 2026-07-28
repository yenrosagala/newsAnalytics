import os
from google import genai
import streamlit as st
from app.core.logger import get_logger

logger = get_logger("AIService")

class AIService:
    def __init__(self):
        # 1. Inisialisasi index dan daftar model cadangan terbaru
        self.active_index = 0
        
        # Daftar model yang akan di-rotate secara berurutan jika model utama habis kuota / error
        self.active_model_index = 0

        self.models_list = [
        "gemini-2.5-flash",
        "gemini-3-flash",
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite"
        ]
        
        self.model_name = self.models_list[self.active_model_index]
        
        # 2. Ambil data mentah dari secrets (dukungan list atau string koma)
        raw_keys = st.secrets.get("GEMINI_API_KEYS")
        
        self.api_keys = []
        if isinstance(raw_keys, list):
            self.api_keys = [str(k).strip() for k in raw_keys if k and str(k).strip()]
        elif isinstance(raw_keys, str):
            self.api_keys = [k.strip() for k in raw_keys.split(",") if k.strip()]
            
        # 3. Eksekusi Klien AI
        if self.api_keys:
            self._init_client()
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
        
        if current_key is None or not isinstance(current_key, str) or current_key.strip() == "":
            logger.error(f"API Key pada index {self.active_index} tidak valid (None/Kosong).")
            self.client = None
            return
            
        try:
            self.client = genai.Client(api_key=current_key.strip())
            logger.info(f"AI Service siap menggunakan API Key index ke-{self.active_index} dengan model {self.model_name}")
        except Exception as e:
            logger.error(f"Gagal inisialisasi Gemini Client: {e}")
            self.client = None

    def rotate_key(self) -> bool:
        """Menggeser ke API key cadangan berikutnya (Round-Robin)"""
        if len(self.api_keys) <= 1:
            return False
            
        self.active_index = (self.active_index + 1) % len(self.api_keys)
        self._init_client()
        logger.warning(f"🔄 Rotasi API Key! Beralih ke index {self.active_index}")
        return True

    def rotate_key_for_level(self, level_depth: int):
        """Menggeser API Key secara otomatis berdasarkan level rekursif (1, 2, 3, dst)."""
        if not self.api_keys:
            return
        self.active_index = (level_depth - 1) % len(self.api_keys)
        self._init_client()
        logger.info(f"🔄 [Level {level_depth}] Rotasi otomatis ke API Key index ke-{self.active_index}")

    def rotate_model(self) -> bool:
        """Menggeser ke model AI cadangan berikutnya jika model saat ini habis kuota"""
        if len(self.models_list) <= 1:
            return False
            
        self.active_model_index = (self.active_model_index + 1) % len(self.models_list)
        self.model_name = self.models_list[self.active_model_index]
        logger.warning(f"🧠🔄 Rotasi Model AI! Beralih menggunakan model: {self.model_name}")
        return True

    def analyze_article(self, full_text: str) -> dict:
        """Analisis artikel dengan mekanisme rotasi ganda: API Key & Model AI otomatis."""
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
        
        # Total kombinasi percobaan maksimal (jumlah key * jumlah model)
        max_attempts = (len(self.api_keys) * len(self.models_list)) if self.api_keys else 1
        attempts = 0

        while attempts < max_attempts:
            if not self.client:
                return {"summary": "Gagal memproses AI: Klien tidak aktif.", "sentiment": "Neutral"}
                
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                text_res = response.text
                
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
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    logger.warning(f"⚠️ Limit tercapai pada (Key Index: {self.active_index}, Model: {self.model_name}). Mencoba rotasi...")
                    
                    # Prioritaskan rotasi model terlebih dahulu pada key yang sama
                    rotated_model = self.rotate_model()
                    
                    # Jika model sudah berputar penuh kembali ke awal, baru rotasi API Key berikutnya
                    if not rotated_model or self.active_model_index == 0:
                        rotated_key = self.rotate_key()
                        if not rotated_key and not rotated_model:
                            break
                            
                    attempts += 1
                else:
                    logger.error(f"Gagal memproses AI: {err_str}")
                    return {"summary": f"Gagal memproses rangkuman AI: {err_str}", "sentiment": "Neutral"}
        
        return {"summary": "Gagal: Seluruh cadangan API Key dan Model AI telah habis kuotanya (RESOURCE_EXHAUSTED).", "sentiment": "Neutral"}

# Singleton instance
ai_service = AIService()