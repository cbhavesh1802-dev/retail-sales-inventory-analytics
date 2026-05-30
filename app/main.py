import hashlib, hmac, logging, os
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.services import snyk, scorer, github
from app.services.scorer import PRMeta
from app.db.models import init_db, SessionLocal
from app.db.operations import save_evaluation, get_recent_evaluations, get_repo_stats

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("adg")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

@asynccontextmanager
async def lifespan(app):
    await init_db()
    log.info("ADG MVP started — waiting for GitHub webhooks")
    yield

app = FastAPI(title="ADG — Autonomous DevSecOps Guardian", version="0.2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.2.0"}

@app.get("/dashboard")
async def dashboard():
    return FileResponse(os.path.join(STATIC_DIR, "dashboard.html"))

@app.post("/webhook/github")
async def github_webhook(request: Request, background: BackgroundTasks):
    body = await request.body()
    _verify_signature(body, request.headers.get("X-Hub-Signature-256", ""))
    event_type = request.headers.get("X-GitHub-Event", "")
    if event_type != "pull_request":
        return JSONResponse({"message": f"Ignored event: {event_type}"})
    payload = await request.json()
    action = payload.get("action", "")
    if action not in ("opened", "synchronize", "reopened"):
        return JSONResponse({"message": f"Ignored action: {action}"})
    pr = payload["pull_request"]
    repo = payload["repository"]
    owner, repo_name = repo["owner"]["login"], repo["name"]
    pr_number, pr_title = pr["number"], pr.get("title", "")
    background.add_task(evaluate_pr, owner, repo_name, pr_number, pr, pr_title)
    return JSONResponse({"message": "Evaluation queued", "pr": pr_number})

async def evaluate_pr(owner, repo, pr_number, pr_data, pr_title=""):
    log.info(f"[{owner}/{repo}#{pr_number}] Starting evaluation")
    snyk_result = await snyk.scan_repo(owner, repo)
    pr_meta = PRMeta(
        additions=pr_data.get("additions", 0), deletions=pr_data.get("deletions", 0),
        changed_files=pr_data.get("changed_files", 0), commits=pr_data.get("commits", 1),
        branch_age_days=_branch_age_days(pr_data.get("created_at", "")),
    )
    result = scorer.calculate(snyk_result, pr_meta)
    log.info(f"[{owner}/{repo}#{pr_number}] Score: {result.trust_score}/100 → {result.decision}")
    try:
        async with SessionLocal() as session:
            await save_evaluation(session, owner, repo, pr_number, pr_title, result, snyk_result, pr_data)
        log.info(f"[{owner}/{repo}#{pr_number}] Saved to database")
    except Exception as e:
        log.error(f"[{owner}/{repo}#{pr_number}] DB error: {e}")
    success = await github.post_trust_comment(owner, repo, pr_number, result, snyk_result.findings)
    log.info(f"[{owner}/{repo}#{pr_number}] Comment {'posted' if success else 'failed'}")

@app.post("/evaluate/{owner}/{repo}/{pr_number}")
async def manual_evaluate(owner: str, repo: str, pr_number: int, background: BackgroundTasks):
    try:
        pr_data = await github.get_pr_meta(owner, repo, pr_number)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    background.add_task(evaluate_pr, owner, repo, pr_number, pr_data, pr_data.get("title", ""))
    return {"message": "Evaluation started", "pr": pr_number}

@app.get("/api/evaluations")
async def list_evaluations():
    async with SessionLocal() as session:
        rows = await get_recent_evaluations(session)
    return [{"id": ev.id, "repo": repo.full_name, "pr_number": ev.pr_number,
             "pr_title": ev.pr_title, "trust_score": ev.trust_score,
             "decision": ev.decision, "evaluated_at": ev.evaluated_at.isoformat()}
            for ev, repo in rows]

@app.get("/api/stats/{owner}/{repo}")
async def repo_stats(owner: str, repo: str):
    async with SessionLocal() as session:
        return await get_repo_stats(session, f"{owner}/{repo}")

def _verify_signature(body, sig):
    if not sig:
        raise HTTPException(status_code=401, detail="Missing signature")
    expected = "sha256=" + hmac.new(settings.github_webhook_secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise HTTPException(status_code=401, detail="Invalid signature")

def _branch_age_days(created_at_iso):
    if not created_at_iso:
        return 0
    try:
        created = datetime.fromisoformat(created_at_iso.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - created).days
    except:
        return 0


# ── Risk Propagation Engine ──────────────────────────────────────────────
from app.services.risk_propagation import propagate as _propagate, SERVICE_GRAPH as _GRAPH
from sqlalchemy import select as _select, func as _func
from app.db.models import Repository as _Repo, Evaluation as _Eval

@app.get("/api/risk-graph")
async def risk_graph():
    """Return services with base + propagated (effective) risk, and edges."""
    async with SessionLocal() as session:
        rows = await session.execute(
            _select(_Repo.name, _func.min(_Eval.trust_score))
            .join(_Eval, _Eval.repository_id == _Repo.id)
            .group_by(_Repo.name)
        )
        # base risk = 100 - worst trust score for that service
        base_risk = {name: 100 - int(score) for name, score in rows.all()}
    nodes = _propagate(base_risk)
    return {
        "nodes": [
            {"name": n.name, "base_risk": n.base_risk,
             "effective_risk": n.effective_risk, "depends_on": n.depends_on}
            for n in nodes
        ],
        "edges": [{"from": s, "to": dep} for s, deps in _GRAPH.items() for dep in deps],
    }
