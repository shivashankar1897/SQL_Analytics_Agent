# tests/test_chart_tools.py
# Author: Suresh D R | AI Product Developer & Technology Mentor

import pandas as pd

from src.tools.chart_tools import build_chart, pick_chart_type


def test_two_column_df_picks_bar():
    df = pd.DataFrame({"region": ["North", "South"], "revenue": [100, 200]})
    assert pick_chart_type(df) == "bar"


def test_date_column_picks_line():
    df = pd.DataFrame({"order_date": ["2026-01-01", "2026-02-01"], "revenue": [100, 200]})
    assert pick_chart_type(df) == "line"


def test_empty_df_picks_table():
    df = pd.DataFrame()
    assert pick_chart_type(df) == "table"


def test_build_chart_returns_json_for_bar():
    df = pd.DataFrame({"region": ["North", "South"], "revenue": [100, 200]})
    chart_json, chart_type = build_chart(df, "Test")
    assert chart_type == "bar"
    assert chart_json is not None
    assert "data" in chart_json
