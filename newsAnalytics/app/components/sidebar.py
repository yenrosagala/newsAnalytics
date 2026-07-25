import streamlit as st

def render_sidebar() -> None:
    """Rendering sidebar untuk navigasi dan filter."""
    with st.sidebar:
        st.title("🔐 Otorisasi Akses")
        # Logika login dipindahkan ke sini
        if not st.session_state["authenticated"]:
            if st.button("Masuk"): 
                st.session_state["authenticated"] = True
                st.rerun()