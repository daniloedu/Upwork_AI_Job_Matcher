import os
import upwork # This should now refer to python-upwork-oauth2
import logging
import json # For formatting GraphQL variables
from dotenv import load_dotenv
from functools import lru_cache
import asyncio

# Load environment variables specifically for this module if needed
# Assumes .env is in the parent directory relative to this file's location (backend/)
DOTENV_PATH = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=DOTENV_PATH)

logger = logging.getLogger(__name__)

UPWORK_API_BASE_URL = "https://www.upwork.com"
UPWORK_GQL_ENDPOINT = "https://api.upwork.com/graphql" # Standard GQL Endpoint

# --- Client Initialization (Keep as is for now) ---
def get_authenticated_client():
    """Creates and returns an authenticated Upwork client instance using python-upwork-oauth2."""
    access_token = os.getenv("UPWORK_ACCESS_TOKEN")
    refresh_token = os.getenv("UPWORK_REFRESH_TOKEN")
    client_id = os.getenv("UPWORK_CLIENT_ID")
    client_secret = os.getenv("UPWORK_CLIENT_SECRET")
    redirect_uri = os.getenv("UPWORK_REDIRECT_URI")

    if not all([access_token, refresh_token, client_id, client_secret, redirect_uri]):
        logger.error("Missing necessary credentials (tokens/ID/secret/redirect) in environment for authenticated client.")
        raise ValueError("Missing Upwork credentials in environment.")

    # Create config dictionary in the format expected by python-upwork-oauth2
    config = {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "token": {
            "access_token": access_token,
            "refresh_token": refresh_token
        }
    }
    
    try:
        # Create Config instance and pass it to Client
        client = upwork.Client(upwork.Config(config))
        return client
    except Exception as e:
        logger.error(f"Failed to create authenticated Upwork client: {e}", exc_info=True)
        raise ConnectionError("Could not create authenticated Upwork client.") from e

# --- Tenant ID Fetching (NEW) ---
# Use a simple in-memory cache for the tenant ID during the app's lifetime
_tenant_id_cache = None
_tenant_id_lock = asyncio.Lock()

async def get_organization_tenant_id():
    """Fetches the user's default organization Tenant ID using GraphQL and caches it."""
    global _tenant_id_cache
    async with _tenant_id_lock:
        if _tenant_id_cache:
            logger.info(f"Using cached Tenant ID: {_tenant_id_cache}")
            return _tenant_id_cache

        logger.info("Fetching organization Tenant ID...")
        client = get_authenticated_client()
        gql_query = """
        query companySelector {
          companySelector {
            items {
              title
              organizationId
            }
          }
        }
        """
        try:
            # Set the endpoint to graphql
            client.epoint = "graphql"
            
            # Execute the GraphQL query using post method
            gql_response = client.post("", {"query": gql_query})

            if not gql_response:
                logger.error("Received empty response from companySelector query")
                raise ValueError("Received empty response fetching tenant ID.")

            # Log the full response for debugging
            logger.info(f"Company selector response: {json.dumps(gql_response, indent=2)}")

            items = gql_response.get('data', {}).get('companySelector', {}).get('items', [])
            if not items:
                logger.warning("No organizations found in companySelector response. Using default organization.")
                # If no organizations are found, we'll use a default tenant ID
                # This is a fallback and might need to be adjusted based on your needs
                default_tenant_id = os.getenv("UPWORK_DEFAULT_TENANT_ID")
                if default_tenant_id:
                    logger.info(f"Using default tenant ID from environment: {default_tenant_id}")
                    _tenant_id_cache = default_tenant_id
                    return default_tenant_id
                else:
                    raise ValueError("No organizations found and no default tenant ID configured.")

            # Use the first organization ID as the default Tenant ID
            tenant_id = items[0].get('organizationId')
            if not tenant_id:
                logger.error("First organization in list has no organizationId")
                raise ValueError("First organization in list has no organizationId.")

            logger.info(f"Fetched and cached Tenant ID: {tenant_id}")
            _tenant_id_cache = tenant_id
            return tenant_id

        except Exception as e:
            logger.error(f"Failed to fetch Tenant ID: {e}", exc_info=True)
            raise ConnectionError("Could not determine organization Tenant ID.") from e

# --- Category Fetching (Updated) ---
async def fetch_upwork_categories():
    """Returns a predefined list of common Upwork categories."""
    logger.info("Using predefined categories instead of fetching from API")
    
    # Common Upwork categories with their IDs
    # These are approximate and may need adjustment
    categories = [
        {"id": "531770282580668419", "label": "Web Development"},
        {"id": "531770282580668420", "label": "Mobile Development"},
        {"id": "531770282580668421", "label": "UI/UX Design"},
        {"id": "531770282580668422", "label": "Data Science & Analytics"},
        {"id": "531770282580668423", "label": "DevOps & System Administration"},
        {"id": "531770282580668424", "label": "QA & Testing"},
        {"id": "531770282580668425", "label": "Project Management"},
        {"id": "531770282580668426", "label": "Content Writing"},
        {"id": "531770282580668427", "label": "Translation"},
        {"id": "531770282580668428", "label": "Digital Marketing"},
        {"id": "531770282580668429", "label": "SEO"},
        {"id": "531770282580668430", "label": "Social Media Marketing"},
        {"id": "531770282580668431", "label": "Video & Animation"},
        {"id": "531770282580668432", "label": "Graphic Design"},
        {"id": "531770282580668433", "label": "Accounting & Bookkeeping"},
        {"id": "531770282580668434", "label": "Customer Service"},
        {"id": "531770282580668435", "label": "Data Entry"},
        {"id": "531770282580668436", "label": "Virtual Assistant"},
        {"id": "531770282580668437", "label": "Sales & Marketing"},
        {"id": "531770282580668438", "label": "Business Analysis"},
        {"id": "531770282580668439", "label": "Legal"},
        {"id": "531770282580668440", "label": "Engineering & Architecture"},
        {"id": "531770282580668441", "label": "Other"}
    ]
    
    logger.info(f"Returning {len(categories)} predefined categories")
    return categories

