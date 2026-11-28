
from dataclasses import dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Literal
from urllib.parse import urlparse
import re


EntityType = Literal["investor", "fund", "startup"]

HIGH_THRESHOLD = 80
UNCERTAIN_THRESHOLD = 65

GENERIC_WORDS = {
    "capital", "ventures", "partners", "investment",
    "investments", "fund", "group",
}

LEGAL_SUFFIXES = {
    "inc", "incorporated", "ltd", "limited", "pvt",
    "private", "llp", "llc", "plc",
}


# --------------------------------------------------
# 1. Data models
# --------------------------------------------------

@dataclass
class Entity:
    id: str
    name: str
    entity_type: EntityType
    website: str | None = None
    country: str | None = None


@dataclass
class Alias:
    entity_id: str
    alias_name: str
    source_url: str | None = None


@dataclass
class EntityAlias:
    id: str
    entity_type: EntityType
    entity_id: str
    alias_normalized: str
    verification_status: Literal[
        "unverified", "verified", "disputed"
    ] = "unverified"


@dataclass
class EntityAliasSource:
    alias_id: str
    source_evidence_id: str


@dataclass
class SourceEvidence:
    id: str
    source_url: str
    source_name: str | None = None
    verification_method: str | None = None
    verified_at: datetime | None = None
    observed_at: datetime | None = None
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass
class EntityClaim:
    entity_type: EntityType
    entity_id: str
    field_name: str
    value: str
    source_evidence_id: str
    observed_at: datetime
    status: Literal[
        "latest_confirmed", "conflicting", "superseded"
    ] = "superseded"


@dataclass
class RawEntity:
    name: str
    kind: EntityType
    source_url: str
    observed_at: datetime
    attributes: dict = field(default_factory=dict)


@dataclass
class ResolvedEntity:
    canonical_name: str
    kind: EntityType
    aliases: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)


def add_alias_source(
    alias: EntityAlias,
    source_evidence: SourceEvidence,
    alias_sources: list[EntityAliasSource],
) -> bool:
    """Link an alias to a source without creating duplicate links."""

    if not alias.alias_normalized.strip():
        raise ValueError("Alias cannot be empty")

    if any(
        link.alias_id == alias.id
        and link.source_evidence_id == source_evidence.id
        for link in alias_sources
    ):
        return False

    alias_sources.append(
        EntityAliasSource(
            alias_id=alias.id,
            source_evidence_id=source_evidence.id,
        )
    )

    return True


def get_alias_sources(
    alias_id: str,
    alias_sources: list[EntityAliasSource],
    evidence: list[SourceEvidence],
) -> list[SourceEvidence]:
    """Return all evidence records linked to an alias."""

    evidence_by_id = {
        item.id: item for item in evidence
    }

    return [
        evidence_by_id[link.source_evidence_id]
        for link in alias_sources
        if link.alias_id == alias_id
        and link.source_evidence_id in evidence_by_id
    ]


def update_alias_verification(
    alias: EntityAlias,
    status: Literal["unverified", "verified", "disputed"],
) -> None:
    """Update the verification status of an alias."""

    if status not in ("unverified", "verified", "disputed"):
        raise ValueError("Invalid alias verification status")

    alias.verification_status = status


# --------------------------------------------------
# 2. Name normalization
# --------------------------------------------------

