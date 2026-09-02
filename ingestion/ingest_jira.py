import os
import requests
from dotenv import load_dotenv
from common import embed_and_upsert

load_dotenv()

BASE_URL = os.getenv("JIRA_BASE_URL")
EMAIL = os.getenv("JIRA_EMAIL")
TOKEN = os.getenv("JIRA_API_TOKEN")

PAGE_SIZE = 50


def fetch_all_issues(jql):
    all_issues = []
    next_page_token = None

    while True:
        params = {
            "jql": jql,
            "maxResults": PAGE_SIZE,
            "fields": "summary,description,status,priority,issuetype,created,updated,comment"
        }
        if next_page_token:
            params["nextPageToken"] = next_page_token

        response = requests.get(
            f"{BASE_URL}/rest/api/3/search/jql",
            params=params,
            auth=(EMAIL, TOKEN),
            headers={"Accept": "application/json"}
        )

        if response.status_code != 200:
            print(f"Error fetching issues: {response.status_code} - {response.text}")
            break

        data = response.json()
        issues = data.get("issues", [])
        all_issues.extend(issues)
        print(f"Fetched {len(all_issues)} tickets so far...")

        next_page_token = data.get("nextPageToken")
        if not next_page_token or not issues:
            break

    return all_issues


def extract_text_from_adf(adf_node):
    """JIRA cloud stores descriptions/comments in Atlassian Document Format (nested JSON).
    This walks the structure and pulls out plain text."""
    if not adf_node:
        return ""
    text_parts = []

    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "text":
                text_parts.append(node.get("text", ""))
            for child in node.get("content", []):
                walk(child)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(adf_node)
    return " ".join(text_parts)


def build_chunk_for_issue(issue):
    fields = issue["fields"]
    key = issue["key"]

    summary = fields.get("summary", "")
    description = extract_text_from_adf(fields.get("description"))
    status = fields.get("status", {}).get("name", "")
    priority = (fields.get("priority") or {}).get("name", "")
    issue_type = fields.get("issuetype", {}).get("name", "")
    created = fields.get("created", "")
    updated = fields.get("updated", "")

    text = (
        f"JIRA Ticket: {key}\n"
        f"Type: {issue_type} | Status: {status} | Priority: {priority}\n"
        f"Summary: {summary}\n"
        f"Description: {description}\n"
        f"Created: {created} | Updated: {updated}"
    )

    return {
        "text": text,
        "payload": {
            "source_type": "jira_ticket",
            "ticket_id": key,
            "status": status,
            "priority": priority,
            "issue_type": issue_type,
            "url": f"{BASE_URL}/browse/{key}"
        },
        "id_seed": f"jira::{key}::main"
    }


def build_chunks_for_comments(issue):
    """Long comment threads get their own linked sub-chunks, per our chunking strategy."""
    key = issue["key"]
    comments = (issue["fields"].get("comment") or {}).get("comments", [])
    chunks = []

    if not comments:
        return chunks

    comment_texts = []
    for c in comments:
        author = (c.get("author") or {}).get("displayName", "Unknown")
        body = extract_text_from_adf(c.get("body"))
        comment_texts.append(f"{author}: {body}")

    full_comment_text = "\n\n".join(comment_texts)

    # Simple length-based split for very long threads (~600 tokens per sub-chunk, per our strategy)
    MAX_CHARS = 2400  # ~600 tokens
    for i in range(0, len(full_comment_text), MAX_CHARS):
        sub_text = full_comment_text[i:i + MAX_CHARS]
        chunk_idx = i // MAX_CHARS
        chunks.append({
            "text": f"JIRA Ticket: {key} (comments, part {chunk_idx + 1})\n{sub_text}",
            "payload": {
                "source_type": "jira_comment",
                "ticket_id": key,
                "url": f"{BASE_URL}/browse/{key}"
            },
            "id_seed": f"jira::{key}::comment::{chunk_idx}"
        })

    return chunks


def run(since_minutes=None):
    """
    since_minutes: if provided, only pulls tickets updated within the last N
    minutes (used by auto_ingest.py for hourly sweeps). Leave as None to pull
    every ticket matching the base JQL, same as before.
    """
    jql = "project = SCRUM ORDER BY created DESC"
    if since_minutes:
        jql = f"project = SCRUM AND updated >= -{since_minutes}m ORDER BY created DESC"

    print(f"Fetching JIRA tickets with JQL: {jql}")
    issues = fetch_all_issues(jql)
    print(f"\nTotal tickets fetched: {len(issues)}")

    all_chunks = []
    for issue in issues:
        all_chunks.append(build_chunk_for_issue(issue))
        all_chunks.extend(build_chunks_for_comments(issue))

    print(f"Total chunks to embed (tickets + comment sub-chunks): {len(all_chunks)}")
    if all_chunks:
        embed_and_upsert(all_chunks)
    print("JIRA ingestion complete.")
    return len(all_chunks)


if __name__ == "__main__":
    run()