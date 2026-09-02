import os
from pypdf import PdfReader
from docx import Document as DocxDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter
from common import embed_and_upsert, normalize_path

DOC_SOURCES = [
    {"folder": "data_sources/05_company_docs", "doc_category": "company_doc", "source_type": "document"},
    {"folder": "data_sources/09_prd_srs_brd_frd", "doc_category": "prd_srs_brd_frd", "source_type": "document"},
    {"folder": "data_sources/07_meeting_notes", "doc_category": "meeting_notes", "source_type": "meeting_notes"},
]

CHUNK_SIZE = 3200      # ~800 tokens
CHUNK_OVERLAP = 500    # ~125 tokens

MEETING_CHUNK_SIZE = 4000     # ~1000 tokens
MEETING_CHUNK_OVERLAP = 700   # ~175 tokens

doc_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", ". ", " ", ""]
)

meeting_splitter = RecursiveCharacterTextSplitter(
    chunk_size=MEETING_CHUNK_SIZE,
    chunk_overlap=MEETING_CHUNK_OVERLAP,
    separators=["\n\n", "\n", ". ", " ", ""]
)


def extract_text(filepath):
    if filepath.lower().endswith(".pdf"):
        reader = PdfReader(filepath)
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    elif filepath.lower().endswith(".md"):
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    elif filepath.lower().endswith(".docx"):
        doc = DocxDocument(filepath)
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return None


def run(changed_only=None):
    """
    changed_only: optional set of NORMALIZED filepaths to restrict ingestion to.
    """
    all_chunks = []

    for source in DOC_SOURCES:
        folder = source["folder"]
        print(f"Scanning {folder}...")
        if not os.path.exists(folder):
            continue

        splitter = meeting_splitter if source["source_type"] == "meeting_notes" else doc_splitter

        for filename in os.listdir(folder):
            filepath = normalize_path(os.path.join(folder, filename))
            if not (filename.lower().endswith(".pdf") or filename.lower().endswith(".md") or filename.lower().endswith(".docx")):
                continue

            if changed_only is not None and filepath not in changed_only:
                continue

            print(f"  -> attempting: {filename}")
            try:
                text = extract_text(filepath)
            except Exception as e:
                print(f"  -> Could not read {filename}: {e}")
                continue

            if not text or not text.strip():
                print(f"  -> No extractable text in {filename}, skipping")
                continue

            file_chunks = splitter.split_text(text)
            for idx, chunk_text in enumerate(file_chunks):
                all_chunks.append({
                    "text": chunk_text,
                    "payload": {
                        "source_type": source["source_type"],
                        "doc_category": source["doc_category"],
                        "file_path": filepath,
                        "chunk_index": idx
                    },
                    "id_seed": f"{filepath}::{idx}"
                })
            print(f"  -> {filename}: {len(file_chunks)} chunks")

    print(f"\nTotal document chunks to embed: {len(all_chunks)}")
    if all_chunks:
        embed_and_upsert(all_chunks)
    print("Document ingestion complete.")
    return len(all_chunks)


if __name__ == "__main__":
    run()