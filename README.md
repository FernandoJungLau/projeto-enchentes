# Projeto Extensionista - Análise de Dados de Enchentes do INCT SiMAI

Integrantes do grupo: Fernando Lau, Piedro Nunes e Victória Marques
## Como rodar

Requisitos: Python 3.13 (ou 3.10+) e internet para a coleta.

```bash
# 1. Ambiente
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Coleta das bases externas (rodar da raiz do repositório)
python scripts/coleta_zenodo.py    # UFRGS/IPH: glossário, abrigos e GeoPackage (~196 MB, alguns minutos)
python scripts/coleta_osm.py       # OpenStreetMap: escolas e unidades de saúde
python scripts/coleta_ana.py       # ANA: nível do Guaíba, mai-jun/2024

# 3. Notebook com a visão geral das fontes
jupyter notebook notebooks/fontes_enchentes_rs.ipynb
```

Os scripts podem ser rodados mais de uma vez: se o arquivo bruto já existe em `dados/originais/<base>/`, ele não é baixado de novo.
Cada pasta tem um `_coleta.json` com a fonte, o link, a licença e a data da coleta.

### Arquivo grande fora do GitHub

`dados/originais/zenodo/cheias_rhguaiba_2024_db_v12.gpkg` (196 MB) não está no repositório porque passa de 50 MB.
Para obtê-lo, rode `python scripts/coleta_zenodo.py`. O script baixa do [Zenodo, registro 13227745](https://zenodo.org/records/13227745), confere o md5 e, se a conexão cair, continua de onde parou na próxima execução.

Decisões tomadas na coleta (versão do Zenodo, camada da mancha, grafia dos bairros, período da ANA): [relatorios/decisoes_coleta.md](relatorios/decisoes_coleta.md).
