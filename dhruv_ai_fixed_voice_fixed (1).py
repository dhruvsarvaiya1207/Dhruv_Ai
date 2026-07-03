"""
Dhruv AI - A personal desktop assistant (English)
Run this from VS Code (Run > Run Without Debugging, or python dhruv_ai.py)

Works on Windows, macOS, and Linux (OS-specific commands like shutdown
are handled automatically below).
"""

import os
import re
import sys
import time
import socket
import random
import platform
import datetime
import webbrowser
import subprocess

try:
    import google.generativeai as genai
    GENAI_ENABLED = True
except (ImportError, ModuleNotFoundError):
    genai = None
    GENAI_ENABLED = False
from dotenv import load_dotenv
load_dotenv()

if GENAI_ENABLED:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel("gemini-2.5-flash")
    chat = model.start_chat(history=[])
else:
    model = None
    chat = None

# ---------------------------------------------------------------------
# Text-to-speech (offline, via pyttsx3).
# ---------------------------------------------------------------------
try:
    import pyttsx3
    TTS_ENABLED = True
except Exception as e:
    TTS_ENABLED = False
    print(f"(Voice output disabled -- pyttsx3 failed to load: {e})")
    print("(Fix: run 'pip install pyttsx3' -- on Linux also run 'sudo apt install espeak'.)")

TTS_WORKER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts_worker.py")

print(f"[TTS status] Voice output: {'ON' if TTS_ENABLED else 'OFF'}")

# ---------------------------------------------------------------------
# Optional: speech recognition (voice commands via microphone).
# Uses sounddevice (prebuilt binaries, no compiler needed) to record
# audio, then Google's speech-to-text via speech_recognition.
# ---------------------------------------------------------------------
try:
    import sounddevice as sd
    import numpy as np
    import speech_recognition as sr
    recognizer = sr.Recognizer()
    VOICE_IN_ENABLED = True
except Exception:
    VOICE_IN_ENABLED = False

# ---------------------------------------------------------------------
# Optional: screenshots + volume control.
# ---------------------------------------------------------------------
try:
    import pyautogui
    SCREEN_ENABLED = True
except Exception:
    SCREEN_ENABLED = False

# ---------------------------------------------------------------------
# Optional: battery / system info.
# ---------------------------------------------------------------------
try:
    import psutil
    SYSINFO_ENABLED = True
except Exception:
    SYSINFO_ENABLED = False

# ---------------------------------------------------------------------
# Optional: Wikipedia summaries.
# ---------------------------------------------------------------------
try:
    import wikipedia
    WIKI_ENABLED = True
except Exception:
    WIKI_ENABLED = False

SAMPLE_RATE = 16000
LISTEN_SECONDS = 5
NOTES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notes.txt")

JOKES = [
    "Why don't scientists trust atoms? Because they make up everything.",
    "Why did the computer go to the doctor? Because it had a virus.",
    "I would tell you a joke about pizza, but it's a bit cheesy.",
]


# ---------------------------------------------------------------------
# Speaking / listening
# ---------------------------------------------------------------------

def speak(text):
    text = str(text)
    print(f"Dhruv AI: {text}")

    try:
        if TTS_ENABLED:
            # Run TTS in a brand-new process every time. Reusing one
            # pyttsx3 engine (or even re-creating it) inside the same
            # long-running process eventually corrupts its internal
            # COM state on Windows and it goes silent with no error.
            # A fresh process each time sidesteps that completely.
            subprocess.run(
                [sys.executable, TTS_WORKER],
                input=text.encode("utf-8"),
                timeout=30,
            )
    except Exception as e:
        print("Speech Error:", e)


