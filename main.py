import os
import time
import base64
import requests
import json
import multiprocessing
from flask import Flask, request, redirect, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*", "allow_headers": ["Content-Type"], "methods": ["GET", "POST", "OPTIONS"]}})

# Spotify API Credentials
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")

# Token storage
access_token = None
refresh_token = None
token_expires_in = 0
token_acquired_at = 0

# Helper: Get current time
def current_time():
    return int(time.time())   

# Step 1: Authorization URL
def get_auth_url():
    scope = "user-read-playback-state user-modify-playback-state user-read-currently-playing"
    return (
        f"https://accounts.spotify.com/authorize"
        f"?client_id={CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={scope}"
        f"&show_dialog=true"
    )

# Step 2: Exchange Auth Code for Tokens
def get_tokens(auth_code):
    global access_token, refresh_token, token_expires_in, token_acquired_at
    url = "https://accounts.spotify.com/api/token"
    auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth_header}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
    }

    response = requests.post(url, headers=headers, data=data)
    token_info = response.json()

    # Store tokens and expiration time
    access_token = token_info.get("access_token")
    refresh_token = token_info.get("refresh_token")
    token_expires_in = token_info.get("expires_in")  # Default: 1 hour
    token_acquired_at = current_time()

    print("✅ Tokens received and stored!")
    return token_info

def save_tokens(access_token, refresh_token, expires_in):
    token_data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": int(time.time()) + expires_in 
    }    
    with open("tokens.json", "w") as f:
        json.dump(token_data, f)
    print("✅ Token saved successfully!")  

def load_tokens():
    try:
        with open("tokens.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

# Step 3: Refresh Access Token
def refresh_access_token():
    token_data = load_tokens()
    if not token_data or "refresh_token" not in token_data:
        print("❌ No valid refresh token found. Please log in again.")
        return None

    # Check if token needs refreshing (5 min buffer)
    if time.time() < token_data["expires_at"] - 300:
        return token_data["access_token"]

    print("🔄 Refreshing access token...")
    url = "https://accounts.spotify.com/api/token"
    auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    headers = {"Authorization": f"Basic {auth_header}"}
    data = {
        "grant_type": "refresh_token",
        "refresh_token": token_data["refresh_token"],
    }

    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        new_tokens = response.json()
        token_data["access_token"] = new_tokens["access_token"]
        token_data["expires_at"] = int(time.time()) + new_tokens["expires_in"] 

        # Save new refresh token if provided
        if "refresh_token" in new_tokens:
            token_data["refresh_token"] = new_tokens["refresh_token"]

        save_tokens(token_data["access_token"], token_data["refresh_token"], new_tokens["expires_in"])
        print("✅ Access token refreshed successfully!")
        return token_data["access_token"]
    else:
        print("❌ Failed to refresh token. Please log in again.")
        return None

# Helper: Send request to Spotify API
def spotify_request(command):
    global access_token
    access_token = refresh_access_token()

    if not access_token:
        return jsonify({"error": "Authorization required. Please log in at /"}), 401

    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Define proper HTTP methods for each command
    actions = {
        "play": {"method": "PUT", "endpoint": "play"},
        "pause": {"method": "PUT", "endpoint": "pause"},
        "next": {"method": "POST", "endpoint": "next"},
        "previous": {"method": "POST", "endpoint": "previous"},
    }

    if command not in actions:
        return jsonify({"error": "Invalid action."}), 400

    url = f"https://api.spotify.com/v1/me/player/{actions[command]}"
    response = requests.put(url, headers=headers)
    
    return jsonify({"status": "success", "command": command}) if response.status_code in (200,204) else f"❌ Error: {response.reason}"

# force refresh on first use
if not access_token:
    refresh_access_token()

# Flask Routes: Authorization Flow
@app.route("/")
def home():
    return redirect(get_auth_url())

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "Error: Missing code from Spotify", 400

    response = requests.post("https://accounts.spotify.com/api/token", {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    })

    if response.status_code == 200:
        token_info = response.json()
        save_tokens(token_info["access_token"], token_info["refresh_token"], token_info["expires_in"])
        return "✅ Spotify connected! <a href='/voice'>Go to Voice Control</a>"
        return redirect("http://localhost:8080/voice")
    return "Error: Failed to get token", 400

# Spotify Control Routes (play,pause,next,previous)
@app.route('/<command>', methods=['GET'])
def handle_command(command):
    return spotify_request(command)

# Voice Control Routes
@app.route('/voice')
def voice_interface():
    return render_template('index.html')

@app.route('/voice_control', methods=['OPTIONS', 'POST'])
def voice_control():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'success'})
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response

    try:
        command = request.json.get('command', '').lower()
        print(f"🎤 Received command: {command}")

        SPOTIFY_ACTIONS = {
            "play": "play",
            "pause": "pause",
            "next": "next",
            "previous": "previous"
        }

        # Map commands to Spotify API endpoints
        for keyword, action in SPOTIFY_ACTIONS.items():
            if keyword in command:
                try:
                    result = spotify_request(action)
                    # Check if result is a tuple (response, status_code)
                    if isinstance(result, tuple):
                        return result
                    return result
                except Exception as e:
                    print(f"Error executing command: {e}")
                    return jsonify({"status": "error", "message": str(e)}), 500
        
        # If no command was matched
        return jsonify({"status": "error", "message": "Unknown command"}), 400
    
    except Exception as e:
        print(f"Exception in voice_control: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Debug helper to log responses
@app.after_request
def log_response_info(response):
    print(f"Response Status: {response.status}")
    print(f"Response Headers: {response.headers}")
    # Only log JSON responses to avoid logging binary data
    if response.headers.get('Content-Type') == 'application/json':
        print(f"Response Body: {response.get_data(as_text=True)}")
    return response

if __name__ == "__main__":
    print("🚀 Starting Spotify Voice Control App")
    print("Visit: http://localhost:8080 to authenticate with Spotify")
    print("Visit: http://localhost:8080/voice for voice control interface")
    
    app.run(host="0.0.0.0", port=8080, debug=True)