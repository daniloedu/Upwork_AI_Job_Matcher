# Upwork API Documentation: Jobs

## GraphQL OAuth2 scopes
| Name | Description |
|------|-------------|
| Read marketplace Job Postings | Scope to read marketplace Job Postings for enterprise user |

## Search for jobs
The search parameters mirror the options available on the site plus options to configure the format of your results.

### REST
```
GET  /api/profiles/v2/search/jobs.{format}
```

### GRAPHQL
```graphql
query marketplaceJobPostings(
  $marketPlaceJobFilter: MarketplaceJobFilter,
  $searchType: MarketplaceJobPostingSearchType,
  $sortAttributes: [MarketplaceJobPostingSearchSortAttribute]
) {
  marketplaceJobPostings(
    marketPlaceJobFilter: $marketPlaceJobFilter,
    searchType: $searchType,
    sortAttributes: $sortAttributes
  ) {
    totalCount
    edges {
      ...MarketplaceJobpostingSearchEdgeFragment
    }
    pageInfo {
      ...PageInfoFragment
    }
  }
}
```

### VARIABLES
```json
{
  "searchExpression_eq": "abc123",
  "skillExpression_eq": "xyz789",
  "titleExpression_eq": "abc123",
  "searchTerm_eq": {
    "andTerms_all": ["xyz789"],
    "orTerms_any": ["abc123"],
    "exactTerms_any": ["xyz789"],
    "excludeTerms_any": ["abc123"]
  },
  "categoryIds_any": ["4"],
  "subcategoryIds_any": ["4"],
  "occupationIds_any": [4],
  "ontologySkillIds_all": [4],
  "sinceId_eq": "abc123",
  "maxId_eq": "abc123",
  "jobType_eq": "HOURLY",
  "duration_eq": "WEEK",
  "workload_eq": "FULL_TIME",
  "clientHiresRange_eq": {"rangeStart": 987, "rangeEnd": 987},
  "clientFeedBackRange_eq": {"rangeStart": 987.65, "rangeEnd": 123.45},
  "budgetRange_eq": {"rangeStart": 987, "rangeEnd": 987},
  "verifiedPaymentOnly_eq": false,
  "previousClients_eq": true,
  "experienceLevel_eq": "ENTRY_LEVEL",
  "locations_any": ["abc123"],
  "cityId_any": ["xyz789"],
  "zipCodeId_any": ["xyz789"],
  "radius_eq": 987,
  "areaId_any": ["xyz789"],
  "timezone_eq": "xyz789",
  "usState_eq": "abc123",
  "daysPosted_eq": 987,
  "jobPostingAccess": "PUBLIC_INDEX",
  "ptcIds_any": [4],
  "ptcOnly_eq": true,
  "enterpriseOnly_eq": true,
  "proposalRange_eq": {"rangeStart": 987, "rangeEnd": 987},
  "pagination_eq": {"after": "abc123", "first": 987},
  "area_eq": {"latitude": 987.65, "longitude": 123.45, "radius": 123.45},
  "preserveFacet_eq": "abc123",
  "userLocationMatch_eq": true,
  "visitorCountry_eq": "abc123",
  "sortAttributes": [{
    "attribute": "RECENCY",
    "direction": "DESC"
  }]
}
```

## `marketplaceJobPostingsSearch`

Search Marketplace Jobs and get their relevant details. `searchType` determines the context and method of the job search being executed. 

Note: searchType value will be ignored and always set to USER_JOBS_SEARCH, utilized when performing a user-initiated job search.

### Response
Returns a `MarketplaceJobPostingSearchConnection`

### Arguments
| Name | Description |
|------|-------------|
| `marketPlaceJobFilter` | `MarketplaceJobPostingsSearchFilter` |
| `searchType` | `MarketplaceJobPostingSearchType` |
| `sortAttributes` | `[MarketplaceJobPostingSearchSortAttribute]` |

```graphql
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
      ...MarketplaceJobpostingSearchEdgeFragment
    }
    pageInfo {
      ...PageInfoFragment
    }
  }
}
```

