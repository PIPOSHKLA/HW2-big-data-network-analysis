"""Streamlit Community Cloud default entry point.

Streamlit Cloud looks for `streamlit_app.py` by default; the actual app lives in
`app.py`. This runs it fresh on every rerun so interactivity is preserved.
"""
import os
import runpy

runpy.run_path(os.path.join(os.path.dirname(__file__), "app.py"), run_name="__main__")
