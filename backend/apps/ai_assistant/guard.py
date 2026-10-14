"""LLM yozgan SQL'ni tekshirish va xavfsiz bajarish (CLAUDE.md 13, 3-band).

Himoya bir necha qavatli:
1. Tahlil (sqlglot): bitta so'rov, faqat SELECT/WITH, faqat `analytics_*` view'lar, xavfli funksiyalar taqiqlangan.
2. Natija LIMIT bilan o'raladi, so'rov vaqti 5 soniya.
3. PostgreSQL: tranzaksiya READ ONLY va `codial_ai` roli (faqat view'larni o'qiy oladi); SQLite: `PRAGMA query_only`.
Tranzaksiya oxirida doim bekor qilinadi."""

import datetime
import time
from decimal import Decimal

import sqlglot
from django.conf import settings
from django.db import connection, transaction
from sqlglot import exp

from .analytics import PII_COLUMNS, PII_VIEWS, ROLE, VIEW_NAMES

ALLOWED = set(VIEW_NAMES)
FORBIDDEN_NODES = tuple(getattr(exp, n) for n in ("Insert", "Update", "Delete", "Drop", "Create", "Alter", "Command", "Merge", "Set", "Pragma", "Into", "Lock", "Copy", "Transaction")
                        if hasattr(exp, n))
FORBIDDEN_FUNCS = ("pg_", "lo_", "dblink", "set_config", "current_setting", "load_extension", "query_to_", "xpath", "txid", "inet_", "version", "sqlite_", "readfile", "writefile")


class Blocked(Exception):
    """SQL tekshiruvdan o'tmadi (matni foydalanuvchiga va LLM'ga qaytariladi)."""


def dialect():
    return "postgres" if connection.vendor == "postgresql" else "sqlite"


def validate(sql):
    """Tekshiradi va (toza SQL, pii_ishlatilganmi) qaytaradi."""
    sql = (sql or "").strip().rstrip(";").strip()
    if not sql:
        raise Blocked("SQL bo'sh")
    try:
        trees = sqlglot.parse(sql, read=dialect())
    except sqlglot.errors.ParseError as e:
        raise Blocked(f"SQL tushunarsiz: {str(e).splitlines()[0][:200]}") from None
    if len(trees) != 1 or trees[0] is None:
        raise Blocked("Faqat bitta SELECT so'rovi bo'lishi kerak")
    tree = trees[0]
    if not isinstance(tree, exp.Query):
        raise Blocked("Faqat SELECT so'rovi ruxsat etilgan")
    for node in tree.walk():
        if isinstance(node, FORBIDDEN_NODES):
            raise Blocked("Faqat o'qish ruxsat etilgan (o'zgartiruvchi buyruq topildi)")
        if isinstance(node, exp.Func):
            name = (node.sql_name() if not isinstance(node, exp.Anonymous) else node.name or "").lower()
            if name.startswith(FORBIDDEN_FUNCS):
                raise Blocked(f"Ruxsat etilmagan funksiya: {name}")
    ctes = {c.alias_or_name.lower() for c in tree.find_all(exp.CTE)}
    for t in tree.find_all(exp.Table):
        name = (t.name or "").lower()
        if t.args.get("db") or t.args.get("catalog"):
            raise Blocked(f"Ruxsat etilmagan jadval: {t.sql()}")
        if name in ctes:
            continue
        if name not in ALLOWED:
            raise Blocked(f"Ruxsat etilmagan jadval: {name or t.sql()}. Faqat analytics_* view'lar")
    if not any(True for _ in tree.find_all(exp.Table)):
        raise Blocked("So'rov analytics_* view'laridan o'qishi kerak")
    cols = {c.name.lower() for c in tree.find_all(exp.Column)}
    return sql, bool(cols & PII_COLUMNS) or _star_pii(tree)


def _star_pii(tree):
    """`SELECT *` shaxsiy ma'lumotli view'dan to'g'ridan-to'g'ri o'qisa (COUNT(*) hisoblanmaydi)."""
    for s in tree.find_all(exp.Star):
        if isinstance(s.parent, exp.Count):
            continue
        sel = s.find_ancestor(exp.Select)
        if sel is None:
            return True
        srcs = {t.name.lower() for part in (sel.args.get("from"), *(sel.args.get("joins") or [])) if part for t in part.find_all(exp.Table)}
        if srcs & PII_VIEWS:
            return True
    return False


def _plain(v):
    if isinstance(v, Decimal):
        return int(v) if v == v.to_integral_value() else float(v)
    if isinstance(v, (datetime.date, datetime.datetime, datetime.time)):
        return v.isoformat()
    if isinstance(v, (bytes, memoryview)):
        return None
    if v is None or isinstance(v, (int, float, str, bool)):
        return v
    return str(v)


def execute(sql):
    """Tekshirilgan SQL'ni bajaradi: {columns, rows, truncated, ms}."""
    limit = settings.AI_MAX_ROWS
    timeout = settings.AI_SQL_TIMEOUT_S
    wrapped = f"SELECT * FROM ({sql}) ai_q LIMIT {limit + 1}"
    started = time.monotonic()
    connection.ensure_connection()
    pg = connection.vendor == "postgresql"
    raw = connection.connection
    try:
        with transaction.atomic():
            with connection.cursor() as cur:
                if pg:
                    cur.execute("SET TRANSACTION READ ONLY")
                    cur.execute(f"SET LOCAL statement_timeout = {int(timeout * 1000)}")
                    cur.execute(f"SET LOCAL ROLE {ROLE}")
                else:
                    cur.execute("PRAGMA query_only = 1")
                    deadline = started + timeout
                    raw.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, 2000)
                cur.execute(wrapped)
                columns = [d[0] for d in cur.description]
                rows = [[_plain(v) for v in r] for r in cur.fetchmany(limit + 1)]
            transaction.set_rollback(True)
    except Exception as e:  # noqa: BLE001 — har qanday baza xatosi foydalanuvchiga matn bo'lib qaytadi
        msg = str(e).splitlines()[0][:300] if str(e) else e.__class__.__name__
        if "interrupted" in msg or "statement timeout" in msg or "canceling statement" in msg:
            msg = f"So'rov {timeout:g} soniyadan uzoq davom etdi va to'xtatildi"
        raise Blocked(f"Bajarishda xato: {msg}") from None
    finally:
        if not pg:
            raw.set_progress_handler(None, 0)
            with connection.cursor() as cur:
                cur.execute("PRAGMA query_only = 0")
    truncated = len(rows) > limit
    return {"columns": columns, "rows": rows[:limit], "truncated": truncated, "ms": int((time.monotonic() - started) * 1000)}
