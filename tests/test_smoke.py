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


def test_explicit_type_prefixes():
    # Mixed case, since detect_record_type lowercases input
    assert rule_parser.detect_record_type("family expense RM50") == "expense"
    assert rule_parser.detect_record_type("Family Expense Tesco RM50") == "expense"
    assert rule_parser.detect_record_type("family savings RM500") == "savings"
    assert rule_parser.detect_record_type("family income RM3800") == "income"
    assert rule_parser.detect_record_type("family transfer RM200") == "transfer"


def test_transfer_standalone_vs_payment_method():
    # "transfer" alone => transfer record
    assert rule_parser.detect_record_type("transfer RM200 to mom") == "transfer"
    # "bank transfer" / "online transfer" are payment methods, not transfer records
    assert rule_parser.detect_record_type("Tesco RM50 bank transfer") != "transfer"
    assert rule_parser.detect_record_type("Tesco RM50 online transfer") != "transfer"
    # DuitNow keyword
    assert rule_parser.detect_record_type("duitnow RM150 to dad") == "transfer"


def test_query_patterns_match():
    from app.routers.whatsapp import _QUERY_PATTERNS

    def kind_for(text):
        for rx, kind in _QUERY_PATTERNS:
            if rx.search(text):
                return kind
        return None

    assert kind_for("how much did I spend this month") == "month_expense"
    assert kind_for("this month savings") == "month_savings"
    assert kind_for("this month income") == "month_income"
    assert kind_for("savings rate") == "savings_rate"
    assert kind_for("today expense") == "today_expense"
    assert kind_for("monthly summary") == "month_summary"
    assert kind_for("export") == "export"
    assert kind_for("hello there") is None


def test_undo_and_delete_regexes():
    from app.routers.whatsapp import _UNDO_RE, _DELETE_BY_ID_RE
    assert _UNDO_RE.match("undo")
    assert _UNDO_RE.match("/undo")
    assert _UNDO_RE.match("delete last")
    assert _UNDO_RE.match("delete recent")
    assert not _UNDO_RE.match("undo this expense")  # only bare command
    m = _DELETE_BY_ID_RE.match("delete #5")
    assert m and m.group(1) == "5"
    m = _DELETE_BY_ID_RE.match("/del 12")
    assert m and m.group(1) == "12"
    assert not _DELETE_BY_ID_RE.match("delete the cat")


def test_account_command_regexes():
    from app.routers.whatsapp import _BALANCE_LIST_RE, _BALANCE_SET_RE, _ADD_ACCOUNT_RE
    assert _BALANCE_LIST_RE.match("balance")
    assert _BALANCE_LIST_RE.match("Balances")
    assert not _BALANCE_LIST_RE.match("balance Maybank")
    m = _BALANCE_SET_RE.match("set Maybank 5000")
    assert m and m.group(1).strip() == "Maybank" and float(m.group(2)) == 5000.0
    m = _BALANCE_SET_RE.match("set Hong Leong RM 1234.50")
    assert m and m.group(1).strip() == "Hong Leong" and float(m.group(2)) == 1234.5
    m = _ADD_ACCOUNT_RE.match("add account OCBC")
    assert m and m.group(1).strip() == "OCBC"
    assert not _ADD_ACCOUNT_RE.match("add OCBC")
