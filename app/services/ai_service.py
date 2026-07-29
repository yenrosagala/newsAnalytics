import streamlit as st
from google import genai
from typing import Optional
from app.core.logger import get_logger
from app.services.gwen_ai_service import call_gwen_ai # New import for Gwen AI

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
            raise Exception("Tidak ada API key yang dikonfigurasi.")

        try:
            genai.configure(api_key=self.api_keys[self.active_index])
            self.client = genai.get_client()
            logger.info(f"AI Service terinisialisasi dengan API Key index {self.active_index}.")
        except Exception as e:
            logger.error(f"Gagal menginisialisasi Google GenAI client: {e}")
            self.client = None # Pastikan client diset None jika inisialisasi gagal


    def rotate_key(self) -> bool:
        """Memutar ke API key berikutnya. Mengembalikan True jika ada key lain yang tersedia, False jika tidak."""
        if not self.api_keys:
            return False

        self.active_index = (self.active_index + 1) % len(self.api_keys)
        if self.active_index == 0:
            logger.warning("Semua API key telah dicoba. Tidak ada key cadangan lagi.")
            return False # Sudah mencoba semua key dan kembali ke awal

        self._init_client()
        return True

    def _is_auth_error(self, e: Exception) -> bool:
        """Memeriksa apakah error adalah kesalahan otentikasi berdasarkan pesan error."""
        error_message = str(e).upper()
        return any(marker in error_message for marker in AUTH_ERROR_MARKERS)

    def generate(self, prompt: str) -> str:
        """Menghasilkan konten dari model AI dengan rotasi API key dan fallback ke Gwen AI jika terjadi kegagalan."""
        if not self.client:
            # Fallback to Gwen AI immediately if primary AI service is not initialized
            logger.warning("Primary AI Service not initialized. Attempting fallback to Gwen AI.")
            success, gwen_response = call_gwen_ai(prompt)
            if success:
                logger.info("Successfully used Gwen AI as fallback.")
                return gwen_response
            else:
                logger.error(f"Gwen AI fallback failed: {gwen_response}")
                raise Exception(f"AI Service not initialized and Gwen AI fallback failed: {gwen_response}")

        last_error = None
        for _ in range(len(self.api_keys)): # Try all primary keys once
            try:
                response = self.client.models.generate_content(model=self.model_name, contents=prompt)
                return response.text
            except Exception as e:
                last_error = e
                if self._is_auth_error(e) and self.rotate_key():
                    logger.warning(f"Primary API key failed authentication, trying next backup key. Detail: {e}")
                    continue
                # If it's not an auth error, or if rotation failed, break and try fallback
                break

        # If primary AI failed (either all keys exhausted or a non-auth error occurred)
        if last_error:
            if self._is_auth_error(last_error):
                logger.error(
                    "ALL configured primary API keys failed authentication (401/UNAUTHENTICATED). "
                    "This is likely NOT a code bug -- check if keys are valid, not expired, and "
                    f"formatted as 'AIza...' (not 'AQ.'). Original error: {last_error}"
                )
            else:
                logger.warning(f"Primary AI generation failed with error: {last_error}. Attempting fallback to Gwen AI.")

            # Attempt Gwen AI fallback
            success, gwen_response = call_gwen_ai(prompt)
            if success:
                logger.info("Successfully used Gwen AI as fallback.")
                return gwen_response
            else:
                logger.error(f"Gwen AI fallback also failed: {gwen_response}")
                raise Exception(f"Primary AI failed and Gwen AI fallback also failed: {gwen_response}. Original error: {last_error}")

        # This part should ideally not be reached if an error occurred, but as a safeguard:
        raise Exception("AI generation failed for an unknown reason and no fallback was successful.")

    def analyze_article(self, full_text: str) -> dict:
        """Satu kali request API untuk mendapatkan Rangkuman & Sentimen sekaligus."""
        if not self.client:
            # Try Gwen AI for analysis if primary is not available
            logger.warning("Primary AI client not available for analyze_article. Attempting Gwen AI fallback.")
            try:
                success, gwen_response = call_gwen_ai(
                    f"""Act as a professional media analyst. Analyze the following news and provide
sentiment (Positive, Negative, or Neutral) and a summary in the format:
SENTIMENT: [Point 1]
SUMMARY:
- [Point 1]
- [Point 2]
- [Point 3]

{full_text}"""
                )
                if success:
                    sentiment_label = "Neutral"
                    if "SENTIMEN: Positif" in gwen_response or "SENTIMEN: POSITIF" in gwen_response:
                        sentiment_label = "Positive"
                    elif "SENTIMEN: Negatif" in gwen_response or "SENTIMEN: NEGATIF" in gwen_response:
                        sentiment_label = "Negative"
                    return {"summary": gwen_response, "sentiment": sentiment_label}
                else:
                    return {"summary": f"Failed to process with primary AI and Gwen AI fallback: {gwen_response}", "sentiment": "Neutral"}
            except Exception as e:
                logger.error(f"Gwen AI fallback for analyze_article failed: {str(e)}")
                return {"summary": f"Failed to process with primary AI and Gwen AI fallback due to error: {str(e)}", "sentiment": "Neutral"}

        if not full_text or len(full_text.strip()) < 150:
            return {"summary": "Konten berita terlalu pendek untuk dirangkum.", "sentiment": "Neutral"}

        prompt = f"""Bertindaklah sebagai analis media profesional. Analisis berita berikut:

{full_text}

Berikan hasil persis dalam format berikut (tanpa basa-basi):
SENTIMEN: [Isi dengan Positif, Negatif, atau Netral]
RANGKUMAN:
- [Poin 1]
- [Poin 2]
- [Poin 3]"""

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