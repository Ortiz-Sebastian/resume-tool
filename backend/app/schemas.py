from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

# User schemas
class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Resume schemas
class ResumeBase(BaseModel):
    filename: str
    file_type: str

class ResumeCreate(ResumeBase):
    pass

class Resume(ResumeBase):
    id: int
    user_id: Optional[int]
    uploaded_at: datetime
    parsed_data: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True

class ResumeUploadResponse(BaseModel):
    id: int
    filename: str
    file_size: int
    file_type: str
    message: str

# ATS Score schemas
class ATSHighlight(BaseModel):
    page: int
    bbox: List[float]
    severity: str  # 'critical', 'high', 'medium', 'low'
    issue_type: str
    message: str
    tooltip: str

class ATSIssueSummary(BaseModel):
    total_issues: int
    critical: int
    high: int
    medium: int
    low: int

class ATSScore(BaseModel):
    overall_score: float  # Changed from int to float (scores can have decimals)
    formatting_score: float  # Changed from int to float
    keyword_score: float  # Changed from int to float
    structure_score: float  # Changed from int to float
    readability_score: float  # Changed from int to float
    issues: List[str]
    suggestions: List[str]
    recommendations: List[str] = []  # Tier 1: Quick, rule-based recommendations
    ats_text: str
    highlights: List[ATSHighlight] = []
    issue_summary: Optional[ATSIssueSummary] = None

# Alias for compatibility
ResumeScore = ATSScore

# Section Comparison schemas (NEW)
class SectionComparison(BaseModel):
    section_name: str  # 'contact_info', 'skills', 'experience', 'education', 'certifications'
    status: str  # 'perfect', 'good', 'issues', 'missing'
    original_count: Optional[int] = None  # e.g., 10 skills in original
    extracted_count: Optional[int] = None  # e.g., 3 skills extracted
    message: str  # "7 skills missing"
    details: Optional[str] = None  # Additional context

class ResumeSummary(BaseModel):
    resume_id: int
    sections: List[SectionComparison]
    overall_status: str  # 'good', 'needs_improvement', 'critical'

# Section Analysis Request (NEW)
class SectionAnalysisRequest(BaseModel):
    resume_id: int
    section: str  # 'skills', 'experience', 'education', 'contact_info'

# Section Analysis Response (NEW)
class SectionAnalysisResponse(BaseModel):
    section: str
    status: str
    formatting_issues: List[str]
    recommendations: List[str]
    highlights: List[ATSHighlight]
    visual_location: Optional[Dict[str, Any]] = None  # Page, bbox of section

# LLM Diagnostic schemas (NEW - User-prompted analysis)
class LLMDiagnosticRequest(BaseModel):
    resume_id: int
    user_prompt: str  # e.g., "I'm missing 5 skills" or "My email isn't showing"

class LLMDiagnosticResponse(BaseModel):
    explanation: str  # Why this happened
    location: Optional[str] = None  # Where to look (description)
    recommendations: List[str]  # How to fix

# Role Match schemas
class RoleMatch(BaseModel):
    role_title: str
    match_score: float
    required_skills: Optional[List[str]] = []
    matched_skills: List[str]
    missing_skills: List[str]
    description: Optional[str] = None

class RoleMatchRequest(BaseModel):
    resume_id: int
    target_roles: Optional[List[str]] = None

class RoleMatchResponse(BaseModel):
    matches: List[RoleMatch]

# Skill Suggestion schemas (DISABLED - for future use)
# class SkillSuggestionRequest(BaseModel):
#     resume_id: int
#     target_role: str

# class SkillSuggestionResponse(BaseModel):
#     suggested_skills: List[str]
#     reasoning: str
