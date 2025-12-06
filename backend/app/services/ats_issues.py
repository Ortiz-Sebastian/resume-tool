"""
Structured ATS Issue and Metrics Models

Defines the ATSIssue dataclass for representing formatting issues
and ATSMetrics dataclass for quantitative resume evaluation.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class IssueSeverity(str, Enum):
    """Issue severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueSection(str, Enum):
    """Resume sections where issues can occur"""
    CONTACT = "contact"
    SKILLS = "skills"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    GENERAL = "general"


@dataclass
class ATSIssue:
    """
    Structured representation of an ATS parsing issue.
    
    Detected by business rules (not AI), used for LLM explanation.
    
    Attributes:
        code: Machine-friendly identifier (e.g., "contact_in_header", "skills_in_table")
        severity: Issue severity level
        message: Short human-readable summary
        details: Detailed explanation/context
        page: Page number where issue occurs
        bbox: Bounding box [x0, y0, x1, y1] of affected area
        section: Resume section affected (optional)
        block_indices: Indices into blocks list (optional, for reference)
        location_hint: Human-readable location description (optional)
    """
    code: str
    severity: IssueSeverity
    message: str
    details: str
    page: int
    bbox: Optional[List[float]] = None  # [x0, y0, x1, y1], None for document-wide issues
    section: Optional[IssueSection] = None
    block_indices: List[int] = field(default_factory=list)
    location_hint: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "code": self.code,
            "severity": self.severity.value if isinstance(self.severity, Enum) else self.severity,
            "section": self.section.value if isinstance(self.section, Enum) else self.section,
            "message": self.message,
            "details": self.details,
            "page": self.page,
            "bbox": self.bbox,
            "block_count": len(self.block_indices),
            "location_hint": self.location_hint
        }
    
    def to_highlight_dict(self) -> Dict[str, Any]:
        """Convert to frontend-compatible highlight format (legacy support)"""
        return {
            "page": self.page,
            "bbox": self.bbox,
            "severity": self.severity.value if isinstance(self.severity, Enum) else self.severity,
            "issue_type": self.code,
            "message": self.message,
            "tooltip": self.details
        }
    
    def get_recommendation(self) -> Optional[str]:
        """
        Generate quick, generic recommendation for this issue.
        
        TWO-TIER RECOMMENDATION SYSTEM:
        
        1. RULE-BASED (this method):
           - Fast, generic, deterministic
           - Shown immediately in score summary
           - Example: "Move email from header to body"
           - Use case: Quick overview of what needs fixing
        
        2. AI-BASED (llm_diagnostic.py):
           - Contextual, detailed, personalized
           - Shown on-demand when user asks
           - Example: "Your email 'john@example.com' is at top-right in the 
             header. Move it to line 2 under your name: 'Email: john@example.com'"
           - Use case: Deep diagnostic with specific instructions
        
        This maps issue codes to generic fix actions.
        """
        recommendations = {
            # Contact issues
            "contact_email_in_header_footer": "Move email address from header/footer to main body under your name",
            "contact_phone_in_header_footer": "Move phone number from header/footer to main body under your name",
            "contact_linkedin_not_extracted": "Display LinkedIn URL as plain text, not just as an icon",
            "contact_missing": "Add contact information (email and phone) in the main body under your name",
            
            # Skills issues
            "skills_no_section": "Add a dedicated Skills section with clear header (e.g., 'SKILLS' or 'TECHNICAL SKILLS')",
            "skills_section_unreadable": "Reformat Skills section as simple bullet points - ATS extracted 0 skills",
            "skills_partially_extracted": "Improve Skills section formatting - use simple bullets instead of tables/grids",
            "skills_in_table": "Replace skills table/grid with a simple bullet list for better ATS compatibility",
            "skills_in_sidebar": "Move skills from sidebar to main body in a single-column layout",
            
            # Experience issues
            "experience_not_extracted": "Experience section not readable by ATS - use simple format with clear job titles and dates",
            "experience_no_bullets": "Add bullet points to job descriptions using standard characters (•, -, or *)",
            "experience_incomplete": "Ensure all jobs have clear job title and company name",
            "experience_in_columns": "Use single-column layout for work experience section",
            
            # Education issues
            "education_not_extracted": "Education section not readable by ATS - use clear format with degree and university",
            "education_incomplete": "Ensure all education entries have clear degree and institution names",
            
            # General formatting issues
            "image_content": "Remove images and replace any important content with plain text",
            "scanned_pdf": "Convert scanned/image PDF to text-based PDF by exporting from your original document editor",
            "icon_usage": "Replace icons with text labels for all contact information and links",
            "unmapped_content": "Ensure all important information is in clearly labeled sections (Experience, Education, Skills)",
            
            # Date format issues
            "date_format_apostrophe_year": "Replace abbreviated years with full 4-digit years (e.g., 'Jan '21' → 'Jan 2021')",
            "date_format_year_only": "Add months to year-only dates (e.g., '2021 - 2023' → 'Jan 2021 - Mar 2023')",
            "date_format_single_digit_month": "Use two-digit months or month names (e.g., '1/2021' → '01/2021' or 'Jan 2021')",
            "date_format_full_date_format": "Remove days from dates, use month and year only (e.g., '01/15/2021' → 'Jan 2021')",
            "date_format_day_included": "Remove days from dates, use month and year only (e.g., 'Jan 15, 2021' → 'Jan 2021')",
            
            # Font issues
            "decorative_font": "Replace decorative fonts with ATS-friendly fonts like Arial, Calibri, or Georgia",
            "uncommon_font": "Use ATS-friendly fonts: Arial, Calibri, Georgia, Garamond, Helvetica, or Times New Roman",
            "too_many_fonts": "Use only 1-2 fonts maximum throughout your resume for consistency",
            
            # Layout issues
            "excessive_header_footer": "Move important content from headers/footers to main body",
            "extensive_table_usage": "Reduce use of tables - use simple bullet lists instead",
            "multi_column_layout": "Use single-column layout for better ATS readability",
            
            # Complexity issues (new metrics-based)
            "very_complex_layout": "Simplify to single-column layout, use 1-2 standard fonts, remove all tables and images",
            "complex_layout": "Reduce formatting complexity: minimize tables, images, and font variations",
            "moderate_complexity": "Good overall - consider minor simplifications for optimal ATS compatibility",
        }
        
        return recommendations.get(self.code)


