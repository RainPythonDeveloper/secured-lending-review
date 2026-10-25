"""One console for the whole loan application: an overview and the application pipeline.

streamlit run app/platform_app.py
"""

from pathlib import Path

import streamlit as st

import design
from language import render_language_selector

APP_DIR = Path(__file__).resolve().parent

st.set_page_config(page_title="Secured Lending Review", page_icon="🏦", layout="wide")

pages = [
    st.Page(
        APP_DIR / "overview_page.py",
        title="მიმოხილვა · Overview",
        icon="✨",
        url_path="overview",
        default=True,
    ),
    st.Page(
        APP_DIR / "application_page.py",
        title="სესხის განაცხადი · Loan application",
        icon="🏦",
        url_path="application",
    ),
]
navigation = st.navigation(pages)
design.apply_styles()
# Drawn once here, above every page's own sidebar, so all pages share one language.
render_language_selector()
navigation.run()
