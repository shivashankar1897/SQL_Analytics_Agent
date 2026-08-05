# src/tools/chart_tools.py
# Author: Suresh D R | AI Product Developer & Technology Mentor
#
# Pure pandas/Plotly code -- no LLM call at all. Picks a chart type from
# the real DataFrame's shape and builds the actual chart object.

import pandas as pd
import plotly.express as px


def pick_chart_type(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return "table"
    has_date_col = any("date" in col.lower() or "month" in col.lower() for col in df.columns)
    if has_date_col:
        return "line"
    if len(df.columns) == 2:
        return "bar"
    return "table"


def build_chart(df: pd.DataFrame, title: str):
    """Builds a real Plotly figure from the real query result. Returns
    (fig_as_json_or_None, chart_type) so it can travel over the API as JSON."""
    chart_type = pick_chart_type(df)

    if chart_type == "bar":
        x_col, y_col = df.columns[0], df.columns[1]
        fig = px.bar(df, x=x_col, y=y_col, title=title)
        return fig.to_json(), chart_type

    if chart_type == "line":
        date_col = next(col for col in df.columns if "date" in col.lower() or "month" in col.lower())
        value_col = [col for col in df.columns if col != date_col][0]
        fig = px.line(df, x=date_col, y=value_col, title=title)
        return fig.to_json(), chart_type

    return None, "table"
