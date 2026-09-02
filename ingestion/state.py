import json
import os

STATE_PATH = os.path.join(os.path.dirname(__file__), "state.json")

def load_state():
    if not os.path.exists(STATE_PATH):
        return {"file_mtimes": {}, "jira_last_run": None, "code_commits": {}}
    with open(STATE_PATH, "r") as f:
        return json.load(f)

def save_state(state):
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)