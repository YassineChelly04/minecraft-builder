"""
Room kits — per-room default furniture, must-include focal rules, and the op
menus served to the interior agent. `detail_level="kit"` furnishes straight from
`default` (seeded); the LLM path picks from `menu`.

Each op name maps to a placer in placers/furniture.py (Phase D). `must` entries
are focal points the deterministic critic guarantees if the agent omits them.
"""

ROOM_KITS: dict[str, dict] = {
    "living": {
        "must": ["fireplace_or_focal"],
        "default": ["sofa", "rug", "side_table", "bookshelf_wall"],
        "menu": ["sofa", "armchair", "coffee_table", "fireplace", "rug",
                 "bookshelf_wall", "plant", "chandelier", "side_table"],
    },
    "kitchen": {
        "must": ["kitchen_run"],
        "default": ["kitchen_run", "dining_set", "storage_wall"],
        "menu": ["kitchen_run", "dining_set", "storage_wall", "plant",
                 "side_table", "chandelier"],
    },
    "bedroom": {
        "must": ["bed"],
        "default": ["bed", "side_table", "rug", "storage_wall"],
        "menu": ["bed", "side_table", "rug", "bookshelf_wall", "plant",
                 "storage_wall", "desk", "armchair"],
    },
    "bedroom_1": {"must": ["bed"], "default": ["bed", "side_table", "rug"],
                  "menu": ["bed", "side_table", "rug", "desk", "storage_wall"]},
    "bedroom_2": {"must": ["bed"], "default": ["bed", "side_table", "rug"],
                  "menu": ["bed", "side_table", "rug", "desk", "storage_wall"]},
    "study": {
        "must": ["desk"],
        "default": ["desk", "bookshelf_wall", "armchair", "rug"],
        "menu": ["desk", "bookshelf_wall", "armchair", "rug", "plant",
                 "side_table", "chandelier"],
    },
    "workshop": {
        "must": ["storage_wall"],
        "default": ["storage_wall", "crafting_bench", "furnace_row"],
        "menu": ["storage_wall", "crafting_bench", "furnace_row", "shelf_row",
                 "anvil_station", "ceiling_beams"],
    },
    "storage": {
        "must": ["storage_wall"],
        "default": ["storage_wall", "barrel_stack"],
        "menu": ["storage_wall", "barrel_stack", "shelf_row", "ceiling_beams"],
    },
    "hallway": {
        "must": [],
        "default": ["rug", "plant"],
        "menu": ["rug", "plant", "side_table", "chandelier", "bookshelf_wall"],
    },
    "bathroom": {
        "must": ["bathtub"],
        "default": ["bathtub", "side_table"],
        "menu": ["bathtub", "side_table", "plant", "storage_wall"],
    },
}

# Default focal mapping when a "must" pseudo-op needs resolving to a real placer.
FOCAL_RESOLUTION = {
    "fireplace_or_focal": "fireplace",
}


def kit_for(room: str) -> dict:
    return ROOM_KITS.get(room, ROOM_KITS.get(room.split("_")[0], ROOM_KITS["living"]))
