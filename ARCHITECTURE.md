# Resume Tool - Architecture Documentation

## System Overview

The Resume Tool is a full-stack application that analyzes resumes for ATS (Applicant Tracking System) compatibility, matches candidates to job roles, and provides personalized skill suggestions.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                             │
│                  (Next.js + Tailwind CSS)                    │
│  - Drag-and-drop upload                                      │
│  - Side-by-side PDF viewer                                   │
│  - Real-time score display                                   │
│  - Role matching UI                                          │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/REST API
                     ↓
┌─────────────────────────────────────────────────────────────┐
│                      Backend API                             │
│                      (FastAPI)                               │
│  Routes:                                                     │
│  - POST /api/parse         Parse resume                     │
│  - POST /api/score         Calculate ATS score              │
│  - GET  /api/roles         Get role matches                 │
│  - POST /api/suggest       Get skill suggestions            │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        ↓            ↓            ↓
   ┌─────────┐  ┌─────────┐  ┌──────────┐
   │PostgreSQL│  │  Redis  │  │  Celery  │
   │         │  │         │  │  Worker  │
   │ Resumes │  │ Queue   │  │          │
   │ Users   │  │ Cache   │  │ Async    │
   │ Matches │  │         │  │ Tasks    │
   └─────────┘  └─────────┘  └──────────┘
                                    │
                     ┌──────────────┴──────────────┐
                     ↓                             ↓
              ┌─────────────┐              ┌─────────────┐
              │ AI/ML Stack │              │   Storage   │
              │             │              │             │
              │ • PyMuPDF   │              │ • Local FS  │
              │ • spaCy     │              │ • AWS S3    │
              │ • Transformers│            │             │
              │ • OpenAI    │              │             │
              └─────────────┘              └─────────────┘
