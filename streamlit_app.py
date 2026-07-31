import streamlit as st
import os

st.set_page_config(
    page_title="NewsAnalytics AI Hub",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

css_path = "app/assets/style.css"
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### ⚡ NewsAnalytics AI")
    st.caption("AI Decision Intelligence Platform")
    st.markdown("---")
    st.page_link("streamlit_app.py", label="Home", icon="🏠")
    st.page_link("pages/1_Scraping.py", label="AI Understanding", icon="📥")
    st.page_link("pages/2_Dashboard.py", label="Analytics Dashboard", icon="📊")
    st.page_link("pages/3_Fenomena.py", label="AI Investigator", icon="🕵️")
    
    st.markdown("---")
    st.markdown("""
    <div style="background: rgba(0,240,255,0.05); padding: 12px; border-radius: 8px; border: 1px solid rgba(0,240,255,0.1);">
        <small style="color: #00f0ff; font-weight: 600;">SYSTEM STATUS</small><br>
        <span style="color: #10b981; font-size: 0.85rem;">● AI Engines Online</span><br>
        <span style="color: #94a3b8; font-size: 0.75rem;">v2.5.0 Professional</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown("# ⚡ NewsAnalytics Professional Hub")
st.markdown("### AI Decision Intelligence Platform — Ubah Berita Menjadi Intelijen yang Actionable")
st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class="feature-card">
        <h3>📥 AI Understanding</h3>
        <p style="color: #94a3b8; font-size: 0.9rem;">Mengekstrak informasi berita secara real-time dan mengelola penyimpanan ringkasan eksekutif menggunakan format tabel yang sistematis.</p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Buka News Scraper", key="btn_scraping", width='stretch', type="primary"):
        st.switch_page("pages/1_Scraping.py")

with col2:
    st.markdown("""
    <div class="feature-card">
        <h3>📊 Analytics Dashboard</h3>
        <p style="color: #94a3b8; font-size: 0.9rem;">Visualisasi data mendalam dengan filter horizontal di bagian atas untuk ruang kerja grafik yang lebih luas.</p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Buka Analytics Dashboard", key="btn_dashboard", width='stretch', type="primary"):
        st.switch_page("pages/2_Dashboard.py")

with col3:
    st.markdown("""
    <div class="feature-card">
        <h3>🕵️ AI Investigator</h3>
        <p style="color: #94a3b8; font-size: 0.9rem;">Telusuri akar masalah secara rekursif mendalam, lengkap dengan evidence graph & skor keyakinan, dirangkum sebagai Executive Intelligence Brief.</p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Buka AI Investigator", key="btn_fenomena", width='stretch', type="primary"):
        st.switch_page("pages/3_Fenomena.py")
