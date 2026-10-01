from datetime import datetime, timezone


def scrape():
    results = []

    # Add scraper logic here.

    # Every result should follow:
    #
    # {
    #     "title": "",
    #     "organization": "",
    #     "start_date": None,
    #     "end_date": None,
    #     "registration_deadline": None,
    #     "location": "",
    #     "mode": "",
    #     "prize": "",
    #     "description": "",
    #     "url": "",
    #     "source": "",
    #     "scraped_at": datetime.now(timezone.utc).isoformat()
    # }

    return results


if __name__ == "__main__":
    data = scrape()
    print(f"Records collected: {len(data)}")

    for item in data[:5]:
        print(item)
