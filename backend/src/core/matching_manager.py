import os
import json
import math
import logging
from openai import OpenAI
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from src.core import model
from src.core.schema import MatchingResult, MatchDetail, WorkerMatchingResult, MatchedJobDetail
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

SCORE_THRESHOLD = 70

_nvidia_client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ.get("NVIDIA_API_KEY"),
)
RERANK_MODEL = "meta/llama-3.1-8b-instruct"
MAX_CANDIDATES_FOR_RERANK = 25


def _search_workers(
    db: Session,
    query_vector: list[float],
    customer_location,
    radius_meters: int,
) -> list[tuple]:
    distance_expr = model.WorkerSkill.embedding.cosine_distance(query_vector)

    best_skill = (
        select(
            model.WorkerSkill.worker_id.label("worker_id"),
            model.WorkerSkill.id.label("skill_id"),
            model.WorkerSkill.title.label("skill_title"),
            model.WorkerSkill.description.label("skill_description"),
            model.WorkerSkill.skill_type.label("skill_type"),
            distance_expr.label("distance"),
        )
        .where(
            model.WorkerSkill.embedding.isnot(None),
            model.WorkerSkill.is_active.is_(True),
        )
        .distinct(model.WorkerSkill.worker_id)
        .order_by(model.WorkerSkill.worker_id, distance_expr.asc())
        .subquery()
    )

    stmt = (
        select(
            model.WorkerProfile,
            model.User,
            best_skill.c.distance,
            best_skill.c.skill_id,
            best_skill.c.skill_title,
            best_skill.c.skill_description,
            best_skill.c.skill_type,
        )
        .join(best_skill, best_skill.c.worker_id == model.WorkerProfile.id)
        .join(model.User, model.User.id == model.WorkerProfile.user_id)
        .where(
            model.WorkerProfile.location.isnot(None),
            model.WorkerProfile.is_complete.is_(True),
            model.WorkerProfile.is_rejected.is_(False),
            func.ST_DWithin(model.WorkerProfile.location, customer_location, radius_meters),
        )
        .order_by(best_skill.c.distance.asc())
    )

    return db.execute(stmt).all()


def calculate_match_score(distance: float) -> float:
    try:
        return max(0.0, min(100.0, round((1.0 / (1.0 + math.exp(25.0 * (distance - 0.90)))) * 100.0, 2)))
    except Exception:
        return 0.0


def _deduplicate_by_user(search_results: list[tuple]) -> list[tuple]:
    seen_user_ids: set[int] = set()
    deduped: list[tuple] = []
    for row in search_results:
        user = row[1]
        if user.id in seen_user_ids:
            continue
        seen_user_ids.add(user.id)
        deduped.append(row)
    return deduped


def _build_candidate_summary(
    worker: model.WorkerProfile,
    score: float,
    rank: int,
    skill_title: str | None = None,
    skill_description: str | None = None,
) -> dict:
    summary = {
        "worker_id": worker.id,
        "vector_rank": rank,
        "vector_score": score,
        "primary_trade": worker.job_category,
        "trade_tag": worker.category_tag,
        "profile_summary": worker.job_description,
    }
    if skill_title:
        summary["matched_skill_title"] = skill_title
    if skill_description:
        summary["matched_skill_description"] = skill_description
    return summary


