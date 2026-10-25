"""One interface language for every page of the console."""

from collections.abc import Callable, Sequence

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


# Widgets drawn with choice(), by the key that holds their value.
_CHOICE_WIDGETS_KEY = "_choice_widgets"


def choice_widget_key(key: str, language: Language) -> str:
    return f"{key}@{language.value}"


def _seed_marker(widget_key: str) -> str:
    return f"{widget_key}#seed"


def choice[Option](
    widget: Callable[..., Option],
    label: str,
    options: Sequence[Option],
    format_func: Callable[[Option], str],
    key: str,
    *,
    on_change: Callable[[], None] | None = None,
    in_form: bool = False,
    **widget_options: object,
) -> Option:
    """A select box or radio whose labels follow the interface language.

    The browser sends back the label of the chosen option, so a widget whose labels changed with
    the language returned a stale label as its value. Each language therefore gets its own
    widget, and the choice itself lives under `key`, where the rest of the console reads it.
    Inside a form, call remember_choices() from the submit handler.
    """
    widget_key = choice_widget_key(key, current_language())
    st.session_state.setdefault(key, options[0])
    _seed_widget(key, widget_key)
    st.session_state.setdefault(_CHOICE_WIDGETS_KEY, {})[key] = widget_key

    def remember() -> None:
        _remember(key, widget_key)
        if on_change is not None:
            on_change()

    callback = {} if in_form else {"on_change": remember}
    return widget(
        label, options, format_func=format_func, key=widget_key, **callback, **widget_options
    )


def _seed_widget(key: str, widget_key: str) -> None:
    # Seed a new widget, or one whose value the console changed, for example a loaded demo case;
    # otherwise keep what the officer selected and has not submitted yet.
    value = st.session_state[key]
    marker = _seed_marker(widget_key)
    if widget_key not in st.session_state or st.session_state.get(marker) != value:
        st.session_state[widget_key] = value
        st.session_state[marker] = value


def _remember(key: str, widget_key: str) -> None:
    value = st.session_state[widget_key]
    st.session_state[key] = value
    st.session_state[_seed_marker(widget_key)] = value


def remember_choices() -> None:
    """Copies the values of choice() widgets in a submitted form to their keys."""
    for key, widget_key in st.session_state.get(_CHOICE_WIDGETS_KEY, {}).items():
        if widget_key in st.session_state:
            _remember(key, widget_key)
