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
                        user_input = pipe.readline().strip()
                        if not user_input:
                            continue
                        if user_input.lower() in ('exit', 'quit', 'stop'):
                            self._log('Daemon received stop command.')
                            break

                        response = self.process_query(user_input)
                        
                        if self.speak_enabled and response:
                            self._voice_output(response)

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

