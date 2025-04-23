# backend/main.py
import os
# import upwork # No longer needed here
import logging
from fastapi import FastAPI, Request, Query, HTTPException # Add HTTPException
from fastapi.responses import RedirectResponse, JSONResponse # Add JSONResponse
from dotenv import load_dotenv, set_key
import urllib.parse
import httpx
from pydantic import BaseModel, Field # For request body validation
from typing import Optional, List # For typing

# Import functions from upwork_api module
from . import upwork_api

# --- Configuration & Setup ---
DOTENV_PATH = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=DOTENV_PATH)  # Load environment variables from .env file

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

UPWORK_CLIENT_ID = os.getenv("UPWORK_CLIENT_ID")
UPWORK_CLIENT_SECRET = os.getenv("UPWORK_CLIENT_SECRET")
UPWORK_REDIRECT_URI = os.getenv("UPWORK_REDIRECT_URI")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8501")

if not all([UPWORK_CLIENT_ID, UPWORK_CLIENT_SECRET, UPWORK_REDIRECT_URI]):
    logger.error("FATAL: Missing Upwork API credentials in .env file")
    exit("Missing environment variables.")

# Initialize client with dictionary config - might be needed for token exchange later? NO LONGER NEEDED FOR AUTH
# config = {
#     "client_id": UPWORK_CLIENT_ID,
#     "client_secret": UPWORK_CLIENT_SECRET,
#     "redirect_uri": UPWORK_REDIRECT_URI
# }
# upwork_client = upwork.Client(config)

app = FastAPI(title="Upwork Opportunity Matcher Backend")

# Define Upwork OAuth2 Endpoints
UPWORK_OAUTH_BASE_URL = "https://www.upwork.com/ab/account-security/oauth2/authorize"
UPWORK_TOKEN_ENDPOINT = "https://www.upwork.com/api/v3/oauth2/token" # Corrected endpoint based on latest documentation

# --- Upwork API Endpoints ---

@app.get("/filters/categories", tags=["Filters"])
async def get_categories():
    """Endpoint to fetch job categories from Upwork."""
    try:
        categories = await upwork_api.fetch_upwork_categories()
        return JSONResponse(content=categories)
    except ValueError as e: # Credentials missing
        raise HTTPException(status_code=401, detail=str(e))
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e)) # Service unavailable
    except Exception as e:
        logger.error(f"Unexpected error fetching categories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error fetching categories.")

# Define Pydantic model for job search request body
class JobSearchRequest(BaseModel):
    query: Optional[str] = None
    # Use category_ids for GraphQL - frontend needs to send IDs if available
    category_ids: Optional[List[str]] = None 
    # Keep category2 for potential REST mapping? No, stick to GQL.
    # categories: Optional[List[str]] = Field(None, alias="category2") 
    # Add other potential filters here based on Upwork API
    # skills: Optional[List[str]] = None
    # duration: Optional[str] = None
    # workload: Optional[str] = None

@app.post("/jobs/fetch", tags=["Jobs"])
async def fetch_jobs(search_request: JobSearchRequest):
    """Endpoint to fetch jobs based on search criteria using GraphQL."""
    try:
        # Pass parameters to the GraphQL search function
        jobs_data = await upwork_api.search_upwork_jobs_gql(
            query=search_request.query,
            category_ids=search_request.category_ids
            # Pass other fields from search_request if added
            # e.g., duration=search_request.duration
        )
        # The gql function now returns data in the desired format {"jobs": [...], "paging": {...}}
        return JSONResponse(content=jobs_data)
    except ValueError as e: # Credentials missing
        raise HTTPException(status_code=401, detail=str(e))
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e)) # Service unavailable
    except NotImplementedError as e: # SDK method missing
         raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error fetching jobs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error fetching jobs.")

# --- Authentication Routes ---