### VARIABLES
```json
{
  "marketPlaceJobFilter": "MarketplaceJobPostingsSearchFilter",
  "searchType": "USER_JOBS_SEARCH",
  "sortAttributes": [{
    "attribute": "RECENCY",
    "direction": "DESC"
  }]
}
```

### RESPONSE
```json
{
  "data": {
    "marketplaceJobPostingsSearch": {
      "totalCount": 987,
      "edges": ["MarketplaceJobpostingSearchEdge"],
      "pageInfo": "PageInfo"
    }
  }
}
```

## Field Mapping between REST and GraphQL

| REST Field | GraphQL Path | Description |
|------------|--------------|-------------|
| q | marketPlaceJobFilter.searchExpression_eq | The search query. At least one of the `q`, `title`, `skill` parameters should be specified. |
| title | marketPlaceJobFilter.titleExpression_eq | Searches for the title in the freelancer's profile. At least one of the `q`, `title`, `skill` parameters should be specified. |
| skills | marketPlaceJobFilter.skillExpression_eq | Searches for skills of freelancer's profile. At least one of the `q`, `title`, `skill` parameters should be specified. |
| category2 | marketPlaceJobFilter.categoryIds_any | The category (V2) of the freelancer's profile. Use Metadata resource to get it. You can get it via Metadata Category (v2) resource. |
| subcategory2 | marketPlaceJobFilter.subcategoryIds_any | The subcategory of the job according to the list of Categories 2.0. Example: `Web & Mobile Development`. You can get it via Metadata Category (v2) resource. |
| duration | marketPlaceJobFilter.duration_eq | The duration of the job. Valid values: week, month, semester, ongoing |
| workload | marketPlaceJobFilter.workload_eq | Indicates the workload for the job. Valid values: as_needed, part_time, full_time |
| client_feedback | marketPlaceJobFilter.clientFeedBackRange_eq | A number or range used to filter the search by jobs posted by clients with a rating equal to, more or less than, or within the values provided. If the value is `None`, then jobs from clients without rating are returned. |
| client_hires | marketPlaceJobFilter.clientHiresRange_eq | A number or range used to filter the search by clients with a number of past hires equal to, more or less than, or within the values provided. |
| budget | marketPlaceJobFilter.budgetRange_eq | A number or range used to filter the search by jobs having a budget equal to, more or less than, or within the values provided. |
| days_posted | marketPlaceJobFilter.daysPosted_eq | Number of days since the job was posted. |
| paging | marketPlaceJobFilter.pagination_eq | Pagination, formed as `$offset;$count`. Page size is restricted to be <= 50. Example: page=20;10. |
| sort | sortAttributes | Sorts the search results by the value provided. Example: `sort=create_time%20desc`. |

## Response Field Mapping

| REST Field | GraphQL Path | Description |
|------------|--------------|-------------|
| budget | Varies by job_type:<br>- fixed --> response.edges.node.amount<br>- hourly --> range (response.edges.node.hourlyBudgetMin - response.edges.node.hourlyBudgetMax) | Budget |
| category2 | response.edges.node.category | Category |
| client.country | response.edges.node.client.location.country | Client Country |
| client.feedback | response.edges.node.client.totalFeedback | Client Feedback |
| client.jobs_posted | response.edges.node.client.totalPostedJobs | Client Jobs Posted |
| client.past_hires | response.edges.node.client.totalHires | Client Past Hires |
| client.payment_verification_status | response.edges.node.client.verificationStatus | Client Payment Verification Status |
| client.reviews_count | response.edges.node.client.totalReviews | Client Reviews Count |
| date_created | response.edges.node.createdDateTime | Date Created |
| duration | response.edges.node.duration | Duration |
| id | response.edges.node.ciphertext | ID (Legacy) |
| job_status | #deprecated | Job Status |
| job_type | response.edges.node.job.contractTerms.contractType | Job Type |
| skills | response.edges.node.skills | Skills |
| snippet | response.edges.node.description | Snippet |
| subcategory2 | response.edges.node.subcategory | Subcategory |
| title | response.edges.node.title | Title |
| url | Missing, but can be constructed using ${(stage.)?upwork.com/jobs/ + response.edges.node.ciphertext} | URL |
| workload | response.edges.node.job.contractTerms.hourlyContractTerms.engagementType | Workload |