# ============================================================================
# ATS METRICS SYSTEM
# ============================================================================

class ComplexityLevel(str, Enum):
    """Layout complexity levels"""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


class MetricCategory(str, Enum):
    """Categories of metrics we track"""
    LAYOUT = "layout"
    CONTENT = "content"
    FORMATTING = "formatting"
    STRUCTURE = "structure"


@dataclass
class ComplexityMetric:
    """
    Detailed complexity analysis with score and label.
    
    Score: 0-100 (higher = more complex/worse for ATS)
    Label: human-readable complexity level
    
    Factors considered:
    - Font count and variety
    - Image presence and count
    - Table usage
    - Multi-column layout
    - Text boxes and shapes
    - Headers/footers usage
    """
    score: float  # 0-100 (0=simple, 100=very complex)
    label: ComplexityLevel
    font_count: int
    has_images: bool
    image_count: int
    has_tables: bool
    table_count: int
    has_multi_column: bool
    has_headers_footers: bool
    contributing_factors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "score": round(self.score, 2),
            "label": self.label.value if isinstance(self.label, Enum) else self.label,
            "font_count": self.font_count,
            "has_images": self.has_images,
            "image_count": self.image_count,
            "has_tables": self.has_tables,
            "table_count": self.table_count,
            "has_multi_column": self.has_multi_column,
            "has_headers_footers": self.has_headers_footers,
            "contributing_factors": self.contributing_factors
        }


@dataclass
class ContentCoverageMetric:
    """
    Measures how much visual content was successfully parsed by ATS.
    
    Score: 0-100 (higher = better extraction)
    """
    score: float  # 0-100 (0=nothing extracted, 100=everything extracted)
    total_blocks: int
    mapped_blocks: int
    unmapped_blocks: int
    coverage_percentage: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": round(self.score, 2),
            "total_blocks": self.total_blocks,
            "mapped_blocks": self.mapped_blocks,
            "unmapped_blocks": self.unmapped_blocks,
            "coverage_percentage": round(self.coverage_percentage, 2)
        }


