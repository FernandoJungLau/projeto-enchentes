"""Dashboard das enchentes de Porto Alegre (INCT SiMAI).

Rodar a partir da raiz do repositório:
    streamlit run app/app.py
"""

import streamlit as st

import estilo

st.set_page_config(
    page_title="Enchentes em Porto Alegre: simulação do INCT SiMAI",
    page_icon=":material/water:",
    layout="wide",
)
estilo.aplicar_css()

pg = st.navigation([
    st.Page("tela1.py", title="Simulação do INCT", default=True),
    st.Page("tela2.py", title="O que outras fontes de dados nos dizem?"),
])

pg.run()
