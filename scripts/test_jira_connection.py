import os
import requests
from dotenv import load_dotenv

load_dotenv()

base_url = os.getenv("JIRA_BASE_URL")
email = os.getenv("JIRA_EMAIL")
token = os.getenv("JIRA_API_TOKEN")

# Replace this JQL with whatever query you actually want to pull tickets with
jql = "project = SCRUM ORDER BY created DESC"

response = requests.get(
    f"{base_url}/rest/api/3/search/jql",
    params={
        "jql": jql,
        "maxResults": 5,
        "fields": "summary,status,created"
    },
    auth=(email, token),
    headers={"Accept": "application/json"}
)

print("Status code:", response.status_code)

if response.status_code == 200:
    data = response.json()
    issues = data.get("issues", [])
    print(f"Tickets returned: {len(issues)}")
    for issue in issues:
        print(f"- {issue['key']}: {issue['fields']['summary']}")
    if data.get("nextPageToken"):
        print("More results available — pagination token:", data["nextPageToken"])
else:
    print("Error response:", response.text)