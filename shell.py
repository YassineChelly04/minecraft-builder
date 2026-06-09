"""
Deterministic structural shell — the guarantee that a build is always a *complete*
building, not 40% of one.

The LLM is unreliable at the one thing a house must get right: a watertight envelope
(floor + four walls + a real roof, with openings cut cleanly). So we generate the whole
envelope in Python from the intent. The result is always enclosed, always has a floor and
roof, always has a door and windows — regardless of model quality. The LLM agents then only
*decorate* (facade detail) and *furnish* (interior), which is where they add real value.

Coordinate convention (origin = min corner, y = floor level):
    floor_y  = y                      solid floor across the full footprint
    wall_lo  = y + 1                   first wall course
    wall_hi  = y + sy - 1              top wall course
    roof_y   = y + sy                  flat enclosing roof across the full footprint
    (a gabled roof is added decoratively above roof_y for pitched styles)
"""
from blocks import VALID_BLOCKS

_FLAT_ROOF_HINTS = ("modern", "warehouse", "industrial", "tower", "bunker", "flat", "shop", "store")


def _ok(block: str | None, fallback: str) -> str:
    """Use the requested material if it's a real block, else a safe default."""
    if not block:
        return fallback
    if not block.startswith("minecraft:"):
        block = "minecraft:" + block
    return block if block.split("[")[0] in VALID_BLOCKS else fallback


def _materials(intent: dict) -> dict:
    m = intent.get("materials", {}) or {}
    walls = _ok(m.get("walls"), "minecraft:stone_bricks")
    return {
        "walls": walls,
        "floor": _ok(m.get("floor"), "minecraft:oak_planks"),
        "roof":  _ok(m.get("roof"),  "minecraft:dark_oak_planks"),
        "foundation": "minecraft:cobbled_deepslate",
        "glass": "minecraft:glass_pane",
        "accent": _ok(m.get("accent"), walls),
    }


def _roof_is_flat(intent: dict) -> bool:
    tag = (str(intent.get("style", "")) + " " + str(intent.get("structure_type", ""))).lower()
    return any(h in tag for h in _FLAT_ROOF_HINTS)


def build_shell(intent: dict, origin: dict) -> list[str]:
    """Return a complete, watertight building envelope as /fill + /setblock commands."""
    x, y, z = origin["x"], origin["y"], origin["z"]
    sx = max(4, int(intent.get("size", {}).get("x", 10)))
    sy = max(4, int(intent.get("size", {}).get("y", 6)))
    sz = max(4, int(intent.get("size", {}).get("z", 10)))

    mat = _materials(intent)
    x1, z1 = x, z
    x2, z2 = x + sx - 1, z + sz - 1
    floor_y = y
    wall_lo, wall_hi = y + 1, y + sy - 1
    roof_y = y + sy

    cmds: list[str] = []

    # 1. Foundation — one course below the floor, extended a block on every side.
    cmds.append(f"/fill {x1-1} {floor_y-1} {z1-1} {x2+1} {floor_y-1} {z2+1} {mat['foundation']}")

    # 2. Floor — full footprint.
    cmds.append(f"/fill {x1} {floor_y} {z1} {x2} {floor_y} {z2} {mat['floor']}")

    # 3. Clear the interior volume to air (handles building over existing terrain).
    if x2 - 1 >= x1 + 1 and z2 - 1 >= z1 + 1 and wall_hi >= wall_lo:
        cmds.append(f"/fill {x1+1} {wall_lo} {z1+1} {x2-1} {wall_hi} {z2-1} minecraft:air")

    # 4. Four walls as 1-thick planes (no box+carve → no over-carving, no gaps).
    w = mat["walls"]
    cmds.append(f"/fill {x1} {wall_lo} {z1} {x2} {wall_hi} {z1} {w}")   # north
    cmds.append(f"/fill {x1} {wall_lo} {z2} {x2} {wall_hi} {z2} {w}")   # south
    cmds.append(f"/fill {x1} {wall_lo} {z1} {x1} {wall_hi} {z2} {w}")   # west
    cmds.append(f"/fill {x2} {wall_lo} {z1} {x2} {wall_hi} {z2} {w}")   # east

    # 5. Flat enclosing roof — guarantees the building is closed at the top.
    cmds.append(f"/fill {x1} {roof_y} {z1} {x2} {roof_y} {z2} {mat['roof']}")

    # 6. Pitched roof on top for non-flat styles (decorative, completeness already assured).
    if not _roof_is_flat(intent):
        cmds += _gable_roof(x1, z1, x2, z2, roof_y, mat)
    else:
        cmds += _parapet(x1, z1, x2, z2, roof_y, mat)

    # 7. Door opening (centred on the front/north wall) + a real door.
    cmds += _door(x1, x2, z1, wall_lo, mat)

    # 8. Windows along every wall.
    cmds += _windows(x1, z1, x2, z2, wall_lo, wall_hi, mat)

    return cmds


