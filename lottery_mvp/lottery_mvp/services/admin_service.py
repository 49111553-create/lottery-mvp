from datetime import datetime

from config import LOTTERY_CONFIG
from db import (
    create_access_codes,
    disable_access_code,
    extend_access_code,
    get_access_codes,
    get_admin_actions,
    get_dashboard_summary,
    get_fetch_logs,
    get_orders,
    get_update_logs,
    manual_upsert_draw,
    mark_order_issued,
    save_admin_action,
)
from services.draw_service import seed_all_demo_data
from data_service import run_daily_update


def dashboard_data():
    return get_dashboard_summary()


def generate_codes(
    count: int,
    plan_type: str,
    days_valid: int,
    note: str,
    allowed_lotteries: list[str] | None = None,
    admin_name: str = "admin",
):
    codes = create_access_codes(
        count,
        plan_type=plan_type,
        days_valid=days_valid,
        note=note,
        allowed_lotteries=allowed_lotteries,
    )
    save_admin_action(
        admin_name,
        "create_codes",
        "access_codes",
        ",".join(codes[:5]),
        f"count={count}, plan={plan_type}, allowed={','.join(allowed_lotteries or [])}",
    )
    return codes


def disable_code(code: str, admin_name: str = "admin"):
    disable_access_code(code)
    save_admin_action(admin_name, "disable_code", "access_code", code, "manual disable")


def extend_code(code: str, days: int, admin_name: str = "admin"):
    ok = extend_access_code(code, days)
    if ok:
        save_admin_action(admin_name, "extend_code", "access_code", code, f"extend {days} days")
    return ok


def issue_code_for_order(order_id: int, code: str, admin_name: str = "admin"):
    mark_order_issued(order_id, code)
    save_admin_action(admin_name, "issue_code", "order", str(order_id), code)


def get_admin_lists():
    return {
        "codes": get_access_codes(),
        "orders": get_orders(),
        "update_logs": get_update_logs(),
        "fetch_logs": get_fetch_logs(),
        "admin_actions": get_admin_actions(),
    }


def run_seed(admin_name: str = "admin"):
    count = seed_all_demo_data()
    save_admin_action(admin_name, "seed_demo", "draw_results", "all", f"count={count}")
    return count


def run_update(admin_name: str = "admin"):
    count = run_daily_update()
    save_admin_action(admin_name, "run_update", "draw_results", "all", f"count={count}")
    return count


def save_manual_draw(
    lottery_type: str,
    issue: str,
    draw_date: str,
    numbers_main: str,
    numbers_extra: str,
    admin_name: str = "admin",
):
    record = {
        "lottery_type": lottery_type,
        "issue": issue,
        "draw_date": draw_date or datetime.utcnow().date().isoformat(),
        "numbers_main": numbers_main,
        "numbers_extra": numbers_extra,
        "sales_amount": 0,
        "jackpot_amount": 0,
        "source_name": "manual_admin",
        "source_url": "",
        "ingested_at": datetime.utcnow().isoformat(),
    }
    manual_upsert_draw(record)
    save_admin_action(admin_name, "manual_upsert_draw", lottery_type, issue, numbers_main)
    return record
