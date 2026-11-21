"""Cores e aparência comuns aos gráficos.

Azul é a única cor de destaque; o resto fica em cinza. Não usamos vermelho, para
não passar ideia de alarme.

Pensado para projetor, que achata o contraste: as cores se distinguem pela claridade,
não só pelo tom (tons da rampa azul da skill dataviz, a mais clara com 2:1 no branco),
e o texto fica em 7:1 ou mais.
"""

from pathlib import Path

import streamlit as st

ASSETS = Path(__file__).resolve().parent / "assets"

AZUL = "#256abf"  # série principal / destaque (azul 500, 5,4:1)
AZUL_ESCURO = "#0d366b"  # nível escolhido, pico (azul 700, bem mais escuro que a série)
CINZA = "#7a7974"  # linhas de referência e pontos de contexto (4,4:1)
CINZA_BARRA = "#a3a29c"  # barras de contexto (o azul fica só no que está em destaque)
CINZA_TEXTO = "#3f3e3a"  # eixos e texto dos gráficos (10,7:1)
CINZA_LEGENDA = "#45443f"  # legendas, créditos e deltas: 9,8:1 no branco (o padrão do Streamlit dá ~3,7:1)
TINTA = "#1f1e1c"  # contorno dos bairros em destaque nos mapas
MANCHA = "rgba(37, 106, 191, 0.35)"  # preenchimento da mancha de inundação

# Escala sequencial de uma cor só (claro -> escuro) para % e mapas.
# O tom mais claro (#86b6ef, 2,1:1) ainda aparece projetado; 0% fica fora da escala.
ESCALA_SEQ = [[0.0, "#86b6ef"], [0.5, "#2a78d6"], [1.0, "#0d366b"]]

FONTE = dict(family='"Source Sans", "Source Sans Pro", sans-serif', size=16, color=CINZA_TEXTO)


def layout_base(fig, altura=380, **kw):
    """Fundo neutro, grade discreta, sem título interno (o título fica no st.subheader)."""
    padrao = dict(
        template="plotly_white",
        height=altura,
        margin=dict(l=10, r=20, t=30, b=10),
        font=FONTE,
        hoverlabel=dict(font_size=16),
        showlegend=False,
        separators=",.",  # vírgula decimal, ponto de milhar
    )
    fig.update_layout(**(padrao | kw))
    fig.update_xaxes(gridcolor="#dcdbd6", zeroline=False)
    fig.update_yaxes(gridcolor="#dcdbd6", zeroline=False)
    return fig


CONFIG_PLOTLY = {"displaylogo": False, "locale": "pt-BR"}


def aplicar_css() -> None:
    """Ajustes que o tema do Streamlit não cobre: cor das legendas (st.caption) e dos deltas.

    O Streamlit esmaece a legenda com opacidade no contêiner (opacity: 0.x, color: inherit),
    não com cor. Trocar só a cor não adianta: o texto continua semitransparente. Por isso a
    opacidade volta a 1 e a cor vem do token. Links ficam de fora para manter a cor de link.
    """
    cor = ", ".join(
        f".stApp [data-testid='{t}'], .stApp [data-testid='{t}'] *:not(a)"
        for t in ("stCaptionContainer", "stMetricDelta")
    )
    # st.html com só <style> injeta o CSS sem ocupar espaço na página.
    st.html(
        "<style>"
        ".stApp [data-testid='stCaptionContainer'] {opacity: 1 !important;}"
        f"{cor} {{color: {CINZA_LEGENDA} !important;}}"
        "</style>"
    )


def faixa_foto(arquivo: str, legenda: str, autor: str, url: str, extra: str = "") -> None:
    """Foto em faixa no topo da tela, com o crédito pedido pela licença logo abaixo."""
    st.image(str(ASSETS / arquivo), width="stretch")
    st.markdown(
        f'<p style="font-size:0.875rem;color:{CINZA_LEGENDA};margin:-0.6rem 0 0.4rem;text-align:right">'
        f'{legenda} Foto: <a href="{url}" style="color:inherit">{autor}</a>{extra}, recortada.</p>',
        unsafe_allow_html=True,
    )