def _gable_roof(x1, z1, x2, z2, roof_y, mat) -> list[str]:
    """Ridge along X; triangular gable ends closed with wall material."""
    cmds = []
    sz = z2 - z1 + 1
    half = sz // 2
    roof = mat["roof"]
    wall = mat["walls"]
    for h in range(1, half + 1):
        y = roof_y + h
        zn, zf = z1 + h, z2 - h
        if zn > zf:
            break
        # two sloped courses (full width in X)
        cmds.append(f"/fill {x1} {y} {zn} {x2} {y} {zn} {roof}")
        cmds.append(f"/fill {x1} {y} {zf} {x2} {y} {zf} {roof}")
        # close the gable triangles at the X-ends so it's not see-through
        cmds.append(f"/fill {x1} {y} {zn} {x1} {y} {zf} {wall}")
        cmds.append(f"/fill {x2} {y} {zn} {x2} {y} {zf} {wall}")
    return cmds


def _parapet(x1, z1, x2, z2, roof_y, mat) -> list[str]:
    """A low wall ring around a flat roof — a clean modern silhouette."""
    p = roof_y + 1
    w = mat["accent"]
    return [
        f"/fill {x1} {p} {z1} {x2} {p} {z1} {w}",
        f"/fill {x1} {p} {z2} {x2} {p} {z2} {w}",
        f"/fill {x1} {p} {z1} {x1} {p} {z2} {w}",
        f"/fill {x2} {p} {z1} {x2} {p} {z2} {w}",
    ]


def _door(x1, x2, z1, wall_lo, mat) -> list[str]:
    cx = (x1 + x2) // 2
    return [
        # 2-wide × 3-tall opening
        f"/fill {cx} {wall_lo} {z1} {cx+1} {wall_lo+2} {z1} minecraft:air",
        # a real door in the left half of the opening
        f"/setblock {cx} {wall_lo} {z1} minecraft:oak_door",
    ]


def _windows(x1, z1, x2, z2, wall_lo, wall_hi, mat) -> list[str]:
    """Evenly spaced 1×2 window openings glazed with panes, on all four walls."""
    cmds = []
    glass = mat["glass"]
    wy1 = wall_lo + 1
    wy2 = min(wall_lo + 2, wall_hi - 1)
    if wy2 < wy1:
        return cmds

    cx = (x1 + x2) // 2
    # North & south walls: step along X, skip the door region near centre.
    for wx in range(x1 + 2, x2 - 1, 3):
        if abs(wx - cx) <= 1:
            continue
        for (zz) in (z1, z2):
            cmds.append(f"/fill {wx} {wy1} {zz} {wx} {wy2} {zz} minecraft:air")
            cmds.append(f"/fill {wx} {wy1} {zz} {wx} {wy2} {zz} {glass}")
    # West & east walls: step along Z.
    for wz in range(z1 + 2, z2 - 1, 3):
        for (xx) in (x1, x2):
            cmds.append(f"/fill {xx} {wy1} {wz} {xx} {wy2} {wz} minecraft:air")
            cmds.append(f"/fill {xx} {wy1} {wz} {xx} {wy2} {wz} {glass}")
    return cmds