@dataclass
class StructureMetric:
    """
    Measures presence and quality of standard resume sections.
    
    Score: 0-100 (higher = better structure)
    """
    score: float  # 0-100
    has_contact: bool
    has_experience: bool
    has_education: bool
    has_skills: bool
    contact_complete: bool  # Has both email and phone
    experience_count: int
    education_count: int
    skill_count: int
    missing_sections: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": round(self.score, 2),
            "has_contact": self.has_contact,
            "has_experience": self.has_experience,
            "has_education": self.has_education,
            "has_skills": self.has_skills,
            "contact_complete": self.contact_complete,
            "experience_count": self.experience_count,
            "education_count": self.education_count,
            "skill_count": self.skill_count,
            "missing_sections": self.missing_sections
        }


@dataclass
class ATSMetrics:
    """
    Complete metrics package for resume ATS compatibility evaluation.
    
    Provides quantitative measurements separate from issues.
    Can be used for scoring, analytics, and trend tracking.
    """
    complexity: ComplexityMetric
    content_coverage: ContentCoverageMetric
    structure: StructureMetric
    overall_score: float  # Weighted combination of all metrics
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "overall_score": round(self.overall_score, 2),
            "complexity": self.complexity.to_dict(),
            "content_coverage": self.content_coverage.to_dict(),
            "structure": self.structure.to_dict()
        }
    
    def get_summary(self) -> Dict[str, str]:
        """Get human-readable summary of key metrics"""
        return {
            "complexity": f"{self.complexity.label.value} ({self.complexity.score}/100)",
            "content_coverage": f"{self.content_coverage.coverage_percentage}% extracted",
            "structure": f"{len([s for s in [self.structure.has_contact, self.structure.has_experience, self.structure.has_education, self.structure.has_skills] if s])}/4 core sections present",
            "overall": f"{self.overall_score}/100"
        }


# ============================================================================
# METRICS COMPUTATION FUNCTIONS
# ============================================================================

def compute_secondary_column_ratio(blocks: List[Dict[str, Any]]) -> float:
    """
    Compute the ratio of content in secondary columns (columns 2+).
    
    Args:
        blocks: List of text blocks with 'column' and 'text' attributes
    
    Returns:
        Float between 0.0 and 1.0:
        - 0.0 = all content in column 1 (primary)
        - 0.3 = 30% in secondary columns
        - 1.0 = all content in secondary columns
    
    Example:
        If resume has 1000 chars in column 1 and 500 chars in column 2:
        ratio = 1 - (1000/1500) = 1 - 0.667 = 0.333 (33.3% in secondary)
    """
    if not blocks:
        return 0.0
    
    column_char_counts = {}
    for block in blocks:
        col = block.get('column', 1)
        column_char_counts[col] = column_char_counts.get(col, 0) + len(block.get('text', ''))
    
    total_chars = sum(column_char_counts.values())
    if total_chars == 0:
        return 0.0
    
    primary_column_chars = column_char_counts.get(1, 0)
    secondary_ratio = 1 - (primary_column_chars / total_chars)
    
    return secondary_ratio


