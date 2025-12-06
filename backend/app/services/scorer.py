from typing import Dict, Any, List
from app.services.ats_issue_detector import ATSIssueDetector


class ResumeScorer:
    """
    Resume ATS Scorer - Uses data from hybrid parser architecture.
    
    The parser provides:
    - Structured data (from Textkernel or spaCy)
    - ATS text view (always from PyMuPDF via ATSViewGenerator)
    - Layout diagnostics (always from PyMuPDF via ATSViewGenerator)
    
    This scorer leverages those pre-computed values and detects visual formatting issues.
    """
    
    def __init__(self):
        self.weights = {
            "formatting": 0.25,
            "keywords": 0.25,
            "structure": 0.30,
            "readability": 0.20
        }
        self.issue_detector = ATSIssueDetector()
    
    def score(self, file_path: str, file_type: str, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate comprehensive ATS score using hybrid parser data.
        
        Args:
            file_path: Path to resume file
            file_type: File extension (.pdf, .docx)
            parsed_data: Data from ResumeParser including ats_text and ats_diagnostics
        
        Returns:
            Dictionary with scores, issues, suggestions, and visual highlights
        """
        
        # Get ATS text view (now from parser, not generated here)
        ats_text = parsed_data.get("ats_text", "")
        
        # Get diagnostics (now from ATSViewGenerator via parser)
        ats_diagnostics = parsed_data.get("ats_diagnostics", {})
        
        # Calculate individual scores using diagnostics
        formatting_score = self._score_formatting(parsed_data, ats_diagnostics)
        keyword_score = self._score_keywords(parsed_data)
        structure_score = self._score_structure(parsed_data)
        readability_score = self._score_readability(parsed_data)
        
        # Calculate overall score
        overall_score = (
            formatting_score * self.weights["formatting"] +
            keyword_score * self.weights["keywords"] +
            structure_score * self.weights["structure"] +
            readability_score * self.weights["readability"]
        )
        
        # ALL issue detection now happens in ats_issue_detector.py (single source of truth)
        issue_detection = self.issue_detector.detect_issues(
            file_path,
            file_type,
            parsed_data,
            ats_diagnostics  # Pass diagnostics for comprehensive detection
        )
        
        # Extract issues and recommendations from the unified detector
        issues = issue_detection.get("issues", [])
        recommendations = issue_detection.get("recommendations", [])
        
        return {
            "overall_score": round(overall_score, 2),
            "formatting_score": round(formatting_score, 2),
            "keyword_score": round(keyword_score, 2),
            "structure_score": round(structure_score, 2),
            "readability_score": round(readability_score, 2),
            "ats_text": ats_text,
            "issues": issues,  # From unified detector
            "suggestions": recommendations,  # Legacy field
            "recommendations": recommendations,  # Tier 1: Quick fixes
            "highlights": issue_detection["highlights"],
            "issue_summary": issue_detection["summary"]
        }
    
    def _score_formatting(self, parsed_data: Dict[str, Any], ats_diagnostics: Dict[str, Any]) -> float:
        """
        Score formatting based on ATS compatibility using diagnostics from ATSViewGenerator.
        
        This replaces the old approach of re-parsing the PDF. Now we use the diagnostics
        that were already computed by ATSViewGenerator during parsing.
        """
        score = 100.0
        
        # Use diagnostics from ATSViewGenerator (part of hybrid parser)
        if ats_diagnostics:
            # Penalize for images (ATS cannot read them)
            if ats_diagnostics.get("has_images"):
                score -= 15
            
            # Penalize for tables (can confuse ATS)
            if ats_diagnostics.get("has_tables"):
                score -= 10
            
            # Penalize for headers/footers (ATS may miss content)
            if ats_diagnostics.get("has_headers_footers"):
                score -= 5
            
            # Penalize based on layout complexity
            complexity = ats_diagnostics.get("layout_complexity", "simple")
            if complexity == "complex":
                score -= 15
            elif complexity == "moderate":
                score -= 5
        
        # Check for contact information
        if not parsed_data.get("email"):
            score -= 15
        if not parsed_data.get("phone"):
            score -= 10
        
        return max(0, min(100, score))
    
    def _score_keywords(self, parsed_data: Dict[str, Any]) -> float:
        """Score based on keyword presence and density"""
        score = 0.0
        
        # Skills section present and populated
        skills = parsed_data.get("skills", [])
        if skills:
            score += 40
            # More skills = better (up to a point)
            score += min(30, len(skills) * 2)
        
        # Experience section present
        experience = parsed_data.get("experience", [])
        if experience:
            score += 30
        
        return min(100, score)
    
    def _score_structure(self, parsed_data: Dict[str, Any]) -> float:
        """Score resume structure"""
        score = 0.0
        
        # Check for essential sections
        if parsed_data.get("name"):
            score += 10
        if parsed_data.get("summary"):
            score += 15
        if parsed_data.get("skills"):
            score += 20
        if parsed_data.get("experience"):
            score += 30
        if parsed_data.get("education"):
            score += 20
        if parsed_data.get("email") or parsed_data.get("phone"):
            score += 5
        
        return min(100, score)
    
    def _score_readability(self, parsed_data: Dict[str, Any]) -> float:
        """Score readability and clarity"""
        score = 100.0
        
        # Check summary length
        summary = parsed_data.get("summary", "")
        if summary:
            words = len(summary.split())
            if words < 20:
                score -= 10
            elif words > 100:
                score -= 10
        
        # Check experience descriptions
        experience = parsed_data.get("experience", [])
        for exp in experience:
            desc = exp.get("description", "")
            if len(desc) < 50:
                score -= 5
        
        return max(0, score)
    
    # Note: Issue detection moved to ats_issue_detector.py (single source of truth)

