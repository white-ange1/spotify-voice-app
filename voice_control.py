import speech_recognition as sr
import time
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Spotify API Tokens (import from main.py if already there)
ACCESS_TOKEN = os.getenv("SPOTIFY_ACCESS_TOKEN")

# Spotify API endpoints
SPOTIFY_API_BASE_URL = "https://api.spotify.com/v1/me/player"

# Function to send playback commands to Spotify
def send_spotify_command(command):
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    command_map = {
        "play": "/play",
        "pause": "/pause",
        "next": "/next",
        "previous": "/previous",
        "stop": "/pause",
    }

    if command in command_map:
        url = SPOTIFY_API_BASE_URL + command_map[command]
        method = "PUT" if command in ["play", "pause"] else "POST"
        
        response = requests.request(method, url, headers=headers)
        
        if response.status_code == 204:
            print(f"✅ Command '{command}' sent successfully!")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
    else:
        print(f"⚠️ Unknown command: {command}")

# Function to recognize voice and map to Spotify
def listen_and_control():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    print("🎤 Listening for Spotify commands...")

    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
        while True:
            try:
                print("🔊 Say a command (play, pause, next, previous, stop):")
                audio = recognizer.listen(source, timeout=10)

                command = recognizer.recognize_google(audio).lower()
                print(f"🗣️ You said: {command}")

                send_spotify_command(command)

                time.sleep(2)  # Small delay for smoother operation

            except sr.UnknownValueError:
                print("🤷 Couldn't understand the command.")
            except sr.RequestError:
                print("🚨 Error with the speech recognition service.")
            except KeyboardInterrupt:
                print("👋 Stopping voice control.")
                break

if __name__ == "__main__":
    listen_and_control()