import streamlit as st
import pandas as pd

def render_kpi(df: pd.DataFrame) -> None:
    """Menampilkan KPI utama dashboard."""
    col_media = "source" if "source" in df.columns else "media"
    col_keyword = "keyword" if "keyword" in df.columns else "kata_kunci"
    
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Total Berita Terfilter", len(df))
    kpi2.metric("Portal Media Unik", df[col_media].nunique())
    kpi3.metric("Keyword Aktif", df[col_keyword].nunique())