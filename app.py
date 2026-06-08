import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

load_dotenv()

from orchestrator import get_intent
from exterior_agent import get_exterior_commands
from interior_agent import get_interior_commands
from normalizer import normalize_commands, merge_fills
from validator import validate_commands
from input_agent import execute_commands

app = Flask(__name__)


def _air_clear(intent: dict, origin: dict) -> list[str]:
    """One /fill that wipes the building interior clean before interior agent runs."""
    x, y, z = origin["x"], origin["y"], origin["z"]
    sx = intent.get("size", {}).get("x", 10)
    sy = intent.get("size", {}).get("y", 6)
    sz = intent.get("size", {}).get("z", 10)

    x1, z1 = x + 1, z + 1
    x2, z2 = x + sx - 2, z + sz - 2
    y1 = y + 1           # one above floor
    y2 = y + sy - 2      # one below roof

    if x2 < x1 or z2 < z1 or y2 < y1:
        return []
    return [f"/fill {x1} {y1} {z1} {x2} {y2} {z2} minecraft:air"]


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

    exterior_cmds, interior_cmds = [], []
    errors_by_agent = {}

    with ThreadPoolExecutor(max_workers=2) as pool:
        future_ext = pool.submit(get_exterior_commands, intent, origin)
        future_int = pool.submit(get_interior_commands, intent, origin)

        for future in as_completed([future_ext, future_int]):
            label = "Exterior" if future is future_ext else "Interior"
            try:
                result = future.result()
                if future is future_ext:
                    exterior_cmds = result
                else:
                    interior_cmds = result
            except Exception as e:
                errors_by_agent[label] = str(e)

    if errors_by_agent:
        msg = " | ".join(f"{k} agent failed: {v}" for k, v in errors_by_agent.items())
        return jsonify({"error": msg}), 500

    # Normalise → merge redundant fills → clear interior → validate
    exterior_cmds = merge_fills(normalize_commands(exterior_cmds))
    interior_cmds = merge_fills(normalize_commands(interior_cmds))

    air_clear = _air_clear(intent, origin)

    # Execution order: exterior shell → clear inside → interior furnishing
    all_commands = exterior_cmds + air_clear + interior_cmds

    if not all_commands:
        return jsonify({"error": "Both agents returned no commands"}), 500

    valid, errors = validate_commands(all_commands)

    return jsonify({
        "intent": intent,
        "exterior_commands": exterior_cmds,
        "interior_commands": air_clear + interior_cmds,
        "commands": all_commands,
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
