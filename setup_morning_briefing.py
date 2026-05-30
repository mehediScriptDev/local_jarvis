#!/usr/bin/env python3
import os
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parent / 'morning_briefing.py'
PLIST_PATH = Path.home() / 'Library' / 'LaunchAgents' / 'com.mehedi.jarvis.morningbriefing.plist'

PLIST_CONTENT = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.mehedi.jarvis.morningbriefing</string>
  <key>ProgramArguments</key>
  <array>
    <string>{sys.executable}</string>
    <string>{SCRIPT_PATH}</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>8</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>StandardOutPath</key>
  <string>{Path.home() / "Library" / "Logs" / "jarvis_morning_briefing.log"}</string>
  <key>StandardErrorPath</key>
  <string>{Path.home() / "Library" / "Logs" / "jarvis_morning_briefing.err"}</string>
</dict>
</plist>
'''


def main():
    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PLIST_PATH, 'w', encoding='utf-8') as f:
        f.write(PLIST_CONTENT)
    print(f'LaunchAgent plist created at: {PLIST_PATH}')
    print('To enable it, run:')
    print(f'  launchctl load {PLIST_PATH}')
    print('To disable it later:')
    print(f'  launchctl unload {PLIST_PATH}')


if __name__ == '__main__':
    main()
