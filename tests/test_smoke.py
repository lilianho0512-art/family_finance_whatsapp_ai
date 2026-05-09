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


# ---------------------------------------------------------------------------
# Step-by-step flow (ask_amount step)
# ---------------------------------------------------------------------------


def test_resolve_amount_answer():
    assert question_engine.resolve_answer("ask_amount", "88.50") == 88.5
    assert question_engine.resolve_answer("ask_amount", "RM 1234.50") == 1234.5
    assert question_engine.resolve_answer("ask_amount", "MYR123") == 123.0
    assert question_engine.resolve_answer("ask_amount", "abc") is None
    assert question_engine.resolve_answer("ask_amount", "0") is None


class _StubRecord:
    def __init__(self, **kw):
        self.record_type = kw.get("record_type", "unknown")
        self.amount = kw.get("amount", 0)
        self.category = kw.get("category", "")
        self.payment_method = kw.get("payment_method", "")
        self.source = kw.get("source", "")
        self.account = kw.get("account", "")


def test_determine_next_asks_amount_after_record_type():
    # Record_type known but amount missing -> ask_amount comes next
    rec = _StubRecord(record_type="expense", amount=0)
    nxt = question_engine.determine_next_question(rec)
    assert nxt is not None
    step, _q, _opts = nxt
    assert step == "ask_amount"


def test_determine_next_skips_amount_when_present():
    rec = _StubRecord(record_type="expense", amount=50.0)
    step, _q, _opts = question_engine.determine_next_question(rec)
    assert step == "ask_category"  # already past ask_amount


def test_determine_next_unknown_type_first():
    rec = _StubRecord(record_type="unknown", amount=0)
    step, _q, _opts = question_engine.determine_next_question(rec)
    assert step == "ask_record_type"  # type still trumps amount


# ---------------------------------------------------------------------------
# Loan service CRUD + family scoping
# ---------------------------------------------------------------------------


def _make_db():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.database import Base
    import app.models  # ensure models register on Base
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _make_family(db, name="TestFam"):
    from app.models import Family
    f = Family(name=name)
    db.add(f)
    db.commit()
    db.refresh(f)
    return f


def test_loan_create_and_list():
    from app.services import loan_service
    from datetime import date as _date
    db = _make_db()
    fam = _make_family(db)
    loan = loan_service.create_loan(
        db, fam.id,
        lender="Maybank Home Loan",
        principal=300000.0,
        monthly_payment=1500.0,
        interest_rate=4.25,
        term_months=360,
        start_date=_date(2026, 1, 1),
        payment_due_day=10,
        notes="30-yr mortgage",
    )
    assert loan.id is not None
    assert loan.kind == "loan"
    assert loan.status == "active"
    assert loan.current_balance == 300000.0  # defaults to principal
    listed = loan_service.list_loans(db, fam.id)
    assert len(listed) == 1 and listed[0].id == loan.id


def test_loan_kind_installment():
    from app.services import loan_service
    db = _make_db()
    fam = _make_family(db)
    plan = loan_service.create_loan(
        db, fam.id,
        lender="Shopee SPayLater",
        principal=1200.0,
        monthly_payment=400.0,
        kind="installment",
    )
    assert plan.kind == "installment"
    # Invalid kind falls back to "loan"
    bad = loan_service.create_loan(
        db, fam.id, lender="x", principal=10, monthly_payment=10, kind="garbage"
    )
    assert bad.kind == "loan"


def test_loan_family_scoping():
    from app.services import loan_service
    db = _make_db()
    fam_a = _make_family(db, "A")
    fam_b = _make_family(db, "B")
    a_loan = loan_service.create_loan(db, fam_a.id, lender="A Bank", principal=100, monthly_payment=10)
    loan_service.create_loan(db, fam_b.id, lender="B Bank", principal=200, monthly_payment=20)
    # Family A only sees their own
    a_loans = loan_service.list_loans(db, fam_a.id)
    assert len(a_loans) == 1 and a_loans[0].id == a_loan.id
    # Cross-family get returns None
    assert loan_service.get_loan(db, fam_b.id, a_loan.id) is None
    # Cross-family delete fails
    assert loan_service.delete_loan(db, fam_b.id, a_loan.id) is False
    # Loan still exists in A
    assert loan_service.get_loan(db, fam_a.id, a_loan.id) is not None


def test_loan_update_close_delete():
    from app.services import loan_service
    db = _make_db()
    fam = _make_family(db)
    loan = loan_service.create_loan(db, fam.id, lender="X", principal=1000, monthly_payment=100)
    # Update
    upd = loan_service.update_loan(db, fam.id, loan.id, monthly_payment=120, current_balance=900)
    assert upd.monthly_payment == 120 and upd.current_balance == 900
    # Close
    closed = loan_service.close_loan(db, fam.id, loan.id)
    assert closed.status == "closed" and closed.current_balance == 0.0
    # Delete
    assert loan_service.delete_loan(db, fam.id, loan.id) is True
    assert loan_service.get_loan(db, fam.id, loan.id) is None


def test_loan_totals():
    from app.services import loan_service
    db = _make_db()
    fam = _make_family(db)
    loan_service.create_loan(db, fam.id, lender="A", principal=500, monthly_payment=50)
    loan_service.create_loan(db, fam.id, lender="B", principal=1000, monthly_payment=100, current_balance=800)
    closed = loan_service.create_loan(db, fam.id, lender="C", principal=300, monthly_payment=30)
    loan_service.close_loan(db, fam.id, closed.id)
    # Totals only count active loans
    assert loan_service.total_monthly_payment(db, fam.id) == 150.0
    assert loan_service.total_outstanding(db, fam.id) == 1300.0  # 500 default + 800 set


def test_loan_due_day_validation():
    from app.services import loan_service
    db = _make_db()
    fam = _make_family(db)
    loan = loan_service.create_loan(
        db, fam.id, lender="X", principal=100, monthly_payment=10, payment_due_day=99
    )
    assert loan.payment_due_day is None  # invalid -> nulled
    upd = loan_service.update_loan(db, fam.id, loan.id, payment_due_day=15)
    assert upd.payment_due_day == 15


# ---------------------------------------------------------------------------
# Excel export Loans sheet
# ---------------------------------------------------------------------------


def test_excel_export_includes_loans_sheet(tmp_path, monkeypatch):
    from openpyxl import load_workbook
    from app.services import excel_export, loan_service
    from app import config as app_config
    db = _make_db()
    fam = _make_family(db)
    loan_service.create_loan(db, fam.id, lender="LoanZ", principal=1000, monthly_payment=100)
    # Redirect output dir so we don't touch the repo
    monkeypatch.setattr(app_config.settings, "OUTPUT_DIR", tmp_path)
    out_path = excel_export.export_monthly(db, fam.id)
    wb = load_workbook(out_path)
    assert "Loans" in wb.sheetnames
    ws = wb["Loans"]
    rows = list(ws.iter_rows(values_only=True))
    header = rows[0]
    assert "Lender" in header and "Monthly Payment" in header
    body = [r for r in rows[1:] if r[0] is not None]  # skip totals padding
    assert any(r[2] == "LoanZ" for r in body)
