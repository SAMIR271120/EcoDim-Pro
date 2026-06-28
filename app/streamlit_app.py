"""
app/streamlit_app.py — Point d'entrée EcoDim Pro
Lance Streamlit avec : streamlit run app/streamlit_app.py
Redirige automatiquement vers la gestion des dossiers (page 1).
"""
import sys
from pathlib import Path
root_path = str(Path(__file__).resolve().parent.parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

import streamlit as st
from ecodimpro.session import init_session
from ecodimpro.ui import inject_css

st.set_page_config(
    page_title="EcoDim Pro",
    page_icon="logo/ecodimpro_favicon_64_1.png",
    layout="wide",
    initial_sidebar_state="expanded"
)
inject_css(st)
init_session(st.session_state)

# Redirection immédiate vers la page d'accueil dossiers
st.switch_page("pages/1_accueil_dossiers.py")
