import os
from langchain_text_splitters import RecursiveCharacterTextSplitter, Language
from common import embed_and_upsert, normalize_path

# Map file extensions to their Language enum and folder to repo name
CODE_SOURCES = [
    {"folder": "data_sources/01_selenium_framework", "repo": "selenium_framework", "extensions": {".java": Language.JAVA}},
    {"folder": "data_sources/02_playwright_framework", "repo": "playwright_framework", "extensions": {".ts": Language.TS, ".js": Language.JS}},
]

CHUNK_SIZE = 3000     # ~750 tokens
CHUNK_OVERLAP = 400   # ~100 tokens


def ingest_code_source(source, changed_only=None):
    """
    changed_only: optional set of NORMALIZED filepaths. If provided, only
    files whose normalized path appears in this set are processed.
    """
    chunks = []
    for root, _, files in os.walk(source["folder"]):
        if any(skip in root for skip in [".git", "node_modules", "target", "allure-report", "allure-results"]):
            continue

        for filename in files:
            ext = os.path.splitext(filename)[1]
            if ext not in source["extensions"]:
                continue

            filepath = normalize_path(os.path.join(root, filename))

            if changed_only is not None and filepath not in changed_only:
                continue

            language = source["extensions"][ext]

            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    code = f.read()
            except Exception as e:
                print(f"Skipping {filepath}: {e}")
                continue

            if not code.strip():
                continue

            splitter = RecursiveCharacterTextSplitter.from_language(
                language=language, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
            )
            file_chunks = splitter.split_text(code)

            for idx, chunk_text in enumerate(file_chunks):
                chunks.append({
                    "text": chunk_text,
                    "payload": {
                        "source_type": "code",
                        "repo": source["repo"],
                        "file_path": filepath,
                        "chunk_index": idx
                    },
                    "id_seed": f"{filepath}::{idx}"
                })

    return chunks


def run(changed_only=None):
    all_chunks = []
    for source in CODE_SOURCES:
        print(f"Scanning {source['folder']}...")
        source_chunks = ingest_code_source(source, changed_only=changed_only)
        print(f"  -> {len(source_chunks)} chunks")
        all_chunks.extend(source_chunks)

    print(f"\nTotal code chunks to embed: {len(all_chunks)}")
    if all_chunks:
        embed_and_upsert(all_chunks)
    print("Code ingestion complete.")
    return len(all_chunks)


if __name__ == "__main__":
    run()