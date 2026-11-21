"""Tela 1: Simulação do INCT. Se o rio chegar a X metros, quais bairros e quantas pessoas são afetados?"""

import plotly.graph_objects as go
import streamlit as st

import dados
import mapas
from dados import NIVEL_REF_2024, RECORDE_2024_M, fmt_dec, fmt_int
from estilo import (AZUL, AZUL_ESCURO, CINZA, CINZA_BARRA, CINZA_TEXTO, CONFIG_PLOTLY,
                    faixa_foto, layout_base)

TOTAL_BAIRROS = 94
NIVEIS = [round(3.0 + 0.1 * i, 1) for i in range(71)]  # 3,0 a 10,0 m

# Texto da tabela de correções, por tipo de tratamento feito na limpeza do INCT.
CORRECOES = {
    "zero isolado": "Zero no meio de valores positivos; interpolado entre os níveis vizinhos",
    "pico isolado": "Valor muito acima dos níveis vizinhos; interpolado entre eles",
    "ruído": "Valor que sobe e desce entre níveis; alinhado aos níveis vizinhos",
    "patamar inicial inconsistente": "Primeiros níveis maiores que os seguintes; alinhados a eles",
}

_b = dados.coleta("bairros")
coleta_bairros = dados.data_br(max(a["data_coleta"] for a in _b["arquivos"].values()))

faixa_foto(
    "faixa_cais_maua_cheia.jpg",
    "Cais Mauá em 2 de maio de 2024, com o Guaíba na altura da plataforma.",
    "Luciano Lanes/PMPA",
    "https://commons.wikimedia.org/wiki/File:IBPA_133621_-_Porto_Alegre,_RS._"
    "Fechamento_das_comportas_do_Cais_Mau%C3%A1._-_2024-05-02_-_Luciano_Lanes-PMPA.jpg",
)
st.title("Se o Guaíba subir")
st.caption("Simulação do INCT SiMAI para níveis de 3,0 a 10,0 m · Projeto de extensão da "
           "disciplina Coleta, Preparação e Análise de Dados, PUCRS · Novembro de 2026")
st.markdown("**Os números desta página são estimativas de um modelo**, não previsão nem "
            "contagem oficial. As limitações estão no fim da página.")

df = dados.inct()
cidade = dados.inct_por_nivel()

# Controle de nível e indicadores
# O nível fica em "nivel_escolhido" (fora do widget) para sobreviver à troca de
# tela: o Streamlit apaga o estado de widgets que não aparecem na página atual.
if "_nivel_t1" not in st.session_state:
    st.session_state["_nivel_t1"] = round(st.session_state.get("nivel_escolhido", NIVEL_REF_2024), 1)

with st.container(border=True):
    nivel = st.select_slider(
        "Nível do Guaíba",
        options=NIVEIS,
        format_func=lambda v: f"{fmt_dec(v)} m",
        key="_nivel_t1",
        help=f"O pico de maio de 2024 foi {fmt_dec(RECORDE_2024_M, 2)} m. "
        f"O nível simulado mais próximo é {fmt_dec(NIVEL_REF_2024)} m.",
    )
    st.session_state["nivel_escolhido"] = nivel  # a Tela 2 usa o mesmo nível

    atual = cidade.loc[cidade["nivel_m"] == nivel].iloc[0]
    ref = cidade.loc[cidade["nivel_m"] == NIVEL_REF_2024].iloc[0]

    def delta(campo):
        if nivel == NIVEL_REF_2024:
            return None
        return f"{fmt_int(atual[campo] - ref[campo])} em relação a {fmt_dec(NIVEL_REF_2024)} m"

    c1, c2, c3 = st.columns(3)
    c1.metric("Pessoas afetadas (est.)", fmt_int(atual["pessoas"]),
              delta=delta("pessoas"), delta_color="off",
              help="Soma, nos bairros, da população × % de prédios afetados.")
    c2.metric("Prédios afetados", fmt_int(atual["predios"]),
              delta=delta("predios"), delta_color="off")
    c3.metric("Bairros atingidos", f"{int(atual['bairros'])} de {TOTAL_BAIRROS}",
              delta=delta("bairros"), delta_color="off",
              help="Bairros com pelo menos um prédio afetado.")

