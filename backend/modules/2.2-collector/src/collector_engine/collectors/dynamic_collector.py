"""Dynamic collector: Playwright (headless Chromium) for JavaScript-rendered pages.

Only used for sources configured with "type": "dynamic". Playwright is imported lazily so
static-only runs never load a browser stack.

Optional per-source options (in sources.json):
  wait_for_selector   CSS selector that must appear before we read the page
  load_more_selector  CSS selector of a "Load more" button, clicked until it disappears
  max_load_more       cap on load-more clicks            (default 10)
  scroll_to_end       true -> scroll to the bottom repeatedly for infinite scroll
  max_scrolls         cap on scrolls                     (default 10)
  action_pause        seconds to wait after each click/scroll (default 1.0, polite pacing)
"""
from __future__ import annotations

from ..models import FetchResponse, Source, TemporaryFetchError
from .base_collector import BaseCollector, check_not_challenge, check_status


class DynamicCollector(BaseCollector):
    collector_type = "dynamic"

    def fetch(self, source: Source) -> FetchResponse:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeout
        from playwright.sync_api import sync_playwright

        opts = source.options
        timeout_ms = int(self.settings.request_timeout * 1000)
        pause_ms = int(float(opts.get("action_pause", 1.0)) * 1000)

        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(
                    headless=self.settings.headless,
                    slow_mo=0 if self.settings.headless else self.settings.slow_mo_ms,
                )
                try:
                    # Honest, identifiable User-Agent - we do not impersonate a normal browser.
                    headers = self.settings.request_headers()
                    context = browser.new_context(
                        user_agent=headers.pop("User-Agent"), extra_http_headers=headers
                    )
                    page = context.new_page()
                    page.set_default_timeout(timeout_ms)

                    response = page.goto(source.url, wait_until="domcontentloaded")
                    status = response.status if response else 0
                    check_status(status, source.url)

                    if opts.get("wait_for_selector"):
                        page.wait_for_selector(opts["wait_for_selector"])
                    else:
                        page.wait_for_load_state("networkidle")

                    if opts.get("load_more_selector"):
                        self._click_load_more(page, opts, pause_ms)
                    if opts.get("scroll_to_end"):
                        self._scroll_to_end(page, opts, pause_ms)

                    content = page.content()
                    final_url = page.url
                    content_type = (response.headers.get("content-type", "") if response else "")
                    if not self.settings.headless and self.settings.hold_seconds > 0:
                        page.wait_for_timeout(int(self.settings.hold_seconds * 1000))  # let a human look
                finally:
                    browser.close()
        except (PlaywrightTimeout, PlaywrightError) as exc:
            raise TemporaryFetchError(f"Playwright error for {source.url}: {exc}") from exc

        check_not_challenge(content, source.url)
        return FetchResponse(
            url=source.url,
            http_status=status,
            content=content,
            content_type=content_type,
            final_url=final_url,
        )

    @staticmethod
    def _click_load_more(page, opts: dict, pause_ms: int) -> None:
        selector = opts["load_more_selector"]
        for _ in range(int(opts.get("max_load_more", 10))):
            button = page.locator(selector).first
            if button.count() == 0 or not button.is_visible() or not button.is_enabled():
                break
            button.click()
            page.wait_for_timeout(pause_ms)

    @staticmethod
    def _scroll_to_end(page, opts: dict, pause_ms: int) -> None:
        for _ in range(int(opts.get("max_scrolls", 10))):
            before = page.evaluate("document.body.scrollHeight")
            # Mouse wheel (not window.scrollTo): headless Chromium only fires the page's
            # scroll events - which infinite-scroll sites listen to - for real wheel input.
            page.mouse.wheel(0, 100_000)
            page.wait_for_timeout(pause_ms)
            if page.evaluate("document.body.scrollHeight") == before:
                break  # no new content appeared
