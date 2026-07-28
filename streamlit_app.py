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
    st.caption("Futuristic Intelligence & Root Cause Engine")
    st.markdown("---")
    st.page_link("streamlit_app.py", label="Home Dashboard", icon="🏠")
    st.page_link("pages/1_Scraping.py", label="News Insight", icon="📥")
    st.page_link("pages/2_Dashboard.py", label="Analytics & Metrics", icon="📊")
    st.page_link("pages/3_Fenomena.py", label="Root Cause", icon="🔍")
    
    st.markdown("---")
    st.markdown("""
    <div style="background: rgba(0,240,255,0.05); padding: 12px; border-radius: 8px; border: 1px solid rgba(0,240,255,0.1);">
        <small style="color: #00f0ff; font-weight: 600;">SYSTEM STATUS</small><br>
        <span style="color: #10b981; font-size: 0.85rem;">● AI Engines Online</span><br>
        <span style="color: #94a3b8; font-size: 0.75rem;">v2.5.0 Professional</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown("# ⚡ NewsAnalytics Professional Hub")
st.markdown("### Platform Analisis Berita & Root Cause Intelligence Berbasis AI")
st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class="feature-card">
        <h3>📥 The Insight Engine</h3>
        <p style="color: #94a3b8; font-size: 0.9rem;">Ambil data berita terkini secara real-time dan kelola ringkasan eksekutif tersimpan melalui tabel terstruktur.</p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Buka Scraping Hub", key="btn_scraping", use_container_width=True, type="primary"):
        st.switch_page("pages/1_Scraping.py")

with col2:
    st.markdown("""
    <div class="feature-card">
        <h3>📊 Analytics Dashboard</h3>
        <p style="color: #94a3b8; font-size: 0.9rem;">Visualisasi data mendalam dengan filter horizontal di bagian atas untuk ruang kerja grafik yang lebih luas.</p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Buka Dashboard", key="btn_dashboard", use_container_width=True, type="primary"):
        st.switch_page("pages/2_Dashboard.py")

with col3:
    st.markdown("""
    <div class="feature-card">
        <h3>🔍 Root Cause Analysis</h3>
        <p style="color: #94a3b8; font-size: 0.9rem;">Analisis akar masalah secara rekursif mendalam dilengkapi panduan visual interaktif pada area kosong.</p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Buka Fenomena Analysis", key="btn_fenomena", use_container_width=True, type="primary"):
        st.switch_page("pages/3_Fenomena.py")