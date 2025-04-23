# frontend/app.py
import streamlit as st
import requests
import os
import time
import json # For JSON download
import pandas as pd # For CSV download
from io import StringIO # For CSV download
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv() # Load .env if needed, though frontend mainly interacts via backend
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000") # Get backend URL

# --- Helper Function ---
def check_backend_auth_status():
    """Checks if the backend reports authentication tokens are present."""
    try:
        response = requests.get(f"{BACKEND_URL}/auth/status")
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        is_authenticated = response.json().get("authenticated", False)
        st.session_state['authenticated'] = is_authenticated # Update session state directly
        return is_authenticated
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to backend: {e}")
        st.session_state['authenticated'] = False # Ensure state is false on error
        return False

# Function to fetch categories
@st.cache_data(ttl=3600) # Cache for 1 hour
def get_categories():
    try:
        response = requests.get(f"{BACKEND_URL}/filters/categories")
        response.raise_for_status()
        # Backend now returns list of dicts: [{'id': ..., 'label': ...}]
        categories_data = response.json()
        return categories_data if isinstance(categories_data, list) else []
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching categories: {e}")
        return []
    except Exception as e:
        st.error(f"An error occurred processing categories: {e}")
        return []

# Function to fetch jobs
def fetch_jobs_from_backend(query: str, category_ids: list):
    payload = {
        "query": query if query else None,
        "category_ids": category_ids if category_ids else None # Pass IDs now
    }
    try:
        response = requests.post(f"{BACKEND_URL}/jobs/fetch", json=payload)
        response.raise_for_status()
        return response.json() # Expecting dict with 'jobs' and 'paging'
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching jobs: {e.response.text if e.response else e}")
        return None
    except Exception as e:
        st.error(f"An error occurred fetching jobs: {e}")
        return None

# --- Streamlit App ---
st.set_page_config(layout="wide")
st.title("AI-Powered Upwork Opportunity Matcher")

# Initialize session state keys if they don't exist
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'jobs_data' not in st.session_state:
    st.session_state['jobs_data'] = None
if 'categories_list' not in st.session_state:
    st.session_state['categories_list'] = []
if 'category_options' not in st.session_state:
    st.session_state['category_options'] = {}
if 'selected_category_ids' not in st.session_state:
    st.session_state['selected_category_ids'] = []

# --- Authentication Check ---
# Initialize session state if it doesn't exist
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False # Default to not authenticated
    # Perform initial check only if not already authenticated
    check_backend_auth_status()

# Check for callback status from URL query parameters
query_params = st.query_params
auth_status = query_params.get("auth_status")
refresh_needed = query_params.get("refresh")

if auth_status == "success":
    st.success("Authentication successful! Tokens saved automatically.")
    if refresh_needed == "true":
        st.info("Checking backend status... Please wait a moment.")
        # Give backend/filesystem a moment before checking
        time.sleep(1)
        # Clear only the refresh param, keep auth_status for potential re-display if check fails
        query_params.pop("refresh", None)
        st.query_params = query_params # Update query params in Streamlit
        check_backend_auth_status() # Re-check auth status
        st.rerun() # Rerun to reflect the potentially updated state
    # If already authenticated, just clear params
    elif st.session_state.get('authenticated'):
         query_params.clear()
         st.query_params = query_params
         # Don't need to rerun if already showing dashboard

elif auth_status == "error":
    message = query_params.get("message", "Unknown error during authentication.")
    st.error(f"Authentication failed: {message.replace('_', ' ')}")
    st.session_state['authenticated'] = False
    query_params.clear()
    st.query_params = query_params
    # Rerun might be needed if switching from dashboard to login
    st.rerun()

