#!/usr/bin/env python3
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap

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
        self.listen_enabled = listen and self._can_listen()
        self.ollama_path = shutil.which('ollama')

    def _has_say(self):
        return shutil.which('say') is not None

    def _can_listen(self):
        return shutil.which('ffmpeg') is not None and shutil.which('whisper') is not None

    def _run_command(self, cmd, capture_output=True, timeout=120):
        try:
            process = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
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
                'ffmpeg',
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
                'whisper',
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

    def _check_requirements(self):
        if not self.ollama_path:
            print('ERROR: Ollama CLI not found. Install Ollama and ensure it is on PATH.')
            return False
        return True

    def _build_prompt(self, user_input):
        return textwrap.dedent(
            f"""
            {SYSTEM_PROMPT}

            Mehedi: {user_input}
            JARVIS:
            """
        )

    def _ask_ollama(self, prompt):
        cmd = ['ollama', 'query', self.model, prompt]
        code, out, err = self._run_command(cmd, capture_output=True, timeout=180)
        if code != 0:
            raise RuntimeError(err or 'Ollama query failed.')
        return out.strip()

    def run(self):
        if not self._check_requirements():
            return

        if self.speak_enabled:
            self._voice_output('JARVIS is online, Mehedi. Ready when you are.')

        print('JARVIS is online. Type your question or enter "hey mehedi" to wake me.')
        if self.listen_enabled:
            print('Voice input enabled. Use --listen to capture speech.')
        print('Type "exit" or "quit" to stop.')

        while True:
            try:
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
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    assistant = JarvisAssistant(args.model, args.speak, args.listen)
    assistant.run()


if __name__ == '__main__':
    main()
