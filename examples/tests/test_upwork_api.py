import unittest
from unittest.mock import patch, MagicMock
import os
import asyncio

# Similar to above, ensure backend.upwork_api can be imported
from backend.upwork_api import get_authenticated_client, search_upwork_jobs_gql
from backend.main import token_cache # To manipulate for testing get_authenticated_client

# Helper to run async tests if not using a dedicated async test runner
def async_test(coro):
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro(*args, **kwargs))
        finally:
            loop.close()
    return wrapper

class TestUpworkApi(unittest.TestCase):

    def setUp(self):
        token_cache.clear()
        # Set necessary env vars for get_authenticated_client
        os.environ["UPWORK_CLIENT_ID"] = "test_client_id"
        os.environ["UPWORK_CLIENT_SECRET"] = "test_client_secret"
        os.environ["UPWORK_REDIRECT_URI"] = "http://localhost/callback"
        # For get_organization_tenant_id mock or actual call if not mocked broadly
        os.environ["UPWORK_DEFAULT_TENANT_ID"] = "test_tenant_id"


    def tearDown(self):
        token_cache.clear()

    @patch('upwork.config.Config') # Mock the Config class from python-upwork
    @patch('upwork.client.Client') # Mock the Client class from python-upwork
    def test_get_authenticated_client_retrieves_tokens_from_cache(self, MockClient, MockConfig):
        token_cache["access_token"] = "cached_access_token"
        token_cache["refresh_token"] = "cached_refresh_token"

        mock_config_instance = MockConfig.return_value
        mock_client_instance = MockClient.return_value

        client = get_authenticated_client()

        MockConfig.assert_called_once_with({
            "client_id": "test_client_id", "client_secret": "test_client_secret",
            "redirect_uri": "http://localhost/callback",
            "token": {"access_token": "cached_access_token", "refresh_token": "cached_refresh_token"}
        })
        MockClient.assert_called_once_with(mock_config_instance)
        self.assertEqual(client, mock_client_instance)

    @patch('backend.upwork_api.get_authenticated_client')
    @patch('backend.upwork_api.get_organization_tenant_id') # Keep it as a standard mock
    @async_test
    async def test_search_upwork_jobs_gql_includes_url_and_rate(self, mock_get_tenant_id, mock_get_auth_client):
        # Mock the authenticated client and its post method
        mock_client = MagicMock()
        # Configure the mock client's post method to be an async function if it's awaited in the original code
        # For this test, client.post is synchronous as per python-upwork library's typical usage with .epoint

        mock_gql_response_hourly = {
            "data": {
                "marketplaceJobPostingsSearch": {
                    "totalCount": 1,
                    "edges": [
                        {
                            "node": {
                                "title": "Test Job Hourly",
                                "ciphertext": "job_ciphertext_hourly",
                                "description": "Test description hourly",
                                "skills": [{"name": "python"}],
                                "createdDateTime": "2023-01-01T00:00:00Z",
                                "category": "Web Development",
                                "subcategory": "Web Programming",
                                "job": {"contractTerms": {"contractType": "HOURLY"}},
                                "client": {
                                    "location": {"country": "USA"}, "totalFeedback": 4.5, "totalPostedJobs": 10,
                                    "totalHires": 5, "verificationStatus": "VERIFIED", "totalReviews": 8
                                },
                                "duration": "3-6 months",
                                "amount": None,
                                "hourlyBudget": {"currencyCode": "USD", "amount": 50.00}
                            }
                        }
                    ],
                    "pageInfo": {"endCursor": "next_page_cursor_hourly", "hasNextPage": True}
                }
            }
        }

        mock_gql_response_fixed = {
            "data": {
                "marketplaceJobPostingsSearch": {
                    "totalCount": 1,
                    "edges": [
                        {
                            "node": {
                                "title": "Test Job Fixed",
                                "ciphertext": "job_ciphertext_fixed",
                                "description": "Test description fixed",
                                "skills": [{"name": "django"}],
                                "createdDateTime": "2023-01-02T00:00:00Z",
                                "category": "Web Development",
                                "subcategory": "Full Stack",
                                "job": {"contractTerms": {"contractType": "FIXED_PRICE"}},
                                "client": {
                                    "location": {"country": "CAN"}, "totalFeedback": 5.0, "totalPostedJobs": 2,
                                    "totalHires": 1, "verificationStatus": "VERIFIED", "totalReviews": 1
                                },
                                "duration": "1 month",
                                "amount": {"currencyCode": "USD", "amount": 1000.00},
                                "hourlyBudget": None
                            }
                        }
                    ],
                    "pageInfo": {"endCursor": "next_page_cursor_fixed", "hasNextPage": False}
                }
            }
        }

        # Mock get_authenticated_client to return our mock_client
        mock_get_auth_client.return_value = mock_client

        # Mock get_organization_tenant_id to be an async coroutine function
        # and return a specific value when awaited.
        async def async_mock_tenant_id():
            return "test_tenant_id"
        mock_get_tenant_id.side_effect = async_mock_tenant_id


        # Test Hourly Job
        mock_client.post.return_value = mock_gql_response_hourly
        result_hourly = await search_upwork_jobs_gql(query="test hourly")

        self.assertIn("jobs", result_hourly)
        self.assertEqual(len(result_hourly["jobs"]), 1)
        job_hourly = result_hourly["jobs"][0]

        self.assertEqual(job_hourly["title"], "Test Job Hourly")
        self.assertEqual(job_hourly["id"], "job_ciphertext_hourly")
        self.assertEqual(job_hourly["url"], "https://www.upwork.com/jobs/job_ciphertext_hourly")
        self.assertEqual(job_hourly["rate"], "50.0 USD/hr") # Assuming amount is float 50.00 -> 50.0

        # Test Fixed Price Job
        mock_client.post.return_value = mock_gql_response_fixed
        result_fixed = await search_upwork_jobs_gql(query="test fixed")

        self.assertIn("jobs", result_fixed)
        self.assertEqual(len(result_fixed["jobs"]), 1)
        job_fixed = result_fixed["jobs"][0]

        self.assertEqual(job_fixed["title"], "Test Job Fixed")
        self.assertEqual(job_fixed["id"], "job_ciphertext_fixed")
        self.assertEqual(job_fixed["url"], "https://www.upwork.com/jobs/job_ciphertext_fixed")
        self.assertEqual(job_fixed["rate"], "1000.0 USD") # Assuming amount is float 1000.00 -> 1000.0


if __name__ == '__main__':
    # This structure allows running tests with `python examples/tests/test_upwork_api.py`
    # The async_test decorator helps in running async test methods.
    # For more complex scenarios or integration with FastAPI's event loop,
    # pytest with pytest-asyncio is generally preferred.
    print("Running Upwork API tests...")
    print("Consider using pytest with pytest-asyncio for more robust async test execution:")
    print("pytest examples/tests/test_upwork_api.py")
    unittest.main()
