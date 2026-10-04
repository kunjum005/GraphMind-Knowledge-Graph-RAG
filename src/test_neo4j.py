from neo4j import GraphDatabase

URI = "neo4j://127.0.0.1:7687"
USERNAME = "neo4j"
PASSWORD = input("Enter your Neo4j password: ")

driver = GraphDatabase.driver(
    URI,
    auth=(USERNAME, PASSWORD)
)

try:
    with driver.session(database="graphmind") as session:
        result = session.run(
            'RETURN "Neo4j connection successful!" AS message'
        )
        print(result.single()["message"])

finally:
    driver.close()