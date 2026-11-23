"""BAC-02: tests for v4.1 event fields, filters and unknown-contact fallback.

These tests only exercise the Pydantic schemas, so they need no database.
"""
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas.event import EventCreate, EventListParams, EventResponse


def make_event(**overrides):
    data = {"title": "Test Hackathon", "organization": "Test Org"}
    data.update(overrides)
    return EventCreate(**data)


def test_old_payload_still_valid_and_gets_defaults():
    event = make_event()
    assert event.category is None
    assert event.tags == []
    assert event.lifecycle_state == "upcoming"


def test_missing_contacts_serialize_as_unknown():
    contacts = make_event().contacts.model_dump()
    assert contacts == {
        "name": "unknown",
        "designation": "unknown",
        "email": "unknown",
        "phone": "unknown",
    }


def test_partial_contacts_fill_missing_fields_with_unknown():
    event = make_event(contacts={"name": "Asha", "email": None, "phone": "  "})
    assert event.contacts.name == "Asha"
    assert event.contacts.designation == "unknown"
    assert event.contacts.email == "unknown"
    assert event.contacts.phone == "unknown"


def test_legacy_row_without_v41_data_reads_without_error():
    response = EventResponse.model_validate(
        {"id": 1, "title": "Legacy Event", "tags": None, "contacts": None}
    )
    assert response.tags == []
    assert response.contacts.email == "unknown"
    assert response.category is None


@pytest.mark.parametrize("category", ["college", "corporate", "community", "government", "startup"])
def test_valid_categories_accepted(category):
    assert make_event(category=category).category == category


def test_invalid_category_rejected():
    with pytest.raises(ValidationError):
        make_event(category="banana")


@pytest.mark.parametrize("state", ["upcoming", "active", "completed", "cancelled"])
def test_valid_lifecycle_states_accepted(state):
    assert make_event(lifecycle_state=state).lifecycle_state == state


def test_invalid_lifecycle_state_rejected():
    with pytest.raises(ValidationError):
        make_event(lifecycle_state="paused")


def test_end_date_before_start_date_rejected():
    with pytest.raises(ValidationError):
        make_event(start_date=datetime(2026, 12, 10), end_date=datetime(2026, 12, 1))


def test_valid_date_range_accepted():
    event = make_event(start_date=datetime(2026, 12, 1), end_date=datetime(2026, 12, 3))
    assert event.end_date >= event.start_date


def test_list_params_accept_new_filters():
    params = EventListParams(
        category="college",
        tag="python",
        lifecycle_state="active",
        country="India",
        city="Hyderabad",
    )
    assert params.category == "college"
    assert params.tag == "python"
    assert params.lifecycle_state == "active"
    assert params.country == "India"
    assert params.city == "Hyderabad"


def test_list_params_reject_invalid_category():
    with pytest.raises(ValidationError):
        EventListParams(category="banana")


def test_list_params_reject_invalid_lifecycle_state():
    with pytest.raises(ValidationError):
        EventListParams(lifecycle_state="paused")
