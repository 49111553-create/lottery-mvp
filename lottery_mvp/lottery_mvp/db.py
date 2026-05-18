import secrets
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from typing import Iterable

from config import (
    ADMIN_PASSWORD,
    DATABASE_URL,
    DB_PATH,
    DEFAULT_ACCESS_CODE_DAYS,
    DEFAULT_PAID_ALLOWED_TYPES,
    DEFAULT_FREE_DAILY_AI_LIMIT,
    DEFAULT_PAID_DAILY_AI_LIMIT,
)

IS_POSTGRES = DATABASE_URL.startswith("postgresql+psycopg://")

if IS_POSTGRES:
    from sqlalchemy import (
        Column,
        Float,
        Integer,
        MetaData,
        String,
        Table,
        Text,
        UniqueConstraint,
        create_engine,
        func,
        select,
        update,
    )
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)
    metadata = MetaData()

    draw_results = Table(
        "draw_results",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("lottery_type", String(20), nullable=False),
        Column("issue", String(40), nullable=False),
        Column("draw_date", String(20), nullable=False),
        Column("numbers_main", Text, nullable=False),
        Column("numbers_extra", Text, nullable=False, default=""),
        Column("sales_amount", Float, nullable=False, default=0),
        Column("jackpot_amount", Float, nullable=False, default=0),
        Column("source_name", String(100), nullable=False, default=""),
        Column("source_url", Text, nullable=False, default=""),
        Column("ingested_at", String(40), nullable=False),
        UniqueConstraint("lottery_type", "issue", name="uq_draw_results_lottery_issue"),
    )

    access_codes = Table(
        "access_codes",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("code", String(40), nullable=False, unique=True),
        Column("plan_type", String(20), nullable=False, default="paid"),
        Column("status", String(20), nullable=False, default="active"),
        Column("expires_at", String(40), nullable=False),
        Column("max_uses", Integer, nullable=False, default=9999),
        Column("used_count", Integer, nullable=False, default=0),
        Column("bound_device", String(200), nullable=False, default=""),
        Column("allowed_lotteries", Text, nullable=False, default=""),
        Column("note", Text, nullable=False, default=""),
        Column("created_at", String(40), nullable=False),
        Column("created_by", String(60), nullable=False, default="admin"),
    )

    payment_orders = Table(
        "payment_orders",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("payer_name", String(100), nullable=False, default=""),
        Column("payment_channel", String(30), nullable=False, default=""),
        Column("payment_note", String(120), nullable=False, default=""),
        Column("amount", Float, nullable=False, default=9.9),
        Column("status", String(20), nullable=False, default="pending"),
        Column("issued_code", String(40), nullable=False, default=""),
        Column("created_at", String(40), nullable=False),
    )

    ai_usage_logs = Table(
        "ai_usage_logs",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("actor_key", String(120), nullable=False),
        Column("access_code", String(40), nullable=False, default=""),
        Column("usage_date", String(20), nullable=False),
        Column("lottery_type", String(20), nullable=False),
        Column("prompt_type", String(40), nullable=False),
        Column("created_at", String(40), nullable=False),
    )

    update_logs = Table(
        "update_logs",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("run_type", String(40), nullable=False),
        Column("status", String(20), nullable=False),
        Column("detail", Text, nullable=False, default=""),
        Column("created_at", String(40), nullable=False),
    )

    draw_fetch_logs = Table(
        "draw_fetch_logs",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("lottery_type", String(20), nullable=False),
        Column("fetch_time", String(40), nullable=False),
        Column("source_url", Text, nullable=False, default=""),
        Column("status", String(20), nullable=False),
        Column("is_fallback", Integer, nullable=False, default=0),
        Column("detail", Text, nullable=False, default=""),
        Column("issue_found", String(40), nullable=False, default=""),
    )

    stats_cache = Table(
        "stats_cache",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("lottery_type", String(20), nullable=False),
        Column("stat_type", String(40), nullable=False),
        Column("period_range", String(20), nullable=False),
        Column("cache_key", String(120), nullable=False, unique=True),
        Column("cache_json", Text, nullable=False),
        Column("updated_at", String(40), nullable=False),
    )

    admin_actions = Table(
        "admin_actions",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("admin_name", String(60), nullable=False),
        Column("action_type", String(40), nullable=False),
        Column("target_type", String(40), nullable=False),
        Column("target_id", String(60), nullable=False),
        Column("detail", Text, nullable=False, default=""),
        Column("created_at", String(40), nullable=False),
    )