# Curva da população afetada
st.subheader("Pessoas afetadas em cada nível")
st.markdown(
    f"A {fmt_dec(nivel)} m, o modelo estima **{fmt_int(atual['pessoas'])} pessoas** em "
    f"{int(atual['bairros'])} dos 94 bairros. A linha tracejada marca o pico de maio de 2024."
)
fig = go.Figure()
fig.add_scatter(
    x=cidade["nivel_m"], y=cidade["pessoas"], mode="lines",
    line=dict(color=AZUL, width=2.5),
    hovertemplate="%{x:.1f} m: %{y:,.0f} pessoas<extra></extra>",
)
fig.add_vline(x=RECORDE_2024_M, line=dict(color=CINZA, dash="dash", width=1.5))
fig.add_annotation(
    x=RECORDE_2024_M, y=1, yref="paper", yanchor="bottom", xanchor="left",
    text=f" Maio de 2024: {fmt_dec(RECORDE_2024_M, 2)} m",
    showarrow=False, font=dict(color="#52514e"),
)
fig.add_scatter(
    x=[nivel], y=[atual["pessoas"]], mode="markers+text",
    marker=dict(color=AZUL_ESCURO, size=12, line=dict(color="white", width=2)),
    text=[fmt_int(atual["pessoas"])], textposition="top left",
    textfont=dict(color=AZUL_ESCURO, size=13),
    hovertemplate="Nível escolhido: %{x:.1f} m<extra></extra>",
)
fig.update_xaxes(title="Nível do Guaíba (m)", range=[2.9, 10.1], dtick=1)
fig.update_yaxes(title="Pessoas afetadas (est.)", rangemode="tozero", tickformat=",.0f")
st.plotly_chart(layout_base(fig, altura=320, margin=dict(l=10, r=20, t=40, b=10)),
                config=CONFIG_PLOTLY)

# Mapa e ranking
todos = df[df["nivel_m"] == nivel].copy()
no_nivel = todos[todos["affected_buildings"] > 0]
esq, dir_ = st.columns([3, 2], gap="large")

with esq:
    st.subheader("Prédios afetados por bairro")
    st.caption("Mais escuro = maior parte dos prédios atingida. Cinza = nenhum.")
    mapa = mapas.coropletico(
        todos[["bairro", "percentage", "affected_buildings", "total_buildings",
               "affected_population"]],
        coluna="percentage", rotulo="% prédios",
        hover="<b>%{location}</b><br>%{customdata[0]:.1f}% dos prédios "
              "(%{customdata[1]:,} de %{customdata[2]:,})"
              "<br>%{customdata[3]:,} pessoas (est.)<extra></extra>",
    )
    st.plotly_chart(mapa, config=CONFIG_PLOTLY)

with dir_:
    st.subheader("Bairros mais afetados")
    criterio = st.radio(
        "Ordenar por", ["Pessoas afetadas", "% de prédios afetados"],
        horizontal=True, label_visibility="collapsed",
    )
    col = "affected_population" if criterio == "Pessoas afetadas" else "percentage"
    ranking = (
        no_nivel.sort_values([col, "affected_population"], ascending=False)
        .head(10)
        .reset_index(drop=True)
    )
    if ranking.empty:
        st.markdown(f"Nenhum bairro tem prédios afetados a {fmt_dec(nivel)} m.")
    else:
        # Barras horizontais em ordem: 1º no topo, posição junto do nome e valor na
        # ponta da barra (o eixo x fica sem rótulos, como no gráfico por bairro da Tela 2).
        por_pessoas = col == "affected_population"
        valores = ranking[col]
        rotulos_valor = [fmt_int(v) if por_pessoas else f"{fmt_dec(v)}%" for v in valores]
        fig = go.Figure(go.Bar(
            x=valores,
            y=[f"{i}º  {b}" for i, b in enumerate(ranking["bairro"], start=1)],
            orientation="h",
            marker=dict(color=AZUL, cornerradius=3),
            text=rotulos_valor, textposition="outside", cliponaxis=False,
            textfont=dict(size=13, color=CINZA_TEXTO),
            customdata=ranking[["affected_population", "percentage"]],
            hovertemplate="<b>%{y}</b><br>%{customdata[0]:,.0f} pessoas (est.)"
                          "<br>%{customdata[1]:.1f}% dos prédios<extra></extra>",
        ))
        fig.update_xaxes(showticklabels=False, showgrid=False, title=None,
                         range=[0, valores.max() * 1.18 if por_pessoas else 112])
        fig.update_yaxes(title=None, autorange="reversed", tickfont=dict(size=13))
        st.plotly_chart(layout_base(fig, altura=40 * len(ranking) + 40, bargap=0.25,
                                    margin=dict(l=10, r=20, t=10, b=10)),
                        config=CONFIG_PLOTLY)
    st.caption("Pessoas afetadas = população do bairro × % de prédios afetados.")

