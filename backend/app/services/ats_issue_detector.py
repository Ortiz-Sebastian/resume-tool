"""
ATS Issue Detector - Maps parsed data to PDF blocks and identifies formatting issues.

This service combines:
- Parsed structured data (from spaCy/Textkernel)
- PDF layout data (from PyMuPDF)

To detect and visually highlight ATS-unfriendly formatting patterns.
"""

import fitz  # PyMuPDF
from typing import Dict, Any, List, Tuple, Optional
import re


class ATSIssueDetector:
    """Detect ATS formatting issues by mapping parsed fields to PDF blocks"""
    
    def __init__(self):
        self.severity_levels = {
            "critical": {"color": "#EF4444", "priority": 1},  # Red
            "high": {"color": "#F97316", "priority": 2},      # Orange
            "medium": {"color": "#EAB308", "priority": 3},    # Yellow
            "low": {"color": "#3B82F6", "priority": 4}        # Blue
        }
    
    def detect_issues(
        self, 
        file_path: str,
        file_type: str,
        parsed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Detect ATS formatting issues and generate highlight data.
        
        Returns:
            {
                "highlights": [
                    {
                        "page": int,
                        "bbox": [x0, y0, x1, y1],
                        "severity": str,
                        "issue_type": str,
                        "message": str,
                        "tooltip": str
                    }
                ],
                "summary": {
                    "total_issues": int,
                    "critical": int,
                    "high": int,
                    "medium": int,
                    "low": int
                },
                "recommendations": List[str]
            }
        """
        if file_type != ".pdf":
            return self._empty_result("Only PDF analysis is supported")
        
        # Extract blocks with metadata
        blocks = self._extract_blocks_with_metadata(file_path)
        
        # Detect specific issues
        highlights = []
        recommendations = []
        
        # 0. Scanned PDF / Image-only resume
        scanned_issues = self._detect_scanned_pdf(file_path)
        highlights.extend(scanned_issues["highlights"])
        recommendations.extend(scanned_issues["recommendations"])
        
        # 1. Contact info in header/footer
        contact_issues = self._detect_contact_in_header_footer(blocks, parsed_data)
        highlights.extend(contact_issues["highlights"])
        recommendations.extend(contact_issues["recommendations"])
        
        # 2. Skills in tables/columns/sidebar
        skills_issues = self._detect_skills_issues(blocks, parsed_data)
        highlights.extend(skills_issues["highlights"])
        recommendations.extend(skills_issues["recommendations"])
        
        # 3. Experience in multi-column layout
        experience_issues = self._detect_experience_issues(blocks, parsed_data)
        highlights.extend(experience_issues["highlights"])
        recommendations.extend(experience_issues["recommendations"])
        
        # 4. Content in images
        image_issues = self._detect_content_in_images(file_path, blocks)
        highlights.extend(image_issues["highlights"])
        recommendations.extend(image_issues["recommendations"])
        
        # 5. Floating text boxes
        textbox_issues = self._detect_floating_text_boxes(blocks)
        highlights.extend(textbox_issues["highlights"])
        recommendations.extend(textbox_issues["recommendations"])
        
        # 6. Icons used for contact/skills
        icon_issues = self._detect_icon_usage(file_path, parsed_data)
        highlights.extend(icon_issues["highlights"])
        recommendations.extend(icon_issues["recommendations"])
        
        # 7. Unmapped/ignored content
        unmapped_issues = self._detect_unmapped_content(blocks, parsed_data)
        highlights.extend(unmapped_issues["highlights"])
        recommendations.extend(unmapped_issues["recommendations"])
        
        # 8. Date format issues
        date_issues = self._detect_date_format_issues(blocks, parsed_data)
        highlights.extend(date_issues["highlights"])
        recommendations.extend(date_issues["recommendations"])
        
        # 9. Uncommon fonts
        font_issues = self._detect_uncommon_fonts(file_path, blocks)
        highlights.extend(font_issues["highlights"])
        recommendations.extend(font_issues["recommendations"])
        
        # 10. ATS DIFFERENTIAL ANALYSIS - Compare visual content vs parsed data
        # This is the KEY feature: prove what the ATS missed!
        differential_issues = self._detect_ats_extraction_gaps(
            file_path, blocks, parsed_data
        )
        highlights.extend(differential_issues["highlights"])
        recommendations.extend(differential_issues["recommendations"])
        
        # Calculate summary
        summary = self._calculate_summary(highlights)
        
        return {
            "highlights": highlights,
            "summary": summary,
            "recommendations": list(set(recommendations))  # Remove duplicates
        }
    
    def _extract_blocks_with_metadata(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract text blocks with rich metadata using advanced detection"""
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
                    
                    # Extract text
                    text = ""
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text += span.get("text", "") + " "
                    
                    text = text.strip()
                    
                    if text:  # Only process blocks with text
                        page_blocks.append({
                            "text": text,
                            "bbox": bbox,
                            "block_data": block
                        })
            
            # Advanced detection methods
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
    
    def _detect_columns(self, blocks: List[Dict[str, Any]], page_width: float) -> Dict[int, int]:
        """
        Detect multi-column layout by clustering x positions.
        Returns dict mapping block_index -> column_number
        """
        if not blocks:
            return {}
        
        # Extract left edges (x0)
        x_positions = [(i, block["bbox"][0]) for i, block in enumerate(blocks)]
        
        # Simple clustering: find natural gap in x positions
        x_sorted = sorted(x_positions, key=lambda x: x[1])
        
        # Look for a significant gap (> 20% of page width)
        gap_threshold = page_width * 0.2
        column_assignments = {}
        current_column = 1
        
        for i in range(len(x_sorted)):
            idx, x_pos = x_sorted[i]
            column_assignments[idx] = current_column
            
            # Check if there's a big gap to next block
            if i < len(x_sorted) - 1:
                next_x = x_sorted[i + 1][1]
                if next_x - x_pos > gap_threshold:
                    current_column += 1
        
        return column_assignments
    
    def _detect_tables(self, blocks: List[Dict[str, Any]]) -> set:
        """
        Detect table-like structures by finding blocks arranged in rows/grids.
        Returns set of block indices that are in tables.
        """
        if len(blocks) < 4:  # Need at least 4 blocks for a minimal table
            return set()
        
        table_blocks = set()
        y_threshold = 5  # Blocks within 5 points are same row
        
        # Group blocks by row (similar y0 values)
        rows = {}
        for i, block in enumerate(blocks):
            y0 = block["bbox"][1]
            
            # Find existing row or create new one
            found_row = False
            for row_y in rows:
                if abs(y0 - row_y) < y_threshold:
                    rows[row_y].append((i, block))
                    found_row = True
                    break
            
            if not found_row:
                rows[y0] = [(i, block)]
        
        # Check each row for table-like patterns
        for row_y, row_blocks in rows.items():
            if len(row_blocks) >= 3:  # 3+ blocks in a row suggests table
                # Check if blocks are evenly spaced
                x_positions = sorted([b[1]["bbox"][0] for b in row_blocks])
                
                if len(x_positions) >= 3:
                    # Check spacing consistency
                    gaps = [x_positions[i+1] - x_positions[i] for i in range(len(x_positions)-1)]
                    avg_gap = sum(gaps) / len(gaps)
                    
                    # If gaps are relatively consistent, it's likely a table row
                    if all(abs(gap - avg_gap) < avg_gap * 0.5 for gap in gaps):
                        for idx, _ in row_blocks:
                            table_blocks.add(idx)
        
        return table_blocks
    
    def _detect_text_boxes(self, blocks: List[Dict[str, Any]], page_width: float) -> set:
        """
        Detect floating text boxes or isolated narrow containers.
        Returns set of block indices that appear to be in text boxes.
        """
        text_box_blocks = set()
        
        for i, block in enumerate(blocks):
            bbox = block["bbox"]
            x0, y0, x1, y1 = bbox
            width = x1 - x0
            
            # Narrow blocks far from margins are suspicious
            left_margin = x0
            right_margin = page_width - x1
            
            # Text box heuristics:
            # 1. Very narrow (< 30% of page width)
            # 2. Not near left margin AND not near right margin
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
    
    def _extract_fonts(self, block: Dict[str, Any]) -> List[str]:
        """Extract font names from block"""
        fonts = set()
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                fonts.add(span.get("font", ""))
        return list(fonts)
    
    def _detect_contact_in_header_footer(
        self, 
        blocks: List[Dict[str, Any]], 
        parsed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Detect if contact information is only in header/footer"""
        email = parsed_data.get("email", "")
        phone = parsed_data.get("phone", "")
        
        highlights = []
        recommendations = []
        
        # Find blocks containing contact info
        email_blocks = [b for b in blocks if email and email.lower() in b["text"].lower()]
        phone_blocks = [b for b in blocks if phone and phone in b["text"]]
        
        # Check if email is only in header/footer
        if email_blocks:
            all_in_header_footer = all(b["region"] in ["header", "footer"] for b in email_blocks)
            if all_in_header_footer:
                for block in email_blocks:
                    highlights.append({
                        "page": block["page"],
                        "bbox": block["bbox"],
                        "severity": "high",
                        "issue_type": "contact_in_header",
                        "message": "Contact info in header/footer",
                        "tooltip": "Your email is only in the header/footer. Many ATS systems ignore headers and footers, causing them to miss your contact information. Move this to the main body."
                    })
                recommendations.append("Move email address from header/footer to main body of resume")
        
        # Check if phone is only in header/footer
        if phone_blocks:
            all_in_header_footer = all(b["region"] in ["header", "footer"] for b in phone_blocks)
            if all_in_header_footer:
                for block in phone_blocks:
                    highlights.append({
                        "page": block["page"],
                        "bbox": block["bbox"],
                        "severity": "high",
                        "issue_type": "contact_in_header",
                        "message": "Phone in header/footer",
                        "tooltip": "Your phone number is only in the header/footer. Many ATS systems ignore this area. Move your phone number to the main body for better visibility."
                    })
                recommendations.append("Move phone number from header/footer to main body of resume")
        
        return {
            "highlights": highlights,
            "recommendations": recommendations
        }
    
    def _detect_skills_issues(
        self,
        blocks: List[Dict[str, Any]],
        parsed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Detect if skills are in tables, sidebars, or text boxes"""
        skills = parsed_data.get("skills", [])
        
        highlights = []
        recommendations = []
        
        if not skills:
            return {"highlights": highlights, "recommendations": recommendations}
        
        # Find blocks containing skills
        skill_blocks = []
        for block in blocks:
            if block["in_table"]:
                # Check if any skill is in this block
                text_lower = block["text"].lower()
                for skill in skills:
                    if skill.lower() in text_lower:
                        skill_blocks.append(block)
                        break
        
        # If significant skills are in tables, flag it
        if len(skill_blocks) > 0:
            for block in skill_blocks:
                highlights.append({
                    "page": block["page"],
                    "bbox": block["bbox"],
                    "severity": "medium",
                    "issue_type": "skills_in_table",
                    "message": "Skills in table/grid",
                    "tooltip": "Your skills are formatted in a table or grid. Many ATS systems struggle to parse tables correctly, which may cause skills to be missed or read in the wrong order. Use a simple bullet list instead."
                })
            
            recommendations.append("Replace skills table/grid with a simple bullet list for better ATS compatibility")
        
        return {
            "highlights": highlights,
            "recommendations": recommendations
        }
    
    def _detect_experience_issues(
        self,
        blocks: List[Dict[str, Any]],
        parsed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Detect if experience is in multi-column layout or spans columns"""
        experience = parsed_data.get("experience", [])
        
        highlights = []
        recommendations = []
        
        if not experience:
            return {"highlights": highlights, "recommendations": recommendations}
        
        # Find blocks in column 2 (right column) that might be experience
        right_column_blocks = [b for b in blocks if b["column"] == 2]
        
        # Check if any experience-related terms are in right column
        experience_keywords = ["experience", "work history", "employment", "position", "role"]
        
        for block in right_column_blocks:
            text_lower = block["text"].lower()
            if any(keyword in text_lower for keyword in experience_keywords):
                highlights.append({
                    "page": block["page"],
                    "bbox": block["bbox"],
                    "severity": "high",
                    "issue_type": "experience_in_columns",
                    "message": "Experience in multi-column layout",
                    "tooltip": "Your work experience appears to be in a multi-column layout. ATS systems may read columns out of order or skip one entirely, causing your experience to be missed or jumbled. Use a single-column layout."
                })
                recommendations.append("Use single-column layout for work experience section")
                break  # Only flag once
        
        return {
            "highlights": highlights,
            "recommendations": recommendations
        }
    
    def _detect_content_in_images(
        self,
        file_path: str,
        blocks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Detect images that may contain important content"""
        doc = fitz.open(file_path)
        
        highlights = []
        recommendations = []
        
        for page_num, page in enumerate(doc):
            images = page.get_images()
            
            if images:
                for img_index, img in enumerate(images):
                    # Get image bounding box
                    img_rect = page.get_image_bbox(img[7])  # img[7] is xref
                    
                    if img_rect:
                        highlights.append({
                            "page": page_num + 1,
                            "bbox": [img_rect.x0, img_rect.y0, img_rect.x1, img_rect.y1],
                            "severity": "critical",
                            "issue_type": "image_content",
                            "message": "Image detected",
                            "tooltip": "Images, logos, charts, and graphics are completely invisible to ATS systems. If this image contains important information (skills, achievements, contact info), it will be missed. Replace with plain text."
                        })
                
                if len(images) > 0:
                    recommendations.append(f"Remove images and replace any important content with plain text")
        
        doc.close()
        
        return {
            "highlights": highlights,
            "recommendations": recommendations
        }
    
    def _detect_unmapped_content(
        self,
        blocks: List[Dict[str, Any]],
        parsed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Detect content that wasn't parsed (may be ignored by ATS)"""
        highlights = []
        recommendations = []
        
        # Collect all text from parsed data
        parsed_text_fragments = set()
        
        # From contact
        if parsed_data.get("email"):
            parsed_text_fragments.add(parsed_data["email"].lower())
        if parsed_data.get("phone"):
            parsed_text_fragments.add(parsed_data["phone"].lower())
        if parsed_data.get("name"):
            parsed_text_fragments.add(parsed_data["name"].lower())
        
        # From skills
        for skill in parsed_data.get("skills", []):
            parsed_text_fragments.add(skill.lower())
        
        # From experience (titles, companies, dates, location, bullets, description)
        for exp in parsed_data.get("experience", []):
            if exp.get("title"):
                parsed_text_fragments.add(exp["title"].lower())
            if exp.get("company"):
                parsed_text_fragments.add(exp["company"].lower())
            if exp.get("dates"):
                parsed_text_fragments.add(exp["dates"].lower())
            if exp.get("location"):
                parsed_text_fragments.add(exp["location"].lower())
            if exp.get("description"):
                # Add description (may be long, but check if it's in blocks)
                parsed_text_fragments.add(exp["description"].lower())
            # Add all bullet points - use multiple fragments from each bullet
            for bullet in exp.get("bullets", []):
                if bullet and len(bullet.strip()) > 5:
                    bullet_lower = bullet.lower().strip()
                    # Add the full bullet
                    parsed_text_fragments.add(bullet_lower)
                    # Also add chunks of the bullet (first 40 chars, first 60, etc.)
                    if len(bullet_lower) > 40:
                        parsed_text_fragments.add(bullet_lower[:40])
                    if len(bullet_lower) > 60:
                        parsed_text_fragments.add(bullet_lower[:60])
                    # Add first few words (common pattern)
                    words = bullet_lower.split()
                    if len(words) >= 3:
                        parsed_text_fragments.add(' '.join(words[:3]))
                    if len(words) >= 5:
                        parsed_text_fragments.add(' '.join(words[:5]))
        
        # From education (degree, institution, dates, GPA, major)
        for edu in parsed_data.get("education", []):
            if edu.get("degree"):
                parsed_text_fragments.add(edu["degree"].lower())
            if edu.get("institution"):
                parsed_text_fragments.add(edu["institution"].lower())
            if edu.get("graduation_date"):
                parsed_text_fragments.add(edu["graduation_date"].lower())
            if edu.get("gpa"):
                parsed_text_fragments.add(str(edu["gpa"]).lower())
            if edu.get("major"):
                parsed_text_fragments.add(edu["major"].lower())
        
        # From certifications
        for cert in parsed_data.get("certifications", []):
            if isinstance(cert, str):
                parsed_text_fragments.add(cert.lower())
            elif isinstance(cert, dict):
                if cert.get("name"):
                    parsed_text_fragments.add(cert["name"].lower())
                if cert.get("issuer"):
                    parsed_text_fragments.add(cert["issuer"].lower())
        
        # From summary
        if parsed_data.get("summary"):
            # Add first 100 chars of summary
            parsed_text_fragments.add(parsed_data["summary"].lower()[:100])
        
        # Check blocks for unmapped content
        # (This is a simplified heuristic - we check if block contains ANY parsed content)
        for block in blocks:
            text_lower = block["text"].lower().strip()
            
            # Skip very short blocks (likely formatting)
            if len(text_lower) < 10:
                continue
            
            # Check if this block contains any parsed content
            # Use very flexible matching for bullet points
            contains_parsed_content = False
            
            # Remove bullet characters for cleaner matching
            clean_text = text_lower.replace('•', '').replace('-', '').replace('*', '').strip()
            
            # First, check for exact fragment matches (both directions)
            for fragment in parsed_text_fragments:
                if len(fragment) < 5:
                    continue
                # Check if fragment is in block OR block is in fragment
                if fragment in text_lower or text_lower in fragment or fragment in clean_text or clean_text in fragment:
                    contains_parsed_content = True
                    break
            
            # If no match yet, check word overlap (for fragmented blocks)
            if not contains_parsed_content and len(clean_text) > 15:
                # Get significant words from block (ignore common words)
                common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
                block_words = set(w for w in clean_text.split() if len(w) > 3 and w not in common_words)
                
                # Check if block shares significant words with any parsed fragment
                for fragment in parsed_text_fragments:
                    if len(fragment) > 20:  # Only check substantial fragments
                        fragment_words = set(w for w in fragment.split() if len(w) > 3 and w not in common_words)
                        # If more than 40% word overlap, consider it mapped
                        if block_words and fragment_words:
                            overlap = len(block_words & fragment_words)
                            if overlap >= 2 or overlap / len(block_words) > 0.4:
                                contains_parsed_content = True
                                break
            
            # If block has significant text but no parsed content, it might be ignored
            if not contains_parsed_content and len(text_lower) > 30:
                # Additional check: is this a common section header?
                common_headers = ["experience", "education", "skills", "summary", "objective", 
                                "projects", "certifications", "awards", "work history", "employment",
                                "technical skills", "professional experience", "qualifications"]
                is_header = any(header in text_lower for header in common_headers)
                
                # Also check if it's just a date or location (common non-parsed elements)
                looks_like_metadata = (
                    len(text_lower) < 50 and 
                    any(month in text_lower for month in ['january', 'february', 'march', 'april', 'may', 'june', 
                                                           'july', 'august', 'september', 'october', 'november', 'december',
                                                           'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])
                )
                
                if not is_header and not looks_like_metadata and block["region"] == "body":
                    highlights.append({
                        "page": block["page"],
                        "bbox": block["bbox"],
                        "severity": "low",
                        "issue_type": "unmapped_content",
                        "message": "Potentially ignored content",
                        "tooltip": "This content doesn't clearly map to standard resume sections (experience, education, skills). ATS systems may skip or misclassify it. Ensure important information is in clearly labeled sections."
                    })
        
        if any(h["issue_type"] == "unmapped_content" for h in highlights):
            recommendations.append("Ensure all important information is in clearly labeled sections (Experience, Education, Skills)")
        
        return {
            "highlights": highlights,
            "recommendations": recommendations
        }
    
    def _detect_floating_text_boxes(self, blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect floating text boxes using block metadata"""
        highlights = []
        recommendations = []
        
        # Find blocks marked as text boxes
        textbox_blocks = [b for b in blocks if b.get("in_text_box", False)]
        
        if textbox_blocks:
            for block in textbox_blocks:
                highlights.append({
                    "page": block["page"],
                    "bbox": block["bbox"],
                    "severity": "medium",
                    "issue_type": "floating_text_box",
                    "message": "Floating text box detected",
                    "tooltip": "This content appears to be in a floating text box. ATS systems may read these out of order or miss them entirely. Move this content to the main text flow."
                })
            recommendations.append("Replace floating text boxes with standard left-aligned text")
        
        return {
            "highlights": highlights,
            "recommendations": recommendations
        }
    
    def _detect_scanned_pdf(self, file_path: str) -> Dict[str, Any]:
        """Detect scanned/image-only PDFs"""
        doc = fitz.open(file_path)
        
        highlights = []
        recommendations = []
        
        total_chars = 0
        total_images = 0
        
        for page in doc:
            # Count text characters
            text = page.get_text("text")
            total_chars += len(text.strip())
            
            # Count images
            images = page.get_images()
            total_images += len(images)
        
        doc.close()
        
        # If very little text but many images, likely scanned
        if total_chars < 100 and total_images > 0:
            # Highlight the entire first page
            doc = fitz.open(file_path)
            if len(doc) > 0:
                rect = doc[0].rect
                highlights.append({
                    "page": 1,
                    "bbox": [rect.x0, rect.y0, rect.x1, rect.y1],
                    "severity": "critical",
                    "issue_type": "scanned_pdf",
                    "message": "Image-based or scanned PDF",
                    "tooltip": "Your resume appears to be an image-based or scanned PDF with very little extractable text. ATS systems cannot read image-based content. Please export your resume as a text-based PDF from Word, Google Docs, or your resume editor."
                })
                recommendations.append("Convert scanned/image PDF to text-based PDF by exporting from your original document editor")
            doc.close()
        
        return {
            "highlights": highlights,
            "recommendations": recommendations
        }
    
    def _detect_icon_usage(self, file_path: str, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect icons used instead of text for contact info or skills"""
        doc = fitz.open(file_path)
        
        highlights = []
        recommendations = []
        
        # Check if parsed data is missing common fields
        missing_email = not parsed_data.get("email")
        missing_phone = not parsed_data.get("phone")
        few_skills = len(parsed_data.get("skills", [])) < 3
        
        # Look for suspicious image placements
        for page_num, page in enumerate(doc):
            rect = page.rect
            images = page.get_images()
            
            if len(images) > 0 and (missing_email or missing_phone or few_skills):
                # Check for small images near top (likely icons)
                for img_index, img in enumerate(images):
                    try:
                        img_rect = page.get_image_bbox(img[7])
                        
                        if img_rect:
                            # Small images near top are likely contact icons
                            img_width = img_rect.x1 - img_rect.x0
                            img_height = img_rect.y1 - img_rect.y0
                            img_y = img_rect.y0
                            
                            # Icons are typically small (< 10% of page) and near top
                            is_small = (img_width * img_height) < (rect.width * rect.height * 0.01)
                            is_near_top = img_y < rect.height * 0.2
                            
                            if is_small and is_near_top:
                                highlights.append({
                                    "page": page_num + 1,
                                    "bbox": [img_rect.x0, img_rect.y0, img_rect.x1, img_rect.y1],
                                    "severity": "high",
                                    "issue_type": "icon_usage",
                                    "message": "Icon detected (possibly contact info)",
                                    "tooltip": "Small icons or graphics detected near the top of your resume. If you're using icons for contact information (email, phone, LinkedIn), ATS systems cannot read them. Always include text versions of all contact details and social links."
                                })
                                recommendations.append("Replace icons with text labels for all contact information and links")
                                break  # Only flag once per page
                    except:
                        pass  # Skip if image bbox cannot be retrieved
        
        doc.close()
        
        return {
            "highlights": highlights,
            "recommendations": recommendations
        }
    
    def _detect_date_format_issues(
        self,
        blocks: List[Dict[str, Any]],
        parsed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Detect incorrect date formatting that may confuse ATS"""
        highlights = []
        recommendations = []
        
        # Problematic date patterns
        bad_patterns = [
            (r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*['']\d{2}\b", 
             "apostrophe_year", 
             "Date with apostrophe (e.g., Jan '21)",
             "Dates with apostrophes like \"Jan '21\" can confuse ATS parsers. Use full 4-digit years: \"Jan 2021\" or \"January 2021\"."),
            
            (r"\b\d{4}\s*[-–—]\s*\d{4}\b(?!\s*\()", 
             "year_only", 
             "Year-only dates (e.g., 2021 - 2023)",
             "Using only years without months (e.g., \"2021 - 2023\") makes it harder for ATS to calculate tenure. Include months: \"Jan 2021 - Mar 2023\"."),
            
            (r"\b\d{1}/\d{4}\b", 
             "single_digit_month", 
             "Single-digit month (e.g., 1/2021)",
             "Single-digit months like \"1/2021\" should use two digits or month names. Use \"01/2021\" or \"Jan 2021\" instead."),
            
            (r"\b\d{2}/\d{2}/\d{2,4}\b", 
             "full_date_format", 
             "Full date format (e.g., 01/15/2021)",
             "Full dates like \"01/15/2021\" are unnecessarily precise for resumes. Use month and year only: \"Jan 2021\" or \"01/2021\"."),
            
            (r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b", 
             "day_included", 
             "Date with day (e.g., Jan 15, 2021)",
             "Including the day in dates (e.g., \"Jan 15, 2021\") is too specific. Use month and year only: \"Jan 2021\"."),
        ]
        
        # Good patterns (for reference, not flagged)
        good_patterns = [
            r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}\b",  # Jan 2021
            r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b",  # January 2021
            r"\b\d{2}/\d{4}\b",  # 01/2021
            r"\b(?:Present|Current|Ongoing|Now)\b",  # Present, Current, etc.
        ]
        
        # Check blocks for problematic date patterns
        flagged_blocks = set()  # Track to avoid duplicate highlights
        
        for block in blocks:
            text = block["text"]
            block_id = (block["page"], tuple(block["bbox"]))
            
            # Skip if already flagged
            if block_id in flagged_blocks:
                continue
            
            # Check each bad pattern
            for pattern, issue_type, short_msg, long_msg in bad_patterns:
                matches = list(re.finditer(pattern, text, re.IGNORECASE))
                
                if matches:
                    # Found a problematic date pattern
                    match = matches[0]  # Use first match
                    flagged_blocks.add(block_id)
                    
                    highlights.append({
                        "page": block["page"],
                        "bbox": block["bbox"],
                        "severity": "medium",
                        "issue_type": f"date_format_{issue_type}",
                        "message": short_msg,
                        "tooltip": long_msg + f"\n\nFound: \"{match.group()}\""
                    })
                    
                    if issue_type == "apostrophe_year":
                        recommendations.append("Replace abbreviated years with full 4-digit years (e.g., change 'Jan '21' to 'Jan 2021')")
                    elif issue_type == "year_only":
                        recommendations.append("Add months to year-only dates (e.g., change '2021 - 2023' to 'Jan 2021 - Mar 2023')")
                    elif issue_type == "single_digit_month":
                        recommendations.append("Use two-digit months or month names (e.g., change '1/2021' to '01/2021' or 'Jan 2021')")
                    elif issue_type == "full_date_format":
                        recommendations.append("Remove days from dates, use month and year only (e.g., change '01/15/2021' to '01/2021' or 'Jan 2021')")
                    elif issue_type == "day_included":
                        recommendations.append("Remove days from dates, use month and year only (e.g., change 'Jan 15, 2021' to 'Jan 2021')")
                    
                    break  # Only flag once per block
        
        # Additional check: Look for dates in experience/education data
        experience = parsed_data.get("experience", [])
        education = parsed_data.get("education", [])
        
        # Flag if structured data shows problematic dates
        for exp in experience:
            start_date = exp.get("start_date", "")
            end_date = exp.get("end_date", "")
            
            if start_date or end_date:
                # Check if dates are in bad format
                combined_dates = f"{start_date} {end_date}"
                
                for pattern, issue_type, short_msg, long_msg in bad_patterns:
                    if re.search(pattern, combined_dates, re.IGNORECASE):
                        if not recommendations or "date format" not in str(recommendations):
                            recommendations.append("Use consistent date format throughout: 'Month Year' (e.g., 'Jan 2021') or 'MM/YYYY' (e.g., '01/2021')")
                        break
        
        return {
            "highlights": highlights,
            "recommendations": list(set(recommendations))  # Remove duplicates
        }
    
    def _detect_uncommon_fonts(
        self,
        file_path: str,
        blocks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Detect uncommon fonts that may confuse ATS"""
        highlights = []
        recommendations = []
        
        # ATS-friendly fonts (commonly available and widely supported)
        ats_friendly_fonts = {
            # Serif fonts
            'cambria', 'garamond', 'georgia', 'palatino', 'palatino linotype',
            'times', 'times new roman', 'bookman',
            
            # Sans-serif fonts
            'arial', 'calibri', 'helvetica', 'tahoma', 'verdana', 'trebuchet',
            
            # Common variations and weights
            'arial-bold', 'arial-italic', 'calibri-bold', 'calibri-italic',
            'helvetica-bold', 'helvetica-oblique', 'times-bold', 'times-italic',
            'georgia-bold', 'georgia-italic', 'verdana-bold', 'verdana-italic',
            
            # Include base names that might have variations
            'arialmt', 'arial mt', 'helveticaneue', 'helvetica neue',
            'timesnewroman', 'timesnewromanps', 'timesnewromanpsmt',
            'calibriregular', 'arialregular',
        }
        
        # Fonts to definitely avoid (decorative/difficult to read)
        problematic_fonts = {
            'comic sans', 'comicsans', 'comicsansms', 'comic sans ms',
            'papyrus', 'brush script', 'brushscript', 'curlz', 'impact',
            'zapfino', 'bleeding cowboys', 'chiller', 'jokerman', 'ravie',
            'mistral', 'script', 'freestyle', 'lucida handwriting',
        }
        
        # Map common internal font names to actual font names
        font_name_mapping = {
            # TeX/LaTeX fonts (Computer Modern family)
            'cmr': 'computer modern', 'cmb': 'computer modern', 'cmbx': 'computer modern',
            'cmti': 'computer modern', 'cmsl': 'computer modern', 'cmss': 'computer modern',
            'cmtt': 'computer modern', 'cmssbx': 'computer modern', 'cmsy': 'computer modern',
            
            # Common PostScript/internal names
            'arialmt': 'arial', 'arial-boldmt': 'arial', 'arial-italicmt': 'arial',
            'timesnewromanpsmt': 'times new roman', 'timesnewromanps': 'times new roman',
            'helvetica-bold': 'helvetica', 'helvetica-oblique': 'helvetica',
            'courier': 'courier new', 'couriernew': 'courier new',
        }
        
        doc = fitz.open(file_path)
        
        # Collect all unique fonts used in the document
        all_fonts = set()
        font_locations = {}  # Track where each font is used
        
        for page_num, page in enumerate(doc):
            text_dict = page.get_text("dict")
            
            for block in text_dict.get("blocks", []):
                if block.get("type") == 0:  # Text block
                    bbox = block["bbox"]
                    
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            raw_font_name = span.get("font", "").strip()
                            
                            if raw_font_name:
                                # Clean and map the font name
                                font_name = self._clean_font_name(raw_font_name, font_name_mapping)
                                
                                if font_name:
                                    all_fonts.add(font_name)
                                    
                                    # Track first occurrence of this font (store both raw and cleaned names)
                                    if font_name not in font_locations:
                                        font_locations[font_name] = {
                                            "page": page_num + 1,
                                            "bbox": bbox,
                                            "text_sample": span.get("text", "")[:50],
                                            "raw_name": raw_font_name
                                        }
        
        doc.close()
        
        # Analyze fonts
        uncommon_fonts = []
        decorative_fonts = []
        
        for font in all_fonts:
            # Normalize font name (remove weights, styles, etc. for comparison)
            font_base = self._normalize_font_name(font)
            
            # Check if it's a problematic decorative font
            is_decorative = any(prob in font_base for prob in problematic_fonts)
            
            # Check if it's ATS-friendly
            is_friendly = any(friendly in font_base for friendly in ats_friendly_fonts)
            
            if is_decorative:
                decorative_fonts.append(font)
            elif not is_friendly:
                uncommon_fonts.append(font)
        
        # Flag decorative fonts (high severity)
        for font in decorative_fonts:
            loc = font_locations.get(font, {})
            if loc:
                display_name = font.title() if loc.get("raw_name") == font else f"{font.title()} (PDF name: {loc.get('raw_name', font)})"
                highlights.append({
                    "page": loc["page"],
                    "bbox": loc["bbox"],
                    "severity": "high",
                    "issue_type": "decorative_font",
                    "message": f"Decorative font: {font.title()}",
                    "tooltip": f"Your resume uses '{display_name}', which is a decorative font that is very difficult for ATS systems to read accurately. Decorative fonts can cause text to be completely misread or ignored.\n\nRecommended fonts:\nSerif: Cambria, Garamond, Georgia, Palatino, Times New Roman\nSans-serif: Arial, Calibri, Helvetica, Verdana, Tahoma"
                })
        
        if decorative_fonts:
            font_list = ", ".join(decorative_fonts[:3])
            recommendations.append(f"Replace decorative fonts ({font_list}) with ATS-friendly fonts like Arial, Calibri, or Georgia")
        
        # Flag uncommon fonts (medium severity)
        for font in uncommon_fonts:
            loc = font_locations.get(font, {})
            if loc:
                display_name = font.title() if loc.get("raw_name") == font else f"{font.title()} (PDF name: {loc.get('raw_name', font)})"
                highlights.append({
                    "page": loc["page"],
                    "bbox": loc["bbox"],
                    "severity": "medium",
                    "issue_type": "uncommon_font",
                    "message": f"Uncommon font: {font.title()}",
                    "tooltip": f"Your resume uses '{display_name}', which may not be widely available on ATS systems. While it may look good, uncommon fonts can cause parsing errors or text misinterpretation.\n\nFor maximum ATS compatibility, use these widely supported fonts:\n\nSerif (traditional): Cambria, Garamond, Georgia, Palatino, Times New Roman\nSans-serif (modern): Arial, Calibri, Helvetica, Verdana, Tahoma"
                })
        
        if uncommon_fonts:
            recommendations.append(f"Use ATS-friendly fonts: Arial, Calibri, Georgia, Garamond, Helvetica, or Times New Roman")
        
        # Check for too many different fonts
        if len(all_fonts) > 3:
            # Flag the entire first page
            doc = fitz.open(file_path)
            if len(doc) > 0:
                rect = doc[0].rect
                highlights.append({
                    "page": 1,
                    "bbox": [rect.x0, rect.y0, rect.x1, rect.y1],
                    "severity": "low",
                    "issue_type": "too_many_fonts",
                    "message": f"Too many fonts ({len(all_fonts)} different fonts)",
                    "tooltip": f"Your resume uses {len(all_fonts)} different fonts, which creates inconsistency and can confuse ATS parsers. Stick to 1-2 fonts maximum:\n\n• One font for headings\n• One font for body text\n\nRecommended: Use a single font family throughout for maximum clarity."
                })
                recommendations.append("Use only 1-2 fonts maximum throughout your resume for consistency")
            doc.close()
        
        return {
            "highlights": highlights,
            "recommendations": recommendations
        }
    
    def _detect_ats_extraction_gaps(
        self,
        file_path: str,
        blocks: List[Dict[str, Any]],
        parsed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        DIFFERENTIAL ANALYSIS: Trust the ATS parser's results, then explain WHY
        extraction was poor by correlating with formatting issues.
        
        Philosophy:
        - Commercial parser = "ground truth" for what ATS extracted
        - PyMuPDF = find formatting problems that explain poor extraction
        - Don't compete with parser, explain its struggles
        """
        highlights = []
        recommendations = []
        
        # Extract all text from blocks for simple pattern matching
        all_text = "\n".join([b.get("text", "") for b in blocks])
        
        # 1. Check CONTACT INFORMATION - simple regex patterns we CAN reliably detect
        contact_gaps = self._check_contact_extraction_gaps(blocks, parsed_data, all_text)
        highlights.extend(contact_gaps["highlights"])
        recommendations.extend(contact_gaps["recommendations"])
        
        # 2. Check SKILLS extraction - correlate low extraction with formatting issues
        skills_gaps = self._check_skills_extraction_quality(blocks, parsed_data)
        highlights.extend(skills_gaps["highlights"])
        recommendations.extend(skills_gaps["recommendations"])
        
        # 3. Check EXPERIENCE extraction quality
        experience_gaps = self._check_experience_extraction_quality(blocks, parsed_data)
        highlights.extend(experience_gaps["highlights"])
        recommendations.extend(experience_gaps["recommendations"])
        
        # 4. Check EDUCATION extraction quality
        education_gaps = self._check_education_extraction_quality(blocks, parsed_data)
        highlights.extend(education_gaps["highlights"])
        recommendations.extend(education_gaps["recommendations"])
        
        return {
            "highlights": highlights,
            "recommendations": recommendations
        }
    
    def _check_contact_extraction_gaps(
        self,
        blocks: List[Dict[str, Any]],
        parsed_data: Dict[str, Any],
        all_text: str
    ) -> Dict[str, Any]:
        """Check if contact info is visible but not extracted by ATS"""
        highlights = []
        recommendations = []
        
        contact_info = parsed_data.get("contact_info", {})
        
        # Email pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        # Phone pattern (various formats)
        phone_pattern = r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'
        # LinkedIn pattern
        linkedin_pattern = r'(?:linkedin\.com/in/|linkedin\.com/pub/)[\w-]+'
        
        # Check for email
        emails_in_text = re.findall(email_pattern, all_text)
        parsed_email = contact_info.get("email")
        
        if emails_in_text and not parsed_email:
            # Email exists visually but ATS didn't extract it
            for block in blocks:
                if re.search(email_pattern, block.get("text", "")):
                    highlights.append({
                        "page": block["page"],
                        "bbox": block["bbox"],
                        "severity": "critical",
                        "issue_type": "missing_email_extraction",
                        "message": "Email not extracted by ATS",
                        "tooltip": f"Your email address '{emails_in_text[0]}' is visible on the resume but was NOT extracted by the ATS parser. This is a CRITICAL issue.\n\nLikely causes:\n• Email is in header/footer region\n• Email is inside an image or text box\n• Complex formatting around email\n\nFix: Move your email to the main body, directly under your name."
                    })
                    recommendations.append("Move email address to main body under your name - it's currently not being extracted by ATS")
                    break
        
        # Check for phone
        phones_in_text = re.findall(phone_pattern, all_text)
        parsed_phone = contact_info.get("phone")
        
        if phones_in_text and not parsed_phone:
            # Phone exists visually but ATS didn't extract it
            for block in blocks:
                if re.search(phone_pattern, block.get("text", "")):
                    highlights.append({
                        "page": block["page"],
                        "bbox": block["bbox"],
                        "severity": "high",
                        "issue_type": "missing_phone_extraction",
                        "message": "Phone not extracted by ATS",
                        "tooltip": f"Your phone number is visible but was NOT extracted by the ATS parser.\n\nLikely causes:\n• Phone is in header/footer\n• Unusual phone formatting\n• Phone mixed with icons\n\nFix: Use standard format like (555) 123-4567 or 555-123-4567 in the main body."
                    })
                    recommendations.append("Reformat phone number using standard format: (555) 123-4567")
                    break
        
        # Check for LinkedIn
        linkedin_in_text = re.findall(linkedin_pattern, all_text, re.IGNORECASE)
        parsed_linkedin = contact_info.get("linkedin")
        
        if linkedin_in_text and not parsed_linkedin:
            for block in blocks:
                if re.search(linkedin_pattern, block.get("text", ""), re.IGNORECASE):
                    highlights.append({
                        "page": block["page"],
                        "bbox": block["bbox"],
                        "severity": "medium",
                        "issue_type": "missing_linkedin_extraction",
                        "message": "LinkedIn not extracted by ATS",
                        "tooltip": "Your LinkedIn URL is visible but was NOT extracted by the ATS.\n\nLikely causes:\n• LinkedIn displayed as icon only\n• LinkedIn in header/footer\n• Non-standard URL format\n\nFix: Write full URL as text: linkedin.com/in/yourname"
                    })
                    recommendations.append("Display LinkedIn URL as plain text, not just as an icon")
                    break
        
        return {
            "highlights": highlights,
            "recommendations": recommendations
        }
    
    def _check_skills_extraction_quality(
        self,
        blocks: List[Dict[str, Any]],
        parsed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check skills extraction quality by correlating ATS results with formatting issues.
        Trust the parser, explain WHY extraction might be poor.
        """
        highlights = []
        recommendations = []
        
        parsed_skills = parsed_data.get("skills", [])
        
        # Find skills section location
        skill_headers = ['skills', 'technical skills', 'core competencies', 'technologies', 
                        'expertise', 'proficiencies', 'tools', 'technical']
        
        skills_blocks = []
        skills_section_found = False
        
        for i, block in enumerate(blocks):
            text = block.get("text", "").lower()
            
            # Check if this is a skills header
            if any(header == text.strip() or f"{header}:" in text for header in skill_headers):
                skills_section_found = True
                # Collect surrounding blocks
                for j in range(i, min(i + 6, len(blocks))):
                    skills_blocks.append(blocks[j])
                break
        
        if not skills_section_found:
            # No dedicated skills section found
            if len(parsed_skills) == 0:
                # ATS found no skills and there's no skills section
                highlights.append({
                    "page": 1,
                    "bbox": [0, 0, 100, 100],
                    "severity": "high",
                    "issue_type": "no_skills_section",
                    "message": "No dedicated Skills section detected",
                    "tooltip": "ATS extracted 0 skills. Your resume appears to have no dedicated Skills section.\n\nBest practice: Always include a clear Skills section with a header like 'SKILLS' or 'TECHNICAL SKILLS'.\n\nThis helps both ATS and recruiters quickly identify your capabilities."
                })
                recommendations.append("Add a dedicated Skills section with clear header (e.g., 'SKILLS' or 'TECHNICAL SKILLS')")
            return {"highlights": highlights, "recommendations": recommendations}
        
        # Skills section exists - check extraction quality
        if len(parsed_skills) == 0:
            # Skills section exists but ATS extracted nothing - major formatting problem
            # Check what formatting issues exist in this section
            formatting_issues = self._diagnose_section_formatting(skills_blocks)
            
            issue_text = "ATS extracted 0 skills despite a Skills section being present.\n\n"
            if formatting_issues:
                issue_text += "Detected formatting problems:\n" + "\n".join(f"• {issue}" for issue in formatting_issues)
            else:
                issue_text += "Possible causes:\n• Skills in a table or grid\n• Skills in sidebar column\n• Unusual formatting or separators"
            
            for block in skills_blocks[:2]:  # Highlight first 2 blocks
                highlights.append({
                    "page": block["page"],
                    "bbox": block["bbox"],
                    "severity": "critical",
                    "issue_type": "skills_section_unreadable",
                    "message": "Skills section not extracted by ATS",
                    "tooltip": issue_text + "\n\nFix: Use simple bullet points in the main body:\n• Python\n• JavaScript\n• React"
                })
            
            recommendations.append("Reformat Skills section as simple bullet points - ATS extracted 0 skills")
        
        elif len(parsed_skills) < 3:
            # ATS extracted very few skills - likely partial extraction failure
            formatting_issues = self._diagnose_section_formatting(skills_blocks)
            
            if formatting_issues:
                for block in skills_blocks[:1]:
                    highlights.append({
                        "page": block["page"],
                        "bbox": block["bbox"],
                        "severity": "high",
                        "issue_type": "skills_partially_extracted",
                        "message": f"Only {len(parsed_skills)} skill(s) extracted by ATS",
                        "tooltip": f"ATS extracted only {len(parsed_skills)} skill(s).\n\nDetected formatting issues:\n" + "\n".join(f"• {issue}" for issue in formatting_issues) + "\n\nThese formatting issues likely prevented full extraction."
                    })
                
                recommendations.append(f"Skills section has formatting issues - only {len(parsed_skills)} skills extracted")
        
        return {
            "highlights": highlights,
            "recommendations": recommendations
        }
    
    def _diagnose_section_formatting(self, section_blocks: List[Dict[str, Any]]) -> List[str]:
        """
        Diagnose formatting issues in a section by checking against known problems.
        Returns list of detected issues.
        """
        issues = []
        
        if not section_blocks:
            return issues
        
        # Check if section is in a table (already detected earlier)
        for block in section_blocks:
            block_id = (block["page"], tuple(block["bbox"]))
            
            # Check our previously detected issues for this block
            if block.get("in_table"):
                issues.append("Content in table/grid format")
                break
        
        # Check if section is in sidebar (secondary column)
        if section_blocks:
            # Check column placement
            first_block = section_blocks[0]
            page_width = 612  # Standard letter width in points
            x_pos = first_block["bbox"][0]
            
            # If starts in right half or narrow column
            if x_pos > page_width * 0.6:
                issues.append("Content in sidebar/secondary column")
            elif first_block["bbox"][2] - first_block["bbox"][0] < page_width * 0.4:
                issues.append("Content in narrow column")
        
        # Check if content has unusual separators
        text = " ".join([b.get("text", "") for b in section_blocks])
        if '|' in text:
            issues.append("Pipe separators used (|)")
        if text.count(',') > 5:  # Multiple commas
            issues.append("Comma-separated format")
        
        # Check for header/footer placement
        for block in section_blocks:
            if block.get("region") in ["header", "footer"]:
                issues.append(f"Content in {block.get('region')} region")
                break
        
        return issues
    
    def _check_experience_extraction_quality(
        self,
        blocks: List[Dict[str, Any]],
        parsed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check experience extraction quality - trust parser, explain formatting issues.
        """
        highlights = []
        recommendations = []
        
        parsed_experience = parsed_data.get("experience", [])
        
        # Find experience section location
        exp_headers = ['experience', 'work experience', 'employment', 'work history', 
                      'professional experience', 'career']
        
        exp_section_blocks = []
        exp_section_found = False
        
        for i, block in enumerate(blocks):
            text = block.get("text", "").lower().strip()
            
            # Check if this is experience header
            if any(header == text or f"{header}:" in text for header in exp_headers):
                exp_section_found = True
                # Collect blocks until next section
                for j in range(i + 1, len(blocks)):
                    next_text = blocks[j].get("text", "").lower().strip()
                    # Stop at next major section
                    if any(h in next_text for h in ['education', 'skills', 'projects', 'certifications', 'awards']):
                        break
                    exp_section_blocks.append(blocks[j])
                break
        
        if not exp_section_found:
            return {"highlights": highlights, "recommendations": recommendations}
        
        # Check extraction quality based on ATS results
        if len(parsed_experience) == 0 and len(exp_section_blocks) > 0:
            # Experience section exists but ATS extracted nothing
            formatting_issues = self._diagnose_section_formatting(exp_section_blocks)
            
            for block in exp_section_blocks[:2]:
                highlights.append({
                    "page": block["page"],
                    "bbox": block["bbox"],
                    "severity": "critical",
                    "issue_type": "experience_not_extracted",
                    "message": "Experience section not extracted by ATS",
                    "tooltip": f"ATS extracted 0 jobs from your Experience section.\n\n" + 
                              (f"Detected formatting issues:\n" + "\n".join(f"• {issue}" for issue in formatting_issues) if formatting_issues 
                               else "Likely causes:\n• Jobs in table format\n• Multi-column layout\n• Missing job titles or dates") +
                              "\n\nFix: Use simple format:\nJob Title | Company\nMonth Year - Month Year\n• Achievement\n• Achievement"
                })
            
            recommendations.append("Experience section not readable by ATS - check formatting")
        
        elif len(parsed_experience) > 0:
            # Check for jobs without bullet points
            jobs_without_bullets = sum(1 for job in parsed_experience 
                                      if not job.get("bullets") or len(job.get("bullets", [])) == 0)
            
            if jobs_without_bullets > 0 and len(exp_section_blocks) > 0:
                highlights.append({
                    "page": exp_section_blocks[0]["page"],
                    "bbox": exp_section_blocks[0]["bbox"],
                    "severity": "high",
                    "issue_type": "missing_job_descriptions",
                    "message": f"{jobs_without_bullets} job(s) missing bullet points",
                    "tooltip": f"ATS extracted {len(parsed_experience)} jobs, but {jobs_without_bullets} have no bullet points/descriptions.\n\nLikely causes:\n• Descriptions in paragraph format\n• Bullets in a table\n• Unusual bullet characters\n\nFix: Use standard bullet points (•, -, or *) for each job."
                })
                recommendations.append(f"Add bullet points to job descriptions - {jobs_without_bullets} jobs have no bullets extracted")
            
            # Check for jobs missing key fields
            incomplete_jobs = 0
            for job in parsed_experience:
                if not job.get("title") or not job.get("company"):
                    incomplete_jobs += 1
            
            if incomplete_jobs > 0 and len(exp_section_blocks) > 0:
                highlights.append({
                    "page": exp_section_blocks[0]["page"],
                    "bbox": exp_section_blocks[0]["bbox"],
                    "severity": "high",
                    "issue_type": "incomplete_job_entries",
                    "message": f"{incomplete_jobs} job(s) missing title or company",
                    "tooltip": f"{incomplete_jobs} job entries are missing critical information (title or company name).\n\nEnsure each job clearly shows:\n• Job Title\n• Company Name\n• Date Range"
                })
                recommendations.append("Ensure all jobs have clear job title and company name")
        
        return {
            "highlights": highlights,
            "recommendations": recommendations
        }
    
    def _check_education_extraction_quality(
        self,
        blocks: List[Dict[str, Any]],
        parsed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check education extraction quality - trust parser, explain formatting issues.
        """
        highlights = []
        recommendations = []
        
        parsed_education = parsed_data.get("education", [])
        
        # Find education section location
        edu_headers = ['education', 'academic', 'academic background', 'qualifications']
        
        edu_section_blocks = []
        edu_section_found = False
        
        for i, block in enumerate(blocks):
            text = block.get("text", "").lower().strip()
            
            if any(header == text or f"{header}:" in text for header in edu_headers):
                edu_section_found = True
                # Collect blocks until next section
                for j in range(i + 1, len(blocks)):
                    next_text = blocks[j].get("text", "").lower().strip()
                    # Stop at next major section
                    if any(h in next_text for h in ['experience', 'skills', 'projects', 'certifications', 'awards']):
                        break
                    edu_section_blocks.append(blocks[j])
                break
        
        if not edu_section_found:
            return {"highlights": highlights, "recommendations": recommendations}
        
        # Check extraction quality
        if len(parsed_education) == 0 and len(edu_section_blocks) > 0:
            # Education section exists but ATS extracted nothing
            formatting_issues = self._diagnose_section_formatting(edu_section_blocks)
            
            for block in edu_section_blocks[:2]:
                highlights.append({
                    "page": block["page"],
                    "bbox": block["bbox"],
                    "severity": "high",
                    "issue_type": "education_not_extracted",
                    "message": "Education not extracted by ATS",
                    "tooltip": f"ATS extracted 0 education entries.\n\n" +
                              (f"Detected formatting issues:\n" + "\n".join(f"• {issue}" for issue in formatting_issues) if formatting_issues
                               else "Likely causes:\n• Education in table format\n• Non-standard degree names\n• Missing university name") +
                              "\n\nFix: Use clear format:\nDegree Name (e.g., Bachelor of Science in Computer Science)\nUniversity Name\nGraduation Date"
                })
            
            recommendations.append("Education section not readable by ATS - check formatting")
        
        elif len(parsed_education) > 0:
            # Check for incomplete education entries
            incomplete_edu = 0
            for edu in parsed_education:
                if not edu.get("degree") or not edu.get("institution"):
                    incomplete_edu += 1
            
            if incomplete_edu > 0 and len(edu_section_blocks) > 0:
                highlights.append({
                    "page": edu_section_blocks[0]["page"],
                    "bbox": edu_section_blocks[0]["bbox"],
                    "severity": "medium",
                    "issue_type": "incomplete_education_entries",
                    "message": f"{incomplete_edu} education entry(ies) incomplete",
                    "tooltip": f"{incomplete_edu} education entries are missing degree name or university name.\n\nEnsure each entry clearly shows:\n• Degree Name\n• University/Institution Name\n• Graduation Date (or expected)"
                })
                recommendations.append("Ensure all education entries have clear degree and institution names")
        
        return {
            "highlights": highlights,
            "recommendations": recommendations
        }
    
    def _clean_font_name(self, raw_font_name: str, font_mapping: Dict[str, str]) -> str:
        """Clean and standardize font names from PDFs"""
        if not raw_font_name:
            return ""
        
        # Convert to lowercase for processing
        font_name = raw_font_name.lower().strip()
        
        # Remove font subset prefix (e.g., "ABCDEE+" or "ABCDEF+")
        # Font subsets are prefixed with 6 uppercase letters + "+"
        if len(font_name) > 7 and font_name[6] == '+':
            font_name = font_name[7:]
        
        # Check if it matches a known internal name prefix (e.g., "cmbx10" → "cmbx")
        for prefix, mapped_name in font_mapping.items():
            if font_name.startswith(prefix):
                return mapped_name
        
        # Normalize the font name
        return self._normalize_font_name(font_name)
    
    def _normalize_font_name(self, font_name: str) -> str:
        """Normalize font name for comparison"""
        # Convert to lowercase
        normalized = font_name.lower()
        
        # Remove common suffixes
        suffixes = ['-bold', '-italic', '-regular', '-light', '-medium', 
                   '-semibold', '-black', '-oblique', 'mt', 'ps', 'psmt',
                   '-boldmt', '-italicmt', 'regular', 'bold', 'italic']
        
        for suffix in suffixes:
            normalized = normalized.replace(suffix, '')
        
        # Remove hyphens, underscores and extra spaces
        normalized = normalized.replace('-', '').replace('_', '').replace('  ', ' ').strip()
        
        return normalized
    
    def _calculate_summary(self, highlights: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate issue summary by severity"""
        summary = {
            "total_issues": len(highlights),
            "critical": sum(1 for h in highlights if h["severity"] == "critical"),
            "high": sum(1 for h in highlights if h["severity"] == "high"),
            "medium": sum(1 for h in highlights if h["severity"] == "medium"),
            "low": sum(1 for h in highlights if h["severity"] == "low")
        }
        return summary
    
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

