"""
LLM-Powered Resume Diagnostic Service

Takes user's observation + layout data → Returns intelligent explanation

TWO-TIER RECOMMENDATION SYSTEM:

TIER 1 - Rule-Based (ats_issue_detector.py):
  • Fast, generic recommendations shown immediately
  • Example: "Move email from header to body"
  • Purpose: Quick overview in score summary

TIER 2 - AI-Based (this file):
  • Contextual, detailed, personalized recommendations
  • Shown on-demand when user asks questions
  • Example: "Your email 'john@example.com' is in the header at top-right. 
    Move it to line 2 under your name: 'Email: john@example.com'"
  • Purpose: Deep diagnostic with specific instructions

This service provides TIER 2 - detailed, context-aware explanations.
"""

from typing import Dict, Any, List
import os
from openai import OpenAI


class LLMDiagnostic:
    """Uses OpenAI to explain ATS extraction issues based on user prompts"""
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key) if api_key else None
    
    def explain_issues(
        self,
        user_prompt: str,
        ats_extracted: Dict[str, Any],
        detected_issues: List[Dict[str, Any]],  # Structured ATSIssue objects
        block_summaries: List[Dict[str, Any]]   # Condensed block info
    ) -> Dict[str, Any]:
        """
        Get intelligent explanation from OpenAI about detected issues.
        
        Args:
            user_prompt: User's observation (e.g., "I'm missing 5 skills")
            ats_extracted: What ATS actually extracted
            detected_issues: List of structured ATSIssue objects (already detected by rules)
            block_summaries: Condensed block information for context
        """
        if not self.client:
            return {
                "explanation": "OpenAI API key not configured. Please set OPENAI_API_KEY environment variable.",
                "location": None,
                "recommendations": []
            }
        
        # Build the prompt
        system_prompt = self._build_system_prompt()
        user_message = self._build_user_message(
            user_prompt,
            ats_extracted,
            detected_issues,
            block_summaries
        )
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Fast and cheap
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3,  # Keep it focused
                max_tokens=600
            )
            
            # Parse response
            content = response.choices[0].message.content
            return self._parse_llm_response(content)
            
        except Exception as e:
            return {
                "explanation": f"Error calling OpenAI: {str(e)}",
                "location": None,
                "recommendations": []
            }
    
    def _build_system_prompt(self) -> str:
        """System prompt defining the LLM's role"""
        return """You are an ATS (Applicant Tracking System) resume formatting expert.

You will receive:
- user_observation: What the user noticed is wrong
- ats_extracted: What the ATS actually extracted  
- detected_issues: List of issues found by BUSINESS RULES (already detected, not guessing)
- block_summaries: Context about resume structure

IMPORTANT: The "detected_issues" are DEFINITIVE. They were found by reliable business logic, NOT AI guessing.

Your job is to EXPLAIN, not DETECT:
1. Match user's observation to the relevant detected issue(s)
2. Explain WHY this happened in simple, human terms
3. Use the location_hint from issues to tell user WHERE to look
4. Translate technical issue details into actionable fixes

Structure your response EXACTLY as:

**Why this happened:**
[2-3 sentence explanation in plain English - connect the issue to the symptom]

**Where to look:**
[Use the location_hint from relevant issues - be specific]

**How to fix:**
1. [Specific action]
2. [Specific action]
3. [Specific action]

Be concise. Focus on the most relevant issue(s) that match the user's observation."""
    
    def _build_user_message(
        self,
        user_prompt: str,
        ats_extracted: Dict[str, Any],
        detected_issues: List[Dict[str, Any]],
        block_summaries: List[Dict[str, Any]]
    ) -> str:
        """Build the user message with structured issues from rule-based detection"""
        
        import json
        
        # Build structured data payload
        data_payload = {
            "user_observation": user_prompt,
            
            "ats_extracted": {
                "contact_info": {
                    "email": ats_extracted.get("contact_info", {}).get("email") or "NOT_EXTRACTED",
                    "phone": ats_extracted.get("contact_info", {}).get("phone") or "NOT_EXTRACTED",
                },
                "skills": {
                    "count": len(ats_extracted.get("skills", [])),
                    "list": ats_extracted.get("skills", [])[:15]  # First 15
                },
                "experience": {
                    "count": len(ats_extracted.get("experience", [])),
                    "jobs": [
                        {
                            "title": job.get("title", "No title"),
                            "company": job.get("company", "No company"),
                            "bullets_count": len(job.get("bullets", []))
                        }
                        for job in ats_extracted.get("experience", [])[:5]  # First 5 jobs
                    ]
                },
                "education": {
                    "count": len(ats_extracted.get("education", [])),
                    "degrees": [
                        {
                            "degree": edu.get("degree", "No degree"),
                            "institution": edu.get("institution", "No institution")
                        }
                        for edu in ats_extracted.get("education", [])[:3]  # First 3
                    ]
                }
            },
            
            "detected_issues": detected_issues,  # Structured ATSIssue objects (rule-based)
            
            "block_summaries": block_summaries  # Condensed block info for context
        }
        
        # Format as clean JSON string
        message = f"""User's observation: "{user_prompt}"

Here is the structured data about this resume:

```json
{json.dumps(data_payload, indent=2)}
```

The "detected_issues" are DEFINITIVE - detected by business rules (not AI guessing).
Each issue has:
- code: machine ID
- severity: low/medium/high/critical
- section: which part is affected
- message: short summary
- details: explanation
- location_hint: where to look

Your job is to:
1. Identify which detected issue(s) relate to the user's observation
2. Explain WHY this happened in simple terms (connect the dots)
3. Point to WHERE on the resume (use location_hint)
4. Suggest HOW to fix (specific actionable steps)

Be concise. Focus on the most relevant issue(s)."""
        
        return message
    
    def _parse_llm_response(self, content: str) -> Dict[str, Any]:
        """Parse LLM response into structured format"""
        
        # Simple parsing - split by headers
        explanation = ""
        location = ""
        recommendations = []
        
        lines = content.split('\n')
        current_section = None
        
        for line in lines:
            line_lower = line.lower().strip()
            
            if 'why this happened' in line_lower or 'explanation' in line_lower:
                current_section = 'explanation'
                continue
            elif 'where to look' in line_lower or 'location' in line_lower:
                current_section = 'location'
                continue
            elif 'how to fix' in line_lower or 'recommendations' in line_lower or 'fixes' in line_lower:
                current_section = 'recommendations'
                continue
            
            # Add content to appropriate section
            if current_section == 'explanation' and line.strip():
                explanation += line + "\n"
            elif current_section == 'location' and line.strip():
                location += line + "\n"
            elif current_section == 'recommendations' and line.strip():
                # Extract numbered items or bullets
                cleaned = line.strip().lstrip('1234567890.-*• ')
                if cleaned:
                    recommendations.append(cleaned)
        
        return {
            "explanation": explanation.strip() or content,  # Fallback to full content
            "location": location.strip(),
            "recommendations": recommendations
        }


