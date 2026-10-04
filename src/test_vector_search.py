import psycopg2
from sentence_transformers import SentenceTransformer

# Load embedding model
print("Loading embedding model...")
model = SentenceTransformer("BAAI/bge-small-en-v1.5")
print("Model loaded!")

# Question we want to search
question = "What companies are related to Microsoft?"

# Convert question into an embedding
question_embedding = model.encode(
    question,
    normalize_embeddings=True
)

# Connect to PostgreSQL
connection = psycopg2.connect(
    host="localhost",
    port=5432,
    database="graphmind",
    user="postgres",
    password=input("Enter your PostgreSQL password: ")
)

cursor = connection.cursor()

# Search for the 5 most similar chunks
cursor.execute(
    """
    SELECT chunk_id, company, document_type, text,
           1 - (embedding <=> %s::vector) AS similarity
    FROM document_chunks
    ORDER BY embedding <=> %s::vector
    LIMIT 5;
    """,
    (
        question_embedding.tolist(),
        question_embedding.tolist()
    )
)

results = cursor.fetchall()

print("\nTop 5 matching chunks:\n")

for rank, result in enumerate(results, start=1):
    chunk_id, company, document_type, text, similarity = result

    print(f"--- Result {rank} ---")
    print(f"Chunk ID: {chunk_id}")
    print(f"Company: {company}")
    print(f"Document Type: {document_type}")
    print(f"Similarity: {similarity:.4f}")
    print(f"Text: {text[:500]}")
    print()

cursor.close()
connection.close()