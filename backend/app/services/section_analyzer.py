"""
Section Analyzer - Compares original resume vs ATS extraction and provides targeted analysis.

This service implements the hybrid approach:
1. Generate high-level summary comparing original vs extracted
2. Provide targeted deep-dive analysis for specific sections
"""

from typing import Dict, Any, List
import fitz  # PyMuPDF
import re


class SectionAnalyzer:
    """Analyzes specific resume sections on-demand"""
    
    def __init__(self):
        pass
    
    def generate_summary(
        self,
        file_path: str,
        file_type: str,
        parsed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate high-level comparison of original resume vs ATS extraction.
        Returns status for each section without detailed analysis.
        """
        sections = []
        overall_issues = 0
        
        # 1. Contact Info
        contact_status = self._check_contact_completeness(parsed_data)
        sections.append(contact_status)
        if contact_status['status'] not in ['perfect', 'good']:
            overall_issues += 1
        
        # 2. Skills
        skills_status = self._check_skills_completeness(parsed_data)
        sections.append(skills_status)
        if skills_status['status'] not in ['perfect', 'good']:
            overall_issues += 1
        
        # 3. Experience
        experience_status = self._check_experience_completeness(parsed_data)
        sections.append(experience_status)
        if experience_status['status'] not in ['perfect', 'good']:
            overall_issues += 1
        
        # 4. Education
        education_status = self._check_education_completeness(parsed_data)
        sections.append(education_status)
        if education_status['status'] not in ['perfect', 'good']:
            overall_issues += 1
        
        # 5. Certifications (optional)
        certs_status = self._check_certifications_completeness(parsed_data)
        if certs_status['status'] != 'not_present':
            sections.append(certs_status)
            if certs_status['status'] not in ['perfect', 'good']:
                overall_issues += 1
        
        # Determine overall status
        if overall_issues == 0:
            overall_status = 'good'
        elif overall_issues <= 2:
            overall_status = 'needs_improvement'
        else:
            overall_status = 'critical'
        
        return {
            'sections': sections,
            'overall_status': overall_status
        }
    
    def analyze_section(
        self,
        file_path: str,
        file_type: str,
        parsed_data: Dict[str, Any],
        section: str
    ) -> Dict[str, Any]:
        """
        Perform deep analysis on a specific section.
        Returns formatting issues, recommendations, and visual highlights.
        """
        # Import here to avoid circular dependency
        from .ats_issue_detector import ATSIssueDetector
        
        detector = ATSIssueDetector()
        
        # Get all blocks
        blocks = detector._extract_blocks_with_metadata(file_path)
        
        # Find the section location
        section_blocks = self._find_section_blocks(blocks, section)
        
        if not section_blocks:
            return {
                'section': section,
                'status': 'not_found',
                'formatting_issues': [f"Could not locate {section} section in resume"],
                'recommendations': [f"Add a clear '{section.upper()}' header to your resume"],
                'highlights': [],
                'visual_location': None
            }
        
        # Run targeted analysis on this section
        issues = []
        recommendations = []
        highlights = []
        
        if section == 'skills':
            result = self._analyze_skills_section(section_blocks, parsed_data, detector)
        elif section == 'experience':
            result = self._analyze_experience_section(section_blocks, parsed_data, detector)
        elif section == 'education':
            result = self._analyze_education_section(section_blocks, parsed_data, detector)
        elif section == 'contact_info':
            result = self._analyze_contact_section(blocks, parsed_data, detector)
        else:
            result = {
                'formatting_issues': [],
                'recommendations': [],
                'highlights': []
            }
        
        # Get visual location
        visual_location = None
        if section_blocks:
            first_block = section_blocks[0]
            visual_location = {
                'page': first_block['page'],
                'bbox': first_block['bbox']
            }
        
        return {
            'section': section,
            'status': 'analyzed',
            'formatting_issues': result.get('formatting_issues', []),
            'recommendations': result.get('recommendations', []),
            'highlights': result.get('highlights', []),
            'visual_location': visual_location
        }
    
    def _check_contact_completeness(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check if contact info is complete"""
        contact = parsed_data.get('contact_info', {})
        
        has_email = bool(contact.get('email') or parsed_data.get('email'))
        has_phone = bool(contact.get('phone') or parsed_data.get('phone'))
        has_name = bool(parsed_data.get('name'))
        
        extracted_count = sum([has_email, has_phone, has_name])
        
        if extracted_count >= 3:
            status = 'perfect'
            message = 'All contact info extracted'
        elif extracted_count == 2:
            status = 'good'
            missing = []
            if not has_email: missing.append('email')
            if not has_phone: missing.append('phone')
            if not has_name: missing.append('name')
            message = f'Missing: {", ".join(missing)}'
        elif extracted_count == 1:
            status = 'issues'
            message = 'Most contact info not extracted'
        else:
            status = 'missing'
            message = 'No contact info extracted'
        
        return {
            'section_name': 'contact_info',
            'status': status,
            'extracted_count': extracted_count,
            'original_count': 3,  # Assuming email, phone, name
            'message': message
        }
    
    def _check_skills_completeness(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check skills extraction"""
        skills = parsed_data.get('skills', [])
        extracted_count = len(skills)
        
        if extracted_count == 0:
            status = 'missing'
            message = 'No skills extracted'
        elif extracted_count < 3:
            status = 'issues'
            message = f'Only {extracted_count} skills extracted'
        elif extracted_count < 5:
            status = 'good'
            message = f'{extracted_count} skills extracted'
        else:
            status = 'perfect'
            message = f'{extracted_count} skills extracted'
        
        return {
            'section_name': 'skills',
            'status': status,
            'extracted_count': extracted_count,
            'original_count': None,  # Unknown without visual analysis
            'message': message,
            'details': 'Click to analyze if skills seem incomplete'
        }
    
    def _check_experience_completeness(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check experience extraction"""
        experience = parsed_data.get('experience', [])
        extracted_count = len(experience)
        
        # Check for jobs without bullets
        jobs_without_bullets = sum(1 for job in experience 
                                   if not job.get('bullets') or len(job.get('bullets', [])) == 0)
        
        if extracted_count == 0:
            status = 'missing'
            message = 'No work experience extracted'
        elif jobs_without_bullets > 0:
            status = 'issues'
            message = f'{extracted_count} jobs extracted, {jobs_without_bullets} without descriptions'
        elif extracted_count < 2:
            status = 'good'
            message = f'{extracted_count} job extracted'
        else:
            status = 'perfect'
            message = f'{extracted_count} jobs extracted with descriptions'
        
        return {
            'section_name': 'experience',
            'status': status,
            'extracted_count': extracted_count,
            'original_count': None,
            'message': message,
            'details': 'Click to analyze if jobs or descriptions are missing'
        }
    
    def _check_education_completeness(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check education extraction"""
        education = parsed_data.get('education', [])
        extracted_count = len(education)
        
        if extracted_count == 0:
            status = 'missing'
            message = 'No education extracted'
        elif extracted_count >= 1:
            # Check if education has key fields
            complete_entries = sum(1 for edu in education 
                                  if edu.get('degree') and edu.get('institution'))
            if complete_entries == extracted_count:
                status = 'perfect'
                message = f'{extracted_count} degree(s) extracted'
            else:
                status = 'issues'
                message = f'{extracted_count} degree(s) extracted, some incomplete'
        
        return {
            'section_name': 'education',
            'status': status,
            'extracted_count': extracted_count,
            'original_count': None,
            'message': message
        }
    
    def _check_certifications_completeness(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check certifications extraction"""
        certifications = parsed_data.get('certifications', [])
        
        if not certifications or len(certifications) == 0:
            return {
                'section_name': 'certifications',
                'status': 'not_present',
                'message': 'No certifications section'
            }
        
        extracted_count = len(certifications)
        
        return {
            'section_name': 'certifications',
            'status': 'perfect' if extracted_count > 0 else 'missing',
            'extracted_count': extracted_count,
            'message': f'{extracted_count} certification(s) extracted'
        }
    
    def _find_section_blocks(
        self,
        blocks: List[Dict[str, Any]],
        section: str
    ) -> List[Dict[str, Any]]:
        """Find blocks belonging to a specific section"""
        section_headers = {
            'skills': ['skills', 'technical skills', 'core competencies', 'technologies', 'expertise'],
            'experience': ['experience', 'work experience', 'employment', 'work history', 'professional experience'],
            'education': ['education', 'academic', 'academic background'],
            'contact_info': []  # Contact is usually at top, not a section
        }
        
        headers = section_headers.get(section, [])
        if not headers:
            return []
        
        section_blocks = []
        in_section = False
        
        for i, block in enumerate(blocks):
            text = block.get('text', '').lower().strip()
            
            # Check if this is the section header
            if any(header == text or f"{header}:" in text for header in headers):
                in_section = True
                continue
            
            # Check if we hit the next section
            if in_section:
                next_section_headers = ['experience', 'education', 'skills', 'projects', 
                                       'certifications', 'awards', 'summary', 'objective']
                if any(h in text and len(text) < 50 for h in next_section_headers):
                    break
                
                section_blocks.append(block)
        
        return section_blocks
    
    def _analyze_skills_section(
        self,
        section_blocks: List[Dict[str, Any]],
        parsed_data: Dict[str, Any],
        detector: Any
    ) -> Dict[str, Any]:
        """Analyze skills section formatting"""
        formatting_issues = detector._diagnose_section_formatting(section_blocks)
        recommendations = []
        highlights = []
        
        extracted_skills = len(parsed_data.get('skills', []))
        
        # Highlight the section with issues
        if formatting_issues and extracted_skills < 5:
            for block in section_blocks[:2]:
                highlights.append({
                    'page': block['page'],
                    'bbox': block['bbox'],
                    'severity': 'high',
                    'issue_type': 'skills_formatting',
                    'message': 'Skills section formatting issues',
                    'tooltip': f"ATS only extracted {extracted_skills} skills.\n\n" +
                              "Detected issues:\n" + "\n".join(f"• {issue}" for issue in formatting_issues) +
                              "\n\nFix: Use simple bullets in main body"
                })
        
        if formatting_issues:
            recommendations.append("Move skills to main body as simple bullet points")
            recommendations.append("Avoid tables, grids, or multi-column layouts for skills")
        
        return {
            'formatting_issues': formatting_issues,
            'recommendations': recommendations,
            'highlights': highlights
        }
    
    def _analyze_experience_section(
        self,
        section_blocks: List[Dict[str, Any]],
        parsed_data: Dict[str, Any],
        detector: Any
    ) -> Dict[str, Any]:
        """Analyze experience section formatting"""
        formatting_issues = detector._diagnose_section_formatting(section_blocks)
        recommendations = []
        highlights = []
        
        experience = parsed_data.get('experience', [])
        jobs_without_bullets = sum(1 for job in experience 
                                   if not job.get('bullets') or len(job.get('bullets', [])) == 0)
        
        if jobs_without_bullets > 0:
            formatting_issues.append(f"{jobs_without_bullets} job(s) without bullet points extracted")
            recommendations.append("Use standard bullet points (•, -, *) for all job descriptions")
        
        if formatting_issues:
            for block in section_blocks[:2]:
                highlights.append({
                    'page': block['page'],
                    'bbox': block['bbox'],
                    'severity': 'high',
                    'issue_type': 'experience_formatting',
                    'message': 'Experience formatting issues',
                    'tooltip': "Detected issues:\n" + "\n".join(f"• {issue}" for issue in formatting_issues) +
                              "\n\nFix: Use consistent format:\nJob Title | Company\nDate Range\n• Bullet\n• Bullet"
                })
        
        if formatting_issues:
            recommendations.append("Use consistent format for all jobs: Title, Company, Dates, Bullets")
        
        return {
            'formatting_issues': formatting_issues,
            'recommendations': recommendations,
            'highlights': highlights
        }
    
    def _analyze_education_section(
        self,
        section_blocks: List[Dict[str, Any]],
        parsed_data: Dict[str, Any],
        detector: Any
    ) -> Dict[str, Any]:
        """Analyze education section formatting"""
        formatting_issues = detector._diagnose_section_formatting(section_blocks)
        recommendations = []
        highlights = []
        
        education = parsed_data.get('education', [])
        
        if len(education) == 0:
            formatting_issues.append("No education entries extracted")
            recommendations.append("Ensure education section has clear degree and institution names")
        
        if formatting_issues:
            for block in section_blocks[:1]:
                highlights.append({
                    'page': block['page'],
                    'bbox': block['bbox'],
                    'severity': 'medium',
                    'issue_type': 'education_formatting',
                    'message': 'Education formatting issues',
                    'tooltip': "Detected issues:\n" + "\n".join(f"• {issue}" for issue in formatting_issues)
                })
        
        return {
            'formatting_issues': formatting_issues,
            'recommendations': recommendations,
            'highlights': highlights
        }
    
    def _analyze_contact_section(
        self,
        blocks: List[Dict[str, Any]],
        parsed_data: Dict[str, Any],
        detector: Any
    ) -> Dict[str, Any]:
        """Analyze contact info placement and extraction"""
        formatting_issues = []
        recommendations = []
        highlights = []
        
        # Check contact info extraction
        contact = parsed_data.get('contact_info', {})
        has_email = bool(contact.get('email') or parsed_data.get('email'))
        has_phone = bool(contact.get('phone') or parsed_data.get('phone'))
        
        # Find email/phone in blocks
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        phone_pattern = r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'
        
        # Check first few blocks (usually header area)
        for block in blocks[:10]:
            text = block.get('text', '')
            
            # Email found but not extracted
            if re.search(email_pattern, text) and not has_email:
                region = block.get('region', 'body')
                if region in ['header', 'footer']:
                    formatting_issues.append(f"Email found in {region} region")
                highlights.append({
                    'page': block['page'],
                    'bbox': block['bbox'],
                    'severity': 'critical',
                    'issue_type': 'contact_not_extracted',
                    'message': 'Email not extracted',
                    'tooltip': f"Email found in {region} but not extracted by ATS. Move to main body under name."
                })
            
            # Phone found but not extracted
            if re.search(phone_pattern, text) and not has_phone:
                region = block.get('region', 'body')
                if region in ['header', 'footer']:
                    formatting_issues.append(f"Phone found in {region} region")
                highlights.append({
                    'page': block['page'],
                    'bbox': block['bbox'],
                    'severity': 'high',
                    'issue_type': 'contact_not_extracted',
                    'message': 'Phone not extracted',
                    'tooltip': f"Phone found in {region} but not extracted by ATS. Move to main body."
                })
        
        if formatting_issues:
            recommendations.append("Move contact info from header/footer to main body under your name")
        
        return {
            'formatting_issues': formatting_issues,
            'recommendations': recommendations,
            'highlights': highlights
        }

