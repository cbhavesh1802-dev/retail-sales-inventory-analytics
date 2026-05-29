"""
ADG MVP — Main FastAPI application.

Endpoint:  POST /webhook/github
Receives GitHub pull_request events, runs trust scoring, posts PR comment.
"""
import hashlib
import hmac
import logging
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from app.config import settings
from app.services import snyk, scorer, github
from app.services.scorer import PRMeta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("adg")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("ADG MVP started — waiting for GitHub webhooks")
    yield
    log.info("ADG MVP shutting down")


app = FastAPI(
    title="ADG — Autonomous DevSecOps Guardian",
    description="Deployment trust scoring via GitHub webhooks",
    version="0.1.0",
    lifespan=lifespan,
)


# ── Health check ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0", "timestamp": datetime.now(timezone.utc).isoformat()}


# ── GitHub webhook ────────────────────────────────────────────────────────────

@app.post("/webhook/github")
async def github_webhook(request: Request, background: BackgroundTasks):
    """
    Receives GitHub webhook events.
    Validates signature, filters pull_request events, kicks off scoring.
    """
    body = await request.body()

    # 1. Verify webhook signature
    _verify_signature(body, request.headers.get("X-Hub-Signature-256", ""))

    # 2. Only process pull_request events
    event_type = request.headers.get("X-GitHub-Event", "")
    if event_type != "pull_request":
        return JSONResponse({"message": f"Ignored event: {event_type}"})

    payload = await request.json()
    action  = payload.get("action", "")

    # Only process when PR is opened or updated
    if action not in ("opened", "synchronize", "reopened"):
        return JSONResponse({"message": f"Ignored action: {action}"})

    pr   = payload["pull_request"]
    repo = payload["repository"]

    owner      = repo["owner"]["login"]
    repo_name  = repo["name"]
    pr_number  = pr["number"]
    pr_title   = pr["title"]

    log.info(f"PR #{pr_number} '{pr_title}' in {owner}/{repo_name} — queuing evaluation")

    # Run evaluation in background so webhook returns fast
    background.add_task(evaluate_pr, owner, repo_name, pr_number, pr)

    return JSONResponse({"message": "Evaluation queued", "pr": pr_number})


# ── Core evaluation logic ─────────────────────────────────────────────────────

async def evaluate_pr(owner: str, repo: str, pr_number: int, pr_data: dict):
    """
    Full evaluation pipeline:
      1. Scan dependencies with Snyk
      2. Build PR metadata
      3. Calculate trust score
      4. Post comment on PR
    """
    log.info(f"[{owner}/{repo}#{pr_number}] Starting evaluation")

    # Step 1 — Snyk dependency scan
    log.info(f"[{owner}/{repo}#{pr_number}] Running Snyk scan...")
    snyk_result = await snyk.scan_repo(owner, repo)

    if snyk_result.error:
        log.warning(f"[{owner}/{repo}#{pr_number}] Snyk error: {snyk_result.error}")
    else:
        log.info(
            f"[{owner}/{repo}#{pr_number}] Snyk done — "
            f"{len(snyk_result.findings)} findings, risk={snyk_result.risk_score}"
        )

    # Step 2 — PR metadata
    branch_age = _branch_age_days(pr_data.get("created_at", ""))
    pr_meta = PRMeta(
        additions      = pr_data.get("additions", 0),
        deletions      = pr_data.get("deletions", 0),
        changed_files  = pr_data.get("changed_files", 0),
        commits        = pr_data.get("commits", 1),
        branch_age_days = branch_age,
    )

    # Step 3 — Trust score
    result = scorer.calculate(snyk_result, pr_meta)
    log.info(
        f"[{owner}/{repo}#{pr_number}] Trust score: {result.trust_score}/100 "
        f"→ {result.decision}"
    )

    # Step 4 — Post GitHub comment
    success = await github.post_trust_comment(
        owner, repo, pr_number, result, snyk_result.findings
    )
    if success:
        log.info(f"[{owner}/{repo}#{pr_number}] Comment posted successfully")
    else:
        log.error(f"[{owner}/{repo}#{pr_number}] Failed to post comment")


# ── Manual trigger (for testing without a real PR) ────────────────────────────

@app.post("/evaluate/{owner}/{repo}/{pr_number}")
async def manual_evaluate(owner: str, repo: str, pr_number: int, background: BackgroundTasks):
    """
    Manually trigger evaluation for any PR.
    Useful for testing before webhook is wired up.
    """
    log.info(f"Manual evaluation triggered for {owner}/{repo}#{pr_number}")

    try:
        pr_data = await github.get_pr_meta(owner, repo, pr_number)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    background.add_task(evaluate_pr, owner, repo, pr_number, pr_data)
    return {"message": "Evaluation started", "pr": pr_number, "repo": f"{owner}/{repo}"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _verify_signature(body: bytes, signature_header: str):
    """Verify GitHub's HMAC-SHA256 webhook signature."""
    if not signature_header:
        raise HTTPException(status_code=401, detail="Missing X-Hub-Signature-256 header")

    expected = "sha256=" + hmac.new(
        settings.github_webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature_header):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")


def _branch_age_days(created_at_iso: str) -> int:
    """Calculate how many days old the branch is from the PR created_at timestamp."""
    if not created_at_iso:
        return 0
    try:
        created = datetime.fromisoformat(created_at_iso.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - created).days
    except ValueError:
        return 0
