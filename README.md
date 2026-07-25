# 📰 News Intelligence Dashboard

Google News Scraping • Sentiment Analysis • Real-time Monitoring

A comprehensive Streamlit application for scraping Google News, performing sentiment analysis, and monitoring news trends with an interactive dashboard.

## Features

✨ **Core Functionality**
- 🚀 Multi-keyword Google News scraping with parallel processing
- 📊 Sentiment analysis using lexicon-based approach
- 📈 Real-time dashboard with KPI cards and visualizations
- 💾 SQLite & PostgreSQL database support
- 👥 Dual user authentication (User Umum & User Login)
- 🔒 Role-based access control (delete permissions)
- 📝 Executive summary generation from article content

## Quick Start - Local Development

### Prerequisites
- Python 3.8+
- pip or conda

### Installation

1. Clone the repository
   ```bash
   git clone https://github.com/yenrosagala/Google_News_Scrapping.git
   cd Google_News_Scrapping
   ```

2. Create and activate virtual environment
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application
   ```bash
   streamlit run streamlit_app.py
   ```

The app will open at `http://localhost:8501`

## Deployment to Streamlit Cloud

### Step 1: Push to GitHub

```bash
git add .
git commit -m "Prepare for Streamlit Cloud deployment"
git push origin main
```

### Step 2: Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click "New app"
3. Select your GitHub repo: `yenrosagala/Google_News_Scrapping`
4. Branch: `main`
5. Main file path: `streamlit_app.py`
6. Click "Deploy"

### Step 3: Configure Secrets (if using PostgreSQL)

1. In Streamlit Cloud dashboard, go to **Settings** → **Secrets**
2. Add your database configuration:
   ```toml
   DATABASE_URL_TEMPLATE = "postgresql://user:password@host:port/dbname"
   ```
3. Save changes (app will auto-rerun)

### Default Configuration

If no secrets are configured, the app uses **SQLite** database at `berita_google_news.db` (local file storage).

## User Types

### 👥 User Umum (General User)
- ✅ Access dashboard without password
- ✅ View all data and analytics
- ❌ Cannot delete database
- **Perfect for**: Stakeholders, viewers

### 🔐 User Login (Admin)
- ✅ Access dashboard with password authentication
- ✅ View all data and analytics
- ✅ Delete all database records
- **Perfect for**: Administrators, data managers

## Project Structure

```
Google_News_Scrapping/
├── app/
│   ├── __init__.py
│   ├── database.py          # Database abstraction layer
│   ├── scraper.py           # Google News scraper
│   ├── sentiment.py         # Sentiment analysis
│   └── ui.py                # Streamlit dashboard
├── .streamlit/
│   ├── config.toml          # Streamlit configuration
│   └── secrets.toml.example # Secrets template
├── streamlit_app.py         # App entry point
├── requirements.txt         # Python dependencies
└── README.md
```

## Configuration

### Local Development
- Create `.streamlit/secrets.toml` (optional):
  ```toml
  DATABASE_URL_TEMPLATE = "postgresql://..."
  ```

### Streamlit Cloud
- Set secrets via dashboard (Settings → Secrets)
- Environment variables are automatically loaded

## Technologies

- **Frontend**: Streamlit, Plotly, Pandas
- **Backend**: Python, NLTK, Newspaper3k
- **Database**: SQLite / PostgreSQL
- **Scraping**: feedparser, googlenewsdecoder
- **Sentiment**: Lexicon-based with negation support

## Performance Tips

1. **Database**: Use PostgreSQL for production (better concurrency)
2. **Caching**: Streamlit caching (@st.cache_data) is enabled for summaries
3. **Threading**: Parallel article processing with ThreadPoolExecutor
4. **Connection Pooling**: Requests session with pooled connections

## Troubleshooting

### "database connection failed"
- Check DATABASE_URL_TEMPLATE in secrets
- If empty, app uses SQLite (create berita_google_news.db)

### "NLTK tokenizer not found"
- Downloaded automatically on first run
- Check internet connection

### "Playwright browser not found"
- Run: `playwright install`

## Development Notes

### Adding New Features
1. Update relevant file (scraper.py, sentiment.py, ui.py)
2. Test locally: `streamlit run streamlit_app.py`
3. Commit and push changes
4. Streamlit Cloud auto-redeploys on push

### Database Schema
```sql
CREATE TABLE artikel (
    id SERIAL PRIMARY KEY,
    kata_kunci VARCHAR,
    judul VARCHAR,
    media VARCHAR,
    waktu_tampilan TIMESTAMP,
    waktu_iso VARCHAR,
    link VARCHAR,
    isi_konten TEXT
);
```

## License

See LICENSE file

## Author

Yenro Sagala - BPS Provinsi Papua
