
from datetime import datetime, timezone

from app.services.investor_resolution import (
    Entity,
    Alias,
    SourceEvidence,
    EntityClaim,
    normalize_name,
    compare_names,
    find_candidates,
    find_alias_matches,
    resolve_entity,
    get_latest_confirmed_claims,
    EntityAlias,
    EntityAliasSource,
    add_alias_source,
    get_alias_sources,
    update_alias_verification,
    update_claim_statuses,
)


ENTITIES = [
    Entity("INV001", "Accel Partners", "investor",
           "https://accel.com", "India"),
    Entity("INV002", "Sequoia Capital", "investor",
           "https://sequoiacap.com", "USA"),
    Entity("FUND001", "Accel Growth Fund", "fund",
           "https://accel.com", "India"),
    Entity("START001", "Blue Ridge Technologies", "startup",
           "https://blueridge.example", "India"),
]

ALIASES = [
    Alias("INV001", "Accel"),
    Alias("INV001", "Accel India"),
    Alias("INV002", "Sequoia"),
]


def test_normalize_name():
    assert normalize_name("  SEQUOIA   CAPITAL ") == "sequoia capital"


def test_normalize_legal_suffixes():
    assert normalize_name("Blue Ridge Technologies Pvt. Ltd.") == (
        "blue ridge technologies"
    )


def test_compare_names():
    assert compare_names("Accel", "Accel")["ratio"] == 100


def test_empty_name():
    assert normalize_name("") == ""


def test_generic_words_only():
    assert find_candidates("Ventures", ENTITIES) == []


def test_exact_alias_match():
    result = resolve_entity("Accel", ENTITIES, ALIASES)
    assert result["status"] == "exact_alias_match"


def test_ambiguous_alias():
    aliases = [
        Alias("INV001", "Accel"),
        Alias("INV002", "Accel"),
    ]

    result = resolve_entity("Accel", ENTITIES, aliases)
    assert result["status"] == "ambiguous_match"


def test_exact_name_match():
    result = resolve_entity(
        "Accel Partners Pvt Ltd",
        ENTITIES,
        ALIASES,
    )
    assert result["status"] == "exact_name_match"


def test_entity_type_separation():
    result = resolve_entity(
        "Accel Growth Fund",
        ENTITIES,
        ALIASES,
        entity_type="investor",
    )
    assert result["status"] == "no_match"


def test_fund_can_match_fund():
    result = resolve_entity(
        "Accel Growth Fund",
        ENTITIES,
        ALIASES,
        entity_type="fund",
    )
    assert result["status"] == "exact_name_match"


def test_candidate_type_filter():
    results = find_candidates(
        "Accel",
        ENTITIES,
        entity_type="investor",
    )

    assert all(
        item["entity_type"] == "investor"
        for item in results
    )


def test_fuzzy_match_without_corroboration_needs_evidence():
    result = resolve_entity(
        "Accel Partner",
        ENTITIES,
        ALIASES,
        entity_type="investor",
    )

    assert result["status"] in (
        "needs_more_evidence",
        "no_match",
    )


def test_fuzzy_match_with_same_website():
    result = resolve_entity(
        "Accel Partner",
        ENTITIES,
        ALIASES,
        entity_type="investor",
        attributes={"website": "https://accel.com"},
    )

    assert result["status"] == "high_confidence_match"


def test_fuzzy_match_with_same_country():
    result = resolve_entity(
        "Accel Partner",
        ENTITIES,
        ALIASES,
        entity_type="investor",
        attributes={"country": "India"},
    )

    assert result["status"] == "high_confidence_match"


def test_unrelated_entity_does_not_match():
    result = resolve_entity(
        "Completely Different Organization",
        ENTITIES,
        ALIASES,
    )

    assert result["status"] == "no_match"


