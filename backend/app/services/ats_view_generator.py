"""
ATS View Generator - Uses PyMuPDF for accurate text extraction and layout analysis.

This is SEPARATE from the structured parser and always uses PyMuPDF to show
exactly how ATS systems will read the resume.
"""

import fitz  # PyMuPDF
from docx import Document
from typing import Dict, Any, List, Tuple


class ATSViewGenerator:
    """Generate ATS-compatible plain text view and extract layout diagnostics"""
    
    def generate_ats_view(self, file_path: str, file_type: str) -> Dict[str, Any]:
        """
        Generate ATS plain-text view and layout diagnostics.
        
        Returns:
            {
                "ats_text": str - Plain text as ATS would see it
                "diagnostics": {
                    "has_images": bool,
                    "has_tables": bool,
                    "has_headers_footers": bool,
                    "has_text_boxes": bool,
                    "font_count": int,
                    "page_count": int,
                    "character_count": int,
                    "layout_complexity": str,  # simple/moderate/complex
                    "warnings": List[str]
                }
            }
        """
        if file_type == ".pdf":
            return self._generate_from_pdf(file_path)
        elif file_type == ".docx":
            return self._generate_from_docx(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
    
    def _generate_from_pdf(self, file_path: str) -> Dict[str, Any]:
        """Generate ATS view and diagnostics from PDF"""
        doc = fitz.open(file_path)
        
        # Extract plain text (as ATS sees it)
        ats_text = ""
        for page in doc:
            ats_text += page.get_text("text")
        
        # Run diagnostics
        diagnostics = self._analyze_pdf_layout(doc)
        
        doc.close()
        
        return {
            "ats_text": ats_text,
            "diagnostics": diagnostics
        }
    
    def _generate_from_docx(self, file_path: str) -> Dict[str, Any]:
        """Generate ATS view and diagnostics from DOCX"""
        doc = Document(file_path)
        
        # Extract plain text
        ats_text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        
        # Basic diagnostics for DOCX
        diagnostics = self._analyze_docx_layout(doc)
        
        return {
            "ats_text": ats_text,
            "diagnostics": diagnostics
        }
    
    def _analyze_pdf_layout(self, doc: fitz.Document) -> Dict[str, Any]:
        """Analyze PDF layout for ATS compatibility issues"""
        has_images = False
        has_tables = False
        has_text_boxes = False
        font_set = set()
        warnings = []
        
        for page_num, page in enumerate(doc):
            # Check for images
            images = page.get_images()
            if images:
                has_images = True
                warnings.append(f"Page {page_num + 1}: Contains {len(images)} image(s) - ATS cannot read these")
            
            # Check for tables
            tables = page.find_tables()
            if tables.tables:
                has_tables = True
                warnings.append(f"Page {page_num + 1}: Contains tables - may confuse ATS systems")
            
            # Analyze fonts
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            font_set.add(span["font"])
            
            # Check for text boxes (text in separate layers)
            drawings = page.get_drawings()
            if drawings:
                has_text_boxes = True
        
        # Determine layout complexity
        font_count = len(font_set)
        if font_count <= 2 and not has_images and not has_tables:
            complexity = "simple"
        elif font_count <= 4 and (has_images or has_tables):
            complexity = "moderate"
        else:
            complexity = "complex"
            warnings.append("Complex layout with multiple fonts may reduce ATS accuracy")
        
        # Check for headers/footers (heuristic: text in top/bottom 10% of page)
        has_headers_footers = self._detect_headers_footers(doc)
        if has_headers_footers:
            warnings.append("Headers/footers detected - may interfere with ATS parsing")
        
        return {
            "has_images": has_images,
            "has_tables": has_tables,
            "has_headers_footers": has_headers_footers,
            "has_text_boxes": has_text_boxes,
            "font_count": font_count,
            "page_count": len(doc),
            "character_count": len("".join([page.get_text() for page in doc])),
            "layout_complexity": complexity,
            "warnings": warnings
        }
    
    def _analyze_docx_layout(self, doc: Document) -> Dict[str, Any]:
        """Analyze DOCX layout for ATS compatibility"""
        warnings = []
        
        # Check for tables
        has_tables = len(doc.tables) > 0
        if has_tables:
            warnings.append(f"Document contains {len(doc.tables)} table(s) - may confuse ATS")
        
        # Check for images (inline shapes)
        has_images = False
        for rel in doc.part.rels.values():
            if "image" in rel.target_ref:
                has_images = True
                warnings.append("Document contains images - ATS cannot read these")
                break
        
        # Count paragraphs and text
        paragraph_count = len(doc.paragraphs)
        text = "\n".join([p.text for p in doc.paragraphs])
        
        # Determine complexity
        if not has_images and not has_tables and paragraph_count < 50:
            complexity = "simple"
        elif has_tables or paragraph_count > 100:
            complexity = "moderate"
        else:
            complexity = "simple"
        
        return {
            "has_images": has_images,
            "has_tables": has_tables,
            "has_headers_footers": False,  # Hard to detect in DOCX
            "has_text_boxes": False,
            "font_count": 0,  # Not easily accessible in python-docx
            "page_count": 1,  # Estimate
            "character_count": len(text),
            "layout_complexity": complexity,
            "warnings": warnings
        }
    
    def _detect_headers_footers(self, doc: fitz.Document) -> bool:
        """Detect if document has headers/footers"""
        for page in doc:
            rect = page.rect
            height = rect.height
            
            # Check top 10% and bottom 10% for text
            top_rect = fitz.Rect(0, 0, rect.width, height * 0.1)
            bottom_rect = fitz.Rect(0, height * 0.9, rect.width, height)
            
            top_text = page.get_text("text", clip=top_rect).strip()
            bottom_text = page.get_text("text", clip=bottom_rect).strip()
            
            if top_text or bottom_text:
                return True
        
        return False
    
    def extract_text_with_coordinates(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract text with bounding box coordinates (useful for advanced features).
        
        Returns list of text blocks with coordinates:
        [
            {
                "text": str,
                "x0": float, "y0": float, "x1": float, "y1": float,
                "page": int,
                "font_size": float,
                "font_name": str
            }
        ]
        """
        doc = fitz.open(file_path)
        blocks = []
        
        for page_num, page in enumerate(doc):
            text_dict = page.get_text("dict")
            for block in text_dict["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            blocks.append({
                                "text": span["text"],
                                "x0": span["bbox"][0],
                                "y0": span["bbox"][1],
                                "x1": span["bbox"][2],
                                "y1": span["bbox"][3],
                                "page": page_num + 1,
                                "font_size": span["size"],
                                "font_name": span["font"]
                            })
        
        doc.close()
        return blocks

