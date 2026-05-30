from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from app.db.models import Repository, Evaluation, Vulnerability
import logging

log = logging.getLogger("adg.db")

async def save_evaluation(session, owner, repo, pr_number, pr_title, result, snyk, pr_data):
    full_name = f"{owner}/{repo}"
    repo_obj = await _get_or_create_repo(session, owner, repo, full_name)
    evaluation = Evaluation(
        repository_id=repo_obj.id, pr_number=pr_number, pr_title=pr_title,
        trust_score=result.trust_score, decision=result.decision,
        dependency_risk=result.dependency_risk, pr_size_risk=result.pr_size_risk,
        branch_age_risk=result.branch_age_risk, rationale=result.rationale,
        additions=pr_data.get("additions", 0), deletions=pr_data.get("deletions", 0),
        changed_files=pr_data.get("changed_files", 0),
    )
    session.add(evaluation)
    await session.flush()
    for finding in snyk.findings:
        session.add(Vulnerability(
            evaluation_id=evaluation.id, package=finding.package,
            version=finding.version, severity=finding.severity,
            title=finding.title, cve=finding.cve, cvss=finding.cvss,
            fix_version=finding.fix_version,
        ))
    await session.commit()
    log.info(f"Saved evaluation #{evaluation.id} for {full_name}#{pr_number}")
    return evaluation

async def get_recent_evaluations(session, limit=20):
    result = await session.execute(
        select(Evaluation, Repository).join(Repository)
        .order_by(desc(Evaluation.evaluated_at)).limit(limit)
    )
    return result.all()

async def get_repo_stats(session, full_name):
    repo = await session.execute(select(Repository).where(Repository.full_name == full_name))
    repo_obj = repo.scalar_one_or_none()
    if not repo_obj:
        return {}
    stats = await session.execute(
        select(func.count(Evaluation.id), func.avg(Evaluation.trust_score))
        .where(Evaluation.repository_id == repo_obj.id)
    )
    row = stats.one()
    return {"total_evaluations": row[0] or 0, "avg_trust_score": round(float(row[1] or 0), 1)}

async def _get_or_create_repo(session, owner, name, full_name):
    result = await session.execute(select(Repository).where(Repository.full_name == full_name))
    repo = result.scalar_one_or_none()
    if not repo:
        repo = Repository(owner=owner, name=name, full_name=full_name)
        session.add(repo)
        await session.flush()
    return repo
