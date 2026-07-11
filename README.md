# HW2 — Big Data Network Analysis (Streamlit)

Interactive dashboard for the April 2009 MemeTracker domain hyperlink graph:
7 centrality / community measures computed in Neo4j GDS (Cypher).

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```
Opens at http://localhost:8501

## Files the app needs (keep alongside app.py)
- `app.py`
- `viz_data.json`        (network + summary + communities)
- `core_metrics.csv`     (10,290 core domains × 7 measures)
- `requirements.txt`
- `.streamlit/config.toml`

## Deploy a public link (Streamlit Community Cloud)
1. Push this folder to a **GitHub** repo (public or private).
2. Go to https://share.streamlit.io → **New app** → sign in with GitHub.
3. Pick the repo, branch, and `app.py` as the entry point → **Deploy**.
4. You get a public URL like `https://<your-app>.streamlit.app` to submit HW2.
```bash
# minimal push
git init && git add app.py viz_data.json core_metrics.csv requirements.txt .streamlit
git commit -m "HW2 Big Data Network Analysis (Streamlit)"
git branch -M main
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```
