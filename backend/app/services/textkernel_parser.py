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
        api_key_raw = os.getenv("AFFINDA_API_KEY")
        # Strip whitespace in case there's any
        self.api_key = api_key_raw.strip() if api_key_raw else None
        self.workspace_id = "gThVEtSq"
        self.timeout = 30.0
        self.document_type = "wbTlWoen"
        # Debug logging
        if not self.api_key:
            print("[AFFINDA DEBUG] API key not found. Checked: AFFINDA_API_KEY env var")
        if not self.workspace_id:
            print("[AFFINDA DEBUG] Workspace ID not found. Checked: AFFINDA_WORKSPACE_ID env var and settings.affinda_workspace_id")
        if self.api_key and self.workspace_id:
            api_key_preview = f"{self.api_key[:8]}...{self.api_key[-4:]}" if len(self.api_key) > 12 else "***"
            print(f"[AFFINDA DEBUG] API key found (length: {len(self.api_key)}): {api_key_preview}, Workspace ID: {self.workspace_id[:10]}...")
    
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
        url = "https://api.us1.affinda.com/v3/documents"
        
        # Verify API key is set and format header correctly
        if not self.api_key:
            raise ValueError("AFFINDA_API_KEY is not set or is empty")
        
        # Strip any whitespace and create authorization header
        api_key_clean = self.api_key.strip()
        headers = {"Authorization": f"Bearer {api_key_clean}"}
        # Note: Don't set Content-Type for multipart/form-data - requests library sets it automatically with boundary
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
                    if resume_data_check and isinstance(resume_data_check, dict) and len(resume_data_check) > 0:
                        break
        
        # Extract the resume data from the JSON response
        # The resume data should be in the 'data' field
        resume_data = doc_response.get("data", {})
        meta = doc_response.get("meta", {})
        
        # Check if data is empty but maybe the resume data is nested differently
        if not resume_data or (isinstance(resume_data, dict) and len(resume_data) == 0):
            # Check if maybe the resume data is directly in the response (not nested in 'data')
            if any(key in doc_response for key in ['name', 'emails', 'workExperience', 'work_experience', 'education']):
                resume_data = doc_response
            else:
                raise Exception(f"Document processed but no resume data available. Extractor: {doc_response.get('extractor', 'EMPTY')}, DocumentType: {meta.get('documentType', 'EMPTY')}, Failed: {meta.get('failed', False)}, IsRejected: {meta.get('isRejected', False)}")
        
        # Convert Affinda JSON response to our standard format
        try:
            result = self._convert_affinda_json_response(resume_data)
            return result
        except Exception as e:
            print(f"[AFFINDA ERROR] Failed to convert response: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    def _convert_affinda_json_response(self, resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Affinda JSON response (dict) to our standard format"""
        
        # Extract name - Affinda uses "candidateName" with nested structure
        name = ""
        name_obj = resume_data.get("candidateName") or resume_data.get("name")
        if name_obj:
            if isinstance(name_obj, dict):
                # Affinda returns: {"raw": "SEBASTIAN ORTIZ", "parsed": {"firstName": {...}, "familyName": {...}}}
                # Try raw field first (simplest)
                if name_obj.get("raw"):
                    name = str(name_obj.get("raw")).strip()
                else:
                    # Try parsed structure
                    parsed_name = name_obj.get("parsed", {})
                    if isinstance(parsed_name, dict):
                        first = ""
                        last = ""
                        # Check for firstName (could be nested)
                        first_obj = parsed_name.get("firstName", {})
                        if isinstance(first_obj, dict):
                            first = first_obj.get("raw", "") or first_obj.get("parsed", "") or ""
                        else:
                            first = str(first_obj) if first_obj else ""
                        
                        # Check for familyName (could be nested)
                        last_obj = parsed_name.get("familyName", {})
                        if isinstance(last_obj, dict):
                            last = last_obj.get("raw", "") or last_obj.get("parsed", "") or ""
                        else:
                            last = str(last_obj) if last_obj else ""
                        
                        if first or last:
                            name = f"{first} {last}".strip()
            else:
                name = str(name_obj).strip()
        
        # If name is still empty, try to extract from rawText
        if not name and resume_data.get("rawText"):
            raw_text_lines = resume_data.get("rawText", "").split("\n")
            if raw_text_lines:
                # First line often contains the name
                potential_name = raw_text_lines[0].strip()
                # Basic check: if it looks like a name (2-4 words, mostly letters)
                if potential_name and len(potential_name.split()) <= 4 and potential_name.replace(" ", "").replace("-", "").isalpha():
                    name = potential_name
        
        # Extract contact info - Affinda may return "email" (string, list, or array) or "emails" (array)
        email = ""
        email_field = resume_data.get("email")
        if email_field:
            # If it's a list/array, extract the first item
            if isinstance(email_field, list) and len(email_field) > 0:
                email_obj = email_field[0]
                if isinstance(email_obj, dict):
                    # Try common fields for email value
                    email = email_obj.get("value", "") or email_obj.get("raw", "") or email_obj.get("parsed", "")
                else:
                    email = str(email_obj)
            # If it's already a string, use it directly
            elif isinstance(email_field, str):
                email = email_field
            else:
                email = str(email_field)
        else:
            # Try emails array
            emails = resume_data.get("emails", [])
            if emails and len(emails) > 0:
                email_obj = emails[0]
                if isinstance(email_obj, dict):
                    email = email_obj.get("value", "") or email_obj.get("raw", "")
                else:
                    email = str(email_obj)
        
        # Extract phone - Affinda uses "phoneNumber" (string, list, or array) or "phoneNumbers" (array)
        phone = ""
        phone_field = resume_data.get("phoneNumber") or resume_data.get("phone")
        if phone_field:
            # If it's a list/array, extract the first item
            if isinstance(phone_field, list) and len(phone_field) > 0:
                phone_obj = phone_field[0]
                if isinstance(phone_obj, dict):
                    # Try common fields for phone value
                    parsed_phone = phone_obj.get("parsed", {})
                    if isinstance(parsed_phone, dict):
                        phone = parsed_phone.get("formattedNumber", "") or parsed_phone.get("nationalNumber", "") or parsed_phone.get("rawText", "")
                    else:
                        phone = phone_obj.get("value", "") or phone_obj.get("raw", "") or str(parsed_phone)
                else:
                    phone = str(phone_obj)
            # If it's already a string, use it directly
            elif isinstance(phone_field, str):
                phone = phone_field
            else:
                phone = str(phone_field)
        else:
            # Try phoneNumbers array
            phone_numbers = resume_data.get("phoneNumbers", []) or resume_data.get("phone_numbers", [])
            if phone_numbers and len(phone_numbers) > 0:
                phone_obj = phone_numbers[0]
                if isinstance(phone_obj, dict):
                    parsed_phone = phone_obj.get("parsed", {})
                    if isinstance(parsed_phone, dict):
                        phone = parsed_phone.get("formattedNumber", "") or parsed_phone.get("nationalNumber", "")
                    else:
                        phone = phone_obj.get("value", "") or phone_obj.get("raw", "")
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
            for idx, position in enumerate(work_experience):
                if isinstance(position, dict):
                    # Affinda returns experience entries with 'raw' and 'parsed' fields
                    # The actual data is in the 'parsed' field
                    parsed_exp = position.get("parsed", {})
                    if not parsed_exp and position.get("raw"):
                        # If no parsed field, try to use raw as fallback
                        parsed_exp = {}
                    
                    # Extract from parsed field (the actual structured data)
                    # Affinda uses prefixed field names: workExperienceJobTitle, workExperienceOrganization, etc.
                    if isinstance(parsed_exp, dict):
                        # Job title - Affinda uses workExperienceJobTitle
                        job_title_obj = (parsed_exp.get("workExperienceJobTitle") or 
                                        parsed_exp.get("jobTitle") or 
                                        parsed_exp.get("job_title") or 
                                        parsed_exp.get("title"))
                        if isinstance(job_title_obj, dict):
                            job_title = job_title_obj.get("raw", "") or job_title_obj.get("parsed", "") or ""
                        else:
                            job_title = str(job_title_obj) if job_title_obj else ""
                        
                        # Company/Organization - Affinda uses workExperienceOrganization
                        company_obj = (parsed_exp.get("workExperienceOrganization") or 
                                      parsed_exp.get("organization") or 
                                      parsed_exp.get("company") or 
                                      parsed_exp.get("employer"))
                        if isinstance(company_obj, dict):
                            company = company_obj.get("raw", "") or company_obj.get("parsed", "") or ""
                        else:
                            company = str(company_obj) if company_obj else ""
                        
                        # Dates - Affinda uses workExperienceDates
                        dates_obj = parsed_exp.get("workExperienceDates")
                        if dates_obj:
                            if isinstance(dates_obj, dict):
                                start_date = self._format_date_from_json(dates_obj.get("startDate")) or self._format_date_from_json(dates_obj.get("start_date"))
                                end_date = self._format_date_from_json(dates_obj.get("endDate")) or self._format_date_from_json(dates_obj.get("end_date"))
                            else:
                                # Try direct fields
                                start_date = self._format_date_from_json(parsed_exp.get("startDate")) or self._format_date_from_json(parsed_exp.get("start_date"))
                                end_date = self._format_date_from_json(parsed_exp.get("endDate")) or self._format_date_from_json(parsed_exp.get("end_date"))
                        else:
                            start_date = self._format_date_from_json(parsed_exp.get("startDate")) or self._format_date_from_json(parsed_exp.get("start_date"))
                            end_date = self._format_date_from_json(parsed_exp.get("endDate")) or self._format_date_from_json(parsed_exp.get("end_date"))
                        
                        # Location - Affinda uses workExperienceLocation
                        location_obj = (parsed_exp.get("workExperienceLocation") or 
                                       parsed_exp.get("location", {}))
                        if isinstance(location_obj, dict):
                            location = location_obj.get("city", "") or location_obj.get("raw", "") or location_obj.get("formatted", "") or ""
                        else:
                            location = str(location_obj) if location_obj else ""
                        
                        # Description - Affinda uses workExperienceDescription
                        description_obj = (parsed_exp.get("workExperienceDescription") or 
                                          parsed_exp.get("description") or 
                                          parsed_exp.get("summary"))
                        if isinstance(description_obj, dict):
                            description = description_obj.get("raw", "") or description_obj.get("parsed", "") or ""
                        else:
                            description = str(description_obj) if description_obj else ""
                        
                        # Achievements/Highlights - might be in description or separate
                        achievements = (parsed_exp.get("achievements", []) or 
                                        parsed_exp.get("highlights", []) or 
                                        parsed_exp.get("responsibilities", []))
                        # Handle if achievements is a list of objects
                        if achievements and len(achievements) > 0 and isinstance(achievements[0], dict):
                            achievements = [a.get("raw", "") or a.get("parsed", "") or str(a) for a in achievements if a]
                        
                        exp_entry = {
                            "title": job_title.strip() if job_title else "",
                            "company": company.strip() if company else "",
                            "start_date": start_date or "",
                            "end_date": end_date or "",
                            "location": location.strip() if location else "",
                            "description": description.strip() if description else "",
                            "highlights": achievements if isinstance(achievements, list) else []
                        }
                    else:
                        # Fallback: create empty entry
                        exp_entry = {
                            "title": "",
                            "company": "",
                            "start_date": "",
                            "end_date": "",
                            "location": "",
                            "description": "",
                            "highlights": []
                        }
                    
                    experience.append(exp_entry)
        
        # Extract education
        education = []
        education_list = resume_data.get("education", [])
        if education_list:
            for idx, degree in enumerate(education_list):
                if isinstance(degree, dict):
                    # Affinda returns education entries with 'raw' and 'parsed' fields
                    # The actual data is in the 'parsed' field
                    parsed_edu = degree.get("parsed", {})
                    if not parsed_edu and degree.get("raw"):
                        # If no parsed field, try to use raw as fallback
                        parsed_edu = {}
                    
                    # Extract from parsed field (the actual structured data)
                    # Affinda uses prefixed field names: educationAccreditation, educationOrganization, etc.
                    if isinstance(parsed_edu, dict):
                        # Degree - Affinda uses educationAccreditation or educationLevel
                        degree_obj = (parsed_edu.get("educationAccreditation") or 
                                     parsed_edu.get("educationLevel") or
                                     parsed_edu.get("degree") or 
                                     parsed_edu.get("accreditation") or 
                                     parsed_edu.get("qualification"))
                        if isinstance(degree_obj, dict):
                            degree_name = degree_obj.get("raw", "") or degree_obj.get("parsed", "") or ""
                        else:
                            degree_name = str(degree_obj) if degree_obj else ""
                        
                        # Institution - Affinda uses educationOrganization
                        institution_obj = (parsed_edu.get("educationOrganization") or 
                                          parsed_edu.get("organization") or 
                                          parsed_edu.get("institution") or 
                                          parsed_edu.get("school") or 
                                          parsed_edu.get("university"))
                        if isinstance(institution_obj, dict):
                            institution = institution_obj.get("raw", "") or institution_obj.get("parsed", "") or ""
                        else:
                            institution = str(institution_obj) if institution_obj else ""
                        
                        # Dates - Affinda uses educationDates
                        dates_obj = parsed_edu.get("educationDates")
                        if dates_obj:
                            if isinstance(dates_obj, dict):
                                graduation_date = self._format_date_from_json(dates_obj.get("endDate")) or self._format_date_from_json(dates_obj.get("graduation_date")) or self._format_date_from_json(dates_obj.get("date"))
                            else:
                                graduation_date = self._format_date_from_json(parsed_edu.get("endDate")) or self._format_date_from_json(parsed_edu.get("graduation_date")) or self._format_date_from_json(parsed_edu.get("date"))
                        else:
                            graduation_date = self._format_date_from_json(parsed_edu.get("endDate")) or self._format_date_from_json(parsed_edu.get("graduation_date")) or self._format_date_from_json(parsed_edu.get("date"))
                        
                        # GPA - Affinda uses educationGrade
                        gpa_obj = (parsed_edu.get("educationGrade") or 
                                  parsed_edu.get("gpa"))
                        if isinstance(gpa_obj, dict):
                            gpa = gpa_obj.get("raw", "") or gpa_obj.get("parsed", "") or ""
                        else:
                            gpa = str(gpa_obj) if gpa_obj else ""
                        
                        # Major - Affinda uses educationMajor
                        major_obj = (parsed_edu.get("educationMajor") or 
                                    parsed_edu.get("major"))
                        major = ""
                        if isinstance(major_obj, dict):
                            major = major_obj.get("raw", "") or major_obj.get("parsed", "") or ""
                        elif isinstance(major_obj, list):
                            majors: List[str] = []
                            for m in major_obj:
                                if isinstance(m, dict):
                                    majors.append(m.get("raw", "") or m.get("parsed", "") or m.get("value", "") or "")
                                elif m is not None:
                                    majors.append(str(m))
                            majors = [x.strip() for x in majors if isinstance(x, str) and x.strip()]
                            # De-dupe while preserving order
                            seen = set()
                            majors_deduped = []
                            for x in majors:
                                if x not in seen:
                                    seen.add(x)
                                    majors_deduped.append(x)
                            major = ", ".join(majors_deduped)
                        else:
                            major = str(major_obj) if major_obj else ""
                        
                        edu_entry = {
                            "degree": degree_name.strip() if degree_name else "",
                            "institution": institution.strip() if institution else "",
                            "graduation_date": graduation_date or "",
                            "gpa": gpa.strip() if gpa else "",
                            "major": major.strip() if major else ""
                        }
                    else:
                        # Fallback: create empty entry
                        edu_entry = {
                            "degree": "",
                            "institution": "",
                            "graduation_date": "",
                            "gpa": "",
                            "major": ""
                        }
                    
                    education.append(edu_entry)
        
        # Extract skills - Affinda may use "skill" (singular) or "skills" (plural)
        # Skills might also be in parsed objects with 'raw' and 'parsed' fields
        skills = []
        skills_list = resume_data.get("skill", []) or resume_data.get("skills", [])
        if skills_list:
            for skill in skills_list:
                skill_name = ""
                if isinstance(skill, dict):
                    # Check if it's a structured object with raw/parsed
                    if "raw" in skill or "parsed" in skill:
                        skill_name = skill.get("raw", "") or skill.get("parsed", "") or ""
                    else:
                        # Try standard fields
                        skill_name = skill.get("name", "") or skill.get("value", "") or skill.get("skill", "")
                else:
                    skill_name = str(skill)
                
                if skill_name and skill_name.strip() and skill_name not in skills:
                    skills.append(skill_name.strip())
        
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
        
        # Extract languages - Affinda may use "language" (singular) or "languages" (plural)
        languages = []
        langs_list = resume_data.get("language", []) or resume_data.get("languages", [])
        if langs_list:
            for lang in langs_list:
                if isinstance(lang, dict):
                    lang_name = lang.get("name", "") or lang.get("value", "")
                else:
                    lang_name = str(lang)
                if lang_name:
                    languages.append(lang_name)
        
        # Extract projects
        projects = []
        projects_list = resume_data.get("project", []) or resume_data.get("projects", [])
        if projects_list:
            for project in projects_list:
                if isinstance(project, dict):
                    # Projects might have raw/parsed structure
                    parsed_proj = project.get("parsed", {})
                    if isinstance(parsed_proj, dict):
                        project_name = parsed_proj.get("name", "") or parsed_proj.get("title", "") or project.get("raw", "")
                        project_desc = parsed_proj.get("description", "") or parsed_proj.get("summary", "")
                    else:
                        project_name = project.get("name", "") or project.get("title", "") or project.get("raw", "")
                        project_desc = project.get("description", "") or project.get("summary", "")
                    
                    if project_name or project_desc:
                        projects.append({
                            "name": str(project_name).strip() if project_name else "",
                            "description": str(project_desc).strip() if project_desc else ""
                        })
                else:
                    projects.append({"name": str(project).strip(), "description": ""})
        
        # Extract achievements
        achievements = []
        achievements_list = resume_data.get("achievement", []) or resume_data.get("achievements", [])
        if achievements_list:
            for achievement in achievements_list:
                if isinstance(achievement, dict):
                    # Achievements might have raw/parsed structure
                    parsed_ach = achievement.get("parsed", {})
                    if isinstance(parsed_ach, dict):
                        ach_name = parsed_ach.get("name", "") or parsed_ach.get("title", "") or achievement.get("raw", "")
                        ach_desc = parsed_ach.get("description", "") or parsed_ach.get("summary", "")
                    else:
                        ach_name = achievement.get("name", "") or achievement.get("title", "") or achievement.get("raw", "")
                        ach_desc = achievement.get("description", "") or achievement.get("summary", "")
                    
                    if ach_name or ach_desc:
                        achievements.append({
                            "name": str(ach_name).strip() if ach_name else "",
                            "description": str(ach_desc).strip() if ach_desc else ""
                        })
                else:
                    achievements.append({"name": str(achievement).strip(), "description": ""})
        
        # Extract associations/extracurriculars
        associations = []
        associations_list = resume_data.get("association", []) or resume_data.get("associations", [])
        if associations_list:
            for association in associations_list:
                if isinstance(association, dict):
                    # Associations might have raw/parsed structure
                    parsed_assoc = association.get("parsed", {})
                    if isinstance(parsed_assoc, dict):
                        assoc_name = parsed_assoc.get("name", "") or parsed_assoc.get("organization", "") or association.get("raw", "")
                        assoc_role = parsed_assoc.get("role", "") or parsed_assoc.get("position", "")
                    else:
                        assoc_name = association.get("name", "") or association.get("organization", "") or association.get("raw", "")
                        assoc_role = association.get("role", "") or association.get("position", "")
                    
                    if assoc_name:
                        associations.append({
                            "name": str(assoc_name).strip() if assoc_name else "",
                            "role": str(assoc_role).strip() if assoc_role else ""
                        })
                else:
                    associations.append({"name": str(association).strip(), "role": ""})
        
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
            "projects": projects,
            "achievements": achievements,
            "associations": associations,
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

