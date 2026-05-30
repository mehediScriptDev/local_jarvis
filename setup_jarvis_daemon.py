#!/usr/bin/env python3
import os
import sys
from pathlib import Path

DAEMON_SCRIPT = Path(__file__).resolve().parent / 'jarvis_daemon.py'
PLIST_PATH = Path.home() / 'Library' / 'LaunchAgents' / 'com.mehedi.jarvis.daemon.plist'
LOG_PATH = Path.home() / 'Library' / 'Logs' / 'jarvis_daemon.log'

PLIST_CONTENT = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.mehedi.jarvis.daemon</string>
  <key>ProgramArguments</key>
  <array>
    <string>{sys.executable}</string>
    <string>{DAEMON_SCRIPT}</string>
    <string>--speak</string>
    <string>--log</string>
    <string>{LOG_PATH}</string>
  </array>
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
    print('To enable JARVIS daemon on startup:')
    print(f'  launchctl load {PLIST_PATH}')
    print()
    print('To disable it:')
    print(f'  launchctl unload {PLIST_PATH}')
    print()
    print('To view logs:')
    print(f'  tail -f {LOG_PATH}')


if __name__ == '__main__':
    main()
