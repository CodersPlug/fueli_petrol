import streamlit as st
import sys
from pathlib import Path

# Add the project root directory to Python path
root_dir = Path(__file__).parent.absolute()
sys.path.append(str(root_dir))

# Import tabs
from tabs import gnc, liquidos, taller, tienda

# Set page config
st.set_page_config(
    page_title="Fueli Petrol",
    page_icon="⛽",
    layout="wide"
)

# Add a header
st.title("Panel de Control")
st.markdown("---")

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs(["GNC", "Líquidos", "Taller", "Tienda"])

# Render each tab
with tab1:
    gnc.render()

with tab2:
    liquidos.render()

with tab3:
    taller.render()

with tab4:
    tienda.render()

# Add footer
st.markdown("---")
st.markdown("<div style='text-align: center; font-size: 0.8em; color: #666;'>Desarrollado por Fueli</div>", unsafe_allow_html=True)
