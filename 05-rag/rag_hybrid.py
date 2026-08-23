"""
Hybrid RAG — Handles both documents AND structured data (tables)

This combines two approaches:
1. DOCUMENTS (txt, pdf, docx) → Semantic search via ChromaDB
2. TABLES (csv, xlsx) → LLM writes pandas code to query the data

The LLM decides which approach to use based on your question:
- "What is the refund policy?" → searches documents
- "What is Alice's salary?" → queries the table with pandas
- "Who earns more than 100K?" → queries the table with pandas

Run: python3 rag_hybrid.py
"""

import os
import json
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
import chromadb
from chromadb.utils import embedding_functions
from file_loaders import load_file
from utils import retry_on_failure

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

MODEL = "openai/gpt-oss-20b"


# ============================================================
# SETUP: ChromaDB for documents
# ============================================================

CHROMA_DB_PATH = "./chroma_db_hybrid"

chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)
collection = chroma_client.get_or_create_collection(
    name="hybrid_docs",
    embedding_function=embedding_fn,
)


# ============================================================
# SETUP: Load CSV/Excel files into pandas DataFrames
# ============================================================

def load_dataframes(folder_path: str) -> dict[str, pd.DataFrame]:
    """Load all CSV/Excel files into DataFrames."""
    dataframes = {}
    for filename in sorted(os.listdir(folder_path)):
        filepath = os.path.join(folder_path, filename)
        if filename.endswith(".csv"):
            dataframes[filename] = pd.read_csv(filepath)
        elif filename.endswith((".xlsx", ".xls")):
            dataframes[filename] = pd.read_excel(filepath)
    return dataframes


# ============================================================
# SETUP: Index documents (non-table files) into ChromaDB
# ============================================================

def chunk_text(text: str, source: str, chunk_size: int = 300) -> list[dict]:
    """Split text into chunks."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    for para in paragraphs:
        if len(para) > chunk_size:
            sentences = para.split(". ")
            current_chunk = ""
            for sentence in sentences:
                if len(current_chunk) + len(sentence) > chunk_size:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    current_chunk += ". " + sentence if current_chunk else sentence
            if current_chunk:
                chunks.append(current_chunk.strip())
        else:
            chunks.append(para)

    return [
        {"text": chunk, "source": source, "chunk_index": i}
        for i, chunk in enumerate(chunks)
    ]


def index_documents(folder_path: str):
    """Index non-table files into ChromaDB."""
    table_extensions = {".csv", ".xlsx", ".xls"}

    for filename in sorted(os.listdir(folder_path)):
        ext = os.path.splitext(filename)[1].lower()
        if ext in table_extensions:
            continue  # Skip tables — handled by pandas

        filepath = os.path.join(folder_path, filename)
        try:
            content = load_file(filepath)
            if not content.strip():
                continue

            chunks = chunk_text(content, source=filename)

            # Only add new chunks
            for chunk in chunks:
                chunk_id = f"{chunk['source']}_{chunk['chunk_index']}"
                existing = collection.get(ids=[chunk_id])
                if not existing["ids"]:
                    collection.add(
                        documents=[chunk["text"]],
                        ids=[chunk_id],
                        metadatas=[{"source": chunk["source"]}],
                    )
        except Exception as e:
            print(f"   ⚠️  Skipped {filename}: {e}")

    print(f"   📚 Documents in ChromaDB: {collection.count()} chunks")


# ============================================================
# TOOL 1: Search documents (semantic search)
# ============================================================

def search_documents(question: str, top_k: int = 5) -> str:
    """Search ChromaDB for relevant document chunks."""
    results = collection.query(query_texts=[question], n_results=top_k)

    if not results["documents"][0]:
        return "No relevant documents found."

    context = ""
    for i, (doc, meta) in enumerate(zip(results["documents"][0], results["metadatas"][0])):
        context += f"\n[Source: {meta['source']}]\n{doc}\n"

    return context


# ============================================================
# TOOL 2: Query tables with pandas (LLM writes the code)
# ============================================================

@retry_on_failure(max_retries=3, delay=1.0)
def query_table(question: str, dataframes: dict[str, pd.DataFrame]) -> str:
    """
    LLM writes pandas code to answer questions about tables.
    Then we execute that code and return the result.
    """
    # Build a description of available data
    data_description = ""
    for name, df in dataframes.items():
        data_description += f"\nDataFrame '{name}':\n"
        data_description += f"  Columns: {df.columns.tolist()}\n"
        data_description += f"  Sample rows:\n{df.head(3).to_string()}\n"
        data_description += f"  Shape: {df.shape[0]} rows, {df.shape[1]} columns\n"

    # Ask LLM to write pandas code
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a data analyst. Write pandas code to answer the user's question. "
                    "The DataFrames are already loaded. Use the variable names exactly as shown. "
                    "Return ONLY the Python code, no explanation. "
                    "The code should print the answer. Use print() for the final output."
                ),
            },
            {
                "role": "user",
                "content": f"Available data:\n{data_description}\n\nQuestion: {question}\n\nWrite pandas code to answer this:",
            },
        ],
        temperature=0.0,
    )

    code = response.choices[0].message.content.strip()
    # Remove markdown code fences if present
    code = code.replace("```python", "").replace("```", "").strip()

    print(f"   💻 Generated code:\n      {code.replace(chr(10), chr(10) + '      ')}")

    # Execute the code safely
    try:
        # Create a local namespace with the dataframes
        local_vars = {}
        for name, df in dataframes.items():
            # Use the filename without extension as variable name
            var_name = os.path.splitext(name)[0]
            local_vars[var_name] = df
            local_vars["df"] = df  # Also make it available as 'df'

        local_vars["pd"] = pd

        # Capture print output
        import io
        import sys
        output_buffer = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = output_buffer

        exec(code, {"__builtins__": __builtins__}, local_vars)

        sys.stdout = old_stdout
        result = output_buffer.getvalue().strip()

        if result:
            return result
        else:
            return "Code executed but produced no output."

    except Exception as e:
        return f"Error executing code: {e}"


# ============================================================
# ROUTER: Decide which tool to use
# ============================================================

@retry_on_failure(max_retries=3, delay=1.0)
def route_question(question: str, dataframes: dict[str, pd.DataFrame]) -> str:
    """
    LLM decides: is this a document question or a data/table question?
    
    This is the HYBRID part — one system that handles both.
    """
    # Build context about what data is available
    table_info = ""
    for name, df in dataframes.items():
        table_info += f"- {name}: columns = {df.columns.tolist()}\n"

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a router that decides how to answer a question. "
                    "Respond with ONLY one word: 'documents' or 'table'.\n\n"
                    "Use 'table' if the question is about specific data, numbers, filtering, "
                    "aggregation, or looking up specific values from structured data.\n"
                    "Use 'documents' if the question is about policies, procedures, plans, "
                    "meeting notes, or general knowledge from text documents."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Available tables:\n{table_info}\n\n"
                    f"Available documents: company policies, meeting notes, product plans, whiteboard notes\n\n"
                    f"Question: {question}\n\n"
                    f"Route to (documents or table):"
                ),
            },
        ],
        temperature=0.0,
    )

    route = response.choices[0].message.content.strip().lower()
    return "table" if "table" in route else "documents"


# ============================================================
# MAIN: Answer questions using the right approach
# ============================================================

@retry_on_failure(max_retries=3, delay=1.0)
def answer_with_context(question: str, context: str, source_type: str) -> str:
    """Send context + question to LLM for final answer."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    f"You are a helpful assistant. Answer based on the provided {source_type} data. "
                    "Be concise and direct."
                ),
            },
            {
                "role": "user",
                "content": f"Data:\n{context}\n\nQuestion: {question}",
            },
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content


