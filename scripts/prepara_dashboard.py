"""Gera os arquivos que o dashboard lê, a partir do .gpkg do Zenodo e da malha de bairros.

Rodar da raiz do repositório, depois dos scripts de coleta e dos notebooks de limpeza:
    python scripts/prepara_dashboard.py

Saídas:
- dados/processados/bairros/bairros_poa_94.geojson: os 94 bairros, simplificados
- dados/processados/bairros/nomes_bairros.json: nome na malha -> nome no INCT
- dados/processados/zenodo/alagamento_bairros_94.json: % da área de cada bairro sob cada mancha
- dados/processados/zenodo/mancha_obs_20240506_poa.geojson: mancha de 06/05/2024 em Porto Alegre
- dados/processados/osm/osm_mancha_2024.json: escolas e unidades de saúde com bairro e
  indicação de estar dentro da mancha
"""

import json
import re
import unicodedata
from pathlib import Path

import geopandas as gpd
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
MALHA = RAIZ / "dados/originais/bairros/Bairros_LC12112_16.zip"
GPKG = RAIZ / "dados/originais/zenodo/cheias_rhguaiba_2024_db_v12.gpkg"
COLETA_ZENODO = RAIZ / "dados/originais/zenodo/_coleta.json"
INCT = RAIZ / "dados/processados/inct/inct_limpo.json"
OSM = RAIZ / "dados/processados/osm/osm_escolas_saude_poa.json"

PROC = RAIZ / "dados/processados"
SAIDA_BAIRROS = PROC / "bairros/bairros_poa_94.geojson"
SAIDA_NOMES = PROC / "bairros/nomes_bairros.json"
SAIDA_ALAGAMENTO = PROC / "zenodo/alagamento_bairros_94.json"
SAIDA_MANCHA = PROC / "zenodo/mancha_obs_20240506_poa.geojson"
SAIDA_OSM = PROC / "osm/osm_mancha_2024.json"

CRS_METRICO = 31982  # SIRGAS 2000 / UTM 22S, o mesmo usado no notebook do Zenodo
TOLERANCIA_M = 15
LIMIAR = 1  # % da área para considerar que o bairro alagou (igual ao notebook)

# Manchas: as mesmas do notebook do Zenodo (nome da cheia, nível do Guaíba em m, tipo, camada).
# A camada observada não informa o nível; o notebook usa 5,33 m, nível registrado em
# 06/05/2024 na camada poa_pontos_nivel (mesmo dia das imagens).
MANCHAS = [
    ("1941", 4.75, "simulada", "poa_inundacao_1941_475cm"),
    ("1967", 3.13, "simulada", "poa_inundacao_1967_313cm"),
    ("2015", 2.94, "simulada", "poa_inundacao_2015_294cm"),
    ("set/2023", 3.18, "simulada", "poa_inundacao_2023_set_318cm"),
    ("nov/2023", 3.46, "simulada", "poa_inundacao_2023_nov_346cm"),
    ("2024", 5.30, "simulada", "poa_inundacao_2024_530cm"),
    ("obs 2024", 5.33, "observada", "rhguaiba_planet-skysat_inundacao_obs_20240506"),
]

# Nomes que não batem com o INCT nem depois de normalizar (maiúsculas, sem acento,
# sem pontuação, espaços simples). Chave = nome normalizado. Conferidos um a um.
AJUSTES = {
    "CEL APARICIO BORGES": ("Coronel Aparício Borges", "abreviação 'CEL.' na malha"),
    "PASSO DA AREIA": ("Passo D'Areia", "malha escreve 'DA AREIA', INCT escreve 'D'Areia'"),
}


