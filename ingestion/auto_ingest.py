import os
import time
from state import load_state, save_state
from common import normalize_path, delete_by_filter

import ingest_test_cases
import ingest_code
import ingest_docs
import ingest_jira

CODE_FOLDERS = ["data_sources/01_selenium_framework", "data_sources/02_playwright_framework"]
CODE_EXTENSIONS = {".java", ".ts", ".js"}
DOC_FOLDERS = ["data_sources/05_company_docs", "data_sources/09_prd_srs_brd_frd", "data_sources/07_meeting_notes"]
DOC_EXTENSIONS = {".pdf", ".md", ".docx"}
TEST_CASE_FILE = normalize_path("data_sources/03_test_cases/healthcare_application_5000_test_cases.csv")


def scan_current_files(folders, extensions):
    """Returns the set of normalized filepaths currently present on disk."""
    current = set()
    for folder in folders:
        if not os.path.exists(folder):
            continue
        for root, _, files in os.walk(folder):
            if any(skip in root for skip in [".git", "node_modules", "target", "allure-report", "allure-results"]):
                continue
            for filename in files:
                ext = os.path.splitext(filename)[1]
                if ext not in extensions:
                    continue
                current.add(normalize_path(os.path.join(root, filename)))
    return current


def find_changed_files(current_files, known_mtimes):
    """Given the current file set, returns which ones changed (new or modified mtime)."""
    changed = set()
    updated_mtimes = dict(known_mtimes)
    for filepath in current_files:
        mtime = os.path.getmtime(filepath)
        if known_mtimes.get(filepath) != mtime:
            changed.add(filepath)
            updated_mtimes[filepath] = mtime
    return changed, updated_mtimes


def remove_deleted_files(current_files, known_mtimes, state):
    """Any file previously tracked in state but no longer on disk gets its
    Qdrant chunks deleted, and its entry removed from state."""
    known_files = {
        path for path in known_mtimes.keys()
        if any(path.startswith(normalize_path(folder)) for folder in CODE_FOLDERS + DOC_FOLDERS)
    }
    deleted_files = known_files - current_files

    for filepath in deleted_files:
        print(f"  -> Removing stale chunks for deleted file: {filepath}")
        delete_by_filter("file_path", filepath)
        state["file_mtimes"].pop(filepath, None)

    return len(deleted_files)


def run_sweep():
    print(f"\n{'='*50}\nAuto-ingestion sweep starting: {time.strftime('%Y-%m-%d %H:%M:%S')}\n{'='*50}")
    state = load_state()
    state.setdefault("known_test_case_ids", [])

    # --- Test cases: change + deletion detection ---
    if os.path.exists(TEST_CASE_FILE):
        mtime = os.path.getmtime(TEST_CASE_FILE)
        if state["file_mtimes"].get(TEST_CASE_FILE) != mtime:
            print("\n[Test Cases] Change detected, re-ingesting...")
            _, current_ids = ingest_test_cases.run(row_limit=100)

            previous_ids = set(state["known_test_case_ids"])
            deleted_ids = previous_ids - current_ids
            for test_case_id in deleted_ids:
                print(f"  -> Removing deleted test case: {test_case_id}")
                delete_by_filter("test_case_id", test_case_id)

            state["known_test_case_ids"] = list(current_ids)
            state["file_mtimes"][TEST_CASE_FILE] = mtime
        else:
            print("\n[Test Cases] No change, skipping.")

    # --- Code: change + deletion detection ---
    current_code_files = scan_current_files(CODE_FOLDERS, CODE_EXTENSIONS)
    changed_code, updated_code_mtimes = find_changed_files(current_code_files, state["file_mtimes"])
    deleted_code_count = remove_deleted_files(current_code_files, state["file_mtimes"], state)

    if changed_code:
        print(f"\n[Code] {len(changed_code)} changed file(s) detected, re-ingesting those...")
        ingest_code.run(changed_only=changed_code)
        state["file_mtimes"].update(updated_code_mtimes)
    else:
        print("\n[Code] No changes detected.")
    if deleted_code_count:
        print(f"[Code] Cleaned up {deleted_code_count} deleted file(s).")

    # --- Docs: change + deletion detection ---
    current_doc_files = scan_current_files(DOC_FOLDERS, DOC_EXTENSIONS)
    changed_docs, updated_doc_mtimes = find_changed_files(current_doc_files, state["file_mtimes"])
    deleted_doc_count = remove_deleted_files(current_doc_files, state["file_mtimes"], state)

    if changed_docs:
        print(f"\n[Docs] {len(changed_docs)} changed file(s) detected, re-ingesting those...")
        ingest_docs.run(changed_only=changed_docs)
        state["file_mtimes"].update(updated_doc_mtimes)
    else:
        print("\n[Docs] No changes detected.")
    if deleted_doc_count:
        print(f"[Docs] Cleaned up {deleted_doc_count} deleted file(s).")

    # --- JIRA: incremental pull only (deletion handled separately, see Step 52) ---
    print("\n[JIRA] Pulling tickets updated in the last 65 minutes...")
    ingest_jira.run(since_minutes=65)

    save_state(state)
    print(f"\n{'='*50}\nSweep complete: {time.strftime('%Y-%m-%d %H:%M:%S')}\n{'='*50}")


if __name__ == "__main__":
    run_sweep()