@contextmanager
def get_sqlite_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    if IS_POSTGRES:
        metadata.create_all(engine)
    else:
        with get_sqlite_conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS draw_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lottery_type TEXT NOT NULL,
                    issue TEXT NOT NULL,
                    draw_date TEXT NOT NULL,
                    numbers_main TEXT NOT NULL,
                    numbers_extra TEXT DEFAULT '',
                    sales_amount REAL DEFAULT 0,
                    jackpot_amount REAL DEFAULT 0,
                    source_name TEXT DEFAULT '',
                    source_url TEXT DEFAULT '',
                    ingested_at TEXT NOT NULL,
                    UNIQUE(lottery_type, issue)
                );
                CREATE TABLE IF NOT EXISTS access_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    plan_type TEXT NOT NULL DEFAULT 'paid',
                    status TEXT NOT NULL DEFAULT 'active',
                    expires_at TEXT NOT NULL,
                    max_uses INTEGER NOT NULL DEFAULT 9999,
                    used_count INTEGER NOT NULL DEFAULT 0,
                    bound_device TEXT DEFAULT '',
                    allowed_lotteries TEXT DEFAULT '',
                    note TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    created_by TEXT DEFAULT 'admin'
                );
                CREATE TABLE IF NOT EXISTS payment_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    payer_name TEXT DEFAULT '',
                    payment_channel TEXT DEFAULT '',
                    payment_note TEXT DEFAULT '',
                    amount REAL NOT NULL DEFAULT 9.9,
                    status TEXT NOT NULL DEFAULT 'pending',
                    issued_code TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS ai_usage_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor_key TEXT NOT NULL,
                    access_code TEXT DEFAULT '',
                    usage_date TEXT NOT NULL,
                    lottery_type TEXT NOT NULL,
                    prompt_type TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS update_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    detail TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS draw_fetch_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lottery_type TEXT NOT NULL,
                    fetch_time TEXT NOT NULL,
                    source_url TEXT DEFAULT '',
                    status TEXT NOT NULL,
                    is_fallback INTEGER NOT NULL DEFAULT 0,
                    detail TEXT DEFAULT '',
                    issue_found TEXT DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS stats_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lottery_type TEXT NOT NULL,
                    stat_type TEXT NOT NULL,
                    period_range TEXT NOT NULL,
                    cache_key TEXT NOT NULL UNIQUE,
                    cache_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS admin_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_name TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    detail TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                );
                """
            )
            _ensure_sqlite_column(conn, "access_codes", "allowed_lotteries", "TEXT DEFAULT ''")
    ensure_default_codes()


def _ensure_sqlite_column(conn, table_name: str, column_name: str, column_def: str):
    columns = [row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()]
    if column_name not in columns:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")


def ensure_default_codes():
    now = datetime.utcnow().isoformat()
    if IS_POSTGRES:
        with engine.begin() as conn:
            free_count = conn.execute(
                select(func.count()).select_from(access_codes).where(access_codes.c.plan_type == "free")
            ).scalar_one()
            if not free_count:
                conn.execute(
                    access_codes.insert().values(
                        code="FREE-DEMO",
                        plan_type="free",
                        status="active",
                        expires_at=(datetime.utcnow() + timedelta(days=3650)).isoformat(),
                        max_uses=9999,
                        used_count=0,
                        bound_device="",
                        allowed_lotteries="",
                        note="演示访问码，每日 AI 次数受限",
                        created_at=now,
                        created_by="admin",
                    )
                )
    else:
        with get_sqlite_conn() as conn:
            cnt = conn.execute(
                "SELECT COUNT(*) AS cnt FROM access_codes WHERE plan_type='free'"
            ).fetchone()["cnt"]
            if not cnt:
                conn.execute(
                    """
                    INSERT INTO access_codes
                    (code, plan_type, status, expires_at, max_uses, used_count,
                     bound_device, allowed_lotteries, note, created_at, created_by)
                    VALUES (?, 'free', 'active', ?, 9999, 0, '', '', ?, ?, 'admin')
                    """,
                    (
                        "FREE-DEMO",
                        (datetime.utcnow() + timedelta(days=3650)).isoformat(),
                        "演示访问码，每日 AI 次数受限",
                        now,
                    ),
                )


def generate_access_code(prefix: str = "VIP") -> str:
    return f"{prefix}-{secrets.token_hex(4).upper()}"


def create_access_codes(
    count: int,
    plan_type: str = "paid",
    days_valid: int = DEFAULT_ACCESS_CODE_DAYS,
    note: str = "",
    allowed_lotteries: list[str] | None = None,
):
    created = []
    now = datetime.utcnow()
    expires = now + timedelta(days=days_valid)
    allowed_lotteries = allowed_lotteries or ([] if plan_type == "free" else DEFAULT_PAID_ALLOWED_TYPES[:3])
    allowed_lotteries_text = ",".join(allowed_lotteries)
    if IS_POSTGRES:
        with engine.begin() as conn:
            for _ in range(count):
                code = generate_access_code("VIP" if plan_type == "paid" else "FREE")
                conn.execute(
                    access_codes.insert().values(
                        code=code,
                        plan_type=plan_type,
                        status="active",
                        expires_at=expires.isoformat(),
                        max_uses=9999,
                        used_count=0,
                        bound_device="",
                        allowed_lotteries=allowed_lotteries_text,
                        note=note,
                        created_at=now.isoformat(),
                        created_by="admin",
                    )
                )
                created.append(code)
    else:
        with get_sqlite_conn() as conn:
            for _ in range(count):
                code = generate_access_code("VIP" if plan_type == "paid" else "FREE")
                conn.execute(
                    """
                    INSERT INTO access_codes
                    (code, plan_type, status, expires_at, max_uses, used_count,
                     bound_device, allowed_lotteries, note, created_at, created_by)
                    VALUES (?, ?, 'active', ?, 9999, 0, '', ?, ?, ?, 'admin')
                    """,
                    (code, plan_type, expires.isoformat(), allowed_lotteries_text, note, now.isoformat()),
                )
                created.append(code)
    return created


def verify_access_code(code: str, device_key: str = ""):
    if IS_POSTGRES:
        with engine.begin() as conn:
            row = conn.execute(
                select(access_codes).where(
                    access_codes.c.code == code.strip(), access_codes.c.status == "active"
                )
            ).mappings().first()
            if not row:
                return False, "访问码不存在或已停用", None
            if row["expires_at"] < datetime.utcnow().isoformat():
                return False, "访问码已过期", None
            if row["used_count"] >= row["max_uses"]:
                return False, "访问码已达到可用次数上限", None
            if row["bound_device"] and device_key and row["bound_device"] != device_key:
                return False, "访问码已绑定其他设备", None
            if device_key and not row["bound_device"]:
                conn.execute(update(access_codes).where(access_codes.c.id == row["id"]).values(bound_device=device_key))
                row = {**row, "bound_device": device_key}
            conn.execute(
                update(access_codes).where(access_codes.c.id == row["id"]).values(
                    used_count=access_codes.c.used_count + 1
                )
            )
            return True, "登录成功", dict(row)
    with get_sqlite_conn() as conn:
        row = conn.execute(
            "SELECT * FROM access_codes WHERE code=? AND status='active'", (code.strip(),)
        ).fetchone()
        if not row:
            return False, "访问码不存在或已停用", None
        if row["expires_at"] < datetime.utcnow().isoformat():
            return False, "访问码已过期", None
        if row["used_count"] >= row["max_uses"]:
            return False, "访问码已达到可用次数上限", None
        if row["bound_device"] and device_key and row["bound_device"] != device_key:
            return False, "访问码已绑定其他设备", None
        if device_key and not row["bound_device"]:
            conn.execute("UPDATE access_codes SET bound_device=? WHERE id=?", (device_key, row["id"]))
        conn.execute("UPDATE access_codes SET used_count = used_count + 1 WHERE id=?", (row["id"],))
        return True, "登录成功", dict(row)


def admin_login(password: str) -> bool:
    return password == ADMIN_PASSWORD


def get_access_codes(limit: int = 50):
    if IS_POSTGRES:
        with engine.begin() as conn:
            return [dict(r) for r in conn.execute(select(access_codes).order_by(access_codes.c.id.desc()).limit(limit)).mappings()]
    with get_sqlite_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM access_codes ORDER BY id DESC LIMIT ?", (limit,)).fetchall()]


def disable_access_code(code: str):
    if IS_POSTGRES:
        with engine.begin() as conn:
            conn.execute(update(access_codes).where(access_codes.c.code == code).values(status="disabled"))
    else:
        with get_sqlite_conn() as conn:
            conn.execute("UPDATE access_codes SET status='disabled' WHERE code=?", (code,))


def create_order(payer_name: str, payment_channel: str, payment_note: str, amount: float):
    now = datetime.utcnow().isoformat()
    if IS_POSTGRES:
        with engine.begin() as conn:
            conn.execute(
                payment_orders.insert().values(
                    payer_name=payer_name,
                    payment_channel=payment_channel,
                    payment_note=payment_note,
                    amount=amount,
                    status="pending",
                    issued_code="",
                    created_at=now,
                )
            )
    else:
        with get_sqlite_conn() as conn:
            conn.execute(
                """
                INSERT INTO payment_orders
                (payer_name, payment_channel, payment_note, amount, status, issued_code, created_at)
                VALUES (?, ?, ?, ?, 'pending', '', ?)
                """,
                (payer_name, payment_channel, payment_note, amount, now),
            )


def get_orders(limit: int = 100):
    if IS_POSTGRES:
        with engine.begin() as conn:
            return [dict(r) for r in conn.execute(select(payment_orders).order_by(payment_orders.c.id.desc()).limit(limit)).mappings()]
    with get_sqlite_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM payment_orders ORDER BY id DESC LIMIT ?", (limit,)).fetchall()]


def mark_order_issued(order_id: int, issued_code: str):
    if IS_POSTGRES:
        with engine.begin() as conn:
            conn.execute(
                update(payment_orders).where(payment_orders.c.id == order_id).values(status="issued", issued_code=issued_code)
            )
    else:
        with get_sqlite_conn() as conn:
            conn.execute("UPDATE payment_orders SET status='issued', issued_code=? WHERE id=?", (issued_code, order_id))


def extend_access_code(code: str, days: int):
    if IS_POSTGRES:
        with engine.begin() as conn:
            row = conn.execute(
                select(access_codes).where(access_codes.c.code == code)
            ).mappings().first()
            if not row:
                return False
            base = max(row["expires_at"], datetime.utcnow().isoformat())
            new_expiry = (
                datetime.fromisoformat(base) + timedelta(days=days)
            ).isoformat()
            conn.execute(
                update(access_codes)
                .where(access_codes.c.code == code)
                .values(expires_at=new_expiry)
            )
            return True
    with get_sqlite_conn() as conn:
        row = conn.execute(
            "SELECT * FROM access_codes WHERE code=?", (code,)
        ).fetchone()
        if not row:
            return False
        base = max(row["expires_at"], datetime.utcnow().isoformat())
        new_expiry = (
            datetime.fromisoformat(base) + timedelta(days=days)
        ).isoformat()
        conn.execute("UPDATE access_codes SET expires_at=? WHERE code=?", (new_expiry, code))
        return True


def log_ai_usage(actor_key: str, access_code: str, lottery_type: str, prompt_type: str):
    today = date.today().isoformat()
    now = datetime.utcnow().isoformat()
    if IS_POSTGRES:
        with engine.begin() as conn:
            conn.execute(
                ai_usage_logs.insert().values(
                    actor_key=actor_key,
                    access_code=access_code,
                    usage_date=today,
                    lottery_type=lottery_type,
                    prompt_type=prompt_type,
                    created_at=now,
                )
            )
    else:
        with get_sqlite_conn() as conn:
            conn.execute(
                """
                INSERT INTO ai_usage_logs
                (actor_key, access_code, usage_date, lottery_type, prompt_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (actor_key, access_code, today, lottery_type, prompt_type, now),
            )


