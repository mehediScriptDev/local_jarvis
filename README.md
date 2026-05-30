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
- A local Ollama model downloaded (e.g., `llama2`)
- macOS `say` command for voice output
- Optional: `ffmpeg` and `whisper` for local voice transcription

### Download a model first

Before running the assistant, download a model:

```bash
ollama pull llama2
```

Or use another fast model suitable for M4 Mac:

```bash
ollama pull mistral
ollama pull neural-chat
```

Check available models:

```bash
ollama list
```

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

When using `--listen`, JARVIS will automatically record your question and transcribe it. You do not need to type anything when voice mode is active.

> Note: Voice transcription requires `ffmpeg` plus the Whisper transcription tool.
> If these are not installed, hotword and voice capture will not work.

Install dependencies on macOS with:

```bash
python3 -m pip install openai-whisper
# Install ffmpeg manually (Homebrew or direct download):
# brew install ffmpeg
```

### Run with hotword wake word

For the closest hands-free flow, use hotword mode:

```bash
python3 jarvis_assistant.py --hotword --listen --speak
```

JARVIS will listen for `Hey Mehedi` or `Hey Jarvis`, then record your command and answer it.

### Auto-start hotword listener

To have JARVIS start automatically and listen at login:

```bash
python3 setup_hotword_listener.py
launchctl load ~/Library/LaunchAgents/com.mehedi.jarvis.hotword.plist
```

Then you can speak to JARVIS without opening a terminal.

## Phase 3 — Background daemon

JARVIS can run as a background daemon on your Mac so it's always listening.

### Setup daemon

First, download an Ollama model:

```bash
ollama pull llama2
```

Then set up the daemon:

```bash
python3 setup_jarvis_daemon.py
launchctl load ~/Library/LaunchAgents/com.mehedi.jarvis.daemon.plist
```

### Query JARVIS from anywhere

Once the daemon is running, query it from any terminal:

```bash
python3 jarvis_cli.py "What's the weather?"
python3 jarvis_cli.py --interactive
```

### Local Mac control commands

JARVIS can now perform local Mac actions directly when you use the interactive assistant or daemon.

Examples:

```bash
python3 jarvis_assistant.py --speak
# then type:
open app "Visual Studio Code"
run command ls -la ~/projects
read file ~/projects/README.md
write file ~/projects/todo.txt with content Finish JARVIS automation
delete file ~/projects/old.txt confirm
```

For the daemon, ask via `jarvis_cli.py` and JARVIS will perform the action and speak the result.

### Check daemon status

View the daemon logs:

```bash
tail -f ~/Library/Logs/jarvis_daemon.log
```

Stop the daemon:

```bash
launchctl unload ~/Library/LaunchAgents/com.mehedi.jarvis.daemon.plist
```

### Notes

- The assistant is local and uses Ollama only.
- If `ollama` is not installed, the script will print a helpful message.
- Voice transcription requires `ffmpeg` and the `whisper` CLI.
- The daemon runs with voice output enabled by default.
