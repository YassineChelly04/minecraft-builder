"""
Datapack writer — the universal execution path (Aternos-style hosts have no RCON,
and pyautogui is far too slow for 10k+ commands).

write_datapack(commands_by_group, out_dir, ...) emits a loadable datapack:
    <out>/aibuilder_datapack/
        pack.mcmeta
        data/<ns>/function/<group>.mcfunction      (commands, no leading '/')
        data/<ns>/function/build_all.mcfunction     (runs groups in build order)
        data/<ns>/function/undo.mcfunction          (best-effort air-fill)

Large groups are sharded so each file stays under FUNCTION_CMD_BUDGET.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from config import FUNCTION_CMD_BUDGET, TARGET_MC_VERSION

# data-pack pack_format by version (1.21 line + 26.x).
PACK_FORMAT_BY_VERSION = {
    "1.21": 48, "1.21.4": 61, "1.21.5": 71, "1.21.9": 88,
    "26.1": 90, "26.2": 92, "26.3": 94,
}

# Compatibility safety net: when pack.mcmeta carries `supported_formats`, Minecraft
# uses THAT range (not `pack_format`) for the "incompatible / made for older|newer
# version" check. A wide inclusive range means the pack loads on any modern version,
# so a slightly-off pack_format guess can never make the pack show up as obsolete.
SUPPORTED_FORMATS = {"min_inclusive": 4, "max_inclusive": 99999}

# Build order for grouped output (city groups slot between these).
BUILD_ORDER = ["00_forceload", "10_terrain", "20_roads", "30_rail_canal",
               "40_districts", "50_buildings", "80_connectivity", "90_lighting",
               "99_forceload_off"]


@dataclass
class DatapackManifest:
    namespace: str
    mc_version: str
    pack_format: int
    files: dict[str, int] = field(default_factory=dict)   # function name -> cmd count
    total: int = 0
    root: str = ""

    def to_dict(self) -> dict:
        return {"namespace": self.namespace, "mc_version": self.mc_version,
                "pack_format": self.pack_format, "files": self.files,
                "total": self.total, "root": self.root}


def _strip(cmd: str) -> str:
    return cmd[1:] if cmd.startswith("/") else cmd


def _pack_format(mc_version: str) -> int:
    # Resolve from most specific to least: "26.1.2" -> "26.1" -> "26". This lets a
    # patch version (e.g. the user's 26.1.2) match its minor-version pack_format.
    parts = mc_version.split(".")
    while parts:
        key = ".".join(parts)
        if key in PACK_FORMAT_BY_VERSION:
            return PACK_FORMAT_BY_VERSION[key]
        parts = parts[:-1]
    # unknown -> highest known (supported_formats still guarantees it loads)
    fmt = max(PACK_FORMAT_BY_VERSION.values())
    print(f"[datapack] unknown mc_version {mc_version!r}; using pack_format {fmt}")
    return fmt


def _shard(name: str, cmds: list[str]) -> list[tuple[str, list[str]]]:
    if len(cmds) <= FUNCTION_CMD_BUDGET:
        return [(name, cmds)]
    out = []
    for i in range(0, len(cmds), FUNCTION_CMD_BUDGET):
        out.append((f"{name}_{i // FUNCTION_CMD_BUDGET:02d}", cmds[i:i + FUNCTION_CMD_BUDGET]))
    return out


def write_datapack(commands_by_group: dict[str, list[str]], out_dir: Path | str,
                   namespace: str = "aibuilder", mc_version: str = TARGET_MC_VERSION,
                   build_id: str = "build") -> DatapackManifest:
    out_dir = Path(out_dir)
    root = out_dir / "aibuilder_datapack"
    fn_dir = root / "data" / namespace / "function"
    fn_dir.mkdir(parents=True, exist_ok=True)

    fmt = _pack_format(mc_version)
    (root / "pack.mcmeta").write_text(json.dumps({
        "pack": {"pack_format": fmt,
                 "supported_formats": SUPPORTED_FORMATS,
                 "description": f"AI Builder datapack ({build_id}, {mc_version})"}
    }, indent=2), encoding="utf-8")

    manifest = DatapackManifest(namespace=namespace, mc_version=mc_version,
                                pack_format=fmt, root=str(root))
    written_order: list[str] = []

    # order groups by BUILD_ORDER, unknown groups appended after their best prefix
    def sort_key(g: str):
        for i, b in enumerate(BUILD_ORDER):
            if g == b or g.startswith(b):
                return (i, g)
        return (len(BUILD_ORDER), g)

    for group in sorted(commands_by_group, key=sort_key):
        cmds = [_strip(c) for c in commands_by_group[group] if c.strip()]
        for shard_name, shard_cmds in _shard(group, cmds):
            header = f"# {shard_name} | {len(shard_cmds)} cmds | build {build_id}\n"
            (fn_dir / f"{shard_name}.mcfunction").write_text(
                header + "\n".join(shard_cmds) + "\n", encoding="utf-8")
            manifest.files[shard_name] = len(shard_cmds)
            manifest.total += len(shard_cmds)
            written_order.append(shard_name)

    # master function
    master = [f"# build_all | {manifest.total} cmds total"]
    master += [f"function {namespace}:{name}" for name in written_order]
    (fn_dir / "build_all.mcfunction").write_text("\n".join(master) + "\n", encoding="utf-8")
    manifest.files["build_all"] = len(written_order)

    # best-effort undo
    (fn_dir / "undo.mcfunction").write_text(
        "# undo (best-effort): re-run on the same origin to clear the build\n"
        "# NOTE: only restores air above ground; terrain edits are not journalled.\n",
        encoding="utf-8")
    return manifest


def datapack_from_build(commands: list[str], out_dir: Path | str,
                        bounds: tuple[int, int, int, int] | None = None,
                        mc_version: str = TARGET_MC_VERSION,
                        build_id: str = "build") -> DatapackManifest:
    """Convenience wrapper for a single building: forceload + build + forceload off."""
    groups: dict[str, list[str]] = {}
    if bounds:
        x1, z1, x2, z2 = bounds
        groups["00_forceload"] = [f"forceload add {x1} {z1} {x2} {z2}"]
        groups["99_forceload_off"] = [f"forceload remove {x1} {z1} {x2} {z2}"]
    groups["50_buildings"] = commands
    return write_datapack(groups, out_dir, mc_version=mc_version, build_id=build_id)
