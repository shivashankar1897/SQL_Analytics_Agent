

import json
import logging
import re

import pandas as pd
from sqlalchemy import create_engine, text
from openai import OpenAI
from openai import AzureOpenAI
from functools import lru_cache

from src.utils.cache import get_cached_schema, set_cached_schema
from src.utils.config import get_settings

logger = logging.getLogger("sql_agent.sql_tools")

settings = get_settings()


@lru_cache
def get_azure_client() -> AzureOpenAI:
    """Create one Azure OpenAI client."""
    

    return AzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
    )


client = get_azure_client()


KNOWN_TABLES = {
    "customers", "products", "sales_reps", "orders", "marketing_campaigns",
    "campaign_attribution", "support_tickets", "inventory_snapshots",
    "competitor_pricing", "macro_indicators",
}

FORBIDDEN_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER",
    "TRUNCATE", "GRANT", "REVOKE", "CREATE",
}

_SCHEMA_CONTEXT = """
You have access to a PostgreSQL database with these tables and columns.
Each column has a short description — use these to understand what values
to filter on, not just the column name.

customers(
  customer_id,        -- primary key, format CUST_1000, CUST_1001, ...
  name,               -- company name
  region,             -- one of: North, South, East, West
  segment,            -- one of: SMB, Mid-Market, Enterprise
  signup_date,        -- date the customer signed up
  account_tier        -- one of: Basic, Premium, Enterprise
)

products(
  product_id,         -- primary key, format PROD_001, PROD_002, ...
  product_name,       -- descriptive product name
  category,           -- one of: Electronics, Apparel, Home & Kitchen, Sports, Books
  unit_price,         -- price per unit in Rupees, range roughly 500-15000
  launch_date         -- date the product was launched
)

sales_reps(
  sales_rep_id,       -- primary key, format REP_001, REP_002, ...
  name,               -- rep's full name
  region,             -- one of: North, South, East, West
  hire_date,          -- date the rep was hired
  target_quota        -- quarterly revenue target in Rupees, range 500000-2000000
)

orders(
  order_id,           -- primary key, format ORD_00001, ORD_00002, ...
  customer_id,        -- FK to customers
  product_id,         -- FK to products
  sales_rep_id,       -- FK to sales_reps
  order_date,         -- date the order was placed
  quantity,           -- units ordered, integer 1-5
  revenue,            -- total revenue for this order in Rupees
  discount_applied    -- discount as decimal, e.g. 0.05 means 5% off
)

marketing_campaigns(
  campaign_id,        -- primary key, format CAMP_001, CAMP_002, ...
  name,               -- campaign name
  channel,            -- one of: Email, Social
  region,             -- one of: North, South, East, West
  start_date,         -- campaign start date
  end_date,           -- campaign end date — if BEFORE the period asked about, campaign was NOT active
  budget_spent        -- total budget spent in Rupees
)

campaign_attribution(
  order_id,           -- FK to orders
  campaign_id         -- FK to marketing_campaigns — links an order to the campaign that influenced it
)

support_tickets(
  ticket_id,          -- primary key, format TKT_00001, TKT_00002, ...
  customer_id,        -- FK to customers
  order_id,           -- FK to orders
  created_at,         -- date the ticket was created
  issue_type,         -- one of: Billing, Shipping Delay, Product Defect, Account Access, General Inquiry
  resolved,           -- boolean, true if closed
  csat_score          -- customer satisfaction score, integer 2 (worst) to 5 (best)
)

inventory_snapshots(
  product_id,         -- FK to products
  snapshot_date,      -- date of this stock snapshot
  units_in_stock      -- units in stock on this date; below ~100 indicates stockout risk
)

competitor_pricing(
  product_category,   -- one of: Electronics, Apparel, Home & Kitchen, Sports, Books
  snapshot_date,      -- date of this pricing snapshot
  competitor_avg_price -- competitor's average price for this category in Rupees
)

macro_indicators(
  region,             -- one of: North, South, East, West
  month,              -- first day of the month this snapshot covers
  consumer_confidence_index,  -- index value, typically 95-105; higher = more confidence
  unemployment_rate   -- percentage, typically 4.5-7.0
)

Foreign key relationships:
  orders.customer_id -> customers.customer_id
  orders.product_id -> products.product_id
  orders.sales_rep_id -> sales_reps.sales_rep_id
  campaign_attribution.order_id -> orders.order_id
  campaign_attribution.campaign_id -> marketing_campaigns.campaign_id
  support_tickets.customer_id -> customers.customer_id
  support_tickets.order_id -> orders.order_id
  inventory_snapshots.product_id -> products.product_id

Data covers exactly two periods — use these exact date ranges:
  Q4 = 2025-10-01 to 2025-12-31
  Q1 = 2026-01-01 to 2026-03-31
"""


