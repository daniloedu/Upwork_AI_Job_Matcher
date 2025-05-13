# backend/main.py
import os
import logging
from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from dotenv import load_dotenv, set_key
import urllib.parse
import httpx
from pydantic import BaseModel, Field
from typing import Optional, List

# --- CORRECTED IMPORT ---
from . import upwork_api # Use relative import for sibling module
# --- END CORRECTION ---

# --- Configuration & Setup ---
DOTENV_PATH = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=DOTENV_PATH)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO) # Set logging level

UPWORK_CLIENT_ID = os.getenv("UPWORK_CLIENT_ID")
UPWORK_CLIENT_SECRET = os.getenv("UPWORK_CLIENT_SECRET")
UPWORK_REDIRECT_URI = os.getenv("UPWORK_REDIRECT_URI")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8501")

if not all([UPWORK_CLIENT_ID, UPWORK_CLIENT_SECRET, UPWORK_REDIRECT_URI]):
    logger.error("FATAL: Missing Upwork API credentials in .env file")
    exit("Missing environment variables.")

# Define Upwork OAuth2 Endpoints
UPWORK_OAUTH_BASE_URL = "https://www.upwork.com/ab/account-security/oauth2/authorize"
UPWORK_TOKEN_ENDPOINT = "https://www.upwork.com/api/v3/oauth2/token"

# --- Pydantic Models ---
class JobSearchRequest(BaseModel):
    query: Optional[str] = None
    category_ids: Optional[List[str]] = None
    # locations: Optional[List[str]] = None # Keep locations if you added logic for it in upwork_api.py
    first: int = 50
    after: Optional[str] = None

# --- FastAPI App ---
app = FastAPI(title="Upwork Opportunity Matcher Backend")


# --- Authentication Routes ---

@app.get("/login", tags=["Authentication"])
async def login_via_upwork():
    # ... (rest of function is likely OK) ...
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
    # ... (rest of function is likely OK, keep User-Agent header) ...
    logger.info(f"Received callback from Upwork with code: {code}")
    token_data = {
        "grant_type": "authorization_code", "code": code, "redirect_uri": UPWORK_REDIRECT_URI,
        "client_id": UPWORK_CLIENT_ID, "client_secret": UPWORK_CLIENT_SECRET,
    }
    headers = { 'User-Agent': 'Mozilla/5.0 ...' } # Keep your User-Agent
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(UPWORK_TOKEN_ENDPOINT, data=token_data, headers=headers)
            # ... (token processing and saving) ...
            response.raise_for_status()
            tokens = response.json()
            access_token = tokens.get('access_token')
            refresh_token = tokens.get('refresh_token')
            if not access_token: raise Exception("Access token not found...")
            logger.info("Successfully obtained access and refresh tokens.")
            # ... (save to .env) ...
            if not os.path.exists(DOTENV_PATH): open(DOTENV_PATH, 'a').close()
            set_key(DOTENV_PATH, "UPWORK_ACCESS_TOKEN", access_token)
            set_key(DOTENV_PATH, "UPWORK_REFRESH_TOKEN", refresh_token or "")
            logger.info(f"Tokens saved to {DOTENV_PATH}")
            load_dotenv(dotenv_path=DOTENV_PATH, override=True)
            return RedirectResponse(url=f"{FRONTEND_URL}?auth_status=success&refresh=true")
    except httpx.HTTPStatusError as e:
        # ... (error handling is likely OK) ...
        error_details = e.response.text
        logger.error(f"HTTP error obtaining tokens: {e.response.status_code}", exc_info=True)
        message = f"HTTP_Error_{e.response.status_code}"
        if "Cloudflare" in error_details: message += "_Cloudflare_Blocked"
        return RedirectResponse(url=f"{FRONTEND_URL}?auth_status=error&message={message}")
    except Exception as e:
        logger.error(f"Generic error obtaining tokens: {e}", exc_info=True)
        return RedirectResponse(url=f"{FRONTEND_URL}?auth_status=error&message=Failed_to_get_tokens")


@app.get("/auth/status", tags=["Authentication"])
async def get_auth_status():
    # ... (function is likely OK) ...
    load_dotenv(dotenv_path=DOTENV_PATH, override=True)
    access_token = os.getenv("UPWORK_ACCESS_TOKEN")
    authenticated = bool(access_token)
    logger.info(f"Auth status check: {authenticated}")
    return {"authenticated": authenticated}


# --- API Endpoints ---

@app.get("/filters/categories", tags=["Filters"])
async def get_categories():
    # ... (function is likely OK) ...
    try:
        categories = await upwork_api.fetch_upwork_categories()
        return JSONResponse(content=categories)
    except ValueError as e: raise HTTPException(status_code=401, detail=str(e))
    except ConnectionError as e: raise HTTPException(status_code=503, detail=str(e))
    except Exception as e: logger.error(f"Error fetching categories: {e}", exc_info=True); raise HTTPException(status_code=500)


@app.post("/jobs/fetch", tags=["Jobs"])
async def fetch_jobs(search_request: JobSearchRequest):
    # ... (function is likely OK, ensure locations param is passed if needed) ...
    logger.info(f"Received job fetch request: query='{search_request.query}', categories={search_request.category_ids}") # , locations={search_request.locations}")
    try:
        jobs_data = await upwork_api.search_upwork_jobs_gql(
            query=search_request.query,
            category_ids=search_request.category_ids,
            # locations=search_request.locations, # Pass locations if used in upwork_api.py
            first=search_request.first,
            after=search_request.after
        )
        return JSONResponse(content=jobs_data)
    except ValueError as e: logger.error(f"Credentials error: {e}"); raise HTTPException(status_code=401, detail=str(e))
    except ConnectionError as e: logger.error(f"ConnectionError: {e}", exc_info=True); raise HTTPException(status_code=503, detail=f"Service unavailable: {getattr(e, 'message', str(e))}")
    except Exception as e: logger.error(f"Unexpected error: {e}", exc_info=True); raise HTTPException(status_code=500)


# --- Health Check ---
@app.get("/healthz", tags=["System"])
async def health_check():
    return {"status": "ok"}