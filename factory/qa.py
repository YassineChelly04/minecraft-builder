"""
Factory QA — deterministic checks on a finished plan: value-stream order
(stages strictly west→east, the industry-standard straight-through flow), full
stage coverage vs the industry template, process links present, no overlapping
footprints, and gate→spine road continuity.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from factory.industries import INDUSTRIES
from factory.model import FactoryPlan

WEIGHTS = {"flow_order": 3.0, "stage_coverage": 3.0, "links": 1.5,
           "no_overlap": 2.0, "gate_road": 1.5}
TARGETS = {"flow_order": 100, "stage_coverage": 100, "links": 80,
           "no_overlap": 100, "gate_road": 100}


@dataclass
class FactoryScore:
    metrics: dict[str, float] = field(default_factory=dict)
    total: float = 0.0
    failing: list[str] = field(default_factory=list)

    def to_dict(self):
        return {"total": round(self.total, 1),
                "metrics": {k: round(v, 1) for k, v in self.metrics.items()},
                "failing": self.failing}


def _flow_order(plan: FactoryPlan) -> float:
    stages = plan.process_stages()
    if len(stages) < 2:
        return 100.0
    ok = sum(1 for a, b in zip(stages, stages[1:]) if a.rect.x2 < b.rect.x1)
    return 100.0 * ok / (len(stages) - 1)


def _stage_coverage(plan: FactoryPlan) -> float:
    template = INDUSTRIES.get(plan.industry, INDUSTRIES["generic"])
    want = [s for s, _, _ in template.flow]
    have = {s.stage for s in plan.process_stages()}
    return 100.0 * sum(1 for s in want if s in have) / max(1, len(want))


def _links(plan: FactoryPlan) -> float:
    if plan.link_kind == "none":
        return 100.0
    stages = [s for s in plan.process_stages() if s.archetype != "apron"]
    expected = max(0, len(stages) - 1)
    return 100.0 if not expected else min(100.0, 100.0 * len(plan.links) / expected)


def _no_overlap(plan: FactoryPlan) -> float:
    rects = [s.rect for s in plan.stages]
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            if rects[i].intersect(rects[j]):
                return 0.0
    return 100.0


def _gate_road(plan: FactoryPlan) -> float:
    if not (plan.gate and plan.front_road and plan.spine):
        return 0.0
    touches_gate = plan.front_road.z2 >= plan.bounds.z2 - 1
    touches_spine = plan.front_road.z1 <= plan.spine.z2 + 1
    return 100.0 if (touches_gate and touches_spine
                     and plan.front_road.contains(plan.gate.x, plan.front_road.z1)) else 0.0


def score_factory(plan: FactoryPlan) -> FactoryScore:
    metrics = {
        "flow_order": _flow_order(plan),
        "stage_coverage": _stage_coverage(plan),
        "links": _links(plan),
        "no_overlap": _no_overlap(plan),
        "gate_road": _gate_road(plan),
    }
    num = den = 0.0
    failing = []
    for k, v in metrics.items():
        w = WEIGHTS[k]
        num += w * v
        den += w
        if v < TARGETS[k]:
            failing.append(k)
    return FactoryScore(metrics=metrics, total=num / den if den else 0.0, failing=failing)
