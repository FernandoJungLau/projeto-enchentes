# Coleta do Banco de dados das cheias 2024 - UFRGS/IPH (Zenodo)
# Rodar da raiz do repositório: python scripts/coleta_zenodo.py
#
# Fonte: https://zenodo.org/records/13227745 (versão v.1.2, licença CC-BY 4.0)
# Coleta responsável: o robots.txt do Zenodo bloqueia /api, mas libera
# /api/records/*/files e pede Crawl-delay de 10 s. Por isso usamos só:
#   - /api/records/<id>/files               -> lista de arquivos com tamanho
#   - /api/records/<id>/files/<nome>/content -> download de cada arquivo
#   - /records/<id>/latest                   -> descobrir se existe versão mais nova

import hashlib
import json
import time
import unicodedata
from datetime import datetime
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pyogrio
import requests

# -----------------------------
# 0. Configurações
# -----------------------------
# Caminhos montados a partir da localização do script (funciona de qualquer pasta)
RAIZ = Path(__file__).resolve().parents[1]
PASTA = RAIZ / "dados" / "originais" / "zenodo"
PASTA.mkdir(parents=True, exist_ok=True)

# Registro citado no relatório da Fase 1 (relatorios/base_dados.pdf)
REGISTRO = "13227745"
VERSAO = "v.1.2"  # informada na página do registro
LICENCA = "CC-BY-4.0"
URL_REGISTRO = f"https://zenodo.org/records/{REGISTRO}"

# Arquivos que vamos usar (nomes iguais aos do Zenodo)
ARQUIVOS = [
    "cheias_rhguaiba_2024_db_v12_glossario.csv",  # glossário das camadas
    "rs_crise_abrigos_24052024_20h.csv",          # abrigos em 24/05/2024
    "cheias_rhguaiba_2024_db_v12.gpkg",           # GeoPackage com as manchas
]

# User-Agent genérico identificando o projeto (sem e-mail)
HEADERS = {"User-Agent": "projeto-enchentes-pucrs (trabalho academico)"}
ESPERA = 10  # segundos entre requisições (Crawl-delay do robots.txt)

# -----------------------------
# 1. Listar os arquivos do registro
# -----------------------------
print("1. Arquivos do registro", REGISTRO)
r = requests.get(f"https://zenodo.org/api/records/{REGISTRO}/files",
                 headers=HEADERS, timeout=60)
r.raise_for_status()
lista = r.json()["entries"]

for arq in lista:
    print(f"   {arq['size'] / 1e6:9.1f} MB  {arq['key']}")

# -----------------------------
# 2. Verificar se existe versão mais nova (só avisa, não troca)
# -----------------------------
time.sleep(ESPERA)
r = requests.head(f"https://zenodo.org/records/{REGISTRO}/latest",
                  headers=HEADERS, timeout=60, allow_redirects=False)
mais_nova = r.headers.get("Location", "").rstrip("/").split("/")[-1]

print("\n2. Versão")
if mais_nova and mais_nova != REGISTRO:
    print(f"   AVISO: existe versão mais nova do conjunto: https://zenodo.org/records/{mais_nova}")
    print(f"   Continuamos usando o registro {REGISTRO} ({VERSAO}), que é o citado no relatório.")
else:
    print(f"   O registro {REGISTRO} é a versão mais recente.")

# -----------------------------
# 3. Baixar os arquivos (só se ainda não existem)
# -----------------------------
print("\n3. Download")

# Lê o _coleta.json anterior, se existir, para guardar a data de cada download
arq_coleta = PASTA / "_coleta.json"
if arq_coleta.exists():
    coleta = json.loads(arq_coleta.read_text(encoding="utf-8"))
else:
    coleta = {"fonte": "UFRGS/IPH - Banco de dados das cheias na Região Hidrográfica do Lago Guaíba (Zenodo)",
              "url": URL_REGISTRO,
              "doi": f"10.5281/zenodo.{REGISTRO}",
              "versao": VERSAO,
              "licenca": LICENCA,
              "arquivos": {}}

