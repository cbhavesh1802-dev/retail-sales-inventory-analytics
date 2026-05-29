"""
Snyk service — scans a GitHub repo's dependencies for vulnerabilities.
Returns a list of findings and a dependency risk score (0-100).
"""
import httpx
from dataclasses import dataclass, field
from typing import List
from app.config import settings

SNYK_API = "https://api.snyk.io/v1"

SEVERITY_SCORE = {
    "critical": 40,
    "high":     20,
    "medium":   8,
    "low":      2,
}

@dataclass
class SnykFinding:
    package:     str
    version:     str
    severity:    str
    title:       str
    cve:         str = ""
    cvss:        float = 0.0
    fix_version: str = ""

@dataclass
class SnykResult:
    findings:   List[SnykFinding] = field(default_factory=list)
    risk_score: int = 0
    error:      str = ""

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "critical")

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "high")

    @property
    def medium_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "medium")


async def scan_repo(owner: str, repo: str) -> SnykResult:
    """
    Ask Snyk to test a public GitHub repo for dependency vulnerabilities.
    Uses the /test/github endpoint — no need to clone the repo.
    """
    headers = {
        "Authorization": f"token {settings.snyk_token}",
        "Content-Type":  "application/json",
    }
    payload = {"targetFile": None}

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(
                f"{SNYK_API}/test/github/{owner}/{repo}",
                headers=headers,
                json=payload,
            )
            if resp.status_code == 422:
                # No supported manifest found — zero dependency risk
                return SnykResult(risk_score=0)

            if resp.status_code != 200:
                return SnykResult(
                    risk_score=0,
                    error=f"Snyk API returned {resp.status_code}: {resp.text[:200]}"
                )

            data = resp.json()
            return _parse_response(data)

        except httpx.RequestError as e:
            return SnykResult(risk_score=0, error=str(e))


def _parse_response(data: dict) -> SnykResult:
    findings = []
    raw_vulns = data.get("vulnerabilities") or []

    # Deduplicate by CVE id
    seen = set()
    for v in raw_vulns:
        key = v.get("id", v.get("title", ""))
        if key in seen:
            continue
        seen.add(key)

        identifiers = v.get("identifiers", {})
        cve_list = identifiers.get("CVE", [])

        findings.append(SnykFinding(
            package     = v.get("packageName", "unknown"),
            version     = v.get("version", "?"),
            severity    = v.get("severity", "low"),
            title       = v.get("title", "Unknown vulnerability"),
            cve         = cve_list[0] if cve_list else "",
            cvss        = v.get("cvssScore", 0.0),
            fix_version = _extract_fix(v),
        ))

    # Score: cap at 100, each severity adds points
    raw = sum(SEVERITY_SCORE.get(f.severity, 0) for f in findings)
    risk_score = min(raw, 100)

    return SnykResult(findings=findings, risk_score=risk_score)


def _extract_fix(vuln: dict) -> str:
    try:
        upgrades = vuln.get("fixedIn", [])
        return upgrades[0] if upgrades else ""
    except Exception:
        return ""
