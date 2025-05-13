# backend/upwork_api.py
import os
import upwork
import logging
import json
from dotenv import load_dotenv
from functools import lru_cache
import asyncio
from typing import List, Optional

# --- Load environment variables ---
DOTENV_PATH = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=DOTENV_PATH)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO) # Ensure INFO level is set
# --- End Load environment variables ---

# --- Constants ---
UPWORK_API_BASE_URL = "https://www.upwork.com"
UPWORK_GQL_ENDPOINT = "https://api.upwork.com/graphql"
# --- End Constants ---

# --- Client Initialization (Unchanged) ---
def get_authenticated_client():
    access_token = os.getenv("UPWORK_ACCESS_TOKEN")
    refresh_token = os.getenv("UPWORK_REFRESH_TOKEN")
    client_id = os.getenv("UPWORK_CLIENT_ID")
    client_secret = os.getenv("UPWORK_CLIENT_SECRET")
    redirect_uri = os.getenv("UPWORK_REDIRECT_URI")
    if not all([access_token, refresh_token, client_id, client_secret, redirect_uri]):
        logger.error("Missing necessary credentials...")
        raise ValueError("Missing Upwork credentials...")
    config = {
        "client_id": client_id, "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "token": {"access_token": access_token, "refresh_token": refresh_token}
    }
    try:
        client = upwork.Client(upwork.Config(config))
        return client
    except Exception as e:
        logger.error(f"Failed to create authenticated Upwork client: {e}", exc_info=True)
        raise ConnectionError("Could not create authenticated Upwork client.") from e

# --- Tenant ID Fetching (Unchanged) ---
_tenant_id_cache = None
_tenant_id_lock = asyncio.Lock()
async def get_organization_tenant_id():
    global _tenant_id_cache
    async with _tenant_id_lock:
        if _tenant_id_cache: logger.info(f"Using cached Tenant ID: {_tenant_id_cache}"); return _tenant_id_cache
        logger.info("Fetching organization Tenant ID...")
        client = get_authenticated_client()
        gql_query = """ query companySelector { companySelector { items { title organizationId } } } """
        try:
            client.epoint = "graphql"
            gql_response = client.post("", {"query": gql_query})
            if not gql_response: raise ValueError("Received empty response fetching tenant ID.")
            logger.info(f"Company selector response: {json.dumps(gql_response, indent=2)}")
            items = gql_response.get('data', {}).get('companySelector', {}).get('items', [])
            if not items:
                default_tenant_id = os.getenv("UPWORK_DEFAULT_TENANT_ID")
                if default_tenant_id: _tenant_id_cache = default_tenant_id; logger.info(f"Using default Tenant ID: {default_tenant_id}"); return default_tenant_id
                else: raise ValueError("No organizations found and no default tenant ID configured.")
            tenant_id = items[0].get('organizationId')
            if not tenant_id: raise ValueError("First organization has no organizationId.")
            _tenant_id_cache = tenant_id; logger.info(f"Fetched and cached Tenant ID: {tenant_id}"); return tenant_id
        except Exception as e:
            logger.error(f"Failed to fetch Tenant ID: {e}", exc_info=True)
            raise ConnectionError("Could not determine organization Tenant ID.") from e

# --- Category Fetching (Unchanged - Keep Live Fetching) ---
async def fetch_upwork_categories():
    logger.info("Fetching categories from Upwork API using ontologyCategories...")
    client = get_authenticated_client()
    tenant_id = await get_organization_tenant_id()
    gql_query = """ query ontologyCategories { ontologyCategories { id preferredLabel } } """
    try:
        client.epoint = "graphql"
        client.set_org_uid_header(tenant_id)
        gql_response = client.post("", {"query": gql_query})
        if not gql_response or 'errors' in gql_response:
            raise ConnectionError(f"Error fetching categories: {gql_response.get('errors', 'Empty response')}")
        categories_data = gql_response.get('data', {}).get('ontologyCategories', [])
        if not categories_data: return []
        transformed_categories = [{"id": c.get("id"), "label": c.get("preferredLabel")} for c in categories_data if c.get("id") and c.get("preferredLabel")]
        logger.info(f"Successfully fetched {len(transformed_categories)} categories.")
        return transformed_categories
    except ValueError as e: logger.error(f"Credentials error fetching categories: {e}"); raise
    except ConnectionError as e: logger.error(f"API connection error fetching categories: {e}"); raise
    except Exception as e: logger.error(f"Unexpected error fetching categories: {e}", exc_info=True); return []