def get_schema_context() -> str:
    cached = get_cached_schema()
    if cached:
        return cached
    set_cached_schema(_SCHEMA_CONTEXT)
    return _SCHEMA_CONTEXT


def get_engine():
    """Returns a SQLAlchemy engine — required by pd.read_sql_query."""
    return create_engine(settings.DATABASE_URL)


def generate_sql(question: str, conversation_history: list = None) -> dict:
    """Writes real SQL from schema + question. Includes conversation history
    so follow-up questions like 'now break that down by region' have context."""
    schema = get_schema_context()
    system_prompt = f"""You are a PostgreSQL expert. Given the schema below and a
business question, write ONE SQL query that answers it.

{schema}

Rules:
- Write ONLY a SELECT statement — never INSERT, UPDATE, DELETE, DROP
- Always include a LIMIT clause (default 100 if not specified)
- Use proper JOINs based on the foreign keys given above
- Return ONLY this JSON object: {{"sql": "the SQL query text", "explanation": "one sentence"}}"""

    messages = [{"role": "system", "content": system_prompt}]

    # Add conversation history for follow-up context
    if conversation_history:
        for turn in conversation_history[-4:]:  # last 4 turns max
            messages.append({"role": "user", "content": turn.get("question", "")})
            messages.append({"role": "assistant", "content": turn.get("answer", "")})

    messages.append({"role": "user", "content": question})

    resp = client.chat.completions.create(
        model="gpt-5.4-nano",
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(resp.choices[0].message.content)


def validate_sql(sql: str) -> dict:
    """Safety gate — 4 sequential checks, fail-closed at every step."""
    sql_upper = sql.upper().strip()
    if not sql_upper.startswith("SELECT"):
        return {"valid": False, "reason": "Query must start with SELECT", "sql": sql}
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(r"\b" + keyword + r"\b", sql_upper):
            return {"valid": False, "reason": f"Forbidden keyword: {keyword}", "sql": sql}
    found_pairs = re.findall(r"FROM\s+(\w+)|JOIN\s+(\w+)", sql, re.IGNORECASE)
    referenced = {t for pair in found_pairs for t in pair if t}
    unknown = referenced - KNOWN_TABLES
    if unknown:
        return {"valid": False, "reason": f"Unknown table(s): {unknown}", "sql": sql}
    if "LIMIT" not in sql_upper:
        sql = sql.rstrip(";") + " LIMIT 100;"
    return {"valid": True, "reason": "Passed all checks", "sql": sql}


def execute_query(sql: str) -> pd.DataFrame:
    """Runs validated SQL as read-only DB user via SQLAlchemy."""
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql_query(text(sql), conn)
    return df


def run_sql_pipeline(question: str, conversation_history: list = None) -> dict:
    """Generate -> validate -> execute."""
    gen = generate_sql(question, conversation_history)
    validated = validate_sql(gen["sql"])
    if not validated["valid"]:
        logger.warning(f"SQL rejected: {validated['reason']} | question={question[:80]}")
        return {"success": False, "reason": validated["reason"], "df": None, "sql": gen["sql"]}
    df = execute_query(validated["sql"])
    return {"success": True, "sql": validated["sql"], "df": df}
