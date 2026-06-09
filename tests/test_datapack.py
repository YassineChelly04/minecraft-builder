"""Datapack writer structure/format (Phase E — de-risk execution; CI asserts
structure only, in-game smoke test is manual)."""
import json

from execution.datapack import (
    write_datapack, datapack_from_build, PACK_FORMAT_BY_VERSION, FUNCTION_CMD_BUDGET,
)


def test_writes_loadable_structure(tmp_path):
    man = write_datapack({"50_buildings": ["/fill 0 64 0 3 64 3 minecraft:stone",
                                           "/setblock 1 65 1 minecraft:lantern"]},
                         tmp_path, mc_version="1.21.9")
    root = tmp_path / "aibuilder_datapack"
    assert (root / "pack.mcmeta").exists()
    meta = json.loads((root / "pack.mcmeta").read_text())
    assert meta["pack"]["pack_format"] == PACK_FORMAT_BY_VERSION["1.21.9"]
    fn = root / "data" / "aibuilder" / "function"
    assert (fn / "50_buildings.mcfunction").exists()
    assert (fn / "build_all.mcfunction").exists()
    # commands have no leading slash
    body = (fn / "50_buildings.mcfunction").read_text().splitlines()
    assert any(line.startswith("fill ") for line in body)
    assert not any(line.startswith("/") for line in body)


def test_build_all_calls_groups_in_order(tmp_path):
    man = datapack_from_build(["/setblock 0 64 0 minecraft:stone"], tmp_path,
                              bounds=(0, 0, 15, 15))
    master = (tmp_path / "aibuilder_datapack" / "data" / "aibuilder" / "function"
              / "build_all.mcfunction").read_text()
    assert master.index("00_forceload") < master.index("50_buildings")
    assert master.index("50_buildings") < master.index("99_forceload_off")


def test_large_group_is_sharded(tmp_path):
    big = [f"/setblock {i} 64 0 minecraft:stone" for i in range(FUNCTION_CMD_BUDGET + 10)]
    man = write_datapack({"50_buildings": big}, tmp_path)
    shards = [k for k in man.files if k.startswith("50_buildings_")]
    assert len(shards) >= 2
    assert all(c <= FUNCTION_CMD_BUDGET for k, c in man.files.items()
               if k.startswith("50_buildings_"))


def test_unknown_version_falls_back(tmp_path):
    man = write_datapack({"50_buildings": ["/setblock 0 64 0 minecraft:stone"]},
                         tmp_path, mc_version="99.9")
    assert man.pack_format == max(PACK_FORMAT_BY_VERSION.values())
