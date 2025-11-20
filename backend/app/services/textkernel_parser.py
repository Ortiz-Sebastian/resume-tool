"""
Textkernel Parser Adapter - Commercial-grade resume parsing.

Textkernel provides highly accurate parsing with minimal R&D effort.
This adapter wraps their API and converts to our standard format.
"""

import httpx
import base64
from typing import Dict, Any, List, Optional
from app.services.base_parser import BaseResumeParser
from app.config import settings


class TextkernelParser(BaseResumeParser):
    """Textkernel API parser implementation"""
    
    def __init__(self):
        self.api_key = settings.textkernel_api_key
        self.api_url = settings.textkernel_api_url
        self.timeout = 30.0
    
    def get_parser_name(self) -> str:
        return "Textkernel"
    
    def is_available(self) -> bool:
        """Check if Textkernel is configured"""
        return bool(self.api_key)
    
    def parse_to_structured_json(self, file_path: str, file_type: str) -> Dict[str, Any]:
        """
        Parse resume using Textkernel API.
        
        Textkernel provides:
        - High accuracy contact info extraction
        - Intelligent section detection
        - Date parsing and normalization
        - Skills taxonomy mapping
        - Education normalization
        - Multi-language support
        """
        if not self.is_available():
            raise ValueError("Textkernel API key not configured")
        
        # Read file and encode to base64
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        file_base64 = base64.b64encode(file_content).decode('utf-8')
        
        # Prepare request
        payload = {
            "DocumentAsBase64String": file_base64,
            "DocumentLastModified": None,  # Optional
            "GeocodeOptions": {
                "IncludeGeocoding": False  # Set to True if you need location geocoding
            },
            "IndexingOptions": {
                "IndexId": None,
                "DocumentId": None
            },
            "ProfessionNormalizationOptions": {
                "Enabled": True,
                "Language": "en"
            },
            "SkillsNormalizationOptions": {
                "Enabled": True,
                "Language": "en"
            }
        }
        
        headers = {
            "Tx-AccountId": self.api_key.split(':')[0] if ':' in self.api_key else "account",
            "Tx-ServiceKey": self.api_key.split(':')[1] if ':' in self.api_key else self.api_key,
            "Content-Type": "application/json"
        }
        
        try:
            # Call Textkernel API
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    self.api_url,
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()
            
            # Convert Textkernel response to our standard format
            return self._convert_textkernel_response(result)
            
        except httpx.HTTPError as e:
            raise Exception(f"Textkernel API error: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to parse resume with Textkernel: {str(e)}")
    
    def _convert_textkernel_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Textkernel response to our standard format"""
        
        # Textkernel response structure varies, but typically has Value.ResumeData
        if "Value" not in response or "ResumeData" not in response["Value"]:
            raise ValueError("Invalid Textkernel response format")
        
        resume_data = response["Value"]["ResumeData"]
        contact_info = resume_data.get("ContactInformation", {})
        
        # Extract contact details
        candidate_name = contact_info.get("CandidateName", {})
        name = f"{candidate_name.get('GivenName', '')} {candidate_name.get('FamilyName', '')}".strip()
        
        email = ""
        emails = contact_info.get("EmailAddresses", [])
        if emails:
            email = emails[0]
        
        phone = ""
        phones = contact_info.get("Telephones", [])
        if phones:
            phone = phones[0].get("Raw", "")
        
        location = ""
        location_obj = contact_info.get("Location", {})
        if location_obj:
            city = location_obj.get("Municipality", "")
            region = location_obj.get("Region", "")
            country = location_obj.get("CountryCode", "")
            location = ", ".join(filter(None, [city, region, country]))
        
        # Extract professional summary
        summary = resume_data.get("ProfessionalSummary", "")
        
        # Extract experience
        experience = []
        for position in resume_data.get("EmploymentHistory", {}).get("Positions", []):
            employer = position.get("Employer", {})
            job_titles = position.get("JobTitle", {})
            
            exp_entry = {
                "title": job_titles.get("Raw", "") if isinstance(job_titles, dict) else job_titles,
                "company": employer.get("Name", {}).get("Raw", "") if isinstance(employer.get("Name"), dict) else employer.get("Name", ""),
                "start_date": self._format_date(position.get("StartDate")),
                "end_date": self._format_date(position.get("EndDate")),
                "location": employer.get("Location", {}).get("Municipality", ""),
                "description": position.get("Description", ""),
                "highlights": []  # Could parse bullets from description
            }
            experience.append(exp_entry)
        
        # Extract education
        education = []
        for degree in resume_data.get("Education", {}).get("EducationDetails", []):
            school = degree.get("SchoolName", {})
            edu_entry = {
                "degree": degree.get("Degree", {}).get("Name", {}).get("Raw", ""),
                "institution": school.get("Raw", "") if isinstance(school, dict) else school,
                "graduation_date": self._format_date(degree.get("LastEducationDate")),
                "gpa": degree.get("GPA", {}).get("Score", ""),
                "major": degree.get("Major", "")
            }
            education.append(edu_entry)
        
        # Extract skills
        skills = []
        skill_list = resume_data.get("Skills", {}).get("Normalized", [])
        for skill in skill_list:
            skills.append(skill.get("Name", ""))
        
        # Also get raw skills
        raw_skills = resume_data.get("Skills", {}).get("Raw", [])
        for skill in raw_skills:
            skill_name = skill.get("Name", "")
            if skill_name and skill_name not in skills:
                skills.append(skill_name)
        
        # Extract certifications
        certifications = []
        for cert in resume_data.get("Certifications", []):
            cert_entry = {
                "name": cert.get("Name", ""),
                "issuer": cert.get("Issuer", ""),
                "date": self._format_date(cert.get("Date"))
            }
            certifications.append(cert_entry)
        
        # Extract languages
        languages = []
        for lang in resume_data.get("Languages", []):
            languages.append(lang.get("Language", ""))
        
        # Get raw text
        raw_text = response["Value"].get("ParsingMetadata", {}).get("PlainText", "")
        
        return {
            "name": name,
            "email": email,
            "phone": phone,
            "location": location,
            "summary": summary,
            "experience": experience,
            "education": education,
            "skills": skills,
            "certifications": certifications,
            "languages": languages,
            "raw_text": raw_text,
            "metadata": {
                "parser": "textkernel",
                "parsing_version": response.get("Info", {}).get("Code", ""),
                "resume_quality": resume_data.get("ResumeMetadata", {}).get("ResumeQuality", []),
                "detected_language": response.get("Value", {}).get("ParsingMetadata", {}).get("DetectedLanguage", "")
            }
        }
    
    def _format_date(self, date_obj: Optional[Dict[str, Any]]) -> str:
        """Format Textkernel date object to string"""
        if not date_obj:
            return ""
        
        if isinstance(date_obj, str):
            return date_obj
        
        # Textkernel returns dates as {"Date": "YYYY-MM-DD"}
        return date_obj.get("Date", "")

