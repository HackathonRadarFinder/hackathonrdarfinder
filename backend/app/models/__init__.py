from app.models.hackathon import Hackathon
from app.models.organization import Organization

from app.models.core import (
    User,
    Role,
    UserRole,
    Preference,
    Source,
    EventVersion,
    Prediction,
    SavedItem,
    Notification,
    Model,
    AuditLog,
)

from app.models.password_reset_otp import PasswordResetOTP
from app.models.revoked_token import RevokedToken
from app.models.email_delivery import EmailDelivery
from app.models.discovery import DiscoverySource, DiscoveryRun, DiscoveryLock, DiscoveryEvent, DiscoveryEvidence

from app.models.institution import Institution, Announcement
from app.models.investor import Fund, Investment, Investor, Startup

# v4.1 tables (INT-01). Imported so Base.metadata, Alembic and the drift checks see them.
from app.models.provenance import SourceEvidence, EntityAlias, EntityAliasSource, EntityClaim
from app.models.job import Employer, Job
from app.models.ingest_run import IngestRun
from app.models.contact import Contact
from app.models.alert import Alert
