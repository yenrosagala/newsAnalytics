import streamlit as st
from app.core.config import Config

def init_auth_session():
    """Inisialisasi variabel session login saat aplikasi pertama kali dimuat."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.role = None
        st.session_state.username = ""


def is_authenticated() -> bool:
    """
    Mengecek status login pengguna.
    st.session_state bersifat per-browser-session dan dibagikan ke SEMUA
    halaman pada aplikasi multipage Streamlit ini -- jadi begitu status ini
    True di sini, ia akan tetap True saat pengguna berpindah ke halaman lain
    (Scraping/Dashboard/Fenomena) TANPA perlu login ulang, selama tab
    browser yang sama tidak ditutup atau di-refresh penuh.
    """
    return bool(st.session_state.get("authenticated", False))


def require_login():
    """
    Dipanggil di baris paling atas setiap halaman yang butuh proteksi login.
    Menghentikan render halaman (st.stop()) jika pengguna belum login.
    """
    if not is_authenticated():
        st.warning("⚠️ Silakan lakukan otorisasi akses (Login) melalui halaman utama (Homepage) terlebih dahulu.")
        st.stop()


def render_login_form():
    """Merender form login di sidebar atau halaman utama.

    Kredensial dibaca dari Config (bersumber dari st.secrets), TIDAK PERNAH
    hardcoded di kode. Jika sebuah role belum punya password dikonfigurasi,
    login untuk role tersebut dinonaktifkan (fail-closed) alih-alih diam-diam
    memakai password default yang mudah ditebak.
    """
    st.sidebar.subheader("🔒 Masuk ke Sistem")

    if not Config.ADMIN_PASSWORD and not Config.USER_PASSWORD:
        st.sidebar.error(
            "⚠️ Belum ada kredensial yang dikonfigurasi. Set ADMIN_PASSWORD "
            "dan/atau USER_PASSWORD di st.secrets sebelum aplikasi bisa dipakai."
        )
        return

    username = st.sidebar.text_input("Username", key="login_user")
    password = st.sidebar.text_input("Password", type="password", key="login_pass")

    if st.sidebar.button("Login"):
        if Config.ADMIN_PASSWORD and username == Config.ADMIN_USERNAME and password == Config.ADMIN_PASSWORD:
            st.session_state.authenticated = True
            st.session_state.role = "admin"
            st.session_state.username = username
            st.sidebar.success("Login Admin Berhasil!")
            st.rerun()
        elif Config.USER_PASSWORD and username == Config.USER_USERNAME and password == Config.USER_PASSWORD:
            st.session_state.authenticated = True
            st.session_state.role = "user"
            st.session_state.username = username
            st.sidebar.success("Login User Berhasil!")
            st.rerun()
        else:
            st.sidebar.error("Username atau password salah!")

def render_logout():
    """Tombol logout untuk membersihkan session state."""
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.role = None
        st.session_state.username = ""
        st.rerun()