def chave(nome: str) -> str:
    """'Passo D'Areia' -> 'PASSO DAREIA'; 'VILA  ASSUNÇÃO' -> 'VILA ASSUNCAO'."""
    s = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().upper()
    s = re.sub(r"[^A-Z ]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def malha_94(inct_nomes):
    """Lê a malha oficial, junta as partes de cada bairro e põe o nome do INCT."""
    malha = gpd.read_file(MALHA)[["NOME", "geometry"]].to_crs(CRS_METRICO)
    partes = malha["NOME"].value_counts()
    print("malha:", len(malha), "polígonos,", malha["NOME"].nunique(), "nomes; "
          "com mais de uma parte:", dict(partes[partes > 1]))
    malha = malha.dissolve(by="NOME", as_index=False)

    por_chave = {chave(n): n for n in inct_nomes}
    nomes = []
    for nome in malha["NOME"]:
        if chave(nome) in AJUSTES:
            bairro, ajuste = AJUSTES[chave(nome)]
        else:
            bairro = por_chave.get(chave(nome))
            if bairro is None:
                raise ValueError(f"bairro da malha sem par no INCT: {nome!r}")
            if nome == bairro:
                ajuste = ""
            elif re.search(r"\s{2,}", nome):
                ajuste = "espaço duplo na malha; " + "maiúsculas/acentos"
            else:
                ajuste = "maiúsculas/acentos"
        nomes.append({"nome_malha": nome, "bairro": bairro, "ajuste": ajuste})
    nomes = pd.DataFrame(nomes)
    malha["bairro"] = nomes["bairro"].values

    faltam = set(inct_nomes) - set(malha["bairro"])
    assert not faltam, f"bairros do INCT sem polígono: {faltam}"
    assert malha["bairro"].is_unique
    especiais = nomes[nomes["ajuste"] != "maiúsculas/acentos"]
    print("ajustes além de maiúsculas/acentos:\n" + especiais.to_string(index=False))
    return malha, nomes


def main():
    inct_nomes = sorted(pd.read_json(INCT)["bairro"].unique())
    bairros, nomes = malha_94(inct_nomes)
    bairros["area_km2"] = bairros.area / 1e6
    print(f"área total: {bairros['area_km2'].sum():.1f} km²")

    # Alagamento por bairro, com o mesmo método do notebook
    linhas, manchas = [], {}
    for cheia, nivel, tipo, camada in MANCHAS:
        mancha = gpd.read_file(GPKG, layer=camada).to_crs(CRS_METRICO)
        mancha["geometry"] = mancha.force_2d()
        mancha = mancha.make_valid()
        if tipo == "observada":
            mancha = gpd.clip(mancha, bairros.total_bounds)  # recorta para Porto Alegre
        mancha = mancha.union_all()
        manchas[cheia] = mancha
        area_alagada = bairros.intersection(mancha).area / 1e6
        linhas.append(pd.DataFrame({
            "cheia": cheia,
            "nivel_m": nivel,
            "tipo_mancha": tipo,
            "camada": camada,
            "bairro": bairros["bairro"],
            "nome_malha": bairros["NOME"],
            "area_bairro_km2": bairros["area_km2"].round(4),
            "area_alagada_km2": area_alagada.round(4),
            "pct_area_alagada": (area_alagada / bairros["area_km2"] * 100).round(2),
        }))
    alag = pd.concat(linhas, ignore_index=True)
    alag["alagou"] = (alag["pct_area_alagada"] > LIMIAR).astype(int)
    assert len(alag) == len(MANCHAS) * 94
    assert not alag.duplicated(["cheia", "bairro"]).any()
    assert alag["pct_area_alagada"].between(0, 100.01).all()
    assert alag.notna().all().all()
    SAIDA_ALAGAMENTO.write_text(json.dumps(alag.to_dict(orient="records"),
                                           ensure_ascii=False, indent=1), encoding="utf-8")
    obs = alag[alag["cheia"] == "obs 2024"]
    print(f"alagamento: {len(alag)} linhas; bairros com >1% da área na mancha de "
          f"06/05/2024: {obs['alagou'].sum()}")

    # OSM x mancha observada e x bairros
    poa = bairros.union_all()
    mancha_obs = manchas["obs 2024"].intersection(poa)
    osm = pd.read_json(OSM)
    pontos = gpd.GeoDataFrame(
        osm, geometry=gpd.points_from_xy(osm["lon"], osm["lat"]), crs=4326
    ).to_crs(CRS_METRICO)
    pontos["na_mancha_2024"] = pontos.within(mancha_obs).astype(int)
    pontos = gpd.sjoin(pontos, bairros[["bairro", "geometry"]].rename(
        columns={"bairro": "bairro_poligono"}), how="left", predicate="within")
    pontos = pontos.drop(columns=["index_right", "geometry"])
    print(f"osm: {len(pontos)} pontos, {pontos['na_mancha_2024'].sum()} na mancha, "
          f"{pontos['bairro_poligono'].isna().sum()} fora dos polígonos")
    SAIDA_OSM.write_text(pontos.to_json(orient="records", force_ascii=False, indent=1),
                         encoding="utf-8")

    # Geometrias simplificadas, só para desenho
    SAIDA_BAIRROS.parent.mkdir(parents=True, exist_ok=True)
    nomes.to_json(SAIDA_NOMES, orient="records", force_ascii=False, indent=1)
    mancha_gdf = gpd.GeoDataFrame(geometry=[mancha_obs], crs=CRS_METRICO)
    for gdf, saida in [(bairros[["bairro", "geometry"]], SAIDA_BAIRROS),
                       (mancha_gdf, SAIDA_MANCHA)]:
        gdf = gdf.copy()
        gdf["geometry"] = gdf.geometry.simplify(TOLERANCIA_M, preserve_topology=True)
        gdf.to_crs(4326).to_file(saida, driver="GeoJSON", COORDINATE_PRECISION=5)
        print(f"{saida.relative_to(RAIZ)}: {saida.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
