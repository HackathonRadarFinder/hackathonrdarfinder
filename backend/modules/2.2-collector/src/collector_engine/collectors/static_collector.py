"""Static HTML/JSON collection through the governed HTTP transport."""
from ..models import ComplianceError, FetchResponse
from .base_collector import BaseCollector, check_not_challenge, check_status


class StaticCollector(BaseCollector):
    collector_type = "static"

    def fetch(self, source):
        if not source.tos_allows_scraping:
            raise ComplianceError("Explicit scraping permission is required")
        transport, authorize = self.request_context(source)
        response = transport.request(source.url, headers=self.settings.request_headers(), authorize=authorize)
        check_status(response.status, response.url)
        content = response.text
        check_not_challenge(content, response.url)
        return FetchResponse(source.url, response.status, content,
                             response.headers.get("content-type", ""), response.url)
