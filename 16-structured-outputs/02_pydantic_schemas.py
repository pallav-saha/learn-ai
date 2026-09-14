"""
02 - Pydantic Schemas: define + validate the shape of LLM output

JSON mode (file 01) guarantees valid JSON, but NOT that it has the right fields/types.
Pydantic lets you define the EXACT shape you expect as a Python class, then validate the
LLM's JSON against it. If the model returns a wrong type or misses a field, you catch it
immediately (instead of crashing later when you use the data).

Think of a Pydantic model as a CONTRACT for the data.

Run:
    cd 16-structured-outputs && ../.venv/bin/python3 02_pydantic_schemas.py
"""

import os
import json
from typing import Literal
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)
MODEL = "openai/gpt-oss-20b"


# ============================================================
# DEFINE THE SCHEMA — the shape we expect back
# ============================================================
# Each field has a name + type. Pydantic enforces these.

class Product(BaseModel):
    name: str
    price: float
    in_stock: bool
    # Literal restricts to specific allowed values (like an enum)
    category: Literal["electronics", "clothing", "food", "other"]
    # Field(...) lets you add constraints and descriptions
    rating: float = Field(ge=0, le=5, description="rating from 0 to 5")


# ============================================================
# GET THE LLM TO FILL THE SCHEMA
# ============================================================

def extract_product(description: str) -> Product:
    """
    Ask the LLM to extract product info, then VALIDATE against the Product schema.

    Pydantic v2 can generate a JSON schema from the model — we put it in the prompt
    so the LLM knows the exact shape to return.

    Product.model_json_schema() reads that class and produces a dictionary describing it:
    {
    "title": "Product",
    "type": "object",
    "properties": {
        "name":     {"type": "string", "title": "Name"},
        "price":    {"type": "number", "title": "Price"},
        "in_stock": {"type": "boolean", "title": "In Stock"},
        "category": {"enum": ["electronics", "clothing", "food", "other"], "type": "string"},
        "rating":   {"type": "number", "minimum": 0, "maximum": 5, "description": "rating from 0 to 5"}
    },
    "required": ["name", "price", "in_stock", "category", "rating"]
    }


    """
    schema = Product.model_json_schema()

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Extract product info from this description:\n{description}\n\n"
                    f"Respond ONLY as JSON matching this schema:\n{json.dumps(schema)}"
                ),
            }
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )

    raw = json.loads(response.choices[0].message.content)

    # VALIDATE: this raises ValidationError if the data doesn't match the schema
    # (wrong type, missing field, rating out of range, invalid category, etc.)
    return Product(**raw)


# ============================================================
# DEMO
# ============================================================

def main():
    print("=" * 60)
    print("  Pydantic Schemas — validate the LLM's structured output")
    print("=" * 60)

    print("\n  Our schema (the contract):")
    print("    Product(name:str, price:float, in_stock:bool,")
    print("            category:[electronics|clothing|food|other], rating:0-5)")

    descriptions = [
        "The new UltraBook Pro laptop costs $1299.99, currently available, "
        "rated 4.5 stars. It's an electronics item.",

        "Organic almond butter, $12.50 a jar, in stock, 4.8 rating, food category.",
    ]

    for desc in descriptions:
        print(f"\n  Description: {desc[:60]}...")
        try:
            product = extract_product(desc)
            # product is now a validated Python object — safe to use
            print(f"    ✓ Validated Product:")
            print(f"      name={product.name!r}, price=${product.price}, "
                  f"in_stock={product.in_stock}")
            print(f"      category={product.category!r}, rating={product.rating}")
            # You can use it like any Python object:
            print(f"      → product.price * 1.1 (with tax) = ${product.price * 1.1:.2f}")
        except ValidationError as e:
            print(f"    ✗ Validation failed: {e}")

    # ============================================================
    # Show what happens when data is INVALID
    # ============================================================
    print("\n" + "=" * 60)
    print("  What if the data is INVALID? Pydantic catches it:")
    print("=" * 60)

    bad_examples = [
        {"name": "Widget", "price": "not a number", "in_stock": True,
         "category": "electronics", "rating": 4},              # price wrong type
        {"name": "Gadget", "price": 9.99, "in_stock": True,
         "category": "toys", "rating": 3},                     # invalid category
        {"name": "Thing", "price": 5.0, "in_stock": True,
         "category": "food", "rating": 9},                     # rating out of range
    ]
    for bad in bad_examples:
        try:
            Product(**bad)
            print(f"    (unexpectedly valid: {bad})")
        except ValidationError as e:
            # Grab the first error for a concise message
            err = e.errors()[0]
            print(f"    ✗ Rejected: {err['loc'][0]} — {err['msg']}")

    print("\n  Pydantic is your safety net: it guarantees the data matches your")
    print("  contract BEFORE your code uses it. Never trust raw LLM JSON blindly.")


if __name__ == "__main__":
    main()
