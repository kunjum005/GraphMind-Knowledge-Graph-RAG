import builtins
import io
import os
import runpy
from contextlib import redirect_stdout

QUESTIONS = [
    "Who acquired Activision Blizzard?",
    "Which company was acquired by Microsoft?",
    "When did CoreWeave and NVIDIA enter the agreement?",
    "What was the initial value of the NVIDIA and CoreWeave agreement?",
    "What is the relationship between Microsoft and Activision Blizzard?",
    "What is the name of the NVIDIA platform that delivers a full stack end-to-end solution for the AV market?",
]

SCRIPT_PATH = os.path.join(
    os.path.dirname(__file__),
    "graph_rag_retrieval.py"
)

print("BATCH RUNNER SCRIPT_PATH:", SCRIPT_PATH)
print("FILE EXISTS:", os.path.exists(SCRIPT_PATH))

def run_one_question(question, postgres_password, neo4j_password):
    inputs = iter([
        question,
        postgres_password,
        neo4j_password
    ])

    original_input = builtins.input

    def fake_input(prompt=""):
        print(prompt, end="")
        return next(inputs)

    builtins.input = fake_input

    output = io.StringIO()

    try:
        with redirect_stdout(output):
            runpy.run_path(
                SCRIPT_PATH,
                run_name="__main__"
            )
    finally:
        builtins.input = original_input

    return output.getvalue()


def extract_final_answer(output):
    marker = "FINAL GRAPHMIND ANSWER"

    if marker in output:
        section = output.split(marker, 1)[1]

        # Remove the separator immediately after the marker
        section = section.lstrip()

        if section.startswith("="):
            section = section.split("\n", 1)[1]

        return section.strip()

    return output.strip()

def main():
    print("=" * 70)
    print("GRAPHMIND BATCH TEST")
    print("=" * 70)
    print(f"Running {len(QUESTIONS)} questions automatically.\n")

    postgres_password = input("Enter PostgreSQL password: ")
    neo4j_password = input("Enter Neo4j password: ")

    print("\nPasswords received.")
    print("Starting batch test...\n")

    results = []

    for index, question in enumerate(QUESTIONS, start=1):

        print("\n" + "=" * 70)
        print(f"QUESTION {index}/{len(QUESTIONS)}")
        print("=" * 70)
        print(question)

        try:
            output = run_one_question(
                question,
                postgres_password,
                neo4j_password
            )

            answer = extract_final_answer(output)

            results.append((question, answer))

            print("\nRESULT:")
            print(answer)

        except Exception as e:
            results.append((question, f"ERROR: {e}"))

            print("\nERROR:")
            print(e)

    print("\n\n" + "=" * 70)
    print("BATCH TEST SUMMARY")
    print("=" * 70)

    for index, (question, answer) in enumerate(results, start=1):
        print(f"\n{index}. {question}")
        print("-" * 70)
        print(answer)

    print("\n" + "=" * 70)
    print("BATCH TEST COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()