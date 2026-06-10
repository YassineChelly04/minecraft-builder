import random
import re
import shutil
import tempfile
from pathlib import Path

from flask import Flask, render_template, request, jsonify, send_file
from dotenv import load_dotenv

load_dotenv()

import config
from clarify_agent import get_clarification
from pipeline import build_structure, PipelineError
from input_agent import CONTROL, execute_commands, execute_via_rcon, rcon_available

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


CITY_SCALE_RE = re.compile(r"\b(city|town|village|metropolis|settlement)\b", re.I)
FACTORY_SCALE_RE = re.compile(
    r"\b(factory|manufactur\w*|gigafactory|brewery|steelworks|assembly\s+plant|"
    r"production\s+plant)\b", re.I)


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400

    # City-scale prompts can't be served by the single-building pipeline (it
    # would return one clamped box) — hand them to the city engine instead.
    if CITY_SCALE_RE.search(prompt):
        return jsonify({"city_redirect": True})

    # Manufacturer prompts (a brand name like Ford/Airbus/Nestlé, or factory
    # words) get the full plant engine: real process flow, not one box.
    from factory.industries import match_industry
    if FACTORY_SCALE_RE.search(prompt) or match_industry(prompt):
        return jsonify({"factory_redirect": True})

    try:
        result = build_structure(
            prompt=prompt,
            origin=data.get("origin", {"x": 0, "y": 64, "z": 0}),
            answers=data.get("answers") or {},
            brief=data.get("brief"),
            refine=data.get("refine", False),
            mode=data.get("mode"),
            # random per-request salt unless the client pins one: same prompt,
            # different build every click (re-roll by building again)
            variation=int(data.get("variation") or random.randrange(1 << 30)),
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


@app.route("/generate_city", methods=["POST"])
def generate_city():
    from city_pipeline import build_city
    from city.plot import plan_to_svg

    data = request.get_json()
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400
    try:
        result = build_city(
            prompt=prompt,
            origin=data.get("origin", {"x": 0, "y": 64, "z": 0}),
            answers=data.get("answers") or {},
            mode=data.get("execute_mode", "datapack"),
            variation=int(data.get("variation") or random.randrange(1 << 30)),
        )
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": f"City build failed: {e}"}), 500

    svg = plan_to_svg(result.pop("plan"))
    return jsonify({
        "plan_summary": result["plan_summary"],
        "qa": result["qa"],
        "usage": result["usage"],
        "command_count": result["command_count"],
        "commands": result["commands"],
        "svg": svg,
    })


@app.route("/exec_info", methods=["GET"])
def exec_info():
    """Tell the UI which placement path /execute will take, for honest ETAs."""
    import os
    rate = int(os.environ.get("RCON_RATE", "150")) if rcon_available() else 12
    return jsonify({"method": "rcon" if rcon_available() else "keyboard", "rate": rate})


@app.route("/generate_factory", methods=["POST"])
def generate_factory():
    from factory_pipeline import build_factory
    from factory.plot import plan_to_svg

    data = request.get_json()
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400
    try:
        result = build_factory(
            prompt=prompt,
            origin=data.get("origin", {"x": 0, "y": 64, "z": 0}),
            answers=data.get("answers") or {},
            variation=int(data.get("variation") or random.randrange(1 << 30)),
        )
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": f"Factory build failed: {e}"}), 500

    svg = plan_to_svg(result.pop("plan"))
    return jsonify({
        "plan_summary": result["plan_summary"],
        "qa": result["qa"],
        "usage": result["usage"],
        "command_count": result["command_count"],
        "commands": result["commands"],
        "svg": svg,
    })


@app.route("/execute", methods=["POST"])
def execute():
    data = request.get_json()
    commands = data.get("commands", [])
    if not commands:
        return jsonify({"error": "No commands provided"}), 400
    # RCON (when configured) sends commands straight to the server — no window
    # focus, no typing — at >10x keyboard speed. Keyboard stays the fallback.
    method = "rcon" if rcon_available() else "keyboard"
    CONTROL.reset(len(commands))   # arms the Pause/Stop buttons for this run
    try:
        if method == "rcon":
            placed = execute_via_rcon(commands)
        else:
            placed = execute_commands(commands)
    except Exception as e:
        return jsonify({"error": f"Execution failed ({method}): {e}"}), 500
    stopped = CONTROL.status()["stopped"]
    return jsonify({"status": "stopped" if stopped else "done",
                    "count": placed, "method": method})


@app.route("/execute_control", methods=["POST"])
def execute_control():
    """Pause/resume/stop the placement currently running in /execute. Flask's
    threaded dev server handles this request on its own thread, so the buttons
    work while the placement loop holds the /execute request open."""
    action = (request.get_json() or {}).get("action")
    if action == "pause":
        CONTROL.pause()
    elif action == "resume":
        CONTROL.resume()
    elif action == "stop":
        CONTROL.stop()
    else:
        return jsonify({"error": "action must be pause, resume or stop"}), 400
    return jsonify(CONTROL.status())


@app.route("/execute_status", methods=["GET"])
def execute_status():
    return jsonify(CONTROL.status())


if __name__ == "__main__":
    app.run(debug=True, port=5000)
