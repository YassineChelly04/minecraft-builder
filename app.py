from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

load_dotenv()

from clarify_agent import get_clarification
from pipeline import build_structure, PipelineError
from input_agent import execute_commands

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/clarify", methods=["POST"])
def clarify():
    data = request.get_json()
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400
    try:
        return jsonify(get_clarification(prompt))
    except Exception as e:
        return jsonify({"error": f"Clarify agent failed: {e}"}), 500


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400

    try:
        result = build_structure(
            prompt=prompt,
            origin=data.get("origin", {"x": 0, "y": 64, "z": 0}),
            answers=data.get("answers") or {},
            brief=data.get("brief"),
            refine=data.get("refine", False),
        )
    except PipelineError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"Build failed: {e}"}), 500

    return jsonify(result)


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
