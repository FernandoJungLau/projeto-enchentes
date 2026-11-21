"""Tela 2: o que outras bases (Zenodo/UFRGS, OpenStreetMap, ANA) acrescentam à simulação do INCT?"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import dados
import mapas
from dados import NIVEL_REF_2024, fmt_dec, fmt_int
from estilo import (AZUL, AZUL_ESCURO, CINZA, CINZA_TEXTO, CONFIG_PLOTLY, MANCHA, faixa_foto,
                    layout_base)

LIMIAR_ALAGOU = 1.0  # % mínima da área para o bairro contar como atingido (mesmo critério do notebook)
CENTRO_POA = dict(lat=-30.07, lon=-51.19)  # centro do mapa de pontos
NIVEIS = [round(3.0 + 0.1 * i, 1) for i in range(31)]  # 3,0 a 6,0 m


def bairros_txt(n: int) -> str:
    return f"{n} bairro" if n == 1 else f"{n} bairros"

faixa_foto(
    "faixa_mercado_marca.jpg",
    "Marca deixada pela cheia na fachada do Mercado Público, 2024.",
    "Ricardo André Frantz",
    "https://commons.wikimedia.org/wiki/File:Enchente_Porto_Alegre_2024_07.jpg",
    extra=', <a href="https://creativecommons.org/licenses/by/4.0" style="color:inherit">CC BY 4.0</a>',
)
st.title("Comparação com maio de 2024")
st.markdown(
    "A simulação do INCT ao lado de três fontes independentes: a mancha de inundação "
    "mapeada pela UFRGS, as escolas e unidades de saúde do OpenStreetMap e o nível do "
    "Guaíba medido pela ANA. Os números do INCT continuam sendo estimativas."
)

alag = dados.alagamento_bairros()
inct = dados.inct()
osm = dados.osm_mancha()
ana = dados.ana()

# 1. A simulação bate com a mancha observada?
st.header("1. A simulação bate com a mancha de 2024?")

# Só manchas a partir de 3,0 m: abaixo disso o INCT não simula.
manchas = (
    alag[alag["nivel_m"] >= 3.0][["cheia", "nivel_m", "tipo_mancha"]]
    .drop_duplicates()
    .sort_values("nivel_m", ascending=False)
)
rotulos = {
    r.cheia: (f"Maio/2024, mancha observada em 06/05 ({fmt_dec(r.nivel_m, 2)} m)"
              if r.tipo_mancha == "observada"
              else f"Cheia de {r.cheia}, mancha simulada pela UFRGS ({fmt_dec(r.nivel_m, 2)} m)")
    for r in manchas.itertuples()
}
cheia = st.selectbox("Comparar o INCT com", list(rotulos), format_func=rotulos.get,
                     index=list(rotulos).index("obs 2024"))
nivel_cheia = float(manchas.loc[manchas["cheia"] == cheia, "nivel_m"].iloc[0])
nivel_inct = round(min(max(nivel_cheia, 3.0), 10.0), 1)

comp = alag[alag["cheia"] == cheia][["bairro", "pct_area_alagada"]].merge(
    inct[inct["nivel_m"] == nivel_inct][["bairro", "percentage", "affected_population"]],
    on="bairro", how="inner",
)
so_mancha = comp[(comp["pct_area_alagada"] > LIMIAR_ALAGOU) & (comp["percentage"] == 0)]
so_inct = comp[(comp["pct_area_alagada"] <= LIMIAR_ALAGOU) & (comp["percentage"] > 0)]
ambos = comp[(comp["pct_area_alagada"] > LIMIAR_ALAGOU) & (comp["percentage"] > 0)]

st.markdown(
    f"As duas fontes apontam os mesmos bairros em **{len(ambos)} casos**. "
    f"{bairros_txt(len(so_inct))} aparecem só no INCT e {bairros_txt(len(so_mancha))} só na "
    "mancha. Mesma escala nos dois mapas: tons parecidos indicam concordância."
)
mapa_e, mapa_d = st.columns(2, gap="medium")
with mapa_e:
    st.markdown(f"**Área do bairro sob a mancha ({rotulos[cheia].split(',')[0]})**")
    st.plotly_chart(mapas.coropletico(
        comp[["bairro", "pct_area_alagada"]], coluna="pct_area_alagada", rotulo="% área",
        hover="<b>%{location}</b><br>%{customdata[0]:.1f}% da área<extra></extra>",
        altura=420, escala=False, zoom=9.0,
    ), config=CONFIG_PLOTLY, key="mapa_mancha")
with mapa_d:
    st.markdown(f"**Prédios afetados no INCT a {fmt_dec(nivel_inct)} m**")
    st.plotly_chart(mapas.coropletico(
        comp[["bairro", "percentage"]], coluna="percentage", rotulo="%",
        hover="<b>%{location}</b><br>%{customdata[0]:.1f}% dos prédios<extra></extra>",
        altura=420, zoom=9.0,
    ), config=CONFIG_PLOTLY, key="mapa_inct")

divergentes = pd.concat([
    so_mancha.assign(onde="Só na mancha"), so_inct.assign(onde="Só no INCT")
])
tab, nota = st.columns([3, 2], gap="large")
with tab:
    if len(divergentes):
        st.dataframe(
            divergentes.assign(
                area=divergentes["pct_area_alagada"].map(lambda v: f"{fmt_dec(v)}%"),
                predios=divergentes["percentage"].map(lambda v: f"{fmt_dec(v)}%"),
            )[["bairro", "onde", "area", "predios"]],
            column_config={"bairro": "Bairro que diverge", "onde": "Atingido",
                           "area": st.column_config.TextColumn("Área sob a mancha",
                                                               alignment="right"),
                           "predios": st.column_config.TextColumn("Prédios no INCT",
                                                                  alignment="right")},
            hide_index=True, width="stretch",
        )
    else:
        st.markdown("Nenhum bairro diverge.")
with nota:
    st.caption(f"Bairro atingido: mais de {fmt_dec(LIMIAR_ALAGOU, 0)}% da área sob a mancha, "
               "ou pelo menos um prédio afetado no INCT. O INCT não tem o nível exato da "
               f"mancha ({fmt_dec(nivel_cheia, 2)} m); usamos o mais próximo, "
               f"{fmt_dec(nivel_inct)} m.")

with st.expander("Ver comparação bairro a bairro"):
    st.markdown(f"**% da área alagada × % de prédios afetados no INCT a {fmt_dec(nivel_inct)} m**")
    fig = go.Figure()
    fig.add_scatter(x=[0, 100], y=[0, 100], mode="lines",
                    line=dict(color=CINZA, dash="dot", width=1), hoverinfo="skip")
    fig.add_annotation(x=8, y=2, xanchor="left", text="valores iguais", showarrow=False,
                       font=dict(color=CINZA_TEXTO, size=11), textangle=-35)
    fig.add_scatter(
        x=comp["pct_area_alagada"], y=comp["percentage"], mode="markers",
        marker=dict(color=AZUL, size=9, opacity=0.8, line=dict(color="white", width=1)),
        customdata=comp[["bairro"]],
        hovertemplate="<b>%{customdata[0]}</b><br>Área alagada: %{x:.1f}%"
                      "<br>Prédios afetados (INCT): %{y:.1f}%<extra></extra>",
    )
    fig.update_xaxes(title="% da área do bairro sob a mancha", range=[-3, 103])
    fig.update_yaxes(title="% de prédios afetados (INCT)", range=[-3, 103])
    st.plotly_chart(layout_base(fig, altura=420), config=CONFIG_PLOTLY)
    st.caption(
        "Cada ponto é um bairro. Sobre a diagonal, as duas fontes dão o mesmo percentual. "
        "Área e prédios não são a mesma medida: bairros com muita área verde ou de várzea "
        "podem ter muita área alagada e poucos prédios."
    )

# 2. Escolas e unidades de saúde na mancha
st.header("2. Escolas e unidades de saúde na área alagada")
grupos = ["Escola", "Creche", "Saúde"]
escolha = st.pills("Tipo de estabelecimento", grupos, default=grupos, selection_mode="multi")
filtrado = osm[osm["grupo"].isin(escolha or grupos)]
dentro = filtrado[filtrado["na_mancha_2024"] == 1]

k1, k2 = st.columns(2)
k1.metric("Dentro da mancha de 06/05/2024", f"{len(dentro)} de {len(filtrado)}")
k2.metric("Bairros com estabelecimentos na mancha", dentro["bairro_poligono"].nunique())

mapa_col, barra_col = st.columns([3, 2], gap="large")
with mapa_col:
    st.subheader("No mapa")
    fig = go.Figure()
    fig.add_trace(go.Choroplethmap(
        geojson=dados.geojson("zenodo/mancha_obs_20240506_poa.geojson"),
        locations=["0"], z=[1],
        colorscale=[[0, MANCHA], [1, MANCHA]], showscale=False,
        marker_line_width=0, hoverinfo="skip", name="Mancha 06/05/2024",
    ))
    for situacao, cor, tam in [("Fora da mancha", CINZA, 6),
                               ("Dentro da mancha de 06/05/2024", AZUL_ESCURO, 9)]:
        p = filtrado[filtrado["situacao"] == situacao]
        fig.add_trace(go.Scattermap(
            lat=p["lat"], lon=p["lon"], mode="markers", name=situacao,
            marker=dict(size=tam, color=cor, opacity=0.9),
            customdata=p[["nome", "grupo", "bairro_poligono"]],
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]} · "
                          "%{customdata[2]}<extra></extra>",
        ))
    fig.update_layout(map=dict(style="carto-positron", center=CENTRO_POA, zoom=10.2),
                      showlegend=True,
                      legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0))
    fig = layout_base(fig, altura=480)
    fig.update_layout(showlegend=True)
    st.plotly_chart(fig, config=CONFIG_PLOTLY)

with barra_col:
    st.subheader("Por bairro")
    por_bairro = (dentro.groupby("bairro_poligono").size().sort_values()
                  .tail(12).rename("n").reset_index())
    fig = go.Figure(go.Bar(
        x=por_bairro["n"], y=por_bairro["bairro_poligono"], orientation="h",
        marker=dict(color=AZUL_ESCURO, cornerradius=3), text=por_bairro["n"],
        textposition="outside", cliponaxis=False,
        hovertemplate="<b>%{y}</b>: %{x} estabelecimentos<extra></extra>",
    ))
    fig.update_xaxes(title=None, showticklabels=False, showgrid=False, rangemode="tozero")
    fig.update_yaxes(title=None)
    st.plotly_chart(layout_base(fig, altura=max(220, 30 * len(por_bairro) + 40)),
                    config=CONFIG_PLOTLY)
    st.caption("Os 12 bairros com mais estabelecimentos dentro da mancha.")

with st.expander(f"Lista dos {len(dentro)} estabelecimentos dentro da mancha"):
    lista = (dentro[["nome", "grupo", "bairro_poligono", "rua", "numero"]]
             .sort_values(["bairro_poligono", "grupo", "nome"]))
    st.dataframe(
        lista,
        column_config={"nome": "Nome", "grupo": "Tipo", "bairro_poligono": "Bairro",
                       "rua": "Rua", "numero": "Número"},
        hide_index=True, width="stretch",
    )
    st.download_button(
        "Baixar lista (CSV)", lista.to_csv(index=False).encode("utf-8-sig"),
        file_name="estabelecimentos_na_mancha_20240506.csv", mime="text/csv",
    )

st.caption(
    "O OpenStreetMap mostra o que estava mapeado em novembro de 2026, não necessariamente "
    "o que existia em maio de 2024, e o mapeamento colaborativo pode estar incompleto."
)

# 3. Nível do Guaíba em 2024
st.header("3. Quanto tempo o Guaíba ficou acima de cada nível?")
f1, f2 = st.columns(2)
if "_nivel_t2" not in st.session_state:
    st.session_state["_nivel_t2"] = round(
        min(st.session_state.get("nivel_escolhido", NIVEL_REF_2024), 6.0), 1)


def _sincroniza_nivel():
    st.session_state["nivel_escolhido"] = st.session_state["_nivel_t2"]


with f1:
    nivel_ref = st.select_slider(
        "Nível (o mesmo da outra tela)", options=NIVEIS,
        format_func=lambda v: f"{fmt_dec(v)} m",
        key="_nivel_t2", on_change=_sincroniza_nivel,
    )
with f2:
    inicio, fim = ana["data_hora"].min().to_pydatetime(), ana["data_hora"].max().to_pydatetime()
    periodo = st.slider("Período", inicio, fim, (inicio, fim), format="DD/MM/YYYY")

serie = ana[(ana["data_hora"] >= periodo[0]) & (ana["data_hora"] <= periodo[1])]
validas = serie.dropna(subset=["nivel_m"])
# Cada leitura vale o intervalo até a próxima (em geral 15 min), limitado a 1 h para
# que uma lacuna longa de leituras não conte como tempo acima do nível.
dur_h = (validas["data_hora"].diff().shift(-1).dt.total_seconds().fillna(900) / 3600).clip(upper=1)
horas_acima = dur_h[validas["nivel_m"] >= nivel_ref].sum()
pico = validas.loc[validas["nivel_m"].idxmax()] if len(validas) else None
cid = dados.inct_por_nivel().set_index("nivel_m")

n1, n2, n3 = st.columns(3)
if horas_acima >= 24:
    tempo_txt = f"{fmt_dec(horas_acima / 24)} dias"
elif horas_acima > 0:
    tempo_txt = f"{fmt_dec(horas_acima)} h"
else:
    tempo_txt = "nenhum"
n1.metric(f"Tempo acima de {fmt_dec(nivel_ref)} m", tempo_txt)
if pico is not None:
    n2.metric("Maior nível no período", f"{fmt_dec(pico['nivel_m'], 2)} m",
              help=f"Em {pico['data_hora']:%d/%m/%Y %H:%M}")
n3.metric(f"Pessoas afetadas a {fmt_dec(nivel_ref)} m (INCT, est.)",
          fmt_int(cid.loc[round(nivel_ref, 1), "pessoas"]))

fig = go.Figure()
fig.add_scatter(x=serie["data_hora"], y=serie["nivel_m"], mode="lines",
                line=dict(color=AZUL, width=2), connectgaps=False,
                hovertemplate="%{x|%d/%m %H:%M}: %{y:.2f} m<extra></extra>")
fig.add_hline(y=nivel_ref, line=dict(color=AZUL_ESCURO, width=1.5))
fig.add_annotation(x=1, xref="paper", xanchor="right", y=nivel_ref, yanchor="bottom",
                   text=f"{fmt_dec(nivel_ref)} m", showarrow=False,
                   font=dict(color=AZUL_ESCURO))
fig.add_hline(y=3.0, line=dict(color=CINZA, dash="dot", width=1))
fig.add_annotation(x=1, xref="paper", xanchor="right", y=3.0, yanchor="top",
                   text="3,0 m, início da simulação do INCT", showarrow=False,
                   font=dict(color=CINZA_TEXTO, size=11))
fig.update_xaxes(title=None, tickformat="%d/%m")
fig.update_yaxes(title="Nível do Guaíba (m)", range=[0, 6])
st.plotly_chart(layout_base(fig, altura=360), config=CONFIG_PLOTLY)
st.caption(
    "Leituras a cada 15 minutos na estação Usina do Gasômetro. Os trechos sem linha são "
    f"leituras que faltam ({fmt_int(serie['nivel_m'].isna().sum())} no período)."
)

# Fontes
st.divider()
st.subheader("Fontes dos dados")


data_br = dados.data_br
z, o, a = dados.coleta("zenodo"), dados.coleta("osm"), dados.coleta("ana")
b = dados.coleta("bairros")
datas_b = sorted(v["data_coleta"] for v in b["arquivos"].values())
datas_z = sorted(v["data_coleta"] for v in z["arquivos"].values())
datas_a = sorted(v["data_coleta"] for v in a["arquivos"].values())
st.markdown(
    f"- Manchas de inundação: [{z['fonte']}]({z['url']}), {z['versao']}, "
    f"licença {z['licenca']}. Coletado em {data_br(datas_z[-1])}.\n"
    f"- Escolas e unidades de saúde: [{o['fonte']}]({o['url']}), licença {o['licenca']}. "
    f"Coletado em {data_br(o['data_coleta'])}.\n"
    f"- Nível do Guaíba: [{a['fonte']}](https://www.snirh.gov.br/hidrotelemetria/), "
    f"{a['licenca'][0].lower() + a['licenca'][1:]}. Coletado em {data_br(datas_a[-1])}.\n"
    f"- Limites dos 94 bairros: [{b['fonte']}]({b['url']}). "
    f"Coletado em {data_br(datas_b[-1])}.\n"
    "- Simulação: INCT SiMAI, arquivo cedido ao projeto."
)
