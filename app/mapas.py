"""Mapa coroplético dos 94 bairros, usado nas duas telas.

Escala de um azul só, fixa de 0 a 100%, para comparar níveis e mapas entre si.
Bairros com 0% ficam em cinza, separados da escala.
"""

import pandas as pd
import plotly.graph_objects as go

import dados
from estilo import ESCALA_SEQ, layout_base

CENTRO_POA = dict(lat=-30.11, lon=-51.17)
CINZA_ZERO = "#ecebe7"
CONTORNO = "#ffffff"


def coropletico(valores: pd.DataFrame, coluna: str, rotulo: str, hover: str,
                altura: int = 520, escala: bool = True, zoom: float = 9.3) -> go.Figure:
    """valores: uma linha por bairro (coluna 'bairro', grafia do INCT) com `coluna` em %.

    hover: hovertemplate com %{customdata[i]} para as colunas de `valores` na ordem
    em que aparecem (o nome do bairro é %{location}).
    """
    gj = dados.geojson_bairros()
    extra = [c for c in valores.columns if c not in ("bairro",)]
    zero = valores[valores[coluna] <= 0]
    pos = valores[valores[coluna] > 0]

    fig = go.Figure()
    fig.add_trace(go.Choroplethmap(
        geojson=gj, locations=zero["bairro"], z=[0] * len(zero),
        colorscale=[[0, CINZA_ZERO], [1, CINZA_ZERO]], showscale=False,
        marker_line_color=CONTORNO, marker_line_width=0.8,
        customdata=zero[extra], hovertemplate=hover,
    ))
    fig.add_trace(go.Choroplethmap(
        geojson=gj, locations=pos["bairro"], z=pos[coluna],
        zmin=0, zmax=100, colorscale=ESCALA_SEQ, showscale=escala,
        colorbar=dict(title=dict(text=rotulo, side="top"), ticksuffix="%",
                      thickness=8, len=0.4, x=0.98, xanchor="right", y=0.05,
                      yanchor="bottom", tickvals=[0, 25, 50, 75, 100],
                      bgcolor="rgba(255,255,255,0.8)"),
        marker_line_color=CONTORNO, marker_line_width=0.8,
        customdata=pos[extra], hovertemplate=hover,
    ))
    fig.update_layout(map=dict(style="carto-positron", center=CENTRO_POA, zoom=zoom))
    return layout_base(fig, altura=altura, margin=dict(l=0, r=0, t=0, b=0))