def ask(question: str, dataframes: dict[str, pd.DataFrame]) -> str:
    """
    The hybrid pipeline:
    1. Route the question (documents or table?)
    2. Use the right tool
    3. Return the answer
    """
    # Step 1: Route
    print(f"\n🔍 Question: \"{question}\"")
    route = route_question(question, dataframes)
    print(f"   🔀 Routed to: {route.upper()}")

    # Step 2: Get context using the right tool
    if route == "table":
        print(f"   📊 Querying table with pandas...")
        result = query_table(question, dataframes)
        print(f"   📋 Result: {result}")
        # For table queries, the result IS the answer
        answer = answer_with_context(question, f"Query result: {result}", "table")
    else:
        print(f"   📚 Searching documents...")
        context = search_documents(question)
        preview = context[:200] + "..." if len(context) > 200 else context
        print(f"   📎 Found context: {preview}")
        answer = answer_with_context(question, context, "document")

    return answer


# ============================================================
# INTERACTIVE DEMO
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  🔀 HYBRID RAG — Documents + Tables")
    print("=" * 60)

    docs_folder = os.path.join(os.path.dirname(__file__), "..", "sample_docs")

    # Load tables
    print("\n📊 Loading tables (CSV/Excel)...")
    dataframes = load_dataframes(docs_folder)
    for name, df in dataframes.items():
        print(f"   ✅ {name}: {df.shape[0]} rows, {df.shape[1]} columns")

    # Index documents
    print("\n📚 Indexing documents into ChromaDB...")
    index_documents(docs_folder)

    print("\n✅ Ready! I can answer questions about BOTH documents and data.")
    print("\n📊 TABLE questions (will use pandas):")
    print('  • "What is Alice\'s salary?"')
    print('  • "Who earns more than 100K?"')
    print('  • "What is the average salary by department?"')
    print('  • "How many people work in Engineering?"')

    print("\n📚 DOCUMENT questions (will search ChromaDB):")
    print('  • "What is the refund policy?"')
    print('  • "When is the product launching?"')
    print('  • "What are the sprint goals?"')
    print('  • "When is the next meeting?"')

    print("\n" + "-" * 60)
    print("Type 'quit' to exit.\n")

    while True:
        question = input("❓ Your question: ").strip()
        if question.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break
        if not question:
            continue

        answer = ask(question, dataframes)
        print(f"\n💬 Answer:\n{answer}")
        print("\n" + "=" * 60)
