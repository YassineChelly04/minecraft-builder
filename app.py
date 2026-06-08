import os
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

load_dotenv()

from orchestrator import get_intent
from planner import get_commands
from validator import validate_commands
from input_agent import execute_commands

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    prompt = (data.get("prompt") or "").strip()
    origin = data.get("origin", {"x": 0, "y": 64, "z": 0})

    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400

    try:
        intent = get_intent(prompt)
    except Exception as e:
        return jsonify({"error": f"Orchestrator failed: {e}"}), 500

    try:
        commands = get_commands(intent, origin)
    except Exception as e:
        return jsonify({"error": f"Planner failed: {e}"}), 500

    if not commands:
        return jsonify({"error": "Planner returned no commands"}), 500

    valid, errors = validate_commands(commands)

    return jsonify({
        "intent": intent,
        "commands": commands,
        "valid": valid,
        "errors": errors,
    })


@app.route("/execute", methods=["POST"])
def execute():
    data = request.get_json()
    commands = data.get("commands", [])

    if not commands:
        return jsonify({"error": "No commands provided"}), 400

    try:
        execute_commands(commands)
    except Exception as e:
        return jsonify({"error": f"Execution failed: {e}"}), 500

    return jsonify({"status": "done", "count": len(commands)})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