def normalize_name(name: str) -> str:
    if not name:
        return ""

    name = name.casefold()
    name = re.sub(r"[^\w\s]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()

    tokens = name.split()

    while tokens and tokens[-1] in LEGAL_SUFFIXES:
        tokens.pop()

    if len(tokens) >= 2 and tokens[-2:] == ["private", "limited"]:
        tokens = tokens[:-2]

    return " ".join(tokens)


def meaningful_tokens(name: str) -> set[str]:
    tokens = set(normalize_name(name).split())
    return tokens - GENERIC_WORDS - LEGAL_SUFFIXES


# --------------------------------------------------
# 3. Similarity and corroborating evidence
# --------------------------------------------------

def compare_names(name1: str, name2: str) -> dict:
    first = normalize_name(name1)
    second = normalize_name(name2)

    if not first or not second:
        score = 0.0
    else:
        score = SequenceMatcher(None, first, second).ratio() * 100

    return {
        "ratio": round(score, 2),
        "token_sort": round(score, 2),
        "token_set": round(score, 2),
    }


def website_domain(website: str | None) -> str:
    if not website:
        return ""

    parsed = urlparse(
        website if "://" in website else "https://" + website
    )

    domain = (parsed.hostname or "").lower()

    if domain.startswith("www."):
        domain = domain[4:]

    return domain


def has_corroborating_evidence(
    entity: Entity,
    attributes: dict | None
) -> bool:
    if not attributes:
        return False

    incoming_website = website_domain(
        attributes.get("website")
    )
    existing_website = website_domain(entity.website)

    if (
        incoming_website
        and existing_website
        and incoming_website == existing_website
    ):
        return True

    incoming_country = attributes.get("country")
    existing_country = entity.country

    if incoming_country and existing_country:
        if normalize_name(incoming_country) == normalize_name(
            existing_country
        ):
            return True

    return False


# --------------------------------------------------
# 4. Candidate matching
# --------------------------------------------------

def find_candidates(
    new_name: str,
    entities: list[Entity],
    threshold: float = HIGH_THRESHOLD,
    entity_type: EntityType | None = None
) -> list[dict]:

    candidates = []
    normalized_name = normalize_name(new_name)

    if not normalized_name:
        return []

    for entity in entities:

        if entity_type and entity.entity_type != entity_type:
            continue

        entity_name = normalize_name(entity.name)

        if not entity_name:
            continue

        score = compare_names(new_name, entity.name)["ratio"]

        if score < threshold:
            continue

        candidates.append({
            "entity_id": entity.id,
            "entity_name": entity.name,
            "entity_type": entity.entity_type,
            "similarity_score": score,
            "exact_match": normalized_name == entity_name,
        })

    candidates.sort(
        key=lambda item: (
            item["exact_match"],
            item["similarity_score"]
        ),
        reverse=True
    )

    return candidates


def find_alias_matches(
    new_name: str,
    aliases: list[EntityAlias],
    entity_type: EntityType | None = None
) -> list[dict]:

    normalized_name = normalize_name(new_name)
    matches = []

    if not normalized_name:
        return []

    for alias in aliases:
        if entity_type and alias.entity_type != entity_type:
            continue

        if normalized_name == normalize_name(alias.alias_normalized):
            matches.append({
                "entity_id": alias.entity_id,
                "entity_type": alias.entity_type,
                "matched_alias": alias.alias_normalized,
                "match_type": "exact_alias",
                "verification_status": alias.verification_status,
            })

    return matches


# --------------------------------------------------
# 5. Entity resolution
# --------------------------------------------------

def resolve_entity(
    new_name: str,
    entities: list[Entity],
    aliases: list[EntityAlias],
    entity_type: EntityType = "investor",
    attributes: dict | None = None
) -> dict:

    if entity_type not in ("investor", "fund", "startup"):
        raise ValueError("Invalid entity type")

    if not normalize_name(new_name):
        return {"status": "no_match", "matches": []}

    typed_entities = [
        entity for entity in entities
        if entity.entity_type == entity_type
    ]

    entity_by_id = {
        entity.id: entity for entity in typed_entities
    }

    # Exact normalized entity name
    exact_matches = [
        entity for entity in typed_entities
        if normalize_name(entity.name) == normalize_name(new_name)
    ]

    if len(exact_matches) == 1:
        return {
            "status": "exact_name_match",
            "matches": [{
                "entity_id": exact_matches[0].id,
                "entity_name": exact_matches[0].name,
            }],
        }

    if len(exact_matches) > 1:
        return {
            "status": "ambiguous_match",
            "matches": [
                {
                    "entity_id": entity.id,
                    "entity_name": entity.name,
                }
                for entity in exact_matches
            ],
        }

    # Exact known alias
    alias_matches = find_alias_matches(
        new_name,
        aliases,
        entity_type=entity_type
    )

    valid_alias_matches = [
        match for match in alias_matches
        if match["entity_id"] in entity_by_id
    ]

    matched_ids = {
        match["entity_id"] for match in valid_alias_matches
    }

    if len(matched_ids) > 1:
        return {
            "status": "ambiguous_match",
            "matches": valid_alias_matches,
        }

    if len(matched_ids) == 1:
        statuses = {
            match["verification_status"]
            for match in valid_alias_matches
        }

        if "disputed" in statuses:
            return {
                "status": "needs_more_evidence",
                "matches": valid_alias_matches,
            }

        if "verified" in statuses:
            return {
                "status": "exact_alias_match",
                "matches": valid_alias_matches,
            }

        return {
            "status": "needs_more_evidence",
            "matches": valid_alias_matches,
        }

    # Fuzzy matching
    candidates = find_candidates(
        new_name,
        typed_entities,
        threshold=UNCERTAIN_THRESHOLD,
        entity_type=entity_type,
    )

    confirmed = []
    uncertain = []

    for candidate in candidates:
        entity = entity_by_id[candidate["entity_id"]]
        score = candidate["similarity_score"]

        if (
            score >= HIGH_THRESHOLD
            and has_corroborating_evidence(entity, attributes)
        ):
            confirmed.append(candidate)

        elif score >= UNCERTAIN_THRESHOLD:
            uncertain.append(candidate)

    if len(confirmed) == 1:
        return {
            "status": "high_confidence_match",
            "matches": confirmed,
        }

    if len(confirmed) > 1:
        return {
            "status": "ambiguous_match",
            "matches": confirmed,
        }

    if uncertain:
        return {
            "status": "needs_more_evidence",
            "matches": uncertain,
        }

    return {
        "status": "no_match",
        "matches": [],
    }


# --------------------------------------------------
# 6. Source and claim tracking
# --------------------------------------------------

def get_latest_confirmed_claims(
    claims: list[EntityClaim],
    evidence: list[SourceEvidence]
) -> dict:

    evidence_by_id = {
        item.id: item for item in evidence
    }

    claims_by_field = {}

    for claim in claims:
        source = evidence_by_id.get(claim.source_evidence_id)

        if source is None or source.verified_at is None:
            continue

        claims_by_field.setdefault(
            (claim.entity_type, claim.entity_id, claim.field_name),
            []
        ).append((claim, source))

    result = {}

    for key, items in claims_by_field.items():

        latest_time = max(
            claim.observed_at for claim, source in items
        )

        latest = [
            claim for claim, source in items
            if claim.observed_at == latest_time
        ]

        values = {claim.value for claim in latest}

        if len(values) > 1:
            result[key] = {
                "latest_confirmed": None,
                "conflicts": latest,
            }
        else:
            result[key] = {
                "latest_confirmed": latest[0],
                "conflicts": [],
            }

    return result


def update_claim_statuses(
    claims: list[EntityClaim],
    evidence: list[SourceEvidence],
) -> dict:
    """Update claim statuses using verified source evidence."""

    evidence_by_id = {
        item.id: item for item in evidence
    }

    groups = {}

    # Initially mark all claims as superseded.
    for claim in claims:
        claim.status = "superseded"

        key = (
            claim.entity_type,
            claim.entity_id,
            claim.field_name,
        )

        source = evidence_by_id.get(claim.source_evidence_id)

        if source is None or source.verified_at is None:
            continue

        groups.setdefault(key, []).append(claim)

    results = {}

    for key, group in groups.items():

        latest_time = max(
            claim.observed_at for claim in group
        )

        latest_claims = [
            claim for claim in group
            if claim.observed_at == latest_time
        ]

        latest_values = {
            claim.value for claim in latest_claims
        }

        if len(latest_values) > 1:
            for claim in latest_claims:
                claim.status = "conflicting"

            results[key] = {
                "status": "conflicting",
                "claims": latest_claims,
            }

        else:
            for claim in latest_claims:
                claim.status = "latest_confirmed"

            results[key] = {
                "status": "latest_confirmed",
                "claims": latest_claims,
            }

    return results