def get_ai_usage_count(actor_key: str):
    today = date.today().isoformat()
    if IS_POSTGRES:
        with engine.begin() as conn:
            return conn.execute(
                select(func.count()).select_from(ai_usage_logs).where(
                    ai_usage_logs.c.actor_key == actor_key,
                    ai_usage_logs.c.usage_date == today,
                )
            ).scalar_one()
    with get_sqlite_conn() as conn:
        return conn.execute(
            "SELECT COUNT(*) AS cnt FROM ai_usage_logs WHERE actor_key=? AND usage_date=?",
            (actor_key, today),
        ).fetchone()["cnt"]


def get_ai_limit(plan_type: str):
    return DEFAULT_PAID_DAILY_AI_LIMIT if plan_type == "paid" else DEFAULT_FREE_DAILY_AI_LIMIT


def log_update(run_type: str, status: str, detail: str):
    now = datetime.utcnow().isoformat()
    if IS_POSTGRES:
        with engine.begin() as conn:
            conn.execute(update_logs.insert().values(run_type=run_type, status=status, detail=detail, created_at=now))
    else:
        with get_sqlite_conn() as conn:
            conn.execute(
                "INSERT INTO update_logs (run_type, status, detail, created_at) VALUES (?, ?, ?, ?)",
                (run_type, status, detail, now),
            )


