from sentence_transformers import SentenceTransformer
from typing import Dict, Any, List
import numpy as np


class RoleMatcher:
    def __init__(self):
        # Load sentence transformer model for semantic matching
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Sample job roles database (in production, this would come from DB)
        self.job_roles = [
            {
                "title": "Full Stack Developer",
                "description": "Develop and maintain web applications using frontend and backend technologies",
                "required_skills": ["JavaScript", "React", "Node.js", "Python", "SQL", "Git"],
                "preferred_skills": ["TypeScript", "Docker", "AWS", "GraphQL"],
                "category": "Software Development"
            },
            {
                "title": "Data Scientist",
                "description": "Analyze data, build ML models, and derive insights from large datasets",
                "required_skills": ["Python", "Machine Learning", "Statistics", "SQL", "Pandas", "NumPy"],
                "preferred_skills": ["TensorFlow", "PyTorch", "Deep Learning", "Spark", "R"],
                "category": "Data Science"
            },
            {
                "title": "DevOps Engineer",
                "description": "Automate infrastructure, manage CI/CD pipelines, and ensure system reliability",
                "required_skills": ["Docker", "Kubernetes", "CI/CD", "Linux", "Cloud (AWS/GCP)", "Python"],
                "preferred_skills": ["Terraform", "Ansible", "Monitoring", "Security"],
                "category": "Infrastructure"
            },
            {
                "title": "Frontend Developer",
                "description": "Build responsive user interfaces and web applications",
                "required_skills": ["JavaScript", "React", "HTML", "CSS", "TypeScript"],
                "preferred_skills": ["Next.js", "Vue.js", "Tailwind CSS", "Webpack"],
                "category": "Software Development"
            },
            {
                "title": "Backend Developer",
                "description": "Design and implement server-side logic and APIs",
                "required_skills": ["Python", "Node.js", "SQL", "REST API", "Git"],
                "preferred_skills": ["GraphQL", "Redis", "PostgreSQL", "MongoDB", "Microservices"],
                "category": "Software Development"
            },
            {
                "title": "Machine Learning Engineer",
                "description": "Deploy and scale machine learning models in production",
                "required_skills": ["Python", "Machine Learning", "TensorFlow", "PyTorch", "Docker"],
                "preferred_skills": ["Kubernetes", "MLOps", "AWS SageMaker", "Spark"],
                "category": "Data Science"
            },
            {
                "title": "Product Manager",
                "description": "Define product strategy and work with cross-functional teams",
                "required_skills": ["Product Strategy", "Agile", "User Research", "Analytics"],
                "preferred_skills": ["SQL", "A/B Testing", "Wireframing", "Technical Background"],
                "category": "Product"
            },
            {
                "title": "UI/UX Designer",
                "description": "Design user interfaces and user experiences for digital products",
                "required_skills": ["Figma", "User Research", "Wireframing", "Prototyping"],
                "preferred_skills": ["Adobe XD", "Sketch", "HTML/CSS", "Motion Design"],
                "category": "Design"
            },
            {
                "title": "Security Engineer",
                "description": "Secure infrastructure and applications from threats",
                "required_skills": ["Security", "Penetration Testing", "Network Security", "Linux"],
                "preferred_skills": ["Cloud Security", "SIEM", "Python", "Incident Response"],
                "category": "Security"
            },
            {
                "title": "Mobile Developer",
                "description": "Build native or cross-platform mobile applications",
                "required_skills": ["React Native", "iOS", "Android", "JavaScript"],
                "preferred_skills": ["Swift", "Kotlin", "Flutter", "Mobile UI/UX"],
                "category": "Software Development"
            }
        ]
        
        # Pre-compute embeddings for job roles
        self._compute_role_embeddings()
    
    def _compute_role_embeddings(self):
        """Compute embeddings for all job roles"""
        for role in self.job_roles:
            # Combine title, description, and skills for embedding
            role_text = f"{role['title']}. {role['description']}. Skills: {', '.join(role['required_skills'])}"
            role["embedding"] = self.model.encode(role_text)
    
    def match_roles(self, parsed_data: Dict[str, Any], top_k: int = 5) -> List[Dict[str, Any]]:
        """Match resume to job roles using semantic similarity"""
        
        # Create resume representation
        resume_text = self._create_resume_text(parsed_data)
        resume_embedding = self.model.encode(resume_text)
        
        # Calculate similarity scores
        matches = []
        for role in self.job_roles:
            similarity = self._cosine_similarity(resume_embedding, role["embedding"])
            
            # Analyze skill match
            resume_skills = set([s.lower() for s in parsed_data.get("skills", [])])
            required_skills = set([s.lower() for s in role["required_skills"]])
            preferred_skills = set([s.lower() for s in role.get("preferred_skills", [])])
            
            matched_skills = resume_skills.intersection(required_skills.union(preferred_skills))
            missing_required = required_skills - resume_skills
            missing_preferred = preferred_skills - resume_skills
            
            # Calculate final score (combination of semantic similarity and skill match)
            skill_match_score = len(matched_skills) / len(required_skills.union(preferred_skills))
            final_score = (similarity * 0.6) + (skill_match_score * 0.4)
            
            matches.append({
                "role_title": role["title"],
                "role_description": role["description"],
                "match_score": float(final_score * 100),  # Convert to percentage
                "matched_skills": sorted(list(matched_skills)),
                "missing_skills": sorted(list(missing_required)),
                "suggestions": self._generate_role_suggestions(
                    role, matched_skills, missing_required, missing_preferred
                )
            })
        
        # Sort by match score and return top k
        matches.sort(key=lambda x: x["match_score"], reverse=True)
        return matches[:top_k]
    
    def _create_resume_text(self, parsed_data: Dict[str, Any]) -> str:
        """Create text representation of resume for embedding"""
        parts = []
        
        if parsed_data.get("summary"):
            parts.append(parsed_data["summary"])
        
        if parsed_data.get("skills"):
            parts.append("Skills: " + ", ".join(parsed_data["skills"]))
        
        if parsed_data.get("experience"):
            for exp in parsed_data["experience"]:
                parts.append(exp.get("title", ""))
                parts.append(exp.get("description", ""))
        
        return " ".join(parts)
    
    def _cosine_similarity(self, vec1, vec2):
        """Calculate cosine similarity between two vectors"""
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    
    def _generate_role_suggestions(
        self,
        role: Dict[str, Any],
        matched_skills: set,
        missing_required: set,
        missing_preferred: set
    ) -> List[str]:
        """Generate suggestions for improving match with role"""
        suggestions = []
        
        if missing_required:
            suggestions.append(
                f"Learn these critical skills: {', '.join(sorted(list(missing_required))[:3])}"
            )
        
        if missing_preferred:
            suggestions.append(
                f"Consider adding: {', '.join(sorted(list(missing_preferred))[:3])}"
            )
        
        if len(matched_skills) > 0:
            suggestions.append(
                f"Highlight your experience with: {', '.join(sorted(list(matched_skills))[:3])}"
            )
        
        suggestions.append(
            f"Tailor your resume to emphasize {role['category']} experience"
        )
        
        return suggestions[:3]

