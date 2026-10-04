from pathlib import Path
import json
import re


CHUNKS_FOLDER = Path("DATASET/chunks")
OUTPUT_FILE = Path("DATASET/chunks_metadata.json")


# Find all chunk files
chunk_files = sorted(CHUNKS_FOLDER.glob("*.txt"))

print(f"Found {len(chunk_files)} chunks.")


metadata = []


for chunk_file in chunk_files:

    filename = chunk_file.stem

    # Example:
    # 01_Microsoft_10K_2025_chunk_001

    match = re.match(
        r"(\d+)_(.+)_chunk_(\d+)$",
        filename
    )

    if not match:
        print(f"Skipping: {chunk_file.name}")
        continue

    document_number = match.group(1)
    document_name = match.group(2)
    chunk_number = int(match.group(3))

    # Read chunk text
    text = chunk_file.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    # Try to identify company
    company = "Unknown"

    if "Microsoft" in document_name:
        company = "Microsoft"

    elif "Activision" in document_name:
        company = "Activision Blizzard"

    elif "Amazon" in document_name:
        company = "Amazon"

    elif "Flex" in document_name:
        company = "Flex"

    elif "Alphabet" in document_name:
        company = "Alphabet"

    elif "NVIDIA" in document_name:
        company = "NVIDIA"

    elif "CoreWeave" in document_name:
        company = "CoreWeave"

    elif "Meta" in document_name:
        company = "Meta"

    # Identify document type
    document_type = "Other"

    if "10K" in document_name:
        document_type = "10-K"

    elif "8K" in document_name:
        document_type = "8-K"

    elif "Ex21" in document_name:
        document_type = "Exhibit 21"

    elif "Ex10" in document_name:
        document_type = "Exhibit 10"

    elif "Ex991" in document_name:
        document_type = "Exhibit 99.1"

    # Create metadata record
    record = {
        "chunk_id": filename,
        "document_number": document_number,
        "document_name": document_name,
        "company": company,
        "document_type": document_type,
        "chunk_number": chunk_number,
        "source_file": chunk_file.name,
        "text": text
    }

    metadata.append(record)


# Save metadata
OUTPUT_FILE.write_text(
    json.dumps(metadata, indent=2),
    encoding="utf-8"
)


print(f"Saved metadata to: {OUTPUT_FILE}")
print(f"Total metadata records: {len(metadata)}")