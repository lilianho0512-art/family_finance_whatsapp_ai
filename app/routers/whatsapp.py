import re
import traceback
from datetime import date
from typing import Optional
from fastapi import APIRouter, Request, Query, Depends
from fastapi.responses import PlainTextResponse, JSONResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import FinancialRecord
from app.services import (
    whatsapp_service,
    ai_parser,
    ocr_service,
    record_service,
    conversation_memory,
    question_engine,
    menu_service,
    report_service,
    excel_export,
    auth_service,
)
from app.services.auto_bug_checker import log_bug
from app.utils.date_tools import parse_date
from app.utils.money_tools import format_money
from app.utils.json_tools import safe_json_dumps
from app.utils.logger import logger

router = APIRouter()

TYPE_ZH = {
    "expense": "家庭开销",
    "savings": "家庭储蓄",
    "income": "家庭收入",
    "transfer": "转账",
    "unknown": "其他",
}


@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("Webhook verified")
        return PlainTextResponse(content=hub_challenge or "", status_code=200)
    return PlainTextResponse(content="forbidden", status_code=403)


@router.post("/webhook")
async def receive_webhook(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
    except Exception as e:
        logger.warning(f"webhook bad json: {e}")
        return JSONResponse({"status": "ignored"}, status_code=200)

    try:
        for entry in body.get("entry", []) or []:
            for change in entry.get("changes", []) or []:
                value = change.get("value", {}) or {}
                messages = value.get("messages") or []
                for msg in messages:
                    try:
                        _handle_message(db, msg)
                    except Exception as inner:
                        tb = traceback.format_exc()
                        logger.error(f"_handle_message error: {inner}\n{tb}")
                        log_bug(
                            "HandleMessageError", str(inner),
                            file_name="whatsapp.py",
                            function_name="_handle_message",
                            traceback_text=tb,
                        )
                        try:
                            whatsapp_service.send_text(
                                msg.get("from", ""),
                                "系统暂时遇到问题，已记录此信息以便人工审核 ✏️\n请稍后再试，或回复 Hi 查看菜单。",
                            )
                        except Exception:
                            pass
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"webhook handler error: {e}\n{tb}")
        log_bug(
            "WebhookError", str(e),
            file_name="whatsapp.py",
            function_name="receive_webhook",
            traceback_text=tb,
        )
    return JSONResponse({"status": "ok"}, status_code=200)


def _onboarding_text() -> str:
    return (
        "你好 👋 你的 WhatsApp 号码尚未绑定家庭。\n\n"
        "请打开 Dashboard 注册（创建家庭账户并绑定此号码）：\n"
        f"  http://<your-domain>:{settings.APP_PORT}/register\n\n"
        "或让管理员在已有家庭中点击「添加 WhatsApp」绑定你的号码。\n"
        "绑定后再回复 Hi 即可开始记账。"
    )


