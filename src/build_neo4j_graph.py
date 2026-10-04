import json
from neo4j import GraphDatabase


# -----------------------------
# Neo4j connection
# -----------------------------

URI = "neo4j://127.0.0.1:7687"
USERNAME = "neo4j"

PASSWORD = input("Enter your Neo4j password: ")


# -----------------------------
# Load metadata
# -----------------------------

with open(
    "DATASET/chunks_metadata.json",
    "r",
    encoding="utf-8"
) as file:
    chunks = json.load(file)


print(f"Found {len(chunks)} chunks.")


# -----------------------------
# Connect to Neo4j
# -----------------------------

driver = GraphDatabase.driver(
    URI,
    auth=(USERNAME, PASSWORD)
)


# -----------------------------
# Create graph
# -----------------------------

def create_graph(tx, chunk):

    query = """
    MERGE (c:Company {
        name: $company
    })

    MERGE (d:Document {
        document_number: $document_number
    })

    SET d.name = $document_name,
        d.type = $document_type

    MERGE (c)-[:HAS_DOCUMENT]->(d)

    MERGE (ch:Chunk {
        id: $chunk_id
    })

    SET ch.chunk_number = $chunk_number,
        ch.source_file = $source_file,
        ch.text = $text

    MERGE (d)-[:HAS_CHUNK]->(ch)
    """

    tx.run(
        query,
        company=chunk["company"],
        document_number=chunk["document_number"],
        document_name=chunk["document_name"],
        document_type=chunk["document_type"],
        chunk_id=chunk["chunk_id"],
        chunk_number=chunk["chunk_number"],
        source_file=chunk["source_file"],
        text=chunk["text"]
    )


# -----------------------------
# Insert data
# -----------------------------

try:

    with driver.session(database="graphmind") as session:

        for index, chunk in enumerate(chunks, start=1):

            session.execute_write(
                create_graph,
                chunk
            )

            if index % 50 == 0:
                print(
                    f"Processed {index}/{len(chunks)} chunks..."
                )

    print("\nNeo4j graph created successfully!")

finally:

    driver.close()