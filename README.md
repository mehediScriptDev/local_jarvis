# JARVIS Morning Briefing Dashboard

Personal developer dashboard for Mehedi, built for Mac Mini M4.

## Phase 1

- Single-file dark theme dashboard
- World news, tech news, dev community feed
- GitHub trending repositories of the day
- Weather in Dhaka
- Motivational developer quote
- Date, time, and greeting

## Requirements

- Python 3
- macOS

Optional:
- `NEWSAPI_KEY` environment variable to use NewsAPI for world/tech news.

## Usage

From the `local_agent` folder:

```bash
python3 morning_briefing.py
```

This generates `morning_briefing.html` and opens it in your default browser.

## Notes

- The dashboard is a plain HTML/CSS/JS file with no React or external build system.
- It uses free public feeds and local fetch logic.
- If the NewsAPI key is not available, the script falls back to RSS sources.
