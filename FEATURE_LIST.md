# ATS Resume Tool - Complete Feature List & Page Structure

## 📄 Overview

This document provides a comprehensive breakdown of all features, pages, and functionality in the ATS Resume Tool.

---

## 🏠 Main Application Structure

### **Landing Page / Upload Page**
**Route:** `/` (root)

**Features:**
- Drag-and-drop file upload interface
- Supports PDF and DOCX files
- File validation (type, size)
- Upload progress indicators
- Automatic parsing trigger after upload
- Navigation to analysis view after successful upload

**Components:**
- `FileUpload.tsx` - Main upload interface

---

## 📊 Analysis Dashboard

### **Navigation Structure**

After uploading a resume, users access the analysis dashboard with:

1. **Left Sidebar** - Main navigation (sticky)
2. **Center Content Area** - View-specific content
3. **Right Panel** - AI Assistant (collapsible overlay)

---

## 📑 Sidebar Navigation Pages

### **1. Overview** 📋
**Icon:** Eye  
**Default View:** Yes

**Purpose:** Combined view showing resume comparison and format issues

**Sub-sections:**

#### A. **Resume Comparison** (Top Section)
**Component:** `ResumeComparison.tsx`

**Features:**
- **Side-by-Side View:**
  - Left: Original resume (PDF viewer)
  - Right: ATS plain-text view (what ATS systems see)
  
- **Extraction Status View:**
  - Color-coded field status:
    - 🟢 **Green** - Field found and extracted correctly
    - 🟡 **Yellow** - Field partially extracted
    - 🔴 **Red** - Field missing or not extracted
  
- **Tracked Fields:**
  - Name (weight: 1.5)
  - Email (weight: 1.5)
  - Phone (weight: 1.0)
  - LinkedIn (weight: 0.5)
  - Location (weight: 0.5)
  - Skills (weight: 1.5)
  - Experience (weight: 2.0)
  - Education (weight: 1.0)

- **Extraction Score:**
  - Weighted percentage score (0-100%)
  - Shows overall ATS parsing success rate
  - Calculated based on field importance weights

#### B. **Format Issues & Highlights** (Bottom Section)
**Components:** `PDFHighlightViewer.tsx`, `IssueSummaryPanel.tsx`

**Features:**
- **PDF Viewer with Color-Coded Highlights:**
  - Red highlights: Critical issues
  - Orange highlights: High severity issues
  - Yellow highlights: Medium severity issues
  - Blue highlights: Low severity issues
  - Interactive tooltips on hover showing issue details

- **Issue Summary Panel:**
  - Issue count by severity (Critical/High/Medium/Low)
  - List of detected issues with descriptions
  - Visual status indicators

**Issues Detected:**
- Multi-column layout
- Tables/grids detected
- Images detected
- Headers/footers with content
- Scanned/image-based PDFs
- Contact info in headers/footers
- Skills section issues
- Experience section issues
- Education section issues
- Date format issues
- Uncommon fonts
- Unmapped content
- Layout complexity

---

### **2. Quick Fixes** ⚡
**Icon:** Zap  
**Badge:** Shows count of issues

**Purpose:** Fast, rule-based recommendations (Tier 1)

**Component:** `QuickRecommendations.tsx`

**Features:**
- **Immediate Recommendations:**
  - Generated instantly using rule-based logic
  - No AI/LLM calls required
  - Generic but actionable suggestions
  
- **Recommendation Categories:**
  - Format fixes (multi-column, tables, images)
  - Contact info fixes (header/footer issues)
  - Section structure fixes (skills, experience, education)
  - Date format corrections
  - Font recommendations
  - Layout simplification

- **Display:**
  - Success message if no issues found
  - List of actionable recommendations with icons
  - Organized by severity/priority

---

### **3. Role Matches** 💼
**Icon:** Briefcase  
**Badge:** Shows number of matches

**Purpose:** Semantic similarity matching to job roles

