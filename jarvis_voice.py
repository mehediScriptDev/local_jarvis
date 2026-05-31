#!/usr/bin/env python3
"""
JARVIS Voice Agent — Fully hands-free, voice-controlled assistant.
Auto-starts on Mac boot, listens continuously for wake word,
responds by voice, and performs tasks. Zero typing required.
"""
import argparse
import datetime
import logging
import os
import queue
import re
import subprocess
import sys
import time

import numpy as np
import requests
import sounddevice as sd
import whisper

# ── Configuration ─────────────────────────────────────────────────────────────

WAKE_WORDS = ['jarvis', 'hey jarvis', 'hey mehedi']
OLLAMA_URL = 'http://localhost:11434'
DEFAULT_MODEL = os.environ.get('OLLAMA_MODEL', 'llama2')
SAMPLE_RATE = 16000
CHANNELS = 1
BLOCK_DURATION = 0.5          # seconds per audio block
SILENCE_TIMEOUT = 1.5         # seconds of silence to end recording
MAX_RECORD_SECONDS = 15       # max seconds per utterance
CONVERSATION_TIMEOUT = 30     # stay in conversation mode this long
LOG_PATH = os.path.expanduser('~/Library/Logs/jarvis_voice.log')
TTS_VOICE = 'Samantha'        # macOS say voice

SYSTEM_PROMPT = (
    "You are JARVIS, Mehedi's personal voice assistant. "
    "You speak out loud. Keep answers to one or two short sentences. "
    "Be casual, warm, and direct like a friend. No lists, no formatting, no disclaimers."
)

# Common Whisper hallucinations on silence / ambient noise
HALLUCINATIONS = {
    'thank you', 'thanks for watching', 'subscribe', 'you', 'bye',
    'the end', 'thanks', 'thank you for watching', 'i\'ll see you next time',
    'see you next time', 'like and subscribe', '', ' ',
    'thanks for watching!', 'you\'re welcome', 'okay',
    'so', 'uh', 'um', 'hmm',
}


# ── Voice Agent ───────────────────────────────────────────────────────────────

