"""
SVG plot of a FactoryPlan — the value stream at a glance: labelled process
stages west→east, support band, front band, roads, rail, fence. No dependencies.
"""
from __future__ import annotations

from factory.model import FactoryPlan

_ROLE_COLOR = {"process": "#b45309", "support": "#6b7280", "front": "#1d4ed8"}


def plan_to_svg(plan: FactoryPlan, scale: int = 3) -> str:
    b = plan.bounds
    w, h = b.width * scale, b.depth * scale
    ox, oz = b.x1, b.z1

    def rx(x): return (x - ox) * scale
    def rz(z): return (z - oz) * scale

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
             f'viewBox="0 0 {w} {h}">',
             f'<rect width="{w}" height="{h}" fill="#f4f6f3"/>',
             f'<rect x="0" y="0" width="{w}" height="{h}" fill="none" '
             f'stroke="#3f3f46" stroke-width="2"/>']   # fence

    for r in (plan.spine, plan.front_road):
        if r:
            parts.append(f'<rect x="{rx(r.x1)}" y="{rz(r.z1)}" width="{r.width*scale}" '
                         f'height="{r.depth*scale}" fill="#3f3f46"/>')
    for r in plan.rail:
        parts.append(f'<rect x="{rx(r.x1)}" y="{rz(r.z1)}" width="{r.width*scale}" '
                     f'height="{r.depth*scale}" fill="#78716c"/>')
    if plan.parking:
        p = plan.parking
        parts.append(f'<rect x="{rx(p.x1)}" y="{rz(p.z1)}" width="{p.width*scale}" '
                     f'height="{p.depth*scale}" fill="#9ca3af" opacity="0.6"/>')
    for rect, _ in plan.links:
        parts.append(f'<rect x="{rx(rect.x1)}" y="{rz(rect.z1)-2}" width="{rect.width*scale}" '
                     f'height="4" fill="#0e7490"/>')

    for s in plan.stages:
        r = s.rect
        col = _ROLE_COLOR.get(s.role, "#9ca3af")
        parts.append(f'<rect x="{rx(r.x1)}" y="{rz(r.z1)}" width="{r.width*scale}" '
                     f'height="{r.depth*scale}" fill="{col}" opacity="0.8"/>')
        cx, cz = rx((r.x1 + r.x2) // 2), rz((r.z1 + r.z2) // 2)
        label = s.stage.replace("_", " ")
        parts.append(f'<text x="{cx}" y="{cz}" text-anchor="middle" fill="#fff" '
                     f'font-family="sans-serif" font-size="10">{label}</text>')
        if s.role == "process":
            parts.append(f'<text x="{cx}" y="{cz + 12}" text-anchor="middle" fill="#fde68a" '
                         f'font-family="sans-serif" font-size="9">{s.order + 1}</text>')
    parts.append("</svg>")
    return "\n".join(parts)
