# Upwork Opportunity Matcher

An AI-powered application that matches Upwork job listings with your profile and preferences.

## Setup

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and fill in your credentials:
   ```bash
   cp .env.example .env
   ```
5. Set up your Upwork API credentials:
   - Go to https://www.upwork.com/services/api/apply
   - Create a new application
   - Copy the Client ID and Client Secret to your `.env` file

## Running the Application

1. Start the FastAPI backend:
   ```bash
   cd backend
   uvicorn main:app --reload
   ```

2. In a new terminal, start the Streamlit frontend:
   ```bash
   cd frontend
   streamlit run app.py
   ```

3. Open your browser and navigate to:
   - Frontend: http://localhost:8501
   - Backend API docs: http://localhost:8000/docs

## Features

- Upwork OAuth authentication
- Job listing fetching and filtering
- AI-powered job matching
- Export to JSON/CSV
- Profile overview

## Development

- Backend: FastAPI
- Frontend: Streamlit
- Database: PostgreSQL
- AI: CrewAI (optional)

## Security

- All sensitive credentials are stored in `.env`
- OAuth2 authentication flow
- Secure session management
- CORS protection 