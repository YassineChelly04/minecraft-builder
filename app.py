import shutil
import tempfile
from pathlib import Path

from flask import Flask, render_template, request, jsonify, send_file
from dotenv import load_dotenv

load_dotenv()

import config
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
            mode=data.get("mode"),
        )
    except PipelineError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"Build failed: {e}"}), 500

    result.pop("geometry", None)  # BuildingGeometry isn't JSON-serialisable
    return jsonify(result)


@app.route("/export_datapack", methods=["POST"])
def export_datapack():
    """Zip a datapack for the given commands so it can be dropped into a world's
    datapacks/ folder (run /reload then /function aibuilder:build_all)."""
    from execution.datapack import datapack_from_build

    data = request.get_json()
    commands = data.get("commands", [])
    if not commands:
        return jsonify({"error": "No commands provided"}), 400
    origin = data.get("origin", {"x": 0, "y": 64, "z": 0})
    span = data.get("span", 64)
    bounds = (origin["x"], origin["z"], origin["x"] + span, origin["z"] + span)
    mc_version = data.get("target_mc_version", config.TARGET_MC_VERSION)

    tmp = Path(tempfile.mkdtemp(prefix="aibuilder_"))
    datapack_from_build(commands, tmp, bounds=bounds, mc_version=mc_version)
    archive = shutil.make_archive(str(tmp / "aibuilder_datapack"), "zip",
                                  root_dir=str(tmp / "aibuilder_datapack"))
    return send_file(archive, as_attachment=True, download_name="aibuilder_datapack.zip")


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
