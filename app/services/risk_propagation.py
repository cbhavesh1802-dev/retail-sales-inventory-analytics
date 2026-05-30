"""
Risk Propagation Engine.
Models the service dependency graph and propagates risk through it:
if A depends on B and B is risky, A inherits a fraction of B's risk.
Edge meaning: "A depends on B" => SERVICE_GRAPH[A] contains B.
"""
from dataclasses import dataclass, field
from typing import Dict, List

SERVICE_GRAPH: Dict[str, List[str]] = {
    "adg-autonomous-devsecops-guardian": ["payment-service", "auth-gateway"],
    "payment-service": ["auth-gateway", "etl-pipeline"],
    "etl-pipeline": ["auth-gateway"],
    "auth-gateway": [],
}

DECAY = 0.4
ITERATIONS = 25


@dataclass
class ServiceNode:
    name: str
    base_risk: int
    effective_risk: int = 0
    depends_on: List[str] = field(default_factory=list)


def propagate(base_risk: Dict[str, int]) -> List[ServiceNode]:
    services = list(SERVICE_GRAPH.keys())
    base = {s: int(base_risk.get(s, 0)) for s in services}
    effective = dict(base)
    for _ in range(ITERATIONS):
        nxt = dict(base)
        for s in services:
            for dep in SERVICE_GRAPH[s]:
                nxt[s] += DECAY * effective.get(dep, 0)
        effective = {s: min(100, round(v)) for s, v in nxt.items()}
    return [
        ServiceNode(name=s, base_risk=base[s], effective_risk=effective[s], depends_on=SERVICE_GRAPH[s])
        for s in services
    ]
