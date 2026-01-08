from typing import Dict, Any, List


class DataValidator:
    """
    Validates the accuracy of extracted resume data.
    
    Checks if extracted data makes sense (e.g., education entries are actual degrees,
    experience entries are actual jobs, not misclassified content).
    """
    
    def validate(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate all extracted data for accuracy.
        
        Args:
            parsed_data: Dictionary containing extracted resume data
        
        Returns:
            Dictionary with validation results for each section
        """
        validation_results = {
            "education": self._validate_education(parsed_data.get("education", [])),
            "experience": self._validate_experience(parsed_data.get("experience", [])),
            "overall": {
                "has_issues": False,
                "total_issues": 0
            }
        }
        
        # Calculate overall stats
        total_issues = 0
        if validation_results["education"]["has_issues"]:
            total_issues += len(validation_results["education"]["issues"])
        if validation_results["experience"]["has_issues"]:
            total_issues += len(validation_results["experience"]["issues"])
        
        validation_results["overall"]["has_issues"] = total_issues > 0
        validation_results["overall"]["total_issues"] = total_issues
        
        return validation_results
    
    def _validate_education(self, education: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate education entries to ensure they look like actual degrees.
        
        Returns:
            Dictionary with 'has_issues' (bool), 'issues' (list), and 'valid_entries' (int)
        """
        issues = []
        valid_entries = 0
        
        if not education:
            return {
                "has_issues": False,
                "issues": [],
                "valid_entries": 0
            }
        
        # Common degree indicators
        degree_indicators = [
            'bachelor', 'master', 'phd', 'doctorate', 'associate', 'certificate',
            'diploma', 'degree', 'bs', 'ba', 'ms', 'ma', 'mba', 'phd', 'dphil',
            'bsc', 'msc', 'b.a', 'b.s', 'm.a', 'm.s', 'a.a', 'a.s', 'b.eng',
            'b.tech', 'm.eng', 'm.tech', 'b.e', 'm.e'
        ]
        
        # Common non-degree words that might be incorrectly extracted
        non_degree_indicators = [
            'high school', 'gpa', 'grade point', 'dean', 'president', 'chairman',
            'member', 'participant', 'volunteer', 'intern', 'internship', 'honors',
            'summa cum laude', 'magna cum laude', 'cum laude'
        ]
        
        for idx, edu in enumerate(education):
            degree = (edu.get("degree") or "").strip()
            institution = (edu.get("institution") or edu.get("organization") or "").strip()
            combined = f"{degree} {institution}".lower()
            
            # Skip if both are empty
            if not degree and not institution:
                issues.append({
                    "entry_index": idx,
                    "entry": edu,
                    "severity": "medium",
                    "message": f"Education entry {idx + 1}: Missing degree and institution",
                    "field": "all"
                })
                continue
            
            # Check if degree field looks like an actual degree
            if degree:
                degree_lower = degree.lower()
                has_degree_indicator = any(indicator in degree_lower for indicator in degree_indicators)
                has_non_degree_indicator = any(indicator in combined for indicator in non_degree_indicators)
                
                # Flag if it contains non-degree indicators but no degree indicators
                if has_non_degree_indicator and not has_degree_indicator:
                    issues.append({
                        "entry_index": idx,
                        "entry": edu,
                        "severity": "high",
                        "message": f'Education entry {idx + 1}: "{degree}" doesn\'t appear to be a degree. May be misclassified content (e.g., GPA, honors, etc.).',
                        "field": "degree"
                    })
                # Flag if very short degree name without institution
                elif len(degree) < 10 and not has_degree_indicator and not institution:
                    issues.append({
                        "entry_index": idx,
                        "entry": edu,
                        "severity": "medium",
                        "message": f'Education entry {idx + 1}: "{degree}" may not be a complete degree name',
                        "field": "degree"
                    })
                elif has_degree_indicator:
                    valid_entries += 1
            else:
                # No degree but has institution - might be okay but less ideal
                if institution:
                    issues.append({
                        "entry_index": idx,
                        "entry": edu,
                        "severity": "low",
                        "message": f"Education entry {idx + 1}: Missing degree name (has institution: {institution})",
                        "field": "degree"
                    })
                valid_entries += 1  # Count as valid if institution exists
            
            # Check if institution field looks reasonable
            if institution and len(institution) < 5:
                issues.append({
                    "entry_index": idx,
                    "entry": edu,
                    "severity": "medium",
                    "message": f'Education entry {idx + 1}: Institution name "{institution}" seems too short',
                    "field": "institution"
                })
        
        return {
            "has_issues": len(issues) > 0,
            "issues": issues,
            "valid_entries": valid_entries,
            "total_entries": len(education)
        }
    
    def _validate_experience(self, experience: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate experience entries to ensure they look like actual jobs.
        
        Returns:
            Dictionary with 'has_issues' (bool), 'issues' (list), and 'valid_entries' (int)
        """
        issues = []
        valid_entries = 0
        
        if not experience:
            return {
                "has_issues": False,
                "issues": [],
                "valid_entries": 0
            }
        
        # Common job title indicators
        job_title_indicators = [
            'engineer', 'developer', 'manager', 'director', 'analyst', 'specialist',
            'coordinator', 'assistant', 'consultant', 'lead', 'senior', 'junior',
            'intern', 'internship', 'associate', 'executive', 'officer', 'supervisor',
            'designer', 'architect', 'scientist', 'researcher', 'developer', 'programmer',
            'administrator', 'technician', 'technologist', 'trainer', 'instructor',
            'coordinator', 'representative', 'agent', 'advisor', 'counselor'
        ]
        
        for idx, exp in enumerate(experience):
            title = (exp.get("title") or exp.get("position") or "").strip()
            company = (exp.get("company") or exp.get("organization") or "").strip()
            description = (exp.get("description") or "").lower()
            
            # Skip if both title and company are empty
            if not title and not company:
                issues.append({
                    "entry_index": idx,
                    "entry": exp,
                    "severity": "high",
                    "message": f"Experience entry {idx + 1}: Missing title and company",
                    "field": "all"
                })
                continue
            
            # Check if title looks like a job title
            if title:
                title_lower = title.lower()
                has_job_indicator = any(indicator in title_lower for indicator in job_title_indicators)
                
                # Check for common non-job patterns
                if 'gpa' in title_lower or 'grade' in title_lower or 'degree' in title_lower:
                    issues.append({
                        "entry_index": idx,
                        "entry": exp,
                        "severity": "high",
                        "message": f'Experience entry {idx + 1}: Title "{title}" appears to be education-related, not work experience. May be misclassified.',
                        "field": "title"
                    })
                # Flag if very short title without company
                elif len(title) < 5 and not company:
                    issues.append({
                        "entry_index": idx,
                        "entry": exp,
                        "severity": "medium",
                        "message": f'Experience entry {idx + 1}: Title "{title}" seems incomplete (very short and no company name)',
                        "field": "title"
                    })
                elif has_job_indicator or company:
                    valid_entries += 1
            else:
                # No title but has company - might be okay but less ideal
                if company:
                    issues.append({
                        "entry_index": idx,
                        "entry": exp,
                        "severity": "low",
                        "message": f"Experience entry {idx + 1}: Missing job title (has company: {company})",
                        "field": "title"
                    })
                    valid_entries += 1
            
            # Check if company field looks reasonable
            if company and len(company) < 3:
                issues.append({
                    "entry_index": idx,
                    "entry": exp,
                    "severity": "medium",
                    "message": f'Experience entry {idx + 1}: Company name "{company}" seems too short',
                    "field": "company"
                })
        
        return {
            "has_issues": len(issues) > 0,
            "issues": issues,
            "valid_entries": valid_entries,
            "total_entries": len(experience)
        }

