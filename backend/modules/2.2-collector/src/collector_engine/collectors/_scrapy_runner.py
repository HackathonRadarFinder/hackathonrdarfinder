"""Runs ONE Scrapy request in its own process and writes the outcome to a JSON file.

Executed as a subprocess by StaticCollector, because Twisted's reactor cannot be restarted
inside a long-lived process. Usage:  python _scrapy_runner.py '<json args>'
args: {url, out_path, user_agent, headers, delay, timeout}
"""
import json
import sys

import scrapy
from scrapy.crawler import CrawlerProcess


class SingleUrlSpider(scrapy.Spider):
    name = "single_url"

    def __init__(self, url, out_path, **kwargs):
        super().__init__(**kwargs)
        self.target_url = url
        self.out_path = out_path
        self.result = {"error": "no response received", "error_type": "NoResponse"}

    async def start(self):
        # handle_httpstatus_all: let us see 403/404/500 pages instead of Scrapy dropping them.
        yield scrapy.Request(
            self.target_url,
            callback=self.parse,
            errback=self.on_error,
            dont_filter=True,
            meta={"handle_httpstatus_all": True},
        )

    def parse(self, response):
        try:
            content = response.text
        except AttributeError:  # non-text body
            content = response.body.decode("utf-8", "replace")
        self.result = {
            "http_status": response.status,
            "final_url": response.url,
            "content_type": response.headers.get("Content-Type", b"").decode("latin-1"),
            "content": content,
        }

    def on_error(self, failure):
        self.result = {"error": repr(failure.value), "error_type": failure.type.__name__}

    def closed(self, reason):
        with open(self.out_path, "w", encoding="utf-8") as fh:
            json.dump(self.result, fh)


def main() -> None:
    args = json.loads(sys.argv[1])
    process = CrawlerProcess(
        settings={
            "USER_AGENT": args["user_agent"],
            "DEFAULT_REQUEST_HEADERS": args["headers"],
            "ROBOTSTXT_OBEY": True,  # second safety layer; the manager already checked
            "DOWNLOAD_DELAY": args["delay"],
            "DOWNLOAD_TIMEOUT": args["timeout"],
            "CONCURRENT_REQUESTS": 1,
            "RETRY_ENABLED": False,  # retries are handled by the framework, with logging
            "COOKIES_ENABLED": False,
            "TELNETCONSOLE_ENABLED": False,
            "LOG_LEVEL": "WARNING",
        }
    )
    process.crawl(SingleUrlSpider, url=args["url"], out_path=args["out_path"])
    process.start()


if __name__ == "__main__":
    main()