def test_source_evidence_records_utc_timestamp():
    evidence = SourceEvidence(
        id="SRC001",
        source_url="https://example.com/investor",
    )

    assert evidence.source_url == "https://example.com/investor"
    assert evidence.created_at.tzinfo == timezone.utc


def test_unverified_claim_is_not_latest_confirmed():
    claim = EntityClaim(
        entity_type="investor",
        entity_id="INV001",
        field_name="country",
        value="India",
        source_evidence_id="SRC001",
        observed_at=datetime(2026, 11, 20, tzinfo=timezone.utc),
    )

    evidence = SourceEvidence(
        id="SRC001",
        source_url="https://example.com",
        verified_at=None,
    )

    result = get_latest_confirmed_claims([claim], [evidence])
    assert result == {}


def test_latest_verified_claim_is_selected():
    old_time = datetime(2026, 11, 20, tzinfo=timezone.utc)
    new_time = datetime(2026, 11, 25, tzinfo=timezone.utc)

    claims = [
        EntityClaim(
            "investor", "INV001", "country", "India", "SRC001", old_time
        ),
        EntityClaim(
            "investor", "INV001", "country", "USA", "SRC002", new_time
        ),
    ]

    evidence = [
        SourceEvidence(
            "SRC001", "https://one.example",
            verified_at=old_time,
        ),
        SourceEvidence(
            "SRC002", "https://two.example",
            verified_at=new_time,
        ),
    ]

    result = get_latest_confirmed_claims(claims, evidence)

    key = ("investor", "INV001", "country")
    assert result[key]["latest_confirmed"].value == "USA"
    assert result[key]["conflicts"] == []


def test_same_time_conflicting_claims_have_no_winner():
    observed = datetime(2026, 11, 25, tzinfo=timezone.utc)

    claims = [
        EntityClaim(
            "investor", "INV001", "country", "India", "SRC001", observed
        ),
        EntityClaim(
            "investor", "INV001", "country", "USA", "SRC002", observed
        ),
    ]

    evidence = [
        SourceEvidence(
            "SRC001", "https://one.example", verified_at=observed
        ),
        SourceEvidence(
            "SRC002", "https://two.example", verified_at=observed
        ),
    ]

    result = get_latest_confirmed_claims(claims, evidence)

    key = ("investor", "INV001", "country")
    assert result[key]["latest_confirmed"] is None
    assert len(result[key]["conflicts"]) == 2


def test_different_entity_types_are_not_returned_as_candidates():
    results = find_candidates(
        "Accel Growth Fund",
        ENTITIES,
        entity_type="investor",
    )

    assert all(
        item["entity_type"] == "investor"
        for item in results
    )


def test_invalid_entity_type():
    try:
        resolve_entity(
            "Accel",
            ENTITIES,
            ALIASES,
            entity_type="company",
        )
    except ValueError:
        pass
    else:
        assert False, "Invalid entity type should raise ValueError"


def test_alias_source_relationship():
    alias = EntityAlias(
        "ALIAS001",
        "investor",
        "INV001",
        "accel india",
    )

    evidence = SourceEvidence(
        "SRC001",
        "https://example.com/accel",
    )

    links = []

    assert add_alias_source(alias, evidence, links) is True
    assert len(links) == 1


def test_duplicate_alias_source_is_not_added():
    alias = EntityAlias(
        "ALIAS001",
        "investor",
        "INV001",
        "accel india",
    )

    evidence = SourceEvidence(
        "SRC001",
        "https://example.com/accel",
    )

    links = []

    add_alias_source(alias, evidence, links)

    assert add_alias_source(alias, evidence, links) is False
    assert len(links) == 1


def test_get_alias_sources():
    alias = EntityAlias(
        "ALIAS001",
        "investor",
        "INV001",
        "accel india",
    )

    evidence = SourceEvidence(
        "SRC001",
        "https://example.com/accel",
    )

    links = [
        EntityAliasSource("ALIAS001", "SRC001")
    ]

    result = get_alias_sources(
        alias.id,
        links,
        [evidence],
    )

    assert len(result) == 1
    assert result[0].id == "SRC001"


