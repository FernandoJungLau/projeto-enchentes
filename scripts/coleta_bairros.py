# Coleta da malha oficial de bairros de Porto Alegre (LC 12.112/16), a mesma divisão
# de 94 bairros usada pelo INCT.
# Rodar da raiz do repositório: python scripts/coleta_bairros.py
#
# Fonte: https://prefeitura.poa.br/carta-de-servicos/mapas-digitais-da-smamus
# Confere o robots.txt antes de baixar e não baixa de novo o que já existe.

import json
import re
import time
import zipfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import geopandas as gpd
import requests

# 0. Configurações
RAIZ = Path(__file__).resolve().parents[1]
PASTA = RAIZ / "dados" / "originais" / "bairros"
PASTA.mkdir(parents=True, exist_ok=True)
ARQ_COLETA = PASTA / "_coleta.json"

PAGINA = "https://prefeitura.poa.br/carta-de-servicos/mapas-digitais-da-smamus"
# nomes dos arquivos na página: a malha e os metadados dela
ARQUIVOS = ["Bairros_LC12112_16.zip", "bairro_vig_metadados.zip"]

HEADERS = {"User-Agent": "projeto-enchentes-pucrs (trabalho academico)"}
PAUSA_S = 5  # entre requisições ao mesmo servidor


def permitido(url):
    """True se o robots.txt do servidor deixa baixar a URL (robots.txt ausente = permitido)."""
    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    r = requests.get(base + "/robots.txt", headers=HEADERS, timeout=30)
    if r.status_code == 404:
        print(f"   {base}/robots.txt: não existe (404), sem restrições")
        return True
    rp = RobotFileParser()
    rp.parse(r.text.splitlines())
    ok = rp.can_fetch(HEADERS["User-Agent"], url)
    print(f"   {base}/robots.txt: {'permite' if ok else 'não permite'} {urlparse(url).path}")
    return ok

# 1. Achar os links na página da Prefeitura
print("1. Coleta")
faltando = [a for a in ARQUIVOS if not (PASTA / a).exists()]
if not faltando:
    print("   já existem, pulando:", ", ".join(ARQUIVOS))
else:
    if not permitido(PAGINA):
        raise RuntimeError("robots.txt não permite ler a página da Prefeitura")
    html = requests.get(PAGINA, headers=HEADERS, timeout=60).text
    links = {urljoin(PAGINA, h) for h in re.findall(r'href="([^"]+)"', html)}
    urls = {}
    for nome in ARQUIVOS:
        achados = [u for u in links if u.endswith("/" + nome)]
        if not achados:
            raise RuntimeError(f"link para {nome} não encontrado em {PAGINA}")
        urls[nome] = achados[0]

    # 2. Baixar o que falta
    coleta = (json.loads(ARQ_COLETA.read_text(encoding="utf-8"))
              if ARQ_COLETA.exists() else {"arquivos": {}})
    for nome in faltando:
        url = urls[nome]
        if not permitido(url):
            raise RuntimeError(f"robots.txt não permite baixar {url}")
        time.sleep(PAUSA_S)
        print("   baixando:", url)
        r = requests.get(url, headers=HEADERS, timeout=300)
        r.raise_for_status()
        if not r.content.startswith(b"PK"):  # todo .zip começa com "PK"
            raise RuntimeError(f"{nome}: a resposta não é um .zip")
        (PASTA / nome).write_bytes(r.content)
        coleta["arquivos"][nome] = {
            "url": url,
            "tamanho_bytes": len(r.content),
            "data_coleta": datetime.now().isoformat(timespec="seconds"),
        }

    coleta.update({
        "fonte": "Prefeitura de Porto Alegre (SMAMUS) - Bairros (LC 12.112/16)",
        "url": PAGINA,
        "licenca": "Dados públicos da Prefeitura de Porto Alegre, uso com citação da fonte",
    })
    ARQ_COLETA.write_text(json.dumps(coleta, ensure_ascii=False, indent=2), encoding="utf-8")
    print("   salvo em", PASTA.relative_to(RAIZ))

# 3. Verificação
print("\n2. Verificação")
with zipfile.ZipFile(PASTA / ARQUIVOS[0]) as z:
    print("Arquivos no .zip:", z.namelist())
bairros = gpd.read_file(PASTA / ARQUIVOS[0])
print("Feições:", len(bairros), "| CRS:", bairros.crs)
print("Colunas:", list(bairros.columns))
print(bairros.drop(columns="geometry").head())
print("Geometrias inválidas:", (~bairros.is_valid).sum())