class JarvisVoice:
    """Fully hands-free voice agent powered by Whisper + Ollama."""

    def __init__(self, model, whisper_size='base', log_path=None, voice=TTS_VOICE):
        self.model = model
        self.whisper_size = whisper_size
        self.log_path = log_path or LOG_PATH
        self.voice = voice
        self.whisper_model = None
        self.silence_threshold = 0.01
        self.is_speaking = False
        self.audio_queue = queue.Queue()
        self.conversation_mode = False
        self.conversation_ts = 0
        self._setup_logging()

    # ── Logging ───────────────────────────────────────────────────────────

    def _setup_logging(self):
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] %(levelname)s: %(message)s',
            handlers=[
                logging.FileHandler(self.log_path),
                logging.StreamHandler(sys.stderr),
            ],
        )
        self.log = logging.getLogger('jarvis')

    # ── Text-to-Speech ────────────────────────────────────────────────────

    def _speak(self, text):
        """Speak text via macOS say. Pauses mic listening during speech."""
        if not text:
            return
        self.is_speaking = True
        clean = re.sub(r'[*#`_\[\]()]', '', text)  # strip markdown chars
        clean = clean.replace('"', '').replace("'", "\\'")
        try:
            subprocess.run(
                ['say', '-v', self.voice, clean],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120,
            )
        except Exception as exc:
            self.log.error('TTS failed: %s', exc)
        finally:
            # Drain any audio captured while speaking (avoid hearing ourselves)
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                except queue.Empty:
                    break
            time.sleep(0.4)
            self.is_speaking = False

    # ── Speech-to-Text ────────────────────────────────────────────────────

    def _load_whisper(self):
        self.log.info('Loading Whisper "%s" model …', self.whisper_size)
        self.whisper_model = whisper.load_model(self.whisper_size)
        self.log.info('Whisper model loaded.')

    def _transcribe(self, audio):
        """Transcribe a numpy float32 audio array. Returns text or None."""
        if audio is None or len(audio) == 0:
            return None
        flat = audio.flatten().astype(np.float32)
        try:
            result = self.whisper_model.transcribe(flat, language='en', fp16=False)
            text = result.get('text', '').strip()
            if text and text.lower() not in HALLUCINATIONS:
                self.log.info('Heard: %s', text)
                return text
            return None
        except Exception as exc:
            self.log.error('Transcription error: %s', exc)
            return None

    # ── Microphone ────────────────────────────────────────────────────────

    def _audio_callback(self, indata, _frames, _time, _status):
        """Sounddevice callback — pushes audio blocks into the queue."""
        if not self.is_speaking:
            self.audio_queue.put(indata.copy())

    def _calibrate(self, duration=2.0):
        """Record ambient noise and set silence threshold."""
        self.log.info('Calibrating mic for %.1f s …', duration)
        audio = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                       channels=CHANNELS, dtype='float32')
        sd.wait()
        rms = float(np.sqrt(np.mean(audio ** 2)))
        self.silence_threshold = max(rms * 3.0, 0.005)
        self.log.info('Ambient RMS=%.6f  threshold=%.6f', rms, self.silence_threshold)

    @staticmethod
    def _rms(block):
        return float(np.sqrt(np.mean(block.astype(np.float32) ** 2)))

    def _record_utterance(self):
        """Wait for speech, record until silence, return numpy array or None."""
        blocks = []
        speech_started = False
        silence_start = None
        t0 = time.time()

        while True:
            if self.is_speaking:
                return None
            try:
                block = self.audio_queue.get(timeout=1.0)
            except queue.Empty:
                if not speech_started and (time.time() - t0) > 60:
                    return None  # idle timeout
                continue

            energy = self._rms(block)

            if not speech_started:
                if energy > self.silence_threshold:
                    speech_started = True
                    blocks.append(block)
                continue

            # Speech in progress
            blocks.append(block)
            if energy <= self.silence_threshold:
                if silence_start is None:
                    silence_start = time.time()
                elif (time.time() - silence_start) >= SILENCE_TIMEOUT:
                    break  # end of utterance
            else:
                silence_start = None

            if (time.time() - t0) > MAX_RECORD_SECONDS:
                break

        return np.concatenate(blocks, axis=0) if blocks else None

    # ── Wake-word detection ───────────────────────────────────────────────

    @staticmethod
    def _detect_wake(text):
        """Return (detected: bool, remaining_command: str)."""
        if not text:
            return False, ''
        lower = text.lower()
        for wake in WAKE_WORDS:
            pat = re.compile(r'\b' + re.escape(wake) + r'\b[,.\s!?]*', re.I)
            m = pat.search(lower)
            if m:
                rest = text[m.end():].strip()
                # Strip any leftover wake-word repetitions
                for w in WAKE_WORDS:
                    rest = re.sub(r'(?i)^\b' + re.escape(w) + r'\b[,.\s!?]*', '', rest).strip()
                return True, rest
        return False, ''

    # ── Local actions ─────────────────────────────────────────────────────

    def _osascript(self, script):
        try:
            r = subprocess.run(['osascript', '-e', script],
                               capture_output=True, text=True, timeout=10)
            return (r.returncode == 0), (r.stdout.strip() or r.stderr.strip())
        except Exception as e:
            return False, str(e)

    def _open_app(self, name):
        ok, msg = self._osascript(f'tell application "{name}" to activate')
        return f'Opened {name}.' if ok else f'Failed to open {name}: {msg}'

    def _close_app(self, name):
        ok, msg = self._osascript(f'tell application "{name}" to quit')
        return f'Closed {name}.' if ok else f'Failed to close {name}: {msg}'

    def _open_url(self, url):
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        try:
            subprocess.run(['open', url], capture_output=True, timeout=5)
            return f'Opened {url}.'
        except Exception as e:
            return f'Failed to open URL: {e}'

    def _run_cmd(self, cmd):
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True,
                               text=True, timeout=30)
            out = r.stdout.strip() or r.stderr.strip() or 'Done.'
            return f'Command result: {out[:300]}'
        except subprocess.TimeoutExpired:
            return 'Command timed out.'
        except Exception as e:
            return f'Command error: {e}'

    def _local_action(self, text):
        """Handle command locally if possible. Returns response or None."""
        lower = text.lower().strip()

        # open / launch
        m = re.match(r'^(?:open|launch|start)\s+(.+)$', text, re.I)
        if m:
            target = m.group(1).strip()
            if re.match(r'^[\w.-]+\.\w{2,}(/.*)?$', target):
                return self._open_url(target)
            return self._open_app(target)

        # close / quit
        m = re.match(r'^(?:close|quit|exit|kill)\s+(.+)$', text, re.I)
        if m:
            return self._close_app(m.group(1).strip())

        # go to URL
        m = re.match(r'^(?:go to|visit|browse|navigate to)\s+(.+)$', text, re.I)
        if m:
            return self._open_url(m.group(1).strip())

        # run shell command
        m = re.match(r'^(?:run command|run|execute)\s+(.+)$', text, re.I)
        if m:
            return self._run_cmd(m.group(1).strip())

        # time
        if re.search(r'what(?:\'s| is) the time|current time|tell.*time', lower):
            now = datetime.datetime.now()
            return f"It's {now.strftime('%I:%M %p')}, Mehedi."

        # date
        if re.search(r'what(?:\'s| is) the date|what day|today\'s date', lower):
            now = datetime.datetime.now()
            return f"Today is {now.strftime('%A, %B %d, %Y')}."

        return None

    # ── Ollama LLM ────────────────────────────────────────────────────────

    def _ask_ollama(self, prompt):
        """Query Ollama HTTP API."""
        try:
            r = requests.post(
                f'{OLLAMA_URL}/api/generate',
                json={
                    'model': self.model,
                    'prompt': prompt,
                    'system': SYSTEM_PROMPT,
                    'stream': False,
                    'options': {'temperature': 0.7, 'num_predict': 100},
                },
                timeout=60,
            )
            r.raise_for_status()
            return r.json().get('response', '').strip()
        except requests.ConnectionError:
            return 'Ollama is not running. Please start the Ollama app, Mehedi.'
        except requests.Timeout:
            return 'The request timed out. Try again.'
        except Exception as exc:
            self.log.error('Ollama error: %s', exc)
            return f'I got an error talking to Ollama: {exc}'

    def _check_ollama(self):
        try:
            r = requests.get(f'{OLLAMA_URL}/api/tags', timeout=5)
            r.raise_for_status()
            names = [m['name'] for m in r.json().get('models', [])]
            found = any(self.model in n for n in names)
            if not found:
                self.log.error('Model %s not found. Available: %s', self.model, names)
            return found
        except Exception as exc:
            self.log.error('Ollama unreachable: %s', exc)
            return False

    # ── Command processing ────────────────────────────────────────────────

    def _process(self, command):
        if not command:
            return None
        self.log.info('Processing: %s', command)
        local = self._local_action(command)
        if local is not None:
            return local
        return self._ask_ollama(command)

    # ── Diagnostics ───────────────────────────────────────────────────────

    def run_test(self):
        """Run quick diagnostics."""
        print('=== JARVIS Voice Diagnostics ===\n')

        print('[1/4] Whisper model …', end=' ', flush=True)
        try:
            self._load_whisper()
            print('OK')
        except Exception as e:
            print(f'FAIL: {e}'); return False

        print('[2/4] Microphone …', end=' ', flush=True)
        try:
            dev = sd.query_devices(kind='input')
            print(f"OK ({dev['name']})")
        except Exception as e:
            print(f'FAIL: {e}'); return False

        print(f'[3/4] Ollama ({self.model}) …', end=' ', flush=True)
        if self._check_ollama():
            print('OK')
        else:
            print('FAIL'); return False

        print('[4/4] TTS …', end=' ', flush=True)
        try:
            subprocess.run(['say', '-v', self.voice, 'JARVIS diagnostics passed.'],
                           timeout=10, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print('OK')
        except Exception as e:
            print(f'FAIL: {e}'); return False

        print('\n=== All tests passed. JARVIS is ready. ===')
        return True

    # ── Main loop ─────────────────────────────────────────────────────────

    def run(self):
        """Start the always-on voice agent."""
        self.log.info('JARVIS Voice Agent starting …')
        self._load_whisper()

        if not self._check_ollama():
            self.log.warning('Ollama not available at startup.')

        self._calibrate()

        block_size = int(BLOCK_DURATION * SAMPLE_RATE)
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                            dtype='float32', blocksize=block_size,
                            callback=self._audio_callback):

            self._speak('JARVIS online. Ready when you are, Mehedi.')
            self.log.info('Listening …')

            while True:
                try:
                    self._tick()
                except KeyboardInterrupt:
                    self.log.info('Shutdown requested.')
                    self._speak('Shutting down. Goodbye, Mehedi.')
                    break
                except Exception as exc:
                    self.log.error('Loop error: %s', exc, exc_info=True)
                    time.sleep(1)

    def _tick(self):
        """One listen → process → respond cycle. Always requires wake word."""
        audio = self._record_utterance()
        if audio is None:
            return

        text = self._transcribe(audio)
        if not text:
            return

        # ── Always require wake word ──────────────────────────────────
        found, command = self._detect_wake(text)
        if not found:
            return  # Ignore everything without "Jarvis"

        self.log.info('Wake word detected.')

        if not command:
            # Just said "Jarvis" with no command — ask what they need
            self._speak('Yes, Mehedi?')
            audio2 = self._record_utterance()
            if audio2 is None:
                return
            command = self._transcribe(audio2)
            if not command:
                return

        response = self._process(command)
        if response:
            self._speak(response)


# ── CLI ───────────────────────────────────────────────────────────────────────

def build_parser():
    p = argparse.ArgumentParser(description='JARVIS Voice Agent')
    p.add_argument('--model', default=DEFAULT_MODEL,
                   help='Ollama model (default: %(default)s)')
    p.add_argument('--whisper-model', default='base',
                   choices=['tiny', 'base', 'small', 'medium'],
                   help='Whisper model size (default: base)')
    p.add_argument('--voice', default=TTS_VOICE,
                   help='macOS TTS voice (default: %(default)s)')
    p.add_argument('--log', default=LOG_PATH,
                   help='Log file path')
    p.add_argument('--test', action='store_true',
                   help='Run diagnostics and exit')
    return p


def main():
    args = build_parser().parse_args()
    jarvis = JarvisVoice(
        model=args.model,
        whisper_size=args.whisper_model,
        log_path=args.log,
        voice=args.voice,
    )
    if args.test:
        sys.exit(0 if jarvis.run_test() else 1)
    jarvis.run()


if __name__ == '__main__':
    main()