def _handle_message(db: Session, msg: dict):
    from_number = msg.get("from") or ""
    msg_id = msg.get("id") or ""
    msg_type = msg.get("type") or ""

    # Resolve family from WhatsApp number — every action is family-scoped.
    enrollment = auth_service.get_enrollment_for_number(db, from_number)
    if enrollment is None:
        # Allow greetings to still get a friendly onboarding reply.
        body_text = ""
        if msg_type == "text":
            body_text = (msg.get("text") or {}).get("body", "") or ""
        if menu_service.is_greeting(body_text) or body_text:
            whatsapp_service.send_text(from_number, _onboarding_text())
        return

    family_id = enrollment.family_id

    text = ""
    file_path = ""
    source_type = "text"

    if msg_type == "text":
        text = (msg.get("text") or {}).get("body", "") or ""
    elif msg_type in ("image", "document", "sticker"):
        media = msg.get(msg_type) or {}
        media_id = media.get("id") or ""
        caption = media.get("caption") or ""
        file_path = whatsapp_service.download_media(media_id) if media_id else ""
        source_type = msg_type
        ocr_text = ""
        if file_path:
            if file_path.lower().endswith(".pdf"):
                ocr_text = ocr_service.ocr_pdf(file_path)
            else:
                ocr_text = ocr_service.ocr_image(file_path)
        text = (caption + "\n" + ocr_text).strip()
        if not text:
            whatsapp_service.send_text(
                from_number,
                "我已收到附件，但暂时未能识别文字。已标记为需要人工审核 ✏️\n请补充：商家、金额、类别。",
            )
            record_service.create_record(
                db,
                family_id=family_id,
                whatsapp_number=from_number,
                source_text=caption,
                source_type=source_type,
                whatsapp_message_id=msg_id,
                file_path=file_path,
                status="need_review",
                missing_fields="ocr_failed",
                date=date.today(),
            )
            return
    elif msg_type == "audio":
        whatsapp_service.send_text(from_number, "暂不支持语音消息，请发送文字、图片或 PDF。")
        return
    else:
        logger.info(f"Unsupported message type: {msg_type}")
        whatsapp_service.send_text(from_number, "暂不支持此消息类型，请发送文字、图片或 PDF。")
        return

    text = (text or "").strip()
    if not text:
        whatsapp_service.send_text(from_number, "我没看到内容，请重新发送。回复 Hi 查看菜单。")
        return

    # 1. greeting → menu
    if menu_service.is_greeting(text):
        conversation_memory.clear_conversation(db, from_number)
        whatsapp_service.send_text(from_number, menu_service.get_welcome_text())
        return

    # 2. active conversation → resolve answer
    conv = conversation_memory.get_conversation(db, from_number)
    if conv and conv.current_record_id and conv.current_step:
        rec = record_service.get_record(db, conv.current_record_id)
        # Defence-in-depth: never allow a conversation to operate on another family's record.
        if rec is None or (rec.family_id is not None and rec.family_id != family_id):
            conversation_memory.clear_conversation(db, from_number)
        else:
            value = question_engine.resolve_answer(conv.current_step, text)
            if value is None:
                whatsapp_service.send_text(
                    from_number,
                    f"未能识别你的选择「{text[:20]}」。请回复字母选项：\n\n{conv.current_question}",
                )
                return
            field_map = {
                "ask_record_type": "record_type",
                "ask_category": "category",
                "ask_payment_method": "payment_method",
                "ask_savings_source": "source",
                "ask_income_source": "source",
            }
            field = field_map.get(conv.current_step)
            if field:
                record_service.update_record(db, rec.id, **{field: value})
                rec = record_service.get_record(db, rec.id)

            nxt = question_engine.determine_next_question(rec)
            if nxt:
                step, qtext, options = nxt
                conversation_memory.upsert_conversation(
                    db, from_number,
                    family_id=family_id,
                    current_record_id=rec.id,
                    current_step=step,
                    current_question=qtext,
                    options=options,
                    expected_answer_type="letter",
                    state="active",
                )
                whatsapp_service.send_text(from_number, qtext)
            else:
                record_service.update_record(
                    db, rec.id, status="completed", missing_fields=""
                )
                rec = record_service.get_record(db, rec.id)
                conversation_memory.clear_conversation(db, from_number)
                whatsapp_service.send_text(from_number, _render_confirmation(rec))
            return

    # 3. queries (family-scoped)
    query_reply = _try_handle_query(db, family_id, text)
    if query_reply is not None:
        whatsapp_service.send_text(from_number, query_reply)
        return

    # 4. parse new record
    parsed = ai_parser.parse(text)
    rec = record_service.create_record(
        db,
        family_id=family_id,
        whatsapp_number=from_number,
        record_type=parsed.get("record_type") or "unknown",
        date=parse_date(parsed.get("date") or "") or date.today(),
        merchant=parsed.get("merchant") or "",
        amount=float(parsed.get("amount") or 0),
        currency=parsed.get("currency") or "MYR",
        category=parsed.get("category") or "",
        payment_method=parsed.get("payment_method") or "",
        source=parsed.get("source") or "",
        note=parsed.get("note") or "",
        source_text=text,
        source_type=source_type,
        whatsapp_message_id=msg_id,
        file_path=file_path,
        confidence_score=float(parsed.get("confidence_score") or 0.5),
        status="need_question",
        missing_fields=",".join(parsed.get("missing_fields") or []),
        raw_ai_json=safe_json_dumps(parsed),
    )

    intro = _render_recognition(rec)
    nxt = question_engine.determine_next_question(rec)
    if nxt:
        step, qtext, options = nxt
        conversation_memory.upsert_conversation(
            db, from_number,
            family_id=family_id,
            current_record_id=rec.id,
            current_step=step,
            current_question=qtext,
            options=options,
            expected_answer_type="letter",
            state="active",
        )
        whatsapp_service.send_text(from_number, intro + "\n\n" + qtext)
    else:
        record_service.update_record(db, rec.id, status="completed", missing_fields="")
        rec = record_service.get_record(db, rec.id)
        whatsapp_service.send_text(from_number, _render_confirmation(rec))


