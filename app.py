"""
Dhruv AI - Flask backend for the web UI.

Run:  python app.py
Then open:  http://127.0.0.1:5000  in your browser (Chrome/Edge
recommended -- they support the microphone Speech API used for voice
input).
"""

from flask import Flask, render_template, request, jsonify
import assistant_core

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/command", methods=["POST"])
def api_command():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    if not message:
        return jsonify({"reply": ""})
    reply = assistant_core.process_command(message)
    return jsonify({"reply": reply})


if __name__ == "__main__":
    print("Dhruv AI web server starting at http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)
