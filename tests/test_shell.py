"""Shell watertightness — migrated from the standalone test_shell.py into pytest.
Uses the shared VoxelGrid simulator (voxel.py)."""
import pytest

from shell import build_shell
from validator import validate_commands
from voxel import VoxelGrid

ORIGIN = {"x": 0, "y": 64, "z": 0}

CASES = {
    "medieval_house_gable": {
        "size": {"x": 13, "y": 7, "z": 11}, "style": "medieval", "structure_type": "house",
        "materials": {"walls": "minecraft:stone_bricks", "floor": "minecraft:oak_planks",
                      "roof": "minecraft:dark_oak_planks"}},
    "modern_shop_flat": {
        "size": {"x": 16, "y": 6, "z": 12}, "style": "modern", "structure_type": "shop",
        "materials": {"walls": "minecraft:white_concrete", "floor": "minecraft:smooth_stone",
                      "roof": "minecraft:gray_concrete"}},
    "tiny_cottage": {
        "size": {"x": 7, "y": 5, "z": 7}, "style": "rustic", "structure_type": "cottage",
        "materials": {}},
    "bad_materials_fallback": {
        "size": {"x": 9, "y": 6, "z": 9}, "style": "fantasy", "structure_type": "house",
        "materials": {"walls": "minecraft:rainbow_brick", "floor": "minecraft:fake_wood",
                      "roof": "minecraft:nonsense"}},
}


@pytest.mark.parametrize("name,intent", CASES.items())
def test_shell_is_complete_and_watertight(name, intent):
    cmds = build_shell(intent, ORIGIN)
    valid, errors = validate_commands(cmds)
    assert valid, f"{name}: {errors[:3]}"

    sx, sy, sz = intent["size"]["x"], intent["size"]["y"], intent["size"]["z"]
    x1, z1, x2, z2 = 0, 0, sx - 1, sz - 1
    floor_y, roof_y = 64, 64 + sy
    grid = VoxelGrid.from_commands(cmds)

    floor_full = all(grid.is_solid(xx, floor_y, zz)
                     for xx in range(x1, x2 + 1) for zz in range(z1, z2 + 1))
    roof_full = all(grid.is_solid(xx, roof_y, zz)
                    for xx in range(x1, x2 + 1) for zz in range(z1, z2 + 1))
    interior_air = sum(1 for xx in range(x1 + 1, x2) for yy in range(65, roof_y)
                       for zz in range(z1 + 1, z2) if grid.base_at(xx, yy, zz) == "air")
    door_open = any(grid.base_at(xx, 65, z1) == "air" for xx in range(x1, x2 + 1))

    assert floor_full, f"{name}: floor not full"
    assert roof_full, f"{name}: roof not full"
    assert interior_air > 0, f"{name}: no interior cavity"
    assert door_open, f"{name}: no door opening"
