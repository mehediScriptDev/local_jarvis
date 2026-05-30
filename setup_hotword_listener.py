#!/usr/bin/env python3
import os
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parent / 'jarvis_assistant.py'
PLIST_PATH = Path.home() / 'Library' / 'LaunchAgents' / 'com.mehedi.jarvis.hotword.plist'
LOG_PATH = Path.home() / 'Library' / 'Logs' / 'jarvis_hotword.log'

PLIST_CONTENT = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.mehedi.jarvis.hotword</string>
  <key>ProgramArguments</key>
  <array>
    <string>{sys.executable}</string>
    <string>{SCRIPT_PATH}</string>
    <string>--hotword</string>
    <string>--listen</string>
    <string>--speak</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>{LOG_PATH}</string>
  <key>StandardErrorPath</key>
  <string>{LOG_PATH}</string>
</dict>
</plist>
'''


def main():
    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PLIST_PATH, 'w', encoding='utf-8') as f:
        f.write(PLIST_CONTENT)
    print(f'LaunchAgent plist created: {PLIST_PATH}')
    print()
    print('Enable auto-starting hotword listener:')
    print(f'  launchctl load {PLIST_PATH}')
    print()
    print('Disable it:')
    print(f'  launchctl unload {PLIST_PATH}')
    print()
    print('View logs:')
    print(f'  tail -f {LOG_PATH}')


if __name__ == '__main__':
    main()