@app.get("/login", tags=["Authentication"])
async def login_via_upwork():
    """
    Redirects the user to the Upwork OAuth2 authorization page.
    Construct the URL manually for OAuth2 flow.
    """
    params = {
        "client_id": UPWORK_CLIENT_ID,
        "redirect_uri": UPWORK_REDIRECT_URI,
        "response_type": "code"
    }
    authorization_url = f"{UPWORK_OAUTH_BASE_URL}?{urllib.parse.urlencode(params)}"
    logger.info(f"Redirecting user to Upwork for authorization: {authorization_url}")
    return RedirectResponse(url=authorization_url)

@app.get("/oauth/callback", tags=["Authentication"])
async def oauth_callback(request: Request, code: str = Query(...), state: str = Query(None)):
    """
    Handles the callback from Upwork after user authorization.
    Exchanges the authorization code for tokens manually and saves them to .env.
    """
    logger.info(f"Received callback from Upwork with code: {code}")

    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": UPWORK_REDIRECT_URI,
        "client_id": UPWORK_CLIENT_ID,
        "client_secret": UPWORK_CLIENT_SECRET,
    }

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(UPWORK_TOKEN_ENDPOINT, data=token_data, headers=headers)
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
            tokens = response.json()

        access_token = tokens.get('access_token')
        refresh_token = tokens.get('refresh_token')

        if not access_token:
            logger.error(f"Failed to get access token from response: {tokens}")
            raise Exception("Access token not found in Upwork response.")

        logger.info("Successfully obtained access and refresh tokens.")

        # --- Automatically Store Tokens in .env ---
        if not os.path.exists(DOTENV_PATH):
             logger.warning(f".env file not found at {DOTENV_PATH}. Creating it.")
             open(DOTENV_PATH, 'a').close() # Create empty file if it doesn't exist

        set_key(DOTENV_PATH, "UPWORK_ACCESS_TOKEN", access_token)
        set_key(DOTENV_PATH, "UPWORK_REFRESH_TOKEN", refresh_token)
        logger.info(f"Tokens automatically saved to {DOTENV_PATH}")
        # Reload environment variables in the current process *after* saving
        load_dotenv(dotenv_path=DOTENV_PATH, override=True)

        # Redirect back to the frontend, indicating success
        # The frontend might need a refresh or restart to see the new auth status
        return RedirectResponse(url=f"{FRONTEND_URL}?auth_status=success&refresh=true")

    except httpx.HTTPStatusError as e:
        error_details = e.response.text
        logger.error(f"HTTP error obtaining tokens from Upwork: {e.response.status_code} - {error_details}", exc_info=True)
        return RedirectResponse(url=f"{FRONTEND_URL}?auth_status=error&message=HTTP_Error_{e.response.status_code}")
    except Exception as e:
        logger.error(f"Generic error obtaining tokens: {e}", exc_info=True)
        return RedirectResponse(url=f"{FRONTEND_URL}?auth_status=error&message=Failed_to_get_tokens")

@app.get("/auth/status", tags=["Authentication"])
async def get_auth_status():
    """
    Checks if Upwork tokens are present in the environment variables.
    Needs to reload env vars potentially if they were just added.
    """
    # Reload from .env in case they were just added by the callback
    # Note: This might not be instant if the file system write is slow,
    # but it's better than nothing for a quick check.
    load_dotenv(dotenv_path=DOTENV_PATH, override=True)
    access_token = os.getenv("UPWORK_ACCESS_TOKEN")
    refresh_token = os.getenv("UPWORK_REFRESH_TOKEN")
    authenticated = bool(access_token and refresh_token)
    logger.info(f"Auth status check: {authenticated}")
    return {"authenticated": authenticated}

# --- Health Check ---
@app.get("/healthz", tags=["System"])
async def health_check():
    """Basic health check endpoint."""
    return {"status": "ok"}

# --- Placeholder for other endpoints ---
# (Add endpoints for filters, jobs, profile later)

# --- Run Instructions ---
# Run the backend server using: uvicorn backend.main:app --reload --port 8000