def test_alias_verification_status():
    alias = EntityAlias(
        "ALIAS001",
        "investor",
        "INV001",
        "accel india",
    )

    update_alias_verification(alias, "verified")
    assert alias.verification_status == "verified"

    update_alias_verification(alias, "disputed")
    assert alias.verification_status == "disputed"


def test_invalid_alias_verification_status():
    alias = EntityAlias(
        "ALIAS001",
        "investor",
        "INV001",
        "accel india",
    )

    try:
        update_alias_verification(alias, "invalid")
    except ValueError:
        pass
    else:
        assert False, "Invalid status should raise ValueError"


def test_latest_claim_status():
    observed = datetime(2026, 11, 25, tzinfo=timezone.utc)

    claim = EntityClaim(
        "investor", "INV001", "country",
        "India", "SRC001", observed,
    )

    evidence = [
        SourceEvidence(
            "SRC001",
            "https://example.com",
            verified_at=observed,
        )
    ]

    update_claim_statuses([claim], evidence)

    assert claim.status == "latest_confirmed"


def test_older_claim_becomes_superseded():
    old_time = datetime(2026, 11, 20, tzinfo=timezone.utc)
    new_time = datetime(2026, 11, 25, tzinfo=timezone.utc)

    old_claim = EntityClaim(
        "investor", "INV001", "country",
        "India", "SRC001", old_time,
    )

    new_claim = EntityClaim(
        "investor", "INV001", "country",
        "USA", "SRC002", new_time,
    )

    evidence = [
        SourceEvidence(
            "SRC001", "https://one.example",
            verified_at=old_time,
        ),
        SourceEvidence(
            "SRC002", "https://two.example",
            verified_at=new_time,
        ),
    ]

    update_claim_statuses(
        [old_claim, new_claim],
        evidence,
    )

    assert old_claim.status == "superseded"
    assert new_claim.status == "latest_confirmed"


def test_same_time_different_values_become_conflicting():
    observed = datetime(2026, 11, 25, tzinfo=timezone.utc)

    claims = [
        EntityClaim(
            "investor", "INV001", "country",
            "India", "SRC001", observed,
        ),
        EntityClaim(
            "investor", "INV001", "country",
            "USA", "SRC002", observed,
        ),
    ]

    evidence = [
        SourceEvidence(
            "SRC001", "https://one.example",
            verified_at=observed,
        ),
        SourceEvidence(
            "SRC002", "https://two.example",
            verified_at=observed,
        ),
    ]

    update_claim_statuses(claims, evidence)

    assert all(
        claim.status == "conflicting"
        for claim in claims
    )


def test_unverified_claim_remains_superseded():
    observed = datetime(2026, 11, 25, tzinfo=timezone.utc)

    claim = EntityClaim(
        "investor", "INV001", "country",
        "India", "SRC001", observed,
    )

    evidence = [
        SourceEvidence(
            "SRC001",
            "https://example.com",
            verified_at=None,
        )
    ]

    update_claim_statuses([claim], evidence)

    assert claim.status == "superseded"


def test_multiple_claims_with_same_value_can_be_latest():
    observed = datetime(2026, 11, 25, tzinfo=timezone.utc)

    claims = [
        EntityClaim(
            "investor", "INV001", "country",
            "India", "SRC001", observed,
        ),
        EntityClaim(
            "investor", "INV001", "country",
            "India", "SRC002", observed,
        ),
    ]

    evidence = [
        SourceEvidence(
            "SRC001", "https://one.example",
            verified_at=observed,
        ),
        SourceEvidence(
            "SRC002", "https://two.example",
            verified_at=observed,
        ),
    ]

    update_claim_statuses(claims, evidence)

    assert all(
        claim.status == "latest_confirmed"
        for claim in claims
    )
