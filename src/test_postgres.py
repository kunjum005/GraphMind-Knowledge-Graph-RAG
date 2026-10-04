import psycopg2

connection = psycopg2.connect(
    host="localhost",
    port=5432,
    database="graphmind",
    user="postgres",
    password=input("Enter your PostgreSQL password: ")
)

print("PostgreSQL connection successful!")

connection.close()