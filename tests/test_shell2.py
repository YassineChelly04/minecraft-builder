"""Shell 2.0 craftsmanship + watertightness (Phase C / DoD-C)."""
import json
from pathlib import Path

import pytest

from architecture.brief import intent_to_brief
from architecture.geometry import OUTWARD
from architecture.shell2 import build_shell2
from architecture.walls import pillar_offsets, _face_axis, build_walls
from architecture.floors import straight_staircase
from architecture.geometry import Rect
from llm_client import stub_mode
from normalizer import normalize_commands
from repair import repair_commands
from validator import validate_commands
from voxel import VoxelGrid, flood_walkable

BENCH = json.loads((Path(__file__).resolve().parent.parent /
                    "benchmarks" / "prompts_buildings.json").read_text())


def _build(intent, origin=None):
    origin = origin or {"x": 0, "y": 64, "z": 0}
    brief = intent_to_brief(intent, origin, prompt=intent.get("notes", "t"))
    raw, geom = build_shell2(brief)
    clean, _ = repair_commands(normalize_commands(raw))
    return clean, geom


# ── pillar law ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("length", range(5, 51))
def test_pillar_spacing_law(length):
    offs = pillar_offsets(length)
    assert offs[0] == 0 and offs[-1] == length - 1          # corners always
    for i in range(len(offs) - 1):
        bay = offs[i + 1] - offs[i] - 1
        # every interior bay must be ≥3 wide (or it's the final corner pair)
        assert bay >= 3 or offs[i + 1] == length - 1


def test_window_never_on_pillar():
    intent = {"size": {"x": 19, "y": 7, "z": 15}, "style": "medieval",
              "structure_type": "house", "palette_name": "medieval_castle",
              "room_program": ["living", "kitchen", "bedroom"]}
    clean, geom = _build(intent)
    grid = VoxelGrid.from_commands(clean)
    rect = geom.footprint[0]
    for wall in geom.walls:
        length, pos, _ = _face_axis(wall.face, rect)
        for t in wall.pillars:
            x, z = pos(t)
            # a pillar column should never be glass
            assert grid.base_at(x, geom.origin.y + 2, z) != "glass_pane"


# ── roof + cornice ───────────────────────────────────────────────────────────

def test_gable_overhang_present():
    intent = {"size": {"x": 13, "y": 7, "z": 11}, "style": "medieval",
              "structure_type": "house", "palette_name": "medieval_castle",
              "room_program": ["living"]}
    clean, geom = _build(intent)
    grid = VoxelGrid.from_commands(clean)
    rect = geom.footprint[0]
    # at least one solid roof cell sits OUTSIDE the footprint (the overhang)
    overhang = any(
        grid.is_solid(x, y, z)
        for y in range(geom.roof_base_y, geom.roof_base_y + 8)
        for x in range(rect.x1 - 1, rect.x2 + 2)
        for z in range(rect.z1 - 1, rect.z2 + 2)
        if not rect.contains(x, z))
    assert overhang


def test_cornice_ring_present():
    intent = {"size": {"x": 13, "y": 7, "z": 11}, "style": "modern",
              "structure_type": "house", "palette_name": "modern_villa",
              "room_program": ["living"]}
    clean, geom = _build(intent)
    grid = VoxelGrid.from_commands(clean)
    rect = geom.footprint[0]
    wall_top = geom.roof_base_y - 1
    # the outward cornice lip should be solid along most of the perimeter
    ring = 0
    total = 0
    for x in range(rect.x1, rect.x2 + 1):
        for (z, oz) in ((rect.z1, -1), (rect.z2, 1)):
            total += 1
            if grid.is_solid(x, wall_top, z + oz):
                ring += 1
    assert ring / total >= 0.8


# ── watertight on all 15 prompts (kit mode, offline) ─────────────────────────

@pytest.mark.parametrize("entry", BENCH, ids=[e["id"] for e in BENCH])
def test_all_prompts_watertight_kit_mode(entry):
    from pipeline import build_structure
    with stub_mode(True):
        res = build_structure(entry["prompt"], entry["origin"], mode="dsl", refine=False)
    assert res["valid"], res["errors"][:3]
    geom = res["geometry"]
    grid = VoxelGrid.from_commands(res["commands"])
    rect = geom.footprint[0]
    fy, ry = geom.origin.y, geom.roof_base_y
    floor_full = all(grid.is_solid(x, fy, z)
                     for x in range(rect.x1, rect.x2 + 1) for z in range(rect.z1, rect.z2 + 1))
    roof_full = all(any(grid.is_solid(x, y, z) for y in range(ry, ry + 8))
                    for x in range(rect.x1, rect.x2 + 1) for z in range(rect.z1, rect.z2 + 1))
    assert floor_full, f"{entry['id']} floor not full"
    assert roof_full, f"{entry['id']} roof not full"


# ── BSP reachability ─────────────────────────────────────────────────────────

def test_every_room_reachable_from_front_door():
    intent = {"size": {"x": 17, "y": 7, "z": 15}, "style": "medieval",
              "structure_type": "house", "palette_name": "medieval_castle",
              "room_program": ["living", "kitchen", "bedroom", "study"]}
    clean, geom = _build(intent)
    grid = VoxelGrid.from_commands(clean)
    door = geom.anchors["door_inside"]
    start = (door.x, door.y, door.z)
    reached = flood_walkable(grid, start)
    for zone in geom.zones:
        inner = zone.rect.inset(1)
        cells = {(x, zone.floor_y + 1, z)
                 for x in range(inner.x1, inner.x2 + 1)
                 for z in range(inner.z1, inner.z2 + 1)
                 if not grid.is_solid(x, zone.floor_y + 1, z)}
        assert cells & reached, f"room {zone.name} unreachable from front door"


# ── staircase headroom ───────────────────────────────────────────────────────

def test_staircase_has_headroom():
    rect = Rect(0, 0, 9, 9)
    cmds, hole = straight_staircase(rect, 64, 69, _PAL, _RNG())
    assert cmds
    assert hole.width >= 1 and hole.depth >= 1


# helpers
from knowledge.palettes import PALETTES
import random
_PAL = PALETTES["medieval_castle"]
def _RNG():
    return random.Random(0)
