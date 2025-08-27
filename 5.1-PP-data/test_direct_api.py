import httpx
import json

# Test the API directly
def test_api_direct():
    base_url = "https://api.test.computesphere.com/api/v1"
    headers = {
        "accept": "application/json, text/plain, */*",
        "authorization": "Bearer eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJmdWp1NVVTWXU2eUlZcHhKRXhKOUh3a1diSGZON09fRFFRRWZTbUtNQmNrIn0.eyJleHAiOjE3NTYzMDIxMjksImlhdCI6MTc1NjI5MTU2OCwiYXV0aF90aW1lIjoxNzU2MjY2MTI5LCJqdGkiOiJvbnJ0YWM6YzgzNmEwOTEtYmJjNS00MWY5LWI5ODctM2M0NTJlYzQwNDQ1IiwiaXNzIjoiaHR0cHM6Ly9hY2NvdW50cy50ZXN0LmNvbXB1dGVzcGhlcmUuY29tL3JlYWxtcy9jb21wdXRlc3BoZXJlIiwiYXVkIjpbInJlYWxtLW1hbmFnZW1lbnQiLCJhY2NvdW50Il0sInN1YiI6IjM3NWFhNTNhLTBhNjQtNDk1YS1iNTRlLWQ1YTM5YmE4ZDhjYiIsInR5cCI6IkJlYXJlciIsImF6cCI6ImNvbXB1dGVzcGhlcmVfY2xpZW50Iiwic2lkIjoiYjUwYmJjYmUtOTVjNS00ZmQ4LWEyYjQtZDlhMzA2OTMwNGJkIiwiYWNyIjoiMCIsImFsbG93ZWQtb3JpZ2lucyI6WyJodHRwczovL2NvbnNvbGUuYWRtaW4udGVzdC5jb21wdXRlc3BoZXJlLmNvbSIsImh0dHBzOi8vY29uc29sZS50ZXN0LmNvbXB1dGVzcGhlcmUuY29tIiwiaHR0cDovL2xvY2FsaG9zdDozMDAwIiwiaHR0cDovL2xvY2FsaG9zdDo2MDAwIl0sInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJkZWZhdWx0LXJvbGVzLWNvbXB1dGVzcGhlcmUiLCJvZmZsaW5lX2FjY2VzcyIsInVtYV9hdXRob3JpemF0aW9uIl19LCJyZXNvdXJjZV9hY2Nlc3MiOnsicmVhbG0tbWFuYWdlbWVudCI6eyJyb2xlcyI6WyJ2aWV3LXJlYWxtIiwidmlldy1pZGVudGl0eS1wcm92aWRlcnMiLCJtYW5hZ2UtaWRlbnRpdHktcHJvdmlkZXJzIiwiaW1wZXJzb25hdGlvbiIsInJlYWxtLWFkbWluIiwiY3JlYXRlLWNsaWVudCIsIm1hbmFnZS11c2VycyIsInF1ZXJ5LXJlYWxtcyIsInZpZXctYXV0aG9yaXphdGlvbiIsInF1ZXJ5LWNsaWVudHMiLCJxdWVyeS11c2VycyIsIm1hbmFnZS1ldmVudHMiLCJtYW5hZ2UtcmVhbG0iLCJ2aWV3LWV2ZW50cyIsInZpZXctdXNlcnMiLCJ2aWV3LWNsaWVudHMiLCJtYW5hZ2UtYXV0aG9yaXphdGlvbiIsIm1hbmFnZS1jbGllbnRzIiwicXVlcnktZ3JvdXBzIl19LCJhY2NvdW50Ijp7InJvbGVzIjpbIm1hbmFnZS1hY2NvdW50Iiwidmlldy1hcHBsaWNhdGlvbnMiLCJ2aWV3LWNvbnNlbnQiLCJ2aWV3LWdyb3VwcyIsIm1hbmFnZS1hY2NvdW50LWxpbmtzIiwibWFuYWdlLWNvbnNlbnQiLCJkZWxldGUtYWNjb3VudCIsInZpZXctcHJvZmlsZSJdfX0sInNjb3BlIjoib3BlbmlkIGVtYWlsIHByb2ZpbGUiLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwibmFtZSI6InVtZXNoLmtoYXRpd2FkYUBiZXJyeWJ5dGVzLmNvbSB1bWVzaC5raGF0aXdhZGFAYmVycnlieXRlcy5jb20iLCJwcmVmZXJyZWRfdXNlcm5hbWUiOiJ1bWVzaC5raGF0aXdhZGFAYmVycnlieXRlcy5jb20iLCJnaXZlbl9uYW1lIjoidW1lc2gua2hhdGl3YWRhQGJlcnJ5Ynl0ZXMuY29tIiwiZmFtaWx5X25hbWUiOiJ1bWVzaC5raGF0aXdhZGFAYmVycnlieXRlcy5jb20iLCJlbWFpbCI6InVtZXNoLmtoYXRpd2FkYUBiZXJyeWJ5dGVzLmNvbSJ9.vAsTWOCklXP3fPioQCoJgscQi6NArAqolCWcR5YIX_yUZDPDSb8ClOEjuWlakQAjVqlAbcpYagy8Cgi_3QvWUW8sR8FO3zKyCXmoMLjutJ48ldyRUz6avGjUW1gTbuMbL772jcqX26ORVOgQGlFvoUFcQLAFMyP82AwFxS747i6DGPRMta7BKbD1Dqbc-auK4UKXddhdKY7GBl8d19q90YS8fXe5FcaiTlA5UJfAWJcGP4nPNUJM3hrVYPLlIE7gnbyt75J4Fj-IJIICekTWZ5y_KQMigui8PcI-pmmRN6IuGrqJf3PmtF4-UcCCLfAqOfyp2XZFVxbv4hCWD0uVng",
        "Content-Type": "application/json"
    }
    
    try:
        print("Testing direct API call...")
        
        # Test home endpoint first
        # with httpx.Client(timeout=10.0) as client:
        #     response = client.get(f"{base_url}/", headers=headers)
        #     print(f"Home endpoint status: {response.status_code}")
        #     print(f"Home response: {response.text[:200]}...")
            
        # Test accounts endpoint
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{base_url}/accounts", headers=headers)
            print(f"Accounts endpoint status: {response.status_code}")
            print(f"Accounts response: {response.text[:200]}...")
            
    except httpx.TimeoutException:
        print("❌ Timeout - API server not responding")
    except httpx.ConnectError:
        print("❌ Connection error - Cannot reach API server")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_api_direct()
