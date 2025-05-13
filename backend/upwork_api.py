# backend/upwork_api.py
import os
# --- CORRECTED IMPORTS ---
# Import Client and Config directly from their modules
from upwork.client import Client
from upwork.config import Config
# --- END CORRECTION ---
import logging
import json
from dotenv import load_dotenv
from functools import lru_cache
import asyncio
from typing import List, Optional

# --- Load environment variables (Unchanged) ---
DOTENV_PATH = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=DOTENV_PATH)
logger = logging.getLogger(__name__)
UPWORK_API_BASE_URL = "https://www.upwork.com"
UPWORK_GQL_ENDPOINT = "https://api.upwork.com/graphql"

# --- Client Initialization (Corrected Import Usage) ---
def get_authenticated_client():
    """Creates and returns an authenticated Upwork client instance using python-upwork-oauth2."""
    access_token = os.getenv("UPWORK_ACCESS_TOKEN")
    refresh_token = os.getenv("UPWORK_REFRESH_TOKEN")
    client_id = os.getenv("UPWORK_CLIENT_ID")
    client_secret = os.getenv("UPWORK_CLIENT_SECRET")
    redirect_uri = os.getenv("UPWORK_REDIRECT_URI")
    
     # --- ADD THIS LOGGING LINE ---
    logger.info(f"DEBUG: Using Access Token: {access_token}") # Log the token for Explorer use
    # --- END ADDITION ---

    
    if not all([access_token, refresh_token, client_id, client_secret, redirect_uri]):
        logger.error("Missing necessary credentials...")
        raise ValueError("Missing Upwork credentials...")
    config = {
        "client_id": client_id, "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "token": {"access_token": access_token, "refresh_token": refresh_token}
    }
    try:
        # Use DIRECTLY imported classes
        client = Client(Config(config))
        return client
    except Exception as e:
        logger.error(f"Failed to create authenticated Upwork client: {e}", exc_info=True)
        raise ConnectionError("Could not create authenticated Upwork client.") from e

# --- Tenant ID Fetching (Unchanged) ---
_tenant_id_cache = None
_tenant_id_lock = asyncio.Lock()
async def get_organization_tenant_id():
    global _tenant_id_cache
    # ... (Function body unchanged) ...
    async with _tenant_id_lock:
        if _tenant_id_cache: return _tenant_id_cache
        logger.info("Fetching organization Tenant ID...")
        client = get_authenticated_client()
        gql_query = """ query companySelector { companySelector { items { title organizationId } } } """
        try:
            client.epoint = "graphql"; gql_response = client.post("", {"query": gql_query})
            if not gql_response: raise ValueError("Received empty response fetching tenant ID.")
            logger.info(f"Company selector response: {json.dumps(gql_response, indent=2)}")
            items = gql_response.get('data', {}).get('companySelector', {}).get('items', [])
            if not items:
                default_tenant_id = os.getenv("UPWORK_DEFAULT_TENANT_ID")
                if default_tenant_id: _tenant_id_cache = default_tenant_id; return default_tenant_id
                else: raise ValueError("No organizations found and no default tenant ID configured.")
            tenant_id = items[0].get('organizationId')
            if not tenant_id: raise ValueError("First organization has no organizationId.")
            _tenant_id_cache = tenant_id; return tenant_id
        except Exception as e: logger.error(f"Failed to fetch Tenant ID: {e}", exc_info=True); raise ConnectionError("Could not determine organization Tenant ID.") from e


# --- Category Fetching (Unchanged) ---
async def fetch_upwork_categories():
    # ... (Function body unchanged) ...
    logger.info("Fetching categories from Upwork API using ontologyCategories...")
    client = get_authenticated_client()
    tenant_id = await get_organization_tenant_id()
    gql_query = """ query ontologyCategories { ontologyCategories { id preferredLabel } } """
    try:
        client.epoint = "graphql"; client.set_org_uid_header(tenant_id); gql_response = client.post("", {"query": gql_query})
        if not gql_response or 'errors' in gql_response: raise ConnectionError(f"Error fetching categories: {gql_response.get('errors', 'Empty response')}")
        categories_data = gql_response.get('data', {}).get('ontologyCategories', [])
        if not categories_data: return []
        transformed_categories = [{"id": c.get("id"), "label": c.get("preferredLabel")} for c in categories_data if c.get("id") and c.get("preferredLabel")]
        logger.info(f"Successfully fetched {len(transformed_categories)} categories.")
        return transformed_categories
    except ValueError as e: logger.error(f"Credentials error fetching categories: {e}"); raise
    except ConnectionError as e: logger.error(f"API connection error fetching categories: {e}"); raise
    except Exception as e: logger.error(f"Unexpected error fetching categories: {e}", exc_info=True); return []


