"""Persistent saved-event reminders. Invoke only from a dedicated worker."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import exists, select, update, func
from sqlalchemy.exc import IntegrityError

from app.models.core import Preference, SavedItem, User
from app.models.email_delivery import EmailDelivery
from app.models.hackathon import Hackathon
from app.services.email_service import render_message, send_message

KINDS = {"registration": "registration_deadline", "upcoming": "start_date"}
MAX_ATTEMPTS = 3


def utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Worker time must be timezone-aware")
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def opted_in(db, user_id, kind):
    # No existing preference meaning is changed. New email keys require explicit opt-in.
    values = dict(db.execute(select(Preference.key, Preference.value).where(
        Preference.user_id == user_id,
        Preference.key.in_(["email_reminders", f"email_{kind}_reminders"]),
    )).all())
    return values.get("email_reminders") == "true" and values.get(f"email_{kind}_reminders", "true") == "true"


def eligible(db, delivery):
    user = db.get(User, delivery.user_id)
    event = db.get(Hackathon, delivery.hackathon_id)
    saved = db.scalar(select(SavedItem.id).where(
        SavedItem.user_id == delivery.user_id, SavedItem.hackathon_id == delivery.hackathon_id,
    ))
    return (user is not None and user.status == "active" and event is not None and saved is not None
            and opted_in(db, user.id, delivery.kind)
            and "Date precision: day" not in (event.description or "")
            and getattr(event, KINDS[delivery.kind]) == delivery.event_at), user, event


def enqueue_due(db, now: datetime, batch_size: int = 100) -> int:
    """Queue at most batch_size upcoming reminders, within 24 hours of event time.

    Owns commits; use a dedicated clean session, never a request/caller transaction.
    """
    current = utc(now)
    if db.new or db.dirty or db.deleted:
        raise ValueError("Use a dedicated clean worker session")
    if not 1 <= batch_size <= 1000:
        raise ValueError("batch_size must be between 1 and 1000")
    # SQLite cannot safely upgrade simultaneous read transactions to writers.
    # Serialize enqueue transactions there; PostgreSQL uses the unique constraint.
    connection = db.connection()
    if connection.dialect.name == "sqlite" and not connection.connection.driver_connection.in_transaction:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
    count = 0
    for kind, field in KINDS.items():
        remaining = batch_size - count
        if not remaining:
            break
        column = getattr(Hackathon, field)
        already = exists(select(EmailDelivery.id).where(
            EmailDelivery.user_id == User.id, EmailDelivery.hackathon_id == Hackathon.id,
            EmailDelivery.kind == kind, EmailDelivery.event_at == column,
        ))
        consent = exists(select(Preference.id).where(
            Preference.user_id == User.id, Preference.key == "email_reminders", Preference.value == "true",
        ))
        opted_out = exists(select(Preference.id).where(
            Preference.user_id == User.id, Preference.key == f"email_{kind}_reminders",
            (Preference.value != "true") | Preference.value.is_(None),
        ))
        rows = db.execute(select(User.id, Hackathon.id, column).select_from(SavedItem)
            .join(User, User.id == SavedItem.user_id).join(Hackathon, Hackathon.id == SavedItem.hackathon_id)
            .where(User.status == "active", consent, ~opted_out, ~already,
                   ~func.coalesce(Hackathon.description, "").contains("Date precision: day"),
                   column > current, column <= current + timedelta(hours=24))
            .order_by(column, Hackathon.id, User.id).limit(remaining)).all()
        for user_id, event_id, event_at in rows:
            try:
                with db.begin_nested():
                    db.add(EmailDelivery(user_id=user_id, hackathon_id=event_id, kind=kind,
                                         event_at=event_at, next_attempt_at=current))
                    db.flush()
                count += 1
            except IntegrityError:
                # Another enqueuer won the unique reminder constraint.
                pass
    db.commit()
    return count


def claim(db, delivery_id, current):
    """Compare-and-swap claim; commit before SMTP, no lease that permits overlap."""
    result = db.execute(update(EmailDelivery).where(
        EmailDelivery.id == delivery_id, EmailDelivery.status.in_(["pending", "retry"]),
        EmailDelivery.next_attempt_at <= current, EmailDelivery.attempts < MAX_ATTEMPTS,
    ).values(status="sending", claimed_at=current, attempts=EmailDelivery.attempts + 1))
    db.commit()
    return result.rowcount == 1


def dispatch_due(db, config, now: datetime, batch_size: int = 100, *, clock=None):
    current = utc(now)
    if db.new or db.dirty or db.deleted:
        raise ValueError("Use a dedicated clean worker session")
    if not 1 <= batch_size <= 1000:
        raise ValueError("batch_size must be between 1 and 1000")
    if config.EMAIL_MODE != "enabled":
        return {config.EMAIL_MODE: 0}  # no claims, network, or success records
    ids = db.scalars(select(EmailDelivery.id).where(
        EmailDelivery.status.in_(["pending", "retry"]), EmailDelivery.next_attempt_at <= current,
        EmailDelivery.attempts < MAX_ATTEMPTS,
    ).order_by(EmailDelivery.next_attempt_at, EmailDelivery.id).limit(batch_size)).all()
    results = {}
    for delivery_id in ids:
        # The CLI supplies a live aware clock, so a slow batch cannot send a
        # reminder that expired since the initial due query.
        current = utc(clock()) if clock is not None else utc(now)
        if not claim(db, delivery_id, current):
            continue
        delivery = db.get(EmailDelivery, delivery_id, populate_existing=True)
        allowed, user, event = eligible(db, delivery)
        if not allowed or delivery.event_at <= current:
            outcome = "cancelled"
        else:
            try:
                message = render_message(config, user.email, user.name, event.title, delivery.kind,
                                         delivery.event_at.replace(tzinfo=timezone.utc).isoformat(), event.url)
            except Exception:
                # Do not log exception text, recipient data, template context or secrets.
                outcome = "render_error"
            else:
                outcome = send_message(config, message)
        delivery.error_code = None if outcome == "accepted" else outcome
        if outcome == "accepted":
            delivery.status = "accepted"
            delivery.accepted_at = current
        elif outcome in ("refused", "transport_error"):
            retry_at = current + timedelta(minutes=5 * 2 ** (delivery.attempts - 1))
            delivery.status = "retry" if delivery.attempts < MAX_ATTEMPTS and retry_at < delivery.event_at else "failed"
            delivery.next_attempt_at = retry_at
        else:
            delivery.status = "failed" if outcome == "render_error" else outcome
        db.commit()
        results[outcome] = results.get(outcome, 0) + 1
    return results
