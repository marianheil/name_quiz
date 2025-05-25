from flask import Flask, jsonify, render_template, session, send_from_directory
from flask import request
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from flask import Response
import random
import json
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Needed for session support
metrics = PrometheusMetrics(app)

correct_guesses = Counter(
    "name_guess_correct_total", "Correct name guesses", ["session_id", "name"]
)

total_guesses = Counter(
    "name_guess_total", "Total name guesses", ["session_id", "name"]
)


with open("data.json") as f:
    data = json.load(f)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/question")
def get_question():
    if "recent_names" not in session:
        session["recent_names"] = []
    if "streak" not in session:
        session["streak"] = []

    candidates = [d for d in data if d["name"] not in session["recent_names"]]
    if not candidates:
        candidates = data

    correct = random.choice(candidates)
    session["recent_names"].append(correct["name"])
    session["recent_names"] = session["recent_names"][-20:]

    image_filename = random.choice(correct["images"])

    same_gender = [
        d["name"]
        for d in data
        if d["gender"] == correct["gender"] and d["name"] != correct["name"]
    ]
    wrong_choices = random.sample(same_gender, min(4, len(same_gender)))

    options = wrong_choices + [correct["name"]]
    random.shuffle(options)

    session["current_answer"] = correct["name"]
    session.modified = True

    return jsonify(
        {
            "image_url": f"/static/images_small/{image_filename}",
            "options": options,
            "streak": len(session["streak"]),
        }
    )


@app.route("/answer", methods=["POST"])
def answer():
    data = request.get_json()
    guess = data.get("guess")
    correct = session.get("current_answer")

    session_id = session.get("session_id")
    if not session_id:
        session_id = os.urandom(8).hex()
        session["session_id"] = session_id

    total_guesses.labels(session_id=session_id, name=correct).inc()
    if guess == correct:
        correct_guesses.labels(session_id=session_id, name=correct).inc()
        session.setdefault("streak", []).append(True)
        session.modified = True
        return jsonify({"correct": True, "streak": len(session["streak"])})
    else:
        session["streak"] = []
        return jsonify({"correct": False, "correct_name": correct, "streak": 0})


@app.route("/static/images_small/<filename>")
def serve_image(filename):
    # Make sure that images are properly served and the filename is checked
    return send_from_directory(
        os.path.join(app.root_path, "static/images_small"), filename
    )


@app.route("/metrics")
def metrics_endpoint():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    app.run(debug=True)
