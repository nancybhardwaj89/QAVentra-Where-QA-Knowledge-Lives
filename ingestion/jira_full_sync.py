from common import delete_by_filter
from state import load_state, save_state
import ingest_jira

def run_full_sync():
    print("Running full JIRA sync to detect deleted tickets...")

    # Pull every ticket that currently exists (no time filter)
    issues = ingest_jira.fetch_all_issues("project = SCRUM ORDER BY created DESC")
    current_keys = {issue["key"] for issue in issues}

    state = load_state()
    known_keys = set(state.get("known_jira_keys", []))

    deleted_keys = known_keys - current_keys
    for key in deleted_keys:
        print(f"  -> Removing deleted JIRA ticket: {key}")
        delete_by_filter("ticket_id", key)

    state["known_jira_keys"] = list(current_keys)
    save_state(state)
    print(f"Full sync complete. {len(deleted_keys)} deleted ticket(s) cleaned up.")

if __name__ == "__main__":
    run_full_sync()