# Using GraphQL for Job Search
async def search_upwork_jobs_gql(query: str = None, category_ids: list = None, **kwargs):
    """Searches for jobs on Upwork using the GraphQL API via the SDK."""
    client = get_authenticated_client()
    tenant_id = await get_organization_tenant_id() # Get Tenant ID

    # GraphQL query based on the official Upwork documentation
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
                    skills {
                        name
                    }
                    createdDateTime
                    category
                    subcategory
                    job {
                        contractTerms {
                            contractType
                        }
                    }
                    client {
                        location {
                            country
                        }
                        totalFeedback
                        totalPostedJobs
                        totalHires
                        verificationStatus
                        totalReviews
                    }
                    duration
                }
            }
            pageInfo {
                endCursor
                hasNextPage
            }
        }
    }
    """

    # Construct variables based on input and docs
    market_place_filter = {}
    if query:
        market_place_filter["searchExpression_eq"] = query
    if category_ids:
        # Ensure category_ids are strings if needed by GraphQL schema
        market_place_filter["categoryIds_any"] = [str(cat_id) for cat_id in category_ids] 
    
    variables = {
        "marketPlaceJobFilter": market_place_filter,
        "searchType": "USER_JOBS_SEARCH",
        "sortAttributes": [{
            "field": "RECENCY"
        }]
    }

    logger.info(f"Executing GraphQL job search with variables: {json.dumps(variables)}")
    
    try:
        # Set the endpoint to graphql
        client.epoint = "graphql"
        
        # Set the tenant ID in the client config
        client.set_org_uid_header(tenant_id)
        
        # Execute the GraphQL query using post method with variables
        gql_response = client.post("", {"query": gql_query, "variables": variables})
        
        # Log the response for debugging
        logger.info(f"GraphQL response: {json.dumps(gql_response, indent=2)}")
        
        if not gql_response:
             raise ValueError("Received empty response from GraphQL execution.")
        
        search_results = gql_response.get('data', {}).get('marketplaceJobPostingsSearch')
        if not search_results:
            logger.warning(f"GraphQL query executed but 'marketplaceJobPostingsSearch' not found in response data: {gql_response}")
            return {"jobs": [], "paging": {}} # Return empty structure
        
        # --- Transform GraphQL edges to match expected REST-like structure --- 
        transformed_jobs = []
        if search_results.get('edges'):
            for edge in search_results['edges']:
                node = edge.get('node', {})
                job = {
                    "title": node.get('title'),
                    "id": node.get('ciphertext'), # Legacy ID
                    "ciphertext": node.get('ciphertext'), # Keep for URL
                    "snippet": node.get('description'),
                    "skills": [s.get('name') for s in node.get('skills', []) if s.get('name')],
                    "date_created": node.get('createdDateTime'),
                    "category2": node.get('category'),
                    "subcategory2": node.get('subcategory'),
                    "job_type": node.get('job', {}).get('contractTerms', {}).get('contractType'),
                    "workload": None, # Not available in the API
                    "duration": node.get('duration'),
                    "client": {
                         "country": node.get('client', {}).get('location', {}).get('country'),
                         "feedback": node.get('client', {}).get('totalFeedback'),
                         "jobs_posted": node.get('client', {}).get('totalPostedJobs'),
                         "past_hires": node.get('client', {}).get('totalHires'),
                         "payment_verification_status": node.get('client', {}).get('verificationStatus'),
                         "reviews_count": node.get('client', {}).get('totalReviews'),
                    }
                }
                transformed_jobs.append(job)
        
        paging_info = {
            "total": search_results.get('totalCount'),
            "next_cursor": search_results.get('pageInfo', {}).get('endCursor'),
            "has_next_page": search_results.get('pageInfo', {}).get('hasNextPage'),
        }

        final_result = {"jobs": transformed_jobs, "paging": paging_info}
        logger.info(f"Found jobs via GQL: {len(transformed_jobs)}")
        return final_result

    except ValueError as e: # Credentials missing or empty response
        logger.error(f"Data error searching jobs GQL: {e}")
        raise
    except Exception as e: # Catch other SDK or network errors
        logger.error(f"Error executing GraphQL job search: {e}", exc_info=True)
        raise ConnectionError("Failed to search jobs on Upwork via GraphQL.") from e