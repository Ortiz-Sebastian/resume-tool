from sqlalchemy import Column, Integer, String, Text, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)
    name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    resumes = relationship("Resume", back_populates="user")


class Resume(Base):
    __tablename__ = "resumes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Made nullable for MVP without auth
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # pdf, docx
    file_size = Column(Integer, nullable=False)
    
    # Parsed data
    parsed_data = Column(JSON, nullable=True)
    ats_text = Column(Text, nullable=True)
    
    # Scores
    ats_score = Column(Float, nullable=True)
    score_details = Column(JSON, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="resumes")
    role_matches = relationship("RoleMatch", back_populates="resume")


class RoleMatch(Base):
    __tablename__ = "role_matches"
    
    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    role_title = Column(String, nullable=False)
    role_description = Column(Text, nullable=True)
    match_score = Column(Float, nullable=False)
    matched_skills = Column(JSON, nullable=True)
    missing_skills = Column(JSON, nullable=True)
    suggestions = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    resume = relationship("Resume", back_populates="role_matches")


class JobRole(Base):
    __tablename__ = "job_roles"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    required_skills = Column(JSON, nullable=False)
    preferred_skills = Column(JSON, nullable=True)
    category = Column(String, nullable=True)
    seniority_level = Column(String, nullable=True)  # junior, mid, senior
    embedding = Column(JSON, nullable=True)  # Store embeddings as JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

