"""VoxelGrid simulator + light/walkability helpers."""
from voxel import VoxelGrid, propagate_light, flood_walkable


def test_fill_and_setblock_last_write_wins():
    g = VoxelGrid.from_commands([
        "/fill 0 64 0 2 64 2 minecraft:stone",
        "/setblock 1 64 1 minecraft:oak_planks",
    ])
    assert g.base_at(0, 64, 0) == "stone"
    assert g.base_at(1, 64, 1) == "oak_planks"
    assert g.base_at(5, 64, 5) == "air"
    assert g.is_solid(0, 64, 0)
    assert not g.is_solid(5, 64, 5)


def test_state_is_stripped_for_base():
    g = VoxelGrid.from_commands(["/setblock 0 64 0 minecraft:oak_stairs[facing=east]"])
    assert g.base_at(0, 64, 0) == "oak_stairs"
    assert g.block_at(0, 64, 0) == "minecraft:oak_stairs[facing=east]"


def test_light_propagation_falls_off():
    g = VoxelGrid.from_commands(["/setblock 0 64 0 minecraft:lantern"])
    light = propagate_light(g)
    assert light[(0, 64, 0)] == 15
    assert light[(1, 64, 0)] == 14
    assert light[(3, 64, 0)] == 12


def test_light_blocked_by_solid():
    # A lantern sealed inside a 3x3x3 stone shell lights its own cell but nothing
    # outside the shell — light cannot pass through solids.
    g = VoxelGrid.from_commands([
        "/fill -1 63 -1 1 65 1 minecraft:stone",
        "/setblock 0 64 0 minecraft:air",
        "/setblock 0 64 0 minecraft:lantern",
    ])
    light = propagate_light(g)
    assert light[(0, 64, 0)] == 15
    assert light.get((5, 64, 0), 0) == 0


def test_flood_walkable_clearance():
    # 3x3 floor with 2-high air above; flood should reach all 9 cells
    g = VoxelGrid.from_commands(["/fill 0 63 0 2 63 2 minecraft:stone"])
    floor = {(x, 64, z) for x in range(3) for z in range(3)}
    reached = flood_walkable(g, (1, 64, 1), floor)
    assert reached == floor
