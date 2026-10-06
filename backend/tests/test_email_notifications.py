from unittest.mock import patch
from app.services.email_service import EmailService
from app.services.notification_service import NotificationService, SENT_REMINDER_KEYS, NOTIFICATION_LOGS

def setup_function():
    # Clear logs and dedup set between test runs
    SENT_REMINDER_KEYS.clear()
    NOTIFICATION_LOGS.clear()

def test_registration_reminder_success():
    user = {"id": 101, "name": "Swetha", "email": "swetha@example.com"}
    hackathon = {"id": 501, "name": "AI Spark 2026", "deadline": "2026-10-15", "url": "https://hackathon.ai/spark"}

    with patch.object(EmailService, "send_registration_reminder", return_value=True) as mock_send:
        result = NotificationService.dispatch_registration_reminder(user, hackathon)
        assert mock_send.called
        assert result["status"] == "DELIVERED"
        assert result["type"] == "REGISTRATION_DEADLINE"
        assert len(NotificationService.get_notification_logs(user["id"])) == 1

def test_duplicate_reminder_prevention():
    user = {"id": 102, "name": "Swetha", "email": "swetha@example.com"}
    hackathon = {"id": 502, "name": "Web3 Surge", "deadline": "2026-11-01", "url": "https://hackathon.ai/web3"}

    with patch.object(EmailService, "send_registration_reminder", return_value=True):
        first_send = NotificationService.dispatch_registration_reminder(user, hackathon)
        assert first_send["status"] == "DELIVERED"

        # Second call must be deduplicated
        second_send = NotificationService.dispatch_registration_reminder(user, hackathon)
        assert second_send["status"] == "skipped"
        assert second_send["reason"] == "duplicate_suppressed"

def test_failed_delivery_does_not_crash():
    user = {"id": 103, "name": "Swetha", "email": "swetha@example.com"}
    hackathon = {"id": 503, "name": "Cloud Native Hack", "start_date": "2026-10-20", "url": "https://hackathon.ai/cloud"}

    # Mock delivery failure
    with patch.object(EmailService, "send_hackathon_reminder", return_value=False):
        result = NotificationService.dispatch_hackathon_reminder(user, hackathon)
        assert result["status"] == "FAILED"
        # Verify deduplication key is not locked on failure so a retry remains possible
        assert f"{user['id']}:{hackathon['id']}:UPCOMING_EVENT" not in SENT_REMINDER_KEYS