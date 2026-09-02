import pandas as pd
from common import get_client, COLLECTION_NAME, delete_by_filter
from qdrant_client.http import models

CSV_PATH = "data_sources/03_test_cases/healthcare_application_5000_test_cases.csv"


def get_all_indexed_test_case_ids():
    """Scrolls through every point in Qdrant with source_type=test_case
    and returns the full set of test_case_id values currently indexed —
    ground truth from the database itself, not from state.json's memory."""
    client = get_client()
    ids = set()
    next_page = None

    while True:
        points, next_page = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=models.Filter(
                must=[models.FieldCondition(key="source_type", match=models.MatchValue(value="test_case"))]
            ),
            limit=200,
            offset=next_page,
            with_payload=["test_case_id"],
            with_vectors=False
        )
        for p in points:
            ids.add(p.payload["test_case_id"])
        if next_page is None:
            break

    return ids


def run_full_sync(row_limit=100):
    print("Running full test case reconciliation...")

    df = pd.read_csv(CSV_PATH)
    if row_limit:
        df = df.head(row_limit)
    current_ids = set(df["Test_Case_ID"].astype(str))

    indexed_ids = get_all_indexed_test_case_ids()

    orphaned_ids = indexed_ids - current_ids
    print(f"CSV has {len(current_ids)} rows. Qdrant has {len(indexed_ids)} indexed test cases.")
    print(f"Found {len(orphaned_ids)} orphaned point(s) to clean up.")

    for test_case_id in orphaned_ids:
        print(f"  -> Removing orphaned test case: {test_case_id}")
        delete_by_filter("test_case_id", test_case_id)

    print("Full test case reconciliation complete.")


if __name__ == "__main__":
    run_full_sync(row_limit=100)