def prepare_diagnostic_data(
    parsed_data: Dict[str, Any],
    blocks: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Prepare structured data for LLM explanation.
    Uses rule-based detection to find issues, then provides context for LLM to explain.
    """
    from .ats_issues import ATSIssueDetector
    
    # 1. Run business rules to detect issues (DEFINITIVE)
    detector = ATSIssueDetector()
    issues = detector.detect_all_issues(blocks, parsed_data)
    
    # Convert to dict for JSON serialization
    issues_dicts = [issue.to_dict() for issue in issues]
    
    # 2. Create condensed block summaries (for context only)
    # Only include blocks relevant to detected issues
    relevant_block_indices = set()
    for issue in issues:
        relevant_block_indices.update(issue.block_indices)
    
    block_summaries = []
    for idx in list(relevant_block_indices)[:30]:  # Limit to 30
        if idx < len(blocks):
            block = blocks[idx]
            block_summaries.append({
                "index": idx,
                "text_preview": block.get('text', '')[:80],
                "page": block.get('page', 1),
                "region": block.get('region', 'body'),
                "in_table": block.get('in_table', False),
                "column": block.get('column', 1)
            })
    
    return {
        'ats_extracted': parsed_data,
        'detected_issues': issues_dicts,  # Structured issues from business rules
        'block_summaries': block_summaries  # Context blocks
    }

