# Hackathon Radar AI - Frontend

React + Vite frontend for the Hackathon Radar AI platform.

## Features

- **HackerEarth-style Discovery Platform**: Discover and filter global hackathons across AI, Cloud, Web3, and Hiring pipelines.
- **Motion Design & Animations**: Dynamic holographic radar sweep, live countdown clocks, interactive modal registrations, and toast notifications.
- **Predictive Intelligence**: AI cadence engine forecasting recurring hackathons ahead of official announcements.
- **Comprehensive Admin Dashboard**: Full 10-view administrative operations console for review queues, scrapers, duplicate deduplication, model calibration, and system health.

## Pages & Routes

- `/` — Home (HackerEarth-style discovery hero, challenge spotlight, trending hackathons, top sponsors)
- `/explore` — Explore Hackathons (Dual Grid/List views, instant category & tech stack filtering)
- `/event/:id` — Event Details (Live countdown timer, prize breakdown, phase timeline, rules)
- `/predictions` — AI Predictions (Recurrence probability gauges, detected evidence checklist, alert triggers)
- `/organizer/:name` — Organizer Profiles (Event timelines, cadence distribution charts)
- `/admin/*` — Admin Operations Console (10 specialized operational management modules)

## Getting Started

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

3. Build for production:
```bash
npm run build
```
