from celery import Celery
from app.config import settings

# Create Celery app
celery_app = Celery(
    "resume_tool",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    worker_prefetch_multiplier=1,
)


@celery_app.task(name="parse_resume")
def parse_resume_task(resume_id: int, file_path: str, file_type: str):
    """Celery task for parsing resumes"""
    from app.services.parser import ResumeParser
    from app.database import SessionLocal
    from app.models import Resume
    
    parser = ResumeParser()
    parsed_data = parser.parse(file_path, file_type)
    
    # Update resume in database
    db = SessionLocal()
    try:
        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        if resume:
            resume.parsed_data = parsed_data
            db.commit()
    finally:
        db.close()
    
    return {"status": "completed", "resume_id": resume_id}


@celery_app.task(name="score_resume")
def score_resume_task(resume_id: int):
    """Celery task for scoring resumes"""
    from app.services.scorer import ResumeScorer
    from app.database import SessionLocal
    from app.models import Resume
    
    db = SessionLocal()
    try:
        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        if not resume or not resume.parsed_data:
            return {"status": "error", "message": "Resume not found or not parsed"}
        
        scorer = ResumeScorer()
        score_result = scorer.score(resume.file_path, resume.parsed_data)
        
        resume.ats_score = score_result["overall_score"]
        resume.ats_text = score_result["ats_text"]
        resume.score_details = score_result
        db.commit()
        
        return {"status": "completed", "resume_id": resume_id, "score": score_result["overall_score"]}
    finally:
        db.close()


@celery_app.task(name="match_roles")
def match_roles_task(resume_id: int, top_k: int = 5):
    """Celery task for role matching"""
    from app.services.role_matcher import RoleMatcher
    from app.database import SessionLocal
    from app.models import Resume, RoleMatch
    
    db = SessionLocal()
    try:
        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        if not resume or not resume.parsed_data:
            return {"status": "error", "message": "Resume not found or not parsed"}
        
        matcher = RoleMatcher()
        matches = matcher.match_roles(resume.parsed_data, top_k=top_k)
        
        # Save matches to database
        for match in matches:
            role_match = RoleMatch(
                resume_id=resume_id,
                role_title=match["role_title"],
                role_description=match["role_description"],
                match_score=match["match_score"],
                matched_skills=match["matched_skills"],
                missing_skills=match["missing_skills"],
                suggestions=match["suggestions"]
            )
            db.add(role_match)
        
        db.commit()
        
        return {"status": "completed", "resume_id": resume_id, "matches_count": len(matches)}
    finally:
        db.close()