# --- Job Search (GraphQL) - CORRECTED PAGINATION/FILTER LOGIC ---
async def search_upwork_jobs_gql(
    query: str = None,
    category_ids: list = None,
    locations: Optional[List[str]] = None, # Accept locations argument
    first: int = 50, # Request 50 by default
    after: Optional[str] = None,
    **kwargs
):
    """
    Searches jobs using marketplaceJobPostingsSearch.
    Correctly includes pagination with 'after' parameter always present.
    """
    client = get_authenticated_client()
    tenant_id = await get_organization_tenant_id()

    # Query with sort definition and fields
    gql_query = """
    query marketplaceJobPostingsSearch(
        $marketPlaceJobFilter: MarketplaceJobPostingsSearchFilter,
        $searchType: MarketplaceJobPostingSearchType,
        $sortAttributes: [MarketplaceJobPostingSearchSortAttribute]
    ) {
        marketplaceJobPostingsSearch(
            marketPlaceJobFilter: $marketPlaceJobFilter,
            searchType: $searchType,
            sortAttributes: $sortAttributes
        ) {
            totalCount
            edges {
                node {
                    title
                    ciphertext
                    description
                    skills { name }
                    createdDateTime
                    category
                    subcategory
                    job { contractTerms { contractType } }
                    client {
                        location { country }
                        totalFeedback
                        totalPostedJobs
                        totalHires
                        verificationStatus
                        totalReviews
                    }
                    duration
                }
            }
            pageInfo { endCursor hasNextPage }
        }
    }
    """

    # Base variables including the sort attribute that worked
    variables = {
        "searchType": "USER_JOBS_SEARCH",
        "sortAttributes": [{"field": "RECENCY"}] # Use the sort that worked previously
    }

    # --- CORRECTED Logic ---
    # Always build the market_place_filter dictionary
    market_place_filter = {}

    # Add specific filters if provided
    has_specific_filter = bool(query or category_ids or locations)
    # --- End include 'locations' ---
    has_specific_filter = False
    if query:
        market_place_filter["searchExpression_eq"] = query
        has_specific_filter = True
    if category_ids:
        market_place_filter["categoryIds_any"] = [str(cat_id) for cat_id in category_ids]
        has_specific_filter = True
    if locations:
        # Replace "locations_any" with the correct field from Upwork docs if different!
        market_place_filter["locations_any"] = locations
        has_specific_filter = True
        logger.info(f"Applying locations filter: {locations}")


    # ALWAYS add pagination_eq, and ALWAYS include 'after', defaulting to "0"
    current_after = after if after is not None else "0" # Default to "0" if None
    market_place_filter["pagination_eq"] = {"first": first, "after": current_after}
    # --- End CORRECTED PAGINATION Logic ---

    # ALWAYS add the marketPlaceJobFilter object to variables
    variables["marketPlaceJobFilter"] = market_place_filter

    log_message_prefix = "Executing FILTERED" if has_specific_filter else "Executing ALL JOBS (with pagination)"
    logger.info(f"{log_message_prefix} GraphQL job search with variables: {json.dumps(variables)}")

    try:
        client.epoint = "graphql"
        client.set_org_uid_header(tenant_id)
        gql_response = client.post("", {"query": gql_query, "variables": variables})

        logger.debug(f"Raw GraphQL response (Anna's Fix Test): {json.dumps(gql_response, indent=2)}")

        if gql_response and 'errors' in gql_response:
             logger.warning(f"GraphQL query (Anna's Fix Test) failed with errors: {gql_response['errors']}")
             # You might want to check for the 500 error specifically again here if it reappears
             return {"jobs": [], "paging": {"total": 0, "next_cursor": None, "has_next_page": False}}

        search_results = gql_response.get('data', {}).get('marketplaceJobPostingsSearch')

        if search_results is None:
             logger.warning(f"GraphQL query (Anna's Fix Test) executed but 'marketplaceJobPostingsSearch' is null/missing: {gql_response}")
             return {"jobs": [], "paging": {"total": 0, "next_cursor": None, "has_next_page": False}}

        # --- Transform Response ---
        transformed_jobs = []
        if search_results.get('edges'):
            for edge in search_results['edges']:
                node = edge.get('node', {})
                job_details=node.get('job',{}) or {}; contract_terms=job_details.get('contractTerms',{}) or {}; client_details=node.get('client',{}) or {}; client_location=client_details.get('location',{}) or {}
                job = {"title": node.get('title'), "id": node.get('ciphertext'), "ciphertext": node.get('ciphertext'), # Using ciphertext as id
                       "snippet": node.get('description'), "skills": [s.get('name') for s in node.get('skills', []) if s.get('name')],
                       "date_created": node.get('createdDateTime'), "category2": node.get('category'), "subcategory2": node.get('subcategory'),
                       "job_type": contract_terms.get('contractType'), "workload": None, "duration": node.get('duration'),
                       "client": { "country": client_location.get('country'), "feedback": client_details.get('totalFeedback'),
                                   "jobs_posted": client_details.get('totalPostedJobs'), "past_hires": client_details.get('totalHires'),
                                   "payment_verification_status": client_details.get('verificationStatus'), "reviews_count": client_details.get('totalReviews'), }}
                transformed_jobs.append(job)

        paging_info = { "total": search_results.get('totalCount'),
                        "next_cursor": search_results.get('pageInfo', {}).get('endCursor'),
                        "has_next_page": search_results.get('pageInfo', {}).get('hasNextPage'), }
        final_result = {"jobs": transformed_jobs, "paging": paging_info}
        logger.info(f"Found jobs via GQL (Anna's Fix Test): {len(transformed_jobs)} (Total matching query: {paging_info.get('total')})")
        return final_result

    except ValueError as e: logger.error(f"Credentials error: {e}"); raise
    except ConnectionError as e: logger.error(f"API connection error: {e}"); raise ConnectionError("Failed to search jobs.") from e
    except Exception as e: logger.error(f"Unexpected error: {e}", exc_info=True); raise ConnectionError("Failed to search jobs.") from e