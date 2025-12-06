from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
import os
import uuid

from app.database import get_db
from app.schemas import (
    ResumeUploadResponse, ResumeScore, RoleMatchResponse,
    ResumeSummary, SectionAnalysisRequest, SectionAnalysisResponse,
    LLMDiagnosticRequest, LLMDiagnosticResponse,
    # TODO: Re-enable for later development
    # SkillSuggestionRequest, SkillSuggestionResponse
)
from app.models import Resume, User
from app.config import settings
from app.services.parser import ResumeParser, get_resume_parser
from app.services.scorer import ResumeScorer
from app.services.role_matcher import RoleMatcher
from app.services.section_analyzer import SectionAnalyzer
from app.services.llm_diagnostic import LLMDiagnostic, prepare_diagnostic_data
from app.services.ats_issue_detector import ATSIssueDetector
# TODO: Re-enable for later development
# from app.services.skill_suggester import SkillSuggester

router = APIRouter()


@router.get("/parser/info")
async def get_parser_info():
    """
    Get information about the configured resume parser.
    Shows which parser is active (Textkernel or spaCy) and availability.
    """
    parser = get_resume_parser()
    return parser.get_parser_info()


@router.post("/parse", response_model=ResumeUploadResponse)
async def parse_resume(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Upload and parse a resume (PDF or DOCX)
    """
    # Validate file type
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file_ext} not allowed. Allowed types: {settings.allowed_extensions}"
        )
    
    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(settings.upload_dir, unique_filename)
    
    # Save file
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Create resume record
    # For now, user_id is None (implement proper auth later)
    resume = Resume(
        user_id=None,
        filename=file.filename,
        file_path=file_path,
        file_type=file_ext.replace(".", ""),
        file_size=len(content)
    )
    
    db.add(resume)
    db.commit()
    db.refresh(resume)
    
    # Parse resume in background
    if background_tasks:
        background_tasks.add_task(parse_resume_task, resume.id, file_path, file_ext)
    
    return ResumeUploadResponse(
        id=resume.id,
        filename=file.filename,
        file_size=len(content),
        file_type=file_ext.replace(".", ""),
        message="Resume uploaded successfully. Parsing in progress."
    )


def parse_resume_task(resume_id: int, file_path: str, file_type: str):
    """Background task to parse resume"""
    from app.database import SessionLocal
    import traceback
    
    db = SessionLocal()
    try:
        parser = ResumeParser()
        parsed_data = parser.parse(file_path, file_type)
        
        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        if resume:
            resume.parsed_data = parsed_data
            db.commit()
    except Exception as e:
        print(f"Error parsing resume {resume_id}: {str(e)}")
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


@router.get("/resume/{resume_id}/parsed")
async def get_parsed_resume(resume_id: int, db: Session = Depends(get_db)):
    """
    Get parsed resume data
    """
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    if not resume.parsed_data:
        raise HTTPException(status_code=400, detail="Resume not yet parsed")
    
    return {
        "resume_id": resume.id,
        "filename": resume.filename,
        "parsed_data": resume.parsed_data,
        "ats_text": resume.ats_text
    }


@router.get("/resume/{resume_id}/file")
async def get_resume_file(resume_id: int, db: Session = Depends(get_db)):
    """
    Get the original resume file (PDF/DOCX)
    """
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    if not os.path.exists(resume.file_path):
        raise HTTPException(status_code=404, detail="Resume file not found")
    
    return FileResponse(
        resume.file_path,
        media_type='application/pdf' if resume.file_type == 'pdf' else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        filename=resume.filename
    )


@router.post("/score/{resume_id}", response_model=ResumeScore)
async def score_resume(resume_id: int, db: Session = Depends(get_db)):
    """
    Calculate ATS compatibility score for a resume
    """
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    if not resume.parsed_data:
        raise HTTPException(status_code=400, detail="Resume must be parsed first")
    
    # Score the resume (pass file_type for ATS issue detection)
    scorer = ResumeScorer()
    file_type = f".{resume.file_type}" if not resume.file_type.startswith(".") else resume.file_type
    score_result = scorer.score(resume.file_path, file_type, resume.parsed_data)
    
    # Update resume with score
    resume.ats_score = score_result["overall_score"]
    resume.ats_text = score_result["ats_text"]
    resume.score_details = score_result
    db.commit()
    
    # Return the score result directly (ResumeScore = ATSScore)
    return score_result


@router.get("/roles/{resume_id}", response_model=RoleMatchResponse)
async def match_roles(resume_id: int, top_k: int = 5, db: Session = Depends(get_db)):
    """
    Find best matching job roles for a resume
    """
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    if not resume.parsed_data:
        raise HTTPException(status_code=400, detail="Resume must be parsed first")
    
    # Match roles
    matcher = RoleMatcher()
    matches = matcher.match_roles(resume.parsed_data, top_k=top_k)
    
    return RoleMatchResponse(
        resume_id=resume.id,
        matches=matches
    )


# TODO: SKILL SUGGESTIONS - Disabled for now, re-enable for later development
# @router.post("/suggest", response_model=SkillSuggestionResponse)
# async def suggest_skills(
#     request: SkillSuggestionRequest,
#     db: Session = Depends(get_db)
# ):
#     """
#     Get skill suggestions for a target role
#     """
#     resume = db.query(Resume).filter(Resume.id == request.resume_id).first()
#     if not resume:
#         raise HTTPException(status_code=404, detail="Resume not found")
#     
#     if not resume.parsed_data:
#         raise HTTPException(status_code=400, detail="Resume must be parsed first")
#     
#     # Get suggestions
#     suggester = SkillSuggester()
#     suggestions = suggester.suggest_skills(
#         resume.parsed_data,
#         request.target_role
#     )
#     
#     return suggestions


@router.get("/resumes")
async def list_resumes(db: Session = Depends(get_db)):
    """
    List all resumes (implement pagination later)
    """
    resumes = db.query(Resume).order_by(Resume.created_at.desc()).limit(50).all()
    return {
        "resumes": [
            {
                "id": r.id,
                "filename": r.filename,
                "file_type": r.file_type,
                "ats_score": r.ats_score,
                "created_at": r.created_at
            }
            for r in resumes
        ]
    }


@router.get("/resume/{resume_id}/summary", response_model=ResumeSummary)
async def get_resume_summary(resume_id: int, db: Session = Depends(get_db)):
    """
    Get high-level summary comparing original resume vs ATS extraction.
    Shows which sections have issues without detailed analysis.
    """
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    if not resume.parsed_data:
        raise HTTPException(status_code=400, detail="Resume must be parsed first")
    
    # Get file path (resume.file_path already contains full path)
    file_path = resume.file_path
    
    # Generate summary
    analyzer = SectionAnalyzer()
    summary = analyzer.generate_summary(
        file_path,
        resume.file_type,
        resume.parsed_data
    )
    
    return {
        "resume_id": resume_id,
        **summary
    }


@router.post("/analyze-section", response_model=SectionAnalysisResponse)
async def analyze_section(request: SectionAnalysisRequest, db: Session = Depends(get_db)):
    """
    Perform deep analysis on a specific resume section.
    Returns formatting issues, recommendations, and visual highlights.
    """
    resume = db.query(Resume).filter(Resume.id == request.resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    if not resume.parsed_data:
        raise HTTPException(status_code=400, detail="Resume must be parsed first")
    
    # Validate section
    valid_sections = ['skills', 'experience', 'education', 'contact_info']
    if request.section not in valid_sections:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid section. Must be one of: {valid_sections}"
        )
    
    # Get file path (resume.file_path already contains full path)
    file_path = resume.file_path
    
    # Analyze section
    analyzer = SectionAnalyzer()
    analysis = analyzer.analyze_section(
        file_path,
        resume.file_type,
        resume.parsed_data,
        request.section
    )
    
    return analysis


@router.post("/llm-diagnostic", response_model=LLMDiagnosticResponse)
async def llm_diagnostic(request: LLMDiagnosticRequest, db: Session = Depends(get_db)):
    """
    Get AI-powered explanation for ATS issues based on user's observation.
    User describes what they see wrong, LLM explains why and how to fix.
    """
    resume = db.query(Resume).filter(Resume.id == request.resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    if not resume.parsed_data:
        raise HTTPException(status_code=400, detail="Resume must be parsed first")
    
    # Get file path
    file_path = resume.file_path
    
    # Extract blocks for analysis
    detector = ATSIssueDetector()
    blocks = detector._extract_blocks_with_metadata(file_path)
    
    # Get ATS diagnostics (if available) - we can generate it or it might be in parsed_data
    ats_diagnostics = None
    if resume.parsed_data and 'ats_diagnostics' in resume.parsed_data:
        ats_diagnostics = resume.parsed_data.get('ats_diagnostics')
    else:
        # Generate diagnostics if not available
        from app.services.ats_view_generator import ATSViewGenerator
        view_gen = ATSViewGenerator()
        diagnostics_result = view_gen.generate_ats_view(file_path, resume.file_type)
        ats_diagnostics = diagnostics_result.get('diagnostics')
    
    # Prepare condensed diagnostic data
    diagnostic_data = prepare_diagnostic_data(
        resume.parsed_data, 
        blocks, 
        file_path=file_path,
        ats_diagnostics=ats_diagnostics
    )
    
    # Get LLM explanation (issues already detected by rules)
    llm = LLMDiagnostic()
    result = llm.explain_issues(
        user_prompt=request.user_prompt,
        ats_extracted=diagnostic_data['ats_extracted'],
        detected_issues=diagnostic_data['detected_issues'],
        block_summaries=diagnostic_data['block_summaries']
    )
    
    return result