# Barras com todos os bairros atingidos
st.subheader("Todos os bairros atingidos")
st.caption(f"{len(no_nivel)} bairros com prédios afetados a {fmt_dec(nivel)} m. "
           "Em azul, os 10 do ranking acima.")
barras = no_nivel.sort_values("percentage")
destaque = set(ranking["bairro"])
fig = go.Figure(go.Bar(
    x=barras["percentage"], y=barras["bairro"], orientation="h",
    marker=dict(color=[AZUL if b in destaque else CINZA_BARRA for b in barras["bairro"]],
                cornerradius=3),
    text=[f"{fmt_dec(p)}%" for p in barras["percentage"]],
    textposition="outside", cliponaxis=False, textfont=dict(size=12),
    customdata=barras[["affected_buildings", "total_buildings"]],
    hovertemplate="<b>%{y}</b><br>%{x:.1f}% dos prédios"
                  "<br>%{customdata[0]:,} de %{customdata[1]:,}<extra></extra>",
))
fig.update_xaxes(range=[0, 108], tickvals=[0, 25, 50, 75, 100],
                 ticktext=["0%", "25%", "50%", "75%", "100%"], title=None, side="top")
fig.update_yaxes(title=None, tickfont=dict(size=12))
st.plotly_chart(layout_base(fig, altura=max(240, 18 * len(barras) + 60), bargap=0.3),
                config=CONFIG_PLOTLY)

# Limitações
st.divider()
st.subheader("Limitações")
n_recalc = fmt_int(df["tratamento"].str.contains("recalculado").sum())
st.markdown(
    "Estes números saem de um modelo, não de contagem em campo nem de dados da Defesa "
    "Civil. O INCT SiMAI estima quantos prédios de cada bairro a água alcança em cada "
    "nível. A população afetada supõe que os moradores se dividem igualmente entre todos "
    "os prédios do bairro (Censo IBGE 2022), inclusive lojas e prédios públicos. A "
    "contagem de prédios vem do OpenStreetMap e pode estar incompleta.\n\n"
    "No arquivo original encontramos zeros e picos isolados e percentuais arredondados "
    "para cima. Corrigimos esses valores antes de montar o painel."
)
with st.expander("O que corrigimos no arquivo do INCT"):
    trat = df[df["tratamento"].str.contains("interpolado")].sort_values(["bairro", "nivel_m"])
    motivo = trat["tratamento"].str.extract(r"interpolado \(([^)]+)\)")[0].map(CORRECOES)
    st.dataframe(
        trat.assign(
            nivel=trat["nivel_m"].map(lambda v: f"{fmt_dec(v)} m"),
            predios=trat["affected_buildings"].map(fmt_int),
            correcao=motivo,
        )[["bairro", "nivel", "predios", "correcao"]],
        column_config={"bairro": "Bairro",
                       "nivel": st.column_config.TextColumn("Nível", alignment="right"),
                       "predios": st.column_config.TextColumn("Prédios afetados (corrigido)",
                                                              alignment="right"),
                       "correcao": "O que havia"},
        hide_index=True, width="stretch",
    )
    st.caption(f"Também recalculamos o percentual e a população afetada em {n_recalc} "
               "linhas, para ficarem coerentes com os prédios afetados.")
st.caption(
    "Fonte: simulação do INCT SiMAI, arquivo cedido ao projeto. Limites dos bairros: "
    f"[Prefeitura de Porto Alegre, Bairros (LC 12.112/16)]({_b['url']}), "
    f"coletados em {coleta_bairros}."
)
