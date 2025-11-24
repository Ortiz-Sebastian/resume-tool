"""
Structured ATS Issue Model

Defines the ATSIssue dataclass for representing formatting issues
detected by rule-based detectors.
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
            "floating_text_box": "Replace floating text boxes with standard left-aligned text",
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
        }
        
        return recommendations.get(self.code)