# --- Main Display Logic ---
if st.session_state.get('authenticated', False):
    st.sidebar.success("✅ Authenticated with Upwork")
    st.header("Dashboard")
    st.write("Authentication successful. You can now fetch jobs and use other features.")

    # Placeholder for future components (Filter Panel, Data Panel, Profile Panel)
    st.subheader("Coming Soon:")
    st.markdown("- Filter Panel (Categories, Locations)")
    st.markdown("- Data Panel (Fetch Jobs, Export)")
    st.markdown("- Profile Panel")
    st.markdown("- AI Filter Toggle")

    # --- Filters Sidebar ---
    with st.sidebar:
        st.header("Filters")
        # Fetch and cache categories
        if 'categories_list' not in st.session_state or not st.session_state['categories_list']:
             st.session_state['categories_list'] = get_categories()
             # Create a mapping for display
             st.session_state['category_options'] = {cat['id']: cat['label'] for cat in st.session_state['categories_list']}
        
        selected_cat_ids = [] # Default
        # Ensure categories are loaded before showing multiselect
        if st.session_state.get('category_options'):
            # Use the category mapping for options and display format
            selected_cat_ids = st.multiselect(
                "Categories", 
                options=list(st.session_state['category_options'].keys()), 
                format_func=lambda cat_id: st.session_state['category_options'].get(cat_id, cat_id),
                key="selected_category_ids" # Use key for state management
            )
        else:
            st.warning("Could not load categories.")
            
        search_query = st.text_input("Keywords (optional)", key="search_query")

        if st.button("Fetch Jobs", key="fetch_button"):
            with st.spinner("Fetching jobs from Upwork..."):
                # Pass the selected IDs to the backend
                jobs_result = fetch_jobs_from_backend(st.session_state.search_query, st.session_state.selected_category_ids)
                st.session_state['jobs_data'] = jobs_result # Store raw result
            if st.session_state['jobs_data']:
                st.success("Jobs fetched successfully!")
            else:
                st.error("Failed to fetch jobs.")
            
    # --- Main Dashboard Area ---
    st.header("Job Results")

    if st.session_state['jobs_data']:
        jobs = st.session_state['jobs_data'].get('jobs', [])
        paging = st.session_state['jobs_data'].get('paging', {})
        
        st.write(f"Showing {len(jobs)} jobs.") 
        # Add paging info if needed: st.write(f"Paging: {paging}")

        # --- Download Buttons ---
        col1, col2 = st.columns(2)
        with col1:
            json_data = json.dumps(st.session_state['jobs_data'], indent=2)
            st.download_button(
                label="Download Raw JSON",
                data=json_data,
                file_name="upwork_jobs.json",
                mime="application/json",
                key="download_json"
            )
        
        with col2:
            if jobs: # Only show CSV download if jobs exist
                try:
                    # Flatten the data for CSV - adjust based on needed columns
                    # This is a basic flattening, might need refinement
                    df = pd.json_normalize(jobs)
                    csv_data = df.to_csv(index=False)
                    st.download_button(
                        label="Download as CSV",
                        data=csv_data,
                        file_name="upwork_jobs.csv",
                        mime="text/csv",
                        key="download_csv"
                    )
                except Exception as e:
                    st.warning(f"Could not generate CSV: {e}")
            else:
                 st.button("Download as CSV", disabled=True, key="download_csv_disabled") 

        # --- Display Results ---
        # Display basic info - customize as needed
        for job in jobs:
            with st.expander(f"{job.get('title', 'No Title')} - {job.get('category2', 'N/A')}"):
                st.write(f"**ID:** {job.get('id', 'N/A')}")
                st.write(f"**Budget:** {job.get('budget', {}).get('amount', 'N/A')} {job.get('budget', {}).get('currencyCode', '')}")
                st.write(f"**Posted:** {job.get('date_created', 'N/A')}")
                st.write(f"**Skills:** {', '.join(job.get('skills', []))}")
                st.markdown(f"**Description:**\n{job.get('snippet', 'N/A')[:500]}...") # Show snippet
                st.link_button("View Job on Upwork", f"https://www.upwork.com/jobs/{job.get('ciphertext', '')}") 
                # Show raw job data for debugging/completeness
                st.write("Raw Data:")
                st.json(job, expanded=False)
    else:
        st.info("Use the filters in the sidebar and click 'Fetch Jobs' to see results.")

else:
    st.sidebar.warning("⚠️ Not Authenticated")
    st.header("Welcome!")
    st.write("Please authenticate with your Upwork account to proceed.")

    # Provide the login link/button
    login_url = f"{BACKEND_URL}/login"
    # Using st.link_button is clean for redirects initiated by user click
    st.link_button("Authenticate with Upwork", login_url)

    st.info(
        """
        Clicking the button will take you to Upwork to authorize this application.
        After authorization, you will be redirected back here, and the tokens
        will be saved automatically to your `.env` file.
        You may need to **restart the backend server** for it to use the new tokens.
        """
    )