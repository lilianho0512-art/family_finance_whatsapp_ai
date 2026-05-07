from datetime import date
from typing import Optional
from openpyxl import Workbook
from openpyxl.styles import Font
from sqlalchemy.orm import Session
from app.config import settings
from app.services import record_service
from app.utils.date_tools import month_range

HEADERS = [
    "ID", "Date", "Type", "Merchant", "Amount", "Currency", "Category",
    "Payment Method", "Source", "Note", "Status", "WhatsApp",
]


def _row(r):
    return [
        r.id,
        r.date.isoformat() if r.date else "",
        r.record_type,
        r.merchant or "",
        float(r.amount or 0),
        r.currency or "",
        r.category or "",
        r.payment_method or "",
        r.source or "",
        (r.note or "")[:200],
        r.status or "",
        r.whatsapp_number or "",
    ]


def _bold_header(ws):
    for cell in ws[1]:
        cell.font = Font(bold=True)


def export_monthly(db: Session, family_id: Optional[int], ref: date = None) -> str:
    if ref is None:
        ref = date.today()
    s, e = month_range(ref)
    wb = Workbook()

    ws = wb.active
    ws.title = "Summary"
    inc = record_service.month_total(db, family_id, "income", ref)
    exp = record_service.month_total(db, family_id, "expense", ref)
    sav = record_service.month_total(db, family_id, "savings", ref)
    rate = record_service.savings_rate(db, family_id, ref)
    ws.append(["Family Finance Monthly Report"])
    ws.append(["Period", f"{s.isoformat()} ~ {e.isoformat()}"])
    ws.append(["Family ID", family_id if family_id is not None else "(all)"])
    ws.append([])
    ws.append(["Income", inc])
    ws.append(["Expense", exp])
    ws.append(["Savings", sav])
    ws.append(["Savings Rate %", rate])
    ws["A1"].font = Font(bold=True, size=14)

    all_records = record_service.list_all(db, family_id)

    def add_sheet(name, rtype):
        ws = wb.create_sheet(name)
        ws.append(HEADERS)
        _bold_header(ws)
        for r in all_records:
            if r.record_type == rtype and r.date and s <= r.date <= e:
                ws.append(_row(r))

    add_sheet("Expenses", "expense")
    add_sheet("Savings", "savings")
    add_sheet("Income", "income")

    ws_cat = wb.create_sheet("Category Breakdown")
    ws_cat.append(["Category", "Total"])
    _bold_header(ws_cat)
    for cat, total in record_service.category_breakdown(db, family_id, ref):
        ws_cat.append([cat, total])

    ws_cf = wb.create_sheet("Cashflow")
    ws_cf.append(["Type", "Amount"])
    _bold_header(ws_cf)
    ws_cf.append(["Income", inc])
    ws_cf.append(["Expense", exp])
    ws_cf.append(["Savings", sav])
    ws_cf.append(["Net (Income - Expense - Savings)", inc - exp - sav])

    ws_nr = wb.create_sheet("Need Review")
    ws_nr.append(HEADERS + ["Missing Fields"])
    _bold_header(ws_nr)
    for r in all_records:
        if r.status in ("need_review", "need_question", "failed"):
            ws_nr.append(_row(r) + [r.missing_fields or ""])

    settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fam_tag = f"_fam{family_id}" if family_id is not None else ""
    out_path = settings.OUTPUT_DIR / f"monthly_finance_report_{s.strftime('%Y%m')}{fam_tag}.xlsx"
    wb.save(out_path)
    return str(out_path)