def get_update_logs(limit: int = 50):
    if IS_POSTGRES:
        with engine.begin() as conn:
            return [dict(r) for r in conn.execute(select(update_logs).order_by(update_logs.c.id.desc()).limit(limit)).mappings()]
    with get_sqlite_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM update_logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()]


def log_fetch_result(lottery_type: str, source_url: str, status: str, is_fallback: bool, detail: str, issue_found: str = ""):
    now = datetime.utcnow().isoformat()
    if IS_POSTGRES:
        with engine.begin() as conn:
            conn.execute(
                draw_fetch_logs.insert().values(
                    lottery_type=lottery_type,
                    fetch_time=now,
                    source_url=source_url,
                    status=status,
                    is_fallback=1 if is_fallback else 0,
                    detail=detail,
                    issue_found=issue_found,
                )
            )
    else:
        with get_sqlite_conn() as conn:
            conn.execute(
                """
                INSERT INTO draw_fetch_logs
                (lottery_type, fetch_time, source_url, status, is_fallback, detail, issue_found)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (lottery_type, now, source_url, status, 1 if is_fallback else 0, detail, issue_found),
            )


def get_fetch_logs(limit: int = 100):
    if IS_POSTGRES:
        with engine.begin() as conn:
            rows = conn.execute(
                select(draw_fetch_logs).order_by(draw_fetch_logs.c.id.desc()).limit(limit)
            ).mappings()
            return [dict(r) for r in rows]
    with get_sqlite_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM draw_fetch_logs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()]


def save_stats_cache(lottery_type: str, stat_type: str, period_range: str, cache_key: str, cache_json: str):
    now = datetime.utcnow().isoformat()
    if IS_POSTGRES:
        from sqlalchemy.dialects.postgresql import insert as pg_insert_local

        with engine.begin() as conn:
            stmt = pg_insert_local(stats_cache).values(
                lottery_type=lottery_type,
                stat_type=stat_type,
                period_range=period_range,
                cache_key=cache_key,
                cache_json=cache_json,
                updated_at=now,
            ).on_conflict_do_update(
                index_elements=["cache_key"],
                set_={"cache_json": cache_json, "updated_at": now},
            )
            conn.execute(stmt)
    else:
        with get_sqlite_conn() as conn:
            conn.execute(
                """
                INSERT INTO stats_cache
                (lottery_type, stat_type, period_range, cache_key, cache_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    cache_json=excluded.cache_json,
                    updated_at=excluded.updated_at
                """,
                (lottery_type, stat_type, period_range, cache_key, cache_json, now),
            )


def get_stats_cache(cache_key: str):
    if IS_POSTGRES:
        with engine.begin() as conn:
            row = conn.execute(
                select(stats_cache).where(stats_cache.c.cache_key == cache_key)
            ).mappings().first()
            return dict(row) if row else None
    with get_sqlite_conn() as conn:
        row = conn.execute(
            "SELECT * FROM stats_cache WHERE cache_key=?", (cache_key,)
        ).fetchone()
        return dict(row) if row else None


def save_admin_action(admin_name: str, action_type: str, target_type: str, target_id: str, detail: str):
    now = datetime.utcnow().isoformat()
    if IS_POSTGRES:
        with engine.begin() as conn:
            conn.execute(
                admin_actions.insert().values(
                    admin_name=admin_name,
                    action_type=action_type,
                    target_type=target_type,
                    target_id=target_id,
                    detail=detail,
                    created_at=now,
                )
            )
    else:
        with get_sqlite_conn() as conn:
            conn.execute(
                """
                INSERT INTO admin_actions
                (admin_name, action_type, target_type, target_id, detail, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (admin_name, action_type, target_type, target_id, detail, now),
            )


def get_admin_actions(limit: int = 100):
    if IS_POSTGRES:
        with engine.begin() as conn:
            rows = conn.execute(
                select(admin_actions).order_by(admin_actions.c.id.desc()).limit(limit)
            ).mappings()
            return [dict(r) for r in rows]
    with get_sqlite_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM admin_actions ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()]


def upsert_draws(records: Iterable[dict]):
    rows = list(records)
    if not rows:
        return 0
    if IS_POSTGRES:
        with engine.begin() as conn:
            for item in rows:
                stmt = pg_insert(draw_results).values(**item).on_conflict_do_update(
                    index_elements=["lottery_type", "issue"],
                    set_={k: item[k] for k in [
                        "draw_date",
                        "numbers_main",
                        "numbers_extra",
                        "sales_amount",
                        "jackpot_amount",
                        "source_name",
                        "source_url",
                        "ingested_at",
                    ]},
                )
                conn.execute(stmt)
        return len(rows)
    with get_sqlite_conn() as conn:
        for item in rows:
            conn.execute(
                """
                INSERT INTO draw_results
                (lottery_type, issue, draw_date, numbers_main, numbers_extra, sales_amount,
                 jackpot_amount, source_name, source_url, ingested_at)
                VALUES (:lottery_type, :issue, :draw_date, :numbers_main, :numbers_extra,
                        :sales_amount, :jackpot_amount, :source_name, :source_url, :ingested_at)
                ON CONFLICT(lottery_type, issue) DO UPDATE SET
                    draw_date=excluded.draw_date,
                    numbers_main=excluded.numbers_main,
                    numbers_extra=excluded.numbers_extra,
                    sales_amount=excluded.sales_amount,
                    jackpot_amount=excluded.jackpot_amount,
                    source_name=excluded.source_name,
                    source_url=excluded.source_url,
                    ingested_at=excluded.ingested_at
                """,
                item,
            )
    return len(rows)


def select_draws(lottery_type: str, limit: int = 100):
    if IS_POSTGRES:
        with engine.begin() as conn:
            rows = conn.execute(
                select(draw_results.c.lottery_type, draw_results.c.issue, draw_results.c.draw_date,
                       draw_results.c.numbers_main, draw_results.c.numbers_extra,
                       draw_results.c.sales_amount, draw_results.c.jackpot_amount)
                .where(draw_results.c.lottery_type == lottery_type)
                .order_by(draw_results.c.draw_date.desc(), draw_results.c.issue.desc())
                .limit(limit)
            ).mappings()
            return [dict(r) for r in rows]
    with get_sqlite_conn() as conn:
        rows = conn.execute(
            """
            SELECT lottery_type, issue, draw_date, numbers_main, numbers_extra,
                   sales_amount, jackpot_amount
            FROM draw_results
            WHERE lottery_type=?
            ORDER BY draw_date DESC, issue DESC
            LIMIT ?
            """,
            (lottery_type, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def query_draws(
    lottery_type: str,
    limit: int = 100,
    issue_keyword: str = "",
    start_date: str | None = None,
    end_date: str | None = None,
):
    rows = select_draws(lottery_type, limit=500)
    results = []
    for row in rows:
        if issue_keyword and issue_keyword not in str(row["issue"]):
            continue
        if start_date and row["draw_date"] < start_date:
            continue
        if end_date and row["draw_date"] > end_date:
            continue
        results.append(row)
    return results[:limit]


def get_latest_for_all_lotteries():
    latest = {}
    lotteries = ["ssq", "dlt", "fc3d", "pl3", "pl5", "qlc", "kl8"]
    for lottery_type in lotteries:
        rows = select_draws(lottery_type, limit=1)
        latest[lottery_type] = rows[0] if rows else None
    return latest


def manual_upsert_draw(record: dict):
    return upsert_draws([record])


def get_dashboard_summary():
    today = date.today().isoformat()
    latest_logs = get_update_logs(1)
    codes = get_access_codes(500)
    orders = get_orders(500)
    ai_today = 0
    if IS_POSTGRES:
        with engine.begin() as conn:
            ai_today = conn.execute(
                select(func.count()).select_from(ai_usage_logs).where(ai_usage_logs.c.usage_date == today)
            ).scalar_one()
            total_draws = conn.execute(select(func.count()).select_from(draw_results)).scalar_one()
    else:
        with get_sqlite_conn() as conn:
            ai_today = conn.execute(
                "SELECT COUNT(*) AS cnt FROM ai_usage_logs WHERE usage_date=?", (today,)
            ).fetchone()["cnt"]
            total_draws = conn.execute(
                "SELECT COUNT(*) AS cnt FROM draw_results"
            ).fetchone()["cnt"]
    return {
        "active_codes": len([c for c in codes if c["status"] == "active"]),
        "pending_orders": len([o for o in orders if o["status"] == "pending"]),
        "ai_today": ai_today,
        "total_draws": total_draws,
        "last_update": latest_logs[0]["created_at"] if latest_logs else "-",
    }
