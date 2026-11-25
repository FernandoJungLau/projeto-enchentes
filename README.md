# Projeto Extensionista - Enchentes INCT SiMAI

Integrantes: Fernando Lau, Piedro Nunes e Victória Marques

## Link para o Dashboard
https://projeto-enchentes-grupo-09.streamlit.app


## Como rodar

### Coleta 

Cria o ambiente virtual python e baixa os dados através das fontes: Zenodo, OSM e ANA.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python scripts/coleta_zenodo.py
python scripts/coleta_osm.py
python scripts/coleta_ana.py
```

### Notebooks

Depois da coleta, executar os notebooks para gerar os dados processados:

```bash
pip install jupyter
jupyter nbconvert --to notebook --execute --inplace notebooks/*.ipynb
```

Também dá para abrir com jupyter notebook e rodar cada um pelo navegador.

### Dashboard

Preparar os dados do dashboard e rodar localmente:

```bash
python scripts/coleta_bairros.py
python scripts/prepara_dashboard.py

pip install -r app/requirements.txt
streamlit run app/app.py
```