def _llm_rerank_matches(
    job_description: str,
    job_category: str | None,
    rich_matches: list[MatchDetail],
) -> list[MatchDetail]:
    if not rich_matches:
        return rich_matches

    candidates = rich_matches[:MAX_CANDIDATES_FOR_RERANK]
    leftover = rich_matches[MAX_CANDIDATES_FOR_RERANK:]

    candidate_payload = [
        _build_candidate_summary(
            m["worker_profile"], m["score"], m["rank"],
            m.get("matched_skill_title"), m.get("matched_skill_description"),
        )
        for m in candidates
    ]

    prompt = (
        "You are a strict trade-fit filter. Your only job is to decide which workers can "
        "PRIMARILY perform the customer's job — not workers who merely mention related objects.\n\n"
        f"Job category: {job_category or 'unknown'}\n"
        f"Job description: {job_description}\n\n"
        f"Candidates:\n{json.dumps(candidate_payload, indent=2)}\n\n"
        "CRITICAL RULES:\n"
        "1. INCIDENTAL MENTION IS NOT QUALIFICATION.\n"
        "   A worker whose description mentions an object does NOT qualify for jobs centred on that object.\n"
        "   - An ELECTRICIAN who 'connects water heaters' CANNOT install a solar water heater system. "
        "Solar water heater installation is a plumbing or solar trade. The electrical connection is a "
        "minor secondary step that does not make an electrician the right hire.\n"
        "   - An ELECTRICIAN who 'installs air conditioners' CANNOT do HVAC ductwork or refrigerant work.\n"
        "   - A CLEANER who 'cleans pipes' CANNOT do plumbing repairs.\n"
        "   Ask yourself: is this worker's PRIMARY trade the one that performs the CORE of this job? "
        "If no, drop them regardless of vector_score.\n\n"
        "2. USE matched_skill_title / matched_skill_description AS PRIMARY EVIDENCE.\n"
        "   This is the specific capability that caused the worker to surface. If that skill belongs "
        "to a different trade than the job requires, drop the worker.\n\n"
        "3. WHEN IN DOUBT, DROP.\n"
        "   A customer with zero matches will be told no one is available. "
        "A customer matched to the wrong trade wastes everyone's time. Prefer zero over wrong.\n\n"
        "Return ONLY a JSON array of worker_id integers you are keeping, best fit first. "
        "No explanation, no text outside the array."
    )

    try:
        response = _nvidia_client.chat.completions.create(
            model=RERANK_MODEL,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = (response.choices[0].message.content or "").strip()
        raw_text = raw_text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        parsed_ids = json.loads(raw_text)
        ordered_ids = [int(x) for x in parsed_ids if isinstance(x, (int, str)) and str(x).isdigit()]
        logger.info(f"LLM reranker kept {len(ordered_ids)}/{len(candidates)} candidates: {ordered_ids}")
    except Exception as e:
        logger.error(f"LLM reranker failed, falling back to vector order: {e}")
        return rich_matches

    by_worker_id = {int(m["worker_profile"].id): m for m in candidates}
    reranked: list[MatchDetail] = []
    seen_ids: set[int] = set()

    for new_rank, worker_id in enumerate(ordered_ids, start=1):
        match = by_worker_id.get(worker_id)
        if match is None or worker_id in seen_ids:
            continue
        match["rank"] = new_rank
        reranked.append(match)
        seen_ids.add(worker_id)

    if not reranked:
        logger.warning("LLM reranker kept zero candidates — falling back to vector order.")
        return rich_matches

    for i, match in enumerate(leftover, start=len(reranked) + 1):
        match["rank"] = i

    return reranked + leftover


def create_matches_for_job(
    db: Session,
    job_id: int,
    query_vector: list[float],
    customer_location,
    radius_meters: int,
    job_description: str,
    job_category: str | None = None,
) -> MatchingResult:
    logger.info(
        f"[job {job_id}] starting match run — radius_meters={radius_meters}, "
        f"job_category={job_category}, query_vector_len={len(query_vector) if query_vector else 0}"
    )

    db.query(model.JobWorkerMatch).filter(
        model.JobWorkerMatch.job_id == job_id
    ).delete(synchronize_session=False)

    search_results = _search_workers(db, query_vector, customer_location, radius_meters)
    logger.info(f"[job {job_id}] _search_workers returned {len(search_results)} raw candidates")

    search_results = _deduplicate_by_user(search_results)
    logger.info(f"[job {job_id}] {len(search_results)} candidates after per-user dedup")

    rich_matches: list[MatchDetail] = []
    distance_by_worker_id: dict[int, float] = {}
    skill_id_by_worker_id: dict[int, int | None] = {}
    vector_rank = 1

    for (worker, user, distance, skill_id, skill_title, skill_description, skill_type) in search_results:
        score = calculate_match_score(float(distance))
        logger.info(
            f"[job {job_id}] worker_id={worker.id} trade={worker.job_category} "
            f"skill={skill_title!r} ({skill_type}) distance={float(distance):.4f} score={score}"
        )
        if score > SCORE_THRESHOLD:
            rich_matches.append({
                "worker_profile": worker,
                "user": user,
                "score": score,
                "rank": vector_rank,
                "worker_chat_id": worker.worker_chat_id,
                "matched_skill_id": skill_id,
                "matched_skill_title": skill_title,
                "matched_skill_description": skill_description,
            })
            distance_by_worker_id[worker.id] = float(distance)
            skill_id_by_worker_id[worker.id] = skill_id
            vector_rank += 1

    logger.info(f"[job {job_id}] {len(rich_matches)} candidates cleared score threshold")

    rich_matches = _llm_rerank_matches(job_description, job_category, rich_matches)
    logger.info(f"[job {job_id}] {len(rich_matches)} candidates after LLM reranker")

    new_match_records = []
    notifiable_worker_chat_ids = []

    for match in rich_matches:
        worker = match["worker_profile"]
        match_row = model.JobWorkerMatch(
            job_id=job_id,
            worker_id=worker.id,
            match_score=match["score"],
            match_rank=match["rank"],
            semantic_distance=distance_by_worker_id[worker.id],
            matched_skill_id=skill_id_by_worker_id.get(worker.id),
            is_active=True,
            is_interested=False,
            is_selected=False,
            is_rejected=False,
        )
        new_match_records.append(match_row)
        notifiable_worker_chat_ids.append(match["worker_chat_id"])

    if new_match_records:
        db.add_all(new_match_records)
        db.flush()

    return {
        "matches": rich_matches,
        "worker_chat_ids": notifiable_worker_chat_ids,
        "count": len(rich_matches),
    }


def create_matches_for_worker(
    db: Session,
    worker_id: int,
    worker_location,
    radius_meters: int = 60_000,
) -> WorkerMatchingResult:
    logger.info(f"Running reverse matching pipeline for worker_id: {worker_id}")

    db.query(model.JobWorkerMatch).filter(
        model.JobWorkerMatch.worker_id == worker_id
    ).delete(synchronize_session=False)

    has_matchable_skill = db.execute(
        select(model.WorkerSkill.id)
        .where(
            model.WorkerSkill.worker_id == worker_id,
            model.WorkerSkill.embedding.isnot(None),
            model.WorkerSkill.is_active.is_(True),
        )
        .limit(1)
    ).scalar_one_or_none()

    if has_matchable_skill is None:
        logger.warning(f"Worker {worker_id} has no active embedded skills — skipping reverse match.")
        return {"matched_jobs": [], "count": 0}

    distance_expr = model.Job.description_vector.cosine_distance(model.WorkerSkill.embedding)

    best_skill_per_job = (
        select(
            model.Job.id.label("job_id"),
            model.WorkerSkill.id.label("skill_id"),
            model.WorkerSkill.title.label("skill_title"),
            distance_expr.label("distance"),
        )
        .select_from(model.Job)
        .join(model.WorkerSkill, model.WorkerSkill.worker_id == worker_id)
        .where(
            model.WorkerSkill.embedding.isnot(None),
            model.WorkerSkill.is_active.is_(True),
            model.Job.description_vector.isnot(None),
            model.Job.location.isnot(None),
            model.Job.status == "pending",
            func.ST_DWithin(model.Job.location, worker_location, radius_meters),
        )
        .distinct(model.Job.id)
        .order_by(model.Job.id, distance_expr.asc())
        .subquery()
    )

    stmt = (
        select(
            model.Job,
            best_skill_per_job.c.distance,
            best_skill_per_job.c.skill_id,
            best_skill_per_job.c.skill_title,
        )
        .join(best_skill_per_job, best_skill_per_job.c.job_id == model.Job.id)
        .order_by(best_skill_per_job.c.distance.asc())
    )

    search_results = db.execute(stmt).all()

    new_match_records = []
    matched_jobs_payload: list[MatchedJobDetail] = []
    current_rank = 1

    for job, distance, skill_id, skill_title in search_results:
        score = calculate_match_score(float(distance))
        if score > SCORE_THRESHOLD:
            match_row = model.JobWorkerMatch(
                job_id=job.id,
                worker_id=worker_id,
                match_score=score,
                match_rank=current_rank,
                semantic_distance=float(distance),
                matched_skill_id=skill_id,
                is_active=True,
                is_interested=False,
                is_selected=False,
                is_rejected=False,
            )
            new_match_records.append(match_row)
            matched_jobs_payload.append({
                "booking_chat_id": job.booking_chat_id,
                "title": job.title,
                "description": job.description,
                "score": score,
                "rank": current_rank,
                "matched_skill_title": skill_title,
            })
            current_rank += 1

    if new_match_records:
        db.add_all(new_match_records)
        db.flush()

    return {
        "matched_jobs": matched_jobs_payload,
        "count": len(matched_jobs_payload),
    }