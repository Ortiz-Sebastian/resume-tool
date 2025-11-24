"""
ATS Issue Detector - Rule-based detection of formatting issues.

Uses structured ATSIssue model for all detections.
"""

import fitz  # PyMuPDF
from typing import Dict, Any, List, Tuple, Optional, Set
import re

from .ats_issues import ATSIssue, IssueSeverity, IssueSection


class ATSIssueDetector:
    """Detect ATS formatting issues using business rules (not AI)"""
    
    def __init__(self):
        self.severity_colors = {
            "critical": "#EF4444",  # Red
            "high": "#F97316",      # Orange
            "medium": "#EAB308",    # Yellow
            "low": "#3B82F6"        # Blue
        }
    
    def detect_issues(
        self,
        file_path: str,
        file_type: str,
        parsed_data: Dict[str, Any],
        ats_diagnostics: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Main entry point: detect all issues and return in legacy highlight format.
        
        Single source of truth for ALL issue detection (visual + diagnostics).
        
        Returns dict with highlights, summary, recommendations, and issue list.
        """
        if file_type != ".pdf":
            return self._empty_result("Only PDF analysis is supported")
        
        # Extract blocks with metadata
        blocks = self._extract_blocks_with_metadata(file_path)
        
        # Run all detections - returns List[ATSIssue]
        issues = self._detect_all_issues(file_path, blocks, parsed_data, ats_diagnostics)
        
        # Convert to legacy format (skip issues with no bbox - they're document-wide)
        highlights = [self._issue_to_highlight(issue) for issue in issues if issue.bbox is not None]
        
        # Generate recommendations based on detected issues
        recommendations = self._issues_to_recommendations(issues)
        
        # Convert issues to simple string messages for the issues list
        issue_messages = [issue.message for issue in issues]
        
        summary = self._calculate_summary(highlights)
        
        return {
            "highlights": highlights,
            "summary": summary,
            "recommendations": recommendations,
            "issues": issue_messages  # String list for "Issues Detected" panel
        }
    
    def _detect_all_issues(
        self,
        file_path: str,
        blocks: List[Dict[str, Any]],
        parsed_data: Dict[str, Any],
        ats_diagnostics: Dict[str, Any] = None
    ) -> List[ATSIssue]:
        """Run all detection rules and return structured issues"""
        issues = []
        
        # A. Diagnostics-based detection (from ATSViewGenerator)
        if ats_diagnostics:
            issues.extend(self._detect_from_diagnostics(ats_diagnostics))
        
        # B. Visual/layout-based detection (from PyMuPDF analysis)
        # 1. Scanned PDF
        issues.extend(self._detect_scanned_pdf(file_path))
        
        # 2. Contact issues
        issues.extend(self._detect_contact_issues(blocks, parsed_data))
        
        # 3. Skills issues
        issues.extend(self._detect_skills_issues(blocks, parsed_data))
        
        # 4. Experience issues
        issues.extend(self._detect_experience_issues(blocks, parsed_data))
        
        # 5. Education issues
        issues.extend(self._detect_education_issues(blocks, parsed_data))
        
        # 6. Images
        issues.extend(self._detect_images(file_path))
        
        # 7. Floating text boxes
        issues.extend(self._detect_floating_text_boxes(blocks))
        
        # 8. Icons
        issues.extend(self._detect_icons(file_path, parsed_data))
        
        # 9. Date format issues
        issues.extend(self._detect_date_format_issues(blocks))
        
        # 10. Font issues
        issues.extend(self._detect_font_issues(file_path, blocks))
        
        # 11. Unmapped content
        issues.extend(self._detect_unmapped_content(blocks, parsed_data))
        
        return issues
    
    def _detect_from_diagnostics(self, ats_diagnostics: Dict[str, Any]) -> List[ATSIssue]:
        """Detect issues from ATS diagnostics (tables, images, headers, complexity)"""
        issues = []
        
        # Images issue
        if ats_diagnostics.get("has_images"):
            issues.append(ATSIssue(
                code="has_images",
                severity=IssueSeverity.HIGH,
                section=IssueSection.GENERAL,
                message="Resume contains images that ATS systems cannot read",
                details="Images, logos, and graphics are invisible to ATS. Replace with text-only formatting.",
                page=1,
                bbox=None  # Document-wide
            ))
        
        # Tables issue
        if ats_diagnostics.get("has_tables"):
            issues.append(ATSIssue(
                code="has_tables",
                severity=IssueSeverity.MEDIUM,
                section=IssueSection.GENERAL,
                message="Resume contains tables - ATS may misread content order",
                details="Tables can cause content to be read in wrong order. Use simple text formatting instead.",
                page=1,
                bbox=None  # Document-wide
            ))
        
        # Headers/footers issue
        if ats_diagnostics.get("has_headers_footers"):
            issues.append(ATSIssue(
                code="has_headers_footers",
                severity=IssueSeverity.MEDIUM,
                section=IssueSection.CONTACT,
                message="Headers or footers detected - ATS may miss this content",
                details="Contact info in headers/footers is often missed by ATS. Move to main body.",
                page=1,
                bbox=None  # Document-wide
            ))
        
        # Complex layout issue
        if ats_diagnostics.get("layout_complexity") == "complex":
            issues.append(ATSIssue(
                code="complex_layout",
                severity=IssueSeverity.HIGH,
                section=IssueSection.GENERAL,
                message="Resume has complex layout that reduces ATS compatibility",
                details="Complex formatting detected (tables, images, or multi-column layout). Simplify to single-column with standard formatting.",
                page=1,
                bbox=None  # Document-wide
            ))
        
        return issues
    
    # ========== BLOCK EXTRACTION ========== #
    
    def _extract_blocks_with_metadata(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract PDF blocks with rich metadata"""
        doc = fitz.open(file_path)
        blocks = []
        
        for page_num, page in enumerate(doc):
            rect = page.rect
            page_height = rect.height
            page_width = rect.width
            
            # Get text blocks
            text_dict = page.get_text("dict")
            page_blocks = []
            
            for block in text_dict["blocks"]:
                if block["type"] == 0:  # Text block
                    bbox = block["bbox"]
                    text = self._extract_text_from_block(block)
                    
                    if text:
                        page_blocks.append({
                            "text": text,
                            "bbox": bbox,
                            "block_data": block
                        })
            
            # Detect layout features
            columns = self._detect_columns(page_blocks, page_width)
            tables = self._detect_tables(page_blocks)
            text_boxes = self._detect_text_boxes(page_blocks, page_width)
            
            # Build enriched blocks
            for i, pb in enumerate(page_blocks):
                bbox = pb["bbox"]
                blocks.append({
                    "text": pb["text"],
                    "bbox": bbox,
                    "page": page_num + 1,
                    "region": self._determine_region(bbox, page_height),
                    "in_table": i in tables,
                    "column": columns.get(i, 1),
                    "in_text_box": i in text_boxes,
                    "fonts": self._extract_fonts(pb["block_data"]),
                    "page_width": page_width,
                    "page_height": page_height
                })
        
        doc.close()
        return blocks
    
    def _extract_text_from_block(self, block: Dict[str, Any]) -> str:
        """Extract text from PDF block"""
        text = ""
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text += span.get("text", "") + " "
        return text.strip()
    
    def _extract_fonts(self, block: Dict[str, Any]) -> List[str]:
        """Extract font names from block"""
        fonts = set()
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                fonts.add(span.get("font", ""))
        return list(fonts)
    
    # ========== LAYOUT DETECTION ========== #
    
    def _detect_columns(self, blocks: List[Dict[str, Any]], page_width: float) -> Dict[int, int]:
        """Detect multi-column layout"""
        if not blocks:
            return {}
        
        x_positions = [(i, block["bbox"][0]) for i, block in enumerate(blocks)]
        x_sorted = sorted(x_positions, key=lambda x: x[1])
        
        gap_threshold = page_width * 0.2
        column_assignments = {}
        current_column = 1
        
        for i in range(len(x_sorted)):
            idx, x_pos = x_sorted[i]
            column_assignments[idx] = current_column
            
            if i < len(x_sorted) - 1:
                next_x = x_sorted[i + 1][1]
                if next_x - x_pos > gap_threshold:
                    current_column += 1
        
        return column_assignments
    
    def _detect_tables(self, blocks: List[Dict[str, Any]]) -> Set[int]:
        """Detect table-like structures"""
        if len(blocks) < 4:
            return set()
        
        table_blocks = set()
        y_threshold = 5
        
        # Group blocks by row
        rows = {}
        for i, block in enumerate(blocks):
            y0 = block["bbox"][1]
            found_row = False
            
            for row_y in rows:
                if abs(y0 - row_y) < y_threshold:
                    rows[row_y].append((i, block))
                    found_row = True
                    break
            
            if not found_row:
                rows[y0] = [(i, block)]
        
        # Check each row for table patterns
        for row_blocks in rows.values():
            if len(row_blocks) >= 3:
                x_positions = sorted([b[1]["bbox"][0] for b in row_blocks])
                
                if len(x_positions) >= 3:
                    gaps = [x_positions[i+1] - x_positions[i] for i in range(len(x_positions)-1)]
                    avg_gap = sum(gaps) / len(gaps)
                    
                    if all(abs(gap - avg_gap) < avg_gap * 0.5 for gap in gaps):
                        for idx, _ in row_blocks:
                            table_blocks.add(idx)
        
        return table_blocks
    
    def _detect_text_boxes(self, blocks: List[Dict[str, Any]], page_width: float) -> Set[int]:
        """Detect floating text boxes"""
        text_box_blocks = set()
        
        for i, block in enumerate(blocks):
            bbox = block["bbox"]
            x0, x1 = bbox[0], bbox[2]
            width = x1 - x0
            
            left_margin = x0
            right_margin = page_width - x1
            
            is_narrow = width < page_width * 0.3
            is_isolated = left_margin > page_width * 0.15 and right_margin > page_width * 0.15
            
            if is_narrow and is_isolated:
                text_box_blocks.add(i)
        
        return text_box_blocks
    
    def _determine_region(self, bbox: Tuple[float, float, float, float], page_height: float) -> str:
        """Determine if block is in header, footer, or body"""
        y0, y1 = bbox[1], bbox[3]
        
        if y0 < page_height * 0.1:
            return "header"
        elif y1 > page_height * 0.9:
            return "footer"
        else:
            return "body"
    
    # ========== SECTION FINDING HELPERS ========== #
    
    def _find_section_blocks(
        self,
        blocks: List[Dict[str, Any]],
        section_headers: List[str],
        max_blocks: int = 8
    ) -> List[Tuple[int, Dict[str, Any]]]:
        """Find blocks belonging to a specific section"""
        for idx, block in enumerate(blocks):
            text_lower = block.get("text", "").lower().strip()
            if any(header in text_lower for header in section_headers) and len(text_lower) < 50:
                # Found header, collect subsequent blocks
                return [(j, blocks[j]) for j in range(idx, min(idx + max_blocks, len(blocks)))]
        return []
    
    def _diagnose_section_formatting(self, section_blocks: List[Tuple[int, Dict[str, Any]]]) -> List[str]:
        """Diagnose formatting issues in a section"""
        issues = []
        
        if not section_blocks:
            return issues
        
        for idx, block in section_blocks:
            if block.get("in_table"):
                issues.append("Content in table/grid format")
                break
        
        if section_blocks:
            first_block = section_blocks[0][1]
            page_width = first_block.get("page_width", 612)
            x_pos = first_block["bbox"][0]
            
            if x_pos > page_width * 0.6:
                issues.append("Content in sidebar/secondary column")
            elif first_block["bbox"][2] - first_block["bbox"][0] < page_width * 0.4:
                issues.append("Content in narrow column")
        
        text = " ".join([b.get("text", "") for _, b in section_blocks])
        if '|' in text:
            issues.append("Pipe separators used (|)")
        if text.count(',') > 5:
            issues.append("Comma-separated format")
        
        for idx, block in section_blocks:
            if block.get("region") in ["header", "footer"]:
                issues.append(f"Content in {block.get('region')} region")
                break
        
        return issues
    
    # ========== ISSUE DETECTORS ========== #
    
    def _detect_scanned_pdf(self, file_path: str) -> List[ATSIssue]:
        """Detect scanned/image-only PDFs"""
        doc = fitz.open(file_path)
        
        total_chars = 0
        total_images = 0
        
        for page in doc:
            text = page.get_text("text")
            total_chars += len(text.strip())
            total_images += len(page.get_images())
        
        first_page_bbox = [0, 0, 612, 792]  # Default letter size
        if len(doc) > 0:
            rect = doc[0].rect
            first_page_bbox = [rect.x0, rect.y0, rect.x1, rect.y1]
        
        doc.close()
        
        if total_chars < 100 and total_images > 0:
            return [ATSIssue(
                code="scanned_pdf",
                severity=IssueSeverity.CRITICAL,
                section=IssueSection.GENERAL,
                message="Image-based or scanned PDF",
                details="Your resume appears to be an image-based or scanned PDF with very little extractable text. ATS systems cannot read image-based content. Please export your resume as a text-based PDF from Word, Google Docs, or your resume editor.",
                page=1,
                bbox=None,  # Document-wide issue - no specific location
                location_hint="Entire document"
            )]
        
        return []
    
    def _detect_contact_issues(
        self,
        blocks: List[Dict[str, Any]],
        parsed_data: Dict[str, Any]
    ) -> List[ATSIssue]:
        """Detect contact information issues"""
        issues = []
        
        contact_info = parsed_data.get("contact_info", {}) or {}
        email = contact_info.get("email") or parsed_data.get("email")
        phone = contact_info.get("phone") or parsed_data.get("phone")
        
        # Patterns
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        phone_pattern = r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'
        linkedin_pattern = r'(?:linkedin\.com/in/|linkedin\.com/pub/)[\w-]+'
        
        all_text = "\n".join([b.get("text", "") for b in blocks])
        
        # Email issues
        emails_in_text = re.findall(email_pattern, all_text)
        if emails_in_text and not email:
            for block in blocks:
                if re.search(email_pattern, block.get("text", "")):
                    if block.get("region") in ["header", "footer"]:
                        issues.append(self._create_issue(
                            code="contact_email_in_header_footer",
                            severity=IssueSeverity.CRITICAL,
                            section=IssueSection.CONTACT,
                            message="Email in header/footer not extracted",
                            details=f"Your email address '{emails_in_text[0]}' is visible on the resume but was NOT extracted by the ATS parser. This is CRITICAL. Likely cause: Email is in header/footer region which ATS often ignores. Fix: Move your email to the main body, directly under your name.",
                            block=block
                        ))
                    break
        
        # Phone issues
        phones_in_text = re.findall(phone_pattern, all_text)
        if phones_in_text and not phone:
            for block in blocks:
                if re.search(phone_pattern, block.get("text", "")):
                    if block.get("region") in ["header", "footer"]:
                        issues.append(self._create_issue(
                            code="contact_phone_in_header_footer",
                            severity=IssueSeverity.HIGH,
                            section=IssueSection.CONTACT,
                            message="Phone in header/footer not extracted",
                            details="Your phone number is visible but was NOT extracted by the ATS parser. Likely cause: Phone is in header/footer. Fix: Use standard format like (555) 123-4567 in the main body.",
                            block=block
                        ))
                    break
        
        # LinkedIn issues
        linkedin = contact_info.get("linkedin") or parsed_data.get("linkedin")
        linkedin_in_text = re.findall(linkedin_pattern, all_text, re.IGNORECASE)
        if linkedin_in_text and not linkedin:
            for block in blocks:
                if re.search(linkedin_pattern, block.get("text", ""), re.IGNORECASE):
                    issues.append(self._create_issue(
                        code="contact_linkedin_not_extracted",
                        severity=IssueSeverity.MEDIUM,
                        section=IssueSection.CONTACT,
                        message="LinkedIn not extracted by ATS",
                        details="Your LinkedIn URL is visible but was NOT extracted by the ATS. Likely causes: LinkedIn displayed as icon only, or in header/footer. Fix: Write full URL as text: linkedin.com/in/yourname",
                        block=block
                    ))
                    break
        
        return issues
    
    def _detect_skills_issues(
        self,
        blocks: List[Dict[str, Any]],
        parsed_data: Dict[str, Any]
    ) -> List[ATSIssue]:
        """Detect skills section issues"""
        issues = []
        
        skills = parsed_data.get("skills", [])
        skill_count = len(skills)
        
        # Find skills section
        skill_headers = ['skills', 'technical skills', 'core competencies', 'technologies', 'expertise', 'proficiencies']
        section_blocks = self._find_section_blocks(blocks, skill_headers)
        
        if not section_blocks:
            if skill_count == 0:
                issues.append(ATSIssue(
                    code="skills_no_section",
                    severity=IssueSeverity.HIGH,
                    section=IssueSection.SKILLS,
                    message="No dedicated Skills section detected",
                    details="ATS extracted 0 skills. Your resume appears to have no dedicated Skills section. Best practice: Always include a clear Skills section with a header like 'SKILLS' or 'TECHNICAL SKILLS'.",
                    page=1,
                    bbox=None,  # Document-wide issue
                    location_hint="Skills section missing"
                ))
            return issues
        
        # Skills section exists - check extraction quality
        first_block = section_blocks[0][1]
        formatting_issues = self._diagnose_section_formatting(section_blocks)
        
        if skill_count == 0:
            issues.append(ATSIssue(
                code="skills_section_unreadable",
                severity=IssueSeverity.CRITICAL,
                section=IssueSection.SKILLS,
                message="Skills section not extracted by ATS",
                details=f"ATS extracted 0 skills despite a Skills section being present. Detected formatting problems: {', '.join(formatting_issues) if formatting_issues else 'Unknown formatting issues'}. Fix: Use simple bullet points in the main body.",
                page=first_block.get("page", 1),
                bbox=first_block["bbox"],
                location_hint=f"Skills section on page {first_block.get('page', 1)}"
            ))
        elif skill_count < 3 and formatting_issues:
            issues.append(ATSIssue(
                code="skills_partially_extracted",
                severity=IssueSeverity.HIGH,
                section=IssueSection.SKILLS,
                message=f"Only {skill_count} skill(s) extracted by ATS",
                details=f"ATS extracted only {skill_count} skill(s). Detected formatting issues: {', '.join(formatting_issues)}. These formatting issues likely prevented full extraction.",
                page=first_block.get("page", 1),
                bbox=first_block["bbox"],
                location_hint=f"Skills section on page {first_block.get('page', 1)}"
            ))
        
        return issues
    
    def _detect_experience_issues(
        self,
        blocks: List[Dict[str, Any]],
        parsed_data: Dict[str, Any]
    ) -> List[ATSIssue]:
        """Detect work experience issues"""
        issues = []
        
        experience = parsed_data.get("experience", [])
        
        # Find experience section
        exp_headers = ['experience', 'work experience', 'employment', 'work history', 'professional experience']
        section_blocks = self._find_section_blocks(blocks, exp_headers, max_blocks=20)
        
        if not section_blocks:
            return issues
        
        first_block = section_blocks[0][1]
        
        # No experience extracted
        if len(experience) == 0:
            formatting_issues = self._diagnose_section_formatting(section_blocks)
            issues.append(ATSIssue(
                code="experience_not_extracted",
                severity=IssueSeverity.CRITICAL,
                section=IssueSection.EXPERIENCE,
                message="Experience section not extracted by ATS",
                details=f"ATS extracted 0 jobs from your Experience section. {f'Detected formatting issues: {chr(10).join(formatting_issues)}' if formatting_issues else 'Likely causes: Jobs in table format, multi-column layout, or missing job titles/dates'}. Fix: Use simple format: Job Title | Company, Month Year - Month Year, • Achievement",
                page=first_block.get("page", 1),
                bbox=first_block["bbox"],
                location_hint=f"Experience section on page {first_block.get('page', 1)}"
            ))
        else:
            # Check for jobs without bullets
            jobs_without_bullets = sum(1 for job in experience if not job.get("bullets") or len(job.get("bullets", [])) == 0)
            if jobs_without_bullets > 0:
                issues.append(ATSIssue(
                    code="experience_no_bullets",
                    severity=IssueSeverity.HIGH,
                    section=IssueSection.EXPERIENCE,
                    message=f"{jobs_without_bullets} job(s) missing bullet points",
                    details=f"ATS extracted {len(experience)} jobs, but {jobs_without_bullets} have no bullet points/descriptions. Likely causes: Descriptions in paragraph format, bullets in a table, or unusual bullet characters. Fix: Use standard bullet points (•, -, or *) for each job.",
                    page=first_block.get("page", 1),
                    bbox=first_block["bbox"],
                    location_hint=f"Experience section on page {first_block.get('page', 1)}"
                ))
            
            # Check for incomplete jobs
            incomplete_jobs = sum(1 for job in experience if not job.get("title") or not job.get("company"))
            if incomplete_jobs > 0:
                issues.append(ATSIssue(
                    code="experience_incomplete",
                    severity=IssueSeverity.HIGH,
                    section=IssueSection.EXPERIENCE,
                    message=f"{incomplete_jobs} job(s) missing title or company",
                    details=f"{incomplete_jobs} job entries are missing critical information (title or company name). Ensure each job clearly shows: Job Title, Company Name, Date Range.",
                    page=first_block.get("page", 1),
                    bbox=first_block["bbox"],
                    location_hint=f"Experience section on page {first_block.get('page', 1)}"
                ))
        
        return issues
    
    def _detect_education_issues(
        self,
        blocks: List[Dict[str, Any]],
        parsed_data: Dict[str, Any]
    ) -> List[ATSIssue]:
        """Detect education section issues"""
        issues = []
        
        education = parsed_data.get("education", [])
        
        # Find education section
        edu_headers = ['education', 'academic', 'academic background', 'qualifications']
        section_blocks = self._find_section_blocks(blocks, edu_headers, max_blocks=10)
        
        if not section_blocks:
            return issues
        
        first_block = section_blocks[0][1]
        
        # No education extracted
        if len(education) == 0:
            formatting_issues = self._diagnose_section_formatting(section_blocks)
            issues.append(ATSIssue(
                code="education_not_extracted",
                severity=IssueSeverity.HIGH,
                section=IssueSection.EDUCATION,
                message="Education not extracted by ATS",
                details=f"ATS extracted 0 education entries. {f'Detected formatting issues: {chr(10).join(formatting_issues)}' if formatting_issues else 'Likely causes: Education in table format, non-standard degree names, or missing university name'}. Fix: Use clear format: Degree Name, University Name, Graduation Date.",
                page=first_block.get("page", 1),
                bbox=first_block["bbox"],
                location_hint=f"Education section on page {first_block.get('page', 1)}"
            ))
        else:
            # Check for incomplete entries
            incomplete_edu = sum(1 for edu in education if not edu.get("degree") or not edu.get("institution"))
            if incomplete_edu > 0:
                issues.append(ATSIssue(
                    code="education_incomplete",
                    severity=IssueSeverity.MEDIUM,
                    section=IssueSection.EDUCATION,
                    message=f"{incomplete_edu} education entry(ies) incomplete",
                    details=f"{incomplete_edu} education entries are missing degree name or university name. Ensure each entry clearly shows: Degree Name, University/Institution Name, Graduation Date (or expected).",
                    page=first_block.get("page", 1),
                    bbox=first_block["bbox"],
                    location_hint=f"Education section on page {first_block.get('page', 1)}"
                ))
        
        return issues
    
    def _detect_images(self, file_path: str) -> List[ATSIssue]:
        """Detect images that may contain important content"""
        issues = []
        doc = fitz.open(file_path)
        
        for page_num, page in enumerate(doc):
            images = page.get_images()
            
            for img in images:
                img_rect = page.get_image_bbox(img[7])
                if img_rect:
                    issues.append(ATSIssue(
                        code="image_content",
                        severity=IssueSeverity.CRITICAL,
                        section=IssueSection.GENERAL,
                        message="Image detected",
                        details="Images, logos, charts, and graphics are completely invisible to ATS systems. If this image contains important information (skills, achievements, contact info), it will be missed. Replace with plain text.",
                        page=page_num + 1,
                        bbox=[img_rect.x0, img_rect.y0, img_rect.x1, img_rect.y1],
                        location_hint=f"Image on page {page_num + 1}"
                    ))
        
        doc.close()
        return issues
    
    def _detect_floating_text_boxes(self, blocks: List[Dict[str, Any]]) -> List[ATSIssue]:
        """Detect floating text boxes"""
        issues = []
        
        for block in blocks:
            if block.get("in_text_box", False):
                issues.append(self._create_issue(
                    code="floating_text_box",
                    severity=IssueSeverity.MEDIUM,
                    section=IssueSection.GENERAL,
                    message="Floating text box detected",
                    details="This content appears to be in a floating text box. ATS systems may read these out of order or miss them entirely. Move this content to the main text flow.",
                    block=block
                ))
        
        return issues
    
    def _detect_icons(self, file_path: str, parsed_data: Dict[str, Any]) -> List[ATSIssue]:
        """Detect icons used instead of text"""
        issues = []
        doc = fitz.open(file_path)
        
        contact_info = parsed_data.get("contact_info", {}) or {}
        missing_email = not (contact_info.get("email") or parsed_data.get("email"))
        missing_phone = not (contact_info.get("phone") or parsed_data.get("phone"))
        few_skills = len(parsed_data.get("skills", [])) < 3
        
        for page_num, page in enumerate(doc):
            rect = page.rect
            images = page.get_images()
            
            if len(images) > 0 and (missing_email or missing_phone or few_skills):
                for img in images:
                    try:
                        img_rect = page.get_image_bbox(img[7])
                        if img_rect:
                            img_width = img_rect.x1 - img_rect.x0
                            img_height = img_rect.y1 - img_rect.y0
                            img_y = img_rect.y0
                            
                            is_small = (img_width * img_height) < (rect.width * rect.height * 0.01)
                            is_near_top = img_y < rect.height * 0.2
                            
                            if is_small and is_near_top:
                                issues.append(ATSIssue(
                                    code="icon_usage",
                                    severity=IssueSeverity.HIGH,
                                    section=IssueSection.CONTACT,
                                    message="Icon detected (possibly contact info)",
                                    details="Small icons or graphics detected near the top of your resume. If you're using icons for contact information (email, phone, LinkedIn), ATS systems cannot read them. Always include text versions of all contact details and social links.",
                                    page=page_num + 1,
                                    bbox=[img_rect.x0, img_rect.y0, img_rect.x1, img_rect.y1],
                                    location_hint=f"Top of page {page_num + 1}"
                                ))
                                break
                    except:
                        pass
        
        doc.close()
        return issues
    
    def _detect_date_format_issues(self, blocks: List[Dict[str, Any]]) -> List[ATSIssue]:
        """Detect incorrect date formatting"""
        issues = []
        
        bad_patterns = [
            (r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*['']\d{2}\b",
             "date_format_apostrophe_year",
             "Date with apostrophe (e.g., Jan '21)",
             "Dates with apostrophes like \"Jan '21\" can confuse ATS parsers. Use full 4-digit years: \"Jan 2021\" or \"January 2021\"."),
            (r"\b\d{4}\s*[-–—]\s*\d{4}\b(?!\s*\()",
             "date_format_year_only",
             "Year-only dates (e.g., 2021 - 2023)",
             "Using only years without months (e.g., \"2021 - 2023\") makes it harder for ATS to calculate tenure. Include months: \"Jan 2021 - Mar 2023\"."),
            (r"\b\d{1}/\d{4}\b",
             "date_format_single_digit_month",
             "Single-digit month (e.g., 1/2021)",
             "Single-digit months like \"1/2021\" should use two digits or month names. Use \"01/2021\" or \"Jan 2021\" instead."),
        ]
        
        flagged_blocks = set()
        
        for block in blocks:
            text = block["text"]
            block_id = (block["page"], tuple(block["bbox"]))
            
            if block_id in flagged_blocks:
                continue
            
            for pattern, code, short_msg, long_msg in bad_patterns:
                matches = list(re.finditer(pattern, text, re.IGNORECASE))
                
                if matches:
                    match = matches[0]
                    flagged_blocks.add(block_id)
                    
                    issues.append(ATSIssue(
                        code=code,
                        severity=IssueSeverity.MEDIUM,
                        section=IssueSection.GENERAL,
                        message=short_msg,
                        details=long_msg + f"\n\nFound: \"{match.group()}\"",
                        page=block["page"],
                        bbox=block["bbox"],
                        location_hint=f"Page {block['page']}"
                    ))
                    break
        
        return issues
    
    def _detect_font_issues(self, file_path: str, blocks: List[Dict[str, Any]]) -> List[ATSIssue]:
        """Detect uncommon fonts that may confuse ATS"""
        issues = []
        
        # ATS-friendly fonts
        ats_friendly = {
            'cambria', 'garamond', 'georgia', 'palatino', 'times', 'times new roman',
            'arial', 'calibri', 'helvetica', 'tahoma', 'verdana', 'trebuchet'
        }
        
        # Decorative fonts to avoid
        decorative = {
            'comic sans', 'comicsans', 'papyrus', 'brush script', 'curlz', 'impact'
        }
        
        doc = fitz.open(file_path)
        all_fonts = set()
        
        for page in doc:
            text_dict = page.get_text("dict")
            for block in text_dict.get("blocks", []):
                if block.get("type") == 0:
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            font_name = span.get("font", "").lower().strip()
                            if font_name:
                                cleaned = self._clean_font_name(font_name)
                                if cleaned:
                                    all_fonts.add(cleaned)
        
        doc.close()
        
        # Check for decorative fonts
        for font in all_fonts:
            if any(dec in font for dec in decorative):
                issues.append(ATSIssue(
                    code="decorative_font",
                    severity=IssueSeverity.HIGH,
                    section=IssueSection.GENERAL,
                    message=f"Decorative font: {font.title()}",
                    details=f"Your resume uses '{font.title()}', which is a decorative font that is very difficult for ATS systems to read accurately. Replace with ATS-friendly fonts like Arial, Calibri, or Georgia.",
                    page=1,
                    bbox=None,  # No visual highlight for document-wide issues
                    location_hint="Throughout document"
                ))
        
        # Check for uncommon fonts
        uncommon = [f for f in all_fonts if not any(friendly in f for friendly in ats_friendly) and not any(dec in f for dec in decorative)]
        if uncommon:
            issues.append(ATSIssue(
                code="uncommon_font",
                severity=IssueSeverity.MEDIUM,
                section=IssueSection.GENERAL,
                message=f"Uncommon font detected",
                details=f"Your resume uses fonts that may not be widely available on ATS systems: {', '.join(f.title() for f in uncommon[:3])}. For maximum ATS compatibility, use widely supported fonts like Arial, Calibri, Georgia, or Times New Roman.",
                page=1,
                bbox=None,  # No visual highlight for document-wide issues
                location_hint="Throughout document"
            ))
        
        # Note: Multiple fonts check removed - not always applicable
        
        return issues
    
    def _detect_unmapped_content(
        self,
        blocks: List[Dict[str, Any]],
        parsed_data: Dict[str, Any]
    ) -> List[ATSIssue]:
        """Detect content that wasn't parsed (may be ignored by ATS)"""
        issues = []
        
        # Collect all text from parsed data
        parsed_fragments = self._collect_parsed_fragments(parsed_data)
        
        # Check blocks for unmapped content
        for block in blocks:
            text_lower = block["text"].lower().strip()
            
            # Skip short blocks
            if len(text_lower) < 10:
                continue
            
            # Only flag longer, substantial blocks that are truly unmapped
            # Increased threshold to 80 chars to reduce false positives
            if not self._is_content_mapped(text_lower, parsed_fragments) and len(text_lower) > 80:
                # Check if it's a common section header or metadata
                if self._is_section_header_or_metadata(text_lower):
                    continue
                
                # Only flag body content (not headers/footers/sidebars)
                if block["region"] == "body":
                    # Additional check: skip if it looks like a job description bullet
                    # (contains action verbs and technical terms)
                    if self._looks_like_experience_bullet(text_lower):
                        continue
                    
                    # Create a preview of the content (first 60 chars)
                    preview = block["text"].strip()[:60]
                    if len(block["text"].strip()) > 60:
                        preview += "..."
                    
                    issues.append(self._create_issue(
                        code="unmapped_content",
                        severity=IssueSeverity.LOW,
                        section=IssueSection.GENERAL,
                        message=f"Unmapped content: \"{preview}\"",
                        details="This content doesn't clearly map to standard resume sections (experience, education, skills). ATS systems may skip or misclassify it. Ensure important information is in clearly labeled sections.",
                        block=block
                    ))
        
        return issues
    
    def _collect_parsed_fragments(self, parsed_data: Dict[str, Any]) -> Set[str]:
        """Collect all text fragments from parsed data"""
        fragments = set()
        
        # Contact info
        contact_info = parsed_data.get("contact_info", {}) or {}
        for key in ["email", "phone", "name", "linkedin"]:
            val = contact_info.get(key) or parsed_data.get(key)
            if val:
                fragments.add(str(val).lower())
        
        # Skills
        for skill in parsed_data.get("skills", []):
            fragments.add(skill.lower())
        
        # Experience
        for exp in parsed_data.get("experience", []):
            for key in ["title", "company", "dates", "location", "description"]:
                if exp.get(key):
                    val = exp[key].lower().strip()
                    fragments.add(val)
                    # Add significant chunks
                    if len(val) > 30:
                        words = val.split()
                        for i in range(len(words) - 3):
                            fragments.add(' '.join(words[i:i+4]))
            
            for bullet in exp.get("bullets", []):
                if bullet and len(bullet) > 5:
                    clean_bullet = bullet.lower().strip()
                    fragments.add(clean_bullet)
                    # Add multiple overlapping chunks for better matching
                    if len(clean_bullet) > 30:
                        words = clean_bullet.split()
                        # Add 4-word chunks
                        for i in range(len(words) - 3):
                            fragments.add(' '.join(words[i:i+4]))
                        # Add first/last portions
                        fragments.add(clean_bullet[:50])
                        fragments.add(clean_bullet[-50:] if len(clean_bullet) > 50 else clean_bullet)
        
        # Education
        for edu in parsed_data.get("education", []):
            for key in ["degree", "institution", "graduation_date", "major"]:
                if edu.get(key):
                    fragments.add(str(edu[key]).lower())
        
        return fragments
    
    def _is_content_mapped(self, text: str, fragments: Set[str]) -> bool:
        """Check if content is represented in parsed fragments"""
        # Clean text more aggressively
        clean_text = text.replace('•', '').replace('-', '').replace('*', '').replace('\n', ' ').strip()
        clean_text = ' '.join(clean_text.split())  # Normalize whitespace
        
        # Check substring matches (both directions)
        for fragment in fragments:
            if len(fragment) < 5:
                continue
            
            clean_fragment = fragment.replace('\n', ' ').strip()
            clean_fragment = ' '.join(clean_fragment.split())
            
            # Direct substring match
            if clean_fragment in clean_text or clean_text in clean_fragment:
                return True
            
            # Check if they share a significant portion (50%+)
            if len(clean_fragment) > 20 and len(clean_text) > 20:
                if clean_fragment[:len(clean_fragment)//2] in clean_text:
                    return True
                if clean_text[:len(clean_text)//2] in clean_fragment:
                    return True
        
        # Check word overlap for fragmented content
        if len(clean_text) > 15:
            common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'as', 'is', 'was', 'be'}
            text_words = set(w.lower() for w in clean_text.split() if len(w) > 3 and w.lower() not in common_words)
            
            for fragment in fragments:
                if len(fragment) > 15:
                    fragment_words = set(w.lower() for w in fragment.split() if len(w) > 3 and w.lower() not in common_words)
                    if text_words and fragment_words:
                        overlap = len(text_words & fragment_words)
                        overlap_ratio = overlap / len(text_words) if text_words else 0
                        # More lenient: 3+ words OR 30%+ overlap
                        if overlap >= 3 or overlap_ratio > 0.3:
                            return True
        
        return False
    
    def _is_section_header_or_metadata(self, text: str) -> bool:
        """Check if text is a section header or metadata"""
        common_headers = [
            "experience", "education", "skills", "summary", "objective",
            "projects", "certifications", "awards", "work history", "employment"
        ]
        
        if any(header in text for header in common_headers):
            return True
        
        # Check if it looks like a date or location
        months = ['january', 'february', 'march', 'april', 'may', 'june',
                  'july', 'august', 'september', 'october', 'november', 'december',
                  'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
        
        if len(text) < 50 and any(month in text for month in months):
            return True
        
        return False
    
    def _looks_like_experience_bullet(self, text: str) -> bool:
        """Check if text looks like an experience bullet point"""
        # Common action verbs used in experience bullets
        action_verbs = [
            'developed', 'created', 'implemented', 'designed', 'built', 'managed',
            'led', 'improved', 'optimized', 'increased', 'decreased', 'reduced',
            'collaborated', 'coordinated', 'established', 'executed', 'maintained',
            'analyzed', 'researched', 'deployed', 'integrated', 'automated',
            'architected', 'engineered', 'delivered', 'launched', 'migrated'
        ]
        
        # Check if starts with action verb or contains technical indicators
        words = text.lower().split()
        if len(words) < 5:
            return False
        
        # Check first few words for action verbs
        first_words = ' '.join(words[:3])
        if any(verb in first_words for verb in action_verbs):
            return True
        
        # Check for technical keywords that indicate experience content
        technical_keywords = [
            'api', 'database', 'framework', 'system', 'algorithm', 'platform',
            'application', 'service', 'pipeline', 'processing', 'data', 'code',
            'testing', 'deployment', 'performance', 'scalable', 'cloud'
        ]
        
        if any(keyword in text.lower() for keyword in technical_keywords):
            return True
        
        return False
    
    # ========== HELPERS ========== #
    
    def _create_issue(
        self,
        code: str,
        severity: IssueSeverity,
        section: IssueSection,
        message: str,
        details: str,
        block: Dict[str, Any]
    ) -> ATSIssue:
        """Helper to create an ATSIssue from a block"""
        return ATSIssue(
            code=code,
            severity=severity,
            section=section,
            message=message,
            details=details,
            page=block.get("page", 1),
            bbox=block["bbox"],
            location_hint=f"Page {block.get('page', 1)}, {block.get('region', 'body')} region"
        )
    
    def _clean_font_name(self, raw_font_name: str) -> str:
        """Clean and standardize font names"""
        if not raw_font_name:
            return ""
        
        font_name = raw_font_name.lower().strip()
        
        # Remove font subset prefix (e.g., "ABCDEE+" or "CRNSY6+")
        if '+' in font_name:
            font_name = font_name.split('+')[-1]
        
        # Ignore fonts that look like internal PDF identifiers (gibberish)
        # Real fonts have recognizable names, not random character sequences
        ignore_patterns = [
            'fontawesome',  # Icon fonts (not readable text)
            'noto',  # Noto fonts are actually ok, but let's be selective
        ]
        
        # If font name is too short or looks like an ID (e.g., 'cf10', 'crnsy6')
        if len(font_name) < 4 or (len(font_name) < 8 and any(c.isdigit() for c in font_name)):
            # Check if it's a known font abbreviation
            known_abbrevs = {
                'cmr': 'computer modern',
                'cmb': 'computer modern',
                'cmbx': 'computer modern',
                'cmsy': 'computer modern',
            }
            for abbrev, full_name in known_abbrevs.items():
                if font_name.startswith(abbrev):
                    return full_name
            # Otherwise, ignore it (likely an internal identifier)
            return ""
        
        # Ignore icon fonts
        for pattern in ignore_patterns:
            if pattern in font_name:
                return ""
        
        # Map common internal names to readable names
        font_mapping = {
            'arialmt': 'arial',
            'timesnewromanpsmt': 'times new roman',
            'timesnewroman': 'times new roman',
            'courier': 'courier new',
            'helvetica': 'helvetica'
        }
        
        for internal, readable in font_mapping.items():
            if font_name.startswith(internal):
                return readable
        
        # Remove common suffixes and separators
        suffixes = ['-bold', '-italic', '-regular', 'mt', 'ps', 'psmt']
        for suffix in suffixes:
            font_name = font_name.replace(suffix, '')
        
        cleaned = font_name.replace('-', '').replace('_', '').strip()
        
        # Final check: if cleaned name is very short or all lowercase gibberish, ignore it
        if len(cleaned) < 4:
            return ""
        
        return cleaned
    
    def _issue_to_highlight(self, issue: ATSIssue) -> Dict[str, Any]:
        """Convert ATSIssue to legacy highlight format"""
        return {
            "page": issue.page,
            "bbox": issue.bbox,
            "severity": issue.severity.value if hasattr(issue.severity, 'value') else issue.severity,
            "issue_type": issue.code,
            "message": issue.message,
            "tooltip": issue.details
        }
    
    def _issues_to_recommendations(self, issues: List[ATSIssue]) -> List[str]:
        """
        Generate quick, rule-based recommendations for immediate display.
        
        TWO-TIER RECOMMENDATION SYSTEM:
        - TIER 1 (this): Fast, generic recommendations shown in score summary
        - TIER 2 (AI): Contextual, detailed recommendations shown in diagnostic chat
        
        Use case: Users see these immediately upon upload without waiting for AI.
        """
        recs = set()
        
        rec_map = {
            # Diagnostics-based recommendations
            "has_images": "Remove images and replace any important content with plain text",
            "has_tables": "Replace tables with simple text formatting using line breaks",
            "has_headers_footers": "Move contact information from header/footer to main document body",
            "complex_layout": "Simplify layout: use single column, standard fonts, and consistent formatting",
            
            # Visual/layout-based recommendations
            "contact_email_in_header_footer": "Move email address from header/footer to main body of resume",
            "contact_phone_in_header_footer": "Move phone number from header/footer to main body of resume",
            "skills_section_unreadable": "Reformat Skills section as simple bullet points - ATS extracted 0 skills",
            "experience_not_extracted": "Experience section not readable by ATS - check formatting",
            "education_not_extracted": "Education section not readable by ATS - check formatting",
            "image_content": "Remove images and replace any important content with plain text",
            "floating_text_box": "Replace floating text boxes with standard left-aligned text",
            "scanned_pdf": "Convert scanned/image PDF to text-based PDF by exporting from your original document editor",
            "icon_usage": "Replace icons with text labels for all contact information and links",
            "decorative_font": "Replace decorative fonts with ATS-friendly fonts like Arial, Calibri, or Georgia",
            "uncommon_font": "Use ATS-friendly fonts: Arial, Calibri, Georgia, Garamond, Helvetica, or Times New Roman",
        }
        
        for issue in issues:
            if issue.code in rec_map:
                recs.add(rec_map[issue.code])
        
        return list(recs)
    
    def _calculate_summary(self, highlights: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate issue summary by severity"""
        return {
            "total_issues": len(highlights),
            "critical": sum(1 for h in highlights if h["severity"] == "critical"),
            "high": sum(1 for h in highlights if h["severity"] == "high"),
            "medium": sum(1 for h in highlights if h["severity"] == "medium"),
            "low": sum(1 for h in highlights if h["severity"] == "low")
        }
    
    def _empty_result(self, message: str) -> Dict[str, Any]:
        """Return empty result with message"""
        return {
            "highlights": [],
            "summary": {
                "total_issues": 0,
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0
            },
            "recommendations": [message]
        }
