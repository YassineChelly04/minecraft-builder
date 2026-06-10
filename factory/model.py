"""
Factory data contracts. A FactoryBrief (director output) + the industry template
become a FactoryPlan: process stages placed left→right along the value stream,
support buildings in a utility band, offices and gate on the front apron.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from architecture.geometry import Rect, Vec3


@dataclass
class FactoryBrief:
    """Output of the factory director (one LLM call + deterministic brand map)."""
    company: str = ""                  # display name, e.g. "Ford"
    industry: str = "generic"          # key into factory.industries.INDUSTRIES
    product: str = "goods"             # what the plant makes
    era: str = "modern"                # victorian | interwar | modern | dieselpunk
    palette_family: str = "steel_and_copper"
    size_class: Literal["S", "M", "L"] = "M"
    mood: str = ""
    signature: list[str] = field(default_factory=list)


@dataclass
class StagePlacement:
    """One building/structure on the site."""
    stage: str                          # e.g. "press_shop", "office_hq"
    archetype: str                      # registered archetype name
    rect: Rect
    order: int                          # process position (0..n-1); -1 = support/front
    role: Literal["process", "support", "front"] = "process"
    height_band: tuple[int, int] = (8, 12)


@dataclass
class FactoryPlan:
    bounds: Rect
    ground_y: int
    industry: str = "generic"
    stages: list[StagePlacement] = field(default_factory=list)
    spine: Rect | None = None           # main internal road, runs the flow axis
    front_road: Rect | None = None      # gate -> spine stub
    rail: list[Rect] = field(default_factory=list)
    parking: Rect | None = None
    gate: Vec3 | None = None            # centre of the main gate on the fence
    links: list[tuple[Rect, int]] = field(default_factory=list)  # (span rect, y offset) conveyor/pipe bridges
    link_kind: str = "conveyor"         # conveyor | pipe | none

    def process_stages(self) -> list[StagePlacement]:
        return sorted((s for s in self.stages if s.role == "process"),
                      key=lambda s: s.order)
