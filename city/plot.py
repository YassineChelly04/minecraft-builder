"""
Pure-python SVG plot of a CityPlan — essential dev aid (roads, districts, lots,
landmarks). No dependencies.
"""
from __future__ import annotations

from pathlib import Path

from city.model import CityPlan

_KIND_COLOR = {
    "heavy_industry": "#b45309", "warehouses": "#a16207", "housing": "#15803d",
    "civic": "#1d4ed8", "docks": "#0e7490", "rail_yard": "#6b7280",
}


def plan_to_svg(plan: CityPlan, scale: int = 3) -> str:
    b = plan.bounds
    w, h = b.width * scale, b.depth * scale
    ox, oz = b.x1, b.z1

    def rx(x): return (x - ox) * scale
    def rz(z): return (z - oz) * scale

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
             f'viewBox="0 0 {w} {h}">',
             f'<rect width="{w}" height="{h}" fill="#faf9f6"/>']

    # districts (lot fills)
    for d in plan.districts:
        col = _KIND_COLOR.get(d.kind, "#9ca3af")
        for lot in d.lots:
            r = lot.rect
            fill = "#7c3aed" if lot.landmark else col
            parts.append(f'<rect x="{rx(r.x1)}" y="{rz(r.z1)}" width="{r.width*scale}" '
                         f'height="{r.depth*scale}" fill="{fill}" opacity="0.75"/>')

    # roads
    for r in plan.roads.all_rects():
        parts.append(f'<rect x="{rx(r.x1)}" y="{rz(r.z1)}" width="{r.width*scale}" '
                     f'height="{r.depth*scale}" fill="#3f3f46"/>')
    # canal
    for c in plan.canal:
        parts.append(f'<rect x="{rx(c.x1)}" y="{rz(c.z1)}" width="{c.width*scale}" '
                     f'height="{c.depth*scale}" fill="#2563eb" opacity="0.6"/>')
    parts.append("</svg>")
    return "\n".join(parts)


def write_plan_svg(plan: CityPlan, path: str | Path) -> str:
    Path(path).write_text(plan_to_svg(plan), encoding="utf-8")
    return str(path)
