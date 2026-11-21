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
python scripts/coleta_bairros.py
```

Os dados ficam em `dados/originais/`. O arquivo `.gpkg` do Zenodo (196 MB) não está no repositório, ele é baixado pelo `coleta_zenodo.py`.

## Dashboard

```bash
# rodar de novo se o .gpkg, a malha de bairros ou os dados do OSM mudarem
python scripts/prepara_dashboard.py

streamlit run app/app.py
```

O app lê apenas `dados/processados/` e os `_coleta.json`, por isso funciona sem o `.gpkg` (por exemplo, no Streamlit Community Cloud, com main file `app/app.py`).
