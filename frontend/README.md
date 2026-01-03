
# Email Automation System

AI-powered email automation with LangGraph workflow and human-in-the-loop approval.

## Tech Stack
- Backend: FastAPI, Python, LangChain, LangGraph
- Frontend: React
- Database: PostgreSQL
- LLM: Groq (Llama 3.3)
- Email: Gmail API

## Setup

### Backend
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # Configure your environment variables
python main_api.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Environment Variables Required
- `GROQ_API_KEY`
- `DATABASE_URL`
- Gmail API credentials (credentials.json)

## Features
- Automated email analysis and categorization
- AI-generated draft responses
- Human approval workflow
- Batch processing
- Email statistics dashboard
