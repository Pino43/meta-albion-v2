import pytest

from albion_analytics.regions import parse_region_filter


def test_parse_region_filter_empty_means_all() -> None:
    assert len(parse_region_filter("")) == 3


def test_parse_region_filter_subset() -> None:
    assert parse_region_filter("europe") == ["europe"]


def test_parse_region_filter_unknown() -> None:
    with pytest.raises(ValueError, match="Unknown"):
        parse_region_filter("mars")
