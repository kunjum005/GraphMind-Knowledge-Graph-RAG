import json


# ==========================================
# Load chunks
# ==========================================

with open(
    "DATASET/chunks_metadata.json",
    "r",
    encoding="utf-8"
) as file:
    chunks = json.load(file)


# ==========================================
# Known companies in our knowledge graph
# ==========================================

companies = [
    "Activision Blizzard",
    "Alphabet",
    "Amazon",
    "CoreWeave",
    "Meta",
    "Microsoft",
    "NVIDIA"
]


# ==========================================
# Find chunks containing multiple companies
# ==========================================

results = []


for chunk in chunks:

    text = chunk["text"]

    mentioned_companies = []

    for company in companies:

        if company.lower() in text.lower():

            mentioned_companies.append(company)

    # Only keep chunks mentioning 2 or more companies
    if len(mentioned_companies) >= 2:

        results.append({
            "chunk_id": chunk["chunk_id"],
            "source_company": chunk["company"],
            "document_type": chunk["document_type"],
            "mentioned_companies": mentioned_companies,
            "text": text
        })


# ==========================================
# Display results
# ==========================================

print("\n==========================================")
print("COMPANY RELATIONSHIP CANDIDATES")
print("==========================================\n")

print(
    f"Total chunks: {len(chunks)}"
)

print(
    f"Chunks mentioning multiple known companies: "
    f"{len(results)}"
)


for index, result in enumerate(results[:30], start=1):

    print("\n------------------------------------------")
    print(f"Candidate {index}")
    print("------------------------------------------")

    print(
        f"Chunk ID: {result['chunk_id']}"
    )

    print(
        f"Source Company: {result['source_company']}"
    )

    print(
        f"Document Type: {result['document_type']}"
    )

    print(
        f"Mentioned Companies: "
        f"{', '.join(result['mentioned_companies'])}"
    )

    print(
        f"\nText:\n{result['text'][:700]}"
    )