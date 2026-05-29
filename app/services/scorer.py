"""
Trust Scorer — combines all risk signals into a single 0-100 trust score
and maps it to a deployment decision.

Phase 1 signals:
  - Dependency risk   (from Snyk)     weight: 50%
  - PR size risk                      weight: 30%
  - Branch age risk                   weight: 20%

Higher trust score = safer to deploy.
"""
from dataclasses import dataclass
from app.services.snyk import SnykResult

@dataclass
class PRMeta:
    additions:    int = 0
    deletions:    int = 0
    changed_files: int = 0
    commits:      int = 1
    branch_age_days: int = 0   # days since branch was created

@dataclass
class TrustResult:
    trust_score:       int = 100
    decision:          str = "APPROVE"
    dependency_risk:   int = 0
    pr_size_risk:      int = 0
    branch_age_risk:   int = 0
    rationale:         str = ""

DECISIONS = [
    (85,  "APPROVE"),
    (60,  "APPROVE_WITH_CONDITIONS"),
    (30,  "REVIEW_REQUIRED"),
    (0,   "BLOCK_DEPLOYMENT"),
]

DECISION_EMOJI = {
    "APPROVE":                   "✅",
    "APPROVE_WITH_CONDITIONS":   "⚠️",
    "REVIEW_REQUIRED":           "🔍",
    "BLOCK_DEPLOYMENT":          "🚫",
}


def calculate(snyk: SnykResult, pr: PRMeta) -> TrustResult:
    dep_risk      = snyk.risk_score
    pr_size_risk  = _pr_size_risk(pr)
    branch_risk   = _branch_age_risk(pr.branch_age_days)

    # Weighted composite risk (0-100)
    composite_risk = (
        dep_risk      * 0.50 +
        pr_size_risk  * 0.30 +
        branch_risk   * 0.20
    )

    trust_score = max(0, min(100, int(100 - composite_risk)))
    decision    = _decision(trust_score)
    rationale   = _build_rationale(snyk, pr, dep_risk, pr_size_risk, branch_risk, trust_score)

    return TrustResult(
        trust_score     = trust_score,
        decision        = decision,
        dependency_risk = dep_risk,
        pr_size_risk    = pr_size_risk,
        branch_age_risk = branch_risk,
        rationale       = rationale,
    )


def _pr_size_risk(pr: PRMeta) -> int:
    total_changes = pr.additions + pr.deletions
    if total_changes < 50:    return 0
    if total_changes < 200:   return 15
    if total_changes < 500:   return 30
    if total_changes < 1000:  return 50
    return 70

def _branch_age_risk(days: int) -> int:
    if days < 3:   return 0
    if days < 7:   return 10
    if days < 14:  return 25
    if days < 30:  return 40
    return 60

def _decision(score: int) -> str:
    for threshold, decision in DECISIONS:
        if score >= threshold:
            return decision
    return "BLOCK_DEPLOYMENT"

def _build_rationale(
    snyk: SnykResult,
    pr: PRMeta,
    dep_risk: int,
    pr_size_risk: int,
    branch_risk: int,
    trust_score: int,
) -> str:
    lines = []

    if snyk.critical_count:
        lines.append(f"🔴 {snyk.critical_count} critical vulnerabilit{'y' if snyk.critical_count==1 else 'ies'} found in dependencies.")
    if snyk.high_count:
        lines.append(f"🟠 {snyk.high_count} high-severity vulnerabilit{'y' if snyk.high_count==1 else 'ies'} found.")
    if snyk.medium_count:
        lines.append(f"🟡 {snyk.medium_count} medium-severity issue{'s' if snyk.medium_count>1 else ''}.")
    if not snyk.findings:
        lines.append("✅ No dependency vulnerabilities found.")

    total_changes = pr.additions + pr.deletions
    if total_changes > 500:
        lines.append(f"📦 Large PR: {total_changes} lines changed across {pr.changed_files} file(s).")
    elif total_changes > 0:
        lines.append(f"📝 {total_changes} lines changed across {pr.changed_files} file(s).")

    if pr.branch_age_days > 14:
        lines.append(f"⏰ Branch is {pr.branch_age_days} days old — consider rebasing.")

    return "\n".join(lines)