for nome in ARQUIVOS:
    destino = PASTA / nome
    info = next(a for a in lista if a["key"] == nome)  # tamanho e checksum do Zenodo

    if destino.exists():
        print("   já existe, pulando:", nome)
    else:
        # Baixa em blocos para um arquivo .part e só renomeia no fim, para que
        # um download interrompido não seja confundido com um arquivo completo.
        # Se já existe um .part, pede só o que falta (cabeçalho Range).
        parcial = PASTA / (nome + ".part")
        ja_baixado = parcial.stat().st_size if parcial.exists() else 0
        cabecalhos = dict(HEADERS)
        if ja_baixado > 0:
            cabecalhos["Range"] = f"bytes={ja_baixado}-"
            print(f"   retomando: {nome} a partir de {ja_baixado / 1e6:.1f} MB")
        else:
            print("   baixando:", nome, f"({info['size'] / 1e6:.1f} MB)")

        time.sleep(ESPERA)
        with requests.get(info["links"]["content"], headers=cabecalhos, timeout=120, stream=True) as r:
            r.raise_for_status()
            modo = "ab" if r.status_code == 206 else "wb"  # 206 = servidor mandou só o pedaço que faltava
            with open(parcial, modo) as f:
                for bloco in r.iter_content(chunk_size=1024 * 1024):
                    f.write(bloco)

        # Confere tamanho e checksum (md5) com o que o Zenodo informa
        md5 = hashlib.md5()
        with open(parcial, "rb") as f:
            for bloco in iter(lambda: f.read(1024 * 1024), b""):
                md5.update(bloco)
        if parcial.stat().st_size != info["size"] or "md5:" + md5.hexdigest() != info["checksum"]:
            raise RuntimeError(f"arquivo {nome} veio corrompido; apague {parcial} e rode de novo")
        parcial.rename(destino)

    # Registra o arquivo nos metadados (se o arquivo já existia de uma coleta
    # sem registro, usa a data de modificação dele como data da coleta)
    if nome not in coleta["arquivos"]:
        data = datetime.fromtimestamp(destino.stat().st_mtime).isoformat(timespec="seconds")
        coleta["arquivos"][nome] = {"url": info["links"]["content"],
                                    "tamanho_bytes": info["size"],
                                    "checksum": info["checksum"],
                                    "data_coleta": data}

    # Salva depois de cada arquivo, para não perder o registro se algo falhar depois
    arq_coleta.write_text(json.dumps(coleta, ensure_ascii=False, indent=2), encoding="utf-8")

print("   metadados salvos em", arq_coleta.relative_to(RAIZ))

# -----------------------------
# 4. Verificação dos CSVs (glossário e abrigos)
# -----------------------------
print("\n4. Verificação dos CSVs")
glossario = pd.read_csv(PASTA / "cheias_rhguaiba_2024_db_v12_glossario.csv")
print("\nGlossário:", glossario.shape[0], "linhas | colunas:", list(glossario.columns))

abrigos = pd.read_csv(PASTA / "rs_crise_abrigos_24052024_20h.csv", sep=";")
print("\nAbrigos:", abrigos.shape[0], "linhas,", abrigos.shape[1], "colunas")
abrigos.info()
print("\nValores faltantes (abrigos):")
print(abrigos.isnull().sum())
print("\nLinhas duplicadas (abrigos):", abrigos.duplicated().sum())
print("\nAbrigos por cidade (10 primeiras):")
print(abrigos["CIDADE"].value_counts().head(10))

# -----------------------------
# 5. Camadas do GeoPackage
# -----------------------------
GPKG = PASTA / "cheias_rhguaiba_2024_db_v12.gpkg"
print("\n5. Camadas do GeoPackage")
camadas = pyogrio.list_layers(GPKG)
print("Total de camadas:", len(camadas))
for nome, tipo in camadas:
    print(f"   {nome:62s} {tipo}")

# Atenção: os nomes dentro do .gpkg não são iguais aos do glossário
# (ex.: glossário diz "..._agua_obs_20240506", o .gpkg tem "..._obs_20240506")
CAMADA_PRINCIPAL = "rhguaiba_planet-skysat_inundacao_obs_20240506"     # Planet/Skysat 06/05
CAMADA_ALTERNATIVA = "rhguaiba_sentinel2_agua_obs_06052024_validada"   # Sentinel-2 validada 06/05
CAMADA_BAIRROS = "poa_admin_bairros"


def normalizar(nome):
    # Maiúsculas, sem acento, sem apóstrofo e sem espaços repetidos
    # (os nomes de bairro mudam de grafia entre as fontes)
    nome = unicodedata.normalize("NFKD", nome)
    nome = "".join(c for c in nome if not unicodedata.combining(c))
    nome = nome.upper().replace("'", "").replace("’", "")
    return " ".join(nome.split())


# -----------------------------
# 6. Cobertura das manchas em Porto Alegre
# -----------------------------
print("\n6. Cobertura das manchas de maio/2024 em Porto Alegre")
bairros = gpd.read_file(GPKG, layer=CAMADA_BAIRROS)
print("Bairros na camada", CAMADA_BAIRROS + ":", len(bairros), "| CRS:", bairros.crs)

# Extensão de Porto Alegre no CRS das manchas (graus, EPSG:4326)
poa = bairros.to_crs("EPSG:4326")
x0, y0, x1, y1 = poa.total_bounds