**Component:** `RoleMatches.tsx`

**Features:**
- **Role Matching Algorithm:**
  - Uses sentence-transformers for semantic similarity
  - Compares resume content to pre-configured job role descriptions
  - Returns top 5 matches with match scores

- **Match Display:**
  - Match percentage (0-100%)
  - Role name and description
  - Expandable cards showing:
    - Skill gaps analysis
    - Required vs. present skills
    - Role-specific recommendations

- **Pre-configured Roles:**
  - Software Engineer
  - Data Scientist
  - Product Manager
  - UX Designer
  - Marketing Manager
  - Sales Representative
  - Project Manager
  - Business Analyst
  - DevOps Engineer
  - Full Stack Developer
  - (Extensible list)

---

## 🤖 AI Assistant Panel (Right Side)

**Component:** `ATSDiagnostic.tsx`

**Position:** Fixed right-side overlay (collapsible)

**Purpose:** Detailed, contextual AI-powered diagnostics (Tier 2)

**Features:**
- **Always Available:**
  - Overlays content (doesn't push layout)
  - Collapsible/expandable toggle button
  - Persistent across all views

- **Interactive Query Interface:**
  - Textarea for user prompts
  - Example prompts provided:
    - "I'm missing 5 skills that are on my resume"
    - "My email address isn't showing up"
    - "Only 2 of my 4 jobs were extracted"
    - "My education section is completely missing"

- **AI Diagnostic Process:**
  1. User enters observation/query
  2. System combines:
     - User prompt
     - ATS extracted data
     - Rule-based detected issues
     - Layout diagnostics
     - Block summaries (context)
  3. OpenAI GPT model analyzes and returns:
     - **Explanation:** Why the issue occurred
     - **Location:** Where on the resume (descriptive)
     - **Recommendations:** Step-by-step fix instructions

- **Response Display:**
  - Detailed explanation with formatting
  - Location hints
  - Numbered recommendation list
  - Error handling for API issues

**Backend API:** `POST /api/llm-diagnostic`

---

## 🔍 Detected Issues Reference

### **Formatting Issues**

1. **Multi-column Layout**
   - Severity: Low/Medium/High (based on secondary column ratio)
   - Detection: X-position clustering, secondary column ratio calculation
   - Recommendation: Convert to single-column layout

2. **Tables/Grids**
   - Severity: Medium
   - Detection: PyMuPDF table detection, block clustering
   - Recommendation: Replace tables with simple text formatting

3. **Images/Graphics**
   - Severity: High
   - Detection: Image count per page
   - Recommendation: Remove images, use text-only formatting

4. **Headers/Footers with Content**
   - Severity: Medium
   - Detection: Multi-page repetition check, margin analysis
   - Recommendation: Move content to main body

5. **Scanned/Image-based PDF**
   - Severity: Critical
   - Detection: Low text character count vs. image count
   - Recommendation: Export as text-based PDF

6. **Complex Layout**
   - Severity: Critical/High/Medium (based on complexity score)
   - Factors: Font count, images, tables, multi-column, headers/footers
   - Recommendation: Simplify layout

7. **Uncommon Fonts**
   - Severity: Medium
   - Detection: Font name cleaning and comparison against standard fonts
   - Recommendation: Use ATS-friendly fonts (Arial, Calibri, Times New Roman, etc.)

### **Contact Information Issues**

8. **Email in Header/Footer**
   - Severity: Critical
   - Detection: Email found in text but not extracted, location in header/footer
   - Recommendation: Move email to main body under name

9. **Phone in Header/Footer**
   - Severity: High
   - Detection: Phone found in text but not extracted, location in header/footer
   - Recommendation: Use standard format in main body

10. **LinkedIn Not Extracted**
    - Severity: Medium
    - Detection: LinkedIn URL pattern found but not extracted
    - Recommendation: Write full URL as text (not icon only)

### **Skills Section Issues**

11. **No Skills Section**
    - Severity: High
    - Detection: 0 skills extracted, no skills section header found
    - Recommendation: Add dedicated Skills section with clear header

12. **Skills Section Unreadable**
    - Severity: Critical
    - Detection: Skills section exists but 0 skills extracted
    - Likely causes: Table format, multi-column, icons
    - Recommendation: Use simple bullet points in main body

13. **Skills Partially Extracted**
    - Severity: High
    - Detection: Fewer skills extracted than expected
    - Recommendation: Check formatting issues in skills section

### **Experience Section Issues**

14. **Experience Not Extracted**
    - Severity: Critical
    - Detection: 0 jobs extracted despite experience section
    - Recommendation: Use simple format with job title, company, dates, bullet points

15. **Missing Bullet Points**
    - Severity: High
    - Detection: Jobs extracted but missing descriptions
    - Recommendation: Use standard bullet points (•, -, *)

16. **Incomplete Job Information**
    - Severity: High
    - Detection: Jobs missing title or company
    - Recommendation: Ensure each job has title, company, dates

### **Education Section Issues**

17. **Education Not Extracted**
    - Severity: High
    - Detection: 0 education entries extracted
    - Recommendation: Use clear format with degree, institution, dates

### **Date Format Issues**

18. **Incorrect Date Formats**
    - Severity: Medium
    - Detection: Regex patterns for problematic formats
    - Invalid formats: Jan '21, 2021-2023 (missing months), 1/2021 (single digit month)
    - Valid formats: Jan 2021 – Mar 2023, January 2021 – March 2023, 01/2021 – 03/2023
    - Recommendation: Use full month names or MM/YYYY format

### **Content Issues**

19. **Unmapped Content**
    - Severity: Low/Medium
    - Detection: Text blocks not mapped to any resume section
    - Shows content snippet in issue details
    - Recommendation: Review unmapped content, ensure it's in appropriate section

---

## 🔧 Backend API Endpoints

### **Resume Management**

1. **POST `/api/parse`**
   - Upload and parse resume
   - Returns: `resume_id`, file metadata
   - Triggers background parsing task

2. **GET `/api/resume/{resume_id}/parsed`**
   - Get parsed resume data
   - Returns: Structured data, ATS view, diagnostics

3. **GET `/api/resume/{resume_id}/file`**
   - Get original resume file
   - Returns: PDF/DOCX file for viewing

4. **GET `/api/resumes`**
   - List all resumes (for future user accounts)

5. **GET `/api/resume/{resume_id}/summary`**
   - Get resume summary/overview

### **Analysis & Scoring**

6. **POST `/api/score/{resume_id}`**
   - Calculate ATS compatibility score
   - Returns: Scores, issues, recommendations, highlights
   - Triggers issue detection

7. **GET `/api/roles/{resume_id}`**
   - Get role matches for resume
   - Returns: Top 5 role matches with scores

### **Advanced Features**

8. **POST `/api/analyze-section`**
   - Analyze specific resume section
   - Returns: Section-specific analysis

9. **POST `/api/llm-diagnostic`**
   - AI-powered diagnostic explanation
   - Takes: User prompt, resume_id
   - Returns: Explanation, location, recommendations

### **System Info**

10. **GET `/api/parser/info`**
    - Get parser configuration info
    - Returns: Active parser (Affinda/spaCy), availability

---

## 📊 Metrics & Scoring System

### **Complexity Metrics**
- **Score:** 0-100 (higher = more complex/risky)
- **Labels:** Simple / Moderate / Complex / Very Complex
- **Factors:**
  - Font count penalty
  - Images penalty
  - Tables penalty
  - Multi-column layout penalty (proportional to secondary column ratio)
  - Headers/footers penalty

### **Extraction Score**
- **Score:** 0-100% (weighted)
- **Calculation:** Field-level extraction status × field weight
- **Field Weights:**
  - Experience: 2.0 (most important)
  - Name: 1.5
  - Email: 1.5
  - Skills: 1.5
  - Phone: 1.0
  - Education: 1.0
  - LinkedIn: 0.5
  - Location: 0.5

### **ATS Compatibility Score** (Currently Hidden/Redesigned)
- **Components:**
  - Formatting (25%)
  - Keywords (25%)
  - Structure (30%)
  - Readability (20%)

---

## 🎨 UI Components Reference

### **Core Components**

1. **FileUpload.tsx** - Drag-and-drop file upload
2. **ResumeViewer.tsx** - Resume data display (structured view)
3. **ResumeComparison.tsx** - Side-by-side original vs. ATS view
4. **PDFHighlightViewer.tsx** - PDF viewer with color-coded highlights
5. **IssueSummaryPanel.tsx** - Issue summary and breakdown
6. **QuickRecommendations.tsx** - Tier 1 quick fixes
7. **RoleMatches.tsx** - Job role matching display
8. **ATSDiagnostic.tsx** - AI assistant panel
9. **ScoreCard.tsx** - Score display (currently hidden/redesigned)

### **Helper Components**

10. **SectionSummary.tsx** - Section-specific summary display
11. **SkillSuggestions.tsx** - Skill suggestions (currently disabled)

---

## 🏗️ Technical Architecture

### **Hybrid Parser System**

1. **Affinda API** (Primary)
   - Commercial-grade structured data extraction
   - High accuracy parsing
   - Returns structured JSON

2. **PyMuPDF** (Always Used)
   - ATS plain-text view generation
   - Layout diagnostics
   - Block extraction with metadata
   - Column detection
   - Font analysis

3. **spaCy** (Fallback)
   - Open-source NLP parsing
   - Free alternative
   - Used when Affinda unavailable

### **Issue Detection System**

- **Rule-Based** (Tier 1)
  - Fast, deterministic
  - Business logic in `ats_issue_detector.py`
  - Structured `ATSIssue` dataclass
  - No AI/LLM required

- **AI-Powered** (Tier 2)
  - Contextual explanations
  - OpenAI GPT integration
  - User-prompted analysis
  - Specific location hints

### **Data Models**

- **ATSIssue** - Structured issue representation
  - `code`, `severity`, `section`, `message`, `details`, `page`, `bbox`, `location_hint`

- **ComplexityMetric** - Layout complexity scoring
- **ContentCoverageMetric** - Field extraction status
- **StructureMetric** - Resume structure evaluation

---

## 🔮 Disabled Features (Future Development)

### **Skill Suggestions**
- Currently commented out
- Ready for re-enablement
- Files: `skill_suggester.py`, `SkillSuggestions.tsx`
- API endpoint: `POST /api/suggest` (disabled)

---

## 📱 User Flow

1. **Upload Resume** → Landing page with file upload
2. **Automatic Parsing** → Background task processes resume
3. **Analysis Dashboard** → Navigate to Overview tab
4. **Review Issues** → See color-coded PDF highlights
5. **Check Extraction** → Compare original vs. ATS view
6. **Quick Fixes** → Review immediate recommendations
7. **Role Matches** → See job compatibility scores
8. **AI Diagnostic** → Ask specific questions about issues
9. **Fix Resume** → Apply recommendations
10. **Re-upload** → Iterate and improve

---

## 🎯 Key Differentiators

1. **Visual ATS View** - Shows exactly what ATS systems see
2. **Hybrid Parser** - Combines commercial accuracy with open-source diagnostics
3. **Differential Analysis** - Compares visual detection vs. ATS extraction
4. **Color-Coded Highlights** - Visual issue location on PDF
5. **Two-Tier Recommendations** - Fast rules + AI explanations
6. **Weighted Extraction Score** - Reflects field importance
7. **Contextual AI Diagnostics** - User-prompted deep analysis

---

**Last Updated:** Based on current codebase state
**Version:** 1.0