```

## Technology Stack

### Frontend

- **Framework**: Next.js 14 (React 18)
- **Styling**: Tailwind CSS
- **State Management**: React Hooks + Zustand (ready to use)
- **File Upload**: react-dropzone
- **HTTP Client**: Axios
- **UI Icons**: lucide-react

### Backend

- **Framework**: FastAPI (Python 3.11+)
- **ASGI Server**: Uvicorn
- **ORM**: SQLAlchemy
- **Migrations**: Alembic
- **Task Queue**: Celery + Redis
- **Validation**: Pydantic v2

### Database & Storage

- **Primary Database**: PostgreSQL 15
- **Cache/Queue**: Redis 7
- **File Storage**: Local filesystem (dev) / S3 (production)

### AI/ML Stack

- **PDF Parsing**: PyMuPDF (fitz)
- **DOCX Parsing**: python-docx
- **OCR (optional)**: Tesseract + pytesseract
- **NLP**: spaCy (en_core_web_lg)
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **LLM**: OpenAI GPT-3.5 Turbo (with fallback)

## Component Details

### 1. Resume Parser (`backend/app/services/parser.py`)

**Purpose**: Extract structured data from PDF and DOCX resumes.

**Process**:
1. Extract raw text using PyMuPDF or python-docx
2. Use spaCy for NLP processing
3. Identify sections (Experience, Education, Skills, etc.)
4. Extract entities (name, email, phone, etc.)
5. Return structured JSON

**Key Methods**:
- `parse()`: Main entry point
- `_extract_pdf_text()`: PDF text extraction
- `_extract_docx_text()`: DOCX text extraction
- `_extract_structured_data()`: NLP-based parsing

### 2. ATS Scorer (`backend/app/services/scorer.py`)

**Purpose**: Calculate ATS compatibility score.

**Scoring Metrics** (0-100 scale):
- **Formatting** (25%): Checks for ATS-friendly formatting
- **Keywords** (25%): Presence of relevant skills and keywords
- **Structure** (30%): Proper section organization
- **Readability** (20%): Text clarity and length

**Process**:
1. Analyze resume formatting (no images, simple tables)
2. Check for essential sections and contact info
3. Evaluate keyword density
4. Generate ATS plain-text view
5. Identify issues and create suggestions

### 3. Role Matcher (`backend/app/services/role_matcher.py`)

**Purpose**: Match resumes to job roles using semantic similarity.

**Process**:
1. Create resume embedding using sentence-transformers
2. Compare against pre-computed role embeddings
3. Calculate cosine similarity scores
4. Analyze skill overlap (required vs preferred)
5. Rank roles by match score

**Matching Algorithm**:
```python
final_score = (semantic_similarity * 0.6) + (skill_match * 0.4)
```

**Built-in Roles**:
- Full Stack Developer
- Data Scientist
- DevOps Engineer
- Frontend Developer
- Backend Developer
- Machine Learning Engineer
- Product Manager
- UI/UX Designer
- Security Engineer
- Mobile Developer

### 4. Skill Suggester (`backend/app/services/skill_suggester.py`)

**Purpose**: Provide personalized skill recommendations.

**Modes**:
1. **OpenAI Mode**: Uses GPT-3.5 for intelligent suggestions
2. **Fallback Mode**: Uses rule-based skill database

**Process**:
1. Identify current skills from resume
2. Compare with target role requirements
3. Generate suggestions with importance levels:
   - **Critical**: Must-have skills
   - **Recommended**: Strongly suggested
   - **Nice-to-have**: Bonus skills
4. Provide learning resources

### 5. Celery Workers

**Purpose**: Handle long-running tasks asynchronously.

**Tasks**:
- `parse_resume_task`: Parse uploaded resume
- `score_resume_task`: Calculate ATS score
- `match_roles_task`: Find role matches

**Benefits**:
- Non-blocking API responses
- Better user experience
- Scalable processing

## Data Models

### User
```python
- id: Integer (PK)
- email: String (unique)
- hashed_password: String (nullable)
- name: String
- created_at: DateTime
- resumes: Relationship
```

### Resume
```python
- id: Integer (PK)
- user_id: Integer (FK)
- filename: String
- file_path: String
- file_type: String (pdf/docx)
- parsed_data: JSON
- ats_text: Text
- ats_score: Float
- score_details: JSON
- created_at: DateTime
```

### RoleMatch
```python
- id: Integer (PK)
- resume_id: Integer (FK)
- role_title: String
- match_score: Float
- matched_skills: JSON
- missing_skills: JSON
- suggestions: JSON
```

### JobRole
```python
- id: Integer (PK)
- title: String
- description: Text
- required_skills: JSON
- preferred_skills: JSON
- category: String
- seniority_level: String
- embedding: JSON
```

## API Endpoints

### POST /api/parse
Upload and parse a resume.

**Request**: `multipart/form-data` with file
**Response**: Resume ID and upload confirmation

### GET /api/resume/{id}/parsed
Get parsed resume data.

**Response**: Structured resume data (JSON)

### POST /api/score/{id}
Calculate ATS score for a resume.

**Response**: Score breakdown and suggestions

### GET /api/roles/{id}
Get role matches for a resume.

**Query Params**: `top_k` (default: 5)
**Response**: Ranked list of matching roles

### POST /api/suggest
Get skill suggestions for a target role.

**Request**: `{ resume_id, target_role }`
**Response**: Categorized skill suggestions

## Frontend Components

### FileUpload
- Drag-and-drop interface
- File validation (PDF, DOCX)
- Upload progress tracking
- Error handling

### ResumeViewer
- Side-by-side comparison
- Original format vs ATS view
- Issue highlighting
- Responsive design

### ScoreCard
- Overall ATS score display
- Metric breakdown (4 categories)
- Visual progress bars
- Actionable recommendations

### RoleMatches
- Expandable role cards
- Match percentage display
- Skill comparison (matched/missing)
- Role-specific suggestions

### SkillSuggestions
- Categorized by importance
- Learning resources
- Current skills overview
- Next steps guidance

## Security Considerations

1. **File Upload**:
   - File type validation
   - Size limits (10MB)
   - Virus scanning (TODO)

2. **API Security**:
   - JWT authentication (ready)
   - CORS configuration
   - Rate limiting (TODO)

3. **Data Privacy**:
   - User data isolation
   - Secure file storage
   - No PII in logs

## Scalability

### Current Scale
- Single server deployment
- Suitable for 100s of concurrent users

### Scale-up Options
1. **Horizontal Scaling**:
   - Multiple backend instances behind load balancer
   - Separate Celery workers
   
2. **Database Optimization**:
   - Read replicas
   - Connection pooling
   - Caching layer

3. **File Storage**:
   - Move to S3/CloudFront
   - CDN for static assets

4. **ML Model Optimization**:
   - GPU-accelerated inference
   - Model quantization
   - Batch processing

## Performance Metrics

### Target Performance
- Resume parsing: < 5 seconds
- ATS scoring: < 2 seconds
- Role matching: < 3 seconds
- Skill suggestions: < 5 seconds (with OpenAI)

### Optimization Strategies
1. Caching parsed resumes
2. Pre-computing role embeddings
3. Async task processing
4. Database indexing
5. Frontend code splitting

## Future Enhancements

1. **Advanced Features**:
   - Resume builder/editor
   - Cover letter generator
   - Interview preparation
   - Job board integration

2. **ML Improvements**:
   - Fine-tuned models for resume parsing
   - Custom embeddings for domain-specific roles
   - Predictive hiring success metrics

3. **Analytics**:
   - User dashboard with trends
   - Industry benchmarking
   - Success tracking

4. **Integrations**:
   - LinkedIn import
   - ATS system direct integration
   - Calendar for interview scheduling

## Monitoring & Logging

### Application Logs
- FastAPI request/response logs
- Celery task logs
- Error tracking with Sentry (TODO)

### Metrics
- API response times
- Task queue lengths
- Database query performance
- ML model inference time

### Health Checks
- `/health` endpoint
- Database connectivity
- Redis connectivity
- Celery worker status

## Development Workflow

1. **Local Development**: Docker Compose
2. **Code Quality**: Black, Flake8, ESLint
3. **Testing**: pytest (backend), Jest (frontend)
4. **CI/CD**: GitHub Actions (TODO)
5. **Deployment**: Docker containers

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [spaCy Documentation](https://spacy.io/usage)
- [sentence-transformers](https://www.sbert.net/)
- [Celery Documentation](https://docs.celeryproject.org/)