tocados = {}
for camada in [CAMADA_PRINCIPAL, CAMADA_ALTERNATIVA]:
    info = pyogrio.read_info(GPKG, layer=camada)
    cx0, cy0, cx1, cy1 = info["total_bounds"]
    cobre_poa = cx0 <= x0 and cy0 <= y0 and cx1 >= x1 and cy1 >= y1

    # Lê só a parte da mancha que cai na extensão de Porto Alegre
    mancha = gpd.read_file(GPKG, layer=camada, bbox=(x0, y0, x1, y1)).to_crs(bairros.crs)
    juntos = gpd.sjoin(bairros, mancha[["geometry"]], predicate="intersects")
    tocados[camada] = set(juntos["nmbop"])

    print(f"\n{camada}")
    print("   CRS:", info["crs"], "| feições na região toda:", info["features"])
    print("   extensão cobre a extensão de Porto Alegre:", cobre_poa)
    print("   bairros tocados pela mancha:", len(tocados[camada]), "de", len(bairros))

so_alt = tocados[CAMADA_ALTERNATIVA] - tocados[CAMADA_PRINCIPAL]
print("\nBairros tocados pela Sentinel-2 e NÃO pela Planet/Skysat:", sorted(so_alt) or "nenhum")

# -----------------------------
# 7. Cruzamento com o INCT (nível 5,3 m) e grafia dos bairros
# -----------------------------
print("\n7. Cruzamento com o INCT")
with open(RAIZ / "dados" / "originais" / "INCT" / "data.json", encoding="utf-8") as f:
    inct = json.load(f)

nomes_inct = sorted(inct["5_3m"].keys())
nomes_gpkg = set(bairros["nmbop"])
exatos = [n for n in nomes_inct if n in nomes_gpkg]
normalizados = [n for n in nomes_inct if n not in nomes_gpkg and normalizar(n) in nomes_gpkg]
sem_par = [n for n in nomes_inct if normalizar(n) not in nomes_gpkg]
print("Bairros no INCT (5,3 m):", len(nomes_inct), "| na camada do .gpkg:", len(nomes_gpkg))
print("Iguais sem mexer:", len(exatos))
print("Iguais depois de normalizar (acento, maiúscula, apóstrofo):", len(normalizados))
print("Sem par no .gpkg:", len(sem_par), sem_par)
gpkg_sem_par = sorted(nomes_gpkg - {normalizar(n) for n in nomes_inct})
print("Do .gpkg sem par no INCT:", len(gpkg_sem_par), gpkg_sem_par)

# Bairros com prédios afetados no INCT a 5,3 m que a mancha principal não toca
atingidos = [n for n, v in inct["5_3m"].items() if v["affected_buildings"] > 0]
atingidos_comparaveis = [n for n in atingidos if normalizar(n) in nomes_gpkg]
fora_principal = sorted(n for n in atingidos_comparaveis if normalizar(n) not in tocados[CAMADA_PRINCIPAL])
fora_alternativa = sorted(n for n in atingidos_comparaveis if normalizar(n) not in tocados[CAMADA_ALTERNATIVA])
print("\nBairros atingidos no INCT a 5,3 m:", len(atingidos),
      "| comparáveis com o .gpkg:", len(atingidos_comparaveis))
print("Atingidos no INCT que a Planet/Skysat não toca:", fora_principal or "nenhum")
print("Atingidos no INCT que a Sentinel-2 não toca:", fora_alternativa or "nenhum")

# -----------------------------
# 8. Escolha da camada da mancha observada
# -----------------------------
# Regra (decidida pelo grupo): fica a Planet/Skysat se ela cobrir o município ou
# pelo menos todos os bairros atingidos; senão, usa a Sentinel-2 validada.
info_p = pyogrio.read_info(GPKG, layer=CAMADA_PRINCIPAL)
px0, py0, px1, py1 = info_p["total_bounds"]
principal_ok = (px0 <= x0 and py0 <= y0 and px1 >= x1 and py1 >= y1) or len(fora_principal) == 0
escolhida = CAMADA_PRINCIPAL if principal_ok else CAMADA_ALTERNATIVA

print("\n8. Camada escolhida para a mancha observada:", escolhida)
mancha = gpd.read_file(GPKG, layer=escolhida, bbox=(x0, y0, x1, y1))
print("CRS:", mancha.crs)
print("Colunas:", list(mancha.columns))
print("Feições na extensão de Porto Alegre:", len(mancha))
print(mancha.drop(columns="geometry").head())

# Guarda a escolha no _coleta.json para quem for usar os dados depois
coleta["camada_mancha_2024"] = escolhida
coleta["camada_bairros"] = CAMADA_BAIRROS
arq_coleta.write_text(json.dumps(coleta, ensure_ascii=False, indent=2), encoding="utf-8")
