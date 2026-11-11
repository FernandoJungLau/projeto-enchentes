# Coleta do nível do Guaíba - ANA (Hidrotelemetria)
# Rodar da raiz do repositório: python scripts/coleta_ana.py
#
# Estação 87444000 - Usina do Gasômetro (Porto Alegre)
# Serviço: http://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicos
# Licença: dados abertos da ANA, uso livre com citação da fonte.
# Coleta responsável: um pedido por mês, XML salvo em disco; se o arquivo
# já existe, não pede de novo.

import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

# -----------------------------
# 0. Configurações
# -----------------------------
RAIZ = Path(__file__).resolve().parents[1]
PASTA = RAIZ / "dados" / "originais" / "ana"
PASTA.mkdir(parents=True, exist_ok=True)

URL = "http://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicos"
ESTACAO = 87444000
HEADERS = {"User-Agent": "projeto-enchentes-pucrs (trabalho academico)"}

# Período de 01/05/2024 a 30/06/2024, dividido por mês
# (respostas menores e um arquivo bruto por mês)
MESES = [("2024-05", "01/05/2024", "31/05/2024"),
         ("2024-06", "01/06/2024", "30/06/2024")]

# Nome da tag de cada leitura no XML (com a grafia da própria ANA)
TAG = "DadosHidrometereologicos"

# -----------------------------
# 1. Baixar um XML por mês (só se ainda não existe)
# -----------------------------
print("1. Coleta")
arq_coleta = PASTA / "_coleta.json"
if arq_coleta.exists():
    coleta = json.loads(arq_coleta.read_text(encoding="utf-8"))
else:
    coleta = {"fonte": "ANA - Hidrotelemetria, estação 87444000 (Usina do Gasômetro, Porto Alegre)",
              "url": URL,
              "licenca": "Dados abertos da ANA - uso livre com citação da fonte",
              "arquivos": {}}

falhas = []
for mes, inicio, fim in MESES:
    destino = PASTA / f"ana_{ESTACAO}_{mes}.xml"
    if destino.exists():
        print("   já existe, pulando:", destino.name)
        continue

    parametros = {"codEstacao": ESTACAO, "dataInicio": inicio, "dataFim": fim}
    print("   consultando:", mes)
    try:
        r = requests.get(URL, params=parametros, headers=HEADERS, timeout=120)
        r.raise_for_status()
        raiz = ET.fromstring(r.content)
    except Exception as e:
        # O serviço às vezes fica instável: mostra o erro e segue para o próximo mês
        print("   ERRO em", mes, "-", type(e).__name__, e)
        falhas.append(mes)
        continue

    # Quando não há dados, a ANA responde 200 com uma tag <Error> dentro do XML.
    # Nesse caso NÃO salvamos, senão o "já existe" guardaria o erro para sempre.
    leituras = list(raiz.iter(TAG))
    if len(leituras) == 0:
        erro = raiz.find(".//Error")
        print("   ANA sem dados para", mes, "-", erro.text if erro is not None else "resposta vazia")
        falhas.append(mes)
        continue

    # Salva o XML exatamente como veio
    destino.write_bytes(r.content)
    print("   salvo:", destino.name, "-", len(leituras), "leituras")

    coleta["arquivos"][destino.name] = {"parametros": parametros,
                                        "url": r.url,
                                        "data_coleta": datetime.now().isoformat(timespec="seconds")}
    arq_coleta.write_text(json.dumps(coleta, ensure_ascii=False, indent=2), encoding="utf-8")

# -----------------------------
# 2. Verificação
# -----------------------------
print("\n2. Verificação")

# Lê todos os XMLs salvos e junta numa tabela (uma linha por leitura)
linhas = []
for arq in sorted(PASTA.glob(f"ana_{ESTACAO}_*.xml")):
    raiz = ET.parse(arq).getroot()
    for leitura in raiz.iter(TAG):
        registro = {campo.tag: campo.text for campo in leitura}
        registro["arquivo"] = arq.name
        linhas.append(registro)

# Se nenhum mês foi salvo (serviço fora do ar ou sem dados), não há o que verificar
if len(linhas) == 0:
    print("Nenhuma leitura salva em", PASTA.relative_to(RAIZ))
    print("Meses sem dados ou com erro:", falhas)
    print("O serviço da ANA às vezes fica instável: tente de novo mais tarde.")
    raise SystemExit(1)

ana = pd.DataFrame(linhas)
print("Arquivos lidos:", ana["arquivo"].nunique(), "| Leituras:", ana.shape[0])
print("Colunas:", list(ana.columns))

# Texto -> data e número (valores vazios viram NaT/NaN)
ana["DataHora"] = pd.to_datetime(ana["DataHora"].str.strip())
ana["Nivel"] = pd.to_numeric(ana["Nivel"], errors="coerce")

print("\nPrimeira leitura:", ana["DataHora"].min())
print("Última leitura:", ana["DataHora"].max())

print("\nLeituras por arquivo:")
print(ana["arquivo"].value_counts().sort_index())

# Nível vem em centímetros, na régua da própria estação
print("\nNível mínimo (cm):", ana["Nivel"].min())
print("Nível máximo (cm):", ana["Nivel"].max(),
      "em", ana.loc[ana["Nivel"].idxmax(), "DataHora"])
print("Leituras com nível vazio:", ana["Nivel"].isnull().sum())

print("\nResumo do nível (cm):")
print(ana["Nivel"].describe())

print("\nValores faltantes por coluna:")
print(ana.isnull().sum())

print("\nLeituras duplicadas (mesma data e hora):", ana.duplicated(subset=["DataHora"]).sum())

# Leituras são a cada 15 min: 96 por dia quando a estação funciona o dia todo
por_dia = ana.groupby(ana["DataHora"].dt.date).size()
print("\nDias com leitura:", len(por_dia), "| dias com menos de 96 leituras:", (por_dia < 96).sum())

if falhas:
    print("\nATENÇÃO: meses sem dados ou com erro:", falhas)
    print("Rode o script de novo mais tarde: só os meses que faltam serão pedidos.")
    raise SystemExit(1)  # código de saída 1 = coleta incompleta
