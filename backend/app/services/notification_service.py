import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

# In-memory stores for notifications and delivery logs (swappable with PostgreSQL once migrated)
NOTIFICATION_LOGS: List[Dict[str, Any]] = []
SENT_REMINDER_KEYS: set = set()

class NotificationService:
    @staticmethod
    def _generate_dedup_key(user_id: int, hackathon_id: int, reminder_type: str) -> str:
        return f"{user_id}:{hackathon_id}:{reminder_type}"

    @classmethod
    def dispatch_registration_reminder(
        cls, user: Dict[str, Any], hackathon: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Dispatches registration deadline reminder, preventing duplicate emails."""
        dedup_key = cls._generate_dedup_key(user["id"], hackathon["id"], "REGISTRATION_DEADLINE")
        if dedup_key in SENT_REMINDER_KEYS:
            logger.warning("Duplicate registration email suppressed for key: %s", dedup_key)
            return {"status": "skipped", "reason": "duplicate_suppressed"}

        success = EmailService.send_registration_reminder(
            to_email=user["email"],
            user_name=user.get("name", "Participant"),
            hackathon_name=hackathon["name"],
            deadline=hackathon["deadline"],
            hackathon_url=hackathon.get("url", "https://hackathonradar.ai")
        )

        log_entry = {
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "hackathon_id": hackathon["id"],
            "type": "REGISTRATION_DEADLINE",
            "channel": "EMAIL",
            "status": "DELIVERED" if success else "FAILED",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        NOTIFICATION_LOGS.append(log_entry)

        if success:
            SENT_REMINDER_KEYS.add(dedup_key)

        return log_entry

    @classmethod
    def dispatch_hackathon_reminder(
        cls, user: Dict[str, Any], hackathon: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Dispatches upcoming hackathon reminder, preventing duplicate emails."""
        dedup_key = cls._generate_dedup_key(user["id"], hackathon["id"], "UPCOMING_EVENT")
        if dedup_key in SENT_REMINDER_KEYS:
            logger.warning("Duplicate hackathon reminder suppressed for key: %s", dedup_key)
            return {"status": "skipped", "reason": "duplicate_suppressed"}

        success = EmailService.send_hackathon_reminder(
            to_email=user["email"],
            user_name=user.get("name", "Participant"),
            hackathon_name=hackathon["name"],
            start_date=hackathon["start_date"],
            hackathon_url=hackathon.get("url", "https://hackathonradar.ai")
        )

        log_entry = {
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "hackathon_id": hackathon["id"],
            "type": "UPCOMING_EVENT",
            "channel": "EMAIL",
            "status": "DELIVERED" if success else "FAILED",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        NOTIFICATION_LOGS.append(log_entry)

        if success:
            SENT_REMINDER_KEYS.add(dedup_key)

        return log_entry

    @staticmethod
    def get_notification_logs(user_id: int | None = None) -> List[Dict[str, Any]]:
        if user_id:
            return [log for log in NOTIFICATION_LOGS if log["user_id"] == user_id]
        return NOTIFICATION_LOGS