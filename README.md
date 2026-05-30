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
 
## Optional: Automatic morning launch

You can install a macOS LaunchAgent to open the briefing each morning at 8:00 AM:

```bash
python3 setup_morning_briefing.py
launchctl load ~/Library/LaunchAgents/com.mehedi.jarvis.morningbriefing.plist
```

To stop the daily launch:

```bash
launchctl unload ~/Library/LaunchAgents/com.mehedi.jarvis.morningbriefing.plist
```

## Notes

- The dashboard is a plain HTML/CSS/JS file with no React or external build system.
- It uses free public feeds and local fetch logic.
- If the NewsAPI key is not available, the script falls back to RSS sources.

## Phase 2 — Local JARVIS Assistant

This project now includes a local assistant for Mehedi using Ollama.

### Requirements

- `ollama` installed and available on `PATH`
- A local Ollama model downloaded, for example `llama2`
- macOS `say` command for voice output
- Optional: `ffmpeg` and `whisper` for local voice transcription

### Run the assistant

```bash
python3 jarvis_assistant.py
```

### Run with voice output

```bash
python3 jarvis_assistant.py --speak
```

### Run with voice transcription (optional)

```bash
python3 jarvis_assistant.py --listen --speak
```

### Notes

- The assistant is local and uses Ollama only.
- If `ollama` is not installed, the script will print a helpful message.
- Voice transcription requires `ffmpeg` and the `whisper` CLI.
