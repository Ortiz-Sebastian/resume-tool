"""
Abstract base class for resume parsers.

This allows swapping between different parsing engines (spaCy, Textkernel, etc.)
while maintaining a consistent interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseResumeParser(ABC):
    """Abstract base class for resume parsing implementations"""
    
    @abstractmethod
    def parse_to_structured_json(self, file_path: str, file_type: str) -> Dict[str, Any]:
        """
        Parse resume file and return structured data.
        
        Args:
            file_path: Path to the resume file
            file_type: File extension (.pdf or .docx)
            
        Returns:
            Dictionary with standardized structure:
            {
                "name": str,
                "email": str,
                "phone": str,
                "location": str,
                "summary": str,
                "experience": List[{
                    "title": str,
                    "company": str,
                    "start_date": str,
                    "end_date": str,
                    "location": str,
                    "description": str,
                    "highlights": List[str]
                }],
                "education": List[{
                    "degree": str,
                    "institution": str,
                    "graduation_date": str,
                    "gpa": str,
                    "major": str
                }],
                "skills": List[str],
                "certifications": List[{
                    "name": str,
                    "issuer": str,
                    "date": str
                }],
                "languages": List[str],
                "raw_text": str,
                "metadata": Dict[str, Any]
            }
        """
        pass
    
    @abstractmethod
    def get_parser_name(self) -> str:
        """Return the name of this parser implementation"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this parser is properly configured and available"""
        pass

