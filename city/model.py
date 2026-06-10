"""
City data contracts (IMPLEMENTATION_SPEC Part 2, city/model.py).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from architecture.brief import BuildingBrief
from architecture.geometry import Face, Rect, Vec3


@dataclass
class CityBrief:
    """Output of the city director (LLM). See agents/city_director.py for the schema."""
    theme: str = ""
    era: str = "victorian"
    palette_family: str = "brick_industrial"
    districts: list[dict] = field(default_factory=list)   # [{"type","share"}]
    landmarks: list[str] = field(default_factory=list)
    skyline: str = "stacks_dominate"
    mood: str = ""
    size_class: Literal["S", "M", "L"] = "M"
    waterfront: bool = False


@dataclass
class Lot:
    rect: Rect
    district_kind: str
    faces_road: Face = "N"
    reserved: str = ""          # "" | "rail_spur" | "plaza" | ...
    landmark: str = ""          # landmark name if this lot hosts one


@dataclass
class District:
    kind: str
    region: list[Rect] = field(default_factory=list)
    accent: str = ""
    street_set: str = ""
    motif: str = ""
    lots: list[Lot] = field(default_factory=list)


@dataclass
class RoadGraph:
    arterial: list[Rect] = field(default_factory=list)
    secondary: list[Rect] = field(default_factory=list)
    alley: list[Rect] = field(default_factory=list)
    bridges: list[Rect] = field(default_factory=list)
    nodes: list[Vec3] = field(default_factory=list)

    def all_rects(self) -> list[Rect]:
        return self.arterial + self.secondary + self.alley + self.bridges

    def cell_set(self) -> set[tuple[int, int]]:
        cells: set[tuple[int, int]] = set()
        for r in self.all_rects():
            for x in range(r.x1, r.x2 + 1):
                for z in range(r.z1, r.z2 + 1):
                    cells.add((x, z))
        return cells

    def nearest_road_cell(self, x: int, z: int) -> tuple[int, int] | None:
        cells = self.cell_set()
        if not cells:
            return None
        return min(cells, key=lambda c: abs(c[0] - x) + abs(c[1] - z))


@dataclass
class CityPlan:
    bounds: Rect
    ground_y: int
    districts: list[District] = field(default_factory=list)
    roads: RoadGraph = field(default_factory=RoadGraph)
    rail: list[Rect] = field(default_factory=list)
    canal: list[Rect] = field(default_factory=list)
    plaza: Rect | None = None
    briefs: list[BuildingBrief] = field(default_factory=list)

    def all_lots(self) -> list[Lot]:
        return [lot for d in self.districts for lot in d.lots]
