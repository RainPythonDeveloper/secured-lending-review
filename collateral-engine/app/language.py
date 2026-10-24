"""One interface language for every page of the console."""

import streamlit as st

from collateral_engine.i18n import Language

# The choice lives under a plain session key. Streamlit drops the state of a widget that is not
# drawn in a run, so the selector's own key would forget the language on every page switch.
LANGUAGE_KEY = "language"
LANGUAGE_WIDGET_KEY = "language_choice"
LANGUAGE_LABELS = {Language.GEORGIAN: "ქართული", Language.ENGLISH: "English"}
# The label does not change with the language, so the widget keeps its identity.
SELECTOR_LABEL = "ენა / Language"


def current_language() -> Language:
    return st.session_state.get(LANGUAGE_KEY, Language.GEORGIAN)


def _remember_language() -> None:
    st.session_state[LANGUAGE_KEY] = st.session_state[LANGUAGE_WIDGET_KEY]


def render_language_selector() -> None:
    st.session_state[LANGUAGE_WIDGET_KEY] = current_language()
    st.sidebar.radio(
        SELECTOR_LABEL,
        list(Language),
        format_func=LANGUAGE_LABELS.get,
        key=LANGUAGE_WIDGET_KEY,
        horizontal=True,
        on_change=_remember_language,
    )
