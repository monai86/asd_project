"""Hugging Face Spaces entry point for the Pastel dashboard.

Local development can still run:
    streamlit run app/dashboard_unified.py
"""

from pathlib import Path
import runpy


runpy.run_path(str(Path(__file__).parent / "app" / "dashboard_unified.py"), run_name="__main__")
