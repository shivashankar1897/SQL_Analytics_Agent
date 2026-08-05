# tests/test_sql_validator.py
# Author: Suresh D R | AI Product Developer & Technology Mentor

from src.tools.sql_tools import validate_sql


def test_valid_select_passes():
    result = validate_sql("SELECT region, SUM(revenue) FROM orders GROUP BY region")
    assert result["valid"] is True


def test_delete_rejected():
    result = validate_sql("DELETE FROM orders WHERE order_id = 'X'")
    assert result["valid"] is False
    assert "SELECT" in result["reason"]


def test_drop_rejected():
    result = validate_sql("DROP TABLE orders")
    assert result["valid"] is False


def test_injection_attempt_rejected():
    result = validate_sql("SELECT * FROM orders; DROP TABLE orders;")
    assert result["valid"] is False
    assert "DROP" in result["reason"]


def test_unknown_table_rejected():
    result = validate_sql("SELECT * FROM employees_salary_table")
    assert result["valid"] is False
    assert "Unknown table" in result["reason"]


def test_lowercase_select_still_works():
    result = validate_sql("select * from orders")
    assert result["valid"] is True


def test_limit_auto_appended_if_missing():
    result = validate_sql("SELECT * FROM orders")
    assert result["valid"] is True
    assert "LIMIT" in result["sql"].upper()


def test_existing_limit_not_duplicated():
    result = validate_sql("SELECT * FROM orders LIMIT 50")
    assert result["valid"] is True
    assert result["sql"].upper().count("LIMIT") == 1