def compute_complexity_metric(
    font_count: int,
    has_images: bool,
    image_count: int,
    has_tables: bool,
    table_count: int,
    has_multi_column: bool,
    has_headers_footers: bool,
    secondary_column_ratio: float = 0.0
) -> ComplexityMetric:
    """
    Compute complexity score and label based on multiple layout factors.
    
    Scoring System (0-100, higher = more complex/worse):
    - Base score starts at 0 (perfect)
    - Each complexity factor adds penalty points
    - Final score determines label
    
    Penalty Points:
    - Fonts: 
        * 0-2 fonts: 0 points
        * 3-4 fonts: +10 points
        * 5-6 fonts: +20 points
        * 7+ fonts: +30 points
    - Images: +15 points base, +2 per additional image
    - Tables: +15 points base, +3 per additional table
    - Multi-column: +20 points base, +up to 20 more based on secondary_column_ratio
    - Headers/footers: +10 points
    
    Labels:
    - 0-20: Simple
    - 21-40: Moderate
    - 41-70: Complex
    - 71+: Very Complex
    
    Args:
        font_count: Number of unique fonts used
        has_images: Whether images are present
        image_count: Total number of images
        has_tables: Whether tables are present
        table_count: Total number of tables detected
        has_multi_column: Whether multi-column layout is used
        has_headers_footers: Whether headers/footers contain content
        secondary_column_ratio: Ratio of content in secondary columns (0.0-1.0)
            - 0.0 = all content in primary column
            - 0.3 = 30% in secondary columns (minor sidebar)
            - 0.5 = 50% in secondary columns (major layout issue)
    
    Returns:
        ComplexityMetric object with score, label, and contributing factors
    """
    score = 0.0
    factors = []
    
    # Image complexity
    if has_images:
        score += 15
        score += min((image_count - 1) * 2, 10)  # Cap additional penalty at 10
        if image_count == 1:
            factors.append("Contains 1 image")
        else:
            factors.append(f"Contains {image_count} images")
    
    # Table complexity
    if has_tables:
        score += 15
        score += min((table_count - 1) * 3, 15)  # Cap additional penalty at 15
        if table_count == 1:
            factors.append("Uses table layout")
        else:
            factors.append(f"Uses {table_count} tables")
    
    # Multi-column penalty (weighted by how much content is in secondary columns)
    if has_multi_column:
        base_penalty = 20
        # Additional penalty based on how much content is in secondary columns
        # If 50%+ is in secondary columns, it's a major issue
        ratio_penalty = secondary_column_ratio * 20  # Up to +20 more points
        total_column_penalty = base_penalty + ratio_penalty
        score += total_column_penalty
        
        if secondary_column_ratio > 0.3:
            # Significant content in secondary columns
            factors.append(f"Multi-column layout with {secondary_column_ratio*100:.0f}% content in secondary columns")
        else:
            # Minor sidebar
            factors.append("Multi-column layout detected")
    
    # Headers/footers penalty
    if has_headers_footers:
        score += 10
        factors.append("Has headers or footers with content")
    
    # Cap score at 100
    score = min(score, 100)
    
    # Determine label based on score
    if score <= 20:
        label = ComplexityLevel.SIMPLE
    elif score <= 40:
        label = ComplexityLevel.MODERATE
    elif score <= 70:
        label = ComplexityLevel.COMPLEX
    else:
        label = ComplexityLevel.VERY_COMPLEX
    
    return ComplexityMetric(
        score=score,
        label=label,
        font_count=font_count,
        has_images=has_images,
        image_count=image_count,
        has_tables=has_tables,
        table_count=table_count,
        has_multi_column=has_multi_column,
        has_headers_footers=has_headers_footers,
        contributing_factors=factors
    )


def compute_content_coverage_metric(
    total_blocks: int,
    mapped_blocks: int
) -> ContentCoverageMetric:
    """
    Compute how much content was successfully extracted by ATS.
    
    Score: 0-100 (higher = better)
    Based on percentage of visual blocks that map to parsed data.
    
    Args:
        total_blocks: Total number of text blocks in visual layout
        mapped_blocks: Number of blocks that map to parsed data
    
    Returns:
        ContentCoverageMetric object
    """
    unmapped = total_blocks - mapped_blocks
    coverage_pct = (mapped_blocks / total_blocks * 100) if total_blocks > 0 else 0
    
    # Score is directly the coverage percentage
    score = coverage_pct
    
    return ContentCoverageMetric(
        score=score,
        total_blocks=total_blocks,
        mapped_blocks=mapped_blocks,
        unmapped_blocks=unmapped,
        coverage_percentage=coverage_pct
    )


