from flask import Flask, render_template, request, jsonify
import requests
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origin": "*", "allow_header": ["Content-Type"], "method": ["GET", "POST", "OPTIONS"]}})

# Spotify Flask app URL (assuming running on same machine)
SPOTIFY_API_URL = "http://localhost:8080"

# Basic routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/voice_control', methods=['OPTIONS', 'POST'])
def voice_control():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
    
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
            response = requests.get(f"{SPOTIFY_API_URL}/{action}")
            if response.status_code == 200:
                try:
                    return jsonify({"message": response.text})
                except:
                    return jsonify({"message": response.text})
            else:
                return jsonify({"status": "error", "message": f"Spotify API error: {response.status_code}"}), response.status_code

if __name__ =='__main__':
    app.run(host='0.0.0.0', port=5050, debug=True)