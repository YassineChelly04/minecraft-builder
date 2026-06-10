"""
gallery.py — writes a single datapack containing all 12 archetypes in a row, for
visual review in-game. Run: python gallery.py [out_dir]
"""
from __future__ import annotations

import sys
from pathlib import Path

from architecture.archetypes import ARCHETYPES, build_archetype
from architecture.brief import intent_to_brief
from execution.datapack import write_datapack
from normalizer import normalize_commands
from repair import repair_commands

GALLERY = [
    "factory_hall", "smokestack_plant", "warehouse", "rowhouse_strip",
    "office_block", "water_tower", "gasometer", "gantry_crane",
    "train_depot", "dock_finger", "civic_hall", "power_station",
]


def main(out_dir: str = "gallery_out") -> None:
    groups: dict[str, list[str]] = {}
    x = 0
    for i, name in enumerate(GALLERY):
        intent = {"size": {"x": 16, "y": 9, "z": 14}, "style": "industrial",
                  "structure_type": name, "palette_name": "brick_industrial",
                  "room_program": [], "features": []}
        brief = intent_to_brief(intent, {"x": x, "y": 64, "z": 0}, prompt=name)
        brief.archetype = name
        raw, _ = build_archetype(brief)
        clean, _ = repair_commands(normalize_commands(raw))
        groups[f"50_{i:02d}_{name}"] = clean
        x += 24  # space them out along +X

    man = write_datapack(groups, Path(out_dir), build_id="gallery")
    print(f"gallery datapack -> {man.root}")
    print(f"{man.total} commands across {len(GALLERY)} archetypes")
    print("install: copy into world/datapacks, /reload, /function aibuilder:build_all")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "gallery_out")
