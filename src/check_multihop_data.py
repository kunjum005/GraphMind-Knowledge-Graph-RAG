import os

# ==========================================
# CONFIGURATION
# ==========================================

CHUNKS_FOLDER = os.path.join(
    "DATASET",
    "chunks"
)

print("=" * 60)
print("GRAPHMIND MULTI-HOP DATASET CHECK")
print("=" * 60)

print("\nLooking for chunk folder...")
print("Path:", CHUNKS_FOLDER)

# ==========================================
# FIND ALL CHUNK FILES
# ==========================================

if not os.path.exists(CHUNKS_FOLDER):
    print("\nERROR: Chunks folder not found!")
    print("Expected:", os.path.abspath(CHUNKS_FOLDER))
    exit()

chunk_files = [
    file for file in os.listdir(CHUNKS_FOLDER)
    if file.endswith(".txt")
]

print(f"\nFound {len(chunk_files)} chunk files.")

if len(chunk_files) == 0:
    print("No chunk files found.")
    exit()

print("\nFirst 5 chunk files:")
for file in chunk_files[:5]:
    print(" -", file)

# ==========================================
# KNOWN COMPANIES IN OUR DATASET
# ==========================================

known_companies = [
    "Microsoft",
    "Activision Blizzard",
    "Alphabet",
    "Amazon",
    "NVIDIA",
    "CoreWeave",
    "Meta",
    "Wiz",
]

print("\nScanning chunks for company mentions...")

company_mentions = []

for file in chunk_files:
    file_path = os.path.join(CHUNKS_FOLDER, file)

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    found_companies = []

    for company in known_companies:
        if company.lower() in text.lower():
            found_companies.append(company)

    if len(found_companies) >= 2:
        company_mentions.append(
            {
                "file": file,
                "companies": found_companies
            }
        )

print(f"\nChunks mentioning 2 or more known companies: {len(company_mentions)}")

# ==========================================
# SHOW MULTI-COMPANY CHUNKS
# ==========================================

print("\n" + "=" * 60)
print("MULTI-COMPANY CHUNKS")
print("=" * 60)

for item in company_mentions:
    print("\nFile:", item["file"])
    print("Companies:", ", ".join(item["companies"]))

# ==========================================
# FIND MICROSOFT + NVIDIA RELATIONSHIP TERMS
# ==========================================

print("\n" + "=" * 60)
print("MICROSOFT + NVIDIA RELATIONSHIP EVIDENCE")
print("=" * 60)

for item in company_mentions:
    if "Microsoft" in item["companies"] and "NVIDIA" in item["companies"]:

        file_path = os.path.join(CHUNKS_FOLDER, item["file"])

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()

        print("\n" + "-" * 60)
        print("FILE:", item["file"])
        print("-" * 60)

        sentences = text.replace("\n", " ").split(".")

        for sentence in sentences:
            if "agreement" in sentence.lower():
                print(sentence.strip() + ".")