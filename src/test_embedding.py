from sentence_transformers import SentenceTransformer


# Load the embedding model
model = SentenceTransformer("BAAI/bge-small-en-v1.5")

# A small test sentence
text = "Microsoft acquired Activision Blizzard."

# Convert text into an embedding
embedding = model.encode(text)

print("Embedding created successfully!")
print("Number of values:", len(embedding))
print("First 10 values:", embedding[:10])