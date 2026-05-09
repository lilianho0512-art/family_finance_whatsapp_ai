from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, Text, ForeignKey, Boolean
from app.database import Base


class Family(Base):
    __tablename__ = "families"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    email = Column(String(200), unique=True, nullable=False, index=True)
    password_hash = Column(String(200), nullable=False)
    role = Column(String(20), default="admin")  # admin / member (within family)
    is_superadmin = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class WhatsappEnrollment(Base):
    __tablename__ = "whatsapp_enrollments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    whatsapp_number = Column(String(50), unique=True, nullable=False, index=True)
    label = Column(String(80))
    created_at = Column(DateTime, default=datetime.utcnow)


class FinancialRecord(Base):
    __tablename__ = "financial_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=True, index=True)
    whatsapp_number = Column(String(50), index=True)
    record_type = Column(String(20), default="unknown")
    date = Column(Date)
    merchant = Column(String(200))
    amount = Column(Float, default=0.0)
    currency = Column(String(10), default="MYR")
    category = Column(String(100))
    payment_method = Column(String(50))
    source = Column(String(100))
    account = Column(String(80), index=True)  # which bank/wallet this record touched
    note = Column(Text)
    source_text = Column(Text)
    source_type = Column(String(20), default="text")
    whatsapp_message_id = Column(String(120))
    file_path = Column(String(500))
    confidence_score = Column(Float, default=0.0)
    status = Column(String(30), default="need_question")
    missing_fields = Column(Text)
    raw_ai_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=True, index=True)
    whatsapp_number = Column(String(50), index=True, unique=True)
    current_record_id = Column(Integer)
    current_step = Column(String(50))
    current_question = Column(Text)
    expected_answer_type = Column(String(50))
    options_json = Column(Text)
    state = Column(String(20), default="active")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BankAccount(Base):
    __tablename__ = "bank_accounts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    family_id = Column(Integer, ForeignKey("families.id"), index=True, nullable=False)
    name = Column(String(80), nullable=False, index=True)  # "Maybank", "UOB", "Cash"
    note = Column(String(200))
    is_active = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


class AccountBalance(Base):
    """A user-supplied balance snapshot for reconciliation."""
    __tablename__ = "account_balances"
    id = Column(Integer, primary_key=True, autoincrement=True)
    family_id = Column(Integer, ForeignKey("families.id"), index=True, nullable=False)
    account_name = Column(String(80), nullable=False, index=True)
    as_of_date = Column(Date, nullable=False)
    balance = Column(Float, nullable=False, default=0.0)
    note = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)


class Loan(Base):
    """Loans and installment plans (BNPL, credit-card plans, etc.).

    `kind` distinguishes a long-term loan ("loan") from a short-term
    installment plan ("installment"); both share the same shape.
    """
    __tablename__ = "loans"
    id = Column(Integer, primary_key=True, autoincrement=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    kind = Column(String(20), nullable=False, default="loan")  # loan | installment
    lender = Column(String(120), nullable=False)
    principal = Column(Float, nullable=False, default=0.0)
    interest_rate = Column(Float, nullable=True)               # annual %, nullable
    term_months = Column(Integer, nullable=True)
    monthly_payment = Column(Float, nullable=False, default=0.0)
    start_date = Column(Date, nullable=True)
    payment_due_day = Column(Integer, nullable=True)           # 1..31
    current_balance = Column(Float, nullable=False, default=0.0)
    status = Column(String(20), nullable=False, default="active")  # active | closed
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BugLog(Base):
    __tablename__ = "bug_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=True, index=True)
    error_type = Column(String(100))
    error_message = Column(Text)
    file_name = Column(String(200))
    function_name = Column(String(200))
    traceback_text = Column(Text)
    auto_fixed = Column(Integer, default=0)
    fix_note = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
