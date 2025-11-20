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
        
        # Generate issues and suggestions using diagnostics
        issues = self._identify_issues(parsed_data, ats_diagnostics, {
            "formatting": formatting_score,
            "keywords": keyword_score,
            "structure": structure_score,
            "readability": readability_score
        })
        
        suggestions = self._generate_suggestions(issues)
        
        # Detect visual formatting issues and generate highlights
        issue_detection = self.issue_detector.detect_issues(
            file_path,
            file_type,
            parsed_data
        )
        
        # Combine text-based recommendations with visual recommendations
        all_recommendations = list(set(suggestions + issue_detection["recommendations"]))
        
        return {
            "overall_score": round(overall_score, 2),
            "formatting_score": round(formatting_score, 2),
            "keyword_score": round(keyword_score, 2),
            "structure_score": round(structure_score, 2),
            "readability_score": round(readability_score, 2),
            "ats_text": ats_text,
            "issues": issues,
            "suggestions": all_recommendations,
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
            
            # Penalize for text boxes (separate layers confuse ATS)
            if ats_diagnostics.get("has_text_boxes"):
                score -= 10
            
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
    
    def _identify_issues(
        self, 
        parsed_data: Dict[str, Any], 
        ats_diagnostics: Dict[str, Any],
        scores: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """
        Identify specific issues using data from hybrid parser.
        
        Leverages diagnostics from ATSViewGenerator to provide specific,
        actionable feedback based on actual layout analysis.
        """
        issues = []
        
        # Use specific diagnostics from ATSViewGenerator
        if ats_diagnostics:
            # Images issue
            if ats_diagnostics.get("has_images"):
                issues.append({
                    "category": "formatting",
                    "severity": "high",
                    "message": "Resume contains images that ATS systems cannot read",
                    "detail": "Images, logos, and graphics are invisible to ATS"
                })
            
            # Tables issue
            if ats_diagnostics.get("has_tables"):
                issues.append({
                    "category": "formatting",
                    "severity": "medium",
                    "message": "Resume uses tables which may confuse ATS parsing",
                    "detail": "Tables can cause content to be read in wrong order"
                })
            
            # Headers/footers issue
            if ats_diagnostics.get("has_headers_footers"):
                issues.append({
                    "category": "formatting",
                    "severity": "medium",
                    "message": "Headers or footers detected - ATS may miss this content",
                    "detail": "Contact info in headers/footers is often missed"
                })
            
            # Complex layout issue
            if ats_diagnostics.get("layout_complexity") == "complex":
                issues.append({
                    "category": "formatting",
                    "severity": "high",
                    "message": "Resume has complex layout that reduces ATS compatibility",
                    "detail": f"Multiple fonts and complex formatting detected"
                })
            
            # Include specific warnings from diagnostics
            for warning in ats_diagnostics.get("warnings", []):
                issues.append({
                    "category": "formatting",
                    "severity": "medium",
                    "message": warning
                })
        
        # Fallback: if diagnostics not available or formatting score is low
        elif scores["formatting"] < 70:
            issues.append({
                "category": "formatting",
                "severity": "high",
                "message": "Resume may contain ATS-unfriendly formatting"
            })
        
        # Missing contact info
        if not parsed_data.get("email"):
            issues.append({
                "category": "structure",
                "severity": "critical",
                "message": "Email address is missing"
            })
        
        # Missing skills
        if not parsed_data.get("skills") or len(parsed_data.get("skills", [])) == 0:
            issues.append({
                "category": "keywords",
                "severity": "high",
                "message": "No skills section found"
            })
        
        # Missing experience
        if not parsed_data.get("experience") or len(parsed_data.get("experience", [])) == 0:
            issues.append({
                "category": "structure",
                "severity": "high",
                "message": "No work experience section found"
            })
        
        # Short or missing summary
        if not parsed_data.get("summary"):
            issues.append({
                "category": "readability",
                "severity": "medium",
                "message": "Professional summary is missing"
            })
        
        return issues
    
    def _generate_suggestions(self, issues: List[Dict[str, Any]]) -> List[str]:
        """
        Generate actionable suggestions based on identified issues.
        
        Provides specific, actionable advice based on diagnostics from the hybrid parser.
        """
        suggestions = []
        
        for issue in issues:
            # Image-related suggestions
            if "images" in issue["message"].lower():
                suggestions.append("Remove images, photos, and logos - use text-only formatting")
            
            # Table-related suggestions
            elif "tables" in issue["message"].lower():
                suggestions.append("Replace tables with simple text formatting using line breaks")
            
            # Headers/footers suggestions
            elif "headers" in issue["message"].lower() or "footers" in issue["message"].lower():
                suggestions.append("Move contact information from header/footer to main document body")
            
            # Complex layout suggestions
            elif "complex layout" in issue["message"].lower():
                suggestions.append("Simplify layout: use single column, standard fonts, and consistent formatting")
            
            # Contact info suggestions
            elif "email" in issue["message"].lower():
                suggestions.append("Add your email address prominently at the top of your resume")
            elif "phone" in issue["message"].lower():
                suggestions.append("Include your phone number in the contact section")
            
            # Skills suggestions
            elif "skills" in issue["message"].lower():
                suggestions.append("Add a dedicated Skills section with relevant technical and soft skills")
            
            # Experience suggestions
            elif "experience" in issue["message"].lower():
                suggestions.append("Add your work experience with job titles, companies, dates, and achievements")
            
            # Summary suggestions
            elif "summary" in issue["message"].lower():
                suggestions.append("Add a brief professional summary (2-3 sentences) highlighting your key qualifications")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_suggestions = []
        for suggestion in suggestions:
            if suggestion not in seen:
                seen.add(suggestion)
                unique_suggestions.append(suggestion)
        
        # Add general suggestions if we have fewer than 3
        if len(unique_suggestions) < 3:
            general = [
                "Use standard section headers (Experience, Education, Skills, Summary)",
                "Include action verbs and quantifiable achievements in your experience",
                "Tailor your resume keywords to match the job description"
            ]
            for gen in general:
                if gen not in seen and len(unique_suggestions) < 5:
                    unique_suggestions.append(gen)
        
        return unique_suggestions[:5]  # Limit to top 5 suggestions

