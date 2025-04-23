# Authentication (OAuth2)

To access Upwork API, you need to go through an authentication process. Currently, we support the OAuth 2.0 method.

You need to authenticate for all requests following the OAuth 2.0, RFC 6749.

## OAuth2 Basics

The OAuth 2.0 protocol enables websites or applications (clients) to access protected resources from a Web service (server) via an API, without requiring resource owners to disclose their service provider credentials to the clients. For more information on the OAuth 2.0 workflow process, visit the OAuth 2.0 protocol official site.

### Client ID

For each application you develop, you need to obtain new client credentials. These include a client identifier and a client shared-secret. You can request these credentials in the API Center while logged into your Upwork account (select Key Type OAuth 2.0). You will receive a key (client_id) for each client identifier and client shared-secret you request.

### Required X-Upwork-API-TenantId header

Each request requires the organization context. In order to specify on behalf of which context the request should be executed, you need to send X-Upwork-API-TenantId header. When the header is missing, the request will use the default organization of the user.

#### How X-Upwork-API-TenantId header can be used to set the Organization for the execution context

In order to get a value for the X-Upwork-API-TenantId header, you need company selector query.

Sample company selector query:

```
companySelector {
  items {
    title
    organizationId
  }
}
```

The request with X-Upwork-API-TenantId would look like:

```
curl --request POST \
  --url https://api.upwork.com/graphql \
  --header 'Authorization: bearer oauth2v2_f5*************************' \
  --header 'Content-Type: application/json' \
  --header 'X-Upwork-API-TenantId: 470*************' \
  --data '{"query":"query { \
      organization { \
      id \
      childOrganizations { \
      id \
      name \
    } \
  } \
}"}'
```

In this case query.organization and organization.childOrganizations will contain information about organization with id 470***********97.

Without the header query.organization will contain the information about 584***********76 which is the default organization for the user.

#### How the default Organization is selected when the header is not present

A default organization is one of the organizations that the user has access to. It is the same Organization that gets selected as the current Organization when a user logs in into the platform.

## Supported OAuth 2.0 Grant Types

Upwork API supports the following OAuth 2.0 grant types:

1. **Authorization Code Grant** - requires authorization request and access token request calls
2. **Implicit Grant** - requires an authorization request call
3. **Client Credentials Grant** - requires an access token request call (available for enterprise accounts only)
4. **Refresh Token Grant Type** - requires an access token request call

### Token Information

- TTL for an access token is 24 hours
- TTL for a refresh token is 2 weeks since its last usage
- Always keep your tokens private to prevent unauthorized access to user data

## Authorization Code Grant

This grant type enables you to obtain an access token by exchanging an authorization code.

### Prerequisites

| Data | Description |
|------|-------------|
| Client ID | Your client identifier key obtained from https://www.upwork.com/developer/keys/apply |
| Client Secret | Your client shared-secret key obtained from the same location |
| Callback URL | The URI to which Upwork redirects after authentication (also known as redirect URI) |

### Step 1: Obtaining an authorization code

**Endpoint:**
```
GET https://www.upwork.com/ab/account-security/oauth2/authorize
```

**Parameters:**
- `response_type` (required, string): Use "code" for Authorization Code Grant
- `client_id` (required, string): Your Client ID
- `redirect_uri` (required, string): Redirect URI matching the callback in key settings

**Returns:**
A code in the redirect URL. Example:
```
https://upwork.com/ab/messages/rooms/?code=b094053c2892cb819942e2d01e7237e7
```

### Step 2: Obtaining an access token

**Endpoint:**
```
POST https://www.upwork.com/api/v3/oauth2/token
```

**Parameters:**
- `grant_type` (required, string): Use "authorization_code"
- `client_id` (required, string): Your Client ID
- `client_secret` (required, string): Your Client Secret
- `code` (required, string): Authorization code received during authorization
- `redirect_uri` (required, string): Redirect URI matching the callback in key settings

**Returns:**
Access token and TTL. Example:
```
/#access_token=abcdefghijklmnopqrstuvwxyz&expires_in=86399
```

## Implicit Grant

This grant type enables you to obtain an access token without obtaining an authorization code first.

### Prerequisites

| Data | Description |
|------|-------------|
| Client ID | Your client identifier key obtained from https://www.upwork.com/developer/keys/apply |
| Callback URL | The URI to which Upwork redirects after authentication |

### Step 1: Obtaining an access token

**Endpoint:**
```
GET https://www.upwork.com/ab/account-security/oauth2/authorize
```

**Parameters:**
- `response_type` (required, string): Use "token" for Implicit Grant
- `client_id` (required, string): Your Client ID
- `redirect_uri` (required, string): Redirect URI matching the callback in key settings

**Returns:**
Access token and TTL directly in the redirect URI. Example:
```
/#access_token=abcdefghijklmnopqrstuvwxyz&expires_in=86399
```

## Client Credentials Grant

This grant type enables server-to-server authentication and is available for enterprise accounts only.

### Prerequisites

| Data | Description |
|------|-------------|
| Client ID | Your client identifier key obtained from https://www.upwork.com/developer/keys/apply |
| Client Secret | Your client shared-secret key obtained from the same location |

### Step 1: Obtaining an access token

**Endpoint:**
```
POST https://www.upwork.com/api/v3/oauth2/token
```

**Parameters:**
- `grant_type` (required, string): Use "client_credentials"
- `client_id` (required, string): Your Client ID
- `client_secret` (required, string): Your Client Secret

**Returns:**
JSON response with access token and TTL. Example:
```json
{
  "access_token": "oauth2v2_584006c0ef4f69fd8278c7769da6ff43",
  "token_type": "Bearer",
  "expires_in": 86400
}
```

## Refresh Token Grant Type

This grant type enables you to exchange a refresh token for a new access token when the access token has expired.

### Prerequisites

| Data | Description |
|------|-------------|
| Client ID | Your client identifier key obtained from https://www.upwork.com/developer/keys/apply |
| Client Secret | Your client shared-secret key obtained from the same location |
| Refresh Token | A valid refresh token from previous authentication |

### Step 1: Obtaining a new access token

**Endpoint:**
```
POST https://www.upwork.com/api/v3/oauth2/token
```

**Parameters:**
- `grant_type` (required, string): Use "refresh_token"
- `client_id` (required, string): Your Client ID
- `client_secret` (required, string): Your Client Secret
- `refresh_token` (required, string): A valid refresh token

**Returns:**
JSON response with refreshed tokens and TTL. Example:
```json
{
  "access_token": "oauth2v2_daedc8c79a4d5f80b88b2ce953772a0f",
  "refresh_token": "oauth2v2_e8ae4feb6b8d10693d8cff420351461a",
  "token_type": "Bearer",
  "expires_in": 86400
}
```

## Service Accounts

Service accounts are specific to a service or application and are designed to run applications. They help you communicate with multiple applications and are useful for fetching information about multiple users in a company.

**Important notes:**
- Service accounts are available only for enterprise accounts in Upwork
- They should not be used to perform write operations
- You must apply for the client credentials key
- After creation, appropriate scopes and permissions must be assigned to the service account
