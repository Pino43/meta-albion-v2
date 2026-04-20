from datetime import UTC

from albion_analytics.storage.events_repo import _normalize_raw_event


def test_normalize_raw_event_accepts_valid_row() -> None:
    row = _normalize_raw_event(
        {
            "EventId": "123",
            "TimeStamp": "2026-04-20T12:34:56Z",
            "Version": "4",
        }
    )

    assert row is not None
    assert row.event_id == 123
    assert row.time_stamp.tzinfo == UTC
    assert row.api_payload_version == 4


def test_normalize_raw_event_skips_missing_event_id() -> None:
    assert _normalize_raw_event({"TimeStamp": "2026-04-20T12:34:56Z"}) is None


def test_normalize_raw_event_skips_invalid_event_id() -> None:
    assert _normalize_raw_event({"EventId": "bad", "TimeStamp": "2026-04-20T12:34:56Z"}) is None


def test_normalize_raw_event_skips_invalid_timestamp() -> None:
    assert _normalize_raw_event({"EventId": 1, "TimeStamp": "not-a-date"}) is None


def test_normalize_raw_event_keeps_row_with_invalid_version_as_none() -> None:
    row = _normalize_raw_event(
        {
            "EventId": 123,
            "TimeStamp": "2026-04-20T12:34:56Z",
            "Version": "not-a-version",
        }
    )

    assert row is not None
    assert row.api_payload_version is None
