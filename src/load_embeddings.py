import json
import psycopg2
from sentence_transformers import SentenceTransformer

# Load embedding model
print("Loading embedding model...")
model = SentenceTransformer("BAAI/bge-small-en-v1.5")
print("Embedding model loaded!")

# Load chunk metadata
with open("DATASET/chunks_metadata.json", "r", encoding="utf-8") as file:
    chunks = json.load(file)

print(f"Found {len(chunks)} chunks.")

# Connect to PostgreSQL
connection = psycopg2.connect(
    host="localhost",
    port=5432,
    database="graphmind",
    user="postgres",
    password=input("Enter your PostgreSQL password: ")
)

cursor = connection.cursor()

print("Connected to PostgreSQL!")

# Process chunks
for index, chunk in enumerate(chunks, start=1):

    text = chunk["text"]

    # Create embedding
    embedding = model.encode(
        text,
        normalize_embeddings=True
    )

    # Convert embedding to PostgreSQL vector format
    embedding_list = embedding.tolist()

    # Insert into database
    cursor.execute(
        """
        INSERT INTO document_chunks
        (chunk_id, company, document_type, source_file, chunk_number, text, embedding)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (chunk_id) DO NOTHING
        """,
        (
            chunk["chunk_id"],
            chunk["company"],
            chunk["document_type"],
            chunk["source_file"],
            chunk["chunk_number"],
            chunk["text"],
            embedding_list
        )
    )

    if index % 50 == 0:
        connection.commit()
        print(f"Processed {index}/{len(chunks)} chunks...")

# Save remaining changes
connection.commit()

cursor.close()
connection.close()

print("\nAll embeddings stored successfully!")