def listen() -> str:
    """Records a few seconds of audio and returns recognized speech as
    text. Empty string if nothing could be understood."""
    speak(f"Listening... (speak now, {LISTEN_SECONDS} seconds)")
    try:
        recording = sd.rec(int(LISTEN_SECONDS * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                            channels=1, dtype="int16")
        sd.wait()
    except Exception as e:
        speak(f"I couldn't access the microphone. Error: {e}")
        return ""

    audio_data = sr.AudioData(recording.tobytes(), SAMPLE_RATE, 2)

    try:
        text = recognizer.recognize_google(audio_data, language="en-IN")
        print(f"You said: {text}")
        return text
    except sr.UnknownValueError:
        speak("Sorry, I couldn't understand that.")
        return ""
    except sr.RequestError:
        speak("Speech recognition service is unavailable. Check your internet.")
        return ""


# ---------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------

def choose_mode() -> str:
    if not VOICE_IN_ENABLED:
        speak("Voice input isn't set up yet. See README.md to enable it. Continuing in text mode.")
        return "text"
    choice = input("Type 'v' for voice mode, or 't' for text mode (default: text): ").strip().lower()
    return "voice" if choice == "v" else "text"


def greet():
    hour = datetime.datetime.now().hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 17:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"
    speak(f"{greeting}! I am Dhruv AI, your personal assistant. Type or say 'help' to see what I can do.")


def show_help():
    print("""
Here are the things I can do for you:

  BROWSING
  open google / youtube / gmail / whatsapp / maps / instagram / facebook / spotify
  play <song/video name>          -> plays it on YouTube
  search <query>                  -> Google search
  wiki <topic>                    -> short Wikipedia summary
  open <any-website.com>

  PC CONTROL
  open notepad / calculator
  volume up / volume down / mute
  screenshot
  lock pc / restart pc / shutdown pc   (restart & shutdown ask for confirmation)
  battery / system info
  my ip

  UTILITY
  time / date
  calculate <expression>          e.g. "calculate 25 * 4"
  note <text>                     -> saves a timestamped note to notes.txt
  joke                            -> tells a joke
  how are you / who made you / thank you   -> a little small talk

  MODE
  switch to voice / switch to text
  help
  exit / quit / bye
""")


# ---------------------------------------------------------------------
# Task implementations
# ---------------------------------------------------------------------

WEBSITES = {
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "gmail": "https://mail.google.com",
    "whatsapp": "https://web.whatsapp.com",
    "maps": "https://maps.google.com",
    "instagram": "https://www.instagram.com",
    "facebook": "https://www.facebook.com",
    "spotify": "https://open.spotify.com",
}


def open_app(app_name: str):
    system = platform.system()
    app_name = app_name.lower()
    try:
        if "notepad" in app_name:
            if system == "Windows":
                os.system("notepad")
            elif system == "Darwin":
                os.system("open -a TextEdit")
            else:
                os.system("gedit || xdg-open .")
            speak("Opening Notepad for you.")
        elif "calculator" in app_name:
            if system == "Windows":
                os.system("calc")
            elif system == "Darwin":
                os.system("open -a Calculator")
            else:
                os.system("gnome-calculator || xcalc")
            speak("Opening Calculator for you.")
        else:
            speak(f"Sorry, I don't know how to open {app_name} yet.")
    except Exception as e:
        speak(f"I couldn't open that. Error: {e}")


def shutdown_pc():
    system = platform.system()
    speak("Shutting down the PC now. Goodbye!")
    time.sleep(1)
    if system == "Windows":
        os.system("shutdown /s /t 1")
    elif system == "Darwin":
        os.system("osascript -e 'tell app \"System Events\" to shut down'")
    else:
        os.system("shutdown now")


def restart_pc():
    system = platform.system()
    speak("Restarting the PC now.")
    time.sleep(1)
    if system == "Windows":
        os.system("shutdown /r /t 1")
    elif system == "Darwin":
        os.system("osascript -e 'tell app \"System Events\" to restart'")
    else:
        os.system("reboot")


def lock_pc():
    system = platform.system()
    speak("Locking your PC.")
    if system == "Windows":
        os.system("rundll32.exe user32.dll,LockWorkStation")
    elif system == "Darwin":
        os.system("pmset displaysleepnow")
    else:
        os.system("xdg-screensaver lock")


def ask_gemini(prompt):
    system_prompt = """
    You are Dhruv AI.

    Talk like a friendly human.

    Reply naturally, in English only.

    Keep replies short.

    Be polite and helpful.

    Do not use markdown, *, #, bullet points or emojis.
    """

    response = chat.send_message(system_prompt + "\n\nUser: " + prompt)

    text = response.text

    # Remove markdown characters
    text = re.sub(r'[*_`#]', '', text)

    return text.strip()


def take_screenshot():
    if not SCREEN_ENABLED:
        speak("Screenshot needs the 'pyautogui' package. See README.")
        return
    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
    os.makedirs(folder, exist_ok=True)
    filename = os.path.join(folder, f"screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
    pyautogui.screenshot().save(filename)
    speak(f"Screenshot saved to {filename}")


def change_volume(direction: str):
    if not SCREEN_ENABLED:
        speak("Volume control needs the 'pyautogui' package. See README.")
        return
    try:
        if direction == "up":
            for _ in range(5):
                pyautogui.press("volumeup")
            speak("Volume increased.")
        elif direction == "down":
            for _ in range(5):
                pyautogui.press("volumedown")
            speak("Volume decreased.")
        elif direction == "mute":
            pyautogui.press("volumemute")
            speak("Volume muted.")
    except Exception as e:
        speak(f"I couldn't change the volume. Error: {e}")


def report_battery():
    if not SYSINFO_ENABLED:
        speak("Battery info needs the 'psutil' package. See README.")
        return
    batt = psutil.sensors_battery()
    if batt is None:
        speak("I couldn't find battery info on this device.")
        return
    plugged = "charging" if batt.power_plugged else "not charging"
    speak(f"Battery is at {int(batt.percent)} percent, {plugged}.")


def report_system_info():
    if not SYSINFO_ENABLED:
        speak("System info needs the 'psutil' package. See README.")
        return
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent
    speak(f"CPU usage is {cpu} percent, and RAM usage is {ram} percent.")


def report_ip():
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        speak(f"Your local IP address is {ip}.")
    except Exception as e:
        speak(f"I couldn't find your IP. Error: {e}")


def tell_joke():
    speak(random.choice(JOKES))


def wiki_summary(topic: str):
    if not WIKI_ENABLED:
        speak("Wikipedia lookup needs the 'wikipedia' package. See README.")
        return
    try:
        summary = wikipedia.summary(topic, sentences=2)
        speak(summary)
    except Exception:
        speak(f"I couldn't find a clear Wikipedia summary for {topic}.")


def save_note(note_text: str):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(NOTES_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {note_text}\n")
    speak("Note saved.")


def calculate(expression: str):
    # Only allow digits, operators, decimals, parentheses, and spaces -- no eval of arbitrary code.
    if not re.fullmatch(r"[0-9\.\+\-\*\/\(\)\s%]+", expression):
        speak("I can only calculate simple math expressions.")
        return
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        speak(f"The answer is {result}.")
    except Exception:
        speak("I couldn't calculate that.")


# ---------------------------------------------------------------------
# Command processing
# ---------------------------------------------------------------------

def process_command(raw_command: str) -> bool:
    command = raw_command.strip().lower()

    if not command:
        return True

    if command in ("exit", "quit", "bye"):
        speak("Goodbye! Have a great day.")
        return False

    if command == "help":
        show_help()
        return True

    if "how are you" in command:
        speak("I'm doing great, thanks for asking! How can I help you?")
        return True
    if "your name" in command:
        speak("I'm Dhruv AI, your personal assistant.")
        return True
    if "who made you" in command or "who created you" in command:
        speak("I was built for you in Python, running right here in VS Code.")
        return True
    if "thank you" in command or "thanks" in command:
        speak("You're welcome!")
        return True

    for site, url in WEBSITES.items():
        if f"open {site}" in command:
            webbrowser.open(url)
            speak(f"Opening {site.capitalize()}.")
            return True

    if command.startswith("play "):
        query = command.split(" ", 1)[1].strip()
        url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
        webbrowser.open(url)
        speak(f"Playing {query} on YouTube.")
        return True

    if command.startswith("search "):
        query = command.split(" ", 1)[1].strip()
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        webbrowser.open(url)
        speak(f"Searching Google for {query}.")
        return True

    if command.startswith("wiki "):
        topic = command.replace("wiki ", "").strip()
        if topic:
            wiki_summary(topic)
        else:
            speak("What topic should I look up?")
        return True

    if command.startswith("open ") and "." in command:
        target = command.replace("open ", "", 1).strip()
        if not target.startswith("http"):
            target = "https://" + target
        webbrowser.open(target)
        speak(f"Opening {target}.")
        return True

    if "notepad" in command:
        open_app("notepad")
        return True
    if "calculator" in command:
        open_app("calculator")
        return True

    if command == "time":
        now = datetime.datetime.now().strftime("%I:%M %p")
        speak(f"The current time is {now}.")
        return True
    if command == "date":
        today = datetime.datetime.now().strftime("%A, %d %B %Y")
        speak(f"Today's date is {today}.")
        return True

    if "volume up" in command:
        change_volume("up")
        return True
    if "volume down" in command:
        change_volume("down")
        return True
    if "mute" in command:
        change_volume("mute")
        return True
    if "screenshot" in command:
        take_screenshot()
        return True
    if "battery" in command:
        report_battery()
        return True
    if "system info" in command:
        report_system_info()
        return True
    if "my ip" in command or "ip address" in command:
        report_ip()
        return True

    if "joke" in command:
        tell_joke()
        return True

    if command.startswith("note "):
        note_text = command.split(" ", 1)[1].strip()
        save_note(note_text)
        return True

    if command.startswith("calculate "):
        expr = command.split(" ", 1)[1].strip()
        calculate(expr)
        return True

    if "lock pc" in command or "lock the pc" in command:
        lock_pc()
        return True

    if "restart pc" in command or "restart the pc" in command:
        confirm = input("Are you sure you want to restart the PC? (yes/no): ").strip().lower()
        if confirm == "yes":
            restart_pc()
        else:
            speak("Restart cancelled.")
        return True

    if "shutdown pc" in command or "shutdown the pc" in command or "shut down" in command:
        confirm = input("Are you sure you want to shut down the PC? (yes/no): ").strip().lower()
        if confirm == "yes":
            shutdown_pc()
        else:
            speak("Shutdown cancelled.")
        return True

    try:
        reply = ask_gemini(command)
        speak(reply)
        return True
    except Exception as e:
        speak(f"Gemini Error: {e}")
        return True


# ---------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------

def main():
    greet()
    show_help()
    mode = choose_mode()
    if mode == "voice":
        speak("Voice mode activated. Say 'switch to text' any time to type instead.")

    running = True
    while running:
        if mode == "voice":
            command = listen()
            if not command:
                continue
            lc = command.strip().lower()
            if "switch to text" in lc:
                mode = "text"
                speak("Switched to text mode.")
                continue
        else:
            try:
                command = input("\nYou: ")
            except (EOFError, KeyboardInterrupt):
                print()
                speak("Goodbye!")
                break
            lc = command.strip().lower()
            if "switch to voice" in lc and VOICE_IN_ENABLED:
                mode = "voice"
                speak("Switched to voice mode.")
                continue

        running = process_command(command)


if __name__ == "__main__":
    main()