# --- Job Search (GraphQL) - Location Test Logic ---
async def search_upwork_jobs_gql(
    query: str = None,
    category_ids: list = None,
    locations: list = None, # Accept locations
    first: int = 50,
    after: Optional[str] = None,
    **kwargs
):
    """
    Searches jobs using marketplaceJobPostingsSearch.
    TESTING: Prioritizes Location filter if provided.
    Falls back to the only known working state (empty filter object).
    Includes pagination *only* when specific filters are sent.
    """
    client = get_authenticated_client()
    tenant_id = await get_organization_tenant_id()

    # Use the query with full fields requested previously
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
                    title ciphertext description skills { name } createdDateTime
                    category subcategory job { contractTerms { contractType } }
                    client { location { country } totalFeedback totalPostedJobs
                             totalHires verificationStatus totalReviews }
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
        "sortAttributes": [{"field": "RECENCY"}] # Keep the sort that worked for no-filter
    }

    # --- TEST Filter Logic ---
    market_place_filter = {}
    filter_applied = False # Flag to know if we added specific filters

    # PRIORITIZE Location for this test
    if locations:
        logger.info(">>> TESTING: Location filter provided. Ignoring query/category. <<<")
        market_place_filter["locations_any"] = locations # Use the provided locations list
        filter_applied = True
    elif query:
        logger.info("Location not provided, using keyword query.")
        market_place_filter["searchExpression_eq"] = query
        filter_applied = True
    elif category_ids:
        logger.info("Location/query not provided, using category.")
        market_place_filter["categoryIds_any"] = [str(cat_id) for cat_id in category_ids]
        filter_applied = True

    # Add pagination ONLY if a specific filter was applied
    if filter_applied:
        pagination_filter = {"first": first}
        if after:
            pagination_filter["after"] = after
        market_place_filter["pagination_eq"] = pagination_filter
        variables["marketPlaceJobFilter"] = market_place_filter # Add populated filter
        log_message_prefix = "Executing FILTERED (Location Priority)"
    else:
        # If NO filters applied, send EMPTY filter object to match successful log
        variables["marketPlaceJobFilter"] = {}
        log_message_prefix = "Executing ALL JOBS (empty filter object)"
        # Default 10 results expected here
    # --- End TEST Filter Logic ---

    logger.info(f"{log_message_prefix} GraphQL job search with variables: {json.dumps(variables)}")

    try:
        client.epoint = "graphql"
        client.set_org_uid_header(tenant_id)
        gql_response = client.post("", {"query": gql_query, "variables": variables})

        logger.debug(f"Raw GraphQL response (Location Test): {json.dumps(gql_response, indent=2)}")

        # --- Refined Error Handling ---
        api_error_message = None
        if gql_response and 'errors' in gql_response:
            logger.warning(f"GraphQL query (Location Test) failed with errors: {gql_response['errors']}")
            # Extract first error message for potential display
            first_error = gql_response['errors'][0].get('message', 'Unknown API error')
            api_error_message = f"Upwork API Error: {first_error}" # Store error message

            # Specifically log the persistent 500 error
            for error in gql_response['errors']:
                if error.get('extensions', {}).get('code') == '500' and 'Elastic migration issue' in error.get('message', ''):
                     logger.error(">>> Persistent Upwork 500 Error Detected Again <<<")

            # Return structure indicating handled error
            return {"jobs": [], "paging": {"total": 0, "next_cursor": None, "has_next_page": False}, "error_message": api_error_message}

        search_results = gql_response.get('data', {}).get('marketplaceJobPostingsSearch')

        if search_results is None:
             logger.warning(f"GraphQL query (Location Test) executed but 'marketplaceJobPostingsSearch' is null/missing: {gql_response}")
             return {"jobs": [], "paging": {"total": 0, "next_cursor": None, "has_next_page": False}, "error_message": "API returned null results."}
        # --- End Refined Error Handling ---


        # --- Transform Response (Full fields) ---
        transformed_jobs = []
        # ... (Keep the transformation logic from the previous full code block) ...
        if search_results.get('edges'):
            for edge in search_results['edges']:
                node = edge.get('node', {})
                job_details = node.get('job', {}) or {}
                contract_terms = job_details.get('contractTerms', {}) or {}
                client_details = node.get('client', {}) or {}
                client_location = client_details.get('location', {}) or {}
                job = {
                     "title": node.get('title'), "id": node.get('ciphertext'), "ciphertext": node.get('ciphertext'),
                     "snippet": node.get('description'), "skills": [s.get('name') for s in node.get('skills', []) if s.get('name')],
                     "date_created": node.get('createdDateTime'), "category2": node.get('category'), "subcategory2": node.get('subcategory'),
                     "job_type": contract_terms.get('contractType'), "workload": None, "duration": node.get('duration'),
                     "client": {
                          "country": client_location.get('country'), "feedback": client_details.get('totalFeedback'),
                          "jobs_posted": client_details.get('totalPostedJobs'), "past_hires": client_details.get('totalHires'),
                          "payment_verification_status": client_details.get('verificationStatus'), "reviews_count": client_details.get('totalReviews'),
                     } }
                transformed_jobs.append(job)
        # --- End Transformation ---


        paging_info = {
            "total": search_results.get('totalCount'),
            "next_cursor": search_results.get('pageInfo', {}).get('endCursor'),
            "has_next_page": search_results.get('pageInfo', {}).get('hasNextPage'),
        }
        final_result = {"jobs": transformed_jobs, "paging": paging_info}
        logger.info(f"Found jobs via GQL (Location Test Logic): {len(transformed_jobs)} (Total matching query: {paging_info.get('total')})")
        return final_result # Return successful result

    except ValueError as e: logger.error(f"Credentials error: {e}"); raise # Let FastAPI handle this
    except ConnectionError as e: logger.error(f"API connection error: {e}"); raise # Let FastAPI handle this
    except Exception as e: logger.error(f"Unexpected error: {e}", exc_info=True); raise ConnectionError("Unexpected backend error during job search.") from e # Wrap unexpected as ConnectionError
