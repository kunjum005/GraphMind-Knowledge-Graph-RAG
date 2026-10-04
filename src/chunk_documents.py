from pathlib import Path


# Folder containing our cleaned TXT documents
PROCESSED_FOLDER = Path("DATASET/processed")

# Folder where chunks will be saved
CHUNKS_FOLDER = Path("DATASET/chunks")

# Create chunks folder if it doesn't exist
CHUNKS_FOLDER.mkdir(parents=True, exist_ok=True)


# Chunk settings
CHUNK_SIZE = 800
OVERLAP = 100


# Find all TXT files
text_files = list(PROCESSED_FOLDER.glob("*.txt"))

print(f"Found {len(text_files)} TXT files.")


# Process each document
for text_file in text_files:

    print(f"\nProcessing: {text_file.name}")

    # Read the document
    text = text_file.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    # Convert text into words
    words = text.split()

    total_words = len(words)

    print(f"Total words: {total_words}")

    chunk_number = 1
    start = 0

    while start < total_words:

        # Calculate where this chunk ends
        end = start + CHUNK_SIZE

        # Get the words for this chunk
        chunk_words = words[start:end]

        # Convert words back into text
        chunk_text = " ".join(chunk_words)

        # Create chunk filename
        chunk_filename = (
            f"{text_file.stem}_chunk_{chunk_number:03d}.txt"
        )

        output_file = CHUNKS_FOLDER / chunk_filename

        # Save chunk
        output_file.write_text(
            chunk_text,
            encoding="utf-8"
        )

        print(
            f"Created: {chunk_filename} "
            f"({len(chunk_words)} words)"
        )

        # Move forward, but keep overlap
        start = end - OVERLAP

        chunk_number += 1


print("\nChunking completed!")