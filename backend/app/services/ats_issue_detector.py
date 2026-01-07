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
        try:
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
            
            result = {
                "highlights": highlights,
                "summary": summary,
                "recommendations": recommendations,
                "issues": issue_messages  # String list for "Issues Detected" panel
            }
            return result
        except Exception as e:
            # If anything fails, return empty result with error message
            print(f"[ATS ISSUE DETECTOR ERROR] Issue detection failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return self._empty_result(f"Issue detection failed: {str(e)}")
    
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
            diag_issues = self._detect_from_diagnostics(ats_diagnostics, blocks)
            issues.extend(diag_issues)
        
        # B. Visual/layout-based detection (from PyMuPDF analysis)
        # 1. Scanned PDF
        scanned_issues = self._detect_scanned_pdf(file_path)
        issues.extend(scanned_issues)
        
        # 2. Contact issues
        contact_issues = self._detect_contact_issues(blocks, parsed_data)
        issues.extend(contact_issues)
        
        # 3. Skills issues
        skills_issues = self._detect_skills_issues(blocks, parsed_data)
        issues.extend(skills_issues)
        
        # 4. Experience issues
        exp_issues = self._detect_experience_issues(blocks, parsed_data)
        issues.extend(exp_issues)
        
        # 5. Education issues
        edu_issues = self._detect_education_issues(blocks, parsed_data)
        issues.extend(edu_issues)
        
        # 6. Images
        img_issues = self._detect_images(file_path)
        issues.extend(img_issues)
        
        # 7. Icons
        icon_issues = self._detect_icons(file_path, parsed_data)
        issues.extend(icon_issues)
        
        # 9. Date format issues
        issues.extend(self._detect_date_format_issues(blocks))
        
        # 10. Font issue
        
        # 11. Unmapped content
        issues.extend(self._detect_unmapped_content(blocks, parsed_data))
        
        return issues
    
    def _detect_from_diagnostics(self, ats_diagnostics: Dict[str, Any], blocks: List[Dict[str, Any]] = None) -> List[ATSIssue]:
        """Detect issues from ATS diagnostics (tables, images, headers, complexity)"""
        issues = []
        if blocks is None:
            blocks = []
        
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
        
        # Multi-column layout issue
        if ats_diagnostics.get("has_multi_column"):
            secondary_ratio = ats_diagnostics.get("secondary_column_ratio", 0.0)
            
            # Determine severity based on how much content is in secondary columns
            if secondary_ratio > 0.4:
                # High ratio = more severe
                severity = IssueSeverity.HIGH
                details = f"Multi-column layout detected with {secondary_ratio*100:.0f}% of content in secondary columns. This significantly increases the risk that ATS systems will misread or miss important information. Recommendation: Convert to single-column layout."
            elif secondary_ratio > 0.2:
                severity = IssueSeverity.MEDIUM
                details = f"Multi-column layout detected with {secondary_ratio*100:.0f}% of content in secondary columns. ATS systems may read content in the wrong order or miss sidebar content. Recommendation: Use single-column layout for maximum compatibility."
            else:
                # Low ratio (small sidebar) - lower severity
                severity = IssueSeverity.LOW
                details = f"Multi-column layout detected with {secondary_ratio*100:.0f}% of content in secondary columns. Minor sidebar detected. While less risky, single-column layouts are still recommended for optimal ATS compatibility."
            
            # Find blocks in secondary columns (column > 1) to highlight
            secondary_column_blocks = [b for b in blocks if b.get("column", 1) > 1]
            
            if secondary_column_blocks:
                # Create one issue per page with secondary columns (to show highlights on PDF)
                # Group blocks by page
                blocks_by_page = {}
                for block in secondary_column_blocks:
                    page = block.get("page", 1)
                    if page not in blocks_by_page:
                        blocks_by_page[page] = []
                    blocks_by_page[page].append(block)
                
                # Create one issue per page with secondary columns
                # Use the first block's bbox as a representative highlight
                for page_num, page_blocks in blocks_by_page.items():
                    # Use the first secondary column block as the highlight location
                    first_block = page_blocks[0]
                    bbox = first_block.get("bbox")
                    
                    # Count how many blocks are in secondary columns on this page
                    secondary_count = len(page_blocks)
                    
                    issues.append(ATSIssue(
                        code="multi_column_layout",
                        severity=severity,
                        section=IssueSection.GENERAL,
                        message=f"Multi-column layout detected (Page {page_num})",
                        details=details + f" Found {secondary_count} block(s) in secondary column(s) on this page.",
                        page=page_num,
                        bbox=bbox,  # Highlight secondary column content
                        location_hint=f"Secondary column content on page {page_num}"
                    ))
            else:
                # Fallback: document-wide issue if no blocks found
                issues.append(ATSIssue(
                    code="multi_column_layout",
                    severity=severity,
                    section=IssueSection.GENERAL,
                    message="Multi-column layout detected",
                    details=details,
                    page=1,
                    bbox=None  # Document-wide (no highlight)
                ))
        
        # Headers/footers issue (only flagged when truly detected)
        if ats_diagnostics.get("has_headers_footers"):
            issues.append(ATSIssue(
                code="has_headers_footers",
                severity=IssueSeverity.MEDIUM,
                section=IssueSection.CONTACT,
                message="Page headers or footers detected - ATS may skip this content",
                details="Content in page margins (headers/footers) is often ignored by ATS systems. If this contains important info like contact details or page numbers, consider moving it to the main body or removing it.",
                page=1,
                bbox=None  # Document-wide
            ))
        
        # Complexity-based issues (using new metrics system)
        complexity_metric = ats_diagnostics.get("complexity_metric")
        if complexity_metric:
            score = complexity_metric.get("score", 0)
            factors = complexity_metric.get("contributing_factors", [])
            factors_str = "; ".join(factors) if factors else "Multiple formatting issues detected"
            
            if score > 70:
                # Very complex - CRITICAL
                issues.append(ATSIssue(
                    code="very_complex_layout",
                    severity=IssueSeverity.CRITICAL,
                    section=IssueSection.GENERAL,
                    message="Resume has very complex layout",
                    details=f"Your resume will likely fail ATS parsing. Issues found: {factors_str}. Recommendation: Simplify to single-column layout with minimal formatting, use only 1-2 standard fonts, and remove tables/images.",
                    page=1,
                    bbox=None
                ))
            elif score > 40:
                # Complex - HIGH
                issues.append(ATSIssue(
                    code="complex_layout",
                    severity=IssueSeverity.HIGH,
                    section=IssueSection.GENERAL,
                    message="Resume has complex layout",
                    details=f"Your resume may have ATS parsing issues. Contributing factors: {factors_str}. Recommendation: Simplify formatting and reduce use of tables, images, and multiple fonts.",
                    page=1,
                    bbox=None
                ))
            elif score > 20:
                # Moderate - MEDIUM
                issues.append(ATSIssue(
                    code="moderate_complexity",
                    severity=IssueSeverity.MEDIUM,
                    section=IssueSection.GENERAL,
                    message="Resume has moderate layout complexity",
                    details=f"Your resume is generally ATS-friendly but could be improved. {factors_str}. Consider simplifying to maximize ATS compatibility.",
                    page=1,
                    bbox=None
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
        
        # ATS-friendly fonts (widely supported and readable)
        ats_friendly = {
            # Serif fonts
            'cambria', 'garamond', 'georgia', 'palatino', 'times', 'times new roman',
            'book antiqua', 'bookman', 'century', 'lucida', 'palatino linotype',
            # Sans-serif fonts
            'arial', 'calibri', 'helvetica', 'tahoma', 'verdana', 'trebuchet',
            'trebuchet ms', 'segoe', 'segoe ui', 'lucida sans', 'open sans',
            'roboto', 'lato', 'source sans', 'noto', 'noto sans',
            # Common system fonts
            'helvetica neue', 'arial black', 'century gothic', 'franklin gothic',
            # Monospace (for technical resumes)
            'courier', 'courier new', 'consolas', 'monaco',
            # TeX/Academic fonts (acceptable for technical resumes)
            'computer modern', 'latin modern',
        }
        
        # Decorative fonts to avoid (hard to read, unprofessional)
        decorative = {
            'comic sans', 'comicsans', 'comic sans ms',
            'papyrus', 'brush script', 'curlz', 'impact',
            'chiller', 'jokerman', 'kristen', 'juice',
            'showcard gothic', 'snap itc', 'stencil'
        }
        
        doc = fitz.open(file_path)
        all_fonts = set()
        
        for page in doc:
            text_dict = page.get_text("dict")
            for block in text_dict.get("blocks", []):
                if block.get("type") == 0:
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            font_name = span.get("font", "").strip()
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
        unmapped_count = 0
        skipped_short = 0
        skipped_mapped = 0
        skipped_header = 0
        skipped_region = 0
        skipped_bullet = 0
        skipped_length = 0
        
        for idx, block in enumerate(blocks):
            text_lower = block.get("text", "").lower().strip()
            text_original = block.get("text", "").strip()
            block_region = block.get("region", "body")
            
            # Skip short blocks
            if len(text_lower) < 10:
                skipped_short += 1
                continue
            
            # Check length threshold (80 chars)
            if len(text_lower) <= 80:
                skipped_length += 1
                continue
            
            # Check if content is in a clearly labeled section (experience, education, etc.)
            # If it's in a recognized section, it's less likely to be truly unmapped
            is_in_labeled_section = self._is_in_labeled_section(blocks, idx)
            
            # Check if content is mapped
            is_mapped = self._is_content_mapped(text_lower, parsed_fragments, is_in_labeled_section)
            if is_mapped:
                skipped_mapped += 1
                continue
            
            # If content is in a labeled section but not mapped, it's less critical
            # (ATS might have extracted it but in a different format)
            if is_in_labeled_section:
                skipped_mapped += 1
                continue
            
            # Check if it's a common section header or metadata
            is_header = self._is_section_header_or_metadata(text_lower)
            if is_header:
                skipped_header += 1
                continue
            
            # Only flag body content (not headers/footers/sidebars)
            if block_region != "body":
                skipped_region += 1
                continue
            
            # Additional check: skip if it looks like a job description bullet
            looks_like_bullet = self._looks_like_experience_bullet(text_lower)
            if looks_like_bullet:
                skipped_bullet += 1
                continue
            
            # Create a preview of the content (first 60 chars)
            preview = text_original[:60]
            if len(text_original) > 60:
                preview += "..."
            
            unmapped_count += 1
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
        for key in ["email", "phone", "name"]:
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
    
    def _is_content_mapped(self, text: str, fragments: Set[str], is_in_labeled_section: bool = False) -> bool:
        """
        Check if content is represented in parsed fragments.
        
        Uses balanced matching:
        - For content in labeled sections: 60%+ overlap (more lenient)
        - For other content: 70%+ overlap (stricter)
        - Prefers exact or near-exact matches
        - Only matches if content is clearly represented in parsed data
        """
        # Clean text more aggressively
        clean_text = text.replace('•', '').replace('-', '').replace('*', '').replace('\n', ' ').strip()
        clean_text = ' '.join(clean_text.split())  # Normalize whitespace
        
        if len(clean_text) < 10:
            return False  # Too short to meaningfully match
        
        # Common stop words to ignore
        common_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'as', 'is', 'was', 'be', 'been', 'have', 'has',
            'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may',
            'might', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he',
            'she', 'it', 'we', 'they', 'am', 'are', 'were'
        }
        
        # Extract significant words from the text (4+ chars, not stop words)
        text_words = set(w.lower().strip('.,;:!?()[]{}') for w in clean_text.split() 
                        if len(w.strip('.,;:!?()[]{}')) >= 4 and w.lower().strip('.,;:!?()[]{}') not in common_words)
        
        if not text_words:
            # If no significant words, check for exact substring matches only
            for fragment in fragments:
                if len(fragment) >= 20:  # Only check substantial fragments
                    clean_fragment = fragment.replace('\n', ' ').strip()
                    clean_fragment = ' '.join(clean_fragment.split())
                    # Exact or near-exact match required
                    if len(clean_fragment) >= len(clean_text) * 0.8:
                        if clean_fragment in clean_text or clean_text in clean_fragment:
                            return True
            return False
        
        # Check each fragment for substantial overlap
        best_match_ratio = 0.0
        for fragment in fragments:
            if len(fragment) < 10:
                continue
            
            clean_fragment = fragment.replace('\n', ' ').strip()
            clean_fragment = ' '.join(clean_fragment.split())
            
            # Extract significant words from fragment
            fragment_words = set(w.lower().strip('.,;:!?()[]{}') for w in clean_fragment.split() 
                               if len(w.strip('.,;:!?()[]{}')) >= 4 and w.lower().strip('.,;:!?()[]{}') not in common_words)
            
            if not fragment_words:
                # If fragment has no significant words, check for exact substring match
                if len(clean_fragment) >= 20 and (clean_fragment in clean_text or clean_text in clean_fragment):
                    return True
                continue
            
            # Calculate word overlap
            overlap = text_words & fragment_words
            if not overlap:
                continue
            
            # Calculate overlap ratio (how much of the text is covered by the fragment)
            overlap_ratio = len(overlap) / len(text_words) if text_words else 0
            
            # Also check reverse ratio (how much of fragment is in text)
            fragment_coverage = len(overlap) / len(fragment_words) if fragment_words else 0
            
            # Require substantial overlap: 
            # - For content in labeled sections: 60%+ (more lenient since ATS may have extracted it differently)
            # - For other content: 70%+ (stricter)
            threshold = 0.6 if is_in_labeled_section else 0.7
            
            if overlap_ratio >= threshold:
                return True
            if overlap_ratio >= (threshold - 0.1) and fragment_coverage >= 0.5 and len(overlap) >= 5:
                return True
            
            # Track best match for debugging
            if overlap_ratio > best_match_ratio:
                best_match_ratio = overlap_ratio
            
            # For very long fragments (like full descriptions), check if text is a substantial substring
            if len(clean_fragment) >= 50 and len(clean_text) >= 30:
                # Check if text appears as a substantial portion of fragment
                if clean_text in clean_fragment:
                    # Verify it's not just a small part
                    if len(clean_text) >= len(clean_fragment) * 0.4:
                        return True
        
        # If we have a good match with at least 4 words, consider it mapped
        # Threshold depends on whether content is in a labeled section
        min_ratio = 0.55 if is_in_labeled_section else 0.6
        if best_match_ratio >= min_ratio and len(text_words) >= 4:
            # Additional check: ensure we matched at least 4 significant words
            for fragment in fragments:
                clean_fragment = fragment.replace('\n', ' ').strip()
                fragment_words = set(w.lower().strip('.,;:!?()[]{}') for w in clean_fragment.split() 
                                   if len(w.strip('.,;:!?()[]{}')) >= 4 and w.lower().strip('.,;:!?()[]{}') not in common_words)
                overlap = text_words & fragment_words
                if len(overlap) >= 4:
                    return True
        
        return False
    
    def _is_in_labeled_section(self, blocks: List[Dict[str, Any]], block_idx: int) -> bool:
        """
        Check if a block is within a clearly labeled section (Experience, Education, etc.)
        by looking backwards for section headers.
        """
        # Look backwards up to 3 blocks for a section header
        section_headers = [
            'experience', 'work experience', 'employment', 'work history', 'professional experience',
            'education', 'academic', 'qualifications',
            'skills', 'technical skills', 'core competencies', 'technologies',
            'projects', 'certifications', 'awards', 'achievements',
            'summary', 'objective', 'profile'
        ]
        
        # Check current block and previous 3 blocks
        for i in range(max(0, block_idx - 3), block_idx + 1):
            if i < len(blocks):
                block_text = blocks[i].get("text", "").lower().strip()
                # Check if it's a short line that looks like a section header
                if len(block_text) < 50:  # Section headers are usually short
                    for header in section_headers:
                        if header in block_text:
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
        """
        Clean and standardize font names from PDFs.
        
        PDFs contain many weird font names that aren't user-recognizable:
        - Subset prefixes: "ABCDEF+Arial" → "Arial"
        - TeX/LaTeX fonts: "cmbx10", "cmr12" → "Computer Modern"
        - Internal IDs: "F1", "G12", "T3" → ignored
        - Platform names: "ArialMT", "TimesNewRomanPSMT" → "Arial", "Times New Roman"
        
        Returns:
            Cleaned font name, or empty string if unrecognizable (to skip it)
        """
        if not raw_font_name:
            return ""
        
        font_name = raw_font_name.strip()
        original_name = font_name  # Keep for debugging
        font_name = font_name.lower()
        
        # Step 1: Remove font subset prefix (e.g., "ABCDEF+" or "XYZABC+")
        # These are 6 uppercase letters followed by a plus sign
        if '+' in font_name:
            font_name = font_name.split('+')[-1]
        
        # Step 2: Ignore icon/symbol fonts entirely
        icon_fonts = ['fontawesome', 'fa-', 'glyphicons', 'icomoon', 'material', 
                      'wingdings', 'webdings', 'symbol', 'zapfdingbats', 'dingbats']
        for icon in icon_fonts:
            if icon in font_name:
                return ""
        
        # Step 3: Map TeX/LaTeX font abbreviations to readable names
        # These are commonly used in academic/technical resumes
        tex_fonts = {
            'cmr': 'computer modern',      # Computer Modern Roman
            'cmb': 'computer modern',      # Computer Modern Bold
            'cmbx': 'computer modern',     # Computer Modern Bold Extended
            'cmti': 'computer modern',     # Computer Modern Text Italic
            'cmsl': 'computer modern',     # Computer Modern Slanted
            'cmss': 'computer modern',     # Computer Modern Sans Serif
            'cmtt': 'computer modern',     # Computer Modern Typewriter
            'cmssbx': 'computer modern',   # Computer Modern Sans Serif Bold
            'cmsy': 'computer modern',     # Computer Modern Symbol
            'cmmi': 'computer modern',     # Computer Modern Math Italic
            'cmex': 'computer modern',     # Computer Modern Extended
            'cmcsc': 'computer modern',    # Computer Modern Small Caps
            'cmu': 'computer modern',      # Computer Modern Unicode
            'cmfi': 'computer modern',     # Computer Modern Fibonacci
            'cmff': 'computer modern',     # Computer Modern Funny Font
            'cminch': 'computer modern',   # Computer Modern Inch
            'lmr': 'latin modern',         # Latin Modern Roman
            'lmss': 'latin modern',        # Latin Modern Sans
            'lmtt': 'latin modern',        # Latin Modern Typewriter
            'ec': 'european computer modern',
            'ptm': 'times',                # PostScript Times
            'phv': 'helvetica',            # PostScript Helvetica
            'pcr': 'courier',              # PostScript Courier
            'ppl': 'palatino',             # PostScript Palatino
            'pbk': 'bookman',              # PostScript Bookman
            'pag': 'avant garde',          # PostScript Avant Garde
            'pnc': 'new century schoolbook',
            'pzc': 'zapf chancery',
        }
        for abbrev, full_name in tex_fonts.items():
            if font_name.startswith(abbrev) and len(font_name) <= len(abbrev) + 3:
                # Matches patterns like "cmr10", "cmbx12", "lmr17"
                return full_name
        
        # Step 4: Ignore internal PDF identifiers
        # These are typically short alphanumeric strings like "F1", "G12", "T3", "C2_0"
        import re
        internal_patterns = [
            r'^[a-z]\d+$',           # F1, G12, T3
            r'^[a-z]\d+_\d+$',       # C2_0, F1_2
            r'^[a-z]{1,2}\d{1,3}$',  # TT1, MT12
            r'^f\d+$',               # f0, f1, f2 (common internal names)
        ]
        for pattern in internal_patterns:
            if re.match(pattern, font_name):
                return ""
        
        # Step 5: Map common PDF internal names to readable names
        font_mapping = {
            # Adobe/PDF standard names
            'arialmt': 'arial',
            'arial-boldmt': 'arial',
            'arial-italicmt': 'arial',
            'arial-bolditalicmt': 'arial',
            'arialmtblack': 'arial black',
            'timesnewromanpsmt': 'times new roman',
            'timesnewromanps-boldmt': 'times new roman',
            'timesnewromanps-italicmt': 'times new roman',
            'timesnewroman': 'times new roman',
            'times-roman': 'times new roman',
            'times-bold': 'times new roman',
            'times-italic': 'times new roman',
            'courier-bold': 'courier',
            'courier-oblique': 'courier',
            'couriernewpsmt': 'courier new',
            'helvetica-bold': 'helvetica',
            'helvetica-oblique': 'helvetica',
            'helveticaneue': 'helvetica neue',
            'helvetica-neue': 'helvetica neue',
            'calibri-bold': 'calibri',
            'calibri-italic': 'calibri',
            'calibri-light': 'calibri',
            'cambria-bold': 'cambria',
            'cambria-italic': 'cambria',
            'georgia-bold': 'georgia',
            'georgia-italic': 'georgia',
            'verdana-bold': 'verdana',
            'verdana-italic': 'verdana',
            'tahoma-bold': 'tahoma',
            'trebuchetms': 'trebuchet ms',
            'trebuchetms-bold': 'trebuchet ms',
            'palatino-roman': 'palatino',
            'palatino-bold': 'palatino',
            'palatinolinotype': 'palatino linotype',
            'bookoldstyle': 'bookman old style',
            'garamond-bold': 'garamond',
            'garamond-italic': 'garamond',
        }
        
        for internal, readable in font_mapping.items():
            if font_name == internal or font_name.startswith(internal):
                return readable
        
        # Step 6: Clean up remaining font names
        # Remove common style suffixes
        style_suffixes = [
            '-bold', '-italic', '-regular', '-light', '-medium', '-semibold',
            '-black', '-oblique', '-condensed', '-extended', '-narrow',
            'bold', 'italic', 'regular', 'light', 'medium',
            'mt', 'ps', 'psmt', 'std', 'pro', 'lt', 'bd', 'it'
        ]
        
        cleaned = font_name
        for suffix in style_suffixes:
            if cleaned.endswith(suffix):
                cleaned = cleaned[:-len(suffix)]
        
        # Remove separators and clean up
        cleaned = cleaned.replace('-', ' ').replace('_', ' ').strip()
        
        # Step 7: Final validation
        # If it's still too short or looks like gibberish, ignore it
        if len(cleaned) < 3:
            return ""
        
        # Check if it contains at least some recognizable letters
        if not re.search(r'[a-z]{3,}', cleaned):
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
            "multi_column_layout": "Convert multi-column layout to single-column format for better ATS compatibility",
            "complex_layout": "Simplify layout: use single column, standard fonts, and consistent formatting",
            
            # Visual/layout-based recommendations
            "contact_email_in_header_footer": "Move email address from header/footer to main body of resume",
            "contact_phone_in_header_footer": "Move phone number from header/footer to main body of resume",
            "skills_section_unreadable": "Reformat Skills section as simple bullet points - ATS extracted 0 skills",
            "experience_not_extracted": "Experience section not readable by ATS - check formatting",
            "education_not_extracted": "Education section not readable by ATS - check formatting",
            "image_content": "Remove images and replace any important content with plain text",
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
