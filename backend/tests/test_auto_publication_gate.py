from app.services.auto_publication_gate import publication_decision


def test_pending_candidate_cannot_be_published_without_proof():
    eligible, reasons = publication_decision({
        "title": "Example", "hosting_college": "Example University",
        "official_source_url": "https://example.edu/event",
        "registration_url": "https://example.edu/register",
        "start_date": "2027-01-01", "end_date": "2027-01-02",
    })
    assert not eligible
    assert "database_duplicate_check_missing" in reasons
    assert "source_permission_unverified" in reasons


def test_verified_unique_event_can_pass_gate():
    eligible, reasons = publication_decision({
        "title": "Example", "hosting_college": "Example University",
        "official_source_url": "https://example.edu/event",
        "registration_url": "https://example.edu/register",
        "start_date": "2027-01-01", "end_date": "2027-01-02",
    }, source_permission_verified=True, source_verified=True,
       duplicate_checked=True, institution_verified=True)
    assert eligible and not reasons


def test_duplicate_or_uncertainty_blocks_publication():
    eligible, reasons = publication_decision({
        "title": "Example", "hosting_college": "Example University",
        "official_source_url": "https://example.edu/event",
        "registration_url": "https://example.edu/register",
        "start_date": "2027-01-01", "end_date": "2027-01-02",
        "uncertainty": ["conflicting year"],
    }, source_permission_verified=True, source_verified=True,
       duplicate_checked=True, duplicate_found=True, institution_verified=True)
    assert not eligible
    assert "duplicate" in reasons
    assert "unresolved_uncertainty" in reasons
