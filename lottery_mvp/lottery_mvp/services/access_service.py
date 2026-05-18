import streamlit as st

from config import DEFAULT_PAID_ALLOWED_TYPES, LOTTERY_CONFIG
from db import admin_login, get_ai_limit, verify_access_code


def ensure_session_defaults():
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("access_code", "")
    st.session_state.setdefault("plan_type", "free")
    st.session_state.setdefault("admin_ok", False)
    st.session_state.setdefault("member_name", "")
    st.session_state.setdefault("allowed_lotteries", [])


def login_with_code(code: str):
    ok, msg, row = verify_access_code(code, device_key="streamlit-browser")
    if ok:
        st.session_state["logged_in"] = True
        st.session_state["access_code"] = code
        st.session_state["plan_type"] = row["plan_type"]
        st.session_state["member_name"] = code
        allowed = [item for item in (row.get("allowed_lotteries") or "").split(",") if item]
        if row["plan_type"] == "paid" and not allowed:
            allowed = DEFAULT_PAID_ALLOWED_TYPES[:3]
        st.session_state["allowed_lotteries"] = allowed
    return ok, msg


def logout():
    st.session_state["logged_in"] = False
    st.session_state["access_code"] = ""
    st.session_state["plan_type"] = "free"
    st.session_state["member_name"] = ""
    st.session_state["allowed_lotteries"] = []


def admin_sign_in(password: str):
    st.session_state["admin_ok"] = admin_login(password)
    return st.session_state["admin_ok"]


def is_member():
    return st.session_state.get("logged_in", False)


def current_plan():
    return st.session_state.get("plan_type", "free")


def current_access_code():
    return st.session_state.get("access_code", "")


def can_view_full_history():
    return current_plan() == "paid"


def history_limit():
    return 200 if can_view_full_history() else 10


def can_export_csv():
    return can_view_full_history()


def allowed_lotteries():
    if current_plan() != "paid":
        return list(LOTTERY_CONFIG.keys())
    return st.session_state.get("allowed_lotteries", DEFAULT_PAID_ALLOWED_TYPES[:3])


def allowed_lottery_names():
    return [LOTTERY_CONFIG[key]["name"] for key in allowed_lotteries() if key in LOTTERY_CONFIG]


def can_access_lottery(lottery_type: str):
    if current_plan() != "paid":
        return True
    return lottery_type in allowed_lotteries()


def can_use_ai_feature(used_today: int):
    limit = get_ai_limit(current_plan())
    return used_today < limit, limit
