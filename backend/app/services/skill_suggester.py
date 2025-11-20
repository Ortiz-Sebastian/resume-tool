from typing import Dict, Any, List
import os
from openai import OpenAI


class SkillSuggester:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        self.use_openai = bool(api_key)
        
        if self.use_openai:
            self.client = OpenAI(api_key=api_key)
        
        # Fallback skill database (used when OpenAI is not available)
        self.skill_database = {
            "Full Stack Developer": {
                "critical": ["JavaScript", "React", "Node.js", "SQL", "Git", "RESTful APIs"],
                "recommended": ["TypeScript", "Docker", "GraphQL", "Testing", "CI/CD"],
                "nice_to_have": ["Next.js", "AWS", "Redis", "MongoDB", "Microservices"]
            },
            "Data Scientist": {
                "critical": ["Python", "Machine Learning", "Statistics", "SQL", "Pandas"],
                "recommended": ["TensorFlow", "PyTorch", "Data Visualization", "Jupyter"],
                "nice_to_have": ["Spark", "Deep Learning", "NLP", "R", "AWS"]
            },
            "DevOps Engineer": {
                "critical": ["Docker", "Kubernetes", "CI/CD", "Linux", "Cloud Platforms"],
                "recommended": ["Terraform", "Ansible", "Monitoring", "Python", "Bash"],
                "nice_to_have": ["AWS/GCP/Azure", "Security", "Helm", "GitOps"]
            },
            "Frontend Developer": {
                "critical": ["JavaScript", "React", "HTML", "CSS", "TypeScript"],
                "recommended": ["Next.js", "Tailwind CSS", "Responsive Design", "Git"],
                "nice_to_have": ["Vue.js", "Testing", "Webpack", "Performance Optimization"]
            },
            "Backend Developer": {
                "critical": ["Python", "Node.js", "SQL", "REST APIs", "Git"],
                "recommended": ["PostgreSQL", "Redis", "Authentication", "Microservices"],
                "nice_to_have": ["GraphQL", "Docker", "Message Queues", "Caching"]
            },
            "Machine Learning Engineer": {
                "critical": ["Python", "Machine Learning", "TensorFlow/PyTorch", "Docker"],
                "recommended": ["MLOps", "Kubernetes", "Model Deployment", "Data Engineering"],
                "nice_to_have": ["AWS SageMaker", "Spark", "Feature Engineering", "A/B Testing"]
            }
        }
    
    def suggest_skills(
        self,
        parsed_data: Dict[str, Any],
        target_role: str
    ) -> Dict[str, Any]:
        """Generate skill suggestions for a target role"""
        
        current_skills = [s.lower() for s in parsed_data.get("skills", [])]
        
        if self.use_openai:
            suggestions = self._get_openai_suggestions(parsed_data, target_role, current_skills)
        else:
            suggestions = self._get_fallback_suggestions(target_role, current_skills)
        
        return {
            "target_role": target_role,
            "current_skills": parsed_data.get("skills", []),
            "suggested_skills": suggestions
        }
    
    def _get_openai_suggestions(
        self,
        parsed_data: Dict[str, Any],
        target_role: str,
        current_skills: List[str]
    ) -> List[Dict[str, Any]]:
        """Get skill suggestions using OpenAI"""
        
        prompt = f"""You are a career advisor. Analyze this resume for a {target_role} position.

Current Skills: {', '.join(current_skills)}

Professional Summary: {parsed_data.get('summary', 'Not provided')}

Provide 5-7 skill suggestions to improve their candidacy for {target_role}. For each skill:
1. Name of the skill
2. Importance level (critical/recommended/nice-to-have)
3. Brief reason why it's important (1 sentence)
4. One learning resource URL (if applicable)

Format your response as JSON array with objects containing: skill, importance, reason, learning_resource
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful career advisor specializing in tech careers."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            # Parse the response
            import json
            content = response.choices[0].message.content
            
            # Try to extract JSON from the response
            try:
                # Find JSON array in response
                start_idx = content.find('[')
                end_idx = content.rfind(']') + 1
                if start_idx != -1 and end_idx != 0:
                    json_str = content[start_idx:end_idx]
                    suggestions = json.loads(json_str)
                    return suggestions
            except:
                pass
            
            # Fallback if JSON parsing fails
            return self._get_fallback_suggestions(target_role, current_skills)
            
        except Exception as e:
            print(f"OpenAI API error: {str(e)}")
            return self._get_fallback_suggestions(target_role, current_skills)
    
    def _get_fallback_suggestions(
        self,
        target_role: str,
        current_skills: List[str]
    ) -> List[Dict[str, Any]]:
        """Get skill suggestions from built-in database"""
        
        # Find matching role in database
        role_skills = None
        for role_key in self.skill_database.keys():
            if role_key.lower() in target_role.lower() or target_role.lower() in role_key.lower():
                role_skills = self.skill_database[role_key]
                break
        
        if not role_skills:
            # Generic tech skills if role not found
            role_skills = {
                "critical": ["Git", "Problem Solving", "Communication"],
                "recommended": ["Cloud Platforms", "Agile", "Testing"],
                "nice_to_have": ["Docker", "CI/CD", "Security"]
            }
        
        suggestions = []
        
        # Check which skills are missing
        for importance, skills in [
            ("critical", role_skills["critical"]),
            ("recommended", role_skills["recommended"]),
            ("nice_to_have", role_skills["nice_to_have"])
        ]:
            for skill in skills:
                if skill.lower() not in current_skills:
                    suggestions.append({
                        "skill": skill,
                        "importance": importance,
                        "reason": self._get_skill_reason(skill, target_role, importance),
                        "learning_resources": self._get_learning_resources(skill)
                    })
        
        return suggestions[:7]  # Return top 7 suggestions
    
    def _get_skill_reason(self, skill: str, target_role: str, importance: str) -> str:
        """Generate reason for skill suggestion"""
        reasons = {
            "critical": f"{skill} is essential for {target_role} positions and highly sought after by employers.",
            "recommended": f"{skill} will significantly strengthen your {target_role} profile and set you apart.",
            "nice_to_have": f"{skill} is a valuable addition that many {target_role} professionals are learning."
        }
        return reasons.get(importance, f"{skill} is valuable for {target_role} roles.")
    
    def _get_learning_resources(self, skill: str) -> List[str]:
        """Get learning resources for a skill"""
        # Map common skills to learning resources
        resources = {
            "JavaScript": ["https://javascript.info"],
            "Python": ["https://python.org/about/gettingstarted"],
            "React": ["https://react.dev/learn"],
            "Node.js": ["https://nodejs.org/en/learn"],
            "Docker": ["https://docs.docker.com/get-started"],
            "Kubernetes": ["https://kubernetes.io/docs/tutorials"],
            "Machine Learning": ["https://coursera.org/learn/machine-learning"],
            "SQL": ["https://sqlzoo.net"],
            "Git": ["https://git-scm.com/doc"],
            "TypeScript": ["https://typescriptlang.org/docs"],
            "AWS": ["https://aws.amazon.com/training"],
        }
        
        return resources.get(skill, [f"https://www.google.com/search?q=learn+{skill.replace(' ', '+')}"])

