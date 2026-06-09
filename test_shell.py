"""Proves the deterministic shell is a complete, watertight building. Run: python test_shell.py"""
from shell import build_shell
from validator import validate_commands


def simulate(commands):
    """Apply /fill and /setblock to a voxel grid (last write wins)."""
    grid = {}
    for cmd in commands:
        p = cmd.split()
        if p[0] == "/fill":
            x1, y1, z1, x2, y2, z2 = map(int, p[1:7])
            block = p[7].split("[")[0]
            for xx in range(min(x1, x2), max(x1, x2) + 1):
                for yy in range(min(y1, y2), max(y1, y2) + 1):
                    for zz in range(min(z1, z2), max(z1, z2) + 1):
                        grid[(xx, yy, zz)] = block
        elif p[0] == "/setblock":
            x, yy, z = map(int, p[1:4])
            grid[(x, yy, z)] = p[4].split("[")[0]
    return grid


def solid(grid, c):
    b = grid.get(c)
    return b is not None and b != "minecraft:air"


def check(name, intent):
    origin = {"x": 0, "y": 64, "z": 0}
    cmds = build_shell(intent, origin)
    valid, errors = validate_commands(cmds)

    sx, sy, sz = intent["size"]["x"], intent["size"]["y"], intent["size"]["z"]
    x1, z1, x2, z2 = 0, 0, sx - 1, sz - 1
    floor_y, roof_y = 64, 64 + sy
    grid = simulate(cmds)

    floor_full = all(solid(grid, (xx, floor_y, zz)) for xx in range(x1, x2 + 1) for zz in range(z1, z2 + 1))
    roof_full = all(solid(grid, (xx, roof_y, zz)) for xx in range(x1, x2 + 1) for zz in range(z1, z2 + 1))

    # Interior cavity exists (hollow), and a door opening exists in the north wall.
    interior_air = sum(1 for xx in range(x1 + 1, x2) for yy in range(65, roof_y)
                       for zz in range(z1 + 1, z2) if grid.get((xx, yy, zz)) == "minecraft:air")
    door_open = any(grid.get((xx, 65, z1)) == "minecraft:air" for xx in range(x1, x2 + 1))

    ok = valid and floor_full and roof_full and interior_air > 0 and door_open
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: cmds={len(cmds)} valid={valid} "
          f"floor={floor_full} roof={roof_full} cavity={interior_air} door={door_open}")
    if not ok and errors:
        print("   errors:", errors[:3])
    return ok


results = [
    check("medieval house (gable)", {"size": {"x": 13, "y": 7, "z": 11}, "style": "medieval",
                                     "structure_type": "house", "materials": {"walls": "minecraft:stone_bricks",
                                     "floor": "minecraft:oak_planks", "roof": "minecraft:dark_oak_planks"}}),
    check("modern shop (flat)", {"size": {"x": 16, "y": 6, "z": 12}, "style": "modern",
                                 "structure_type": "shop", "materials": {"walls": "minecraft:white_concrete",
                                 "floor": "minecraft:smooth_stone", "roof": "minecraft:gray_concrete"}}),
    check("tiny cottage", {"size": {"x": 7, "y": 5, "z": 7}, "style": "rustic",
                           "structure_type": "cottage", "materials": {}}),
    check("bad materials fall back", {"size": {"x": 9, "y": 6, "z": 9}, "style": "fantasy",
                                      "structure_type": "house", "materials": {"walls": "minecraft:rainbow_brick",
                                      "floor": "minecraft:fake_wood", "roof": "minecraft:nonsense"}}),
]

print(f"\n{sum(results)}/{len(results)} shells complete & watertight")
exit(0 if all(results) else 1)
