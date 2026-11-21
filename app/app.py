"""Dashboard das enchentes de Porto Alegre (INCT SiMAI).

Rodar a partir da raiz do repositório:
    streamlit run app/app.py
"""

import streamlit as st

st.set_page_config(
    page_title="Enchentes em Porto Alegre: simulação do INCT SiMAI",
    page_icon=":material/water:",
    layout="wide",
)

pg = st.navigation([
    st.Page("tela1.py", title="Simulação do INCT", default=True),
    st.Page("tela2.py", title="Comparação com maio de 2024"),
])

pg.run()
