# Projeto Extensionista - Enchentes INCT SiMAI

Integrantes: Fernando Lau, Piedro Nunes e Victória Marques

## Como rodar

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python scripts/coleta_zenodo.py
python scripts/coleta_osm.py
python scripts/coleta_ana.py
```

Os dados ficam em `dados/originais/`. O arquivo `.gpkg` do Zenodo (196 MB) não está no repositório, ele é baixado pelo `coleta_zenodo.py`.
