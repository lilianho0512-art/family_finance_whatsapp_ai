import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.services import rule_parser, menu_service, question_engine
from app.utils.json_tools import extract_json
from app.utils.money_tools import extract_amount


def test_greeting():
    assert menu_service.is_greeting("Hi")
    assert menu_service.is_greeting("hello")
    assert menu_service.is_greeting("Menu")
    assert not menu_service.is_greeting("Today Tesco RM88")


def test_rule_parse_expense():
    r = rule_parser.parse("Today Tesco RM88")
    assert r["amount"] == 88.0
    assert r["merchant"].lower() == "tesco"


def test_rule_parse_savings():
    r = rule_parser.parse("Today saved RM500")
    assert r["record_type"] == "savings"
    assert r["amount"] == 500.0


def test_rule_parse_income():
    r = rule_parser.parse("Salary RM3800")
    assert r["record_type"] == "income"
    assert r["amount"] == 3800.0
    assert r["source"] == "Salary"


def test_rule_parse_groceries():
    r = rule_parser.parse("Today groceries RM35")
    assert r["amount"] == 35.0
    assert r["category"] == "Groceries"


def test_extract_amount():
    assert extract_amount("RM 88.50") == 88.5
    assert extract_amount("MYR123") == 123.0
    assert extract_amount("Total 99") == 99.0


def test_extract_json_from_markdown():
    raw = '```json\n{"a": 1, "b": "x"}\n```'
    assert extract_json(raw) == {"a": 1, "b": "x"}


def test_extract_json_with_trailing_comma():
    raw = '{"a": 1, "b": 2,}'
    assert extract_json(raw) == {"a": 1, "b": 2}


def test_question_engine_letters():
    assert question_engine.resolve_answer("ask_record_type", "A") == "expense"
    assert question_engine.resolve_answer("ask_category", "A") == "Groceries"
    assert question_engine.resolve_answer("ask_payment_method", "D") == "Touch n Go"
    assert question_engine.resolve_answer("ask_record_type", "Z") is None
