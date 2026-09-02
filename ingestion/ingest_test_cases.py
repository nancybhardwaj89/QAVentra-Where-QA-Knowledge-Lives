import os
import uuid
import pandas as pd
from FlagEmbedding import BGEM3FlagModel
from qdrant_client import QdrantClient
from qdrant_client.http import models
from common import embed_and_upsert

CSV_PATH = "data_sources/03_test_cases/healthcare_application_5000_test_cases.csv"   # <-- update to your actual filename


def row_to_text(row):
    return (
        f"Test Case ID: {row['Test_Case_ID']}\n"
        f"Module: {row['Module']} | Sub-Module: {row['Sub_Module']}\n"
        f"Title: {row['Test_Case_Title']}\n"
        f"Preconditions: {row['Preconditions']}\n"
        f"Test Steps: {row['Test_Steps']}\n"
        f"Test Data: {row['Test_Data']}\n"
        f"Expected Result: {row['Expected_Result']}\n"
        f"Priority: {row['Priority']} | Test Type: {row['Test_Type']}"
    )


def run(row_limit=None):
    df = pd.read_csv(CSV_PATH)
    if row_limit:
        df = df.head(row_limit)
    print(f"Ingesting {len(df)} test case rows from {CSV_PATH}")

    chunks = []
    current_ids = set()
    for _, row in df.iterrows():
        text = row_to_text(row)
        test_case_id = str(row["Test_Case_ID"])
        current_ids.add(test_case_id)
        chunks.append({
            "text": text,
            "payload": {
                "source_type": "test_case",
                "test_case_id": test_case_id,
                "module": row["Module"],
                "sub_module": row["Sub_Module"],
                "priority": row["Priority"],
                "test_type": row["Test_Type"],
                "source_file": CSV_PATH
            },
            "id_seed": test_case_id
        })

    total = embed_and_upsert(chunks)
    print(f"Done. {total} test cases indexed into Qdrant.")
    return total, current_ids


if __name__ == "__main__":
    run(row_limit=100)