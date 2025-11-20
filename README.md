# Resume Tool

An AI-powered resume analyzer that provides ATS compatibility scoring, role matching, and skill suggestions.

## Features

- 📄 Resume parsing (PDF & DOCX)
- 🎯 ATS compatibility scoring
- 👀 Side-by-side original vs ATS view
- 🔍 Role matching based on resume content
- 📊 Detailed feedback and recommendations

**Note:** Skill suggestions feature is currently disabled for later development. See code comments marked with `TODO: Re-enable for later development` to restore this feature.

## Architecture

### Frontend
- **Next.js** (React) with **Tailwind CSS**
- Drag-and-drop upload
- Side-by-side PDF viewer
- Real-time feedback display

### Backend
- **FastAPI** (Python) REST API
- **Celery** with **Redis** for async processing
- **PostgreSQL** for data storage
- **S3/Supabase** for file storage

### AI/ML Stack
- **Textkernel** (optional) for commercial-grade resume parsing
- **PyMuPDF** for ATS view generation and layout diagnostics
- **spaCy** for NLP-based parsing (free fallback option)
- **sentence-transformers** for semantic role matching
- **OpenAI API** for intelligent skill suggestions

### Hybrid Parser Architecture ✨
The tool uses a unique hybrid approach:
- **Commercial Parser** (Textkernel) for high-accuracy structured data extraction
- **PyMuPDF** always used for ATS view generation (shows what ATS systems actually see)
- **spaCy** as free fallback option
- See `PARSER_GUIDE.md` for detailed comparison and setup

## Getting Started

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+
- PostgreSQL
- Redis

### Quick Start

```bash
# Clone and setup
git clone <repo-url>
cd resume_tool

# Start with Docker Compose
docker-compose up -d

# Frontend will be available at http://localhost:3000
# Backend API at http://localhost:8000
```

### Local Development

#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

## API Endpoints

- `POST /api/parse` - Parse resume and extract data
- `GET /api/resume/{id}/parsed` - Get parsed resume data
- `POST /api/score/{id}` - Calculate ATS compatibility score
- `GET /api/roles/{id}` - Get role matches for resume
- ~~`POST /api/suggest`~~ - (Disabled for now) Get skill suggestions for target role
- `GET /api/parser/info` - Check which parser is active and configured

**New:** Check parser status at http://localhost:8000/api/parser/info to see if you're using Textkernel or spaCy.

## Environment Variables

See `.env.example` for required configuration.

## License

MIT