def compute_structure_metric(parsed_data: Dict[str, Any]) -> StructureMetric:
    """
    Compute structure quality based on presence of standard resume sections.
    
    Score: 0-100 (higher = better)
    
    Scoring:
    - Has contact info: +25 points
    - Contact is complete (email + phone): +5 bonus
    - Has experience: +25 points
    - Has education: +20 points
    - Has skills: +20 points
    - Additional bonuses for quantity:
        * Each experience entry (max +5)
        * Each education entry (max +5)
        * Each skill (max +5)
    
    Args:
        parsed_data: Parsed resume data dictionary
    
    Returns:
        StructureMetric object
    """
    score = 0.0
    missing = []
    
    # Contact info
    contact = parsed_data.get("contact_info", {})
    has_contact = bool(contact.get("email") or contact.get("phone"))
    contact_complete = bool(contact.get("email") and contact.get("phone"))
    
    if has_contact:
        score += 25
        if contact_complete:
            score += 5
    else:
        missing.append("contact information")
    
    # Experience
    experience = parsed_data.get("experience", [])
    exp_count = len(experience) if isinstance(experience, list) else 0
    has_experience = exp_count > 0
    
    if has_experience:
        score += 25
        # Bonus for multiple entries
        score += min(exp_count * 1, 5)
    else:
        missing.append("work experience")
    
    # Education
    education = parsed_data.get("education", [])
    edu_count = len(education) if isinstance(education, list) else 0
    has_education = edu_count > 0
    
    if has_education:
        score += 20
        # Bonus for multiple entries
        score += min(edu_count * 1, 5)
    else:
        missing.append("education")
    
    # Skills
    skills = parsed_data.get("skills", [])
    skill_count = len(skills) if isinstance(skills, list) else 0
    has_skills = skill_count > 0
    
    if has_skills:
        score += 20
        # Bonus for multiple skills
        score += min(skill_count * 0.5, 5)
    else:
        missing.append("skills")
    
    # Cap at 100
    score = min(score, 100)
    
    return StructureMetric(
        score=score,
        has_contact=has_contact,
        has_experience=has_experience,
        has_education=has_education,
        has_skills=has_skills,
        contact_complete=contact_complete,
        experience_count=exp_count,
        education_count=edu_count,
        skill_count=skill_count,
        missing_sections=missing
    )


def compute_ats_metrics(
    ats_diagnostics: Dict[str, Any],
    parsed_data: Dict[str, Any],
    total_blocks: int,
    mapped_blocks: int
) -> ATSMetrics:
    """
    Compute complete ATS metrics package.
    
    This is the main entry point for metrics computation.
    
    Args:
        ats_diagnostics: Layout diagnostics from ATSViewGenerator
        parsed_data: Parsed resume data
        total_blocks: Total visual blocks
        mapped_blocks: Successfully mapped blocks
    
    Returns:
        ATSMetrics object with all computed metrics
    """
    # Compute complexity
    complexity = compute_complexity_metric(
        font_count=ats_diagnostics.get("font_count", 0),
        has_images=ats_diagnostics.get("has_images", False),
        image_count=ats_diagnostics.get("image_count", 0),
        has_tables=ats_diagnostics.get("has_tables", False),
        table_count=ats_diagnostics.get("table_count", 0),
        has_multi_column=ats_diagnostics.get("has_multi_column", False),
        has_headers_footers=ats_diagnostics.get("has_headers_footers", False),
        secondary_column_ratio=ats_diagnostics.get("secondary_column_ratio", 0.0)
    )
    
    # Compute content coverage
    content_coverage = compute_content_coverage_metric(
        total_blocks=total_blocks,
        mapped_blocks=mapped_blocks
    )
    
    # Compute structure
    structure = compute_structure_metric(parsed_data)
    
    # Compute overall score as weighted average
    # Lower complexity is better, so invert it (100 - complexity.score)
    # Higher coverage and structure are better
    weights = {
        "complexity": 0.30,  # 30% - inverted (simpler = better)
        "coverage": 0.35,    # 35% - higher = better
        "structure": 0.35    # 35% - higher = better
    }
    
    overall = (
        (100 - complexity.score) * weights["complexity"] +
        content_coverage.score * weights["coverage"] +
        structure.score * weights["structure"]
    )
    
    return ATSMetrics(
        complexity=complexity,
        content_coverage=content_coverage,
        structure=structure,
        overall_score=overall
    )
