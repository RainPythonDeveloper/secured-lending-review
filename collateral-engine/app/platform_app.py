"""One console for the whole loan application: overview, full application, collateral, income.

streamlit run app/platform_app.py
"""

from pathlib import Path

import streamlit as st

import design
from collateral_engine.settings import INCOME_ENGINE_ROOT
from language import render_language_selector

APP_DIR = Path(__file__).resolve().parent
INCOME_CONSOLE_PATH = INCOME_ENGINE_ROOT / "app" / "streamlit_app.py"

st.set_page_config(page_title="Secured Lending Review", page_icon="🏦", layout="wide")

# Both consoles are named streamlit_app.py, so every page gets its own URL path.
pages = {
    "": [
        st.Page(
            APP_DIR / "overview_page.py",
            title="მიმოხილვა · Overview",
            icon="✨",
            url_path="overview",
            default=True,
        ),
        st.Page(
            APP_DIR / "full_application_page.py",
            title="განაცხადი · Application",
            icon="🏦",
            url_path="full-application",
        ),
    ],
    "მოდულები · Modules": [
        st.Page(
            APP_DIR / "streamlit_app.py",
            title="გირაო · Collateral",
            icon="🏠",
            url_path="collateral",
        ),
        st.Page(
            INCOME_CONSOLE_PATH,
            title="შემოსავალი · Income",
            icon="💼",
            url_path="income",
        ),
    ],
}
navigation = st.navigation(pages)
design.apply_styles()
# Drawn once here, above every page's own sidebar, so all pages share one language.
render_language_selector()
navigation.run()
