from sklearn.feature_extraction.text import TfidfVectorizer
from app.core.logger import setup_logger

logger = setup_logger("sentiment_service")

class SentimentService:
    def __init__(self):
        self.positif_lexicon = ['untung', 'naik', 'positif', 'laba', 'stabil', 'bagus', 'tumbuh', 'maju', 'berhasil', 'suplai', 'cukup']
        self.negatif_lexicon = ['rugi', 'turun', 'negatif', 'inflasi', 'mahal', 'sulit', 'krisis', 'buruk', 'gagal', 'kurang', 'langka']
        logger.info("SentimentService initialized with TF-IDF.")

    def analyze_text(self, text: str) -> str:
        if not text or len(text.strip()) < 50: return "Neutral"
        try:
            vectorizer = TfidfVectorizer(stop_words='english') 
            tfidf_matrix = vectorizer.fit_transform([text.lower()])
            feature_names = vectorizer.get_feature_names_out()
            scores = tfidf_matrix.toarray()[0]
            
            word_weights = dict(zip(feature_names, scores))
            total_score = sum(weight for word, weight in word_weights.items() if word in self.positif_lexicon) - \
                          sum(weight for word, weight in word_weights.items() if word in self.negatif_lexicon)
            
            if total_score > 0.02: return "POSITIVE"
            elif total_score < -0.02: return "NEGATIVE"
            return "NEUTRAL"
        except:
            return "Neutral"

sentiment_service = SentimentService()