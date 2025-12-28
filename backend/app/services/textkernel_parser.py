"""
Affinda Parser Adapter - Commercial-grade resume parsing via Affinda API.

Affinda provides highly accurate parsing with minimal R&D effort.
This adapter wraps the Affinda API (using their Python SDK) and converts to our standard format.
parser that retrieves data from a resume like a companu would, this is the truth of the ats tool
"""

import os
import time
from typing import Dict, Any, List, Optional
from app.services.base_parser import BaseResumeParser
from app.config import settings
from pathlib import Path
from affinda import AffindaAPI, TokenCredential
import tempfile
import requests


class TextkernelParser(BaseResumeParser):
    """
    Affinda API parser implementation.
    
    Note: Class name is kept as TextkernelParser for backward compatibility,
    but this implementation uses the Affinda API service.
    """
    
    def __init__(self):
        # Use AFFINDA_API_KEY (primary) or fallback to textkernel_api_key for backward compatibility
        self.api_key = os.getenv("AFFINDA_API_KEY")
        self.workspace_id = "UOflOxzq"
        self.timeout = 30.0
        self.document_type = "uXPuttKu"
        # Debug logging
        if not self.api_key:
            print("[AFFINDA DEBUG] API key not found. Checked: AFFINDA_API_KEY env var and settings.textkernel_api_key")
        if not self.workspace_id:
            print("[AFFINDA DEBUG] Workspace ID not found. Checked: AFFINDA_WORKSPACE_ID env var and settings.affinda_workspace_id")
        if self.api_key and self.workspace_id:
            print(f"[AFFINDA DEBUG] API key found: {'*' * (len(self.api_key) - 4) + self.api_key[-4:]}, Workspace ID: {self.workspace_id[:10]}...")
    
    def get_parser_name(self) -> str:
        return "Affinda"
    
    def is_available(self) -> bool:
        """Check if Affinda API is configured"""
        has_key = bool(self.api_key)
        has_workspace = bool(self.workspace_id)
        
        if not has_key:
            print("[AFFINDA] Not available: API key missing")
        if not has_workspace:
            print("[AFFINDA] Not available: Workspace ID missing")
        
        return has_key and has_workspace
    
    def parse_to_structured_json(self, file_path: str, file_type: str) -> Dict[str, Any]:
        """
        Parse resume using Affinda API (Textkernel-powered).
        
        Affinda provides:
        - High accuracy contact info extraction
        - Intelligent section detection
        - Date parsing and normalization
        - Skills taxonomy mapping
        - Education normalization
        - Multi-language support
        """
        if not self.api_key:
            raise ValueError("AFFINDA_API_KEY not configured. Set AFFINDA_API_KEY in .env file.")
        if not self.workspace_id:
            raise ValueError("AFFINDA_WORKSPACE_ID not configured. Set AFFINDA_WORKSPACE_ID in .env file.")
        
        # Use the documents endpoint as per Affinda documentation
        url = "https://api.affinda.com/v3/documents"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        # Upload the document - file must be opened during the request
        with open(file_path, "rb") as f:
            file_path_obj = Path(file_path)
            files = {"file": (file_path_obj.name, f, "application/pdf" if file_path_obj.suffix.lower() == ".pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
            data = {
                "workspace": self.workspace_id,
                "documentType": self.document_type,
                "wait": True,
                ##"extractor": "resume"  # Specify extractor type to ensure resume parsing
            }
            response = requests.post(url, headers=headers, files=files, data=data, timeout=120)
        
        # Check for errors and log details
        if response.status_code != 200 and response.status_code != 201:
            error_detail = response.text
            try:
                error_json = response.json()
                error_detail = error_json
            except:
                pass
            print(f"[AFFINDA ERROR] Status {response.status_code}: {error_detail}")
            response.raise_for_status()
        
        doc_response = response.json()
        print(f"[AFFINDA DEBUG] Document upload response keys: {list(doc_response.keys())}")
        
        # Extract document identifier from response
        # The identifier is in meta.identifier based on the API response structure
        meta = doc_response.get("meta", {})
        doc_identifier = meta.get("identifier") or doc_response.get("identifier") or doc_response.get("id")
        
        if not doc_identifier:
            raise Exception(f"Failed to get document identifier from response. Available keys: {list(doc_response.keys())}")
        
        print(f"[AFFINDA DEBUG] Document identifier: {doc_identifier}")
        
        # Debug key meta fields from upload response
        print(f"[AFFINDA DEBUG] === UPLOAD RESPONSE META FIELDS ===")
        print(f"[AFFINDA DEBUG] - ready: {meta.get('ready', 'N/A')}")
        print(f"[AFFINDA DEBUG] - failed: {meta.get('failed', 'N/A')}")
        print(f"[AFFINDA DEBUG] - extractor: {doc_response.get('extractor', 'N/A')}")
        print(f"[AFFINDA DEBUG] - documentType: {meta.get('documentType', 'N/A')}")
        print(f"[AFFINDA DEBUG] - isRejected: {meta.get('isRejected', 'N/A')}")
        print(f"[AFFINDA DEBUG] - errorCode: {meta.get('errorCode', 'N/A')}")
        print(f"[AFFINDA DEBUG] - errorDetail: {meta.get('errorDetail', 'N/A')}")
        print(f"[AFFINDA DEBUG] - error (top level): {doc_response.get('error', 'N/A')}")
        print(f"[AFFINDA DEBUG] - warnings: {doc_response.get('warnings', 'N/A')}")
        print(f"[AFFINDA DEBUG] ====================================")
        
        # Poll the API endpoint to wait for processing to complete
        max_wait_time = 60  # seconds
        wait_interval = 2  # seconds
        elapsed_time = 0
        
        # Use documents endpoint for retrieving the document
        get_url = f"https://api.affinda.com/v3/documents/{doc_identifier}"
        
        # Check initial state
        meta_ready = meta.get("ready", False)
        print(f"[AFFINDA DEBUG] Initial ready state from upload response: {meta_ready}")
        
        # Poll until document is ready
        while not meta_ready and elapsed_time < max_wait_time:
            time.sleep(wait_interval)
            elapsed_time += wait_interval
            
            # Get document status
            get_response = requests.get(get_url, headers=headers, timeout=30)
            if get_response.status_code != 200:
                raise Exception(f"Failed to get document status: {get_response.status_code} - {get_response.text}")
            
            doc_response = get_response.json()
            meta = doc_response.get("meta", {})
            meta_ready = meta.get("ready", False)
            meta_failed = meta.get("failed", False)
            
            print(f"[AFFINDA DEBUG] Doc state after {elapsed_time}s: ready={meta_ready}, failed={meta_failed}")
            
            # Debug key fields during polling
            if elapsed_time % 6 == 0:  # Print every 6 seconds to avoid spam
                print(f"[AFFINDA DEBUG] === POLLING STATUS (t={elapsed_time}s) ===")
                print(f"[AFFINDA DEBUG] - ready: {meta_ready}")
                print(f"[AFFINDA DEBUG] - failed: {meta_failed}")
                print(f"[AFFINDA DEBUG] - extractor: {doc_response.get('extractor', 'N/A')}")
                print(f"[AFFINDA DEBUG] - documentType: {meta.get('documentType', 'N/A')}")
                print(f"[AFFINDA DEBUG] - isRejected: {meta.get('isRejected', 'N/A')}")
                print(f"[AFFINDA DEBUG] - errorCode: {meta.get('errorCode', 'N/A')}")
                print(f"[AFFINDA DEBUG] - errorDetail: {meta.get('errorDetail', 'N/A')}")
                print(f"[AFFINDA DEBUG] - data keys count: {len(doc_response.get('data', {}).keys())}")
                print(f"[AFFINDA DEBUG] =========================================")
            
            if meta_failed:
                error_detail = meta.get("errorDetail") or doc_response.get("error", {}).get("errorDetail") or "Unknown error"
                error_code = meta.get("errorCode") or doc_response.get("error", {}).get("errorCode", "N/A")
                print(f"[AFFINDA ERROR] Document processing failed!")
                print(f"[AFFINDA ERROR] - errorCode: {error_code}")
                print(f"[AFFINDA ERROR] - errorDetail: {error_detail}")
                raise Exception(f"Document processing failed: {error_detail} (code: {error_code})")
        
        if not meta_ready:
            raise Exception(f"Document processing timed out after {max_wait_time} seconds")
        
        # Wait a bit more after ready state to ensure data is populated
        # Sometimes the document is marked ready but data is still being populated
        if meta_ready:
            print(f"[AFFINDA DEBUG] Document marked ready, waiting up to 10s for data to populate...")
            # Poll a few more times to wait for data
            for i in range(5):
                time.sleep(2)
                get_response = requests.get(get_url, headers=headers, timeout=30)
                if get_response.status_code == 200:
                    doc_response = get_response.json()
                    resume_data_check = doc_response.get("data", {})
                    print(f"[AFFINDA DEBUG] Attempt {i+1}: Data keys: {list(resume_data_check.keys()) if isinstance(resume_data_check, dict) else 'Not a dict'}")
                    if resume_data_check and isinstance(resume_data_check, dict) and len(resume_data_check) > 0:
                        print(f"[AFFINDA DEBUG] Data populated after {2*(i+1)}s")
                        break
            print(f"[AFFINDA DEBUG] Final document fetch completed")
        
        # Extract the resume data from the JSON response
        # The resume data should be in the 'data' field
        resume_data = doc_response.get("data", {})
        meta = doc_response.get("meta", {})
        
        print(f"[AFFINDA DEBUG] === FINAL DOCUMENT STATUS ===")
        print(f"[AFFINDA DEBUG] - ready: {meta.get('ready', 'N/A')}")
        print(f"[AFFINDA DEBUG] - failed: {meta.get('failed', 'N/A')}")
        print(f"[AFFINDA DEBUG] - extractor: {doc_response.get('extractor', 'N/A')}")
        print(f"[AFFINDA DEBUG] - documentType: {meta.get('documentType', 'N/A')}")
        print(f"[AFFINDA DEBUG] - isRejected: {meta.get('isRejected', 'N/A')}")
        print(f"[AFFINDA DEBUG] - isConfirmed: {meta.get('isConfirmed', 'N/A')}")
        print(f"[AFFINDA DEBUG] - isArchived: {meta.get('isArchived', 'N/A')}")
        print(f"[AFFINDA DEBUG] - errorCode: {meta.get('errorCode', 'N/A')}")
        print(f"[AFFINDA DEBUG] - errorDetail: {meta.get('errorDetail', 'N/A')}")
        print(f"[AFFINDA DEBUG] - error (top level): {doc_response.get('error', 'N/A')}")
        print(f"[AFFINDA DEBUG] - warnings: {doc_response.get('warnings', 'N/A')}")
        print(f"[AFFINDA DEBUG] - Data type: {type(resume_data)}")
        print(f"[AFFINDA DEBUG] - Data keys: {list(resume_data.keys()) if isinstance(resume_data, dict) else 'Not a dict'}")
        print(f"[AFFINDA DEBUG] - Data keys count: {len(resume_data.keys()) if isinstance(resume_data, dict) else 0}")
        print(f"[AFFINDA DEBUG] ===============================")
        
        # Check if data is empty but maybe the resume data is nested differently
        if not resume_data or (isinstance(resume_data, dict) and len(resume_data) == 0):
            # Try to see if there's any data elsewhere in the response
            print(f"[AFFINDA DEBUG] Data field is empty, checking full response structure...")
            print(f"[AFFINDA DEBUG] Full doc_response (first 2000 chars): {str(doc_response)[:2000]}")
            
            # Check if maybe the resume data is directly in the response (not nested in 'data')
            # Some API versions might return it differently
            if any(key in doc_response for key in ['name', 'emails', 'workExperience', 'work_experience', 'education']):
                print(f"[AFFINDA DEBUG] Found resume fields at top level, using entire response as resume_data")
                resume_data = doc_response
            else:
                # Final diagnostic before raising error
                print(f"[AFFINDA DEBUG] === DIAGNOSTIC INFO (Data Empty) ===")
                print(f"[AFFINDA DEBUG] - extractor: {doc_response.get('extractor', 'EMPTY/MISSING')}")
                print(f"[AFFINDA DEBUG] - documentType: {meta.get('documentType', 'EMPTY/MISSING')}")
                print(f"[AFFINDA DEBUG] - failed: {meta.get('failed', False)}")
                print(f"[AFFINDA DEBUG] - isRejected: {meta.get('isRejected', False)}")
                print(f"[AFFINDA DEBUG] - errorCode: {meta.get('errorCode', 'NONE')}")
                print(f"[AFFINDA DEBUG] - errorDetail: {meta.get('errorDetail', 'NONE')}")
                print(f"[AFFINDA DEBUG] - ready: {meta.get('ready', False)}")
                print(f"[AFFINDA DEBUG] - readyDt: {meta.get('readyDt', 'N/A')}")
                print(f"[AFFINDA DEBUG] - Top level error: {doc_response.get('error', 'NONE')}")
                print(f"[AFFINDA DEBUG] - Warnings: {doc_response.get('warnings', [])}")
                print(f"[AFFINDA DEBUG] =====================================")
                raise Exception(f"Document processed but no resume data available. Extractor: {doc_response.get('extractor', 'EMPTY')}, DocumentType: {meta.get('documentType', 'EMPTY')}, Failed: {meta.get('failed', False)}, IsRejected: {meta.get('isRejected', False)}")
        
        # Convert Affinda JSON response to our standard format
        try:
            result = self._convert_affinda_json_response(resume_data)
            print(f"[AFFINDA DEBUG] Conversion successful, keys: {list(result.keys())}")
            return result
        except Exception as e:
            print(f"[AFFINDA ERROR] Failed to convert response: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    def _convert_affinda_json_response(self, resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Affinda JSON response (dict) to our standard format"""
        
        # Extract name
        name = ""
        name_obj = resume_data.get("name")
        if name_obj:
            if isinstance(name_obj, dict):
                first = name_obj.get("first", "")
                last = name_obj.get("last", "")
                name = f"{first} {last}".strip()
            else:
                name = str(name_obj)
        
        # Extract contact info
        email = ""
        emails = resume_data.get("emails", [])
        if emails and len(emails) > 0:
            email_obj = emails[0]
            if isinstance(email_obj, dict):
                email = email_obj.get("value", "")
            else:
                email = str(email_obj)
        
        phone = ""
        phone_numbers = resume_data.get("phoneNumbers", []) or resume_data.get("phone_numbers", [])
        if phone_numbers and len(phone_numbers) > 0:
            phone_obj = phone_numbers[0]
            if isinstance(phone_obj, dict):
                phone = phone_obj.get("value", "")
            else:
                phone = str(phone_obj)
        
        # Extract location
        location_parts = []
        location = resume_data.get("location")
        if location and isinstance(location, dict):
            if location.get("city"):
                location_parts.append(location["city"])
            if location.get("region"):
                location_parts.append(location["region"])
            if location.get("country"):
                location_parts.append(location["country"])
        location_str = ", ".join(location_parts)
        
        # Extract summary
        summary = resume_data.get("summary", "") or resume_data.get("summaryText", "")
        
        # Extract experience
        experience = []
        work_experience = resume_data.get("workExperience", []) or resume_data.get("work_experience", [])
        if work_experience:
            for position in work_experience:
                if isinstance(position, dict):
                    exp_entry = {
                        "title": position.get("jobTitle", "") or position.get("job_title", ""),
                        "company": position.get("organization", "") or position.get("company", ""),
                        "start_date": self._format_date_from_json(position.get("startDate")) or position.get("start_date", ""),
                        "end_date": self._format_date_from_json(position.get("endDate")) or position.get("end_date", ""),
                        "location": position.get("location", {}).get("city", "") if isinstance(position.get("location"), dict) else "",
                        "description": position.get("description", ""),
                        "highlights": position.get("achievements", []) or position.get("highlights", [])
                    }
                    experience.append(exp_entry)
        
        # Extract education
        education = []
        education_list = resume_data.get("education", [])
        if education_list:
            for degree in education_list:
                if isinstance(degree, dict):
                    edu_entry = {
                        "degree": degree.get("degree", ""),
                        "institution": degree.get("organization", "") or degree.get("institution", ""),
                        "graduation_date": self._format_date_from_json(degree.get("endDate")) or degree.get("graduation_date", ""),
                        "gpa": degree.get("gpa", ""),
                        "major": degree.get("major", "")
                    }
                    education.append(edu_entry)
        
        # Extract skills
        skills = []
        skills_list = resume_data.get("skills", [])
        if skills_list:
            for skill in skills_list:
                if isinstance(skill, dict):
                    skill_name = skill.get("name", "")
                else:
                    skill_name = str(skill)
                if skill_name and skill_name not in skills:
                    skills.append(skill_name)
        
        # Extract certifications
        certifications = []
        certs_list = resume_data.get("certifications", [])
        if certs_list:
            for cert in certs_list:
                if isinstance(cert, dict):
                    cert_entry = {
                        "name": cert.get("name", ""),
                        "issuer": cert.get("issuer", ""),
                        "date": self._format_date_from_json(cert.get("date")) or cert.get("date", "")
                    }
                    certifications.append(cert_entry)
        
        # Extract languages
        languages = []
        langs_list = resume_data.get("languages", [])
        if langs_list:
            for lang in langs_list:
                if isinstance(lang, dict):
                    lang_name = lang.get("name", "")
                else:
                    lang_name = str(lang)
                if lang_name:
                    languages.append(lang_name)
        
        # Get raw text
        raw_text = resume_data.get("rawText", "") or resume_data.get("raw_text", "")
        
        return {
            "name": name,
            "email": email,
            "phone": phone,
            "location": location_str,
            "summary": summary,
            "experience": experience,
            "education": education,
            "skills": skills,
            "certifications": certifications,
            "languages": languages,
            "raw_text": raw_text,
            "metadata": {
                "parser": "affinda",
                "detected_language": resume_data.get("detectedLanguage", "") or resume_data.get("detected_language", "")
            }
        }
    
    def _format_date_from_json(self, date_obj: Any) -> str:
        """Format date from JSON response (can be string, dict, or None)"""
        if not date_obj:
            return ""
        
        if isinstance(date_obj, str):
            # Try to parse ISO format date string
            try:
                from datetime import datetime
                # Handle ISO format with or without timezone
                date_str = date_obj.replace('Z', '+00:00')
                dt = datetime.fromisoformat(date_str)
                return dt.strftime("%Y-%m-%d")
            except:
                # If parsing fails, return as-is if it looks like a date
                if len(date_obj) >= 10:
                    return date_obj[:10]  # Take first 10 chars (YYYY-MM-DD)
                return date_obj
        
        if isinstance(date_obj, dict):
            # Could be {"year": 2023, "month": 12, "day": 1} or {"date": "2023-12-01"}
            if "date" in date_obj:
                return str(date_obj["date"])
            if "year" in date_obj:
                year = str(date_obj.get("year", ""))
                month = int(date_obj.get("month", 1))
                day = int(date_obj.get("day", 1))
                return f"{year}-{month:02d}-{day:02d}"
        
        return str(date_obj)
    
    def _convert_affinda_response(self, parsed_resume) -> Dict[str, Any]:
        """Convert Affinda parsed resume object to our standard format"""
        
        # Extract name
        name = ""
        if hasattr(parsed_resume, 'name') and parsed_resume.name:
            if hasattr(parsed_resume.name, 'first'):
                name = parsed_resume.name.first or ""
            if hasattr(parsed_resume.name, 'last') and parsed_resume.name.last:
                name = f"{name} {parsed_resume.name.last}".strip()
        
        # Extract contact info
        email = ""
        if hasattr(parsed_resume, 'emails') and parsed_resume.emails:
            email = parsed_resume.emails[0].value if hasattr(parsed_resume.emails[0], 'value') else str(parsed_resume.emails[0])
        
        phone = ""
        if hasattr(parsed_resume, 'phone_numbers') and parsed_resume.phone_numbers:
            phone = parsed_resume.phone_numbers[0].value if hasattr(parsed_resume.phone_numbers[0], 'value') else str(parsed_resume.phone_numbers[0])
        
        # Extract location
        location_parts = []
        if hasattr(parsed_resume, 'location') and parsed_resume.location:
            if hasattr(parsed_resume.location, 'city') and parsed_resume.location.city:
                location_parts.append(parsed_resume.location.city)
            if hasattr(parsed_resume.location, 'region') and parsed_resume.location.region:
                location_parts.append(parsed_resume.location.region)
            if hasattr(parsed_resume.location, 'country') and parsed_resume.location.country:
                location_parts.append(parsed_resume.location.country)
        location = ", ".join(location_parts)
        
        # Extract summary
        summary = parsed_resume.summary if hasattr(parsed_resume, 'summary') and parsed_resume.summary else ""
        
        # Extract experience
        experience = []
        if hasattr(parsed_resume, 'work_experience') and parsed_resume.work_experience:
            for position in parsed_resume.work_experience:
                exp_entry = {
                    "title": position.job_title if hasattr(position, 'job_title') else "",
                    "company": position.organization if hasattr(position, 'organization') else "",
                    "start_date": position.start_date.strftime("%Y-%m-%d") if hasattr(position, 'start_date') and position.start_date else "",
                    "end_date": position.end_date.strftime("%Y-%m-%d") if hasattr(position, 'end_date') and position.end_date else "",
                    "location": position.location.city if hasattr(position, 'location') and position.location and hasattr(position.location, 'city') else "",
                    "description": position.description if hasattr(position, 'description') else "",
                    "highlights": position.achievements if hasattr(position, 'achievements') else []
                }
                experience.append(exp_entry)
        
        # Extract education
        education = []
        if hasattr(parsed_resume, 'education') and parsed_resume.education:
            for degree in parsed_resume.education:
                edu_entry = {
                    "degree": degree.degree if hasattr(degree, 'degree') else "",
                    "institution": degree.organization if hasattr(degree, 'organization') else "",
                    "graduation_date": degree.end_date.strftime("%Y-%m-%d") if hasattr(degree, 'end_date') and degree.end_date else "",
                    "gpa": degree.gpa if hasattr(degree, 'gpa') else "",
                    "major": degree.major if hasattr(degree, 'major') else ""
                }
                education.append(edu_entry)
        
        # Extract skills
        skills = []
        if hasattr(parsed_resume, 'skills') and parsed_resume.skills:
            for skill in parsed_resume.skills:
                skill_name = skill.name if hasattr(skill, 'name') else str(skill)
                if skill_name and skill_name not in skills:
                    skills.append(skill_name)
        
        # Extract certifications
        certifications = []
        if hasattr(parsed_resume, 'certifications') and parsed_resume.certifications:
            for cert in parsed_resume.certifications:
                cert_entry = {
                    "name": cert.name if hasattr(cert, 'name') else "",
                    "issuer": cert.issuer if hasattr(cert, 'issuer') else "",
                    "date": cert.date.strftime("%Y-%m-%d") if hasattr(cert, 'date') and cert.date else ""
                }
                certifications.append(cert_entry)
        
        # Extract languages
        languages = []
        if hasattr(parsed_resume, 'languages') and parsed_resume.languages:
            for lang in parsed_resume.languages:
                lang_name = lang.name if hasattr(lang, 'name') else str(lang)
                if lang_name:
                    languages.append(lang_name)
        
        # Get raw text
        raw_text = parsed_resume.raw_text if hasattr(parsed_resume, 'raw_text') else ""
        
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
                "parser": "affinda",
                "detected_language": parsed_resume.detected_language if hasattr(parsed_resume, 'detected_language') else ""
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

