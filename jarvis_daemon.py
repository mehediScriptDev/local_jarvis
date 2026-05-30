#!/usr/bin/env python3
"""
JARVIS Daemon — runs in background and listens for commands via named pipe.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import json
import re

DEFAULT_MODEL = os.environ.get('OLLAMA_MODEL', 'llama2')
SYSTEM_PROMPT = (
    "You are JARVIS, a sharp, no-nonsense developer assistant for Mehedi. "
    "Always address the user as Mehedi. Be direct, helpful, and technical. "
    "Help with development, Mac automation, terminal commands, code ideas, "
    "and productivity while staying local and private. "
    "If you cannot answer, say so clearly and do not fabricate details."
)
PIPE_PATH = os.path.expanduser('~/.jarvis_pipe')


class JarvisDaemon:
    def __init__(self, model, speak, log_file):
        self.model = model
        self.speak_enabled = speak and self._has_say()
        self.ollama_path = shutil.which('ollama')
        self.log_file = log_file

    def _has_say(self):
        return shutil.which('say') is not None

    def _run_command(self, cmd, capture_output=True, timeout=180):
        try:
            process = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                check=False,
                shell=isinstance(cmd, str),
            )
            return process.returncode, process.stdout.strip(), process.stderr.strip()
        except subprocess.TimeoutExpired:
            return 1, '', 'Command timed out.'

    def _log(self, msg):
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f'[{timestamp}] {msg}'
        if self.log_file:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_msg + '\n')
        else:
            print(log_msg, file=sys.stderr)

    def _voice_output(self, text):
        if not self.speak_enabled:
            return
        clean_text = text.replace('"', '')
        subprocess.run(['say', clean_text], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _build_prompt(self, user_input):
        return textwrap.dedent(
            f"""
            {SYSTEM_PROMPT}

            Mehedi: {user_input}
            JARVIS:
            """
        )

    def _run_osascript(self, script):
        code, out, err = self._run_command(['osascript', '-e', script])
        if code != 0:
            return False, err or out or 'AppleScript failed.'
        return True, out.strip()

    def _open_app(self, app_name):
        success, message = self._run_osascript(f'tell application "{app_name}" to activate')
        return f'Opened {app_name}.' if success else f'Failed to open {app_name}: {message}'

    def _close_app(self, app_name):
        success, message = self._run_osascript(f'tell application "{app_name}" to quit')
        return f'Closed {app_name}.' if success else f'Failed to close {app_name}: {message}'

    def _open_url(self, url):
        code, out, err = self._run_command(['open', url])
        if code != 0:
            return f'Failed to open URL: {err or out}'
        return f'Opened URL: {url}'

    def _run_terminal_command(self, command):
        code, out, err = self._run_command(command, capture_output=True, timeout=180)
        if code != 0:
            return f'Command failed ({code}): {err or out}'
        return out or 'Command completed successfully.'

    def _read_file(self, path):
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            return f'File not found: {path}'
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read(4096)
            preview = content[:3000]
            return f'Contents of {path}:\n{preview}'
        except Exception as exc:
            return f'Unable to read file {path}: {exc}'

    def _write_file(self, path, content, append=False):
        path = os.path.expanduser(path)
        try:
            directory = os.path.dirname(path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            mode = 'a' if append else 'w'
            with open(path, mode, encoding='utf-8') as f:
                f.write(content)
            verb = 'Appended to' if append else 'Wrote'
            return f'{verb} file {path}.'
        except Exception as exc:
            return f'Unable to write file {path}: {exc}'

    def _delete_file(self, path, confirm=False):
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            return f'File not found: {path}'
        if not confirm:
            return f'Deletion requires explicit confirmation. Use "delete file {path} confirm".'
        try:
            os.remove(path)
            return f'Deleted file {path}.'
        except Exception as exc:
            return f'Unable to delete file {path}: {exc}'

    def _local_action(self, user_input):
        normalized = user_input.strip()
        lower = normalized.lower()
        if lower.startswith(('open app ', 'launch app ')):
            app_name = normalized.split(' ', 2)[2]
            return self._open_app(app_name)
        if lower.startswith(('close app ', 'quit app ')):
            app_name = normalized.split(' ', 2)[2]
            return self._close_app(app_name)
        if lower.startswith(('open url ', 'browse url ', 'open website ')):
            url = normalized.split(' ', 2)[2]
            return self._open_url(url)
        if lower.startswith(('run command ', 'terminal command ', 'bash ', 'shell ')):
            command = normalized.split(' ', 2)[2] if ' ' in normalized else ''
            if not command:
                return 'Please provide a command to run.'
            return self._run_terminal_command(command)
        if lower.startswith(('read file ', 'show file ', 'view file ')):
            path = normalized.split(' ', 2)[2]
            return self._read_file(path)
        if lower.startswith(('write file ', 'save file ')):
            pattern = re.match(r'^(?:write|save) file\s+(.+?)\s+(?:with content|content)\s+(.+)$', normalized, re.I)
            if not pattern:
                return 'Use: write file <path> with content <text>.'
            path, content = pattern.group(1), pattern.group(2)
            return self._write_file(path, content, append=False)
        if lower.startswith(('append file ',)):
            pattern = re.match(r'^append file\s+(.+?)\s+(?:with content|content)\s+(.+)$', normalized, re.I)
            if not pattern:
                return 'Use: append file <path> with content <text>.'
            path, content = pattern.group(1), pattern.group(2)
            return self._write_file(path, content, append=True)
        if lower.startswith(('delete file ', 'remove file ')):
            pattern = re.match(r'^(?:delete|remove) file\s+(.+?)(?:\s+confirm)?$', normalized, re.I)
            if not pattern:
                return 'Use: delete file <path> confirm to delete a file.'
            path = pattern.group(1)
            confirm = normalized.endswith('confirm')
            return self._delete_file(path, confirm=confirm)
        return None

    def _ask_ollama(self, prompt):
        cmd = f'echo {repr(prompt)} | ollama run {self.model}'
        code, out, err = self._run_command(cmd, capture_output=True, timeout=180)
        if code != 0:
            if 'not found' in err.lower() or 'unknown model' in err.lower():
                raise RuntimeError(f'Model "{self.model}" not found. Download it with: ollama pull {self.model}')
            raise RuntimeError(err or 'Ollama run failed.')
        return out.strip()

    def _check_requirements(self):
        if not self.ollama_path:
            self._log('ERROR: Ollama CLI not found. Install Ollama and ensure it is on PATH.')
            return False
        return True

    def _setup_pipe(self):
        """Create or reset the named pipe."""
        if os.path.exists(PIPE_PATH):
            try:
                os.remove(PIPE_PATH)
            except Exception:
                pass
        os.mkfifo(PIPE_PATH, 0o666)
        self._log(f'Named pipe created: {PIPE_PATH}')

    def process_query(self, user_input):
        """Process a single query and return response."""
        if not user_input or not user_input.strip():
            return ''

        prompt = self._build_prompt(user_input)
        try:
            response = self._ask_ollama(prompt)
            self._log(f'Query: {user_input[:60]}... -> Response: {response[:60]}...')
            return response
        except RuntimeError as exc:
            error_msg = f'Error: {str(exc)}'
            self._log(error_msg)
            return error_msg

    def run_daemon(self):
        """Run daemon in background, listening on named pipe."""
        if not self._check_requirements():
            return

        self._log(f'JARVIS daemon started with model: {self.model}')
        self._voice_output(f'JARVIS daemon online with {self.model}')

        self._setup_pipe()

        try:
            while True:
                try:
                    with open(PIPE_PATH, 'r', encoding='utf-8') as pipe:
                        raw = pipe.readline().strip()
                        if not raw:
                            continue
                        response_pipe = None
                        try:
                            request = json.loads(raw)
                            user_input = request.get('query', '').strip()
                            response_pipe = request.get('response_pipe')
                        except json.JSONDecodeError:
                            user_input = raw
                        if not user_input:
                            continue
                        if user_input.lower() in ('exit', 'quit', 'stop'):
                            self._log('Daemon received stop command.')
                            break

                        local_response = self._local_action(user_input)
                        if local_response is not None:
                            self._log(f'Local action: {user_input}')
                            response = local_response
                        else:
                            response = self.process_query(user_input)
                        if self.speak_enabled and response:
                            self._voice_output(response)
                        if response_pipe:
                            try:
                                with open(response_pipe, 'w', encoding='utf-8') as out_pipe:
                                    out_pipe.write(response + '\n')
                            except Exception as exc:
                                self._log(f'Failed to write response pipe {response_pipe}: {exc}')

                except KeyboardInterrupt:
                    break
                except Exception as exc:
                    self._log(f'Daemon error: {exc}')

        finally:
            self._log('JARVIS daemon stopped.')
            try:
                os.remove(PIPE_PATH)
            except Exception:
                pass


def build_parser():
    parser = argparse.ArgumentParser(
        description='JARVIS daemon — runs in background.',
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument('--model', default=DEFAULT_MODEL, help='Ollama model (default: %(default)s)')
    parser.add_argument('--speak', action='store_true', help='Enable voice output.')
    parser.add_argument('--log', help='Log file path (default: stderr)')
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    daemon = JarvisDaemon(args.model, args.speak, args.log)
    daemon.run_daemon()


if __name__ == '__main__':
    main()

