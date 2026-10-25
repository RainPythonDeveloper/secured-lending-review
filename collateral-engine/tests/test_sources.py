"""The reference list on the Overview page: every source is linked, described and in order."""

from urllib.parse import urlparse

import pytest

from collateral_engine.i18n import Language
from collateral_engine.sources import (
    GROUP_NAMES,
    SOURCE_KIND_NAMES,
    SOURCES,
    SourceGroup,
    SourceKind,
)

LINKED_SOURCES = [source for source in SOURCES if source.url is not None]


@pytest.mark.parametrize("source", LINKED_SOURCES, ids=lambda source: source.title[:40])
def test_source_links_to_a_public_https_address(source) -> None:
    address = urlparse(source.url)

    assert address.scheme == "https"
    assert address.netloc not in {"localhost", "127.0.0.1"}


def test_no_source_is_listed_twice() -> None:
    urls = [source.url for source in LINKED_SOURCES]

    assert len(urls) == len(set(urls))


@pytest.mark.parametrize("source", SOURCES, ids=lambda source: source.title[:40])
def test_source_says_what_it_backs_in_both_languages(source) -> None:
    assert all(source.used_for[language] for language in Language)


def test_sources_are_listed_group_by_group() -> None:
    # The page numbers the sources in this order, so a group must not be split.
    group_order = list(SourceGroup)

    positions = [group_order.index(source.group) for source in SOURCES]

    assert positions == sorted(positions)


def test_every_source_has_a_date() -> None:
    assert all(source.date for source in SOURCES)


@pytest.mark.parametrize(
    ("names", "members"), [(GROUP_NAMES, SourceGroup), (SOURCE_KIND_NAMES, SourceKind)]
)
def test_every_group_and_kind_has_georgian_and_english_names(names, members) -> None:
    assert set(names) == set(members)
