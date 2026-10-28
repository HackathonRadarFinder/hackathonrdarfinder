"""Browser collection is disabled until every browser request can be governed."""
from ..models import BlockedError
from .base_collector import BaseCollector


class DynamicCollector(BaseCollector):
    collector_type = "dynamic"

    def fetch(self, source):
        raise BlockedError("Dynamic collection is disabled: browser requests cannot yet be governed")
