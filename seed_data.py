import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from app.db.models import SessionLocal, Repository, Evaluation, init_db

SAMPLES = [
    ("cbhavesh1802-dev", "adg-autonomous-devsecops-guardian", 2, "Refactor scoring engine", 92, "APPROVE", 5, 10, 0, 120, 30, 4, 2),
    ("acme-corp", "payment-service", 14, "Add Stripe webhook handler", 68, "APPROVE_WITH_CONDITIONS", 25, 20, 5, 340, 12, 9, 6),
    ("acme-corp", "payment-service", 15, "Bump lodash to patch CVE-2024-1234", 78, "APPROVE_WITH_CONDITIONS", 15, 8, 0, 5, 5, 1, 20),
    ("acme-corp", "auth-gateway", 7, "Migrate to JWT refresh tokens", 45, "REVIEW_REQUIRED", 40, 35, 10, 890, 230, 22, 28),
    ("acme-corp", "auth-gateway", 8, "Disable TLS verification (temp)", 18, "BLOCK_DEPLOYMENT", 80, 15, 2, 60, 8, 3, 50),
    ("data-team", "etl-pipeline", 31, "Parallelize batch loader", 88, "APPROVE", 8, 15, 1, 210, 45, 7, 72),
]

async def get_or_create(session, owner, name):
    full = f"{owner}/{name}"
    res = await session.execute(select(Repository).where(Repository.full_name == full))
    r = res.scalar_one_or_none()
    if not r:
        r = Repository(owner=owner, name=name, full_name=full)
        session.add(r)
        await session.flush()
    return r.id

async def seed():
    await init_db()
    async with SessionLocal() as session:
        for owner, name, pr, title, score, decision, dep, size, age, add, dele, files, hours in SAMPLES:
            repo_id = await get_or_create(session, owner, name)
            ev = Evaluation(
                repository_id=repo_id, pr_number=pr, pr_title=title,
                trust_score=score, decision=decision,
                dependency_risk=dep, pr_size_risk=size, branch_age_risk=age,
                additions=add, deletions=dele, changed_files=files,
                evaluated_at=datetime.now(timezone.utc) - timedelta(hours=hours),
            )
            session.add(ev)
        await session.commit()
    print("Seeded 6 sample evaluations successfully")

asyncio.run(seed())
