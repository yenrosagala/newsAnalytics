import streamlit as st
from google import genai
from typing import Optional
from app.core.logger import get_logger

logger = get_logger("AIService")

# Penanda dalam pesan error yang mengindikasikan masalah OTENTIKASI (bukan bug kode)
AUTH_ERROR_MARKERS = (
    "UNAUTHENTICATED",
    "401",
    "ACCESS_TOKEN_TYPE_UNSUPPORTED",
    "API_KEY_INVALID",
    "API_KEY_SERVICE_BLOCKED",
    "PERMISSION_DENIED",
)


class AIService:
    def __init__(self):
        raw_keys = st.secrets.get("GEMINI_API_KEYS")

        self.api_keys = []
        if isinstance(raw_keys, list):
            self.api_keys = [str(k).strip() for k in raw_keys if k and str(k).strip()]
        elif isinstance(raw_keys, str):
            self.api_keys = [k.strip() for k in raw_keys.split(",") if k.strip()]

        self.model_name = "gemini-2.5-flash"
        self.active_index = 0
        self.client: Optional[genai.Client] = None

        for key in self.api_keys:
            if not key.startswith("AIza"):
                logger.warning(
                    f"GEMINI_API_KEYS berisi key berformat tidak lazim ('{key[:6]}...'). "
                    "Key Gemini Developer API yang valid umumnya berawalan 'AIza'. Jika key ini "
                    "berawalan 'AQ.', ini kemungkinan penyebab error 401 ACCESS_TOKEN_TYPE_UNSUPPORTED "
                    "-- coba generate ulang key baru di Google AI Studio."
                )

        if self.api_keys:
            self._init_client()
        else:
            logger.error("GAGAL: GEMINI_API_KEYS kosong atau format salah di st.secrets!")

    def _init_client(self):
        """Membuat instance client dari key pada self.active_index, dengan validasi strict."""
        if not self.api_keys:
            self.client = None
            return

        current_key = self.api_keys[self.active_index]
        if not current_key:
            logger.error(f"API Key pada index {self.active_index} kosong/tidak valid.")
            self.client = None
            return

        try:
            self.client = genai.Client(api_key=current_key)
            logger.info(f"AI Service siap menggunakan API Key index ke-{self.active_index}.")
        except Exception as e:
            logger.error(f"Gagal inisialisasi Gemini Client (index {self.active_index}): {e}")
            self.client = None

    def rotate_key(self) -> bool:
        """Beralih ke API key cadangan berikutnya (round-robin).

        Return False jika hanya ada 1 key (tidak ada yang bisa dirotasi).
        """
        if len(self.api_keys) <= 1:
            return False
        self.active_index = (self.active_index + 1) % len(self.api_keys)
        self._init_client()
        logger.warning(f"Rotasi API Key -> index {self.active_index}.")
        return True

    @staticmethod
    def _is_auth_error(exc: Exception) -> bool:
        text = str(exc).upper()
        return any(marker in text for marker in AUTH_ERROR_MARKERS)

    def generate(self, prompt: str) -> str:
        """Titik masuk TUNGGAL untuk semua pemanggilan Gemini di aplikasi ini.

        Kalau key aktif gagal karena error otentikasi (401/UNAUTHENTICATED/dst),
        otomatis mencoba key berikutnya di GEMINI_API_KEYS sebelum menyerah --
        ini memperbaiki celah lama di mana key cadangan tidak pernah benar-benar
        dipakai walau sudah dikonfigurasi.
        """
        if not self.client:
            raise RuntimeError("Gemini client belum terkonfigurasi. Periksa GEMINI_API_KEYS di st.secrets.")

        attempts = max(1, len(self.api_keys))
        last_error: Optional[Exception] = None

        for _ in range(attempts):
            try:
                response = self.client.models.generate_content(model=self.model_name, contents=prompt)
                return response.text
            except Exception as e:
                last_error = e
                if self._is_auth_error(e) and self.rotate_key():
                    logger.warning(f"API key gagal otentikasi, mencoba key cadangan berikutnya. Detail: {e}")
                    continue
                break

        if last_error and self._is_auth_error(last_error):
            logger.error(
                "SEMUA API key yang dikonfigurasi gagal otentikasi (401/UNAUTHENTICATED). Ini kemungkinan "
                "besar BUKAN bug kode -- periksa apakah key masih valid, belum expired, dan berformat "
                f"'AIza...' (bukan 'AQ.'). Detail error asli: {last_error}"
            )
        raise last_error

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
            text_res = self.generate(prompt)
            sentiment_label = "Neutral"
            if "SENTIMEN: Positif" in text_res or "SENTIMEN: POSITIF" in text_res:
                sentiment_label = "Positive"
            elif "SENTIMEN: Negatif" in text_res or "SENTIMEN: NEGATIF" in text_res:
                sentiment_label = "Negative"
            return {"summary": text_res, "sentiment": sentiment_label}
        except Exception as e:
            logger.error(f"Gagal memproses AI: {str(e)}")
            return {"summary": f"Gagal memproses rangkuman AI: {str(e)}", "sentiment": "Neutral"}


# Singleton instance
ai_service = AIService()