"""Leitura dos dados processados usados pelo dashboard.

Tudo vem de dados/processados/ (gerados pelos notebooks de limpeza e por
scripts/prepara_dashboard.py). O app não lê nada de dados/originais/ além dos
_coleta.json, que trazem link e data de coleta de cada fonte.
"""

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent
PROC = RAIZ / "dados" / "processados"
ORIG = RAIZ / "dados" / "originais"

RECORDE_2024_M = 5.35  # pico do Guaíba em maio de 2024 (Cais Mauá)
NIVEL_REF_2024 = 5.3  # nível simulado pelo INCT mais próximo do recorde


@st.cache_data
def inct() -> pd.DataFrame:
    """INCT limpo em formato longo: uma linha por nível e bairro (6674 linhas)."""
    df = pd.read_json(PROC / "inct" / "inct_limpo.json")
    df["nivel_m"] = df["nivel_m"].round(1)
    return df


@st.cache_data
def inct_por_nivel() -> pd.DataFrame:
    """Totais da cidade por nível do Guaíba."""
    df = inct()
    return (
        df.assign(atingido=df["affected_buildings"] > 0)
        .groupby("nivel_m", as_index=False)
        .agg(
            pessoas=("affected_population", "sum"),
            predios=("affected_buildings", "sum"),
            bairros=("atingido", "sum"),
        )
    )


@st.cache_data
def alagamento_bairros() -> pd.DataFrame:
    """% da área de cada um dos 94 bairros coberta por cada mancha do Zenodo.

    Gerado por scripts/prepara_dashboard.py. A versão de 83 bairros da EDA fica em
    alagamento_bairros_83.json e não é usada pelo app.
    """
    return pd.read_json(PROC / "zenodo" / "alagamento_bairros.json")


@st.cache_data
def osm_mancha() -> pd.DataFrame:
    """Escolas e unidades de saúde do OSM, com bairro e flag de mancha de 2024."""
    df = pd.read_json(PROC / "osm" / "osm_mancha_2024.json")
    grupos = {
        "school": "Escola",
        "kindergarten": "Creche",
        "hospital": "Saúde",
        "clinic": "Saúde",
        "doctors": "Saúde",
    }
    df["grupo"] = df["categoria"].map(grupos)
    df["situacao"] = df["na_mancha_2024"].map(
        {1: "Dentro da mancha de 06/05/2024", 0: "Fora da mancha"}
    )
    df["nome"] = df["nome"].fillna("(sem nome no OSM)")
    return df


@st.cache_data
def ana() -> pd.DataFrame:
    """Nível do Guaíba a cada 15 min (ANA, estação 87444000), maio e junho de 2024."""
    df = pd.read_json(PROC / "ana" / "ana_87444000_nivel_chuva.json")
    df["data_hora"] = pd.to_datetime(df["data_hora"])
    return df


@st.cache_data
def geojson(caminho: str) -> dict:
    """GeoJSON de dados/processados/<caminho>. O Plotly liga dado e polígono pelo id:
    nos bairros o id é o nome do bairro (grafia do INCT); nos outros, a posição."""
    gj = json.loads((PROC / caminho).read_text(encoding="utf-8"))
    for i, feicao in enumerate(gj["features"]):
        feicao["id"] = feicao["properties"].get("bairro", str(i))
    return gj


def geojson_bairros() -> dict:
    """94 bairros da LC 12.112/2016 (malha oficial da Prefeitura, simplificada)."""
    return geojson("bairros/bairros_poa_94.geojson")


@st.cache_data
def coleta(fonte: str) -> dict:
    """Metadados de coleta (link, licença, data) de dados/originais/<fonte>/_coleta.json."""
    return json.loads((ORIG / fonte / "_coleta.json").read_text(encoding="utf-8"))


def fmt_int(n: float) -> str:
    """12345 -> '12.345' (separador de milhar brasileiro)."""
    return f"{int(round(n)):,}".replace(",", ".")


def fmt_dec(x: float, casas: int = 1) -> str:
    """5.35 -> '5,35'."""
    return f"{x:.{casas}f}".replace(".", ",")


def data_br(iso: str) -> str:
    """'2026-11-08T13:51:09' -> '08/11/2026'."""
    return datetime.fromisoformat(iso).strftime("%d/%m/%Y")
