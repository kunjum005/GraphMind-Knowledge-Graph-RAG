import os
import json
import re

import psycopg2
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
import ollama

print("RUNNING GRAPH RAG FILE:", __file__)


# ==========================================
# CONFIGURATION
# ==========================================

NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USERNAME = "neo4j"

POSTGRES_HOST = "localhost"
POSTGRES_PORT = 5432
POSTGRES_DATABASE = "graphmind"
POSTGRES_USER = "postgres"


# ==========================================
# KNOWN COMPANIES
# ==========================================

KNOWN_COMPANIES = [
    "Microsoft",
    "NVIDIA",
    "CoreWeave",
    "Meta",
    "Alphabet",
    "Amazon",
    "Activision Blizzard",
    "Wiz"
]


# ==========================================
# USER QUESTION
# ==========================================

question = input("\nEnter your question: ")


# ==========================================
# LOAD EMBEDDING MODEL
# ==========================================

print("\nLoading embedding model...")

model = SentenceTransformer(
    "BAAI/bge-small-en-v1.5"
)

print("Embedding model loaded!")


# ==========================================
# CREATE QUESTION EMBEDDING
# ==========================================

question_embedding = model.encode(
    question,
    normalize_embeddings=True
)


# ==========================================
# CONNECT TO POSTGRESQL
# ==========================================

print("\nConnecting to PostgreSQL...")

postgres_password = input(
    "Enter your PostgreSQL password: "
)

connection = psycopg2.connect(
    host=POSTGRES_HOST,
    port=POSTGRES_PORT,
    database=POSTGRES_DATABASE,
    user=POSTGRES_USER,
    password=postgres_password
)

cursor = connection.cursor()

print("PostgreSQL connected!")


# ==========================================
# VECTOR SEARCH
# ==========================================

print("\nSearching PostgreSQL...")

