# Scraper Development Contract

All scraper modules in Hackathon Radar Finder must follow this common output structure.

## Required Output Format

Each scraper must return a list of dictionaries in this format:

{
  "title": "",
  "organization": "",
  "start_date": null,
  "end_date": null,
  "registration_deadline": null,
  "location": "",
  "mode": "",
  "prize": "",
  "description": "",
  "url": "",
  "source": "",
  "scraped_at": null
}

## Field Rules

title:
Name of the hackathon.

organization:
Company, college, community, or organization hosting the hackathon.

start_date:
ISO datetime when available.

end_date:
ISO datetime when available.

registration_deadline:
Registration deadline in ISO datetime format.

location:
City, state, country, or Online.

mode:
Use:
Online
Offline
Hybrid

prize:
Keep the original prize information as text.

description:
Short description of the hackathon.

url:
Original hackathon/event page.

source:
Name of the source platform.

scraped_at:
Datetime when scraping was performed.

## Missing Data

Do not invent missing information.

Use None for unavailable Python values.

## Required Scraper Function

Every scraper must expose:

def scrape():
    return []

## Rules

- Do not rename common fields.
- Do not commit API keys.
- Do not directly push data into production.
- Test output locally.
- Include error handling.
- Provide sample records where possible.
