"""
06 - Strict / Native Structured Outputs (json_schema mode)

File 01 used response_format={"type": "json_object"} — that guarantees VALID JSON,
but NOT that it matches your fields/types (you had to describe the shape in the prompt
and validate with Pydantic afterward).

STRICT mode (response_format={"type": "json_schema", ...}) goes further: you give the
API your schema, and it GUARANTEES the output matches it — right fields, right types,
enforced at the API level. No "please return this shape" prompting needed.

  json_object  =  "give me some valid JSON"          (shape not guaranteed)
  json_schema  =  "give me JSON matching THIS schema" (shape guaranteed by the API)

Tested on Groq: openai/gpt-oss-20b supports json_schema.

Run:
    cd 16-structured-outputs && ../.venv/bin/python3 06_strict_schema.py
"""

import os
import json
from pydantic import BaseModel
from typing import Literal
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)
MODEL = "openai/gpt-oss-20b"


# ============================================================
# 1. JSON MODE (from file 01) — valid JSON, shape NOT guaranteed
# ============================================================

def json_mode(text: str):
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content":
                   f"Extract name and price from: {text}\n"
                   'Return JSON like {"name": ..., "price": ...}'}],
        response_format={"type": "json_object"},   # just "be valid JSON"
    )
    return response.choices[0].message.content


# ============================================================
# 2. STRICT SCHEMA MODE — shape guaranteed by the API
# ============================================================
# You pass a JSON Schema. The API enforces that the output matches it:
# exact fields, exact types, no extras.

def strict_schema(text: str):
    schema = {
        "name": "product",           # a name for the schema
        "schema": {                  # the actual JSON Schema
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "price": {"type": "number"},
                "category": {"type": "string", "enum": ["electronics", "food", "other"]},
            },
            "required": ["name", "price", "category"],
            "additionalProperties": False,   # no extra fields allowed
        },
    }
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": f"Extract product info from: {text}"}],
        response_format={
            "type": "json_schema",   # ← strict mode
            "json_schema": schema,
        },
    )
    # Guaranteed to match the schema → safe to parse
    return json.loads(response.choices[0].message.content)


# ============================================================
# 3. STRICT SCHEMA straight from a Pydantic model (the clean way)
# ============================================================
# Pydantic can GENERATE the JSON schema, so you define the shape ONCE as a class.

class Person(BaseModel):
    name: str
    age: int
    role: Literal["engineer", "manager", "designer", "other"]


def strict_from_pydantic(text: str) -> Person:
    schema = {
        "name": "person",
        "schema": Person.model_json_schema(),   # auto-generated from the class
    }
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": f"Extract person info from: {text}"}],
        response_format={"type": "json_schema", "json_schema": schema},
    )
    raw = json.loads(response.choices[0].message.content)
    return Person(**raw)   # validate into a typed object


# ============================================================
# DEMO
# ============================================================

def main():
    print("=" * 60)
    print("  Strict / Native Structured Outputs (json_schema)")
    print("=" * 60)

    # 1. json_object — valid JSON but you hope the shape is right
    print("\n  [1] json_object mode (valid JSON, shape NOT enforced):")
    out = json_mode("The DeluxeMixer sells for $79.99.")
    print(f"    Got: {out}")
    print("    ↑ Valid JSON, but field names/types depend on the model following the prompt.")

    # 2. json_schema — the API guarantees the shape
    print("\n  [2] json_schema mode (shape GUARANTEED by the API):")
    data = strict_schema("The DeluxeMixer sells for $79.99. It's a kitchen appliance.")
    print(f"    Got: {data}")
    print(f"    Guaranteed keys: name, price, category — types enforced.")
    print(f"    category is one of the allowed enum values: {data['category']!r}")

    # 3. Pydantic → schema → validated object
    print("\n  [3] Strict schema generated from a Pydantic class:")
    person = strict_from_pydantic("Meet Priya, a 29-year-old software engineer.")
    print(f"    Got typed object: name={person.name!r}, age={person.age}, role={person.role!r}")
    print(f"    (schema came straight from the Person class — one source of truth)")

    print("\n" + "=" * 60)
    print("  json_object  vs  json_schema:")
    print("=" * 60)
    print("""
    json_object:
      + guarantees valid JSON
      - does NOT guarantee fields/types (you prompt for the shape + validate after)

    json_schema (strict):
      + guarantees the output MATCHES your schema (fields, types, enums, no extras)
      + less prompt-engineering ("please return X") — the API enforces it
      - support varies by model/provider (test yours)

  IMPORTANT: strict mode guarantees the SHAPE, not the CORRECTNESS. The model can
  still put the wrong VALUE in a field (e.g., a price in the 'name' field). Always
  sanity-check values for critical data — schema ≠ accuracy.
""")


if __name__ == "__main__":
    main()