cursor.execute(
    """
    SELECT
        chunk_id,
        company,
        document_type,
        text,
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

vector_results = cursor.fetchall()

cursor.close()
connection.close()


print("\nTop vector search results:\n")

for rank, result in enumerate(
    vector_results,
    start=1
):

    chunk_id, company, document_type, text, similarity = result

    print(f"--- Vector Result {rank} ---")

    print(
        f"Chunk ID: {chunk_id}"
    )

    print(
        f"Company: {company}"
    )

    print(
        f"Document Type: {document_type}"
    )

    print(
        f"Similarity: {similarity:.4f}"
    )

    print(
        f"Text: {text[:300]}"
    )

    print()


# ==========================================
# EXTRACT CHUNK IDS
# ==========================================

chunk_ids = [
    result[0]
    for result in vector_results
]


# ==========================================
# CONNECT TO NEO4J
# ==========================================

print("Connecting to Neo4j...")

neo4j_password = input(
    "Enter your Neo4j password: "
)

driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(
        NEO4J_USERNAME,
        neo4j_password
    )
)

print("Neo4j connected!")


# ==========================================
# GRAPH CONTEXT
# ==========================================

def get_graph_context(tx, chunk_ids):

    query = """
    MATCH (c:Company)-[:HAS_DOCUMENT]->(d:Document)
          -[:HAS_CHUNK]->(ch:Chunk)

    WHERE ch.id IN $chunk_ids

    RETURN DISTINCT
        c.name AS company,
        d.name AS document,
        d.type AS document_type,
        d.document_number AS document_number,
        ch.id AS chunk_id,
        ch.chunk_number AS chunk_number,
        ch.text AS text

    ORDER BY
        c.name,
        d.document_number,
        ch.chunk_number
    """

    result = tx.run(
        query,
        chunk_ids=chunk_ids
    )

    return result.data()


# ==========================================
# GET COMPANY RELATIONSHIPS
# ==========================================

def get_company_relationships(tx, companies):

    query = """
    MATCH (c:Company)-[r]-(related:Company)

    WHERE c.name IN $companies

    RETURN DISTINCT
        startNode(r).name AS company,
        type(r) AS relationship,
        endNode(r).name AS related_company

    ORDER BY
        company,
        relationship,
        related_company
    """

    result = tx.run(
        query,
        companies=companies
    )

    return result.data()


# ==========================================
# GET TWO-HOP RELATIONSHIPS
# ==========================================

def get_two_hop_relationships(tx, companies):

    query = """
    MATCH (start:Company)-[r1]->(middle:Company)
          -[r2]->(end:Company)

    WHERE start.name IN $companies
      AND end <> start
      AND end <> middle

    RETURN DISTINCT

        start.name AS first_company,

        type(r1) AS first_relationship,

        middle.name AS middle_company,

        type(r2) AS second_relationship,

        end.name AS final_company

    ORDER BY
        first_company,
        first_relationship,
        middle_company,
        second_relationship,
        final_company
    """

    result = tx.run(
        query,
        companies=companies
    )

    return result.data()


# ==========================================
# GET EVIDENCE FOR SPECIFIC RELATIONSHIPS
# ==========================================

def get_relationship_evidence(
    tx,
    relationship_pairs
):

    if not relationship_pairs:
        return []

    query = """
    UNWIND $relationship_pairs AS pair

    MATCH (c:Company)-[r]->(related:Company)

    WHERE c.name = pair.company
      AND type(r) = pair.relationship
      AND related.name = pair.related_company

    MATCH (e:Evidence)-[ef:EVIDENCE_FOR]->(related)

    WHERE ef.relationship = type(r)

    MATCH (e)-[:SUPPORTS]->(ch:Chunk)

    RETURN DISTINCT

        c.name AS company,

        type(r) AS relationship,

        related.name AS related_company,

        e.evidence_id AS evidence_id,

        ch.id AS chunk_id,

        ch.chunk_number AS chunk_number,

        coalesce(
            e.evidence_text,
            ch.text
        ) AS text

    ORDER BY
        company,
        relationship,
        related_company
    """

    print("\nDEBUG relationship_pairs:")
    print(relationship_pairs)

    result = tx.run(
        query,
        relationship_pairs=relationship_pairs
    )

    return result.data()


# ==========================================
# SELECT RELEVANT TWO-HOP PATH
# ==========================================

def select_target_path(
    question,
    two_hop_relationships
):

    if not re.search(r"\bthrough\b", question, re.IGNORECASE):
        return []

    if not two_hop_relationships:
        return []

    question_lower = question.lower()

    # --------------------------------------
    # Find companies explicitly mentioned
    # --------------------------------------

    mentioned_companies = [
        company
        for company in KNOWN_COMPANIES
        if company.lower() in question_lower
    ]

    target_path = two_hop_relationships


    # --------------------------------------
    # First company in the question
    # --------------------------------------

    if mentioned_companies:

        start_company = mentioned_companies[0]

        target_path = [
            path
            for path in target_path

            if path["first_company"].lower()
            == start_company.lower()
        ]


    # --------------------------------------
    # Handle "through X"
    # --------------------------------------

    through_match = re.search(
        r"\bthrough\s+(.+?)(?:\?|$)",
        question,
        re.IGNORECASE
    )

    if through_match:

        through_text = (
            through_match
            .group(1)
            .lower()
        )

        for company in KNOWN_COMPANIES:

            if company.lower() in through_text:

                target_path = [
                    path
                    for path in target_path

                    if path["middle_company"].lower()
                    == company.lower()
                ]

                break


    return target_path


# ==========================================
# BUILD EVIDENCE PAIRS FROM PATH
# ==========================================

def get_mentioned_companies(question):
    """Return known companies explicitly mentioned in the question."""
    question_lower = question.lower()
    return [
        company
        for company in KNOWN_COMPANIES
        if re.search(rf"\b{re.escape(company)}\b",
            question,
            re.IGNORECASE)
    ]


# ==========================================
# QUESTION RELATIONSHIP INTENT
# ==========================================

def get_relationship_intent(question):
    """Map relationship wording to graph relationship types without using company-specific rules."""
    q = question.lower()

    if re.search(r"\b(agreed to acquire|agreement to acquire|agreed to buy|agreed on acquisition)\b", q):
        return "AGREED_TO_ACQUIRE"

    if re.search(r"\b(who acquired|which company acquired|who bought|which company bought|acquisition|acquired)\b", q):
        return "ACQUIRED"

    if re.search(r"\b(subsidiary|subsidiaries|owned by|owns)\b", q):
        return "HAS_SUBSIDIARY"

    if re.search(r"\b(agreement|contract|deal|partner|partners)\b", q):
        return "AGREEMENT_WITH"

    return None


# ==========================================
# BUILD QUERY-SPECIFIC EVIDENCE PAIRS
# ==========================================

def build_relationship_pairs(
    question,
    company_relationships,
    target_path
):

    """
    Build exact directed relationship pairs for evidence retrieval.

    Direct relationships are selected from the graph according to the
    question. Two-hop relationships are added only when the question
    explicitly selects a multi-hop path (for example, "through X").
    """
    relationship_pairs = []
    mentioned_companies = get_mentioned_companies(question)
    relationship_intent = get_relationship_intent(question)


    is_through = bool(re.search(r"\bthrough\b", question, re.IGNORECASE))

    if not is_through:
        if len(mentioned_companies) >= 2:
            company_a = mentioned_companies[0]
            company_b = mentioned_companies[1]

            for relationship in company_relationships:
                same_pair = (
                    (relationship["company"].lower() == company_a.lower()
                     and relationship["related_company"].lower() == company_b.lower())
                    or
                    (relationship["company"].lower() == company_b.lower()
                     and relationship["related_company"].lower() == company_a.lower())
                )

                if same_pair and (
                    relationship_intent is None
                    or relationship["relationship"] == relationship_intent
                ):
                    relationship_pairs.append({
                        "company": relationship["company"],
                        "relationship": relationship["relationship"],
                        "related_company": relationship["related_company"]
                    })

        elif len(mentioned_companies) == 1:
            mentioned = mentioned_companies[0]
            q = question.lower()

            # Questions such as "Who acquired Activision Blizzard?"
            # require an incoming ACQUIRED edge to the mentioned company.
            incoming_acquisition = bool(re.search(
                r"\b(who acquired|which company acquired|who bought|which company bought)\b",
                q
            ))

            # Questions such as "Which company was acquired by Microsoft?"
            # require an outgoing ACQUIRED edge from the mentioned company.
            outgoing_acquisition = bool(re.search(
                r"\b(which company was acquired by|who was acquired by|what company was acquired by)\b",
                q
            ))

            for relationship in company_relationships:
                matches_company = (
                    relationship["company"].lower() == mentioned.lower()
                    or relationship["related_company"].lower() == mentioned.lower()
                )

                if not matches_company:
                    continue

                if incoming_acquisition:
                    if not (
                        relationship["related_company"].lower() == mentioned.lower()
                        and relationship["relationship"] == "ACQUIRED"
                    ):
                        continue

                elif outgoing_acquisition:
                    if not (
                        relationship["company"].lower() == mentioned.lower()
                        and relationship["relationship"] == "ACQUIRED"
                    ):
                        continue

                elif relationship_intent is not None:
                    if relationship["relationship"] != relationship_intent:
                        continue

                relationship_pairs.append({
                    "company": relationship["company"],
                    "relationship": relationship["relationship"],
                    "related_company": relationship["related_company"]
                })

        else:
            # No explicit company: do not manufacture relationship evidence.
            relationship_pairs = []

    # For a multi-hop question, evidence comes only from the selected path.
    if is_through:
        for path in target_path:
            relationship_pairs.append({
                "company": path["first_company"],
                "relationship": path["first_relationship"],
                "related_company": path["middle_company"]
            })
            relationship_pairs.append({
                "company": path["middle_company"],
                "relationship": path["second_relationship"],
                "related_company": path["final_company"]
            })

    # Remove duplicates while preserving graph order.
    unique_pairs = []
    seen = set()

    for pair in relationship_pairs:
        key = (
            pair["company"],
            pair["relationship"],
            pair["related_company"]
        )
        if key not in seen:
            seen.add(key)
            unique_pairs.append(pair)

    return unique_pairs


# ==========================================
# DETERMINISTIC FACTUAL ANSWER EXTRACTION
# ==========================================

def extract_explicit_answer(
    question,
    document_context,
    relationship_evidence
):
    """
    Extract answers only from evidence that is relevant to the question.

    Relationship/date/value answers use the structured relationship evidence
    selected by the graph. General document facts continue to use retrieved
    document context.
    """

    # --------------------------------------
    # Platform-name questions
    # --------------------------------------
    platform_question = re.search(
        r"\b(name|what is the name)\b.*\b(platform)\b",
        question,
        re.IGNORECASE
    )

    if platform_question:
        platform_match = re.search(
            r"full stack end-to-end solution for the AV market "
            r"under the\s+"
            r"([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)*)"
            r"\s+platform",
            document_context
        )
        if platform_match:
            return platform_match.group(1) + " platform"

    # --------------------------------------
    # Generic "what is the name" questions
    # --------------------------------------
    name_question = re.search(
        r"\b(what is|what's|what was)\b.*\bname\b",
        question,
        re.IGNORECASE
    )

    if name_question:
        name_match = re.search(
            r"\b(?:called|named)\s+([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+){0,6})",
            document_context
        )
        if name_match:
            return name_match.group(1).strip()

    # --------------------------------------
    # Acquisition / subsidiary / agreement
    # entity answers from graph structure
    # --------------------------------------
    relationship_intent = get_relationship_intent(question)
    mentioned_companies = get_mentioned_companies(question)

    if relationship_intent in {"ACQUIRED", "AGREED_TO_ACQUIRE", "HAS_SUBSIDIARY"}:
        matching = [
            evidence for evidence in relationship_evidence
            if evidence["relationship"] == relationship_intent
        ]

        if matching:
            q = question.lower()

            if relationship_intent == "ACQUIRED":
                if re.search(r"\b(who acquired|which company acquired|who bought|which company bought)\b", q):
                    target = mentioned_companies[0] if mentioned_companies else None
                    candidates = [
                        e for e in matching
                        if target is None or e["related_company"].lower() == target.lower()
                    ]
                    if len(candidates) == 1:
                        return f"{candidates[0]['company']} acquired {candidates[0]['related_company']}."

                if re.search(r"\b(which company was acquired by|who was acquired by|what company was acquired by)\b", q):
                    source = mentioned_companies[0] if mentioned_companies else None
                    candidates = [
                        e for e in matching
                        if source is None or e["company"].lower() == source.lower()
                    ]
                    if len(candidates) == 1:
                        return f"{candidates[0]['related_company']} was acquired by {candidates[0]['company']}."

            if relationship_intent == "AGREED_TO_ACQUIRE":
                target = mentioned_companies[0] if mentioned_companies else None
                candidates = [
                    e for e in matching
                    if target is None or e["related_company"].lower() == target.lower()
                ]
                if len(candidates) == 1:
                    return f"{candidates[0]['company']} agreed to acquire {candidates[0]['related_company']}."

            if relationship_intent == "HAS_SUBSIDIARY":
                source = mentioned_companies[0] if mentioned_companies else None
                candidates = [
                    e for e in matching
                    if source is None or e["company"].lower() == source.lower()
                ]
                if len(candidates) == 1:
                    return f"{candidates[0]['related_company']} is a subsidiary of {candidates[0]['company']}."

    # --------------------------------------
    # Date questions: search ONLY the selected
    # relationship evidence.
    #
    # Prefer a date explicitly associated with
    # the action/event asked about, rather than
    # unrelated reference dates in the same evidence.
    # --------------------------------------
    if re.search(r"\b(when|what date|on what date)\b", question, re.IGNORECASE):
        dates = []

        date_pattern = (
            r"(January|February|March|April|May|June|July|August|"
            r"September|October|November|December)\s+\d{1,2},\s+\d{4}"
        )

        action_patterns = [
            rf"\b({date_pattern})\b.{{0,150}}\b("
            r"entered into|entered|signed|executed|agreed to|"
            r"announced|completed|closed"
            r")\b",

            rf"\b({date_pattern})\b.{{0,150}}\b("
            r"agreement|contract|order form|transaction|acquisition|merger"
            r")\b",
        ]

        for evidence in relationship_evidence:
            text = evidence.get("text", "")

            # First preference: date near the event/action.
            for pattern in action_patterns:
                for match in re.finditer(
                    pattern,
                    text,
                    re.IGNORECASE | re.DOTALL
                ):
                    value = match.group(1)
                    if value not in dates:
                        dates.append(value)

        # If exactly one event-associated date was found,
        # return it even if the evidence contains other dates
        # referring to background agreements or documents.
        if len(dates) == 1:
            return dates[0]

        # Fallback: if the evidence contains exactly one date
        # overall, that date is unambiguous.
        all_dates = []

        for evidence in relationship_evidence:
            text = evidence.get("text", "")

            for match in re.finditer(
                rf"\b({date_pattern})\b",
                text,
                re.IGNORECASE
            ):
                value = match.group(1)
                if value not in all_dates:
                    all_dates.append(value)

        if len(all_dates) == 1:
            return all_dates[0]

    # --------------------------------------
    # Amount/value questions: search ONLY the
    # selected relationship evidence.
    # --------------------------------------
    if re.search(r"\b(value|worth|amount|how much)\b", question, re.IGNORECASE):
        amounts = []

        for evidence in relationship_evidence:
            text = evidence.get("text", "")

            patterns = [
                r"initial\s+value\s+of\s+(\$[\d,.]+\s*(?:billion|million|trillion))",
                r"\b(?:value|worth|amount)\s+(?:of\s+)?(\$[\d,.]+\s*(?:billion|million|trillion))"
            ]

            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    value = match.group(1)
                    if value not in amounts:
                        amounts.append(value)

        if len(amounts) == 1:
            return amounts[0]

    return None


# ==========================================
# GENERATE FINAL ANSWER
# ==========================================

def generate_answer(
    question,
    graph_results,
    company_relationships,
    stored_relationship_evidence,
    target_path
):

    # ---------------------------------------------------------
    # Detect relationship-oriented questions
    # ---------------------------------------------------------
    is_relationship_question = bool(
        re.search(
            r"\b(relationship|related|acquired|acquisition|subsidiary|"
            r"subsidiaries|agreement|agreed|owns|owned|affiliate|"
            r"affiliates|partner|partners|through)\b",
            question,
            re.IGNORECASE
        )
    )

    mentioned_companies = get_mentioned_companies(question)

    # ---------------------------------------------------------
    # Build retrieved document context
    # ---------------------------------------------------------
    document_context = ""

    if graph_results:
        document_blocks = []
        for result in graph_results:
            document_blocks.append(
                f"Company: {result['company']}\n"
                f"Document: {result['document']}\n"
                f"Document Type: {result['document_type']}\n"
                f"Document Number: {result['document_number']}\n"
                f"Chunk ID: {result['chunk_id']}\n"
                f"Chunk Number: {result['chunk_number']}\n"
                f"Text: {result['text']}"
            )
        document_context = "\n\n".join(document_blocks)
    else:
        document_context = "No relevant document context was retrieved."

    # ---------------------------------------------------------
    # Deterministic answers are grounded in either the retrieved
    # document or the exact relationship evidence selected by graph.
    # ---------------------------------------------------------
    deterministic_answer = extract_explicit_answer(
        question,
        document_context,
        stored_relationship_evidence
    )

    if deterministic_answer:
        return deterministic_answer

    # ---------------------------------------------------------
    # Direct company relationship questions
    # ---------------------------------------------------------
    through_question = bool(re.search(r"\bthrough\b", question, re.IGNORECASE))

    if len(mentioned_companies) >= 2 and not through_question:
        company_a = mentioned_companies[0]
        company_b = mentioned_companies[1]

        matching_relationships = [
            r for r in company_relationships
            if (
                (r["company"].lower() == company_a.lower()
                 and r["related_company"].lower() == company_b.lower())
                or
                (r["company"].lower() == company_b.lower()
                 and r["related_company"].lower() == company_a.lower())
            )
        ]

        relationship_intent = get_relationship_intent(question)
        if relationship_intent:
            matching_relationships = [
                r for r in matching_relationships
                if r["relationship"] == relationship_intent
            ]

        if matching_relationships:
            lines = [
                f'{r["company"]} --[{r["relationship"]}]--> {r["related_company"]}'
                for r in matching_relationships
            ]
            return (
                f"The relationship between {company_a} and {company_b} is:\n\n"
                + "\n".join(lines)
            )

    # ---------------------------------------------------------
    # Direct one-company relationship questions
    # ---------------------------------------------------------
    if len(mentioned_companies) == 1 and not through_question:
        company = mentioned_companies[0]
        relationship_intent = get_relationship_intent(question)
        matching_relationships = [
            r for r in company_relationships
            if (
                r["company"].lower() == company.lower()
                or r["related_company"].lower() == company.lower()
            )
            and (
                relationship_intent is None
                or r["relationship"] == relationship_intent
            )
        ]

        q = question.lower()
        if re.search(r"\b(who acquired|which company acquired|who bought|which company bought)\b", q):
            matching_relationships = [
                r for r in matching_relationships
                if r["related_company"].lower() == company.lower()
                and r["relationship"] == "ACQUIRED"
            ]
        elif re.search(r"\b(which company was acquired by|who was acquired by|what company was acquired by)\b", q):
            matching_relationships = [
                r for r in matching_relationships
                if r["company"].lower() == company.lower()
                and r["relationship"] == "ACQUIRED"
            ]

        if matching_relationships and re.search(
            r"\b(relationship|related|subsidiary|subsidiaries|agreement|acquired|acquisition|owns|owned|affiliate|affiliates|partner|partners)\b",
            question,
            re.IGNORECASE
        ):
            lines = [
                f'{r["company"]} --[{r["relationship"]}]--> {r["related_company"]}'
                for r in matching_relationships
            ]
            return "\n".join(lines)

    # ---------------------------------------------------------
    # Deterministic answer for "through X" questions
    # ---------------------------------------------------------
    if through_question:
        through_match = re.search(
            r"\bthrough\s+(.+?)(?:\?|$)",
            question,
            re.IGNORECASE
        )

        if through_match:
            through_text = through_match.group(1).strip()
            middle_company = None

            for company in KNOWN_COMPANIES:
                if re.search(rf"\b{re.escape(company)}\b", through_text, re.IGNORECASE):
                    middle_company = company
                    break

            matching_paths = [
                path for path in target_path
                if middle_company is None
                or path["middle_company"].lower() == middle_company.lower()
            ]

            if matching_paths:
                final_companies = sorted({path["final_company"] for path in matching_paths})
                if len(final_companies) == 1:
                    return (
                        f"The company reached through "
                        f"{matching_paths[0]['middle_company']} is "
                        f"{final_companies[0]}."
                    )

    # ---------------------------------------------------------
    # Build graph-specific context only when relevant
    # ---------------------------------------------------------
    if is_relationship_question:
        graph_relationship_text = (
            "\n".join(
                f'{r["company"]} --[{r["relationship"]}]--> {r["related_company"]}'
                for r in company_relationships
            )
            if company_relationships
            else "No company relationships found."
        )

        if target_path:
            two_hop_text = "\n".join(
                f'{path["first_company"]} --[{path["first_relationship"]}]--> '
                f'{path["middle_company"]} --[{path["second_relationship"]}]--> '
                f'{path["final_company"]}'
                for path in target_path
            )
        else:
            two_hop_text = "No explicitly selected two-hop paths."

        if stored_relationship_evidence:
            evidence_text = "\n\n".join(
                f"Company: {e['company']}\n"
                f"Relationship: {e['relationship']}\n"
                f"Related Company: {e['related_company']}\n"
                f"Evidence ID: {e['evidence_id']}\n"
                f"Supporting Chunk: {e['chunk_id']}\n"
                f"Chunk Number: {e['chunk_number']}\n"
                f"Evidence Text: {e['text']}"
                for e in stored_relationship_evidence
            )
        else:
            evidence_text = "No relationship evidence found."

        graph_section = f"""
GRAPH RELATIONSHIPS:

{graph_relationship_text}

SELECTED TWO-HOP GRAPH PATHS:

{two_hop_text}

RELATIONSHIP EVIDENCE:

{evidence_text}
"""
    else:
        graph_section = ""

    # ---------------------------------------------------------
    # Final LLM fallback
    # ---------------------------------------------------------
    prompt = f"""
You are GraphMind, a Knowledge Graph RAG system for answering questions using SEC documents.

USER QUESTION:
{question}

{graph_section}

RETRIEVED DOCUMENT CONTEXT:
{document_context}

STRICT RULES:
1. Answer the user's question directly.
2. Use retrieved SEC text for factual claims.
3. Treat graph relationships as authoritative for relationship structure.
4. For multi-hop questions, use ONLY the explicitly selected two-hop paths.
5. Never infer a relationship from co-occurrence in a document.
6. Keep different relationship types separate.
7. Never reverse a directed relationship.
8. Never invent companies, relationships, dates, amounts, or other facts.
9. Use relationship evidence only for the exact relationship it supports.
10. If the evidence is insufficient or ambiguous, say: Insufficient information in the retrieved documents.
11. Do not answer a different question.
12. Keep the answer concise.
13. For "through" questions, return the final company from the selected path.
14. Return only the final answer.
"""

    response = ollama.chat(
        model="llama3.1:8b",
        messages=[
            {
                "role": "system",
                "content": """
You are a strict question-answering engine.
Answer ONLY the USER QUESTION using the supplied GraphMind context.
Do not use outside knowledge. Do not infer missing relationships or facts.
If the context is insufficient or ambiguous, return exactly:
Insufficient information in the retrieved documents.
Return only the answer.
"""
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        options={
            "temperature": 0,
            "num_predict": 50
        }
    )

    return response["message"]["content"].strip()


# ==========================================
# MAIN GRAPH RAG PIPELINE
# ==========================================

try:

    with driver.session(
    database="graphmind"
    ) as session:
        graph_results = session.execute_read(get_graph_context, chunk_ids)

        # ---------------------------------------------------------
        # Retrieval routing
        #
        # Relationship-specific graph retrieval should only run
        # when the question actually asks about a relationship.
        # Ordinary factual/entity questions use the retrieved
        # document context without pulling unrelated graph edges.
        # ---------------------------------------------------------
        relationship_intent = get_relationship_intent(question)

        relationship_question = (
            relationship_intent is not None
            or re.search(
                r"\b(relationship|related to|connected to|connection|"
                r"link between|linked to|associated with)\b",
                question,
                re.IGNORECASE
            )
        )

        if relationship_question:
            companies = list(
                set(result["company"] for result in graph_results)
            )

            question_lower = question.lower()

            for company in KNOWN_COMPANIES:
                if (
                    company.lower() in question_lower
                    and company not in companies
                ):
                    companies.append(company)

            company_relationships = session.execute_read(
                get_company_relationships,
                companies
            )

            all_two_hop_relationships = session.execute_read(
                get_two_hop_relationships,
                companies
            )

            target_path = select_target_path(
                question,
                all_two_hop_relationships
            )

            relationship_pairs = build_relationship_pairs(
                question,
                company_relationships,
                target_path
            )

            stored_relationship_evidence = session.execute_read(
                get_relationship_evidence,
                relationship_pairs
            )

        else:
            # Normal factual/entity question:
            # no relationship graph retrieval is required.
            companies = []
            company_relationships = []
            all_two_hop_relationships = []
            target_path = []
            relationship_pairs = []
            stored_relationship_evidence = []


        # ----------------------------------
        # Generate answer
        # ----------------------------------

        answer = generate_answer(
            question,
            graph_results,
            company_relationships,
            stored_relationship_evidence,
            target_path
        )


        # ==================================
        # FINAL ANSWER
        # ==================================

        print("\n" + "=" * 60)
        print("FINAL GRAPHMIND ANSWER")
        print("=" * 60)

        print(answer)


finally:

    driver.close()


# ==========================================
# DISPLAY GRAPH RETRIEVAL RESULTS
# ==========================================

print("\n==========================================")
print("GRAPH RETRIEVAL RESULTS")
print("==========================================\n")


if not graph_results:

    print(
        "No matching chunks were found in Neo4j."
    )

else:

    for rank, result in enumerate(
        graph_results,
        start=1
    ):

        print(
            f"--- Graph Result {rank} ---"
        )

        print(
            f"Company: {result['company']}"
        )

        print(
            f"Document: {result['document']}"
        )

        print(
            f"Document Type: "
            f"{result['document_type']}"
        )

        print(
            f"Document Number: "
            f"{result['document_number']}"
        )

        print(
            f"Chunk ID: {result['chunk_id']}"
        )

        print(
            f"Chunk Number: "
            f"{result['chunk_number']}"
        )

        print(
            f"Text: {result['text'][:500]}"
        )

        print()


# ==========================================
# DISPLAY COMPANY RELATIONSHIPS
# ==========================================

print("\n==========================================")
print("COMPANY RELATIONSHIPS")
print("==========================================\n")


if not company_relationships:

    print(
        "No company relationships found."
    )

else:

    for relationship in company_relationships:

        print(
            f"{relationship['company']} "
            f"--[{relationship['relationship']}]--> "
            f"{relationship['related_company']}"
        )


# ==========================================
# DISPLAY SELECTED TWO-HOP PATHS
# ==========================================

print("\n" + "=" * 42)
print("RELEVANT TWO-HOP RELATIONSHIPS")
print("=" * 42)


if target_path:

    for rel in target_path:

        print(
            f"{rel['first_company']} "
            f"--[{rel['first_relationship']}]--> "
            f"{rel['middle_company']} "
            f"--[{rel['second_relationship']}]--> "
            f"{rel['final_company']}"
        )

else:

    print(
        "No relevant two-hop relationships "
        "found for this question."
    )


# ==========================================
# DISPLAY RELATIONSHIP EVIDENCE
# ==========================================

print("\n==========================================")
print("RELEVANT RELATIONSHIP EVIDENCE")
print("==========================================\n")


if not stored_relationship_evidence:

    print(
        "No relationship evidence available for this question."
    )

else:

    for rank, result in enumerate(
        stored_relationship_evidence,
        start=1
    ):

        print(
            f"--- Evidence Result {rank} ---"
        )

        print(
            f"Company: "
            f"{result['company']}"
        )

        print(
            f"Relationship: "
            f"{result['relationship']}"
        )

        print(
            f"Related Company: "
            f"{result['related_company']}"
        )

        print(
            f"Evidence ID: "
            f"{result['evidence_id']}"
        )

        print(
            f"Supporting Chunk: "
            f"{result['chunk_id']}"
        )

        print(
            f"Chunk Number: "
            f"{result['chunk_number']}"
        )

        print(
            f"Evidence Text: "
            f"{result['text'][:700]}"
        )

        print()