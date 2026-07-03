"""
TTS worker -- runs as its OWN fresh process for every sentence.

Why this file exists: on Windows, calling pyttsx3.init() repeatedly
inside one long-running process eventually corrupts its internal COM
state, and it stops producing audio (silently -- no error). Running it
fresh, once per sentence, avoids that entirely, matching the behaviour
of the working standalone test script.

Not meant to be run directly by you -- dhruv_ai.py calls this
automatically. Text to speak is read from stdin as UTF-8.
"""

import sys
import pyttsx3


def main():
    text = sys.stdin.buffer.read().decode("utf-8", errors="ignore").strip()
    if not text:
        return
    engine = pyttsx3.init()
    voices = engine.getProperty("voices")
    if voices:
        engine.setProperty("voice", voices[0].id)
    engine.setProperty("rate", 175)
    engine.setProperty("volume", 1.0)
    engine.say(text)
    engine.runAndWait()
    engine.stop()


if __name__ == "__main__":
    main()
