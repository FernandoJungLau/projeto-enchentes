# Dashboard

Rodar a partir da raiz do repositório:

```bash
pip install -r app/requirements.txt

# só se o .gpkg do Zenodo, a malha de bairros ou os dados do OSM mudarem
# (precisa também do requirements.txt da raiz)
python scripts/coleta_bairros.py
python scripts/prepara_dashboard.py

streamlit run app/app.py
```

O app lê apenas `dados/processados/` e os `_coleta.json`, por isso funciona sem o `.gpkg` (por exemplo, no Streamlit Community Cloud, com main file `app/app.py`).
