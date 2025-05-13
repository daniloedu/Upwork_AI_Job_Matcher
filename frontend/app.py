# frontend/app.py
import streamlit as st
import requests
import os
import time
import json
import pandas as pd
from io import StringIO # For CSV, though not strictly needed if pandas handles it
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv() # Load .env if needed, though frontend mainly interacts via backend
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# --- Helper Function ---
def check_backend_auth_status():
    """Checks if the backend reports authentication tokens are present."""
    try:
        response = requests.get(f"{BACKEND_URL}/auth/status")
        response.raise_for_status()
        is_authenticated = response.json().get("authenticated", False)
        st.session_state['authenticated'] = is_authenticated
        return is_authenticated
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to backend: {e}")
        st.session_state['authenticated'] = False
        return False

# Function to fetch categories
@st.cache_data(ttl=3600) # Cache for 1 hour
def get_categories_from_backend(): # Renamed for clarity
    try:
        response = requests.get(f"{BACKEND_URL}/filters/categories")
        response.raise_for_status()
        categories_data = response.json()
        return categories_data if isinstance(categories_data, list) else []
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching categories: {e}")
        return []
    except Exception as e: # Catch other potential errors like JSONDecodeError
        st.error(f"An error occurred processing categories: {e}")
        return []

# Function to fetch jobs
def fetch_jobs_from_backend(query: str, category_ids: list, locations: list = None): # Added locations
    payload = {
        "query": query if query else None,
        "category_ids": category_ids if category_ids else None,
        "locations": locations if locations else None, # Pass locations
        # "first": 50, # Pagination is handled by backend default now,
                       # but could be passed if UI for it is added
        # "after": None # Similarly for 'after'
    }
    try:
        response = requests.post(f"{BACKEND_URL}/jobs/fetch", json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        # Try to get more details from the error response if available
        error_detail = "Unknown error"
        if e.response is not None:
            try:
                error_detail = e.response.json().get("detail", e.response.text)
            except json.JSONDecodeError:
                error_detail = e.response.text
        st.error(f"Error fetching jobs: {error_detail}")
        return None # Return None or an error structure
    except Exception as e:
        st.error(f"An unexpected error occurred fetching jobs: {e}")
        return None


# --- Streamlit App ---
st.set_page_config(layout="wide")
st.title("AI-Powered Upwork Opportunity Matcher")

# --- Initialize ALL required session state keys ---
# This ensures they exist before any widget tries to access or set them
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False # Use attribute access for consistency
if 'jobs_data' not in st.session_state:
    st.session_state.jobs_data = None
if 'categories_list' not in st.session_state: # Stores raw list from backend
    st.session_state.categories_list = []
if 'category_options_map' not in st.session_state: # Stores id:label map for display
    st.session_state.category_options_map = {}
# Filter inputs - Initialize with defaults that make sense
if 'selected_category_ids' not in st.session_state:
    st.session_state.selected_category_ids = []
if 'search_query' not in st.session_state:
    st.session_state.search_query = ""
if 'selected_locations' not in st.session_state: # For location filter
    st.session_state.selected_locations = []
# --- End Initialization ---


# --- Authentication Check & Callback Handling ---
# Perform initial auth check only if not already marked as authenticated
if not st.session_state.authenticated:
    check_backend_auth_status()

query_params = st.query_params # Use st.query_params directly
auth_status_param = query_params.get("auth_status")
refresh_needed_param = query_params.get("refresh")

if auth_status_param == "success":
    st.success("Authentication successful! Tokens saved.")
    if refresh_needed_param == "true":
        st.info("Verifying authentication status...")
        time.sleep(1) # Give backend a moment
        # Create a new dictionary for st.query_params without 'refresh'
        new_params = {k: v for k, v in query_params.items() if k != "refresh"}
        st.query_params = new_params # Update query params
        check_backend_auth_status() # Re-check
        st.rerun() # Rerun to reflect new state
    elif st.session_state.authenticated: # Already authenticated and no refresh needed
        st.query_params.clear() # Clear all query params

elif auth_status_param == "error":
    message = query_params.get("message", "Unknown error during authentication.")
    st.error(f"Authentication failed: {message.replace('_', ' ')}")
    st.session_state.authenticated = False
    st.query_params.clear()
    st.rerun() # Rerun to show login page if previously on dashboard

# --- Main Display Logic ---
if st.session_state.authenticated:
    st.sidebar.success("✅ Authenticated with Upwork")

    # --- Filters Sidebar ---
    with st.sidebar:
        st.header("Filters")

        # Fetch and prepare categories only once or if empty
        if not st.session_state.categories_list:
             st.session_state.categories_list = get_categories_from_backend()
             if st.session_state.categories_list:
                 st.session_state.category_options_map = {
                     cat['id']: cat['label'] for cat in st.session_state.categories_list
                 }
             else:
                 st.sidebar.warning("Could not load job categories.")

        # Category multiselect
        st.multiselect(
            "Categories",
            options=list(st.session_state.category_options_map.keys()),
            format_func=lambda cat_id: st.session_state.category_options_map.get(cat_id, cat_id),
            key="selected_category_ids" # Value stored in st.session_state.selected_category_ids
        )

        # Keyword input
        st.text_input("Keywords (optional)", key="search_query") # Value stored in st.session_state.search_query

        # Location input (Example - you might want a dropdown or a different widget)
        # For now, a simple text input allowing comma-separated values or a single country
        location_input_str = st.text_input("Client Locations (e.g., USA, Canada)", key="location_input_str_temp")
        # Update session state for selected_locations based on this input if needed
        # For now, we'll pass it directly or process it before sending to backend

        # Fetch Button
        if st.button("Fetch Jobs", key="fetch_button", type="primary"):
            # Retrieve current filter values from session state
            query_to_send = st.session_state.search_query
            categories_to_send = st.session_state.selected_category_ids
            
            # Process location_input_str into a list if it's not empty
            locations_to_send = []
            if location_input_str:
                locations_to_send = [loc.strip() for loc in location_input_str.split(',') if loc.strip()]
            st.session_state.selected_locations = locations_to_send # Store processed list if needed

            st.sidebar.write(f"DEBUG: Fetching with Query='{query_to_send}', Categories={categories_to_send}, Locations={locations_to_send}")

            with st.spinner("Fetching jobs from Upwork..."):
                jobs_result = fetch_jobs_from_backend(query_to_send, categories_to_send, locations_to_send)
                st.session_state.jobs_data = jobs_result # Store raw result

            if st.session_state.jobs_data and st.session_state.jobs_data.get("jobs") is not None: # Check if 'jobs' key exists
                st.success(f"Fetched {len(st.session_state.jobs_data.get('jobs', []))} jobs successfully!")
            else:
                # More detailed error if jobs_data is None or jobs key is missing
                error_info = "No data received or jobs list missing."
                if st.session_state.jobs_data and 'errors' in st.session_state.jobs_data:
                    error_info = f"API Error: {st.session_state.jobs_data['errors']}"
                elif st.session_state.jobs_data is None:
                    error_info = "Failed to fetch jobs (backend communication issue)."
                st.error(error_info)
            # st.rerun() # Consider if rerun is always needed or only on success/specific conditions

    # --- Main Dashboard Area ---
    st.header("Job Results")

    if st.session_state.jobs_data:
        jobs_list = st.session_state.jobs_data.get('jobs', []) # Safely get jobs list
        paging_info = st.session_state.jobs_data.get('paging', {})

        if jobs_list: # Check if the jobs_list is not empty
            st.write(f"Displaying {len(jobs_list)} jobs. Total matching query: {paging_info.get('total', 'N/A')}")

            # --- Download Buttons ---
            col1, col2 = st.columns(2)
            with col1:
                try:
                    json_data_to_download = json.dumps(st.session_state.jobs_data, indent=2)
                    st.download_button(
                        label="Download Raw JSON", data=json_data_to_download,
                        file_name="upwork_jobs.json", mime="application/json",
                        key="download_json_button"
                    )
                except Exception as e:
                    st.warning(f"Error preparing JSON for download: {e}")
            with col2:
                try:
                    df = pd.json_normalize(jobs_list) # Normalize only the jobs list
                    csv_data = df.to_csv(index=False)
                    st.download_button(
                        label="Download as CSV", data=csv_data,
                        file_name="upwork_jobs.csv", mime="text/csv",
                        key="download_csv_button"
                    )
                except Exception as e:
                    st.warning(f"Error preparing CSV for download: {e}")

            # --- Display Results ---
            for job_item in jobs_list:
                title = job_item.get('title', 'No Title')
                category = job_item.get('category2', 'N/A') # Assuming 'category2' from your previous structure
                with st.expander(f"{title} - {category}"):
                    st.write(f"**ID (Ciphertext):** {job_item.get('ciphertext', 'N/A')}")
                    st.write(f"**Posted:** {job_item.get('date_created', 'N/A')}")
                    st.write(f"**Skills:** {', '.join(job_item.get('skills', []))}")
                    st.markdown(f"**Description:**\n{job_item.get('snippet', 'N/A')[:500]}...")
                    if job_item.get('ciphertext'):
                        st.link_button("View Job on Upwork", f"https://www.upwork.com/jobs/{job_item.get('ciphertext')}")
                    st.write("--- Raw Data ---")
                    st.json(job_item, expanded=False)
        elif st.session_state.jobs_data.get("errors"): # If 'jobs' is empty but 'errors' exists
            st.error(f"API Error during fetch: {st.session_state.jobs_data['errors']}")
        else: # If 'jobs' is empty and no 'errors' key, means no jobs found
            st.info("No jobs found matching your criteria, or API returned no results.")
    else:
        st.info("Use the filters in the sidebar and click 'Fetch Jobs' to see results.")

else: # Not Authenticated
    st.sidebar.warning("⚠️ Not Authenticated")
    st.header("Welcome!")
    st.write("Please authenticate with your Upwork account to proceed.")
    login_url = f"{BACKEND_URL}/login"
    st.link_button("Authenticate with Upwork", login_url)
    st.info(
        """
        Clicking the button will take you to Upwork to authorize this application.
        After authorization, you will be redirected back here.
        """
    )