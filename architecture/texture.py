"""
Texture variance + oxidation gradients — the "worn" look, deterministic & seeded.
Pro builds never use 100% one block on a large surface.
"""
from __future__ import annotations

import random

from architecture.geometry import Vec3, cmd_fill, cmd_set


def _cells(a: Vec3, b: Vec3):
    for x in range(min(a.x, b.x), max(a.x, b.x) + 1):
        for y in range(min(a.y, b.y), max(a.y, b.y) + 1):
            for z in range(min(a.z, b.z), max(a.z, b.z) + 1):
                yield x, y, z


def textured_fill(a: Vec3, b: Vec3, primary: str, variants: list[str],
                  density: float, rng: random.Random) -> list[str]:
    """One /fill of `primary`, then ≤15% sprinkled variant setblocks."""
    cmds = [cmd_fill(a, b, primary)]
    if not variants:
        return cmds
    density = min(0.15, max(0.0, density))
    cells = list(_cells(a, b))
    n = int(len(cells) * density)
    if n <= 0:
        return cmds
    for x, y, z in rng.sample(cells, min(n, len(cells))):
        cmds.append(cmd_set(Vec3(x, y, z), rng.choice(variants)))
    return cmds


# copper oxidation stages from fresh (low) to oxidized (high)
_OX_ORDER = ["copper", "exposed_copper", "weathered_copper", "oxidized_copper"]


def oxidation_gradient(a: Vec3, b: Vec3, base: str = "copper_block") -> list[str]:
    """Map copper oxidation stages by Y band: fresh low, weathered mid, oxidized
    peaks. `base` should be a *_copper / cut_copper family block."""
    y1, y2 = min(a.y, b.y), max(a.y, b.y)
    span = max(1, y2 - y1)
    cmds: list[str] = []
    suffix = base.replace("copper_block", "copper").replace("copper", "")
    stages = ["copper_block", "exposed_copper", "weathered_copper", "oxidized_copper"]
    for i, stage in enumerate(stages):
        ya = y1 + (span * i) // len(stages)
        yb = y1 + (span * (i + 1)) // len(stages) - 1
        if yb < ya:
            yb = ya
        cmds.append(cmd_fill(Vec3(a.x, ya, a.z), Vec3(b.x, min(yb, y2), b.z), stage))
    return cmds
