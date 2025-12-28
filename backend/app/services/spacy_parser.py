"""
SpaCy-based Resume Parser - Enhanced Free Alternative.

This parser uses advanced spaCy NLP, pattern matching, and entity recognition
to provide commercial-grade parsing quality.
"""

import fitz  # PyMuPDF
from docx import Document
import re
from typing import Dict, Any, List, Optional, Tuple
import spacy
from datetime import datetime
from dateutil import parser as date_parser
from app.services.base_parser import BaseResumeParser


class SpacyResumeParser(BaseResumeParser):
    """spaCy-based resume parser (free, rule-based)"""
    
    def __init__(self):
        try:
            self.nlp = spacy.load("en_core_web_lg")
        except OSError:
            # Fallback to smaller model if large model not available
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                self.nlp = None
    
    def get_parser_name(self) -> str:
        return "spaCy"
    
    def is_available(self) -> bool:
        """Check if spaCy model is loaded"""
        return self.nlp is not None
    
    def parse_to_structured_json(self, file_path: str, file_type: str) -> Dict[str, Any]:
        """Parse resume using spaCy NLP and pattern matching"""
        if not self.is_available():
            raise ValueError("spaCy model not loaded. Run: python -m spacy download en_core_web_lg")
        
        # Extract text
        if file_type == ".pdf":
            text = self._extract_pdf_text(file_path)
        elif file_type == ".docx":
            text = self._extract_docx_text(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
        
        # Extract structured data
        return self._extract_structured_data(text)
    
    def _extract_pdf_text(self, file_path: str) -> str:
        """Extract text from PDF using PyMuPDF"""
        text = ""
        try:
            doc = fitz.open(file_path)
            for page in doc:
                text += page.get_text()
            doc.close()
        except Exception as e:
            raise Exception(f"Error parsing PDF: {str(e)}")
        return text
    
    def _extract_docx_text(self, file_path: str) -> str:
        """Extract text from DOCX"""
        try:
            doc = Document(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        except Exception as e:
            raise Exception(f"Error parsing DOCX: {str(e)}")
        return text
    
    def _extract_structured_data(self, text: str) -> Dict[str, Any]:
        """Extract structured data from resume text using NLP"""
        doc = self.nlp(text)
        
        # Extract basic information
        parsed = {
            "name": self._extract_name(doc),
            "email": self._extract_email(text),
            "phone": self._extract_phone(text),
            "location": "",  # SpaCy doesn't extract this reliably
            "summary": self._extract_summary(text),
            "experience": self._extract_experience(text),
            "education": self._extract_education(text),
            "skills": self._extract_skills(text),
            "certifications": self._extract_certifications(text),
            "languages": [],  # Not implemented in basic version
            "raw_text": text,
            "metadata": {
                "parser": "spacy",
                "model": "en_core_web_lg" if "lg" in self.nlp.meta.get("name", "") else "en_core_web_sm"
            }
        }
        
        return parsed
    
    def _extract_name(self, doc) -> str:
        """Extract name from document (usually first line or PERSON entity)"""
        # Try to find PERSON entities
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                return ent.text
        
        # Fallback: first non-empty line
        lines = doc.text.split("\n")
        for line in lines:
            line = line.strip()
            if line and len(line) < 50:  # Names are usually short
                return line
        
        return ""
    
    def _extract_email(self, text: str) -> str:
        """Extract email address"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        match = re.search(email_pattern, text)
        return match.group(0) if match else ""
    
    def _extract_phone(self, text: str) -> str:
        """Extract phone number"""
        phone_pattern = r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        match = re.search(phone_pattern, text)
        return match.group(0) if match else ""
    
    def _extract_summary(self, text: str) -> str:
        """Extract professional summary/objective"""
        summary_keywords = [
            "summary", "objective", "profile", "about",
            "professional summary", "career objective"
        ]
        
        lines = text.split("\n")
        summary_lines = []
        capturing = False
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            # Check if this line is a summary header
            if any(keyword in line_lower for keyword in summary_keywords):
                capturing = True
                continue
            
            # Stop capturing at next section
            if capturing:
                if self._is_section_header(line):
                    break
                if line.strip():
                    summary_lines.append(line.strip())
        
        return " ".join(summary_lines)
    
    def _extract_experience(self, text: str) -> List[Dict[str, Any]]:
        """Extract work experience with enhanced NLP"""
        experience = []
        experience_keywords = ["experience", "work history", "employment", "work experience", "professional experience"]
        
        lines = text.split("\n")
        capturing = False
        current_entry = None
        description_lines = []
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            # Start capturing after experience header
            if any(keyword in line_lower for keyword in experience_keywords):
                capturing = True
                continue
            
            if capturing:
                # Stop at next major section
                if self._is_section_header(line) and not any(k in line_lower for k in experience_keywords):
                    # Save last entry
                    if current_entry:
                        current_entry["description"] = " ".join(description_lines).strip()
                        current_entry["highlights"] = self._extract_bullet_points(description_lines)
                        experience.append(current_entry)
                    break
                
                if not line.strip():
                    # Empty line often separates entries
                    if current_entry and description_lines:
                        current_entry["description"] = " ".join(description_lines).strip()
                        current_entry["highlights"] = self._extract_bullet_points(description_lines)
                        experience.append(current_entry)
                        current_entry = None
                        description_lines = []
                    continue
                
                # Try to detect if this is a new job entry (title/company line)
                if self._looks_like_job_header(line):
                    # Save previous entry
                    if current_entry:
                        current_entry["description"] = " ".join(description_lines).strip()
                        current_entry["highlights"] = self._extract_bullet_points(description_lines)
                        experience.append(current_entry)
                        description_lines = []
                    
                    # Parse the new entry
                    current_entry = self._parse_job_header(line, lines[i:i+3] if i+3 < len(lines) else lines[i:])
                else:
                    # This is description/bullet content
                    if current_entry:
                        description_lines.append(line.strip())
        
        # Save last entry
        if current_entry:
            current_entry["description"] = " ".join(description_lines).strip()
            current_entry["highlights"] = self._extract_bullet_points(description_lines)
            experience.append(current_entry)
        
        return experience
    
    def _looks_like_job_header(self, line: str) -> bool:
        """Determine if line is likely a job title/company header"""
        line = line.strip()
        if not line or len(line) > 100:
            return False
        
        # Check for date patterns (strong indicator)
        if re.search(r'\d{4}', line):
            return True
        
        # Check for pipe separator (Title | Company)
        if '|' in line or '–' in line or '—' in line:
            return True
        
        # Check for "at Company" pattern
        if re.search(r'\bat\b', line.lower()):
            return True
        
        # Title case and short (likely a header)
        words = line.split()
        if 2 <= len(words) <= 8:
            if sum(1 for w in words if w[0].isupper()) >= len(words) * 0.6:
                return True
        
        return False
    
    def _parse_job_header(self, header_line: str, context_lines: List[str]) -> Dict[str, Any]:
        """Parse job title, company, dates, location from header and context"""
        doc = self.nlp(header_line)
        
        # Initialize entry
        entry = {
            "title": "",
            "company": "",
            "start_date": "",
            "end_date": "",
            "location": "",
            "description": "",
            "highlights": []
        }
        
        # Extract dates from header
        dates = self._extract_dates(header_line)
        if len(dates) >= 2:
            entry["start_date"] = dates[0]
            entry["end_date"] = dates[1]
        elif len(dates) == 1:
            entry["start_date"] = dates[0]
            entry["end_date"] = "Present"
        
        # Extract organizations (companies)
        orgs = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
        
        # Common patterns: "Title at Company" or "Title | Company" or "Company - Title"
        # Try to split by separators
        separators = [' | ', ' – ', ' — ', ' at ', ' @ ', ' - ']
        parts = [header_line]
        for sep in separators:
            if sep in header_line:
                parts = [p.strip() for p in re.split(re.escape(sep), header_line, maxsplit=1)]
                break
        
        # Extract location from header or next line
        location = self._extract_location_from_text(header_line)
        if not location and len(context_lines) > 1:
            location = self._extract_location_from_text(context_lines[1])
        entry["location"] = location
        
        # If we found orgs, use them
        if orgs:
            entry["company"] = orgs[0]
            # Title is likely everything before the company
            entry["title"] = header_line.split(orgs[0])[0].strip()
            # Clean up common separators from title
            for sep in [' | ', ' at ', ' @ ', ' - ', ' – ', ' — ']:
                entry["title"] = entry["title"].rstrip(sep).strip()
        elif len(parts) == 2:
            # Heuristic: first part is usually title, second is company
            entry["title"] = self._remove_dates_and_location(parts[0])
            entry["company"] = self._remove_dates_and_location(parts[1])
        else:
            # Fallback: use the whole line as title
            entry["title"] = self._remove_dates_and_location(header_line)
        
        # Clean up extracted fields
        entry["title"] = entry["title"].strip()
        entry["company"] = entry["company"].strip()
        
        return entry
    
    def _extract_dates(self, text: str) -> List[str]:
        """Extract date strings from text"""
        dates = []
        
        # Common date patterns
        date_patterns = [
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}\b',  # Jan 2020
            r'\b\d{1,2}/\d{4}\b',  # 01/2020
            r'\b\d{4}\b',  # 2020
            r'\bPresent\b',
            r'\bCurrent\b',
            r'\bOngoing\b',
            r'\bNow\b',
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates.extend(matches)
        
        # Normalize "Current", "Now", etc. to "Present"
        dates = [d if d.lower() not in ['current', 'ongoing', 'now'] else 'Present' for d in dates]
        
        return dates[:2]  # Return max 2 dates (start, end)
    
    def _extract_location_from_text(self, text: str) -> str:
        """Extract location (City, State/Country) from text"""
        doc = self.nlp(text)
        
        # Look for GPE (Geo-Political Entity) entities
        locations = [ent.text for ent in doc.ents if ent.label_ in ["GPE", "LOC"]]
        
        if locations:
            # Often format is "City, State" or "City, Country"
            if len(locations) >= 2:
                return f"{locations[0]}, {locations[1]}"
            return locations[0]
        
        # Fallback: look for common location patterns
        location_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),\s*([A-Z]{2}|[A-Z][a-z]+)\b'
        match = re.search(location_pattern, text)
        if match:
            return match.group(0)
        
        return ""
    
    def _remove_dates_and_location(self, text: str) -> str:
        """Remove date and location patterns from text"""
        # Remove dates
        text = re.sub(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\b\d{1,2}/\d{4}\b', '', text)
        text = re.sub(r'\b\d{4}\b', '', text)
        text = re.sub(r'\b(?:Present|Current|Ongoing|Now)\b', '', text, flags=re.IGNORECASE)
        
        # Remove location patterns
        text = re.sub(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),\s*([A-Z]{2}|[A-Z][a-z]+)\b', '', text)
        
        # Remove date separators
        text = re.sub(r'\s*[-–—]\s*', ' ', text)
        
        # Clean up extra whitespace
        text = ' '.join(text.split())
        
        return text.strip()
    
    def _extract_bullet_points(self, lines: List[str]) -> List[str]:
        """Extract bullet points from description lines"""
        bullets = []
        for line in lines:
            line = line.strip()
            # Check if line starts with bullet marker
            if re.match(r'^[•·∙▪▫◦‣⁃○●★☆♦◆■□-]\s+', line) or line.startswith('- '):
                # Remove bullet marker
                bullet = re.sub(r'^[•·∙▪▫◦‣⁃○●★☆♦◆■□-]\s+', '', line)
                if bullet:
                    bullets.append(bullet)
        
        return bullets
    
    def _extract_education(self, text: str) -> List[Dict[str, Any]]:
        """Extract education with enhanced parsing"""
        education = []
        education_keywords = ["education", "academic", "qualification", "academic background"]
        
        lines = text.split("\n")
        capturing = False
        current_entry = None
        entry_lines = []
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            if any(keyword in line_lower for keyword in education_keywords):
                capturing = True
                continue
            
            if capturing:
                if self._is_section_header(line) and not any(k in line_lower for k in education_keywords):
                    # Save last entry
                    if current_entry:
                        education.append(current_entry)
                    break
                
                if not line.strip():
                    # Empty line separates entries
                    if current_entry:
                        education.append(current_entry)
                        current_entry = None
                        entry_lines = []
                    continue
                
                # Check if this looks like a new education entry (degree or institution)
                if self._looks_like_education_header(line):
                    # Save previous entry
                    if current_entry:
                        education.append(current_entry)
                        entry_lines = []
                    
                    # Start new entry
                    current_entry = self._parse_education_entry(line, lines[i:i+3] if i+3 < len(lines) else lines[i:])
                else:
                    # Additional info for current entry (GPA, minor, etc.)
                    if current_entry:
                        self._enhance_education_entry(current_entry, line)
        
        # Save last entry
        if current_entry:
            education.append(current_entry)
        
        return education
    
    def _looks_like_education_header(self, line: str) -> bool:
        """Determine if line is likely degree or institution"""
        line = line.strip()
        if not line or len(line) > 150:
            return False
        
        # Check for degree keywords
        degree_keywords = ['bachelor', 'master', 'phd', 'ph.d', 'b.s.', 'b.a.', 'm.s.', 'm.a.',
                          'associate', 'diploma', 'certificate', 'degree', 'bs', 'ba', 'ms', 'ma']
        if any(keyword in line.lower() for keyword in degree_keywords):
            return True
        
        # Check for university/college keywords
        institution_keywords = ['university', 'college', 'institute', 'school']
        if any(keyword in line.lower() for keyword in institution_keywords):
            return True
        
        # Check for date patterns (graduation year)
        if re.search(r'\b\d{4}\b', line):
            return True
        
        return False
    
    def _parse_education_entry(self, header_line: str, context_lines: List[str]) -> Dict[str, Any]:
        """Parse degree, institution, dates, GPA, major"""
        doc = self.nlp(header_line)
        
        entry = {
            "degree": "",
            "institution": "",
            "graduation_date": "",
            "gpa": "",
            "major": ""
        }
        
        # Extract organizations (likely institution)
        orgs = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
        if orgs:
            entry["institution"] = orgs[0]
        
        # Extract dates
        dates = self._extract_dates(header_line)
        if dates:
            entry["graduation_date"] = dates[0] if dates[0].lower() != 'present' else dates[-1]
        
        # Extract GPA
        gpa = self._extract_gpa(header_line)
        if gpa:
            entry["gpa"] = gpa
        
        # Determine if line is degree or institution
        degree_keywords = ['bachelor', 'master', 'phd', 'ph.d', 'b.s.', 'b.a.', 'm.s.', 'm.a.',
                          'associate', 'diploma', 'certificate', 'degree', 'bs', 'ba', 'ms', 'ma']
        institution_keywords = ['university', 'college', 'institute', 'school']
        
        line_lower = header_line.lower()
        has_degree = any(keyword in line_lower for keyword in degree_keywords)
        has_institution = any(keyword in line_lower for keyword in institution_keywords)
        
        if has_degree:
            # This line is the degree
            entry["degree"] = self._clean_education_field(header_line)
            entry["major"] = self._extract_major(header_line)
            
            # Look for institution in next line
            if not entry["institution"] and len(context_lines) > 1:
                next_line = context_lines[1].strip()
                next_doc = self.nlp(next_line)
                next_orgs = [ent.text for ent in next_doc.ents if ent.label_ == "ORG"]
                if next_orgs:
                    entry["institution"] = next_orgs[0]
                elif any(k in next_line.lower() for k in institution_keywords):
                    entry["institution"] = self._clean_education_field(next_line)
        
        elif has_institution:
            # This line is the institution
            entry["institution"] = self._clean_education_field(header_line)
            
            # Look for degree in next line
            if not entry["degree"] and len(context_lines) > 1:
                next_line = context_lines[1].strip()
                if any(k in next_line.lower() for k in degree_keywords):
                    entry["degree"] = self._clean_education_field(next_line)
                    entry["major"] = self._extract_major(next_line)
        
        return entry
    
    def _extract_gpa(self, text: str) -> str:
        """Extract GPA from text"""
        # Common GPA patterns
        gpa_patterns = [
            r'GPA:?\s*(\d+\.\d+)\s*(?:/\s*(\d+\.\d+))?',
            r'(\d+\.\d+)\s*/\s*(\d+\.\d+)\s+GPA',
            r'(\d+\.\d+)\s+GPA',
        ]
        
        for pattern in gpa_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if match.group(2):  # Has scale (e.g., 3.8/4.0)
                    return f"{match.group(1)}/{match.group(2)}"
                else:
                    return match.group(1)
        
        return ""
    
    def _extract_major(self, text: str) -> str:
        """Extract major/field of study from text"""
        major_patterns = [
            r'(?:major|concentration|specialization|field):\s*([^,\n]+)',
            r'\bin\s+([A-Z][^,\n]{2,50})',  # "Bachelor in Computer Science"
            r'of\s+([A-Z][^,\n]{2,50})',  # "Bachelor of Science"
        ]
        
        for pattern in major_patterns:
            match = re.search(pattern, text)
            if match:
                major = match.group(1).strip()
                # Clean up common trailing words
                major = re.sub(r'\s*(?:from|at|,).*$', '', major)
                if len(major) < 50:  # Sanity check
                    return major
        
        return ""
    
    def _clean_education_field(self, text: str) -> str:
        """Clean education field by removing dates, GPA, etc."""
        # Remove GPA
        text = re.sub(r'GPA:?\s*\d+\.\d+(?:\s*/\s*\d+\.\d+)?', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\d+\.\d+\s*/\s*\d+\.\d+\s+GPA', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\d+\.\d+\s+GPA', '', text, flags=re.IGNORECASE)
        
        # Remove dates
        text = re.sub(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\b\d{1,2}/\d{4}\b', '', text)
        text = re.sub(r'\b\d{4}\b', '', text)
        
        # Remove location
        text = re.sub(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),\s*([A-Z]{2}|[A-Z][a-z]+)\b', '', text)
        
        # Remove date separators
        text = re.sub(r'\s*[-–—]\s*', ' ', text)
        
        # Clean up extra whitespace
        text = ' '.join(text.split())
        
        return text.strip()
    
    def _enhance_education_entry(self, entry: Dict[str, Any], line: str):
        """Add additional info to education entry from supplementary lines"""
        # Extract GPA if not already set
        if not entry["gpa"]:
            gpa = self._extract_gpa(line)
            if gpa:
                entry["gpa"] = gpa
        
        # Extract major if not already set
        if not entry["major"]:
            major = self._extract_major(line)
            if major:
                entry["major"] = major
        
        # Extract dates if not already set
        if not entry["graduation_date"]:
            dates = self._extract_dates(line)
            if dates:
                entry["graduation_date"] = dates[0] if dates[0].lower() != 'present' else dates[-1]
    
    def _extract_skills(self, text: str) -> List[str]:
        """Extract skills"""
        skills = []
        skills_keywords = ["skills", "technical skills", "competencies", "expertise", "technologies"]
        
        lines = text.split("\n")
        capturing = False
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Start capturing after skills header
            if any(keyword in line_lower for keyword in skills_keywords):
                capturing = True
                continue
            
            if capturing:
                # Stop at next section
                if self._is_section_header(line):
                    break
                
                if line.strip():
                    # Split by common delimiters
                    line_skills = re.split(r'[,;|•·]', line)
                    for skill in line_skills:
                        skill = skill.strip()
                        # Filter out obvious non-skills
                        if skill and self._is_likely_skill(skill):
                            skills.append(skill)
        
        return list(set(skills))  # Remove duplicates
    
    def _is_likely_skill(self, text: str) -> bool:
        """Heuristic to determine if text is likely a skill"""
        text = text.strip()
        
        # Filter out very long strings (likely descriptions, not skills)
        if len(text) > 50:
            return False
        
        # Filter out common non-skill patterns
        non_skill_patterns = [
            r'^\d{4}$',  # Just a year
            r'^\d{1,2}/\d{1,2}/\d{2,4}$',  # Date
            r'^[A-Z][a-z]+ \d{4}$',  # "January 2020"
            r'university$',  # School names
            r'college$',
            r'school$',
            r'^GPA',  # GPA entries
        ]
        
        text_lower = text.lower()
        for pattern in non_skill_patterns:
            if re.search(pattern, text_lower):
                return False
        
        # Filter out common non-skill words
        non_skills = ['present', 'current', 'ongoing', 'volunteer', 'member', 'president', 'vice president']
        if text_lower in non_skills:
            return False
        
        return True
    
    def _extract_certifications(self, text: str) -> List[Dict[str, str]]:
        """Extract certifications"""
        certifications = []
        cert_keywords = ["certification", "certificate", "license"]
        
        lines = text.split("\n")
        capturing = False
        
        for line in lines:
            line_lower = line.lower().strip()
            
            if any(keyword in line_lower for keyword in cert_keywords):
                capturing = True
                continue
            
            if capturing:
                if self._is_section_header(line):
                    break
                
                if line.strip():
                    certifications.append({
                        "name": line.strip(),
                        "issuer": "",
                        "date": ""
                    })
        
        return certifications
    
    def _is_section_header(self, line: str) -> bool:
        """Check if line is likely a section header"""
        line = line.strip()
        if not line:
            return False
        
        # Common section headers (expanded list)
        headers = [
            "summary", "objective", "experience", "education", "skills", "relevant experience",
            "certifications", "projects", "awards", "publications",
            "volunteer", "languages", "interests", "references",
            "activities", "extracurricular", "leadership", "involvement",
            "honors", "achievements", "professional development",
            "training", "courses", "portfolio", "research",
            "teaching", "speaking", "presentations", "patents",
            "memberships", "affiliations", "community service"
        ]
        
        line_lower = line.lower()
        
        # Check for exact header match
        for header in headers:
            pattern = rf"^\s*{re.escape(header)}\s*:?\s*$"
            if re.match(pattern, line_lower):
                return True
        
        # Additional heuristics for section headers:
        # - All caps (e.g., "EDUCATION")
        # - Ends with colon (e.g., "Skills:")
        # - Very short line with title case
        if len(line) < 50:
            if line.isupper() or line.endswith(':'):
                return True
            # Title case with < 5 words (likely a header)
            words = line.split()
            if len(words) <= 4 and all(w[0].isupper() if w else False for w in words):
                return True
        
        return False

