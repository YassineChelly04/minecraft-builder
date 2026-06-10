"""Dev check: random variation salts must never break room reachability."""
from architecture.brief import intent_to_brief
from architecture.shell2 import build_shell2
from normalizer import normalize_commands
from repair import repair_commands
from voxel import VoxelGrid, flood_walkable

intent = {"size": {"x": 17, "y": 7, "z": 15}, "style": "medieval",
          "structure_type": "house", "palette_name": "medieval_castle",
          "room_program": ["living", "kitchen", "bedroom", "study"]}

bad = []
for salt in range(1, 31):
    brief = intent_to_brief(intent, {"x": 0, "y": 64, "z": 0}, prompt="t", variation=salt)
    raw, geom = build_shell2(brief)
    clean, _ = repair_commands(normalize_commands(raw))
    grid = VoxelGrid.from_commands(clean)
    d = geom.anchors["door_inside"]
    reached = flood_walkable(grid, (d.x, d.y, d.z))
    for zone in geom.zones:
        inner = zone.rect.inset(1)
        cells = {(x, zone.floor_y + 1, z) for x in range(inner.x1, inner.x2 + 1)
                 for z in range(inner.z1, inner.z2 + 1)
                 if not grid.is_solid(x, zone.floor_y + 1, z)}
        if not (cells & reached):
            bad.append((salt, zone.name, len(reached)))
print("unreachable cases:", bad if bad else "NONE (30/30 salts clean)")
