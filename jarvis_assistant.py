#!/usr/bin/env python3
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import importlib.util

DEFAULT_MODEL = os.environ.get('OLLAMA_MODEL', 'llama2')
SYSTEM_PROMPT = (
    "You are JARVIS, a sharp, no-nonsense developer assistant for Mehedi. "
    "Always address the user as Mehedi. Be direct, helpful, and technical. "
    "Help with development, Mac automation, terminal commands, code ideas, "
    "and productivity while staying local and private. "
    "If you cannot answer, say so clearly and do not fabricate details."
)

VOICE_PROMPT = (
    "You are JARVIS, a sharp local assistant. Speak directly and motivate Mehedi. "
    "Do not be chatty unless Mehedi asks for detail."
)


class JarvisAssistant:
    def __init__(self, model, speak, listen):
        self.model = model
        self.speak_enabled = speak and self._has_say()
        self.whisper_command = self._find_whisper()
        self.ffmpeg_path = self._find_ffmpeg()
        self.listen_enabled = listen and self._can_listen()
        self.ollama_path = shutil.which('ollama')
        if listen and not self.listen_enabled:
            print('WARNING: --listen requested but ffmpeg and/or Whisper are not available. Install ffmpeg and Whisper to enable voice capture.')

    def _has_say(self):
        return shutil.which('say') is not None

    def _can_listen(self):
        return self.ffmpeg_path is not None and self.whisper_command is not None

    def _find_ffmpeg(self):
        ffmpeg_bin = shutil.which('ffmpeg')
        if ffmpeg_bin:
            return ffmpeg_bin

        spec = importlib.util.find_spec('imageio_ffmpeg')
        if spec is not None:
            import imageio_ffmpeg
            return imageio_ffmpeg.get_ffmpeg_exe()

        return None

    def _find_whisper(self):
        whisper_bin = shutil.which('whisper')
        if whisper_bin:
            return [whisper_bin]

        python3_bin = shutil.which('python3') or shutil.which('python')
        if python3_bin:
            code, out, err = self._run_command([python3_bin, '-m', 'whisper', '--help'], capture_output=True, timeout=10)
            if code == 0:
                return [python3_bin, '-m', 'whisper']

        return None

    def _run_command(self, cmd, capture_output=True, timeout=120):
        try:
            process = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                shell=isinstance(cmd, str),
                timeout=timeout,
                check=False,
            )
            return process.returncode, process.stdout.strip(), process.stderr.strip()
        except subprocess.TimeoutExpired:
            return 1, '', 'Command timed out.'

    def _voice_output(self, text):
        if not self.speak_enabled:
            return
        clean_text = text.replace('"', '')
        subprocess.run(['say', clean_text])

    def _transcribe_voice(self):
        if not self.listen_enabled:
            return None
        print('Listening for voice input. Speak after the beep...')
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = os.path.join(tmpdir, 'mehedi_input.wav')
            ffmpeg_cmd = [
                self.ffmpeg_path,
                '-y',
                '-f', 'avfoundation',
                '-i', ':0',
                '-t', '8',
                '-ar', '16000',
                '-ac', '1',
                audio_path,
            ]
            code, out, err = self._run_command(ffmpeg_cmd, capture_output=True, timeout=20)
            if code != 0:
                print('Voice capture failed:', err)
                return None
            whisper_cmd = [
                *self.whisper_command,
                audio_path,
                '--model', 'base',
                '--language', 'en',
                '--task', 'transcribe',
                '--output_format', 'txt',
                '--output_dir', tmpdir,
            ]
            code, out, err = self._run_command(whisper_cmd, capture_output=True, timeout=120)
            if code != 0:
                print('Transcription failed:', err)
                return None
            transcript_path = os.path.join(tmpdir, 'mehedi_input.txt')
            if not os.path.exists(transcript_path):
                return None
            with open(transcript_path, 'r', encoding='utf-8') as f:
                return f.read().strip()

    def _match_hotword(self, text):
        if not text:
            return False
        return bool(re.search(r'\b(hey\s+mehedi|hey\s+jarvis|jarvis)\b', text, re.I))

    def run_hotword_loop(self):
        if not self.listen_enabled:
            print('Hotword mode requires --listen and Whisper.')
            return

        print('Hotword listener active. Say "Hey Mehedi" to wake JARVIS.')
        while True:
            print('Listening for hotword...')
            phrase = self._transcribe_voice()
            if not phrase:
                continue
            print(f'Heard: {phrase}')
            if not self._match_hotword(phrase):
                continue

            ack = 'Yes Mehedi. Listening.'
            print(ack)
            if self.speak_enabled:
                self._voice_output(ack)
            print('Please speak your command.')
            command = self._transcribe_voice()
            if not command:
                print('No command detected. Waiting for hotword again.')
                continue
            print(f'Transcribed command: {command}')
            local_response = self._local_action(command)
            if local_response is not None:
                result = local_response
            else:
                prompt = self._build_prompt(command)
                try:
                    result = self._ask_ollama(prompt)
                except RuntimeError as exc:
                    result = f'Ollama error: {exc}'
            print('\nJARVIS:', result, '\n')
            if self.speak_enabled:
                self._voice_output(result)

    def _check_requirements(self):
        if not self.ollama_path:
            print('ERROR: Ollama CLI not found. Install Ollama and ensure it is on PATH.')
            return False
        return True

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

    def run(self):
        if not self._check_requirements():
            return

        if self.speak_enabled:
            self._voice_output('JARVIS is online, Mehedi. Ready when you are.')

        print('JARVIS is online. Type your question or enter "hey mehedi" to wake me.')
        if self.listen_enabled:
            print('Voice input enabled. Speak your question after the prompt.')
        print('Type "exit" or "quit" to stop.')

        while True:
            user_input = ''
            try:
                if self.listen_enabled:
                    print('Listening now... speak clearly.');
                    transcript = self._transcribe_voice()
                    if transcript:
                        print(f'Transcribed: {transcript}')
                        user_input = transcript.strip()
                    else:
                        print('Voice input failed. Please type your question instead.')
                        user_input = input('Mehedi > ').strip()
                else:
                    user_input = input('Mehedi > ').strip()
            except (EOFError, KeyboardInterrupt):
                print('\nGoodbye, Mehedi.')
                break

            if not user_input:
                continue
            if user_input.lower() in ('exit', 'quit'):
                print('Goodbye, Mehedi.')
                break

            if user_input.lower().startswith('hey mehedi') or user_input.lower().startswith('jarvis'):
                user_input = input('What do you need, Mehedi? ').strip()
                if not user_input:
                    continue

            if user_input.lower() in ('listen', 'voice') and self.listen_enabled:
                transcript = self._transcribe_voice()
                if transcript:
                    print(f'Transcribed: {transcript}')
                    user_input = transcript
                else:
                    print('Voice input failed. Try again or type your question.')
                    continue

            local_response = self._local_action(user_input)
            if local_response is not None:
                print('\nJARVIS:', local_response, '\n')
                if self.speak_enabled:
                    self._voice_output(local_response)
                continue

            prompt = self._build_prompt(user_input)
            try:
                response = self._ask_ollama(prompt)
            except RuntimeError as exc:
                print('Ollama error:', exc)
                continue

            print('\nJARVIS:', response, '\n')
            if self.speak_enabled:
                self._voice_output(response)


def build_parser():
    parser = argparse.ArgumentParser(
        description='Local JARVIS assistant for Mehedi using Ollama.',
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument('--model', default=DEFAULT_MODEL, help='Ollama model name (default: %(default)s)')
    parser.add_argument('--speak', action='store_true', help='Enable macOS voice output with say.')
    parser.add_argument('--listen', action='store_true', help='Enable local voice capture via ffmpeg + whisper if available.')
    parser.add_argument('--hotword', action='store_true', help='Enable hotword listening mode for "Hey Mehedi" wake-up.')
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    assistant = JarvisAssistant(args.model, args.speak, args.listen)
    if args.hotword:
        assistant.run_hotword_loop()
        return
    assistant.run()


if __name__ == '__main__':
    main()
