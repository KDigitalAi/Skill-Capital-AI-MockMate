# 🎯 Skill Capital AI MockMate

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-orange.svg)](https://supabase.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--3.5--turbo-purple.svg)](https://openai.com/)

> **An AI-Powered Interview Preparation Platform** - Practice mock interviews with personalized questions, get real-time AI feedback, and track your performance over time.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Installation](#installation)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [Database Schema](#database-schema)
- [Project Structure](#project-structure)
- [Development Guide](#development-guide)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## 🎯 Overview

**Skill Capital AI MockMate** is a full-stack interview preparation platform that uses AI to provide personalized mock interviews. The system analyzes user resumes, generates context-aware interview questions, and provides detailed feedback on answers.

### Key Capabilities

- 📄 **Resume Analysis** - Automatic skill extraction, experience level detection, and keyword extraction
- 🤖 **AI Question Generation** - Context-aware questions based on resume and role using OpenAI GPT models
- 💬 **Real-time Evaluation** - Multi-dimensional scoring with detailed feedback
- 📊 **Performance Analytics** - Track progress with comprehensive dashboards
- 🎤 **Voice Interaction** - Speech-to-text and text-to-speech for technical interviews
- 💻 **Coding Challenges** - Execute and evaluate code submissions with test cases

---

## ✨ Features

### Core Features

- ✅ **FastAPI Backend** - RESTful API with automatic OpenAPI documentation
- ✅ **Unified Frontend/Backend** - FastAPI serves both API and static frontend files
- ✅ **Supabase Integration** - PostgreSQL database with Row Level Security (RLS)
- ✅ **Resume Upload & Parsing** - Support for PDF and DOCX files with OCR fallback
- ✅ **AI-Powered Question Generation** - Context-aware questions using OpenAI GPT models via LangChain
- ✅ **Multiple Interview Modes** - Technical, Coding, HR, and STAR (behavioral) interviews
- ✅ **Real-time Answer Evaluation** - AI-powered scoring with detailed feedback
- ✅ **Performance Dashboard** - Track progress with charts and analytics
- ✅ **Voice Support** - Speech-to-text and text-to-speech for technical interviews

### Resume Analysis

- ✅ **Automatic Skill Extraction** - Extracts technologies, tools, and skills from resumes
- ✅ **Experience Level Detection** - Identifies experience level from resume content
- ✅ **Resume Keyword Extraction** - Extracts technologies, job titles, and projects
- ✅ **OCR Support** - Tesseract OCR for LaTeX-generated and scanned PDFs

### Interview Features

- ✅ **Dynamic Topic Generation** - Rule-based topic generation based on role and experience
- ✅ **Context-Aware Questions** - Questions reference specific resume content
- ✅ **Multiple Question Types** - HR, Technical, Problem-solving, and Coding questions
- ✅ **Timed Interview Mode** - 60 seconds per question with automatic timeout
- ✅ **Response Time Tracking** - Included in AI evaluation
- ✅ **Question-by-Question Scoring** - Immediate feedback after each answer
- ✅ **Comprehensive Evaluation** - Post-interview analysis with recommendations

### Technical Interview

- ✅ **Conversational AI Interview** - Dynamic follow-up questions based on answers
- ✅ **Speech-to-Text** - Voice input using OpenAI Whisper API
- ✅ **Text-to-Speech** - Audio output for questions and feedback
- ✅ **Real-time Evaluation** - AI evaluates answers and provides feedback
- ✅ **Session Management** - Track conversation history and scores

### Coding Interview

- ✅ **Code Execution** - Run Python code in secure environment
- ✅ **Test Case Validation** - Automatic test case checking
- ✅ **SQL Support** - SQL coding questions with table setup
- ✅ **Difficulty Adaptation** - Adjusts difficulty based on performance
- ✅ **Performance Metrics** - Execution time and test case results

### Dashboard & Analytics

- ✅ **Performance Metrics** - Total interviews, average score, completion rate
- ✅ **Score Trend Charts** - Visualize performance over time
- ✅ **Skills Analysis** - Identify top 3 strong skills and weak areas
- ✅ **Resume Summary** - Quick view of profile and skills
- ✅ **Interview History** - View all past interviews with scores

---

## 🏗️ System Architecture

### High-Level Architecture

The system follows a clean architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend Client (Browser)                 │
│              HTML/CSS/JavaScript + Chart.js                 │
└───────────────────────┬─────────────────────────────────────┘
                         │
                         │ HTTP/REST API
                         │
┌────────────────────────▼─────────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Profile Router│  │Interview Router│ │Dashboard Router│   │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────────────────┬─────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
┌────────▼────┐  ┌───────▼──────┐  ┌─────▼──────┐
│   Services   │  │   Services   │  │  Services  │
│ Resume Parser│  │  Question    │  │  Answer   │
│              │  │  Generator    │  │ Evaluator  │
└────────┬─────┘  └───────┬──────┘  └─────┬──────┘
         │                │               │
         └───────────────┬────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
┌────────▼────┐  ┌───────▼──────┐  ┌─────▼──────┐
│   OpenAI    │  │   LangChain   │  │  Supabase  │
│    API      │  │   Framework   │  │ PostgreSQL │
└─────────────┘  └───────────────┘  └────────────┘
```

### Data Flow

1. **Resume Upload**: User uploads resume → Backend parses → Skills extracted → Stored in database
2. **Interview Setup**: User selects role/type → Topics generated → Questions generated (AI) → Session created
3. **Answer Submission**: User submits answer → Evaluated by AI → Scores calculated → Stored in database
4. **Interview Completion**: All answers aggregated → Final evaluation generated → Dashboard updated

For detailed architecture diagrams, see [`architecture.tex`](architecture.tex) (LaTeX document with TikZ diagrams).

---

## 🛠️ Technology Stack

### Backend

- **Python 3.11+** - Core programming language
- **FastAPI** - Modern async web framework
- **Uvicorn** - ASGI server
- **Pydantic** - Data validation and settings
- **LangChain** - LLM orchestration framework
- **OpenAI API** - GPT models for question generation and evaluation

### Database & Storage

- **Supabase (PostgreSQL)** - Primary database
- **Row Level Security (RLS)** - Data access control
- **Supabase Storage** - File storage for resumes

### Frontend

- **HTML5/CSS3** - Structure and styling
- **Vanilla JavaScript (ES6+)** - Application logic
- **Chart.js** - Performance visualization
- **Web Speech API** - Voice interaction

### PDF Processing

- **PyMuPDF (fitz)** - Primary PDF text extraction
- **pdfplumber** - Advanced PDF parsing
- **python-docx** - DOCX parsing
- **Tesseract OCR** - Image-based PDF parsing

---

## 📦 Installation

### Prerequisites

- **Python 3.8+** (Python 3.11 recommended)
- **pip** (Python package manager)
- **Supabase Account** - For database and storage
- **OpenAI API Key** - For AI features (question generation, evaluation)
- **Tesseract OCR** (Optional but recommended) - For LaTeX/scanned PDF parsing

### Backend Setup

1. **Clone the repository**:
```bash
git clone <repository-url>
cd Skill-Capital-AI-MockMate
```

2. **Create a virtual environment**:
```bash
python -m venv venv
```

3. **Activate the virtual environment**:
   - **Windows (PowerShell)**:
   ```bash
   venv\Scripts\activate
   ```
   - **Windows (CMD)**:
   ```bash
   venv\Scripts\activate.bat
   ```
   - **macOS/Linux**:
   ```bash
   source venv/bin/activate
   ```

4. **Install dependencies**:
```bash
pip install -r app/requirements.txt
```

5. **Install Tesseract OCR** (Optional but recommended):

   **Windows:**
   - Download from: https://github.com/UB-Mannheim/tesseract/wiki
   - Install to default location: `C:\Program Files\Tesseract-OCR\`

   **Linux (Ubuntu/Debian):**
   ```bash
   sudo apt-get update
   sudo apt-get install tesseract-ocr
   ```

   **macOS:**
   ```bash
   brew install tesseract
   ```

6. **Set up Supabase Database**:
   - Create a new Supabase project at https://supabase.com
   - Go to SQL Editor and run the SQL from `app/database/schema.sql`
   - Create a storage bucket named `resumes` (public access)

7. **Create `.env` file** in the project root:
```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_role_key

# Backend Configuration
BACKEND_PORT=8000
ENVIRONMENT=development

# CORS Origins (comma-separated, optional)
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:8000
```

8. **Run the application**:
```bash
python app/main.py
```

The application will:
- Start the FastAPI server at `http://127.0.0.1:8000`
- Serve the frontend at `http://127.0.0.1:8000/`
- Auto-open your browser (if configured)
- API documentation available at `http://127.0.0.1:8000/docs`

### Frontend Setup

The frontend is automatically served by FastAPI. No separate setup is required!

- **Main Application**: `http://127.0.0.1:8000/`
- **Resume Analysis**: `http://127.0.0.1:8000/resume-analysis.html`
- **Technical Interview**: `http://127.0.0.1:8000/technical-interview.html`
- **Coding Interview**: `http://127.0.0.1:8000/coding-interview.html`

---

## ⚙️ Configuration

### Environment Variables

All configuration is done through environment variables in the `.env` file:

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for AI features | Yes |
| `SUPABASE_URL` | Supabase project URL | Yes |
| `SUPABASE_KEY` | Supabase anon/public key | Yes |
| `SUPABASE_SERVICE_KEY` | Supabase service role key | Yes |
| `BACKEND_PORT` | Backend server port | No (default: 8000) |
| `ENVIRONMENT` | Environment (development/production) | No (default: development) |
| `CORS_ORIGINS` | Comma-separated CORS origins | No |

### Supabase Setup

1. **Create a Supabase Project**:
   - Go to https://supabase.com
   - Create a new project
   - Note your project URL and API keys

2. **Run Database Schema**:
   - Go to SQL Editor in Supabase Dashboard
   - Copy and paste the entire content of `app/database/schema.sql`
   - Execute the SQL script
   - Verify tables are created (8 tables total)

3. **Create Storage Bucket**:
   - Go to Storage in Supabase Dashboard
   - Create a new bucket named `resumes`
   - Set it to public access (or configure RLS policies)

4. **Get API Keys**:
   - Go to Settings → API
   - Copy `URL` → `SUPABASE_URL`
   - Copy `anon public` key → `SUPABASE_KEY`
   - Copy `service_role` key → `SUPABASE_SERVICE_KEY`

### LangChain + OpenAI Setup

1. **Get OpenAI API Key**:
   - Go to https://platform.openai.com/api-keys
   - Create a new API key
   - Add it to `.env` as `OPENAI_API_KEY`

2. **LangChain Configuration** (Optional):
   - Set `LANGCHAIN_TRACING_V2=true` for tracing (optional)
   - Set `LANGCHAIN_PROJECT` for project name (optional)

---

## 📡 API Documentation

### Health & Configuration

- `GET /api/health` - Health check endpoint
- `GET /api/health/database` - Database connection health check
- `GET /api/config` - Get frontend configuration (Supabase credentials)

### Profile Management

- `GET /api/profile/{user_id}` - Get user profile
- `POST /api/profile/` - Create user profile
- `PUT /api/profile/{user_id}` - Update user profile
- `POST /api/profile/{user_id}/upload-resume` - Upload and parse resume
- `GET /api/profile/resume-analysis/{session_id}` - Get resume analysis data
- `PUT /api/profile/resume-analysis/{session_id}/experience` - Update experience level

### Interview Management

- `GET /api/interview/roles` - Get available roles
- `GET /api/interview/experience-levels` - Get experience levels
- `POST /api/interview/setup` - Setup interview and generate topics
- `POST /api/interview/generate` - Generate interview questions using AI
- `POST /api/interview/start` - Start mock interview session
- `GET /api/interview/session/{session_id}/questions` - Get all questions for a session
- `GET /api/interview/session/{session_id}/question/{question_number}` - Get specific question
- `GET /api/interview/session/{session_id}/next-question/{current_question_number}` - Get next question
- `POST /api/interview/submit-answer` - Submit answer and get AI evaluation
- `POST /api/interview/evaluate` - Generate comprehensive evaluation report

### Technical Interview

- `POST /api/interview/technical/start` - Start technical interview session
- `POST /api/interview/technical/{session_id}/next-question` - Get next technical question
- `POST /api/interview/technical/{session_id}/submit-answer` - Submit technical answer
- `GET /api/interview/technical/{session_id}/feedback` - Get final feedback
- `POST /api/interview/technical/{session_id}/end` - End technical interview
- `POST /api/interview/speech-to-text` - Convert speech audio to text (Whisper)
- `GET /api/interview/text-to-speech` - Convert text to speech (TTS)

### Coding Interview

- `POST /api/interview/coding/start` - Start coding interview session
- `POST /api/interview/coding/{session_id}/question` - Get coding question
- `POST /api/interview/coding/{session_id}/submit` - Submit code solution
- `GET /api/interview/coding/{session_id}/results` - Get coding results

### Dashboard

- `GET /api/dashboard/performance/{user_id}` - Get performance dashboard data
- `GET /api/dashboard/trends/{user_id}` - Get trends and score progression data

### API Documentation

- `GET /docs` - Interactive Swagger UI documentation
- `GET /redoc` - ReDoc documentation

---

## 🗄️ Database Schema

The application uses Supabase (PostgreSQL) with the following main tables:

### Core Tables

- **user_profiles** - User profile information, skills, resume data
- **interview_sessions** - Interview session metadata
- **technical_round** - Technical interview questions and answers
- **coding_round** - Coding interview questions and solutions
- **hr_round** - HR interview questions and answers
- **star_round** - STAR method behavioral interview data
- **question_templates** - Admin-managed question templates
- **interview_transcripts** - Interview transcripts for analytics

### Schema Details

See `app/database/schema.sql` for the complete schema with:
- Table definitions
- Row Level Security (RLS) policies
- Indexes for performance
- Foreign key constraints
- Triggers for automatic timestamp updates

---

## 📁 Project Structure

```
Skill-Capital-AI-MockMate/
├── app/                          # Backend application
│   ├── __init__.py
│   ├── main.py                   # FastAPI application entry point
│   ├── requirements.txt          # Python dependencies
│   ├── config/                   # Configuration
│   │   ├── __init__.py
│   │   └── settings.py           # Environment settings and CORS config
│   ├── database/                 # Database schema
│   │   ├── __init__.py
│   │   └── schema.sql            # Supabase database schema
│   ├── db/                       # Database client
│   │   ├── __init__.py
│   │   └── client.py             # Supabase client singleton
│   ├── routers/                  # API route handlers
│   │   ├── __init__.py
│   │   ├── profile.py            # User profile and resume upload
│   │   ├── interview.py           # Interview endpoints
│   │   └── dashboard.py          # Performance dashboard
│   ├── schemas/                  # Pydantic models
│   │   ├── __init__.py
│   │   ├── user.py               # User profile schemas
│   │   ├── interview.py          # Interview schemas
│   │   └── dashboard.py          # Dashboard schemas
│   ├── services/                 # Business logic
│   │   ├── __init__.py
│   │   ├── resume_parser.py      # Resume parsing service
│   │   ├── question_generator.py # AI question generation
│   │   ├── answer_evaluator.py   # Answer evaluation
│   │   ├── interview_evaluator.py # Interview evaluation
│   │   ├── topic_generator.py    # Topic generation
│   │   ├── coding_interview_engine.py # Coding interview engine
│   │   └── technical_interview_engine.py # Technical interview engine
│   └── utils/                    # Utility functions
│       ├── __init__.py
│       ├── database.py           # Database utilities
│       ├── datetime_utils.py     # Date/time helpers
│       ├── exceptions.py         # Custom exceptions
│       ├── file_utils.py         # File handling
│       └── resume_parser_util.py # Resume parser utilities
├── frontend/                     # Frontend files (served by FastAPI)
│   ├── index.html                # Main application page
│   ├── resume-analysis.html      # Resume analysis page
│   ├── technical-interview.html  # Technical interview page
│   ├── coding-interview.html     # Coding interview page
│   ├── styles.css                # CSS styles
│   ├── app.js                    # Main JavaScript
│   ├── technical-interview.js    # Technical interview JavaScript
│   └── logo.png                  # Logo image
├── architecture.tex             # LaTeX architecture document
├── .env                          # Environment variables (create this)
├── railway.json                  # Railway deployment config
├── render.yaml                   # Render deployment config
├── vercel.json                   # Vercel deployment config
└── README.md                     # This file
```

---

## 🚀 Development Guide

### Project Architecture

- **Clean Architecture** - Separation of concerns with routers, services, and utils
- **Dependency Injection** - FastAPI's dependency system for database clients
- **Singleton Pattern** - Database client reuse
- **Error Handling** - Custom exceptions with proper HTTP status codes
- **Type Safety** - Pydantic models for request/response validation

### Adding New Features

1. **New API Endpoint**:
   - Add route handler in `app/routers/`
   - Create Pydantic schemas in `app/schemas/`
   - Implement business logic in `app/services/`
   - Register router in `app/main.py`

2. **New Service**:
   - Create service class in `app/services/`
   - Use dependency injection for database clients
   - Add error handling and logging

3. **Database Changes**:
   - Update `app/database/schema.sql`
   - Run SQL in Supabase SQL Editor
   - Update Pydantic models if needed

### Code Style

- Follow PEP 8 Python style guide
- Use type hints for all functions
- Add docstrings for all classes and functions
- Use Pydantic models for data validation

---

## 🚢 Deployment

### Railway

1. Connect your GitHub repository to Railway
2. Railway will auto-detect the `railway.json` configuration
3. Set environment variables in Railway dashboard
4. Deploy!

### Render

1. Create a new Web Service on Render
2. Connect your repository
3. Render will use `render.yaml` for configuration
4. Set environment variables in Render dashboard
5. Deploy!

### Vercel

1. Connect your GitHub repository to Vercel
2. Vercel will auto-detect the `vercel.json` configuration
3. Set environment variables in Vercel dashboard
4. Deploy!

### Manual Deployment

```bash
# Install dependencies
pip install -r app/requirements.txt

# Set environment variables
export OPENAI_API_KEY=your_key
export SUPABASE_URL=your_url
# ... etc

# Run with uvicorn
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

---

## 🐛 Troubleshooting

### Common Issues

1. **"Supabase configuration missing"**
   - Ensure `.env` file exists in project root
   - Check that `SUPABASE_URL` and `SUPABASE_KEY` are set correctly

2. **"OpenAI API key not found"**
   - Set `OPENAI_API_KEY` in `.env` file
   - Restart the server after adding the key

3. **Resume parsing fails for LaTeX PDFs**
   - Install Tesseract OCR (see setup instructions)
   - Ensure Tesseract is in system PATH

4. **CORS errors**
   - Check `CORS_ORIGINS` in `.env`
   - In development, the app allows all origins by default

5. **Database connection errors**
   - Verify Supabase credentials
   - Check that database schema is set up correctly
   - Ensure RLS policies allow service role access

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Contribution Guidelines

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is for educational purposes.

---

## 📧 Support

For issues and questions, please open an issue on the repository.

---

**Built with ❤️ using FastAPI, OpenAI, LangChain, and Supabase**

---

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Supabase Documentation](https://supabase.com/docs)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [LangChain Documentation](https://python.langchain.com/)
- [Architecture Document](architecture.tex) - Complete LaTeX architecture document with diagrams

---

*Last Updated: 2024*
