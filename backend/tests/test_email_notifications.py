"""Real templates and persistence; SMTP is always mocked or forbidden."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
import smtplib
import ssl

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import Base
from app.models.core import Notification, Preference, SavedItem, User
from app.models.email_delivery import EmailDelivery
from app.models.hackathon import Hackathon
from app.models.organization import Organization
from app.services import email_service
from app.services.notification_service import claim, dispatch_due, enqueue_due

NOW = datetime(2026, 10, 13, 12, tzinfo=timezone.utc)


def config(**changes):
    return Settings(_env_file=None, DATABASE_URL="sqlite://", SECRET_KEY="x" * 32,
                    **{"EMAIL_MODE": "enabled", "SMTP_HOST": "smtp.example.com", **changes})


@pytest.fixture(autouse=True)
def no_real_smtp(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Real SMTP forbidden in tests")
    monkeypatch.setattr(smtplib, "SMTP", forbidden)
    monkeypatch.setattr(smtplib, "SMTP_SSL", forbidden)


@pytest.fixture
def smtp(monkeypatch):
    factory = MagicMock()
    server = factory.return_value.__enter__.return_value
    server.send_message.return_value = {}
    monkeypatch.setattr(smtplib, "SMTP", factory)
    monkeypatch.setattr(smtplib, "SMTP_SSL", factory)
    return factory, server


@pytest.fixture
def database(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'email.db').as_posix()}",
                           connect_args={"check_same_thread": False, "timeout": 10})
    @event.listens_for(engine, "connect")
    def foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(name="<Participant>", email="participant@example.com", password_hash="secret")
        org = Organization(name="Builders")
        db.add_all([user, org])
        db.flush()
        hackathon = Hackathon(title="Hack & Build", organization_id=org.id,
            url="https://example.com/event?a=1&b=2", start_date=(NOW + timedelta(hours=12)).replace(tzinfo=None),
            registration_deadline=(NOW + timedelta(hours=2)).replace(tzinfo=None))
        db.add(hackathon)
        db.flush()
        db.add_all([SavedItem(user_id=user.id, hackathon_id=hackathon.id),
                    Preference(user_id=user.id, key="email_reminders", value="true"),
                    Notification(user_id=user.id, title="Existing", message="Preserve")])
        db.commit()
        ids = user.id, hackathon.id
    yield engine, ids
    engine.dispose()


@pytest.mark.parametrize("kind", ["registration", "upcoming"])
def test_actual_template_escaping_and_plain_text(kind):
    message = email_service.render_message(config(), "participant@example.com", '<img src=x>',
        '<b>Hack & Build</b>', kind, "2026-10-13T14:00:00+00:00", "https://example.com/?a=1&b=2")
    html = message.get_body(preferencelist=("html",)).get_content()
    assert "&lt;img src=x&gt;" in html and "&lt;b&gt;Hack &amp; Build&lt;/b&gt;" in html
    assert '<img src=x>' not in html and 'a=1&amp;b=2' in html
    assert "https://example.com" in message.get_body(preferencelist=("plain",)).get_content()


@pytest.mark.parametrize("changes", [
    {"url": "javascript:alert(1)"}, {"url": "ftp://example.com"}, {"url": "//example.com"},
    {"url": "https://user:password@example.com"}, {"url": "https://example.com\nBcc:x"},
    {"title": "Hack\r\nBcc:evil@example.com"}, {"recipient": "a@example.com\nBcc:x"},
    {"recipient": "not-an-email"}, {"kind": "invalid"},
    {"url": "https://example.com:99999"},
])
def test_invalid_links_and_headers(changes):
    args = dict(recipient="a@example.com", name="A", title="Hack", kind="upcoming",
                event_at="tomorrow", url="https://example.com")
    with pytest.raises(ValueError):
        email_service.render_message(config(), **{**args, **changes})


@pytest.mark.parametrize("changes", [
    {"SMTP_PORT": 0}, {"SMTP_PORT": 65536}, {"SMTP_TIMEOUT": 0}, {"SMTP_TIMEOUT": 61},
    {"SMTP_TLS": "none"}, {"SMTP_HOST": ""}, {"SMTP_HOST": "host\n"},
    {"SMTP_USERNAME": "user"}, {"SMTP_PASSWORD": "private"}, {"EMAIL_FROM": "invalid"},
    {"EMAIL_FROM": "a@example.com\n"}, {"SMTP_HOST": "host name"},
])
def test_settings_validation(changes):
    with pytest.raises(ValidationError):
        config(**changes)


def test_settings_preserve_database_and_auth_contracts(monkeypatch):
    monkeypatch.delenv("DATABASE_URL")
    with pytest.raises(ValidationError):
        Settings(_env_file=None, SECRET_KEY="x" * 32)
    value = config(SMTP_USERNAME="user", SMTP_PASSWORD="private")
    assert value.ACCESS_TOKEN_EXPIRE_MINUTES == 30 and value.DEBUG is False
    assert "private" not in repr(value)


@pytest.mark.parametrize("mode", ["disabled", "dry-run"])
def test_disabled_dry_run_never_claim_or_send(database, mode):
    engine, _ = database
    with Session(engine) as db:
        assert enqueue_due(db, NOW) == 2
        assert dispatch_due(db, config(EMAIL_MODE=mode), NOW) == {mode: 0}
        assert all(row.status == "pending" and row.attempts == 0 for row in db.scalars(select(EmailDelivery)))
    message = email_service.render_message(config(), "a@example.com", "A", "Hack", "upcoming", "now", "http://example.com")
    assert email_service.send_message(config(EMAIL_MODE=mode), message) == mode


@pytest.mark.parametrize("tls,auth", [("starttls", True), ("implicit", True), ("starttls", False)])
def test_verified_tls_timeout_optional_auth(smtp, tls, auth):
    factory, server = smtp
    settings = config(SMTP_TLS=tls, SMTP_TIMEOUT=7,
                      SMTP_USERNAME="user" if auth else "", SMTP_PASSWORD="private" if auth else "")
    message = email_service.render_message(settings, "a@example.com", "A", "Hack", "upcoming", "now", "https://example.com")
    assert email_service.send_message(settings, message) == "accepted"
    assert factory.call_args.kwargs["timeout"] == 7
    context = factory.call_args.kwargs["context"] if tls == "implicit" else server.starttls.call_args.kwargs["context"]
    assert context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED
    assert server.login.called == auth
    if auth:
        server.login.assert_called_once_with("user", "private")
    if tls == "implicit":
        server.starttls.assert_not_called()


@pytest.mark.parametrize("failure,outcome", [
    (smtplib.SMTPRecipientsRefused({"a@example.com": (550, b"private")}), "refused"),
    (smtplib.SMTPDataError(451, b"private"), "transport_error"),
    (smtplib.SMTPServerDisconnected("private"), "unknown"), (TimeoutError("private"), "unknown"),
])
def test_transport_errors_are_safe(smtp, failure, outcome, caplog):
    _, server = smtp
    server.send_message.side_effect = failure
    message = email_service.render_message(config(), "a@example.com", "A", "Hack", "upcoming", "now", "https://example.com")
    assert email_service.send_message(config(), message) == outcome
    assert "private" not in caplog.text


def test_refused_recipient_result_is_not_success(smtp):
    _, server = smtp
    server.send_message.return_value = {"a@example.com": (550, b"No")}
    message = email_service.render_message(config(), "a@example.com", "A", "Hack", "upcoming", "now", "https://example.com")
    assert email_service.send_message(config(), message) == "refused"


def test_persistent_dedup_and_actual_models(database, smtp):
    engine, (user_id, event_id) = database
    with Session(engine) as db:
        assert enqueue_due(db, NOW) == 2
        assert dispatch_due(db, config(), NOW) == {"accepted": 2}
    with Session(engine) as db:
        assert enqueue_due(db, NOW) == 0
        assert dispatch_due(db, config(), NOW) == {}
        rows = db.scalars(select(EmailDelivery)).all()
        assert all(row.user_id == user_id and row.hackathon_id == event_id and row.accepted_at for row in rows)
        assert all(row.status == "accepted" for row in rows)
        assert db.scalar(select(func.count()).select_from(Notification)) == 1
    assert smtp[1].send_message.call_count == 2


def test_unique_constraint_and_atomic_concurrent_claim(database):
    engine, _ = database
    with Session(engine) as db:
        enqueue_due(db, NOW, 1)
        row = db.scalar(select(EmailDelivery))
        delivery_id = row.id
        db.add(EmailDelivery(user_id=row.user_id, hackathon_id=row.hackathon_id, kind=row.kind,
                            event_at=row.event_at, next_attempt_at=row.next_attempt_at))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    def compete(_):
        with Session(engine) as db:
            return claim(db, delivery_id, NOW.replace(tzinfo=None))
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(compete, range(2))) == [False, True]
    with Session(engine) as db:
        assert db.get(EmailDelivery, delivery_id).attempts == 1
        # Crashed claims are never automatically sent again.
        assert dispatch_due(db, config(), NOW + timedelta(minutes=30)) == {}
        assert db.get(EmailDelivery, delivery_id).status == "sending"


def test_retry_backoff_and_attempt_limit(database, smtp):
    engine, _ = database
    smtp[1].send_message.side_effect = smtplib.SMTPDataError(451, b"private")
    with Session(engine) as db:
        enqueue_due(db, NOW, 1)
        assert dispatch_due(db, config(), NOW) == {"transport_error": 1}
        assert dispatch_due(db, config(), NOW + timedelta(minutes=4)) == {}
        assert dispatch_due(db, config(), NOW + timedelta(minutes=5)) == {"transport_error": 1}
        assert dispatch_due(db, config(), NOW + timedelta(minutes=14)) == {}
        assert dispatch_due(db, config(), NOW + timedelta(minutes=15)) == {"transport_error": 1}
        row = db.scalar(select(EmailDelivery))
        assert row.status == "failed" and row.attempts == 3 and row.accepted_at is None
        assert dispatch_due(db, config(), NOW + timedelta(minutes=30)) == {}


def test_retry_can_succeed_and_unknown_is_not_retried(database, smtp):
    engine, _ = database
    with Session(engine) as db:
        enqueue_due(db, NOW, 1)
        smtp[1].send_message.return_value = {"participant@example.com": (450, b"No")}
        assert dispatch_due(db, config(), NOW) == {"refused": 1}
        smtp[1].send_message.return_value = {}
        assert dispatch_due(db, config(), NOW + timedelta(minutes=5)) == {"accepted": 1}
        enqueue_due(db, NOW, 1)
        smtp[1].send_message.side_effect = TimeoutError("private")
        assert dispatch_due(db, config(), NOW) == {"unknown": 1}
        assert dispatch_due(db, config(), NOW + timedelta(minutes=30)) == {}


@pytest.mark.parametrize("change", ["opt_out", "kind_opt_out", "unsaved", "inactive", "rescheduled", "expired"])
def test_preferences_ownership_rechecked_before_dispatch(database, change):
    engine, (user_id, event_id) = database
    with Session(engine) as db:
        enqueue_due(db, NOW, 1)
        if change == "opt_out":
            db.scalar(select(Preference)).value = "false"
        elif change == "kind_opt_out":
            db.add(Preference(user_id=user_id, key="email_registration_reminders", value="false"))
        elif change == "unsaved":
            db.delete(db.scalar(select(SavedItem)))
        elif change == "inactive":
            db.get(User, user_id).status = "inactive"
        elif change == "rescheduled":
            db.get(Hackathon, event_id).registration_deadline += timedelta(days=1)
        db.commit()
        when = NOW + timedelta(hours=2) if change == "expired" else NOW
        assert dispatch_due(db, config(), when) == {"cancelled": 1}
        assert db.scalar(select(EmailDelivery)).accepted_at is None


def test_opt_in_and_recipient_ownership_at_enqueue(database):
    engine, (user_id, _) = database
    with Session(engine) as db:
        db.delete(db.scalar(select(Preference)))
        other = User(name="Other", email="other@example.com", password_hash="secret")
        db.add(other)
        db.flush()
        db.add(Preference(user_id=other.id, key="email_reminders", value="true"))
        db.commit()
        assert enqueue_due(db, NOW) == 0  # cannot borrow someone else's saved item or consent


def test_timing_timezone_and_batches(database):
    engine, _ = database
    with Session(engine) as db:
        assert enqueue_due(db, NOW - timedelta(days=2)) == 0
        assert enqueue_due(db, NOW.astimezone(timezone(timedelta(hours=5, minutes=30))), 1) == 1
        assert enqueue_due(db, NOW, 1) == 1
        assert enqueue_due(db, NOW) == 0
        assert enqueue_due(db, NOW + timedelta(days=1)) == 0
        with pytest.raises(ValueError):
            enqueue_due(db, NOW.replace(tzinfo=None))
        with pytest.raises(ValueError):
            dispatch_due(db, config(), NOW, 1001)


def test_render_failure_terminal_safe_state(database, caplog):
    engine, (_, event_id) = database
    with Session(engine) as db:
        db.get(Hackathon, event_id).url = "javascript:private"
        db.commit()
        enqueue_due(db, NOW, 1)
        assert dispatch_due(db, config(), NOW) == {"render_error": 1}
        row = db.scalar(select(EmailDelivery))
        assert row.status == "failed" and row.error_code == "render_error" and row.accepted_at is None
        assert "private" not in caplog.text


def test_concurrent_enqueuers_and_dispatchers(database, smtp):
    engine, _ = database
    def enqueue(_):
        with Session(engine) as db:
            return enqueue_due(db, NOW)
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(enqueue, range(2))) == 2
    def dispatch(_):
        with Session(engine) as db:
            return dispatch_due(db, config(), NOW)
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(dispatch, range(2)))
    assert sum(outcome.get("accepted", 0) for outcome in outcomes) == 2
    assert smtp[1].send_message.call_count == 2


def test_missing_template_is_safe_failure(database, monkeypatch):
    from jinja2 import TemplateNotFound
    engine, _ = database
    def missing(*args):
        raise TemplateNotFound("private")
    monkeypatch.setattr(email_service.templates, "get_template", missing)
    with Session(engine) as db:
        enqueue_due(db, NOW, 1)
        assert dispatch_due(db, config(), NOW) == {"render_error": 1}
        assert db.scalar(select(EmailDelivery)).error_code == "render_error"


def test_tls_failure_does_not_authenticate_or_send(smtp):
    _, server = smtp
    server.starttls.side_effect = ssl.SSLCertVerificationError("private")
    message = email_service.render_message(config(), "a@example.com", "A", "Hack", "upcoming", "now", "https://example.com")
    assert email_service.send_message(config(SMTP_USERNAME="user", SMTP_PASSWORD="private"), message) == "transport_error"
    server.login.assert_not_called()
    server.send_message.assert_not_called()


def test_known_acceptance_preserved_when_quit_fails(smtp):
    factory, _ = smtp
    factory.return_value.__exit__.side_effect = smtplib.SMTPServerDisconnected("private")
    message = email_service.render_message(config(), "a@example.com", "A", "Hack", "upcoming", "now", "https://example.com")
    assert email_service.send_message(config(), message) == "accepted"


def test_generic_error_during_data_is_ambiguous(smtp):
    _, server = smtp
    server.send_message.side_effect = smtplib.SMTPException("private")
    message = email_service.render_message(config(), "a@example.com", "A", "Hack", "upcoming", "now", "https://example.com")
    assert email_service.send_message(config(), message) == "unknown"


def test_email_history_protects_event_deletion(database):
    from fastapi import HTTPException
    from app.services.event_service import delete_event
    engine, (_, event_id) = database
    with Session(engine) as db:
        enqueue_due(db, NOW)
        db.delete(db.scalar(select(SavedItem)))
        db.commit()
        with pytest.raises(HTTPException) as exc:
            delete_event(db, event_id)
        assert exc.value.status_code == 409
        assert db.get(Hackathon, event_id) is not None


def test_live_clock_prevents_sends_after_expiry_during_batch(database):
    engine, _ = database
    with Session(engine) as db:
        enqueue_due(db, NOW, 1)
        assert dispatch_due(db, config(), NOW, clock=lambda: NOW + timedelta(hours=3)) == {"cancelled": 1}


def test_null_kind_preference_does_not_enqueue(database):
    engine, (user_id, _) = database
    with Session(engine) as db:
        db.add(Preference(user_id=user_id, key="email_registration_reminders", value=None))
        db.commit()
        assert enqueue_due(db, NOW) == 1
        assert db.scalar(select(EmailDelivery)).kind == "upcoming"


def test_acceptance_followed_by_database_failure_remains_claimed(database, smtp):
    from sqlalchemy.exc import SQLAlchemyError
    engine, _ = database
    with Session(engine) as db:
        enqueue_due(db, NOW, 1)
    class FailingSession(Session):
        commits = 0
        def commit(self):
            self.commits += 1
            if self.commits == 2:
                self.flush()
                raise SQLAlchemyError("private")
            return super().commit()
    with FailingSession(engine) as db:
        with pytest.raises(SQLAlchemyError):
            dispatch_due(db, config(), NOW)
    with Session(engine) as db:
        row = db.scalar(select(EmailDelivery))
        assert row.status == "sending" and row.accepted_at is None and row.attempts == 1
        assert dispatch_due(db, config(), NOW + timedelta(minutes=30)) == {}
    assert smtp[1].send_message.call_count == 1


def test_worker_rejects_uncommitted_caller_work(database):
    engine, _ = database
    with Session(engine) as db:
        db.add(Organization(name="Caller"))
        with pytest.raises(ValueError):
            enqueue_due(db, NOW)
        with pytest.raises(ValueError):
            dispatch_due(db, config(), NOW)
        assert db.new  # worker never flushed or committed the caller's change


@pytest.mark.parametrize("mode", ["disabled", "dry-run"])
def test_cli_disabled_modes_are_noop(tmp_path, mode):
    import os
    from pathlib import Path
    import subprocess
    import sys
    database_path = tmp_path / "never-created.db"
    result = subprocess.run([sys.executable, "-m", "workers.email_reminders", "--batch-size", "5"],
        cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True,
        env={**os.environ, "DATABASE_URL": f"sqlite:///{database_path.as_posix()}",
             "SECRET_KEY": "test-only-worker-secret-123456789", "EMAIL_MODE": mode,
             "SMTP_HOST": "", "SMTP_USERNAME": "", "SMTP_PASSWORD": ""})
    assert result.returncode == 0, result.stderr
    import json
    assert json.loads(result.stdout) == {"mode": mode, "queued": 0, "accepted": 0}
    assert not database_path.exists()


def test_batch_failure_rolls_back_on_session_close(database, monkeypatch):
    engine, _ = database
    def fail_commit(self):
        raise RuntimeError("private")
    with monkeypatch.context() as patch:
        patch.setattr(Session, "commit", fail_commit)
        with Session(engine) as db:
            with pytest.raises(RuntimeError):
                enqueue_due(db, NOW)
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(EmailDelivery)) == 0


def test_migration_upgrade_matches_model_and_downgrade(tmp_path):
    import os
    from pathlib import Path
    import subprocess
    import sys
    from sqlalchemy import inspect
    backend = Path(__file__).resolve().parents[1]
    database_path = tmp_path / "migration.db"
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{database_path.as_posix()}",
           "SECRET_KEY": "test-only-migration-secret-123456789", "EMAIL_MODE": "disabled"}
    def migrate(revision):
        result = subprocess.run([sys.executable, "-m", "alembic", "upgrade" if revision == "head" else "downgrade", revision],
                                cwd=backend, env=env, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
    migrate("head")
    engine = create_engine(env["DATABASE_URL"])
    with engine.connect() as connection:
        inspector = inspect(connection)
        assert {col["name"] for col in inspector.get_columns("email_deliveries")} == set(EmailDelivery.__table__.columns.keys())
        assert inspector.get_unique_constraints("email_deliveries")[0]["column_names"] == ["user_id", "hackathon_id", "kind", "event_at"]
        assert {fk["referred_table"] for fk in inspector.get_foreign_keys("email_deliveries")} == {"users", "hackathons"}
        from alembic.autogenerate import compare_metadata
        from alembic.migration import MigrationContext
        differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)
        assert differences == []
    engine.dispose()
    migrate("b7c8d9e0f1a2")
    with engine.connect() as connection:
        assert "email_deliveries" not in inspect(connection).get_table_names()
        assert "notifications" in inspect(connection).get_table_names()
    engine.dispose()
