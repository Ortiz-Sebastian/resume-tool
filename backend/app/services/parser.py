"""
Unified Resume Parser - Hybrid approach combining commercial and open-source parsers.

This is the main entry point for resume parsing. It orchestrates:
1. Commercial parser (Affinda API) for high-accuracy structured data extraction
2. PyMuPDF for ATS view generation (always, regardless of parser choice)
3. Fallback to spaCy if commercial parser unavailable

This hybrid approach provides both credibility (commercial parser) and
uniqueness (ATS diagnostics from PyMuPDF).
"""

from typing import Dict, Any
import os
from app.config import settings
from app.services.base_parser import BaseResumeParser
from app.services.textkernel_parser import TextkernelParser
from app.services.spacy_parser import SpacyResumeParser
from app.services.ats_view_generator import ATSViewGenerator


class ResumeParser:
    """
    Unified resume parser with hybrid approach:
    - Uses commercial parser (Affinda API) for structured data when available
    - Always uses PyMuPDF for ATS view and diagnostics
    - Falls back to spaCy parser if commercial parser not configured
    """
    
    def __init__(self):
        self.ats_generator = ATSViewGenerator()
        self._structured_parser = self._initialize_parser()
    
    def _initialize_parser(self) -> BaseResumeParser:
        """Initialize the appropriate structured data parser based on configuration"""
        parser_type = settings.parser_type.lower()
        
        if parser_type == "textkernel":
            parser = TextkernelParser()
            if parser.is_available():
                print(f"✓ Using Affinda API parser (commercial-grade accuracy)")
                return parser
            else:
                print(f"⚠ Affinda API configured but API key/workspace ID missing, falling back to spaCy")
        
        # Default to spaCy parser
        parser = SpacyResumeParser()
        if parser.is_available():
            print(f"✓ Using spaCy parser (open-source)")
            return parser
        else:
            raise ValueError(
                "No parser available. Either:\n"
                "1. Configure Affinda API: set AFFINDA_API_KEY and AFFINDA_WORKSPACE_ID in .env\n"
                "2. Install spaCy model: python -m spacy download en_core_web_lg"
            )
    
    def parse(self, file_path: str, file_type: str) -> Dict[str, Any]:
        """
        Parse resume using hybrid approach.
        
        Returns comprehensive data including:
        - Structured data (from commercial parser or spaCy)
        - ATS plain-text view (always from PyMuPDF)
        - Layout diagnostics (always from PyMuPDF)
        
        Args:
            file_path: Path to resume file
            file_type: File extension (.pdf or .docx)
        
        Returns:
            Dictionary with all parsed data
        """
        # Step 1: Get structured data from configured parser
        try:
            structured_data = self._structured_parser.parse_to_structured_json(file_path, file_type)
            parser_used = self._structured_parser.get_parser_name()
        except Exception as e:
            # If commercial parser fails, try fallback
            print(f"⚠ Primary parser failed: {e}")
            if not isinstance(self._structured_parser, SpacyResumeParser):
                print("Falling back to spaCy parser...")
                fallback_parser = SpacyResumeParser()
                if fallback_parser.is_available():
                    structured_data = fallback_parser.parse_to_structured_json(file_path, file_type)
                    parser_used = "spaCy (fallback)"
                else:
                    raise Exception("Both primary and fallback parsers failed")
            else:
                raise
        
        # Step 2: Always generate ATS view with PyMuPDF (regardless of structured parser)
        ats_data = self.ats_generator.generate_ats_view(file_path, file_type)
        
        # Step 3: Merge results
        result = {
            **structured_data,  # All structured fields (name, email, experience, etc.)
            "ats_text": ats_data["ats_text"],  # Plain text ATS view
            "ats_diagnostics": ats_data["diagnostics"],  # Layout analysis
            "parsing_metadata": {
                "structured_parser": parser_used,
                "ats_generator": "PyMuPDF",
                "file_type": file_type
            }
        }
        
        return result
    
    def get_parser_info(self) -> Dict[str, Any]:
        """Get information about the configured parsers"""
        return {
            "structured_parser": {
                "name": self._structured_parser.get_parser_name(),
                "available": self._structured_parser.is_available()
            },
            "ats_generator": {
                "name": "PyMuPDF",
                "available": True
            },
            "configuration": {
                "parser_type": settings.parser_type,
                "affinda_configured": bool(os.getenv("AFFINDA_API_KEY") or settings.textkernel_api_key),
                "affinda_workspace_configured": bool(os.getenv("AFFINDA_WORKSPACE_ID") or settings.affinda_workspace_id)
            }
        }


# Convenience function for backward compatibility
def get_resume_parser() -> ResumeParser:
    """Factory function to get configured resume parser instance"""
    return ResumeParser()
