"""Cores e aparência comuns aos gráficos.

Azul é a única cor de destaque; o resto fica em cinza. Não usamos vermelho, para
não passar ideia de alarme.
"""

from pathlib import Path

import streamlit as st

ASSETS = Path(__file__).resolve().parent / "assets"

AZUL = "#2a78d6"  # série principal / destaque
AZUL_ESCURO = "#0d3b73"  # nível escolhido (contraste com o azul da série)
CINZA = "#a3a29c"  # contexto, referências
CINZA_BARRA = "#cdd3da"  # barras de contexto (o azul fica só no que está em destaque)
CINZA_TEXTO = "#52514e"
MANCHA = "rgba(42, 120, 214, 0.25)"  # preenchimento da mancha de inundação

# Escala sequencial de uma cor só (claro -> escuro) para % e mapas.
ESCALA_SEQ = [[0.0, "#e8f0fb"], [0.5, "#5b9be3"], [1.0, "#0d3b73"]]

FONTE = dict(family='"Source Sans", "Source Sans Pro", sans-serif', size=13, color=CINZA_TEXTO)


def layout_base(fig, altura=380, **kw):
    """Fundo neutro, grade discreta, sem título interno (o título fica no st.subheader)."""
    padrao = dict(
        template="plotly_white",
        height=altura,
        margin=dict(l=10, r=20, t=30, b=10),
        font=FONTE,
        hoverlabel=dict(font_size=13),
        showlegend=False,
        separators=",.",  # vírgula decimal, ponto de milhar
    )
    fig.update_layout(**(padrao | kw))
    fig.update_xaxes(gridcolor="#eeeeec", zeroline=False)
    fig.update_yaxes(gridcolor="#eeeeec", zeroline=False)
    return fig


CONFIG_PLOTLY = {"displaylogo": False, "locale": "pt-BR"}


def faixa_foto(arquivo: str, legenda: str, autor: str, url: str, extra: str = "") -> None:
    """Foto em faixa no topo da tela, com o crédito pedido pela licença logo abaixo."""
    st.image(str(ASSETS / arquivo), width="stretch")
    st.markdown(
        '<p style="font-size:0.72rem;color:#8a8984;margin:-0.6rem 0 0.4rem;text-align:right">'
        f'{legenda} Foto: <a href="{url}" style="color:inherit">{autor}</a>{extra}, recortada.</p>',
        unsafe_allow_html=True,
    )
