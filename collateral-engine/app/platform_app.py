"""One console for the whole loan application: full application, collateral and income.

streamlit run app/platform_app.py
"""

from pathlib import Path

import streamlit as st

from collateral_engine.settings import INCOME_ENGINE_ROOT
from language import render_language_selector

APP_DIR = Path(__file__).resolve().parent
INCOME_CONSOLE_PATH = INCOME_ENGINE_ROOT / "app" / "streamlit_app.py"

# Both consoles are named streamlit_app.py, so every page gets its own URL path.
pages = [
    st.Page(
        APP_DIR / "full_application_page.py",
        title="სრული განაცხადი · Full application",
        icon="🏦",
        url_path="full-application",
        default=True,
    ),
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
]
navigation = st.navigation(pages)
# Drawn once here, above every page's own sidebar, so all pages share one language.
render_language_selector()
navigation.run()
