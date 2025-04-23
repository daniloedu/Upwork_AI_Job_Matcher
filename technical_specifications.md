# Product Specification: AI-Powered Upwork Opportunity Matcher

## 1. Overview
A single-user web application that fetches Upwork job listings on demand or daily, analyzes them against the user's profile using AI, and provides filtered, scored opportunities. Data can be exported in JSON and CSV formats. The initial frontend is built with Streamlit; a React-based UI may follow in future versions.

## 2. Architecture

```
Streamlit UI  ↔  FastAPI Backend  ↔  Upwork API
                                   ↳  PostgreSQL (jobs, filters, profile)
                                   ↳  CrewAI Agent (optional AI filtering)
```

### 2.1 Environment & Security
* All sensitive credentials (API keys, OAuth secrets) stored in a `.env` file.
* Enforce best security practices: never commit secrets, use `.gitignore`, validate inputs.
* Follow OWASP guidelines and secure HTTP headers on all routes.

## 3. Features & User Stories

| ID | As a user, I want to… | Acceptance Criteria |
|----|----------------------|-------------------|
| U1 | Authenticate via Upwork OAuth | OAuth2 flow completes, tokens stored in `.env`, status shown. |
| U2 | Select job categories and client locations dynamically | Categories fetched via API; location dropdown populated. |
| U3 | Fetch and download raw job data | JSON/CSV files generated, downloadable in UI. |
| U4 | View a summary of my profile & activity | Display basic profile info, past applications, catalog. |
| U5 | (Optional) Run AI filter via CrewAI agent | Toggle AI filter; results scored & ranked. |

## 4. Data Ingestion & Filters
* **Dynamic Filters**: Fetch categories from Upwork API `/profiles/v2/metadata/categories` endpoint; cache locally.
* **Location Filters**: Allow filtering by remote/on-site and client country (ISO code).
* **Export**: Provide both JSON and CSV exports immediately after fetch.

## 5. Data Model

```sql
-- jobs_raw: stores original JSON payload
CREATE TABLE jobs_raw (
  id TEXT PRIMARY KEY,
  raw JSONB,
  scraped_at TIMESTAMP DEFAULT NOW()
);

-- jobs_export: stores parsed, flat data for CSV
CREATE TABLE jobs_export (
  id TEXT PRIMARY KEY,
  title TEXT,
  category TEXT,
  location TEXT,
  budget_range TEXT,
  posted_date DATE,
  scraped_at TIMESTAMP
);

-- user_profile: stores minimal profile overview
CREATE TABLE user_profile (
  user_id TEXT PRIMARY KEY,
  name TEXT,
  title TEXT,
  past_applications INT,
  catalog_items INT,
  last_updated TIMESTAMP
);
```

## 6. Frontend (Streamlit)
* **Authentication Page**: Upwork OAuth2 login button.
* **Filter Panel**: Dropdowns for dynamic categories and locations.
* **Data Panel**: Buttons to `Fetch Jobs`, `Export JSON`, `Export CSV`.
* **Profile Panel**: Show basic profile metrics: opportunities viewed, applications sent, project catalog count.
* **AI Filter Toggle**: Checkbox to run CrewAI scoring; display results with score & summary.

## 7. Backend (FastAPI)
* **Auth**: `/oauth/callback` endpoint to handle Upwork tokens.
* **Endpoints**:
   * `GET /filters/categories`
   * `GET /filters/locations`
   * `POST /jobs/fetch`
   * `GET /jobs/export/json`
   * `GET /jobs/export/csv`
   * `GET /profile/overview`
   * `POST /ai/filter` (optional)
* **Background Tasks**: Use FastAPI `BackgroundTasks` for on-demand fetch.

## 8. AI Integration (CrewAI)
* **Trigger**: Only if user toggles "Run AI Filter".
* **Input**: Raw JSON list of jobs + user profile summary.
* **Output**: Score (0–100), brief rationale, matched keywords.
* **Prompt Configuration**: Stored in `prompts.yaml`, editable without code deploy.

## 9. Deployment & Maintenance
* **Containerization**: Dockerfile with Python 3.11-slim.
* **Secrets**: Load from `.env`; use `python-dotenv`.
* **Hosting**: Render, Fly.io, or AWS Fargate.
* **Monitoring**: Health check endpoint (`/healthz`). Logging with structured JSON.