def _render_recognition(rec) -> str:
    lines = ["我识别到："]
    if rec.merchant:
        lines.append(f"商家：{rec.merchant}")
    if rec.amount:
        lines.append(f"金额：{format_money(rec.amount, rec.currency or 'MYR')}")
    if rec.category:
        lines.append(f"分类：{rec.category}")
    if rec.date:
        lines.append(f"日期：{rec.date.isoformat()}")
    return "\n".join(lines)


def _render_confirmation(rec) -> str:
    lines = ["已记录成功 ✅\n"]
    lines.append(f"类型：{TYPE_ZH.get(rec.record_type, rec.record_type)}")
    if rec.merchant:
        lines.append(f"商家：{rec.merchant}")
    lines.append(f"金额：{format_money(rec.amount or 0, rec.currency or 'MYR')}")
    if rec.category:
        lines.append(f"分类：{rec.category}")
    if rec.payment_method:
        lines.append(f"付款方式：{rec.payment_method}")
    if rec.source:
        lines.append(f"来源：{rec.source}")
    if rec.date:
        lines.append(f"日期：{rec.date.isoformat()}")
    return "\n".join(lines)


_QUERY_PATTERNS = [
    (re.compile(r"(本月|这个月|this month).*(花|开销|支出|expense)", re.IGNORECASE), "month_expense"),
    (re.compile(r"(本月|这个月|this month).*(储蓄|存钱|savings)", re.IGNORECASE), "month_savings"),
    (re.compile(r"(本月|这个月|this month).*(收入|工资|income)", re.IGNORECASE), "month_income"),
    (re.compile(r"(本月|这个月|this month).*(储蓄率|savings rate)", re.IGNORECASE), "savings_rate"),
    (re.compile(r"(今天|今日|today).*(花|开销|支出|expense)", re.IGNORECASE), "today_expense"),
    (re.compile(r"(总结|summary)", re.IGNORECASE), "month_summary"),
    (re.compile(r"(导出|export)", re.IGNORECASE), "export"),
]


def _try_handle_query(db: Session, family_id: Optional[int], text: str):
    t = text.strip()
    for rx, kind in _QUERY_PATTERNS:
        if rx.search(t):
            if kind == "month_expense":
                return f"📤 本月开销：{format_money(record_service.month_total(db, family_id, 'expense'))}"
            if kind == "month_savings":
                return f"💰 本月储蓄：{format_money(record_service.month_total(db, family_id, 'savings'))}"
            if kind == "month_income":
                return f"💵 本月收入：{format_money(record_service.month_total(db, family_id, 'income'))}"
            if kind == "savings_rate":
                return f"📈 本月储蓄率：{record_service.savings_rate(db, family_id)}%"
            if kind == "today_expense":
                return f"📅 今天开销：{format_money(record_service.today_expense(db, family_id))}"
            if kind == "month_summary":
                return report_service.monthly_summary_text(db, family_id)
            if kind == "export":
                path = excel_export.export_monthly(db, family_id)
                return f"📁 已生成月报：\n{path}\n（也可在 dashboard 下载）"

    m = re.search(r"([A-Za-z一-龥]+)\s*类别.*(花|开销|多少|支出)", t)
    if m:
        cat = m.group(1)
        return f"🏷️ {cat} 类别本月开销：{format_money(record_service.category_total(db, family_id, cat))}"

    m = re.search(r"(本月|这个月)\s*([A-Za-z][A-Za-z0-9 ]{1,20}|[一-龥]{1,8})\s*花多少", t)
    if m:
        merchant = m.group(2).strip()
        return f"🏬 {merchant} 本月支出：{format_money(record_service.merchant_total(db, family_id, merchant))}"

    return None
