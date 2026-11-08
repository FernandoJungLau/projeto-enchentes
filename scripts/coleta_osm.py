# Coleta de escolas e unidades de saúde de Porto Alegre - OpenStreetMap (Overpass API)
# Rodar da raiz do repositório: python scripts/coleta_osm.py
#
# Fonte: © contribuidores do OpenStreetMap, licença ODbL
# https://www.openstreetmap.org/copyright
# Coleta responsável: uma única consulta, salva em disco; se o arquivo já
# existe, não consulta de novo (política de uso da Overpass API).

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

# -----------------------------
# 0. Configurações
# -----------------------------
RAIZ = Path(__file__).resolve().parents[1]
PASTA = RAIZ / "dados" / "originais" / "osm"
PASTA.mkdir(parents=True, exist_ok=True)

ARQ_OSM = PASTA / "osm_escolas_saude_poa.json"
ARQ_COLETA = PASTA / "_coleta.json"

HEADERS = {"User-Agent": "projeto-enchentes-pucrs (trabalho academico)"}

# Consulta do notebook da Fase 1, com uma correção:
# escolas, creches, hospitais, clínicas e consultórios dentro do município
# de Porto Alegre (admin_level=8 = limite municipal no OSM).
# O regex agora tem ^( )$: sem isso, "school" também pegava language_school,
# driving_school, music_school etc. (ver relatorios/decisoes_coleta.md).
# "out center" devolve um ponto central para áreas e prédios (ways/relations).
CONSULTA = """
[out:json][timeout:120];
area["name"="Porto Alegre"]["admin_level"="8"]->.poa;
nwr["amenity"~"^(school|kindergarten|hospital|clinic|doctors)$"](area.poa);
out center tags;
"""

# O servidor principal costuma ficar sobrecarregado; tenta os espelhos em sequência
SERVIDORES = ["https://overpass-api.de/api/interpreter",
              "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
              "https://overpass.private.coffee/api/interpreter"]

# -----------------------------
# 1. Consultar a Overpass (só se o arquivo ainda não existe)
# -----------------------------
print("1. Coleta")
if ARQ_OSM.exists():
    print("   já existe, pulando:", ARQ_OSM.relative_to(RAIZ))
else:
    servidor_usado = None
    for url in SERVIDORES:
        try:
            print("   consultando:", url)
            r = requests.post(url, data={"data": CONSULTA}, headers=HEADERS, timeout=300)
            r.raise_for_status()
            r.json()  # falha se o servidor devolveu uma página de erro em vez de JSON
            servidor_usado = url
            break
        except Exception as e:
            print("   falhou:", url, "-", type(e).__name__, e)

    if servidor_usado is None:
        raise RuntimeError("nenhum servidor Overpass respondeu; tente de novo em alguns minutos")

    # Salva a resposta exatamente como veio
    ARQ_OSM.write_bytes(r.content)

    # Metadados da coleta (a Tela 2 mostra fonte, link e data)
    coleta = {"fonte": "OpenStreetMap - escolas e unidades de saúde (Overpass API)",
              "url": "https://www.openstreetmap.org/copyright",
              "servidor": servidor_usado,
              "consulta": CONSULTA.strip(),
              "data_coleta": datetime.now().isoformat(timespec="seconds"),
              "licenca": "ODbL 1.0 (© contribuidores do OpenStreetMap)",
              "arquivos": [ARQ_OSM.name]}
    ARQ_COLETA.write_text(json.dumps(coleta, ensure_ascii=False, indent=2), encoding="utf-8")
    print("   salvo em", ARQ_OSM.relative_to(RAIZ))

# -----------------------------
# 2. Verificação
# -----------------------------
print("\n2. Verificação")
with open(ARQ_OSM, encoding="utf-8") as f:
    bruto = json.load(f)

# Data da base OSM usada pelo servidor (o OSM muda todo dia)
print("Base OSM do servidor em:", bruto["osm3s"]["timestamp_osm_base"])

# Uma linha por elemento; as tags viram colunas "tags.<nome>"
osm = pd.json_normalize(bruto["elements"])
print("Registros:", osm.shape[0], "| Colunas:", osm.shape[1])

# Nós têm lat/lon; áreas (way/relation) têm center.lat/center.lon
osm["lat"] = osm["lat"].fillna(osm["center.lat"])
osm["lon"] = osm["lon"].fillna(osm["center.lon"])

print("\nTipo de elemento OSM:")
print(osm["type"].value_counts())

print("\nContagem por tipo de amenity:")
print(osm["tags.amenity"].value_counts())

sem_nome = osm["tags.name"].isnull()
print("\nRegistros sem nome:", sem_nome.sum(), f"({sem_nome.mean():.1%})")
print("\nSem nome por amenity:")
print(osm.loc[sem_nome, "tags.amenity"].value_counts())

print("\nValores faltantes nas colunas principais:")
print(osm[["type", "id", "lat", "lon", "tags.amenity", "tags.name"]].isnull().sum())

# O id só é único dentro de cada tipo (node 1 e way 1 são coisas diferentes)
print("\nDuplicados (type + id):", osm.duplicated(subset=["type", "id"]).sum())

print("\nLatitude e longitude:")
print(osm[["lat", "lon"]].describe())
